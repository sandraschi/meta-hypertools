"""
MCP Repository Analyzer Tool for MetaMCP.

Comprehensive repository analysis tool with FastMCP 3.4.2 validation,
sampling support detection, dialogic return validation, and SOTA compliance checking.

Scans MCP repositories and identifies "runts" - repos that need SOTA upgrades.
"""

import os
import re
import shutil
import time
from pathlib import Path
from typing import Any

import structlog
import tomli

from .decorators import ToolCategory, tool
from .runt_analyzer_rules import (
    calculate_sota_score,
    evaluate_rules,
)

# from .repo_detail_collector import collect_repo_details  # Module doesn't exist - using basic repo info instead
from .scan_cache import (
    cache_repo_status,
    cache_scan_result,
    get_cached_repo_status,
    get_cached_scan,
)
from .scan_formatter import format_repo_status_markdown, format_scan_result_markdown

logger = structlog.get_logger(__name__)

# SOTA thresholds (FastMCP 3.4.2+)
FASTMCP_LATEST = "3.4.2"
FASTMCP_RUNT_THRESHOLD = "3.4.2"
FASTMCP_SAMPLING_VERSION = "3.4.2"  # Sampling via ctx.sample() stabilized in 3.4.2
TOOL_PORTMANTEAU_THRESHOLD = 15  # Repos with >15 tools should have portmanteau

# Required SOTA features
REQUIRED_TOOLS = ["help", "status"]  # Every MCP server should have these
MCPB_FILES = ["manifest.json", "mcpb.json"]  # Desktop extension packaging

# SOTA Mandatory Files (Section 8 Safety)
SOTA_CRITICAL_FILES = [
    "glama.json",  # Glama.ai integration
    "manifest.json",  # MCP Packaging
    "requirements.txt",  # Dependency management (fallback/legacy)
]

# Quality tooling
RUFF_CONFIG_FILES = ["ruff.toml", ".ruff.toml"]  # Or [tool.ruff] in pyproject.toml
TEST_DIRS = ["tests", "test"]  # Standard test directories
PYTEST_MARKERS = ["pytest", "test_", "_test.py"]  # Evidence of pytest usage

# Logging patterns (good)
LOGGING_PATTERNS = [
    r"import\s+logging",
    r"import\s+structlog",
    r"from\s+logging\s+import",
    r"from\s+structlog\s+import",
    r"logger\s*=\s*logging\.getLogger",
    r"logger\s*=\s*structlog\.get_logger",
]

# Bad patterns (print/console in non-test code)  language-specific
PY_BAD_STDOUT_PATTERNS = [
    r"^\s*print\s*\(",  # print() calls
    r"sys\.stdout\.write\s*\(",  # Direct stdout writes
]
JS_BAD_STDOUT_PATTERNS = [
    r"console\.(log|warn|error|debug)\s*\(",  # JavaScript console calls
]

# Error handling patterns (bad)  separate bare except from broad Exception
BARE_EXCEPT_PATTERNS = [
    r"except\s*:",  # Bare except (catches everything including KeyboardInterrupt)
]
BROAD_EXCEPT_PATTERNS = [
    r"except\s+Exception\s*:",  # Broad exception without handling
]

# Good error handling patterns
GOOD_ERROR_PATTERNS = [
    r"except\s+\w+Error",  # Specific exception types
    r"logger\.\w+\(.*error",  # Logging errors
    r"raise\s+\w+Error",  # Re-raising specific errors
]

# Non-informative error messages (lazy/useless)
# NOTE: "error"/"failed" patterns use negative lookaround to skip dict-key and
# bracket/`.get()` access usage (e.g. {"error": str(e)}, result.get("error"),
# result["error"]) which is the standard structured-error-dict idiom in this
# codebase and is NOT a lazy error message. Without these guards this rule
# flags nearly every well-formed error-response dict as a violation.
# Patched 2026-07-01 after audit found ~427 aggregate hits were dominated by
# this false-positive pattern rather than genuine lazy strings.
LAZY_ERROR_MESSAGES = [
    r'(?<!\[)(?<!\.get\()["\']error["\'](?!\s*:)',  # Just "error" (not a dict key/access)
    r'["\']an?\s+error\s+(occurred|happened)["\']',  # "an error occurred"
    r'["\']something\s+went\s+wrong["\']',  # "something went wrong"
    r'(?<!\[)(?<!\.get\()["\']failed["\'](?!\s*:)',  # Just "failed" (not a dict key/access)
    r'["\']unknown\s+error["\']',  # "unknown error"
    r'["\']error:\s*["\']',  # "error: " with nothing after
    r'["\']exception["\']',  # Just "exception"
    r'["\']oops["\']',  # "oops"
    r'["\']uh\s*oh["\']',  # "uh oh"
    r'["\']something\s+broke["\']',  # "something broke"
    r'["\']it\s+failed["\']',  # "it failed"
    r'["\']error\s+in\s+\w+["\']',  # "error in X" without details
    r'raise\s+Exception\s*\(\s*["\'][^"\']{0,15}["\']\s*\)',  # raise Exception("short msg")
]

# ============================================================================
# MCP ZOO CLASSIFICATION
# Not a flea circus - these are proper beasts!
# ============================================================================

# Keywords indicating heavy/jumbo MCPs (database, virtualization, etc.)
JUMBO_INDICATORS = [
    "database",
    "postgres",
    "mysql",
    "sqlite",
    "mongo",
    "redis",  # Databases
    "docker",
    "kubernetes",
    "k8s",
    "container",
    "virtualization",  # Virtualization
    "virtualbox",
    "vmware",
    "qemu",
    "hyperv",  # VMs
    "davinci",
    "resolve",
    "premiere",
    "video",
    "render",  # Heavy video
    "blender",
    "3d",
    "modeling",  # 3D software
    "ai-",
    "llm-",
    "ml-",
    "machine-learning",  # AI/ML heavy
    "obs",
    "stream",
    "broadcast",  # Streaming
]

# Keywords indicating mini/chipmunk MCPs (simple, single-purpose)
CHIPMUNK_INDICATORS = [
    "txt",
    "text",
    "generator",
    "simple",
    "mini",
    "tiny",
    "lite",
    "basic",
    "hello",
    "echo",
    "demo",
    "example",
    "starter",
    "template",
    "clipboard",
    "timer",
    "counter",
    "converter",
    "calculator",
]

# Zoo animal classification based on tool count and complexity
ZOO_ANIMALS = {
    # Jumbos - Heavy/Complex MCPs ( Elephant,  Hippo,  Rhino)
    "jumbo": {
        "emoji": "",
        "label": "Jumbo",
        "description": "Heavy MCP - DB, virtualization, video processing",
        "min_tools": 20,
    },
    # Large - Substantial MCPs ( Lion,  Bear,  Giraffe)
    "large": {
        "emoji": "",
        "label": "Large",
        "description": "Substantial MCP with many features",
        "min_tools": 10,
    },
    # Medium - Standard MCPs ( Fox,  Wolf,  Deer)
    "medium": {
        "emoji": "",
        "label": "Medium",
        "description": "Standard MCP with moderate complexity",
        "min_tools": 5,
    },
    # Small - Lightweight MCPs ( Rabbit,  Raccoon,  Badger)
    "small": {
        "emoji": "",
        "label": "Small",
        "description": "Lightweight MCP with focused purpose",
        "min_tools": 2,
    },
    # Chipmunk - Mini MCPs ( Chipmunk,  Hamster,  Mouse)
    "chipmunk": {
        "emoji": "",
        "label": "Chipmunk",
        "description": "Mini MCP - simple, single-purpose tool",
        "min_tools": 0,
    },
}


@tool(
    name="analyze_runts",
    description="""Analyze MCP repositories to identify "runts" needing SOTA upgrades.

    Scans a directory for MCP repositories and evaluates each against SOTA criteria:
    - FastMCP version (< 3.4.2 = runt)
    - Tool count (> 20 without portmanteau = runt)
    - 40+ 2026 fleet standards from mcp-central-docs

    Returns categorized list of repos with specific upgrade recommendations.
    Results are cached to avoid re-scanning on every request.""",
    category=ToolCategory.DISCOVERY,
    tags=["runt", "analyzer", "sota", "upgrade"],
    estimated_runtime="2-10s",
)
def analyze_runts_sync(
    scan_path: str | None = None,
    max_depth: int = 1,
    include_sota: bool = True,
    format: str = "json",
    use_cache: bool = True,
    deep_scan: bool = False,
):
    """Synchronous wrapper for analyze_runts."""
    import asyncio

    return asyncio.run(analyze_runts(scan_path, max_depth, include_sota, format, use_cache, deep_scan=deep_scan))


