"""Dynamic routing proxy: lazy-loads fleet servers and routes tool calls.

Hot-starts MCP servers via subprocess isolation when they are first called,
then proxies the tool call via HTTP POST to the server's /mcp endpoint.

Built on top of CapabilityIndex (SQLite) for sub-second tool  server lookups.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

import structlog

from meta_mcp.fleet_manifest import load_runtime_apps
from meta_mcp.fleet_paths import repos_root
from meta_mcp.models.routing import IndexStats, RouteRequest, RouteResult, ServerEndpoint, ToolMapping
from meta_mcp.services.capability_index import CapabilityIndex

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Fleet port registry -- static fallback when live probing is unavailable.
# Source: mcp-central-docs/operations/WEBAPP_PORTS.md
# ---------------------------------------------------------------------------
_FLEET_PORT_MAP: dict[str, int] = {
    "arxiv-mcp": 10770,
    "multi-backup-mcp": 10799,
    "calibre-mcp": 10720,
    "plex-mcp": 10740,
    "email-mcp": 10813,
    "git-github-mcp": 10702,
    "bookmarks-mcp": 10803,
    "browser-mcp": 10776,
    "docker-mcp": 10807,
    "filesystem-mcp": 10742,
    "windows-operations-mcp": 10748,
    "notion-mcp": 10811,
    "speech-mcp": 10909,
    "obsidian-mcp": 10915,
    "llm-txt-mcp": 10837,
    "advanced-memory-mcp": 10704,
    "devices-mcp": 10717,
    "discord-mcp": 10756,
    "home-assistant-mcp": 10835,
    "immich-mcp": 10839,
    "jellyfin-mcp": 10934,
    "local-llm-mcp": 10833,
    "monitoring-mcp": 10851,
    "ocr-mcp": 10859,
    "scraper-mcp": 10998,
    "steam-mcp": 11020,
    "system-admin-mcp": 10861,
    "toolbench-mcp": 10817,
    "repomix-mcp": 10866,
    "quicknotes-mcp": 11058,
    "depot-mcp": 10727,
    "fleet-agent-mcp": 10996,
}

# MCP streamable HTTP sub-path where the server listens
_MCP_PATH = "/mcp"

# Timeout for tool calls (seconds)
_DEFAULT_TOOL_TIMEOUT = 60.0

# How long to hold server status cache before re-probing
_STATUS_CACHE_TTL = 30.0


class ServerProcess:
    """Keeps a lightweight reference to a managed subprocess."""

    __slots__ = ("pid", "proc", "server_name", "started_at")

    def __init__(self, proc: subprocess.Popen, server_name: str):
        self.proc = proc
        self.pid = proc.pid
        self.server_name = server_name
        self.started_at = time.time()

    def is_alive(self) -> bool:
        return self.proc.poll() is None

    def kill(self) -> None:
        try:
            if os.name == "nt" and self.pid:
                # Terminate entire process tree on Windows
                subprocess.run(
                    ["taskkill.exe", "/F", "/T", "/PID", str(self.pid)],
                    capture_output=True,
                    timeout=5,
                    check=False,
                )
            else:
                self.proc.terminate()
                self.proc.wait(timeout=5)
        except (subprocess.TimeoutExpired, OSError):
            try:
                self.proc.kill()
            except Exception:
                pass
        except Exception:
            pass


class DynamicRouter:
    """Lazy-loading proxy that routes tool calls to fleet MCP servers."""

    def __init__(
        self,
        index: CapabilityIndex | None = None,
        fleet_roots: list[Path] | None = None,
        port_map: dict[str, int] | None = None,
    ):
        self._index = index or CapabilityIndex()
        self._fleet_roots = fleet_roots or [
            repos_root(),
        ]

        # Combine static fallback map with runtime manifest apps
        combined_ports = dict(_FLEET_PORT_MAP)
        if port_map:
            combined_ports.update(port_map)
        else:
            try:
                for app in load_runtime_apps():
                    repo_name = app.get("repo")
                    port = app.get("port")
                    if repo_name and port:
                        combined_ports[repo_name] = int(port)
            except Exception:
                pass

        self._port_map = combined_ports
        self._running: dict[str, ServerProcess] = {}
        self._status_cache: dict[str, tuple[float, bool]] = {}
        self._indexed = False

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    async def ensure_indexed(self) -> None:
        """Lazy-first-time indexing: scan fleet configs and populate SQLite."""
        if self._indexed:
            return
        await self._scan_fleet_roots()
        await self._scan_ide_configs()
        self._indexed = True
        logger.info("dynamic_router_indexed", stats=self._index.stats().model_dump())

    async def reindex(self) -> IndexStats:
        """Full fleet re-scan."""
        self._index.clear()
        self._indexed = False
        self._status_cache.clear()
        await self.ensure_indexed()
        return self._index.stats()

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------

    async def route(self, request: RouteRequest) -> RouteResult:
        """Resolve tool_name, hot-start server if needed, proxy the call.

        Returns RouteResult with the tool output or error details.
        """
        t0 = time.perf_counter()
        await self.ensure_indexed()

        mapping = self._index.lookup_exact(request.tool_name, request.target_server)
        if not mapping:
            return RouteResult(
                success=False,
                tool_name=request.tool_name,
                server=request.target_server or "(unknown)",
                error=f"Tool '{request.tool_name}' not found in capability index. "
                f"Run reindex() or check fleet scan coverage.",
                suggestions=[
                    f"Search for similar tools: search_capabilities(query='{request.tool_name}')",
                    "Run reindex() to refresh the capability index",
                ],
            )

        server = mapping.server

        # Hot-start if not reachable
        if server.transport == "http" and server.port:
            reachable = await self._check_server_alive(server.server_name, server.host, server.port)
            if not reachable:
                launched = await self._hot_start_server(server.server_name, server)
                if not launched:
                    elapsed = (time.perf_counter() - t0) * 1000
                    return RouteResult(
                        success=False,
                        tool_name=request.tool_name,
                        server=server.server_name,
                        latency_ms=elapsed,
                        error=f"Could not reach or start server '{server.server_name}'",
                        suggestions=[
                            f"Check if port {server.port} is already occupied",
                            "Verify the server package is installed (uv sync)",
                            "Start the server manually and re-run reindex()",
                        ],
                    )

        try:
            result = await self._call_tool(mapping, request.arguments or {})
            elapsed = (time.perf_counter() - t0) * 1000
            return RouteResult(
                success=True,
                tool_name=request.tool_name,
                server=server.server_name,
                result=result,
                latency_ms=elapsed,
            )
        except Exception as exc:
            elapsed = (time.perf_counter() - t0) * 1000
            logger.exception("route_tool_failed", tool=request.tool_name, server=server.server_name)
            return RouteResult(
                success=False,
                tool_name=request.tool_name,
                server=server.server_name,
                latency_ms=elapsed,
                error=str(exc),
                suggestions=["Check server logs for errors", "Verify tool name and parameter schema"],
            )

    async def search_capabilities(self, query: str, limit: int = 20) -> list[ToolMapping]:
        """Semantic-ish search across tool names and descriptions."""
        await self.ensure_indexed()
        return self._index.search(query, limit=limit)

    async def get_stats(self) -> IndexStats:
        await self.ensure_indexed()
        return self._index.stats()

    async def list_servers(self) -> list[dict[str, Any]]:
        await self.ensure_indexed()
        return self._index.servers_summary()

    # ------------------------------------------------------------------
    # Internal: fleet scanning
    # ------------------------------------------------------------------

    async def _scan_fleet_roots(self) -> None:
        """Scan repo directories for pyproject.toml files and infer server commands."""
        mappings: list[ToolMapping] = []
        seen = set()

        for root in self._fleet_roots:
            if not root.is_dir():
                continue
            for candidate in root.iterdir():
                if not candidate.is_dir() or candidate.name.startswith("."):
                    continue
                repo_name = candidate.name
                if repo_name in seen:
                    continue

                pyproject = candidate / "pyproject.toml"
                if not pyproject.is_file():
                    continue

                try:
                    pkg_name = self._read_project_name(pyproject)
                except Exception:
                    continue

                if not pkg_name:
                    continue

                port = self._port_map.get(repo_name)
                command = f"uv run {pkg_name}-server" if pkg_name else None
                cwd = str(candidate)

                seen.add(repo_name)

                if port:
                    mappings.append(
                        ToolMapping(
                            tool_name=f"{repo_name}:*",
                            server=ServerEndpoint(
                                server_name=repo_name,
                                host="127.0.0.1",
                                port=port,
                                command=command,
                                cwd=cwd,
                                transport="http",
                            ),
                            description=f"Fleet server {repo_name} (auto-detected from pyproject.toml)",
                            status="unknown",
                        )
                    )

        if mappings:
            self._index.upsert_batch(mappings)

        # Probe HTTP endpoints to discover actual tools
        for repo_name, port in self._port_map.items():
            if repo_name in seen:
                await self._probe_server_tools(repo_name, "127.0.0.1", port)

    async def _scan_ide_configs(self) -> None:
        """Scan IDE mcp.json files for stdio-configured MCP servers."""
        ide_config_paths = [
            Path.home() / ".cursor" / "mcp.json",
            Path.home() / "AppData" / "Roaming" / "Claude" / "claude_desktop_config.json",
            Path.home() / "AppData" / "Roaming" / "Windsurf" / "mcp_config.json",
            Path.home() / ".gemini" / "antigravity" / "mcp_config.json",
        ]

        mappings: list[ToolMapping] = []
        for config_path in ide_config_paths:
            if not config_path.is_file():
                continue
            try:
                config = json.loads(config_path.read_text(encoding="utf-8"))
            except Exception:
                continue

            mcp_servers = config.get("mcpServers", {})
            for server_name, server_config in mcp_servers.items():
                if not isinstance(server_config, dict):
                    continue
                command = server_config.get("command", "")
                args = server_config.get("args", [])
                cwd = server_config.get("cwd")

                full_command = command
                if args:
                    full_command = f"{command} {' '.join(args)}"

                if server_name not in self._port_map and not server_config.get("url"):
                    # Stdio-only server -- record but don't try to hot-start via HTTP
                    mappings.append(
                        ToolMapping(
                            tool_name=f"{server_name}:*",
                            server=ServerEndpoint(
                                server_name=server_name,
                                command=full_command,
                                cwd=cwd,
                                transport="stdio",
                            ),
                            description=f"Stdio server {server_name} (from {config_path.name})",
                            status="unknown",
                        )
                    )

        if mappings:
            self._index.upsert_batch(mappings)

    async def _probe_server_tools(self, server_name: str, host: str, port: int) -> None:
        """Connect to a running server and discover its tool list."""
        url = f"http://{host}:{port}{_MCP_PATH}"
        try:
            from fastmcp import Client

            # fastmcp.Client performs the initialize handshake, captures the
            # Mcp-Session-Id, and sets the Accept header required by FastMCP 3.x
            async with Client(url, timeout=10.0) as client:
                tools = await client.list_tools()

            if not tools:
                return

            mappings: list[ToolMapping] = []
            for t in tools:
                tool_name = t.name
                if not tool_name:
                    continue
                mappings.append(
                    ToolMapping(
                        tool_name=tool_name,
                        server=ServerEndpoint(
                            server_name=server_name,
                            host=host,
                            port=port,
                            transport="http",
                        ),
                        description=t.description or "",
                        input_schema=t.inputSchema,
                        status="online",
                    )
                )

            if mappings:
                self._index.purge_server(server_name)
                self._index.upsert_batch(mappings)
                logger.debug("probed_server_tools", server=server_name, tool_count=len(mappings))

        except Exception:
            self._index.update_status(server_name, "offline")

    # ------------------------------------------------------------------
    # Internal: server lifecycle
    # ------------------------------------------------------------------

    async def _check_server_alive(self, server_name: str, host: str, port: int) -> bool:
        """Check if a server is reachable, with short-lived cache."""
        now = time.time()
        cached = self._status_cache.get(server_name)
        if cached and (now - cached[0]) < _STATUS_CACHE_TTL:
            return cached[1]

        try:
            from fastmcp import Client

            # fastmcp.Client performs the initialize handshake + session tracking
            # that live FastMCP 3.x servers require before accepting any call.
            async with Client(f"http://{host}:{port}{_MCP_PATH}", timeout=3.0) as client:
                await client.ping()
            alive = True
        except Exception:
            alive = False

        self._status_cache[server_name] = (now, alive)
        self._index.update_status(server_name, "online" if alive else "offline")
        return alive

    async def _hot_start_server(self, server_name: str, server: Any) -> bool:
        """Launch a fleet server via uv run if it has a registered command."""
        command = getattr(server, "command", None)
        fallback_root = os.environ.get("FLEET_REPOS_ROOT") or os.environ.get("REPOS_DIR")
        fallback_base = Path(fallback_root).expanduser() if fallback_root else Path.home() / "repos"
        cwd = getattr(server, "cwd", None) or str(fallback_base / server_name)
        port = getattr(server, "port", None)

        if not command:
            logger.warning("hot_start_skipped_no_command", server=server_name)
            return False

        env = os.environ.copy()
        if port:
            env["MCP_PORT"] = str(port)
            env["MCP_HOST"] = "127.0.0.1"

        try:
            proc = subprocess.Popen(
                command,
                shell=True,
                cwd=cwd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            sp = ServerProcess(proc, server_name)
            self._running[server_name] = sp

            # Poll for readiness
            for _ in range(30):
                await asyncio.sleep(1)
                if port and await self._check_server_alive(server_name, "127.0.0.1", port):
                    logger.info("hot_started_server", server=server_name, pid=sp.pid)
                    return True
                if not sp.is_alive():
                    logger.error("hot_start_crashed", server=server_name, pid=sp.pid)
                    return False

            logger.warning("hot_start_timeout", server=server_name, pid=sp.pid)
            return False
        except Exception:
            logger.exception("hot_start_failed", server=server_name)
            return False

    async def _call_tool(self, mapping: ToolMapping, arguments: dict[str, Any]) -> Any:
        """Execute a tool call via the MCP streamable HTTP endpoint."""
        server = mapping.server
        if server.transport != "http" or not server.port:
            raise RuntimeError(
                f"Server '{server.server_name}' has no HTTP port. "
                f"Only HTTP-transport servers are supported for routing."
            )

        url = f"http://{server.host}:{server.port}{_MCP_PATH}"

        from fastmcp import Client

        # fastmcp.Client performs the initialize handshake, captures the
        # Mcp-Session-Id, and sets the Accept header required by FastMCP 3.x
        async with Client(url, timeout=_DEFAULT_TOOL_TIMEOUT) as client:
            result = await client.call_tool(mapping.tool_name, arguments, raise_on_error=False)

        if result.is_error:
            texts = [getattr(block, "text", "") for block in result.content or []]
            raise RuntimeError("\n".join(t for t in texts if t) or "Tool call failed")

        if result.data is not None:
            return result.data
        if result.structured_content:
            return result.structured_content
        texts = [getattr(block, "text", "") for block in result.content or []]
        return "\n".join(t for t in texts if t)

    @staticmethod
    def _tcp_probe(host: str, port: int) -> bool:
        import socket

        try:
            s = socket.create_connection((host, port), timeout=2)
            s.close()
            return True
        except OSError:
            return False

    @staticmethod
    def _read_project_name(pyproject_path: Path) -> str | None:
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore[no-redef]

        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
        return (data.get("project") or {}).get("name")

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def shutdown(self) -> None:
        for proc in self._running.values():
            proc.kill()
        self._running.clear()
        self._index.close()
        logger.info("dynamic_router_shutdown")

    async def get_running_servers(self) -> list[dict[str, Any]]:
        return [
            {
                "server_name": name,
                "pid": sp.pid,
                "alive": sp.is_alive(),
                "uptime": time.time() - sp.started_at,
            }
            for name, sp in self._running.items()
        ]

    async def stop_server(self, server_name: str) -> dict[str, Any]:
        sp = self._running.pop(server_name, None)
        if sp:
            sp.kill()
            return {"success": True, "message": f"Stopped {server_name}"}
        return {"success": False, "message": f"Server {server_name} not running"}
