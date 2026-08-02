"""Async dynamic capability router: lazy-loading proxy for the 130+ server fleet.

Builds a lightweight SQLite index mapping semantic intent / tool names to
specific local MCP server endpoints. On invocation of meta_route_tool, it
hot-starts the required sub-server if not already running, proxies the
payload, and returns the response.
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
import structlog

from meta_mcp.services.base import MetaMCPService

logger = structlog.get_logger(__name__)

_DEFAULT_SCAN_ROOTS: tuple[str, ...] = (
    "D:/Dev/repos",
    os.path.expandvars(r"%USERPROFILE%\Dev\repos"),
)

_DEFAULT_SERVER_MANIFEST_GLOBS: tuple[str, ...] = (
    "pyproject.toml",
    "package.json",
    "manifest.json",
    "glama.json",
)

_FLEET_PORT_REGISTRY: dict[str, int] = {}

_DEFAULT_PORT = 10718


@dataclass
class ServerCapability:
    """A single tool entry in the routing index."""

    tool_name: str
    server_name: str
    repo_path: str
    port: int
    transport: str = "http"
    server_command: list[str] = field(default_factory=list)
    description: str = ""
    required_env: dict[str, str] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "server_name": self.server_name,
            "repo_path": self.repo_path,
            "port": self.port,
            "transport": self.transport,
            "server_command": self.server_command,
            "description": self.description,
        }


def _resolve_repos_dir() -> Path:
    env = os.environ.get("FLEET_REPOS_ROOT") or os.environ.get("REPOS_DIR")
    if env:
        return Path(env).expanduser()
    for candidate in _DEFAULT_SCAN_ROOTS:
        p = Path(candidate).expanduser()
        if p.is_dir():
            return p
    return Path("D:/Dev/repos").expanduser()


def _scan_pyproject_tools(repo_path: Path) -> list[str]:
    """Extract registered tool names from a repo's pyproject.toml [project.scripts]."""
    toml_path = repo_path / "pyproject.toml"
    if not toml_path.is_file():
        return []
    try:
        content = toml_path.read_text(encoding="utf-8")
    except OSError:
        return []
    tools: list[str] = []
    in_scripts = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("[project.scripts]"):
            in_scripts = True
            continue
        if in_scripts:
            if stripped.startswith("[") and stripped != "[project.scripts]":
                break
            if "=" in stripped and not stripped.startswith("#"):
                name = stripped.split("=", 1)[0].strip()
                if name:
                    tools.append(name)
    return tools


def _scan_mcp_tool_decorators(repo_path: Path) -> list[str]:
    """Extract @mcp.tool(name=...) from Python source files."""
    src_dir = repo_path / "src"
    if not src_dir.is_dir():
        return []
    tool_names: list[str] = []
    for py_file in src_dir.rglob("*.py"):
        if ".venv" in str(py_file) or "node_modules" in str(py_file):
            continue
        try:
            content = py_file.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("@mcp.tool") and "name=" in stripped:
                name_part = stripped.split("name=", 1)[1]
                if name_part.startswith('"') or name_part.startswith("'"):
                    name_part = name_part[1:]
                name = name_part.split('"')[0].split("'")[0].split(",")[0].split(")")[0].strip()
                if name and not name.startswith("_"):
                    tool_names.append(name)
    return tool_names