async def analyze_runts(
    scan_path: str | None = None,
    max_depth: int = 1,
    include_sota: bool = True,
    format: str = "json",
    use_cache: bool = True,
    cache_ttl: int = 3600,
    deep_scan: bool = False,
) -> dict[str, Any] | str:
    """
    Analyze MCP repositories to identify runts needing upgrades.

    Args:
        scan_path: Directory containing MCP repositories (default: from REPOS_DIR env var or platform default)
        max_depth: How deep to scan for repos (default: 1 = direct children only)
        include_sota: Whether to include SOTA repos in results (default: True)
        format: Output format - "json" or "markdown" (default: "json")
        use_cache: Whether to use cached results (default: True)
        cache_ttl: Cache time-to-live in seconds (default: 3600 = 1 hour)

    Returns:
        Dictionary with runts, sota repos, and summary statistics, or markdown string if format="markdown"
    """
    # Use default scan_path if not provided
    if scan_path is None:
        from meta_mcp.core.config import DEFAULT_REPOS_PATH

        scan_path = DEFAULT_REPOS_PATH

    # Check cache first
    if use_cache:
        cached = get_cached_scan(scan_path, max_depth, cache_ttl)
        if cached:
            if format == "markdown":
                return format_scan_result_markdown(cached)
            return cached

    runts: list[dict[str, Any]] = []
    sota_repos: list[dict[str, Any]] = []

    path = Path(scan_path).expanduser().resolve()
    if not path.exists():
        error_result = {
            "success": False,
            "message": "Operation failed",
            "error": f"Path does not exist: {scan_path}",
            "timestamp": time.time(),
        }
        if format == "markdown":
            return f"# Scan Failed\n\n**Error:** {error_result['error']}\n"
        return error_result

    import asyncio

    for item in path.iterdir():
        if not item.is_dir() or item.name.startswith("."):
            continue

        # Small delay to reduce terminal spam and CPU usage
        await asyncio.sleep(0.1)  # 100ms delay between repos

        repo_info = _analyze_repo(item, deep_scan=deep_scan)
        if repo_info:
            if repo_info.get("is_runt"):
                runts.append(repo_info)
            elif include_sota:
                sota_repos.append(repo_info)

    # Sort runts by severity (most issues first)
    runts.sort(key=lambda x: len(x.get("runt_reasons", [])), reverse=True)
    sota_repos.sort(key=lambda x: x.get("name", ""))

    result = {
        "success": True,
        "summary": {
            "total_mcp_repos": len(runts) + len(sota_repos),
            "runts": len(runts),
            "sota": len(sota_repos),
            "runt_threshold": f"FastMCP < {FASTMCP_RUNT_THRESHOLD}",
            "portmanteau_threshold": f"> {TOOL_PORTMANTEAU_THRESHOLD} tools",
            "sota_version": FASTMCP_LATEST,
        },
        "runts": runts,
        "sota_repos": sota_repos if include_sota else [],
        "scan_path": scan_path,
        "timestamp": time.time(),
    }

    # Cache the result
    if use_cache:
        cache_scan_result(scan_path, max_depth, result)

    try:
        from meta_mcp.services.analysis_depot_service import AnalysisDepotService

        depot = AnalysisDepotService()
        depot.persist_run("fleet_runts", result, scan_path=scan_path)
    except Exception:
        pass

    # Return in requested format
    if format == "markdown":
        return format_scan_result_markdown(result)

    return result


@tool(
    name="get_repo_status",
    description="""Get detailed SOTA status for a specific MCP repository.

    Analyzes a single repo and returns comprehensive status including:
    - FastMCP version and upgrade path
    - Tool count and portmanteau status
    - CI/CD quality assessment
    - Specific upgrade recommendations
    - Detailed repository structure, dependencies, tools, and configuration
    - All information needed for AI to answer questions about the repo without re-analysis

    Results are cached to avoid re-scanning on every request.""",
    category=ToolCategory.DISCOVERY,
    tags=["repo", "status", "sota"],
    estimated_runtime="2-5s",
)
async def get_repo_status(
    repo_path: str,
    format: str = "json",
    use_cache: bool = True,
    cache_ttl: int = 3600,
    deep_scan: bool = False,
) -> dict[str, Any] | str:
    """
    Get detailed SOTA status for a specific repository.

    Args:
        repo_path: Path to the repository
        format: Output format - "json" or "markdown" (default: "json")
        use_cache: Whether to use cached results (default: True)
        cache_ttl: Cache time-to-live in seconds (default: 3600 = 1 hour)

    Returns:
        Detailed repository status and recommendations, or markdown string if format="markdown"
    """
    # Check cache first
    if use_cache:
        cached = get_cached_repo_status(repo_path, cache_ttl)
        if cached:
            if format == "markdown":
                return format_repo_status_markdown(cached)
            return cached

    path = Path(repo_path).expanduser().resolve()
    if not path.exists():
        error_result = {
            "success": False,
            "message": "Operation failed",
            "error": f"Repository not found: {repo_path}",
            "timestamp": time.time(),
        }
        if format == "markdown":
            return f"# Repository Status Failed\n\n**Error:** {error_result['error']}\n"
        return error_result

    repo_info = _analyze_repo(path, deep_scan=deep_scan)
    if not repo_info:
        error_result = {
            "success": False,
            "message": "Operation failed",
            "error": f"Not an MCP repository: {repo_path}",
            "timestamp": time.time(),
        }
        if format == "markdown":
            return f"# Repository Status Failed\n\n**Error:** {error_result['error']}\n"
        return error_result

    # Add more detailed analysis
    repo_info["success"] = True
    repo_info["sota_score"] = _calculate_sota_score(repo_info)
    repo_info["upgrade_priority"] = _determine_priority(repo_info)
    repo_info["timestamp"] = time.time()

    # Add basic repository information
    try:
        repo_info["details"] = {
            "name": path.name,
            "path": str(path),
            "exists": path.exists(),
            "is_directory": path.is_dir() if path.exists() else False,
        }
    except Exception as e:
        logger.warning(f"Failed to collect basic repo info: {e}")
        repo_info["details"] = None

    # Cache the result
    if use_cache:
        cache_repo_status(repo_path, repo_info)

    try:
        from meta_mcp.services.analysis_depot_service import AnalysisDepotService

        depot = AnalysisDepotService()
        depot.persist_run(
            "repo_status",
            repo_info,
            scan_path=repo_path,
            repo_name=repo_info.get("name") or path.name,
        )
    except Exception:
        pass

    # Return in requested format
    if format == "markdown":
        return format_repo_status_markdown(repo_info)

    return repo_info


# Path parts to skip when walking repos (belt-and-suspenders for .venv, node_modules)
_IGNORE_PATH_PARTS: frozenset[str] = frozenset({".venv", "venv", "node_modules", "__pycache__", ".git"})

# Directories to skip when walking repos (prevents hanging on node_modules, .venv, etc.)
_IGNORE_DIRS: frozenset[str] = frozenset(
    {
        ".git",
        "__pycache__",
        ".venv",
        "venv",
        "node_modules",
        "bower_components",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        "target",
        "build",
        "dist",
        ".next",
        ".nuxt",
        ".svelte-kit",
    }
)


def _walk_py_files(repo_path: Path):
    """Yield Python files in repo_path, skipping ignored directories."""
    for root, dirs, files in os.walk(str(repo_path), topdown=True):
        dirs[:] = [d for d in dirs if d not in _IGNORE_DIRS and not d.startswith(".")]
        for fname in files:
            if fname.endswith(".py"):
                yield Path(root) / fname


