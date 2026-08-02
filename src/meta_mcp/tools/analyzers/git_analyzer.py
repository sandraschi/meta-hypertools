import shutil
import subprocess
from pathlib import Path
from typing import Any


def analyze_git_health(repo_path: Path) -> dict[str, Any]:
    """Analyze the Git health of a repository."""
    result = {
        "is_repo": False,
        "branch": None,
        "has_uncommitted_changes": False,
        "needs_push": False,
        "last_commit_timestamp": None,
    }

    git_dir = repo_path / ".git"
    if not git_dir.exists() or not git_dir.is_dir():
        return result

    result["is_repo"] = True

    try:
        # Get current branch
        git_path = shutil.which("git") or "git"
        branch_proc = subprocess.run(
            [git_path, "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        result["branch"] = branch_proc.stdout.strip()

        # Check uncommitted changes
        status_proc = subprocess.run(
            [git_path, "status", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True,
        )
        result["has_uncommitted_changes"] = len(status_proc.stdout.strip()) > 0

        # Check needs push (compare tracking branch)
        try:
            push_proc = subprocess.run(
                [git_path, "log", "@{u}..HEAD", "--oneline"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            result["needs_push"] = len(push_proc.stdout.strip()) > 0
        except subprocess.CalledProcessError:
            # If no upstream is set, it might need a push, but we can't reliably check `@{u}`.
            result["needs_push"] = False

        # Get last commit timestamp (Unix epoch)
        try:
            time_proc = subprocess.run(
                [git_path, "log", "-1", "--format=%ct"],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            result["last_commit_timestamp"] = int(time_proc.stdout.strip())
        except subprocess.CalledProcessError:
            pass

    except subprocess.CalledProcessError:
        pass

    return result
