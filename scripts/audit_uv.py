import os
from pathlib import Path

REPOS_DIR = Path(os.environ.get("REPOS_DIR", Path.home() / "repos"))


def audit_uv_setup():
    print(f"Auditing repositories in {REPOS_DIR} for `uv` setup...\n")

    mcp_repos = []

    # Simple heuristic: directory ends with "-mcp" or contains "mcp" in name
    if REPOS_DIR.exists():
        for item in REPOS_DIR.iterdir():
            if item.is_dir() and "mcp" in item.name.lower() and not item.name.startswith("."):
                mcp_repos.append(item)

    results = []

    for repo in sorted(mcp_repos):
        repo_name = repo.name

        # Check markers
        has_pyproject = (repo / "pyproject.toml").exists()
        has_uv_lock = (repo / "uv.lock").exists()
        has_venv = (repo / ".venv").exists()
        (repo / "node_modules").exists()
        has_package_json = (repo / "package.json").exists()

        # Determine language/type
        repo_type = "Python" if has_pyproject else ("Node.js" if has_package_json else "Unknown/Other")

        if repo_type == "Node.js" and not has_pyproject:
            # Skip pure TS/JS repos for uv audit, unless they also have python
            continue

        status = "SUCCESS OK"
        issues = []

        if repo_type == "Python":
            if not has_uv_lock:
                status = "ERROR MISSING uv.lock"
                issues.append("Needs `uv lock`")
            if not has_venv:
                if status == "SUCCESS OK":
                    status = "WARNING MISSING .venv"
                issues.append("Needs `uv sync`")

            results.append(
                {"repo": repo_name, "status": status, "issues": ", ".join(issues) if issues else "Fully configured"}
            )

    # Print report
    print(f"{'Repository':<30} | {'Status':<20} | {'Details'}")
    print("-" * 80)

    ok_count = 0
    issue_count = 0

    for r in results:
        print(f"{r['repo']:<30} | {r['status']:<20} | {r['issues']}")
        if "SUCCESS" in r["status"]:
            ok_count += 1
        else:
            issue_count += 1

    print("-" * 80)
    print(f"Total Python MCP Repos: {len(results)}")
    print(f"Fully configured with uv: {ok_count}")
    print(f"Missing uv setup/sync: {issue_count}")


if __name__ == "__main__":
    audit_uv_setup()