def _analyze_repo(repo_path: Path, deep_scan: bool = False) -> dict[str, Any] | None:
    """Analyze a repository for MCP status."""
    info = {
        "name": repo_path.name,
        "path": str(repo_path),
        "fastmcp_version": None,
        "tool_count": 0,
        "has_portmanteau": False,
        "has_ci": False,
        "ci_workflows": 0,
        "has_mcpb": False,
        "has_help_tool": False,
        "has_status_tool": False,
        "has_proper_docstrings": False,
        "has_ruff": False,
        "has_tests": False,
        "has_unit_tests": False,
        "has_integration_tests": False,
        "has_pytest_config": False,
        "has_coverage_config": False,
        "test_file_count": 0,
        "has_proper_logging": False,
        "has_good_error_handling": True,  # Assume good until proven bad
        "print_statement_count": 0,
        "bare_except_count": 0,
        "lazy_error_msg_count": 0,
        "is_runt": False,
        "runt_reasons": [],
        "recommendations": [],
        "status_emoji": "SUCCESS",
        "status_color": "green",
        "status_label": "SOTA",
        "zoo_class": "unknown",
        "zoo_animal": "",  # Default: hedgehog (unknown size)
        "loc": {
            "total": 0,
            "python": 0,
            "typescript": 0,
            "powershell": 0,
            "markdown": 0,
        },
        "dependencies": [],
        "tools_metadata": [],
        "entry_points": {},
        "missing_critical_files": [],
        "has_toml_lint": False,
        "has_yaml_lint": False,
        "deep_scan_results": None,
    }

    # SOTA Section 8: Critical File Checks
    for crit_file in SOTA_CRITICAL_FILES:
        if not (repo_path / crit_file).exists():
            info["missing_critical_files"].append(crit_file)
            info["is_runt"] = True
            info["runt_reasons"].append(f"Missing critical file: {crit_file}")
            info["recommendations"].append(f"Restore missing SOTA file: {crit_file}")

    # Configuration Linting Presence
    # (Checking for config or evidence in CI/toml)
    if (repo_path / "ruff.toml").exists() or (repo_path / ".ruff.toml").exists():
        info["has_toml_lint"] = True

    # Check for yaml-lint or similar in CI
    github_workflows = repo_path / ".github" / "workflows"
    if github_workflows.exists():
        for wf in github_workflows.glob("*.y*ml"):
            try:
                wf_content = wf.read_text(encoding="utf-8").lower()
                if "yamllint" in wf_content or "action-yamllint" in wf_content:
                    info["has_yaml_lint"] = True
                    break
            except Exception:
                pass

    # Check for requirements.txt or pyproject.toml
    req_file = repo_path / "requirements.txt"
    pyproject_file = repo_path / "pyproject.toml"

    fastmcp_version = None

    # Extract FastMCP version and other config
    for config_file in [req_file, pyproject_file]:
        if config_file.exists():
            try:
                content = config_file.read_text(encoding="utf-8")

                if config_file.name == "requirements.txt":
                    # Simple requirements.txt parsing
                    for line in content.splitlines():
                        line = line.strip()
                        if line and not line.startswith("#"):
                            info["dependencies"].append(line)

                    # FastMCP version from requirements.txt (raw text)
                    if not fastmcp_version:
                        match = re.search(r"fastmcp[>=<>=!]*(\d+\.\d+\.?\d*)", content, re.IGNORECASE)
                        if match:
                            fastmcp_version = match.group(1)

                elif config_file.name == "pyproject.toml":
                    # Proper TOML parsing
                    config_data = tomli.loads(content)
                    project = config_data.get("project", {})

                    # Project dependencies
                    deps = project.get("dependencies", [])
                    if isinstance(deps, list):
                        info["dependencies"].extend(deps)
                        # FastMCP version from parsed deps (ignores description text)
                        if not fastmcp_version:
                            for dep in deps:
                                dep_stripped = dep.strip().lower()
                                if dep_stripped.startswith("fastmcp"):
                                    dep_clean = re.sub(r"^fastmcp[>=<~!^=\s]*", "", dep_stripped)
                                    ver_match = re.search(r"(\d+\.\d+\.?\d*)", dep_clean)
                                    if ver_match:
                                        fastmcp_version = ver_match.group(1)
                                        break

                    # Optional dependencies (dev, etc)
                    opt_deps = project.get("optional-dependencies", {})
                    for _group, group_deps in opt_deps.items():
                        if isinstance(group_deps, list):
                            info["dependencies"].extend(group_deps)

                    # Entry points
                    scripts = project.get("scripts", {})
                    if scripts:
                        info["entry_points"].update(scripts)

                    # Build system requirements
                    build_system = config_data.get("build-system", {})
                    build_reqs = build_system.get("requires", [])
                    if build_reqs:
                        info["dependencies"].extend(build_reqs)

            except Exception as e:
                logger.debug(f"Failed to parse {config_file}: {e}")
                pass

    if not fastmcp_version:
        return None  # Not an MCP repo

    info["fastmcp_version"] = fastmcp_version

    # Check for portmanteau tools  two methods:
    # 1. Directory-based: portmanteau/ subdirectory with .py files
    # 2. Code-pattern-based: tool function signature contains operation: Literal[...]
    portmanteau_paths = [
        repo_path / "src" / f"{repo_path.name.replace('-', '_')}" / "tools" / "portmanteau",
        repo_path / "src" / f"{repo_path.name.replace('-', '_')}" / "portmanteau",
        repo_path / f"{repo_path.name.replace('-', '_')}" / "portmanteau",
        repo_path / "portmanteau",
    ]
    info["has_portmanteau"] = False
    for p in portmanteau_paths:
        if p.exists() and any(p.glob("*.py")):
            info["has_portmanteau"] = True
            break

    # Check for DXT packaging
    for mcpb_file in MCPB_FILES:
        if (repo_path / mcpb_file).exists():
            info["has_mcpb"] = True
            break

    # Count tools, LoC and check for help/status + docstrings
    # Broad tool detection: any @*.tool( decorator (handles app, mcp, router, server, etc.)
    # plus programmatic registration patterns
    tool_decorator_pattern = r"@\w+\.tool\("
    tool_api_patterns = [
        r"\.(?:add_tool|register_tool|add_mcp_tool)\s*\(",
        r"mcp\s*\.\s*add_tool\s*\(",
    ]
    tool_count = 0
    proper_docstrings = 0
    print_count = 0
    bare_except_count = 0
    lazy_error_count = 0
    has_logging = False

    extensions_map = {
        ".py": "python",
        ".ts": "typescript",
        ".js": "typescript",
        ".ps1": "powershell",
        ".md": "markdown",
    }

    # Recursive scan with directory pruning (os.walk avoids rglob hanging on node_modules)
    for root, dirs, files in os.walk(str(repo_path), topdown=True):
        dirs[:] = [d for d in dirs if d not in _IGNORE_DIRS and not d.startswith(".")]
        # Belt-and-suspenders: skip files whose full path contains ignored dir parts
        if any(ig in str(root) for ig in _IGNORE_PATH_PARTS):
            continue
        for fname in files:
            item = Path(root) / fname
            ext = item.suffix.lower()
            if ext in extensions_map:
                try:
                    content = item.read_text(encoding="utf-8")
                    lines = content.splitlines()
                    line_count = len(lines)

                    category = extensions_map[ext]
                    info["loc"][category] += line_count
                    info["loc"]["total"] += line_count

                    # Only look for tools and specific metadata in source files
                    if ext == ".py":
                        item_str = str(item)
                        item_lower = item_str.lower()
                        is_test = (
                            "/tests/" in item_lower
                            or "\\tests\\" in item_lower
                            or "/test/" in item_lower
                            or "\\test\\" in item_lower
                            or "/scripts/" in item_lower
                            or "\\scripts\\" in item_lower
                            or item_str.endswith("_test.py")
                        )

                        # Tool metadata discovery (only in non-test files)
                        if not is_test:
                            # Method 1: Find @*.tool() decorator followed by def name()
                            # Handles @app.tool, @mcp.tool, @router.tool, @server.tool, etc.
                            for match in re.finditer(
                                tool_decorator_pattern + r".*?\n\s*(?:async\s+)?def\s+(\w+)",
                                content,
                                re.DOTALL,
                            ):
                                tool_name = match.group(1)
                                tool_count += 1

                                # Check if this tool uses portmanteau pattern (operation: Literal[...])
                                # Look between the def line and the first docstring/comments
                                def_sig = content[match.start() : match.end() + 200]
                                if not info["has_portmanteau"] and re.search(r"operation\s*:\s*Literal", def_sig):
                                    info["has_portmanteau"] = True

                                # Check for docstring for THIS specific tool
                                # We look at the body of the function right after the match
                                start_pos = match.end()
                                # Find the end of the def line
                                def_end = content.find(":", start_pos)
                                if def_end != -1:
                                    # Check if next non-empty line starts with triple quotes
                                    after_def = content[def_end + 1 :].strip()
                                    has_docstring = after_def.startswith('"""') or after_def.startswith("'''")

                                    # Deep check for SOTA docstring (Args/Returns)
                                    is_sota_doc = False
                                    if has_docstring:
                                        # Find the end of docstring
                                        quote_type = after_def[:3]
                                        doc_end = after_def.find(quote_type, 3)
                                        if doc_end != -1:
                                            doc_text = after_def[3:doc_end]
                                            if any(
                                                kw in doc_text
                                                for kw in [
                                                    "Args:",
                                                    "Returns:",
                                                    "Example:",
                                                    "PORTMANTEAU",
                                                ]
                                            ):
                                                is_sota_doc = True

                                    info["tools_metadata"].append(
                                        {
                                            "name": tool_name,
                                            "file": str(item.relative_to(repo_path)),
                                            "has_docstring": has_docstring,
                                            "is_sota_doc": is_sota_doc,
                                        }
                                    )
                                    if is_sota_doc:
                                        proper_docstrings += 1

                            # Method 2: Programmatic tool registration (mcp.add_tool, register_tool, etc.)
                            for api_pattern in tool_api_patterns:
                                for api_match in re.finditer(
                                    api_pattern + r'(?:["\'](\w+)["\']\s*,?\s*|(\w+)\s*[=:])',
                                    content,
                                ):
                                    name = api_match.group(1) or api_match.group(2) or "unknown_tool"
                                    tool_count += 1
                                    info["tools_metadata"].append(
                                        {
                                            "name": name,
                                            "file": str(item.relative_to(repo_path)),
                                            "has_docstring": False,
                                            "is_sota_doc": False,
                                            "registration": "programmatic",
                                        }
                                    )

                            # Check for help tool
                            if not info["has_help_tool"]:
                                if re.search(
                                    r'(def\s+help|def\s+get_help|"help"|\'help\')\s*\(',
                                    content,
                                    re.IGNORECASE,
                                ):
                                    info["has_help_tool"] = True

                            # Check for status tool
                            if not info["has_status_tool"]:
                                if re.search(
                                    r'(def\s+status|def\s+get_status|"status"|\'status\')\s*\(',
                                    content,
                                    re.IGNORECASE,
                                ):
                                    info["has_status_tool"] = True

                            # --- Logging, Print and Error Handling Checks ---
                            content_lower = content.lower()

                            # Check for logging setup (only need to find it once)
                            if not has_logging:
                                for pattern in LOGGING_PATTERNS:
                                    if re.search(pattern, content):
                                        has_logging = True
                                        break

                            # Check for print statements in non-test Python files
                            if not is_test:
                                for pattern in PY_BAD_STDOUT_PATTERNS:
                                    matches = re.findall(pattern, content, re.MULTILINE)
                                    print_count += len(matches)

                            # Check for bare except Exception:, NOT except Exception: (separate count)
                            for pattern in BARE_EXCEPT_PATTERNS:
                                matches = re.findall(pattern, content)
                                bare_except_count += len(matches)

                            # Check for lazy/non-informative error messages
                            if not is_test:
                                for pattern in LAZY_ERROR_MESSAGES:
                                    matches = re.findall(pattern, content_lower, re.IGNORECASE)
                                    lazy_error_count += len(matches)
                except Exception as e:
                    logger.debug(f"Failed to scan {item}: {e}")
                    pass

    # Count console.log in JS/TS files (separate from Python print count)
    console_log_count = 0
    for root, dirs, files in os.walk(str(repo_path), topdown=True):
        dirs[:] = [d for d in dirs if d not in _IGNORE_DIRS and not d.startswith(".")]
        if any(ig in str(root) for ig in _IGNORE_PATH_PARTS):
            continue
        for fname in files:
            if not fname.endswith((".ts", ".tsx", ".js", ".jsx")):
                continue
            try:
                content = (Path(root) / fname).read_text(encoding="utf-8")
                for pattern in JS_BAD_STDOUT_PATTERNS:
                    matches = re.findall(pattern, content)
                    console_log_count += len(matches)
            except Exception:
                pass

    info["has_proper_logging"] = has_logging
    info["print_statement_count"] = print_count
    info["console_log_count"] = console_log_count
    info["bare_except_count"] = bare_except_count
    info["lazy_error_msg_count"] = lazy_error_count
    info["has_good_error_handling"] = bare_except_count < 3 and lazy_error_count < 5

    info["tool_count"] = tool_count

    # Post-scan: check registered tool names for portmanteau help/status
    for tm in info.get("tools_metadata", []):
        tn = tm.get("name", "")
        if "help" in tn.lower():
            info["has_help_tool"] = True
        if "status" in tn.lower():
            info["has_status_tool"] = True
    # Consider proper docstrings if >50% of tools have them
    info["has_proper_docstrings"] = proper_docstrings > 0 and (
        tool_count == 0 or proper_docstrings / max(tool_count, 1) > 0.5
    )

    # Check CI
    ci_dir = repo_path / ".github" / "workflows"
    if ci_dir.exists():
        info["has_ci"] = True
        info["ci_workflows"] = len(list(ci_dir.glob("*.yml")))

        # Check for ruff in CI
        for workflow in ci_dir.glob("*.yml"):
            try:
                ci_content = workflow.read_text(encoding="utf-8").lower()
                if "ruff" in ci_content:
                    info["has_ruff"] = True
                    break
            except Exception:
                pass

    # Check for ruff config files
    if not info["has_ruff"]:
        for ruff_file in RUFF_CONFIG_FILES:
            if (repo_path / ruff_file).exists():
                info["has_ruff"] = True
                break

        # Check pyproject.toml for [tool.ruff]
        if not info["has_ruff"] and pyproject_file.exists():
            try:
                pyproject_content = pyproject_file.read_text(encoding="utf-8")
                if "[tool.ruff]" in pyproject_content:
                    info["has_ruff"] = True
            except Exception:
                pass

    # Check test harness
    test_file_count = 0
    for test_dir_name in TEST_DIRS:
        test_dir = repo_path / test_dir_name
        if test_dir.exists():
            info["has_tests"] = True

            # Check for unit tests
            unit_dir = test_dir / "unit"
            if unit_dir.exists() and any(unit_dir.glob("test_*.py")):
                info["has_unit_tests"] = True

            # Check for integration tests
            integration_dir = test_dir / "integration"
            if integration_dir.exists() and any(integration_dir.glob("test_*.py")):
                info["has_integration_tests"] = True

            # Count test files
            test_file_count += len(list(test_dir.rglob("test_*.py")))
            test_file_count += len(list(test_dir.rglob("*_test.py")))

    info["test_file_count"] = test_file_count

    # Check for pytest configuration
    pytest_ini = repo_path / "pytest.ini"
    pyproject_pytest = False
    if pyproject_file.exists():
        try:
            pyproject_content = pyproject_file.read_text(encoding="utf-8")
            if "[tool.pytest" in pyproject_content:
                pyproject_pytest = True
        except Exception:
            pass

    if pytest_ini.exists() or pyproject_pytest:
        info["has_pytest_config"] = True

    # Check for coverage configuration
    coveragerc = repo_path / ".coveragerc"
    pyproject_coverage = False
    if pyproject_file.exists():
        try:
            pyproject_content = pyproject_file.read_text(encoding="utf-8")
            if "[tool.coverage" in pyproject_content:
                pyproject_coverage = True
        except Exception:
            pass

    if coveragerc.exists() or pyproject_coverage:
        info["has_coverage_config"] = True

    # =====================================================================
    # 2026 Fleet Standard Data Collection
    # =====================================================================
    _collect_fleet_2026_info(repo_path, pyproject_file, info)

    # FastMCP 3.4.2 Feature Validation
    pyproject_content = ""
    if pyproject_file.exists():
        try:
            pyproject_content = pyproject_file.read_text(encoding="utf-8")
        except Exception:
            pyproject_content = ""

    # Check for FastMCP 3.4.2 specific features
    fastmcp_features = _check_fastmcp_342_features(repo_path, pyproject_content)
    info.update(fastmcp_features)

    # Check docstring standards
    docstring_analysis = _check_docstring_standards(repo_path)
    info.update(docstring_analysis)

    # Check testing scaffold
    testing_analysis = _check_testing_scaffold(repo_path)
    info.update(testing_analysis)

    # Check CI/CD implementation
    cicd_analysis = _check_cicd_implementation(repo_path)
    info.update(cicd_analysis)

    # Check Zed extension support
    zed_analysis = _check_zed_extension_support(repo_path)
    info.update(zed_analysis)

    # Collect 2026 fleet-standard data points before rule evaluation
    _collect_fleet_2026_info(repo_path, pyproject_file, info)

    # Evaluate using rule-based system
    _evaluate_runt_status(info, fastmcp_version)

    # NEW: Actively run tools if deep_scan is requested
    if deep_scan:
        info["deep_scan_results"] = _run_active_tools(repo_path)
        if not info["deep_scan_results"]["ruff_pass"]:
            info["is_runt"] = True
            info["runt_reasons"].append(
                f"Fails active Ruff linting ({info['deep_scan_results']['ruff_errors']} errors)"
            )
            info["recommendations"].append("Fix all Ruff errors (0 errors mandatory for CI/CD and Release)")
            info["status_color"] = "red"
        if not info["deep_scan_results"]["tests_pass"]:
            info["is_runt"] = True
            info["runt_reasons"].append("Fails active test execution")
            info["status_color"] = "red"

    return info


