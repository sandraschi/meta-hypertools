import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


def analyze_github_health(repo_path: Path) -> dict[str, Any]:
    """Analyze GitHub repository health using the gh CLI."""
    result = {
        "has_github_repo": False,
        "glama_json_present": False,
        "open_issues": 0,
        "open_prs": 0,
        "latest_release": None,
    }

    # Check for glama.json
    if (repo_path / "glama.json").exists():
        result["glama_json_present"] = True

    git_dir = repo_path / ".git"
    if not git_dir.exists():
        return result

    # Check if gh CLI is available and repository is attached
    try:
        gh_path = shutil.which("gh") or "gh"
        # Check if it has a default remote that github CLI can recognize
        repo_check = subprocess.run(
            [gh_path, "repo", "view", "--json", "name"],
            cwd=repo_path,
            capture_output=True,
            text=True,
        )

        if repo_check.returncode == 0:
            result["has_github_repo"] = True

            # Get Issues & PRs count
            stats_proc = subprocess.run(
                [
                    gh_path,
                    "api",
                    "repos/{owner}/{repo}",
                    "--jq",
                    "{issues: .open_issues_count}",
                ],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )
            if stats_proc.returncode == 0:
                try:
                    stats = json.loads(stats_proc.stdout)
                    # Note: GitHub's open_issues_count includes PRs.
                    # To be perfectly accurate we'd need GraphQL, but this is a good approximation.
                    result["open_issues"] = stats.get("issues", 0)
                except json.JSONDecodeError:
                    pass

            # Get Latest Release
            release_proc = subprocess.run(
                [gh_path, "release", "view", "--json", "tagName"],
                cwd=repo_path,
                capture_output=True,
                text=True,
            )
            if release_proc.returncode == 0:
                try:
                    rel_data = json.loads(release_proc.stdout)
                    result["latest_release"] = rel_data.get("tagName")
                except json.JSONDecodeError:
                    pass

    except FileNotFoundError:
        # `gh` CLI not installed
        pass
    except Exception:
        pass

    return result
