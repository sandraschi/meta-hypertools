import time
from pathlib import Path
from typing import Any

from meta_mcp.logging_config import get_logger

from .analyzers.ai_infrastructure_analyzer import analyze_ai_infrastructure
from .analyzers.ce_akg_analyzer import analyze_ce_akg
from .analyzers.docker_analyzer import analyze_docker_readiness

# Import sub-analyzers
from .analyzers.git_analyzer import analyze_git_health
from .analyzers.github_analyzer import analyze_github_health
from .analyzers.security_orchestration_analyzer import analyze_security_orchestration
from .analyzers.web_sota_analyzer import analyze_web_sota
from .decorators import ToolCategory, tool
from .mcp_repo_analyzer import _analyze_repo as analyze_mcp_sota

logger = get_logger(__name__)


def _determine_repo_classification(repo_path: Path, features: dict[str, Any]) -> str:
    """Determine the primary classification of the repository."""
    is_mcp = features.get("mcp", {}).get("fastmcp_version") is not None
    is_web = features.get("web_sota", {}).get("frontend_framework") is not None

    if is_mcp and is_web:
        return "hybrid"
    elif is_mcp:
        return "mcp_server"
    elif is_web:
        return "web_app"
    else:
        return "library/other"


@tool(
    name="analyze_fleet",
    description="""Perform multi-dimensional analysis across all repositories in a directory.

    Scans each sub-directory in the target path and classifies it (mcp_server, web_app, hybrid, other).
    Returns a unified JSON payload detailing:
    - Classification
    - Git backup health
    - Docker readiness
    - Web SOTA standards (React/Tailwind/Shadcn)
    - AI Infrastructure (LLMs, RAG, Observability)
    - Security & Orchestration (Auth, Sampling, Bastion)
    - CE-AKG (Cross-Environment Adversarial Knowledge Graph) Mapping
    - GitHub metrics
    - MCP SOTA standards
    """,
    category=ToolCategory.DISCOVERY,
    tags=["fleet", "analyzer", "git", "web", "ai", "security", "ce-akg"],
    estimated_runtime="10-30s",
)
async def analyze_fleet(scan_path: str | None = None) -> dict[str, Any]:
    """Scan a root directory and return multi-dimensional analysis for all repositories inside."""
    if scan_path is None:
        from meta_mcp.core.config import DEFAULT_REPOS_PATH

        scan_path = DEFAULT_REPOS_PATH

    path = Path(scan_path).expanduser().resolve()
    if not path.exists() or not path.is_dir():
        return {
            "success": False,
            "message": "Operation failed",
            "error": f"Path not found or not a directory: {scan_path}",
        }

    start_time = time.time()
    repositories = []

    items = [item for item in path.iterdir() if item.is_dir() and not item.name.startswith(".")]
    total_items = len(items)

    for idx, item in enumerate(items):
        logger.info(
            ":SCAN: Scanning repository: {repo} ({count}/{total})", repo=item.name, count=idx + 1, total=total_items
        )

        repo_data = {
            "name": item.name,
            "path": str(item),
            "timestamp": time.time(),
        }

        # 1. Component Analyzers
        repo_data["git"] = analyze_git_health(item)
        repo_data["docker"] = analyze_docker_readiness(item)
        repo_data["web_sota"] = analyze_web_sota(item)

        ai_infra = analyze_ai_infrastructure(item)
        repo_data["ai"] = ai_infra.get("ai", {})
        repo_data["infrastructure"] = ai_infra.get("infrastructure", {})

        sec_orch = analyze_security_orchestration(item)
        repo_data["security"] = sec_orch.get("security", {})
        repo_data["orchestration"] = sec_orch.get("orchestration", {})

        repo_data["github"] = analyze_github_health(item)

        # CE-AKG (Cross-Environment Adversarial Knowledge Graph) Mapping
        repo_data["ce_akg"] = analyze_ce_akg(item, path)

        # Pull MCP SOTA data from the legacy parser
        mcp_data = analyze_mcp_sota(item, deep_scan=False)
        if mcp_data and mcp_data.get("fastmcp_version"):
            repo_data["mcp"] = mcp_data
        else:
            repo_data["mcp"] = {}

        # 2. Classification
        repo_data["classification"] = _determine_repo_classification(item, repo_data)

        repositories.append(repo_data)

    duration = time.time() - start_time
    result = {
        "success": True,
        "scan_path": str(path),
        "total_repositories": len(repositories),
        "duration_seconds": round(duration, 2),
        "timestamp": time.time(),
        "repositories": repositories,
    }

    try:
        from meta_mcp.services.analysis_depot_service import AnalysisDepotService

        depot = AnalysisDepotService()
        depot.persist_run("fleet_multidim", result, scan_path=str(path))
    except Exception:
        pass

    return result