def _run_active_tools(repo_path: Path) -> dict[str, Any]:
    """Actively execute Ruff and tests on the repository."""
    import subprocess

    results = {
        "ruff_pass": True,
        "ruff_errors": 0,
        "tests_pass": True,
        "test_summary": "",
    }

    # Run Ruff
    try:
        ruff_path = shutil.which("ruff") or "ruff"
        ruff_proc = subprocess.run(
            [ruff_path, "check", "."],
            cwd=str(repo_path),
            capture_output=True,
            text=True,
            check=False,
        )
        if ruff_proc.returncode != 0:
            results["ruff_pass"] = False
            # Count errors (simplified count from output)
            results["ruff_errors"] = len(ruff_proc.stdout.splitlines())
    except Exception as e:
        results["ruff_pass"] = False
        results["ruff_error_msg"] = str(e)

    # Run Tests (Master script or pytest)
    pwsh_path = shutil.which("powershell") or shutil.which("pwsh") or "powershell"
    test_commands = [
        [pwsh_path, "-ExecutionPolicy", "Bypass", "-File", "./run_tests.ps1"],
        ["pytest"],
        ["python", "-m", "pytest"],
    ]

    for cmd in test_commands:
        try:
            # Check if file exists for binary-based commands
            if cmd[0] == "powershell" and not (repo_path / "run_tests.ps1").exists():
                continue

            test_proc = subprocess.run(cmd, cwd=str(repo_path), capture_output=True, text=True, check=False)
            if test_proc.returncode == 0:
                results["tests_pass"] = True
                results["test_summary"] = "Tests passed successfully"
                break
            else:
                results["tests_pass"] = False
                results["test_summary"] = test_proc.stdout[-500:]  # Last 500 chars
        except Exception as e:
            results["tests_pass"] = False
            results["test_summary"] = f"Test execution failed: {e!s}"

    return results


