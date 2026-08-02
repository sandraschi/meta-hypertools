import re
from pathlib import Path
from typing import Any


def analyze_ce_akg(repo_path: Path, all_repos_path: Path) -> dict[str, Any]:
    """
    Perform Cross-Environment Adversarial Knowledge Graph (CE-AKG) mapping.
    Tracks how data flows between different MCP servers and identifies dependencies.
    """
    results = {
        "dependencies": [],
        "data_flows": [],
        "shared_resources": [],
        "vulnerability_exposure": "low",
        "swarm_connectivity": 0.0,
    }

    # 1. Detect Inter-Repo Dependencies (Imports)
    # Get all sibling repo names to check for imports
    sibling_repos = [item.name.replace("-", "_") for item in all_repos_path.iterdir() if item.is_dir()]

    import_dependencies = set()
    data_flow_triggers = []

    # Scan python files for imports and potential call_tool patterns
    for py_file in repo_path.rglob("*.py"):
        if "venv" in str(py_file) or ".venv" in str(py_file):
            continue

        try:
            content = py_file.read_text(encoding="utf-8")

            # Check for sibling repo imports
            for repo_name in sibling_repos:
                if repo_name == repo_path.name.replace("-", "_"):
                    continue
                if re.search(rf"import\s+{repo_name}|from\s+{repo_name}\s+import", content):
                    import_dependencies.add(repo_name)

            # Check for tool call patterns (Data Flows)
            # Pattern: call_tool("other_server_name:tool_name", ...)
            tool_calls = re.findall(r"call_tool\s*\(\s*['\"]([^'\"]+)['\"]", content)
            for call in tool_calls:
                if ":" in call:
                    target_server = call.split(":")[0]
                    data_flow_triggers.append(
                        {"type": "tool_call", "target": target_server, "file": str(py_file.relative_to(repo_path))}
                    )
                    import_dependencies.add(target_server)

            # Check for Environment Variable usage (Shared Resources)
            env_vars = re.findall(r"os\.environ\.get\s*\(\s*['\"]([^'\"]+)['\"]", content)
            for env_var in env_vars:
                # Common shared env vars across the fleet
                if any(x in env_var for x in ["PATH", "DB", "API_KEY", "URL", "PORT"]):
                    results["shared_resources"].append({"name": env_var, "file": str(py_file.relative_to(repo_path))})

        except Exception:
            pass

    results["dependencies"] = list(import_dependencies)
    results["data_flows"] = data_flow_triggers

    # Calculate Swarm Connectivity (normalized 0.0 to 1.0)
    if sibling_repos:
        results["swarm_connectivity"] = round(len(import_dependencies) / max(len(sibling_repos), 1), 2)

    # Determine vulnerability exposure based on connectivity and shared resources
    if results["swarm_connectivity"] > 0.5 or len(results["shared_resources"]) > 10:
        results["vulnerability_exposure"] = "high"
    elif results["swarm_connectivity"] > 0.2:
        results["vulnerability_exposure"] = "medium"

    return results