def _detect_server_command(repo_path: Path) -> list[str] | None:
    """Detect the server start command from pyproject.toml or package.json."""
    pyproject = repo_path / "pyproject.toml"
    if pyproject.is_file():
        try:
            content = pyproject.read_text(encoding="utf-8")
        except OSError:
            pass
        else:
            for line in content.splitlines():
                if "=" in line and "-server" in line and ":" in line:
                    name = line.split("=", 0)[0].strip()
                    for script_line in content.splitlines():
                        if script_line.strip().startswith(f"{name} "):
                            parts = script_line.split("=", 1)
                            if len(parts) == 2:
                                return ["uv", "run", name]
                    return ["uv", "run", name]

    pkg_json = repo_path / "package.json"
    if pkg_json.is_file():
        try:
            data = json.loads(pkg_json.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        scripts = data.get("scripts", {})
        if "start" in scripts:
            return ["npm", "run", "start"]
        if "dev" in scripts:
            return ["npm", "run", "dev"]
    return None


def _detect_server_port(repo_path: Path) -> int:
    """Detect the backend port from .env.example, start.ps1, or pyproject.toml."""
    port = _DEFAULT_PORT

    env_example = repo_path / ".env.example"
    if env_example.is_file():
        try:
            for line in env_example.read_text(encoding="utf-8").splitlines():
                for var in ("MCP_PORT", "PORT", "BACKEND_PORT"):
                    if line.strip().startswith(f"{var}="):
                        try:
                            port = int(line.split("=", 1)[1].strip().strip('"'))
                        except ValueError:
                            pass
                        break
        except OSError:
            pass

    start_ps1 = repo_path / "start.ps1"
    if start_ps1.is_file() and port == _DEFAULT_PORT:
        try:
            for line in start_ps1.read_text(encoding="utf-8").splitlines():
                if "BackendPort" in line or "BackendPort" in line or "Backend Port" in line:
                    import re

                    m = re.search(r"= (\d+)", line)
                    if m:
                        port = int(m.group(1))
                        break
        except OSError:
            pass

    return port


def _repo_name(path: Path) -> str:
    return path.name.replace(".", "-")


class CapabilityRouter(MetaMCPService):
    """Async dynamic capability router for the MCP server fleet.

    Maintains a lightweight SQLite index mapping tool names to server endpoints
    and manages subprocess lifecycle for on-demand server activation.
    """

    def __init__(self):
        super().__init__()
        self._repos_dir = _resolve_repos_dir()
        default_db = str(Path.home() / ".meta_mcp" / "capability_router.db")
        self._db_path = Path(os.environ.get("META_MCP_ROUTER_DB", default_db))
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._subprocesses: dict[str, subprocess.Popen[Any]] = {}
        self._health_cache: dict[str, tuple[float, bool]] = {}
        self._health_cache_ttl: float = 5.0
        self._http_client: httpx.AsyncClient | None = None
        self._scan_lock = asyncio.Lock()

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
        return self._http_client

    def _init_db(self, conn: sqlite3.Connection) -> None:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS capabilities (
                tool_name TEXT NOT NULL,
                server_name TEXT NOT NULL,
                repo_path TEXT NOT NULL,
                port INTEGER NOT NULL DEFAULT 10718,
                transport TEXT NOT NULL DEFAULT 'http',
                server_command TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                required_env TEXT NOT NULL DEFAULT '{}',
                last_seen REAL NOT NULL DEFAULT 0.0,
                PRIMARY KEY (tool_name, server_name)
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_cap_tool ON capabilities(tool_name)
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_cap_server ON capabilities(server_name)
            """
        )

    def _db_connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.row_factory = sqlite3.Row
        return conn

    async def scan_fleet(self, force: bool = False) -> dict[str, Any]:
        """Scan the fleet directory and rebuild the capabilities index.

        Walks all repos under the configured repos root, extracts tool names
        from Python source decorators and pyproject.toml scripts, and stores
        them in the SQLite routing table.
        """
        async with self._scan_lock:
            conn = self._db_connect()
            try:
                self._init_db(conn)
                existing_count = conn.execute("SELECT COUNT(*) FROM capabilities").fetchone()[0]
                if existing_count > 0 and not force:
                    newest = conn.execute("SELECT MAX(last_seen) FROM capabilities").fetchone()[0] or 0.0
                    if time.time() - newest < 300:
                        servers = conn.execute("SELECT DISTINCT server_name FROM capabilities").fetchall()
                        tool_count = existing_count
                        return {
                            "success": True,
                            "message": (
                                f"Index is fresh ({existing_count} tools across "
                                f"{len(servers)} servers). Use force=True to rebuild."
                            ),
                            "data": {
                                "tool_count": tool_count,
                                "server_count": len(servers),
                                "cached": True,
                                "last_scan_age_s": int(time.time() - newest),
                            },
                        }

                if force:
                    conn.execute("DELETE FROM capabilities")

                repos_scanned = 0
                tools_indexed = 0
                servers_found: set[str] = set()
                now = time.time()

                for entry in sorted(self._repos_dir.iterdir()):
                    if not entry.is_dir():
                        continue
                    if entry.name.startswith("."):
                        continue

                    pyproject = entry / "pyproject.toml"
                    pkg_json = entry / "package.json"
                    if not pyproject.is_file() and not pkg_json.is_file():
                        continue

                    repos_scanned += 1
                    server_name = _repo_name(entry)
                    port = _detect_server_port(entry)
                    command = _detect_server_command(entry) or []

                    tool_names = _scan_mcp_tool_decorators(entry)
                    if not tool_names:
                        tool_names = _scan_pyproject_tools(entry)

                    if tool_names:
                        servers_found.add(server_name)
                    for tool_name in tool_names:
                        conn.execute(
                            "INSERT OR REPLACE INTO capabilities "
                            "(tool_name, server_name, repo_path, port, server_command, last_seen) "
                            "VALUES (?, ?, ?, ?, ?, ?)",
                            (
                                tool_name,
                                server_name,
                                str(entry),
                                port,
                                json.dumps(command),
                                now,
                            ),
                        )
                        tools_indexed += 1

                conn.commit()

                return {
                    "success": True,
                    "message": (
                        f"Scanned {repos_scanned} repos: indexed {tools_indexed} "
                        f"tools across {len(servers_found)} servers"
                    ),
                    "data": {
                        "repos_scanned": repos_scanned,
                        "tools_indexed": tools_indexed,
                        "server_count": len(servers_found),
                        "servers": sorted(servers_found),
                    },
                }
            finally:
                conn.close()

    async def lookup_tool(self, tool_name: str) -> list[ServerCapability]:
        """Look up all servers that provide a given tool name.

        Returns a list of ServerCapability entries sorted with exact matches first.
        """
        conn = self._db_connect()
        try:
            self._init_db(conn)
            rows = conn.execute(
                "SELECT tool_name, server_name, repo_path, port, transport, server_command, description, required_env "
                "FROM capabilities WHERE tool_name = ?",
                (tool_name,),
            ).fetchall()
            if rows:
                results: list[ServerCapability] = []
                for row in rows:
                    cmd = json.loads(row["server_command"]) if row["server_command"] else []
                    env = json.loads(row["required_env"]) if row["required_env"] else {}
                    results.append(
                        ServerCapability(
                            tool_name=row["tool_name"],
                            server_name=row["server_name"],
                            repo_path=row["repo_path"],
                            port=row["port"],
                            transport=row["transport"],
                            server_command=cmd,
                            description=row["description"],
                            required_env=env,
                        )
                    )
                return results

            rows = conn.execute(
                "SELECT tool_name, server_name, repo_path, port, transport, server_command, description, required_env "
                "FROM capabilities WHERE tool_name LIKE ? LIMIT 20",
                (f"%{tool_name}%",),
            ).fetchall()
            results: list[ServerCapability] = []
            for row in rows:
                cmd = json.loads(row["server_command"]) if row["server_command"] else []
                env = json.loads(row["required_env"]) if row["required_env"] else {}
                results.append(
                    ServerCapability(
                        tool_name=row["tool_name"],
                        server_name=row["server_name"],
                        repo_path=row["repo_path"],
                        port=row["port"],
                        transport=row["transport"],
                        server_command=cmd,
                        description=row["description"],
                        required_env=env,
                    )
                )
            return results
        finally:
            conn.close()

    async def await_server_ready(self, server_name: str, port: int, timeout: float = 30.0) -> bool:
        """Poll the target server's /health endpoint until it responds 200."""
        now = time.time()
        cached = self._health_cache.get(server_name)
        if cached and (now - cached[0]) < self._health_cache_ttl and cached[1]:
            return True

        client = await self._get_client()
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                resp = await client.get(f"http://127.0.0.1:{port}/health", timeout=2.0)
                if resp.status_code == 200:
                    self._health_cache[server_name] = (time.time(), True)
                    return True
            except Exception:
                pass
            await asyncio.sleep(0.5)
        self._health_cache[server_name] = (time.time(), False)
        return False

    async def start_server(self, capability: ServerCapability) -> dict[str, Any]:
        """Hot-start a fleet server subprocess if not already running."""
        if await self.await_server_ready(capability.server_name, capability.port, timeout=1.0):
            return {"success": True, "message": f"{capability.server_name} already running on port {capability.port}"}

        cmd = capability.server_command
        if not cmd:
            return {
                "success": False,
                "message": f"No server command configured for {capability.server_name}. Run meta_route_scan first.",
            }

        repo_path = Path(capability.repo_path)
        if not repo_path.is_dir():
            return {"success": False, "message": f"Repo path not found: {capability.repo_path}"}

        env = os.environ.copy()
        env["PORT"] = str(capability.port)
        env["MCP_PORT"] = str(capability.port)
        env["MCP_HOST"] = "127.0.0.1"

        for k, v in capability.required_env.items():
            env[k] = v

        try:
            proc = subprocess.Popen(
                cmd,
                cwd=str(repo_path),
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            self._subprocesses[capability.server_name] = proc
        except Exception as e:
            return {"success": False, "message": f"Failed to start {capability.server_name}: {e}"}

        ready = await self.await_server_ready(capability.server_name, capability.port)
        if ready:
            return {"success": True, "message": f"{capability.server_name} started on port {capability.port}"}
        return {
            "success": False,
            "message": (f"{capability.server_name} started but did not become ready within timeout"),
        }

    async def route_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        target_server: str | None = None,
    ) -> dict[str, Any]:
        """Route a tool call to the appropriate fleet server.

        If target_server is specified, look up its port and forward directly.
        Otherwise, search the capabilities index by tool_name, start the server
        if needed, proxy the call, and return the result.
        """
        arguments = arguments or {}

        if target_server:
            conn = self._db_connect()
            try:
                row = conn.execute(
                    "SELECT tool_name, server_name, repo_path, port, transport, "
                    "server_command, description, required_env "
                    "FROM capabilities WHERE server_name = ? LIMIT 1",
                    (target_server,),
                ).fetchone()
                if not row:
                    return {
                        "success": False,
                        "message": (
                            f"Server '{target_server}' not found in capability index. Run meta_route_scan first."
                        ),
                    }
                cmd = json.loads(row["server_command"]) if row["server_command"] else []
                env = json.loads(row["required_env"]) if row["required_env"] else {}
                capability = ServerCapability(
                    tool_name=tool_name,
                    server_name=row["server_name"],
                    repo_path=row["repo_path"],
                    port=row["port"],
                    transport=row["transport"],
                    server_command=cmd,
                    description=row["description"],
                    required_env=env,
                )
            finally:
                conn.close()
        else:
            matches = await self.lookup_tool(tool_name)
            if not matches:
                return {
                    "success": False,
                    "message": (
                        f"No server found for tool '{tool_name}'. "
                        "Run meta_route_scan to rebuild the index, then try again."
                    ),
                    "data": {
                        "suggestions": [
                            "Run meta_route_scan",
                            "Check tool name spelling",
                            "Specify target_server directly",
                        ]
                    },
                }
            capability = matches[0]

        start_result = await self.start_server(capability)
        if not start_result.get("success"):
            return start_result

        client = await self._get_client()
        try:
            resp = await client.post(
                f"http://127.0.0.1:{capability.port}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {"name": tool_name, "arguments": arguments},
                },
                timeout=30.0,
            )
            resp.raise_for_status()
            result = resp.json()
            return {
                "success": True,
                "message": f"Routed {tool_name} via {capability.server_name}:{capability.port}",
                "data": result,
            }
        except httpx.HTTPStatusError as e:
            return {
                "success": False,
                "message": f"Server {capability.server_name} returned HTTP {e.response.status_code}",
                "data": {"status_code": e.response.status_code, "body": e.response.text[:500]},
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to route {tool_name} to {capability.server_name}: {e}",
            }

    async def list_capabilities(
        self,
        server_name: str | None = None,
        tool_query: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """List indexed capabilities, optionally filtered by server or tool name."""
        conn = self._db_connect()
        try:
            self._init_db(conn)
            if server_name:
                rows = conn.execute(
                    "SELECT tool_name, server_name, repo_path, port, description FROM capabilities "
                    "WHERE server_name = ? ORDER BY tool_name LIMIT ?",
                    (server_name, limit),
                ).fetchall()
            elif tool_query:
                rows = conn.execute(
                    "SELECT tool_name, server_name, repo_path, port, description FROM capabilities "
                    "WHERE tool_name LIKE ? ORDER BY tool_name LIMIT ?",
                    (f"%{tool_query}%", limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT tool_name, server_name, repo_path, port, description FROM capabilities "
                    "ORDER BY server_name, tool_name LIMIT ?",
                    (limit,),
                ).fetchall()

            servers = conn.execute("SELECT COUNT(DISTINCT server_name) FROM capabilities").fetchone()[0]
            tool_count = conn.execute("SELECT COUNT(*) FROM capabilities").fetchone()[0]

            capabilities = [dict(row) for row in rows]

            return {
                "success": True,
                "message": (
                    f"Found {len(capabilities)} capabilities (total: {tool_count} tools across {servers} servers)"
                ),
                "data": {"server_count": servers, "tool_count": tool_count, "capabilities": capabilities},
            }
        finally:
            conn.close()

    async def shutdown(self) -> None:
        """Kill all managed subprocesses."""
        for _name, proc in self._subprocesses.items():
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        self._subprocesses.clear()
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
