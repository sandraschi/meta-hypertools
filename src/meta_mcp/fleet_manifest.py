"""Load and normalize fleet webapp manifest (vendored under fleet_probes/, no mcd required)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from meta_mcp.fleet_paths import repos_root, startup_manifest

_SKIP_REPOS = frozenset(
    {
        "mcp-central-docs",
        "_junk",
        "junk",
        "external",
        ".cursor",
        "node_modules",
    }
)

_START_CANDIDATES = (
    "web_sota/start.ps1",
    "webapp/start.ps1",
    "web-sota/start.ps1",
    "reversing-webapp/start.ps1",
    "web/start.ps1",
    "start.ps1",
)


def load_manifest_rows() -> list[dict[str, Any]]:
    path = startup_manifest()
    if not path.is_file():
        return []
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(raw, list):
        return [r for r in raw if isinstance(r, dict)]
    if isinstance(raw, dict):
        inner = raw.get("entries") or raw.get("webapps") or raw.get("manifest")
        if isinstance(inner, list):
            return [r for r in inner if isinstance(r, dict)]
    return []


def row_to_runtime_app(row: dict[str, Any]) -> dict[str, Any] | None:
    if row.get("probeSkip"):
        return None
    port = row.get("port")
    try:
        port_int = int(port) if port is not None else 0
    except (TypeError, ValueError):
        port_int = 0
    if port_int <= 0:
        return None

    repo = str(row.get("repo", "")).strip()
    if not repo:
        return None

    start_path = str(row.get("startPath") or "start.ps1").replace("\\", "/")
    repo_path = repos_root() / repo
    frontend = row.get("frontendPort")
    try:
        frontend_int = int(frontend) if frontend is not None else 0
    except (TypeError, ValueError):
        frontend_int = 0

    tags: list[str] = []
    if frontend_int > 0:
        tags.append("frontend")
    tags.append("backend")

    return {
        "id": repo,
        "label": repo,
        "port": port_int,
        "frontend_port": frontend_int,
        "repo_path": str(repo_path),
        "start_path": start_path,
        "health_path": row.get("healthPath") or "/health",
        "tags": tags,
        "starts_bats": row.get("startsBats") or [],
    }


def load_runtime_apps() -> list[dict[str, Any]]:
    apps: list[dict[str, Any]] = []
    for row in load_manifest_rows():
        app = row_to_runtime_app(row)
        if app:
            apps.append(app)
    return apps


def find_runtime_app(app_id: str) -> dict[str, Any] | None:
    needle = app_id.strip().lower()
    for app in load_runtime_apps():
        if app["id"].lower() == needle:
            return app
        if app["id"].replace("-mcp", "").lower() == needle.replace("-mcp", ""):
            return app
    return None


def find_manifest_row(app_id: str) -> dict[str, Any] | None:
    """Return raw manifest row (includes nssmService, probeSkip, etc.)."""
    needle = app_id.strip().lower()
    for row in load_manifest_rows():
        repo = str(row.get("repo", "")).strip()
        if not repo:
            continue
        if repo.lower() == needle:
            return row
        if repo.replace("-mcp", "").lower() == needle.replace("-mcp", ""):
            return row
    return None


def resolve_start_script(app: dict[str, Any]) -> Path | None:
    repo_path = Path(app["repo_path"])
    start_rel = str(app.get("start_path") or "start.ps1")
    candidate = repo_path / start_rel.replace("/", "\\")
    if candidate.is_file():
        return candidate
    for rel in _START_CANDIDATES:
        alt = repo_path / rel.replace("/", "\\")
        if alt.is_file():
            return alt
    return None


def _parse_ports_from_start_ps1(text: str) -> dict[str, int]:
    ports: dict[str, int] = {}
    for name in ("BackendPort", "FrontendPort", "WebPort", "ApiPort"):
        m = re.search(rf"\${name}\s*=\s*(\d+)", text)
        if m:
            ports[name] = int(m.group(1))
    return ports


def discover_manifest_rows_from_repos() -> list[dict[str, Any]]:
    """Scan FLEET_REPOS_ROOT for start.ps1 launchers (no mcp-central-docs/starts required)."""
    root = repos_root()
    if not root.is_dir():
        return []

    existing = {(r.get("repo"), r.get("startPath")) for r in load_manifest_rows()}
    discovered: list[dict[str, Any]] = []

    for repo_dir in sorted(root.iterdir()):
        if not repo_dir.is_dir() or repo_dir.name.startswith("."):
            continue
        if repo_dir.name in _SKIP_REPOS:
            continue

        for rel in _START_CANDIDATES:
            start_file = repo_dir / rel.replace("/", "\\")
            if not start_file.is_file():
                continue
            key = (repo_dir.name, rel.replace("\\", "/"))
            if key in existing:
                continue
            try:
                text = start_file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                text = ""
            ports = _parse_ports_from_start_ps1(text)
            backend = ports.get("BackendPort") or ports.get("ApiPort") or ports.get("WebPort") or 0
            frontend = ports.get("FrontendPort") or (ports.get("WebPort") if "BackendPort" in ports else 0)
            discovered.append(
                {
                    "repo": repo_dir.name,
                    "startPath": rel.replace("\\", "/"),
                    "port": backend,
                    "healthPath": "/health",
                    "timeoutSec": 90,
                    "startsBats": [],
                    "frontendPort": frontend,
                    "proxyHealthPath": "/health",
                }
            )
            break

    return discovered


def merge_manifest_rows(base: list[dict[str, Any]], extra: list[dict[str, Any]]) -> list[dict[str, Any]]:
    index: dict[tuple[str, str], dict[str, Any]] = {}
    for row in base:
        repo = str(row.get("repo", ""))
        sp = str(row.get("startPath", "")).replace("\\", "/")
        if repo:
            index[(repo, sp)] = row
    for row in extra:
        repo = str(row.get("repo", ""))
        sp = str(row.get("startPath", "")).replace("\\", "/")
        if repo and (repo, sp) not in index:
            index[(repo, sp)] = row
    return sorted(index.values(), key=lambda r: str(r.get("repo", "")).lower())
