"""Shared demo-capture config builders (routes, ports, video steps)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

_WEBAPP_CANDIDATES = ("web_sota", "webapp", "webapp/frontend", "web-sota")
_APP_TSX_CANDIDATES = (
    "web_sota/src/App.tsx",
    "webapp/src/App.tsx",
    "webapp/frontend/src/App.tsx",
    "src/App.tsx",
)
_SRC_CANDIDATES = ("web_sota/src", "webapp/src", "webapp/frontend/src")


def resolve_frontend_dir(repo_root: Path) -> Path | None:
    """Return the webapp root directory if it exists."""
    for rel in _WEBAPP_CANDIDATES:
        candidate = repo_root / rel.replace("/", "\\")
        if candidate.is_dir() and (candidate / "package.json").is_file():
            return candidate
    return None


def scan_routes(repo_root: str | Path) -> list[dict[str, str]]:
    """Scan a fleet repo's App.tsx or router config for page routes."""
    root = Path(repo_root)
    routes: list[dict[str, str]] = []
    for pattern in _APP_TSX_CANDIDATES:
        app_file = root / pattern.replace("/", "\\")
        if not app_file.is_file():
            continue
        text = app_file.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r'<Route\s+path=["\']([^"\']+)["\'].*?element=\{<(\w+)\s*/>\}', text, re.DOTALL):
            routes.append({"path": m.group(1), "component": m.group(2)})
        for m in re.finditer(r'path:\s*["\']([^"\']+)["\'],?\s*element:\s*<(\w+)', text):
            routes.append({"path": m.group(1), "component": m.group(2)})
        break
    return routes


def scan_data_testid(repo_root: str | Path) -> list[str]:
    """Extract all data-testid values from the webapp source."""
    root = Path(repo_root)
    testids: list[str] = []
    for base in _SRC_CANDIDATES:
        src_dir = root / base.replace("/", "\\")
        if not src_dir.is_dir():
            continue
        for src_file in list(src_dir.rglob("*.tsx")) + list(src_dir.rglob("*.ts")):
            text = src_file.read_text(encoding="utf-8", errors="replace")
            for m in re.finditer(r'data-testid=["\']([^"\']+)["\']', text):
                testids.append(m.group(1))
        break
    return sorted(set(testids))


def read_ports_from_start(repo_root: str | Path) -> dict[str, int]:
    """Try to determine backend and frontend ports from start.ps1."""
    root = Path(repo_root)
    ports: dict[str, int] = {"backend": 11028, "frontend": 11029}
    for ps1 in [root / "start.ps1", root / "web_sota" / "start.ps1", root / "webapp" / "start.ps1"]:
        if not ps1.is_file():
            continue
        text = ps1.read_text(encoding="utf-8", errors="replace")
        for name, key in (("BackendPort", "backend"), ("FrontendPort", "frontend")):
            m = re.search(rf"\${name}\s*=\s*(\d+)", text)
            if m:
                ports[key] = int(m.group(1))
        break
    return ports


def description_to_steps(description: str, routes: list[dict[str, str]], testids: list[str]) -> list[dict[str, Any]]:
    """Parse a natural language description into video steps."""
    desc_lower = description.lower()
    steps: list[dict[str, Any]] = []
    visited: set[str] = set()

    dashboard_routes = [r for r in routes if r["path"] in ("/", "/dashboard")]
    if dashboard_routes:
        route = dashboard_routes[0]
        steps.append({"action": "goto", "url": route["path"]})
        if "dashboard" in testids:
            steps.append({"action": "wait_selector", "selector": "[data-testid='dashboard']"})
        else:
            steps.append({"action": "wait", "ms": 2000})
        visited.add(route["path"])

    keyword_map = [
        ("animat", [r for r in routes if "animat" in r["path"] or "animat" in (r.get("component") or "").lower()]),
        ("layer", [r for r in routes if "layer" in r["path"] or "layer" in (r.get("component") or "").lower()]),
        ("tool", [r for r in routes if "tool" in r["path"] or "agent" in r["path"] or "action" in r["path"]]),
        ("setting", [r for r in routes if "setting" in r["path"]]),
        ("status", [r for r in routes if r["path"] in ("/status", "/health")]),
        ("log", [r for r in routes if "log" in r["path"]]),
        ("help", [r for r in routes if r["path"] == "/help"]),
        ("chat", [r for r in routes if "chat" in r["path"]]),
    ]

    for keyword, matched in keyword_map:
        if keyword in desc_lower:
            for route in matched:
                if route["path"] not in visited:
                    steps.append({"action": "goto", "url": route["path"]})
                    steps.append({"action": "wait", "ms": 1500})
                    visited.add(route["path"])

    for route in routes:
        if route["path"] not in visited and len(steps) < 15:
            steps.append({"action": "goto", "url": route["path"]})
            steps.append({"action": "wait", "ms": 1000})
            visited.add(route["path"])

    return steps


def routes_to_pages(routes: list[dict[str, str]], testids: list[str]) -> list[dict[str, str]]:
    """Build screenshot page list from routes."""
    pages: list[dict[str, str]] = []
    for route in routes:
        selector = ""
        component = route.get("component") or ""
        tid = f"kpi-{component.lower().replace('page', '')}" if component else ""
        if tid and tid in testids:
            selector = f"[data-testid='{tid}']"
        pages.append(
            {
                "route": route["path"],
                "selector": selector,
                "name": component or route["path"].strip("/").capitalize() or "Home",
            }
        )
    return pages


def build_demo_config(
    repo_root: str | Path,
    *,
    backend_port: int | None = None,
    frontend_port: int | None = None,
    health_path: str = "/api/health",
    description: str = "Showcase the dashboard, then visit each major page.",
    repo_name: str | None = None,
) -> dict[str, Any]:
    """Build a complete demo-capture config.json payload."""
    root = Path(repo_root)
    name = repo_name or root.name
    routes = scan_routes(root)
    testids = scan_data_testid(root)
    ports = read_ports_from_start(root)
    backend = backend_port or ports["backend"]
    frontend = frontend_port or ports["frontend"]
    frontend_dir = resolve_frontend_dir(root)
    rel_frontend = frontend_dir.relative_to(root).as_posix() if frontend_dir else "web_sota"

    pages = routes_to_pages(routes, testids)
    video_steps = description_to_steps(description, routes, testids)
    if not video_steps:
        video_steps = [{"action": "goto", "url": "/"}, {"action": "wait", "ms": 2000}]

    return {
        "backend_port": backend,
        "frontend_port": frontend,
        "health_path": health_path,
        "output_dir": "../../docs/screenshots",
        "video_name": "demo walkthrough",
        "trace_name": "demo-trace.zip",
        "frontend_dir": rel_frontend,
        "pages": pages,
        "video_steps": video_steps,
        "repo": name,
    }
