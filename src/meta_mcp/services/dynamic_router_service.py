"""Dynamic capabilities router service  lazy-loading proxy for the MCP server fleet.

Scans local fleet manifests and per-repo start.ps1 files to build a router index
that maps tool names to server endpoints. On invocation of meta_route_tool, hot-starts
the sub-server via subprocess if it isn't already running, proxies the MCP call over
HTTP (streamable or SSE), and returns the response.

Design goals:
- Sub-second local indexing via fleet manifest JSON + cached SQLite
- Hot-start sub-servers via uv run (isolated venv) or direct subprocess
- Async-safe with background index rebuild capability
- Non-blocking; suitable for MCP tool timeouts (Claude Desktop ~4 min)
"""

from __future__ import annotations

import asyncio
import json
import os
import socket
import time
from pathlib import Path
from typing import Any

import aiohttp
import structlog

from meta_mcp.fleet_manifest import (
    discover_manifest_rows_from_repos,
    load_manifest_rows,
    merge_manifest_rows,
)
from meta_mcp.fleet_paths import (
    repos_root,
)
from meta_mcp.router_index import RouterIndex
from meta_mcp.services.base import MetaMCPService

logger = structlog.get_logger(__name__)

# Known MCP HTTP endpoint patterns (ordered by fleet standard preference)
_MCP_PROBE_PATHS = (
    "/mcp",
    "/sse",
    "/mcp/sse",
)

# Timeout for probing a sub-server
_MCP_PROBE_TIMEOUT = aiohttp.ClientTimeout(total=30, connect=5)

# Sub-server startup grace period
_STARTUP_GRACE_SECONDS = 10

# Max retries for sub-server health check
_MAX_HEALTH_RETRIES = 30


def _best_startup_command(repo_path: Path) -> str | None:
    """Derive the best subprocess startup command for a given repo."""
    candidates = (
        repo_path / "web_sota" / "start.ps1",
        repo_path / "webapp" / "start.ps1",
        repo_path / "start.ps1",
    )
    start = next((c for c in candidates if c.is_file()), None)
    if not start:
        return None

    # Prefer direct uvicorn if a run_server.py or server.py is present
    # This avoids the full start.ps1 stack when we just need the MCP HTTP endpoint
    server_files = (
        repo_path / "run_server.py",
        repo_path / "src" / "server.py",
    )
    server_entry = next((s for s in server_files if s.is_file()), None)
    if server_entry:
        # Use uv run for isolated dependency resolution
        return f"uv run {server_entry}"

    # Fallback: use the start.ps1 with MCP_PORT env
    return f'pwsh -NoProfile -ExecutionPolicy Bypass -File "{start}"'