def _evaluate_runt_status(info: dict[str, Any], fastmcp_version: str) -> None:
    """Evaluate if repo is a runt using rule-based system."""
    # Ensure fastmcp_version is in info for rule evaluation
    if fastmcp_version:
        info["fastmcp_version"] = fastmcp_version

    # Evaluate all rules
    rule_result = evaluate_rules(info)

    # Update info with rule evaluation results
    info["is_runt"] = rule_result["is_runt"]
    info["runt_reasons"] = rule_result["runt_reasons"]
    info["recommendations"] = rule_result["recommendations"]

    # Set status emoji, color, and label based on severity
    violation_count = rule_result["violation_count"]
    critical_count = rule_result["critical_count"]

    if info["is_runt"]:
        # RED - Real runts
        info["status_color"] = "red"
        if critical_count >= 5:
            info["status_emoji"] = ""
            info["status_label"] = "Critical Runt"
        elif critical_count >= 3:
            info["status_emoji"] = ""
            info["status_label"] = "Runt"
        else:
            info["status_emoji"] = ""
            info["status_label"] = "Minor Runt"
    else:
        if violation_count > 0:
            # ORANGE - Improvable (has warnings but not runt)
            info["status_emoji"] = "WARNING"
            info["status_color"] = "orange"
            info["status_label"] = "Needs Improvement"
        else:
            # GREEN - Perfect
            info["status_emoji"] = "SUCCESS"
            info["status_color"] = "green"
            info["status_label"] = "SOTA"

    # Store rule evaluation details for debugging
    info["_rule_evaluation"] = {
        "violations": rule_result["violations"],
        "critical_violations": rule_result["critical_violations"],
        "score_deduction": rule_result["score_deduction"],
    }

    # Build human-readable remediation todo list
    info["remediation_todo"] = _build_remediation_todo(rule_result["violations"])

    # Add zoo classification
    _classify_zoo_animal(info)


def _classify_zoo_animal(info: dict[str, Any]) -> None:
    """Classify repo into MCP Zoo animal size category."""
    name_lower = info.get("name", "").lower()
    tool_count = info.get("tool_count", 0)

    # Check for jumbo indicators in name
    is_jumbo_type = any(ind in name_lower for ind in JUMBO_INDICATORS)

    # Check for chipmunk indicators in name
    is_chipmunk_type = any(ind in name_lower for ind in CHIPMUNK_INDICATORS)

    # Determine class based on indicators and tool count
    if is_jumbo_type or tool_count >= 20:
        info["zoo_class"] = "jumbo"
        info["zoo_animal"] = ""
    elif is_chipmunk_type and tool_count <= 3:
        info["zoo_class"] = "chipmunk"
        info["zoo_animal"] = ""
    elif tool_count >= 10:
        info["zoo_class"] = "large"
        info["zoo_animal"] = ""
    elif tool_count >= 5:
        info["zoo_class"] = "medium"
        info["zoo_animal"] = ""
    elif tool_count >= 2:
        info["zoo_class"] = "small"
        info["zoo_animal"] = ""
    else:
        info["zoo_class"] = "chipmunk"
        info["zoo_animal"] = ""


def _calculate_sota_score(info: dict[str, Any]) -> int:
    """Calculate SOTA compliance score (0-100) using rule-based system."""
    return calculate_sota_score(info, base_score=100)


def _check_fastmcp_342_features(repo_path: Path, pyproject_content: str) -> dict[str, Any]:
    """Check for FastMCP 3.4.2+ features: ctx.sample sampling, dialogic returns, prompts, resources."""
    features = {
        "has_sampling_support": False,
        "has_conversational_returns": False,
        "sampling_implementation": None,
        "conversational_implementation": None,
    }

    # Sampling support: look for ctx.sample() usage (FastMCP 3.x API)
    try:
        for py_file in _walk_py_files(repo_path):
            if py_file.is_file():
                content = py_file.read_text(encoding="utf-8")

                # FastMCP 3.x sampling: ctx.sample(...) or from fastmcp import Context
                if re.search(r"ctx\.sample\s*\(", content):
                    features["has_sampling_support"] = True
                    features["sampling_implementation"] = str(py_file.relative_to(repo_path))

                # 2026 dialogic return pattern: dict with "message" + "data" keys
                message_matches = list(re.finditer(r'(?<!["\w])["\']message["\']\s*:', content))
                data_matches = list(re.finditer(r'(?<!["\w])["\']data["\']\s*:', content))
                if message_matches and data_matches:
                    for mm in message_matches:
                        for dm in data_matches:
                            if abs(mm.start() - dm.start()) < 500:
                                if not features["has_conversational_returns"]:
                                    features["has_conversational_returns"] = True
                                    features["conversational_implementation"] = str(py_file.relative_to(repo_path))
                                break
                        if features["has_conversational_returns"]:
                            break

    except Exception:
        pass

    return features


