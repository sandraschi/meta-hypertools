"""Fleet probe path resolution  meta_mcp-first, no mcp-central-docs required."""

from __future__ import annotations

import os
from pathlib import Path

_DEFAULT_REPOS_ROOT = Path("D:/Dev/repos")
_PACKAGE_ROOT = Path(__file__).resolve().parents[2]
_FLEET_PROBES_ROOT = _PACKAGE_ROOT / "fleet_probes"
_FLEET_PROBES_IN_REPO = _FLEET_PROBES_ROOT / "scripts"
_DEFAULT_LOCAL_FLEET = Path.home() / ".meta_mcp" / "fleet"
_DEFAULT_META_MCP_WEB = "http://127.0.0.1:10719/"


def repos_root() -> Path:
    raw = os.environ.get("FLEET_REPOS_ROOT") or os.environ.get("REPOS_DIR")
    if raw:
        return Path(raw).expanduser()
    return _DEFAULT_REPOS_ROOT.expanduser()


def optional_mcp_central_docs() -> Path | None:
    """Optional handbook clone  never required for MetaMCP runtime."""
    raw = os.environ.get("MCP_CENTRAL_DOCS_ROOT", "").strip()
    if raw:
        path = Path(raw).expanduser()
        if path.is_dir():
            return path
    sibling = repos_root().parent / "mcp-central-docs"
    if sibling.is_dir():
        return sibling
    return None


def fleet_probes_scripts_dir() -> Path:
    """Directory containing vendored probe scripts (canonical, public)."""
    if os.environ.get("META_MCP_FLEET_PROBES_ROOT"):
        return Path(os.environ["META_MCP_FLEET_PROBES_ROOT"]).expanduser()
    if _FLEET_PROBES_IN_REPO.is_dir():
        return _FLEET_PROBES_IN_REPO
    legacy = optional_mcp_central_docs()
    if legacy:
        handbook_scripts = legacy / "scripts"
        if handbook_scripts.is_dir():
            return handbook_scripts
    return _FLEET_PROBES_IN_REPO


def master_mcp_config_path() -> Path:
    """Resolve MASTER MCP client config without requiring mcp-central-docs."""
    env = os.environ.get("META_MCP_MASTER_CONFIG", "").strip()
    if env:
        return Path(env).expanduser()
    local = fleet_local_root() / "MASTER_MCP_CONFIG.json"
    if local.is_file():
        return local
    handbook = optional_mcp_central_docs()
    if handbook:
        candidate = handbook / "operations" / "MASTER_MCP_CONFIG.json"
        if candidate.is_file():
            return candidate
    return local


def fleet_registry_path() -> Path:
    """Fleet registry JSON for meta_dev health probes."""
    env = os.environ.get("META_MCP_FLEET_REGISTRY", "").strip()
    if env:
        return Path(env).expanduser()
    local = fleet_local_root() / "fleet-registry.json"
    if local.is_file():
        return local
    handbook = optional_mcp_central_docs()
    if handbook:
        candidate = handbook / "operations" / "fleet-registry.json"
        if candidate.is_file():
            return candidate
    return local


def meta_mcp_web_url() -> str:
    raw = os.environ.get("META_MCP_WEB_URL", "").strip()
    if raw:
        return raw if raw.endswith("/") else f"{raw}/"
    return _DEFAULT_META_MCP_WEB


def meta_mcp_web_start_script() -> Path:
    env = os.environ.get("META_MCP_START_PS1", "").strip()
    if env:
        return Path(env).expanduser()
    return _PACKAGE_ROOT / "web_sota" / "start.ps1"


def fleet_local_root() -> Path:
    return Path(os.environ.get("META_MCP_FLEET_DEPOT", str(_DEFAULT_LOCAL_FLEET))).expanduser()


def manifests_dir() -> Path:
    if os.environ.get("META_MCP_FLEET_MANIFESTS_DIR"):
        return Path(os.environ["META_MCP_FLEET_MANIFESTS_DIR"]).expanduser()
    return fleet_local_root() / "manifests"


def reports_dir() -> Path:
    if os.environ.get("META_MCP_FLEET_REPORTS_DIR"):
        return Path(os.environ["META_MCP_FLEET_REPORTS_DIR"]).expanduser()
    return fleet_local_root() / "reports"


def cold_install_probe_script() -> Path:
    if os.environ.get("FLEET_COLD_INSTALL_PROBE_SCRIPT"):
        return Path(os.environ["FLEET_COLD_INSTALL_PROBE_SCRIPT"]).expanduser()
    return fleet_probes_scripts_dir() / "fleet-cold-install-probe.ps1"


def cold_install_manifest() -> Path:
    if os.environ.get("FLEET_COLD_INSTALL_MANIFEST"):
        return Path(os.environ["FLEET_COLD_INSTALL_MANIFEST"]).expanduser()
    custom = manifests_dir() / "fleet-cold-install-manifest.json"
    if custom.is_file():
        return custom
    bundled = _FLEET_PROBES_ROOT / "manifests" / "fleet-cold-install-manifest.json"
    if bundled.is_file():
        return bundled
    return fleet_probes_scripts_dir().parent / "manifests" / "fleet-cold-install-manifest.json"


def cold_install_report_json() -> Path:
    return reports_dir() / "fleet-cold-install-report.json"


def cold_install_progress_json() -> Path:
    return reports_dir() / "fleet-cold-install-report.progress.json"


def startup_probe_script() -> Path:
    if os.environ.get("FLEET_PROBE_SCRIPT"):
        return Path(os.environ["FLEET_PROBE_SCRIPT"]).expanduser()
    return fleet_probes_scripts_dir() / "fleet-webapp-start-probe.ps1"


def startup_manifest() -> Path:
    if os.environ.get("FLEET_WEBAPP_MANIFEST"):
        return Path(os.environ["FLEET_WEBAPP_MANIFEST"]).expanduser()
    custom = manifests_dir() / "fleet-webapp-manifest.json"
    if custom.is_file():
        return custom
    bundled = _FLEET_PROBES_ROOT / "manifests" / "fleet-webapp-manifest.json"
    if bundled.is_file():
        return bundled
    return fleet_probes_scripts_dir().parent / "manifests" / "fleet-webapp-manifest.json"


def startup_report_json() -> Path:
    return reports_dir() / "fleet-webapp-report.json"


def startup_progress_json() -> Path:
    return reports_dir() / "fleet-webapp-report.progress.json"


def probe_cwd() -> Path:
    """Working directory for subprocess probe runs."""
    scripts = fleet_probes_scripts_dir()
    if scripts.is_dir():
        return scripts.parent
    return _PACKAGE_ROOT
