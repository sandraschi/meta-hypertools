"""Orchestrate fleet webapp demo capture: start stack, Playwright record, collect artifacts."""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from meta_mcp.fleet_manifest import find_manifest_row, find_runtime_app
from meta_mcp.fleet_paths import optional_mcp_central_docs
from meta_mcp.services.base import MetaMCPService
from meta_mcp.services.fleet_runtime_service import FleetRuntimeService
from meta_mcp.utils.demo_capture_config import build_demo_config, resolve_frontend_dir

_TEMPLATE_FILES = (
    "demo-screenshots.ts",
    "demo-video.ts",
    "playwright.demo.config.ts",
    "capture.ps1",
)
_REMOTION_ROOT_FILES = ("package.json", "tsconfig.json", "render.ps1")
_REMOTION_SRC_FILES = ("index.ts", "Root.tsx", "DemoComposition.tsx")


class DemoCaptureService(MetaMCPService):
    """Start a fleet webapp and capture Playwright screenshots + video walkthrough."""

    def __init__(self) -> None:
        super().__init__()
        self.runtime = FleetRuntimeService()

    def template_dir(self) -> Path:
        bundled = Path(__file__).resolve().parents[1] / "demo_capture_templates"
        if bundled.is_dir():
            return bundled
        handbook = optional_mcp_central_docs()
        if handbook:
            legacy = handbook / "templates" / "demo-capture"
            if legacy.is_dir():
                return legacy
        return bundled

    def remotion_template_dir(self) -> Path:
        bundled = self.template_dir() / "remotion"
        if bundled.is_dir():
            return bundled
        return Path(__file__).resolve().parents[1] / "demo_capture_templates" / "remotion"

    def screencast_dir(self, repo_root: Path) -> Path:
        return repo_root / "scripts" / "screencast"

    def resolve_app(self, app_id: str) -> dict[str, Any] | None:
        return find_runtime_app(app_id)

    def resolve_repo_path(self, app_id: str | None = None, repo_path: str | None = None) -> Path | None:
        if repo_path:
            path = Path(repo_path).expanduser()
            return path if path.is_dir() else None
        if not app_id:
            return None
        app = find_runtime_app(app_id)
        if not app:
            return None
        return Path(app["repo_path"])

    def plan_config(
        self,
        *,
        app_id: str | None = None,
        repo_path: str | None = None,
        description: str = "Showcase the dashboard, then visit each major page.",
    ) -> dict[str, Any]:
        root = self.resolve_repo_path(app_id, repo_path)
        if root is None:
            return self.create_response(False, "Repo not found — provide app_id or repo_path")

        app = find_runtime_app(app_id) if app_id else None
        manifest_row = find_manifest_row(root.name)
        backend_port = None
        frontend_port = None
        health_path = "/api/health"
        if app:
            backend_port = app.get("port")
            frontend_port = app.get("frontend_port") or None
            health_path = app.get("health_path") or health_path
        elif manifest_row:
            backend_port = manifest_row.get("port")
            frontend_port = manifest_row.get("frontendPort") or None
            health_path = manifest_row.get("healthPath") or health_path

        config = build_demo_config(
            root,
            backend_port=int(backend_port) if backend_port else None,
            frontend_port=int(frontend_port) if frontend_port else None,
            health_path=str(health_path),
            description=description,
            repo_name=root.name,
        )
        frontend_dir = resolve_frontend_dir(root)
        return self.create_response(
            True,
            f"Generated demo config for {root.name}",
            {
                "repo": root.name,
                "repo_path": str(root),
                "frontend_dir": str(frontend_dir) if frontend_dir else None,
                "config": config,
                "config_json": json.dumps(config, indent=2),
                "routes_found": len(config.get("pages") or []),
                "video_steps": len(config.get("video_steps") or []),
            },
        )

    def materialize_e2e(self, repo_root: Path, config: dict[str, Any]) -> dict[str, Any]:
        frontend = resolve_frontend_dir(repo_root)
        if frontend is None:
            rel = config.get("frontend_dir") or "web_sota"
            frontend = repo_root / rel.replace("/", "\\")
        e2e_dir = frontend / "e2e"
        e2e_dir.mkdir(parents=True, exist_ok=True)

        config_path = e2e_dir / "config.json"
        config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")

        copied: list[str] = []
        template_dir = self.template_dir()
        for name in _TEMPLATE_FILES:
            src = template_dir / name
            dst = e2e_dir / name
            if src.is_file() and not dst.exists():
                shutil.copy2(src, dst)
                copied.append(name)

        output_dir = (e2e_dir / (config.get("output_dir") or "../../docs/screenshots")).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        return {
            "e2e_dir": str(e2e_dir),
            "config_path": str(config_path),
            "output_dir": str(output_dir),
            "copied_templates": copied,
        }

    async def wait_for_stack(
        self,
        *,
        backend_port: int,
        frontend_port: int,
        health_path: str,
        timeout_sec: int = 90,
    ) -> dict[str, Any]:
        deadline = asyncio.get_event_loop().time() + timeout_sec
        backend_ok = False
        frontend_ok = frontend_port <= 0
        last_backend: dict[str, Any] = {}
        while asyncio.get_event_loop().time() < deadline:
            last_backend = await self.runtime._check_health(backend_port, health_path)
            backend_ok = last_backend.get("status") == "healthy"
            if frontend_port > 0:
                frontend_ok = await self.runtime._check_port(frontend_port)
            else:
                frontend_ok = backend_ok
            if backend_ok and frontend_ok:
                return {
                    "ready": True,
                    "backend": last_backend,
                    "frontend_port_open": frontend_ok,
                }
            await asyncio.sleep(2)

        return {
            "ready": False,
            "backend": last_backend,
            "frontend_port_open": frontend_ok if frontend_port > 0 else backend_ok,
            "error": "Stack not ready before timeout",
        }

    async def ensure_stack(
        self,
        app_id: str,
        *,
        timeout_sec: int = 90,
        reuse_existing: bool = True,
    ) -> dict[str, Any]:
        app = find_runtime_app(app_id)
        if not app:
            return self.create_response(False, f"App {app_id!r} not found in fleet manifest")

        backend_port = int(app["port"])
        frontend_port = int(app.get("frontend_port") or 0)
        health_path = str(app.get("health_path") or "/health")
        manifest_row = find_manifest_row(app_id) or {}
        nssm_service = manifest_row.get("nssmService")

        if reuse_existing:
            readiness = await self.wait_for_stack(
                backend_port=backend_port,
                frontend_port=frontend_port,
                health_path=health_path,
                timeout_sec=5,
            )
            if readiness.get("ready"):
                return self.create_response(
                    True,
                    f"Reusing running stack for {app_id}",
                    {"reused": True, "readiness": readiness},
                )

        frontend_only = bool(nssm_service)
        start_result = await self.runtime.start_app(
            app_id,
            headless=True,
            no_browser=True,
            frontend_only=frontend_only,
            wait_health=True,
            timeout_sec=timeout_sec,
        )
        if not start_result.get("success"):
            return start_result

        readiness = await self.wait_for_stack(
            backend_port=backend_port,
            frontend_port=frontend_port,
            health_path=health_path,
            timeout_sec=timeout_sec,
        )
        if not readiness.get("ready"):
            return self.create_response(
                False,
                f"Stack for {app_id} did not become ready",
                {"start": start_result.get("data"), "readiness": readiness},
            )

        return self.create_response(
            True,
            f"Stack ready for {app_id}",
            {
                "reused": False,
                "frontend_only": frontend_only,
                "nssm_service": nssm_service,
                "readiness": readiness,
            },
        )

    def _run_playwright(
        self,
        e2e_dir: Path,
        *,
        screenshots: bool,
        video: bool,
    ) -> dict[str, Any]:
        if not shutil.which("npx"):
            return {"success": False, "error": "npx not found on PATH — install Node.js"}

        targets: list[str] = []
        if screenshots:
            targets.append("demo-screenshots.ts")
        if video:
            targets.append("demo-video.ts")
        if not targets:
            targets = ["demo-screenshots.ts", "demo-video.ts"]

        cmd = [
            "npx",
            "playwright",
            "test",
            *targets,
            "--config",
            "playwright.demo.config.ts",
        ]
        proc = subprocess.run(
            cmd,
            cwd=str(e2e_dir),
            capture_output=True,
            text=True,
            timeout=300,
            shell=bool(__import__("os").name == "nt"),
        )
        return {
            "success": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout[-4000:] if proc.stdout else "",
            "stderr": proc.stderr[-4000:] if proc.stderr else "",
            "command": " ".join(cmd),
        }

    def _collect_artifacts(self, e2e_dir: Path, output_dir: Path) -> dict[str, list[str]]:
        screenshots: list[str] = []
        videos: list[str] = []
        traces: list[str] = []
        mp4s: list[str] = []

        if output_dir.is_dir():
            for path in sorted(output_dir.glob("*.png")):
                screenshots.append(str(path))
            for path in sorted(output_dir.glob("*.zip")):
                traces.append(str(path))
            for path in sorted(output_dir.glob("*.mp4")):
                mp4s.append(str(path))

        results_dir = e2e_dir / "demo-test-results"
        if results_dir.is_dir():
            for path in sorted(results_dir.rglob("*.webm")):
                videos.append(str(path))

        return {"screenshots": screenshots, "videos": videos, "traces": traces, "mp4": mp4s}

    def _find_latest_webm(self, repo_root: Path, e2e_dir: Path | None = None) -> Path | None:
        candidates: list[Path] = []
        search_roots = []
        if e2e_dir is not None:
            search_roots.append(e2e_dir / "demo-test-results")
        frontend = resolve_frontend_dir(repo_root)
        if frontend is not None:
            search_roots.append(frontend / "e2e" / "demo-test-results")
        screencast_public = self.screencast_dir(repo_root) / "public" / "source.webm"
        if screencast_public.is_file():
            candidates.append(screencast_public)
        for root in search_roots:
            if root.is_dir():
                candidates.extend(root.rglob("*.webm"))
        if not candidates:
            return None
        return max(candidates, key=lambda path: path.stat().st_mtime)

    def materialize_screencast(
        self,
        repo_root: Path,
        *,
        title: str,
        subtitle: str = "",
        source_webm: Path | None = None,
    ) -> dict[str, Any]:
        screencast = self.screencast_dir(repo_root)
        src_dir = screencast / "src"
        public_dir = screencast / "public"
        src_dir.mkdir(parents=True, exist_ok=True)
        public_dir.mkdir(parents=True, exist_ok=True)

        copied: list[str] = []
        template = self.remotion_template_dir()
        for name in _REMOTION_ROOT_FILES:
            src = template / name
            dst = screencast / name
            if src.is_file() and not dst.exists():
                shutil.copy2(src, dst)
                copied.append(name)
        for name in _REMOTION_SRC_FILES:
            src = template / "src" / name
            dst = src_dir / name
            if src.is_file() and not dst.exists():
                shutil.copy2(src, dst)
                copied.append(f"src/{name}")

        if source_webm and source_webm.is_file():
            target_webm = public_dir / "source.webm"
            shutil.copy2(source_webm, target_webm)

        output_mp4 = (repo_root / "docs" / "screenshots" / f"{repo_root.name}-demo.mp4").resolve()
        output_mp4.parent.mkdir(parents=True, exist_ok=True)

        config = {
            "title": title,
            "subtitle": subtitle,
            "repo": repo_root.name,
            "source_video": "public/source.webm",
            "output_mp4": output_mp4.as_posix(),
            "composition_id": "DemoComposition",
            "fps": 30,
            "width": 1280,
            "height": 720,
        }
        config_path = screencast / "screencast.config.json"
        config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        props_path = screencast / "screencast.props.json"
        props_path.write_text(json.dumps({"title": title, "subtitle": subtitle}, indent=2) + "\n", encoding="utf-8")

        return {
            "screencast_dir": str(screencast),
            "config_path": str(config_path),
            "props_path": str(props_path),
            "source_webm": str(public_dir / "source.webm"),
            "output_mp4": str(output_mp4),
            "copied_templates": copied,
        }

    def _ensure_npm_deps(self, screencast_dir: Path) -> dict[str, Any]:
        if not shutil.which("npm"):
            return {"success": False, "error": "npm not found on PATH — install Node.js"}
        node_modules = screencast_dir / "node_modules"
        package_json = screencast_dir / "package.json"
        if not package_json.is_file():
            return {"success": False, "error": f"Missing package.json in {screencast_dir}"}
        if node_modules.is_dir():
            return {"success": True, "skipped": True}
        proc = subprocess.run(
            ["npm", "install"],
            cwd=str(screencast_dir),
            capture_output=True,
            text=True,
            timeout=600,
            shell=os.name == "nt",
        )
        return {
            "success": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout[-3000:] if proc.stdout else "",
            "stderr": proc.stderr[-3000:] if proc.stderr else "",
        }

    def _run_remotion_render(self, screencast_dir: Path, output_mp4: Path, props_path: Path) -> dict[str, Any]:
        if not shutil.which("npx"):
            return {"success": False, "error": "npx not found on PATH — install Node.js"}
        source_webm = screencast_dir / "public" / "source.webm"
        if not source_webm.is_file():
            return {"success": False, "error": f"Missing source video: {source_webm}"}

        npm_result = self._ensure_npm_deps(screencast_dir)
        if not npm_result.get("success"):
            return npm_result

        output_mp4.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "npx",
            "remotion",
            "render",
            "src/index.ts",
            "DemoComposition",
            str(output_mp4),
            f"--props={props_path}",
        ]
        proc = subprocess.run(
            cmd,
            cwd=str(screencast_dir),
            capture_output=True,
            text=True,
            timeout=900,
            shell=os.name == "nt",
        )
        return {
            "success": proc.returncode == 0 and output_mp4.is_file(),
            "returncode": proc.returncode,
            "stdout": proc.stdout[-4000:] if proc.stdout else "",
            "stderr": proc.stderr[-4000:] if proc.stderr else "",
            "command": " ".join(cmd),
            "output_mp4": str(output_mp4),
            "npm": npm_result,
        }

    async def render(
        self,
        *,
        app_id: str | None = None,
        repo_path: str | None = None,
        video_path: str | None = None,
        title: str | None = None,
        subtitle: str = "",
    ) -> dict[str, Any]:
        root = self.resolve_repo_path(app_id, repo_path)
        if root is None:
            return self.create_response(False, "Repo not found — provide app_id or repo_path")

        source: Path | None = Path(video_path).expanduser() if video_path else None
        if source is None or not source.is_file():
            frontend = resolve_frontend_dir(root)
            e2e_dir = frontend / "e2e" if frontend else None
            source = self._find_latest_webm(root, e2e_dir)
        if source is None or not source.is_file():
            return self.create_response(
                False,
                "No Playwright .webm found — run demo_ops(record) first or pass video_path",
            )

        display_title = title or f"{root.name} — Fleet Demo"
        materialized = self.materialize_screencast(
            root,
            title=display_title,
            subtitle=subtitle,
            source_webm=source,
        )
        screencast_dir = Path(materialized["screencast_dir"])
        output_mp4 = Path(materialized["output_mp4"])
        props_path = Path(materialized["props_path"])

        remotion_result = self._run_remotion_render(screencast_dir, output_mp4, props_path)
        success = remotion_result.get("success", False)
        return self.create_response(
            success,
            f"Remotion render {'completed' if success else 'failed'} for {root.name}",
            {
                "repo": root.name,
                "repo_path": str(root),
                "source_webm": str(source),
                "screencast_dir": str(screencast_dir),
                "remotion": remotion_result,
                "artifacts": {
                    "mp4": [str(output_mp4)] if output_mp4.is_file() else [],
                    "webm": [str(source)],
                },
            },
        )

    async def record(
        self,
        *,
        app_id: str | None = None,
        repo_path: str | None = None,
        description: str = "Showcase the dashboard, then visit each major page.",
        screenshots: bool = True,
        video: bool = True,
        start_if_needed: bool = True,
        timeout_sec: int = 90,
        render_mp4: bool = False,
        subtitle: str = "",
    ) -> dict[str, Any]:
        root = self.resolve_repo_path(app_id, repo_path)
        if root is None:
            return self.create_response(False, "Repo not found — provide app_id or repo_path")

        resolved_app_id = app_id or root.name
        plan = self.plan_config(app_id=resolved_app_id, repo_path=str(root), description=description)
        if not plan.get("success"):
            return plan

        config = plan["data"]["config"]
        materialized = self.materialize_e2e(root, config)
        e2e_dir = Path(materialized["e2e_dir"])
        output_dir = Path(materialized["output_dir"])

        stack_info: dict[str, Any] | None = None
        if start_if_needed and find_runtime_app(resolved_app_id):
            stack_info = await self.ensure_stack(
                resolved_app_id,
                timeout_sec=timeout_sec,
                reuse_existing=True,
            )
            if not stack_info.get("success"):
                return stack_info

        pw_result = self._run_playwright(e2e_dir, screenshots=screenshots, video=video)
        artifacts = self._collect_artifacts(e2e_dir, output_dir)

        remotion_info: dict[str, Any] | None = None
        if render_mp4 and video and pw_result.get("success"):
            latest_webm = self._find_latest_webm(root, e2e_dir)
            if latest_webm is not None:
                remotion_info = await self.render(
                    repo_path=str(root),
                    video_path=str(latest_webm),
                    subtitle=subtitle,
                )
                if remotion_info.get("success"):
                    mp4_paths = remotion_info.get("data", {}).get("artifacts", {}).get("mp4", [])
                    artifacts["mp4"] = mp4_paths

        success = pw_result.get("success", False)
        if render_mp4 and remotion_info is not None:
            success = success and remotion_info.get("success", False)
        message = f"Demo capture {'completed' if success else 'failed'} for {root.name}"
        return self.create_response(
            success,
            message,
            {
                "repo": root.name,
                "repo_path": str(root),
                "e2e_dir": str(e2e_dir),
                "output_dir": str(output_dir),
                "stack": stack_info.get("data") if stack_info else None,
                "playwright": pw_result,
                "remotion": remotion_info,
                "artifacts": artifacts,
            },
        )

    async def close(self) -> None:
        await self.runtime.close()