def _check_docstring_standards(repo_path: Path) -> dict[str, Any]:
    """Check if docstrings meet current FastMCP standards."""
    docstring_info = {
        "has_proper_docstrings": False,
        "docstring_coverage": 0,
        "tools_with_args": 0,
        "tools_with_returns": 0,
        "tools_with_examples": 0,
        "ascii_only_docstrings": True,
        "unicode_issues_found": [],
    }

    tool_count = 0
    tools_with_proper_docs = 0

    try:
        for py_file in _walk_py_files(repo_path):
            content = py_file.read_text(encoding="utf-8")

            # Check for Unicode characters in docstrings
            unicode_matches = re.findall(r'["\'][\U0001F000-\U0001F999][^"\']*["\']', content)
            if unicode_matches:
                docstring_info["unicode_issues_found"].extend([f"{py_file.name}: {match}" for match in unicode_matches])
                docstring_info["ascii_only_docstrings"] = False

            # Find tool functions
            tool_matches = re.finditer(r"@tool.*?\n\s*(?:async\s+)?def\s+(\w+)", content, re.DOTALL)

            for match in tool_matches:
                tool_count += 1

                # Extract docstring for this tool
                start_pos = match.end()
                def_end = content.find(":", start_pos)
                if def_end != -1:
                    after_def = content[def_end + 1 :].strip()
                    if after_def.startswith('"""') or after_def.startswith("'''"):
                        quote_type = after_def[:3]
                        doc_end = after_def.find(quote_type, 3)
                        if doc_end != -1:
                            doc_text = after_def[3:doc_end]
                            tools_with_proper_docs += 1

                            # Check docstring components (2026 standards)
                            if "## Return Format" in doc_text or "## Return" in doc_text:
                                docstring_info["tools_with_returns"] += 1
                            if "## Examples" in doc_text or "## Example" in doc_text:
                                docstring_info["tools_with_examples"] += 1

        if tool_count > 0:
            docstring_info["docstring_coverage"] = (tools_with_proper_docs / tool_count) * 100
            docstring_info["has_proper_docstrings"] = docstring_info["docstring_coverage"] >= 80

    except Exception:
        pass

    return docstring_info


def _check_testing_scaffold(repo_path: Path) -> dict[str, Any]:
    """Check if proper testing scaffold is in place."""
    testing_info = {
        "has_test_directory": False,
        "has_pytest_config": False,
        "has_coverage_config": False,
        "has_unit_tests": False,
        "has_integration_tests": False,
        "test_file_count": 0,
        "has_ci_cd": False,
        "ci_cd_platform": None,
    }

    # Check for test directories
    for test_dir in ["tests", "test"]:
        test_path = repo_path / test_dir
        if test_path.exists() and test_path.is_dir():
            testing_info["has_test_directory"] = True

            # Check for specific test types
            unit_dir = test_path / "unit"
            integration_dir = test_path / "integration"

            if unit_dir.exists():
                testing_info["has_unit_tests"] = True
            if integration_dir.exists():
                testing_info["has_integration_tests"] = True

            # Count test files
            test_files = list(test_path.rglob("test_*.py")) + list(test_path.rglob("*_test.py"))
            testing_info["test_file_count"] = len(test_files)

    # Check for pytest configuration
    pytest_ini = repo_path / "pytest.ini"
    pyproject_file = repo_path / "pyproject.toml"

    if pytest_ini.exists():
        testing_info["has_pytest_config"] = True

    if pyproject_file.exists():
        try:
            pyproject_content = pyproject_file.read_text(encoding="utf-8")
            if "[tool.pytest" in pyproject_content or "[pytest" in pyproject_content:
                testing_info["has_pytest_config"] = True
        except Exception:
            pass

    # Check for coverage configuration
    coveragerc = repo_path / ".coveragerc"
    if pyproject_file.exists():
        try:
            pyproject_content = pyproject_file.read_text(encoding="utf-8")
            if "[tool.coverage" in pyproject_content:
                testing_info["has_coverage_config"] = True
        except Exception:
            pass

    if coveragerc.exists():
        testing_info["has_coverage_config"] = True

    return testing_info


def _check_cicd_implementation(repo_path: Path) -> dict[str, Any]:
    """Check for CI/CD implementation."""
    cicd_info = {
        "has_ci_cd": False,
        "ci_cd_platform": None,
        "has_github_actions": False,
        "has_gitlab_ci": False,
        "has_azure_pipelines": False,
        "workflow_files": [],
    }

    # Check for GitHub Actions
    github_dir = repo_path / ".github" / "workflows"
    if github_dir.exists() and github_dir.is_dir():
        cicd_info["has_ci_cd"] = True
        cicd_info["ci_cd_platform"] = "github_actions"
        cicd_info["has_github_actions"] = True
        workflow_files = list(github_dir.glob("*.yml")) + list(github_dir.glob("*.yaml"))
        cicd_info["workflow_files"] = [f.name for f in workflow_files]

    # Check for GitLab CI
    gitlab_file = repo_path / ".gitlab-ci.yml"
    if gitlab_file.exists():
        cicd_info["has_ci_cd"] = True
        if not cicd_info["ci_cd_platform"]:
            cicd_info["ci_cd_platform"] = "gitlab_ci"
        cicd_info["has_gitlab_ci"] = True

    # Check for Azure Pipelines
    azure_file = repo_path / ".azure" / "pipelines"
    if azure_file.exists() and azure_file.is_dir():
        cicd_info["has_ci_cd"] = True
        if not cicd_info["ci_cd_platform"]:
            cicd_info["ci_cd_platform"] = "azure_pipelines"
        cicd_info["has_azure_pipelines"] = True

    return cicd_info


def _check_zed_extension_support(repo_path: Path) -> dict[str, Any]:
    """Check for Zed extension implementation."""
    zed_info = {
        "has_zed_extension": False,
        "has_manifest": False,
        "has_main_script": False,
        "extension_files": [],
    }

    # Look for Zed extension files
    extension_patterns = [
        "extension.json",
        "manifest.json",
        "zed_extension.json",
        "package.json",  # Sometimes used for Zed extensions
    ]

    for pattern in extension_patterns:
        matches = list(repo_path.rglob(pattern))
        if matches:
            zed_info["has_zed_extension"] = True
            zed_info["has_manifest"] = True
            zed_info["extension_files"].extend([str(m.relative_to(repo_path)) for m in matches])

    # Look for main extension script
    script_patterns = ["main.py", "index.js", "extension.py", "zed.py"]
    for pattern in script_patterns:
        matches = list(repo_path.rglob(pattern))
        if matches:
            zed_info["has_main_script"] = True
            zed_info["extension_files"].extend([str(m.relative_to(repo_path)) for m in matches])

    return zed_info


def _version_ge(version1: str, version2: str) -> bool:
    """Compare two version strings (>=)."""

    def normalize(v):
        if not v:
            return [0]
        return [int(x) for x in v.split(".") if x.isdigit()]

    v1_parts = normalize(version1)
    v2_parts = normalize(version2)

    # Pad with zeros to same length
    max_len = max(len(v1_parts), len(v2_parts))
    v1_parts.extend([0] * (max_len - len(v1_parts)))
    v2_parts.extend([0] * (max_len - len(v2_parts)))

    return v1_parts >= v2_parts


def _determine_priority(info: dict[str, Any]) -> str:
    """Determine upgrade priority based on runt reasons."""
    reasons = len(info.get("runt_reasons", []))
    if reasons == 0:
        return "none"
    elif reasons == 1:
        return "low"
    elif reasons == 2:
        return "medium"
    else:
        return "high"


