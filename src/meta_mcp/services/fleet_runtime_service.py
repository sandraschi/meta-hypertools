import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any

import aiohttp
import structlog

from meta_mcp.fleet_manifest import (
    discover_manifest_rows_from_repos,
    find_runtime_app,
    load_manifest_rows,
    load_runtime_apps,
    merge_manifest_rows,
    resolve_start_script,
)
from meta_mcp.fleet_paths import manifests_dir, startup_manifest
from meta_mcp.services.base import MetaMCPService

logger = structlog.get_logger(__name__)


class FleetRuntimeService(MetaMCPService):
    """
    Industrial Fleet Management Service.
    Uses vendored fleet-webapp-manifest.json + FLEET_REPOS_ROOT (no mcp-central-docs required).
    """

    def __init__(self):
        super().__init__()
        self._session: aiohttp.ClientSession | None = None

    def _manifest_path(self) -> Path:
        return startup_manifest()

    def _load_apps(self) -> list[dict[str, Any]]:
        return load_runtime_apps()

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2))
        return self._session

    async def _check_port(self, port: int, host: str = "127.0.0.1") -> bool:
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._sync_check_port, host, port)
        except Exception:
            return False

    def _sync_check_port(self, host: str, port: int) -> bool:
        import socket

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex((host, port)) == 0

    async def _check_health(self, port: int, health_path: str | None = None) -> dict[str, Any]:
        session = await self._get_session()
        paths = []
        if health_path:
            paths.append(health_path if health_path.startswith("/") else f"/{health_path}")
        paths.extend(["/health", "/api/health", "/api/v1/health"])

        seen: set[str] = set()
        endpoints: list[str] = []
        for p in paths:
            if p not in seen:
                seen.add(p)
                endpoints.append(f"http://127.0.0.1:{port}{p}")

        last_status: int | None = None
        last_url: str | None = None
        connect_errors: list[str] = []

        for url in endpoints:
            try:
                async with session.get(url) as response:
                    last_status = response.status
                    last_url = url
                    if response.status == 200:
                        try:
                            data = await response.json()
                            return {
                                "status": "healthy",
                                "url": url,
                                "http_status": 200,
                                "data": data,
                            }
                        except Exception:
                            text = await response.text()
                            return {
                                "status": "healthy",
                                "url": url,
                                "http_status": 200,
                                "text": text[:100],
                            }
            except Exception as e:
                connect_errors.append(str(e))
                continue

        # If all REST paths failed, try MCP streamable HTTP protocol probe.
        # Pure FastMCP HTTP servers have no REST endpoints; they return 406 on
        # every path (Accept: text/event-stream check). /mcp confirms liveness.
        if last_status is not None and last_status != 200:
            try:
                mcp_url = f"http://127.0.0.1:{port}/mcp"
                async with session.get(mcp_url, raise_for_status=False) as resp:
                    if resp.status in (200, 406, 404):
                        return {
                            "status": "healthy",
                            "url": mcp_url,
                            "http_status": resp.status,
                            "mode": "fastmcp_streamable_http",
                        }
            except Exception:
                pass

        if last_status is not None:
            return {
                "status": "deficient",
                "http_status": last_status,
                "url": last_url,
                "error": f"Health endpoint HTTP {last_status}",
            }

        detail = connect_errors[0] if connect_errors else "No health response"
        return {"status": "unavailable", "error": "No health response", "detail": detail}

    async def audit_fleet(self) -> dict[str, Any]:
        manifest = self._manifest_path()
        if not manifest.is_file():
            return self.create_response(
                False,
                f"Fleet manifest not found at {manifest}. Set META_MCP_FLEET_MANIFESTS_DIR or refresh manifest.",
            )

        try:
            apps = self._load_apps()
            if not apps:
                return self.create_response(False, f"No runnable apps in manifest {manifest}")

            audit_tasks = [self._audit_app(app) for app in apps]
            results = await asyncio.gather(*audit_tasks)

            total = len(apps)
            healthy = len([r for r in results if r["status"] == "healthy"])
            deficient = len([r for r in results if r["status"] == "deficient"])
            offline = len([r for r in results if r["status"] == "offline"])
            http_404 = len([r for r in results if r.get("health_code") == 404])
            http_500 = len([r for r in results if isinstance(r.get("health_code"), int) and r["health_code"] >= 500])
            unavailable = len(
                [r for r in results if r["status"] == "deficient" and not isinstance(r.get("health_code"), int)]
            )

            zombies = await self._find_zombies(apps)

            summary = {
                "total_apps": total,
                "healthy": healthy,
                "deficient": deficient,
                "offline": offline,
                "http_404": http_404,
                "http_500": http_500,
                "unavailable": unavailable,
                "zombies": len(zombies),
                "apps": results,
                "zombie_ports": zombies,
                "manifest_path": str(manifest),
            }

            return self.create_response(True, "Fleet audit completed", summary)

        except Exception as e:
            self.logger.error("Fleet audit failed", error=str(e))
            return self.create_response(False, f"Audit failed: {e!s}")

    async def _audit_app(self, app: dict[str, Any]) -> dict[str, Any]:
        port = app.get("port")
        if not port:
            return {**app, "status": "unknown", "error": "No port in manifest"}

        is_alive = await self._check_port(port)
        if not is_alive:
            return {**app, "status": "offline", "url": None}

        health = await self._check_health(port, app.get("health_path"))
        frontend_port = app.get("frontend_port") or 0
        url = f"http://127.0.0.1:{frontend_port or port}/"

        if health["status"] == "healthy":
            return {
                **app,
                "status": "healthy",
                "health_info": health,
                "health_code": health.get("http_status", 200),
                "url": url,
            }
        return {
            **app,
            "status": "deficient",
            "health_code": health.get("http_status"),
            "error": health.get("error") or "Port open but no health response",
            "health_info": health if health.get("url") else None,
            "url": url,
        }

    async def _find_zombies(self, registered_apps: list[dict[str, Any]]) -> list[dict[str, Any]]:
        registered_ports = {app.get("port") for app in registered_apps if app.get("port")}
        for app in registered_apps:
            fp = app.get("frontend_port")
            if fp:
                registered_ports.add(fp)
        zombies = []

        try:
            process = await asyncio.create_subprocess_shell(
                'netstat -ano | findstr LISTENING | findstr ":10"',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await process.communicate()
            output = stdout.decode()

            for line in output.splitlines():
                parts = line.split()
                if not parts:
                    continue
                addr = parts[1]
                if ":" not in addr:
                    continue
                try:
                    port = int(addr.split(":")[-1])
                    if 10700 <= port <= 11000 and port not in registered_ports:
                        pid = parts[-1]
                        zombies.append(
                            {
                                "port": port,
                                "pid": pid,
                                "status": "zombie",
                                "severity": "MEDIUM",
                                "message": f"Orphaned listener on fleet port {port}",
                            }
                        )
                except (ValueError, IndexError):
                    continue
        except Exception as e:
            logger.warning("Zombie scan failed", error=str(e))

        return zombies

    async def wait_for_health(
        self,
        app_id: str,
        *,
        timeout_sec: int = 90,
    ) -> dict[str, Any]:
        """Poll manifest health endpoints until ready or timeout."""
        app = find_runtime_app(app_id)
        if not app:
            return self.create_response(False, f"App {app_id!r} not found in fleet manifest")

        backend_port = int(app["port"])
        frontend_port = int(app.get("frontend_port") or 0)
        health_path = str(app.get("health_path") or "/health")
        deadline = asyncio.get_event_loop().time() + timeout_sec
        last_backend: dict[str, Any] = {}

        while asyncio.get_event_loop().time() < deadline:
            last_backend = await self._check_health(backend_port, health_path)
            backend_ok = last_backend.get("status") == "healthy"
            frontend_ok = frontend_port <= 0 or await self._check_port(frontend_port)
            if backend_ok and frontend_ok:
                return self.create_response(
                    True,
                    f"{app_id} stack ready",
                    {
                        "backend": last_backend,
                        "frontend_port_open": frontend_ok,
                    },
                )
            await asyncio.sleep(2)

        return self.create_response(
            False,
            f"{app_id} not ready within {timeout_sec}s",
            {
                "backend": last_backend,
                "frontend_port": frontend_port,
            },
        )

    async def start_app(
        self,
        app_id: str,
        *,
        headless: bool = False,
        no_browser: bool = False,
        frontend_only: bool = False,
        wait_health: bool = False,
        timeout_sec: int = 90,
    ) -> dict[str, Any]:
        """Start a fleet app via its repo start.ps1 (no mcp-central-docs/starts/*.bat)."""
        try:
            app = find_runtime_app(app_id)
            if not app:
                return self.create_response(
                    False,
                    f"App {app_id!r} not found in {self._manifest_path()}",
                )

            start_ps1 = resolve_start_script(app)
            if not start_ps1 or not start_ps1.is_file():
                return self.create_response(
                    False,
                    f"Could not find start.ps1 for {app_id} under {app.get('repo_path')}",
                )

            args = [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(start_ps1),
            ]
            if headless:
                args.append("-Headless")
            if no_browser:
                args.append("-NoBrowser")
            if frontend_only:
                args.append("-FrontendOnly")

            self.logger.info("Launching %s via %s", app_id, start_ps1)
            creationflags = getattr(subprocess, "CREATE_NEW_CONSOLE", 0)
            if headless:
                creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) or creationflags
            subprocess.Popen(
                args,
                cwd=str(start_ps1.parent),
                creationflags=creationflags,
            )

            data: dict[str, Any] = {
                "start_script": str(start_ps1),
                "headless": headless,
                "no_browser": no_browser,
                "frontend_only": frontend_only,
            }
            if wait_health:
                health = await self.wait_for_health(app_id, timeout_sec=timeout_sec)
                data["health"] = health
                if not health.get("success"):
                    return self.create_response(
                        False,
                        f"Launched {app_id} but health check failed",
                        data,
                    )

            return self.create_response(True, f"Launched {app_id} via {start_ps1.name}", data)

        except Exception as e:
            return self.create_response(False, f"Launch failed: {e!s}")

    async def stop_app(self, app_id: str) -> dict[str, Any]:
        """Stop a fleet app by killing the process on its manifest port."""
        try:
            app = find_runtime_app(app_id)
            if not app:
                return self.create_response(False, f"App {app_id} not found in fleet manifest")

            port = app.get("port")
            if not port:
                return self.create_response(False, f"No port registered for {app_id}")

            try:
                output = await asyncio.to_thread(subprocess.check_output, ["netstat", "-ano"])
                output = output.decode()
                lines = [
                    line.strip()
                    for line in output.splitlines()
                    if "LISTENING" in line and f":{port}" in line
                ]
                if not lines:
                    return self.create_response(
                        True,
                        f"No process found listening on port {port} (App likely already stopped)",
                    )

                pid = lines[0].split()[-1]
                self.logger.info("Killing process %s on port %s for %s", pid, port, app_id)
                await asyncio.to_thread(subprocess.run, ["taskkill", "/F", "/PID", pid], check=True)

                return self.create_response(True, f"Stopped {app_id} (Killed PID {pid} on port {port})")
            except subprocess.CalledProcessError:
                return self.create_response(True, f"No active process found on port {port}")

        except Exception as e:
            return self.create_response(False, f"Stop failed: {e!s}")

    def refresh_manifest_from_repos(self, *, dry_run: bool = False, full_rescan: bool = False) -> dict[str, Any]:
        """Merge or rebuild fleet-webapp-manifest.json from FLEET_REPOS_ROOT scan."""
        manifest_path = self._manifest_path()
        base: list[dict[str, Any]] = [] if full_rescan else load_manifest_rows()
        discovered = discover_manifest_rows_from_repos()
        merged = merge_manifest_rows(base, discovered)

        if dry_run:
            return {
                "success": True,
                "dry_run": True,
                "manifest_path": str(manifest_path),
                "existing": len(base),
                "discovered_new": len(discovered),
                "merged_total": len(merged),
                "full_rescan": full_rescan,
            }

        target = manifests_dir() / "fleet-webapp-manifest.json"
        target.parent.mkdir(parents=True, exist_ok=True)

        target.write_text(json.dumps(merged, indent=2) + "\n", encoding="utf-8")
        return {
            "success": True,
            "manifest_path": str(target),
            "existing": len(base),
            "discovered_new": len(discovered),
            "merged_total": len(merged),
            "full_rescan": full_rescan,
        }

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