def _check_port(host: str, port: int, timeout: float = 0.5) -> bool:
    """Synchronous TCP port check."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


async def _async_check_port(host: str, port: int, timeout: float = 0.5) -> bool:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _check_port, host, port, timeout)


class ServerProcess:
    """Lightweight handle for a managed sub-server process."""

    def __init__(self, repo: str, port: int, process: asyncio.subprocess.Process):
        self.repo = repo
        self.port = port
        self.process = process
        self.started_at = time.time()

    async def terminate(self) -> None:
        try:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=5)
            except TimeoutError:
                self.process.kill()
                await self.process.wait()
        except ProcessLookupError:
            pass


class DynamicRouterService(MetaMCPService):
    """Lazy-loading MCP proxy router for the server fleet."""

    def __init__(self):
        super().__init__()
        self._index = RouterIndex()
        self._session: aiohttp.ClientSession | None = None
        self._running_servers: dict[str, ServerProcess] = {}
        self._build_lock = asyncio.Lock()
        self._index_built = False

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=_MCP_PROBE_TIMEOUT)
        return self._session

    async def ensure_index(self) -> dict[str, Any]:
        """Build the routing index on first use (idempotent)."""
        if self._index_built:
            return self._index.stats()

        async with self._build_lock:
            if self._index_built:
                return self._index.stats()

            self._index.ensure_schema()
            stats = await self._rebuild_from_fleet()
            self._index_built = True
            return stats

    async def rebuild_index(self) -> dict[str, Any]:
        """Force a full index rebuild from fleet manifests."""
        async with self._build_lock:
            self._index.ensure_schema()
            return await self._rebuild_from_fleet()

    async def _rebuild_from_fleet(self) -> dict[str, Any]:
        """Scan fleet manifests and index all known server endpoints."""
        start = time.monotonic()

        await self._index.clear_all()
        base_rows = load_manifest_rows()
        discovered = discover_manifest_rows_from_repos()
        merged = merge_manifest_rows(base_rows, discovered)

        indexed = 0
        for row in merged:
            repo = row.get("repo", "")
            port = row.get("port", 0)
            frontend_port = row.get("frontendPort", 0)
            health_path = row.get("healthPath", "/health")
            if not repo or (port <= 0 and frontend_port <= 0):
                continue

            repo_path = repos_root() / repo
            startup_cmd = _best_startup_command(repo_path)

            # Index the server endpoint (backend port)
            if port > 0:
                await self._index.insert_tool(
                    tool_name=f"_server:{repo}",
                    server_repo=repo,
                    server_port=port,
                    startup_command=startup_cmd,
                    health_path=health_path,
                    provenance="manifest",
                )
                indexed += 1

            # Probe the server for its tool catalog if it's currently running
            if port > 0 and await _async_check_port("127.0.0.1", port):
                await self._probe_server_tools(repo, port)

        elapsed = time.monotonic() - start
        stats = await self._index.stats()
        logger.info(
            "router_index_rebuilt",
            indexed_servers=indexed,
            total_tools=stats["tool_count"],
            elapsed_ms=int(elapsed * 1000),
        )
        return {
            "success": True,
            "message": (
                f"Index rebuilt: {stats['tool_count']} tools across "
                f"{stats['server_count']} servers in {int(elapsed * 1000)}ms"
            ),
            "data": stats,
        }

    async def _probe_server_tools(self, repo: str, port: int) -> None:
        """Query a running server for its tool catalog and index each tool."""
        session = await self._get_session()
        catalog_urls = [
            f"http://127.0.0.1:{port}{p}"
            for p in _TOOL_CATALOG_PATHS  # noqa: F821
        ]
        catalog_urls.append(f"http://127.0.0.1:{port}/api/v1/mcp/catalog")

        for url in catalog_urls:
            try:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        continue
                    data = await resp.json()
                    tools: list[dict[str, Any]] = []
                    if isinstance(data, dict):
                        tools = data.get("tools") or data.get("data", {}).get("tools") or []
                    if not tools:
                        continue

                    for tool in tools:
                        tool_name = tool.get("name") or tool.get("tool_name", "")
                        if not tool_name:
                            continue
                        await self._index.insert_tool(
                            tool_name=tool_name,
                            server_repo=repo,
                            server_port=port,
                            health_path="/health",
                            tool_schema=tool,
                            provenance="live_probe",
                        )
                    logger.info("catalog_indexed", repo=repo, port=port, tool_count=len(tools))
                    return  # stop at first successful catalog
            except (TimeoutError, aiohttp.ClientError, json.JSONDecodeError):
                continue

    async def route_tool(
        self,
        target_server: str,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Main entry point: route a tool call to the appropriate sub-server.

        Flow:
        1. Look up the tool in the index
        2. Hot-start the sub-server if not already running
        3. Proxy the MCP tool call over HTTP
        4. Return the response
        """
        await self.ensure_index()

        # Query the index for matching tools
        matches = await self._index.query_tools(tool_name=tool_name, server_repo=target_server or None, limit=10)

        if not matches:
            # Try semantic search
            semantic = await self._index.search_semantic(tool_name, limit=5)
            if not semantic:
                return self.create_response(
                    False,
                    f"No registered server found for tool '{tool_name}' on '{target_server or 'any'}'.",
                    {
                        "suggestions": [
                            "Run rebuild_routing_index to refresh the fleet index",
                            "Check that the target server is registered in fleet-webapp-manifest.json",
                        ]
                    },
                    error_type="not_found",
                )

        # Select best match
        best = matches[0]
        repo = best["server_repo"]
        port = best["server_port"]
        host = best["server_host"]

        # Ensure server is running
        if not await _async_check_port(host, port):
            startup_result = await self._start_server(repo, port, best.get("startup_command"))
            if not startup_result.get("success"):
                return startup_result

        # Proxy the MCP tool call
        return await self._proxy_mcp_call(repo, host, port, tool_name, arguments or {})

    async def _start_server(self, repo: str, port: int, startup_command: str | None) -> dict[str, Any]:
        """Hot-start a sub-server and wait for it to become reachable."""
        # Check for existing managed process
        if repo in self._running_servers:
            existing = self._running_servers[repo]
            if existing.process.returncode is None:
                # Still running  just wait for port
                pass
            else:
                del self._running_servers[repo]

        if not startup_command:
            repo_path = repos_root() / repo
            startup_command = _best_startup_command(repo_path)

        if not startup_command:
            return self.create_response(
                False,
                f"No startup command available for '{repo}'. Add a start.ps1 or run_server.py in the repo.",
                error_type="not_found",
            )

        logger.info(
            "hot_start_server",
            repo=repo,
            port=port,
            command=startup_command[:120],
        )

        try:
            # Set MCP_PORT for the sub-server so it knows to use HTTP transport
            env = os.environ.copy()
            env["MCP_PORT"] = str(port)
            env["MCP_HOST"] = "127.0.0.1"

            proc = await asyncio.create_subprocess_shell(
                startup_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=str(repos_root() / repo),
            )
            self._running_servers[repo] = ServerProcess(repo, port, proc)
        except Exception as e:
            return self.create_response(
                False,
                f"Failed to start server '{repo}': {e}",
                error_type="startup_failure",
            )

        # Wait for server to be reachable
        for attempt in range(_MAX_HEALTH_RETRIES):
            await asyncio.sleep(1.0)
            if await _async_check_port("127.0.0.1", port):
                # Also check health endpoint
                healthy = await self._check_server_health(port)
                if healthy:
                    logger.info("server_ready", repo=repo, port=port, attempt=attempt + 1)
                    return {"success": True, "message": f"Server {repo} ready on port {port}"}
                # Port open but health failing  might still be starting
            if attempt >= 5:
                # Check if process died
                if repo in self._running_servers:
                    proc = self._running_servers[repo]
                    if proc.process.returncode is not None:
                        stderr = await proc.process.stderr.read()
                        logger.error(
                            "server_died",
                            repo=repo,
                            exit_code=proc.process.returncode,
                            stderr=stderr[:500].decode("utf-8", errors="replace"),
                        )
                        return self.create_response(
                            False,
                            f"Server '{repo}' process exited with code {proc.process.returncode} during startup",
                            error_type="startup_failure",
                        )

        return self.create_response(
            False,
            f"Server '{repo}' did not become reachable on port {port} within {_MAX_HEALTH_RETRIES}s",
            error_type="timeout",
        )

    async def _check_server_health(self, port: int) -> bool:
        session = await self._get_session()
        health_urls = [
            f"http://127.0.0.1:{port}/health",
            f"http://127.0.0.1:{port}/api/health",
            f"http://127.0.0.1:{port}/api/v1/health",
        ]
        for url in health_urls:
            try:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        return True
            except (TimeoutError, aiohttp.ClientError):
                continue
        return False

    async def _proxy_mcp_call(
        self,
        repo: str,
        host: str,
        port: int,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """Proxy a tool call to the target MCP server via HTTP."""
        session = await self._get_session()

        # Standard MCP call_tool JSON-RPC over HTTP
        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
            "id": 1,
        }

        # Try streamable HTTP /mcp first
        for path in ("/mcp", "/sse", "/mcp/sse"):
            url = f"http://{host}:{port}{path}"
            try:
                async with session.post(url, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        result = data.get("result") or data.get("data") or data
                        content = result.get("content", [])
                        text_result = content[0].get("text", "") if content else str(result)
                        return {
                            "success": True,
                            "message": f"Routed {tool_name} to {repo}:{port}",
                            "data": {
                                "server": repo,
                                "tool": tool_name,
                                "result": text_result[:10000],
                                "raw": result,
                            },
                        }
                    elif resp.status == 404:
                        continue  # try next path
                    elif resp.status in (405, 406):
                        continue
                    else:
                        text = await resp.text()
                        logger.warning("mcp_proxy_error", url=url, status=resp.status, body=text[:200])
            except (TimeoutError, aiohttp.ClientError, json.JSONDecodeError):
                continue

        # Fallback: try the REST tool execution endpoint (if the server is FastAPI + FastMCP)
        rest_url = f"http://{host}:{port}/api/v1/tools/execute"
        rest_payload = {
            "server_id": repo,
            "tool_name": tool_name,
            "parameters": arguments,
        }
        try:
            async with session.post(rest_url, json=rest_payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return {
                        "success": True,
                        "message": f"Routed {tool_name} to {repo}:{port} (REST fallback)",
                        "data": {
                            "server": repo,
                            "tool": tool_name,
                            "result": data,
                        },
                    }
        except (TimeoutError, aiohttp.ClientError):
            pass

        return self.create_response(
            False,
            f"Could not proxy '{tool_name}' to {repo}:{port}  MCP endpoint not reachable.",
            {
                "suggestions": [
                    f"Check that the server at http://{host}:{port}/mcp accepts POST",
                    "Ensure the sub-server exposes an MCP HTTP transport",
                    "Try rebuild_routing_index to refresh tool schemas",
                ]
            },
            error_type="proxy_failure",
        )

    async def get_routing_status(self) -> dict[str, Any]:
        """Return index stats and running server status."""
        stats = await self._index.stats()
        running = {
            repo: {
                "port": proc.port,
                "alive": proc.process.returncode is None if proc.process else False,
                "uptime_seconds": int(time.time() - proc.started_at),
            }
            for repo, proc in self._running_servers.items()
        }
        return self.create_response(
            True,
            f"Router: {stats['tool_count']} tools, {stats['server_count']} servers, {len(running)} running",
            {"index_stats": stats, "running_servers": running},
        )

    async def search_tools(self, query: str, limit: int = 20) -> dict[str, Any]:
        """Semantic search for tools across the fleet index."""
        await self.ensure_index()
        matches = await self._index.search_semantic(query, limit)
        return self.create_response(
            True,
            f"Found {len(matches)} matching tools for '{query}'",
            {"query": query, "results": matches, "count": len(matches)},
        )

    async def shutdown(self) -> None:
        """Terminate all managed sub-server processes."""
        for repo, proc in list(self._running_servers.items()):
            await proc.terminate()
            logger.info("server_stopped", repo=repo)
        self._running_servers.clear()
        if self._session and not self._session.closed:
            await self._session.close()