# =====================================================================
# 2026 Fleet Standard Data Collection
# Added July 2026  new checks for upgraded runt_analyzer_rules.py
# =====================================================================


def _collect_fleet_2026_info(repo_path: Path, pyproject_file: Path, info: dict[str, Any]) -> None:
    """Collect all 2026 fleet-standard data points into info dict."""
    _check_webapp_presence(repo_path, info)
    if info.get("has_webapp"):
        _check_web_stack(repo_path, info)
        _check_bun_biome(repo_path, info)
        _check_playwright_e2e(repo_path, info)
        _check_dark_mode_data_testid(repo_path, info)
    _check_native_dir(repo_path, info)
    if info.get("has_native_dir"):
        _check_cua_nsis(repo_path, info)
        _check_tauri_cors(repo_path, info)
        _check_tauri_bundles_env(repo_path, info)
    _check_bak_files(repo_path, info)
    _check_api_base_port(repo_path, info)
    _check_llms_txt(repo_path, info)
    _check_glama_json(repo_path, info)
    _check_session_context(repo_path, info)
    _check_start_scripts(repo_path, info)
    _check_run_server_py(repo_path, info)
    _check_pyinstaller_spec(repo_path, info)
    _check_justfile(repo_path, info)
    _check_env_example(repo_path, info)
    _check_dual_transport(repo_path, info)
    _check_port_adjacency(repo_path, info)
    _check_bak_dryrun(repo_path, info)
    _check_prefab_coverage(repo_path, info)
    _check_docstring_2026_pattern(repo_path, info)
    _check_fastmcp_342_capabilities(repo_path, info)


def _check_webapp_presence(repo_path: Path, info: dict[str, Any]) -> None:
    """Detect if repo has a webapp (web_sota, webapp, frontend dirs)."""
    for d in ["web_sota", "webapp", "frontend"]:
        candidate = repo_path / d
        if candidate.is_dir() and (candidate / "package.json").exists():
            info["has_webapp"] = True
            return
    info["has_webapp"] = False


def _check_native_dir(repo_path: Path, info: dict[str, Any]) -> None:
    """Detect Tauri native/ or src-tauri/ directory."""
    for d in ["native", "web_sota/src-tauri"]:
        if (repo_path / d).exists():
            info["has_native_dir"] = True
            return
    info["has_native_dir"] = False


def _check_web_stack(repo_path: Path, info: dict[str, Any]) -> None:
    """Check package.json for fleet-standard web dependencies."""
    for d in ["web_sota", "webapp", "webapp/frontend", "frontend"]:
        pkg = repo_path / d / "package.json"
        if pkg.exists():
            try:
                import json as _json

                data = _json.loads(pkg.read_text(encoding="utf-8"))
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                info["has_tailwindcss"] = "tailwindcss" in deps
                info["has_lucide"] = "lucide-react" in deps
                info["has_zustand"] = "zustand" in deps
                info["has_framer_motion"] = "framer-motion" in deps
                return
            except Exception:
                pass
    info["has_tailwindcss"] = False
    info["has_lucide"] = False
    info["has_zustand"] = False
    info["has_framer_motion"] = False


def _check_bun_biome(repo_path: Path, info: dict[str, Any]) -> None:
    """Check for Bun + Biome usage."""
    has_lock = (repo_path / "bun.lock").exists()
    has_lock_npm = (repo_path / "package-lock.json").exists()
    info["using_npm"] = has_lock_npm and not has_lock
    info["has_biome"] = (repo_path / "biome.json").exists()
    for d in ["web_sota", "webapp", "webapp/frontend", "frontend"]:
        if (repo_path / d / "biome.json").exists():
            info["has_biome"] = True


def _check_llms_txt(repo_path: Path, info: dict[str, Any]) -> None:
    info["has_llms_txt"] = (repo_path / "llms.txt").is_file()
    info["has_llms_full_txt"] = (repo_path / "llms-full.txt").is_file()


def _check_glama_json(repo_path: Path, info: dict[str, Any]) -> None:
    info["has_glama_json"] = (repo_path / "glama.json").is_file()


def _check_env_example(repo_path: Path, info: dict[str, Any]) -> None:
    info["has_env_example"] = (repo_path / ".env.example").is_file()


def _check_playwright_e2e(repo_path: Path, info: dict[str, Any]) -> None:
    for d in ["web_sota", "webapp", "webapp/frontend"]:
        candidate = repo_path / d / "playwright.config.ts"
        if candidate.is_file():
            e2e_dir = repo_path / d / "e2e"
            info["has_playwright_e2e"] = e2e_dir.is_dir() and any(e2e_dir.glob("*.spec.ts"))
            return
        candidate_js = repo_path / d / "playwright.config.js"
        if candidate_js.is_file():
            e2e_dir = repo_path / d / "e2e"
            info["has_playwright_e2e"] = e2e_dir.is_dir() and any(e2e_dir.glob("*.spec.*"))
            return
    info["has_playwright_e2e"] = False


def _check_cua_nsis(repo_path: Path, info: dict[str, Any]) -> None:
    cua_script = repo_path / "scripts" / "cua-smoke.py"
    config = repo_path / "scripts" / "cua-nsis-config.json"
    info["has_cua_nsis"] = cua_script.is_file() and config.is_file()


def _check_session_context(repo_path: Path, info: dict[str, Any]) -> None:
    has_cursor = (repo_path / ".cursorrules").is_file()
    has_windsurf = (repo_path / ".windsurfrules").is_file()
    has_claude_plugin = (repo_path / ".claude-plugin" / "plugin.json").is_file()
    has_hooks = (repo_path / "hooks" / "hooks.json").is_file()
    info["has_session_context"] = has_cursor or has_windsurf or (has_claude_plugin and has_hooks)


def _check_start_scripts(repo_path: Path, info: dict[str, Any]) -> None:
    has_ps1 = (repo_path / "start.ps1").is_file()
    info["has_start_scripts"] = has_ps1


def _check_run_server_py(repo_path: Path, info: dict[str, Any]) -> None:
    info["has_run_server_py"] = (repo_path / "run_server.py").is_file()


def _check_pyinstaller_spec(repo_path: Path, info: dict[str, Any]) -> None:
    repo_name = repo_path.name.replace("-", "_")
    info["has_pyinstaller_spec"] = (repo_path / f"{repo_name}-backend.spec").is_file()


def _check_justfile(repo_path: Path, info: dict[str, Any]) -> None:
    info["has_justfile"] = (repo_path / "justfile").is_file()


def _check_dual_transport(repo_path: Path, info: dict[str, Any]) -> None:
    """Check for MCP_PORT env var handling or --serve arg in CLI."""
    transports_found = set()
    for py_file in _walk_py_files(repo_path):
        try:
            content = py_file.read_text(encoding="utf-8")
            if "MCP_PORT" in content or "MCP_HOST" in content:
                transports_found.add("http")
            if "stdio" in content.lower() or "run_stdio_async" in content:
                transports_found.add("stdio")
        except Exception:
            pass
    info["has_dual_transport"] = "http" in transports_found and "stdio" in transports_found


def _check_port_adjacency(repo_path: Path, info: dict[str, Any]) -> None:
    """Check for port numbers in config/start scripts."""
    import re as _re

    for pattern in ["*.py", "*.ps1", "*.toml", "*.json"]:
        for f in repo_path.glob(f"**/{pattern}"):
            if any(ig in str(f) for ig in _IGNORE_DIRS):
                continue
            try:
                content = f.read_text(encoding="utf-8", errors="replace")
                ports = _re.findall(r"(?:port|PORT)\s*[:=]?\s*(\d{4,5})", content)
                for p in ports:
                    pn = int(p)
                    if 10700 <= pn <= 11500:
                        info["has_adjacent_ports"] = True
                        return
            except Exception:
                pass
    info["has_adjacent_ports"] = False


def _check_bak_dryrun(repo_path: Path, info: dict[str, Any]) -> None:
    """Check if mutation scripts have --bak and --dryrun flags."""
    has_bak = False
    has_dryrun = False
    for py_file in _walk_py_files(repo_path):
        try:
            content = py_file.read_text(encoding="utf-8")
            if "--bak" in content or "create_bak" in content or "backup=True" in content:
                has_bak = True
            if "--dry-run" in content or "dry_run" in content or "--dryrun" in content:
                has_dryrun = True
        except Exception:
            pass
    info["has_bak_dryrun_pattern"] = has_bak and has_dryrun


def _check_prefab_coverage(repo_path: Path, info: dict[str, Any]) -> None:
    """Check for PrefabApp usage or prefab-ui dependency."""
    has_prefab_dep = False
    has_prefab_import = False
    pyproject = repo_path / "pyproject.toml"
    if pyproject.exists():
        try:
            import tomli as _tomli

            data = _tomli.loads(pyproject.read_text(encoding="utf-8"))
            deps = data.get("project", {}).get("dependencies", [])
            has_prefab_dep = any("prefab-ui" in d for d in deps)
        except Exception:
            pass
    for py_file in _walk_py_files(repo_path):
        try:
            content = py_file.read_text(encoding="utf-8")
            if "from prefab_ui" in content or "import prefab_ui" in content:
                has_prefab_import = True
                break
        except Exception:
            pass
    info["has_prefab_coverage"] = has_prefab_dep or has_prefab_import


def _check_dark_mode_data_testid(repo_path: Path, info: dict[str, Any]) -> None:
    """Check for dark mode CSS and data-testid attributes."""
    import re as _re

    has_dark = False
    has_testid = False
    for d in ["web_sota", "webapp", "webapp/frontend", "frontend"]:
        web_dir = repo_path / d
        if not web_dir.is_dir():
            continue
        for css_file in web_dir.rglob("*.css"):
            try:
                content = css_file.read_text(encoding="utf-8")
                if "color-scheme: dark" in content:
                    has_dark = True
            except Exception:
                pass
        for tsx_file in web_dir.rglob("*.tsx"):
            try:
                content = tsx_file.read_text(encoding="utf-8")
                if "data-testid=" in content:
                    has_testid = True
            except Exception:
                pass
    info["has_dark_mode"] = has_dark
    info["has_data_testid"] = has_testid


def _check_tauri_cors(repo_path: Path, info: dict[str, Any]) -> None:
    """Check for tauri://localhost in CORS config."""
    for py_file in _walk_py_files(repo_path):
        try:
            content = py_file.read_text(encoding="utf-8")
            if "tauri://localhost" in content:
                info["has_tauri_cors"] = True
                return
        except Exception:
            pass
    info["has_tauri_cors"] = False


def _check_docstring_2026_pattern(repo_path: Path, info: dict[str, Any]) -> None:
    """Check for docstring SOTA 2026 (Annotated+Field) and flag old-style Args: blocks."""
    import re as _re

    has_annotated_field = False
    has_return_format = False
    has_examples = False
    has_args_block = False
    for py_file in _walk_py_files(repo_path):
        try:
            content = py_file.read_text(encoding="utf-8")
            if not has_annotated_field and _re.search(r"Annotated\[.*Field\(description=", content):
                has_annotated_field = True
            if not has_return_format and _re.search(r"## Return\s+Format", content):
                has_return_format = True
            if not has_examples and _re.search(r"## Examples?", content):
                has_examples = True
            if not has_args_block and _re.search(r'""".*?Args:', content, _re.DOTALL):
                has_args_block = True
        except Exception:
            pass
    info["has_docstring_2026"] = has_annotated_field
    info["has_return_format_section"] = has_return_format
    info["has_examples_section"] = has_examples
    info["has_old_style_args_docstrings"] = has_args_block


def _build_remediation_todo(violations: list[dict[str, Any]]) -> str:
    """Generate a structured markdown remediation todo list from violations.

    Groups by severity (P0 critical, P1 warning, P2 info), orders by score
    deduction descending, and formats as a copy-paste ready LLM prompt.
    """
    if not violations:
        return "No issues found  repo is SOTA compliant."

    severity_order = {"critical": 0, "warning": 1, "info": 2}
    sorted_v = sorted(
        violations,
        key=lambda v: (severity_order.get(v.get("severity", "info"), 9), -v.get("score_deduction", 0)),
    )

    groups: dict[str, list[str]] = {"P0": [], "P1": [], "P2": []}
    for v in sorted_v:
        sev = v.get("severity", "info")
        group = "P0" if sev == "critical" else ("P1" if sev == "warning" else "P2")
        line = f"- [ ] **{v.get('message', 'Unknown issue')}**"
        rec = v.get("recommendation")
        if rec:
            line += f"\n      Fix: {rec}"
        ref = v.get("standard_ref")
        if ref:
            line += f"\n      Standard: `{ref}`"
        groups[group].append(line)

    todo = [
        f"# Remediation Plan: {len(violations)} items\n",
    ]
    for group_label, items in [("P0  Critical", "P0"), ("P1  Warning", "P1"), ("P2  Info", "P2")]:
        if groups[items]:
            todo.append(f"## {group_label}")
            todo.append("")
            todo.extend(groups[items])
            todo.append("")

    return "\n".join(todo)


def _check_fastmcp_342_capabilities(repo_path: Path, info: dict[str, Any]) -> None:
    """Check for FastMCP 3.4.2+ capabilities: prompts, resources, streamable HTTP, skills, output_schema."""
    import re as _re

    has_prompts = False
    has_resources = False
    has_streamable_http = False
    has_output_schema = False
    has_skills_provider = False
    for py_file in _walk_py_files(repo_path):
        try:
            content = py_file.read_text(encoding="utf-8")
            if not has_prompts and _re.search(r"@mcp\.prompt\s*\(", content):
                has_prompts = True
            if not has_resources and _re.search(r"@mcp\.resource\s*\(", content):
                has_resources = True
            if not has_streamable_http and _re.search(r"mcp\.http_app\s*\(", content):
                has_streamable_http = True
            if not has_output_schema and _re.search(r"output_schema\s*=", content):
                has_output_schema = True
            if not has_skills_provider and _re.search(r"SkillsDirectoryProvider", content):
                has_skills_provider = True
        except Exception:
            pass
    info["has_mcp_prompts"] = has_prompts
    info["has_mcp_resources"] = has_resources
    info["has_streamable_http"] = has_streamable_http
    info["has_output_schema"] = has_output_schema
    info["has_skills_provider"] = has_skills_provider


def _check_tauri_bundles_env(repo_path: Path, info: dict[str, Any]) -> None:
    """Check if tauri.conf.json bundles .env instead of .env.example (security leak)."""
    import json as _json

    for cand in ["tauri.conf.json", "native/tauri.conf.json", "web_sota/src-tauri/tauri.conf.json"]:
        tauri_path = repo_path / cand
        if tauri_path.is_file():
            try:
                data = _json.loads(tauri_path.read_text(encoding="utf-8"))
                resources = data.get("bundle", {}).get("resources", [])
                for r in resources if isinstance(resources, list) else []:
                    if ".env" in r and ".env.example" not in r:
                        info["tauri_bundles_env"] = True
                        return
            except Exception:
                pass
    info["tauri_bundles_env"] = False


def _check_bak_files(repo_path: Path, info: dict[str, Any]) -> None:
    """Check for stale .bak files in source directories."""
    count = 0
    for d in ["src", "web_sota", "webapp"]:
        web_dir = repo_path / d
        if web_dir.is_dir():
            try:
                count += len(list(web_dir.rglob("*.bak")))
            except Exception:
                pass
    info["stale_bak_file_count"] = count


def _check_api_base_port(repo_path: Path, info: dict[str, Any]) -> None:
    """Check if API_BASE points to frontend port instead of backend port (Tauri prod breakage)."""
    import re as _re

    for pattern in ["api.ts", "api.js", "api.tsx"]:
        for f in repo_path.rglob(pattern):
            if any(ig in str(f) for ig in _IGNORE_DIRS):
                continue
            try:
                content = f.read_text(encoding="utf-8")
                match = _re.search(r'API_BASE\s*=\s*["\']http://127\.0\.0\.1:(\d+)', content)
                if match:
                    port = int(match.group(1))
                    repo_port = info.get("has_adjacent_ports", None)
                    if repo_port and port != repo_port:
                        info["api_base_port_mismatch"] = True
                        return
            except Exception:
                pass
    info["api_base_port_mismatch"] = False
