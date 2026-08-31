import os
import subprocess
from pathlib import Path


def _resolve_repos_dir() -> Path:
    env_dir = os.environ.get("FLEET_REPOS_ROOT") or os.environ.get("REPOS_DIR") or os.environ.get("REPOS_ROOT")
    if env_dir:
        return Path(env_dir)
    default_d = Path(r"D:\Dev\repos")
    if default_d.exists():
        return default_d
    return Path.home() / "repos"


REPOS_DIR = _resolve_repos_dir()


def run_cmd(cmd, cwd, timeout=120):
    # Run a command and return (success, output)
    try:
        result = subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True, check=False, timeout=timeout)
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, f"Command timed out after {timeout}s"
    except Exception as e:
        return False, str(e)


def autofix_uv_setup():
    print(f"Auto-fixing `uv` setup in {REPOS_DIR}...\n")

    mcp_repos = []

    if REPOS_DIR.exists():
        for item in REPOS_DIR.iterdir():
            if item.is_dir() and "mcp" in item.name.lower() and not item.name.startswith("."):
                mcp_repos.append(item)

    fixed_count = 0
    failed_count = 0
    skipped_count = 0

    for repo in sorted(mcp_repos):
        has_pyproject = (repo / "pyproject.toml").exists()
        has_uv_lock = (repo / "uv.lock").exists()
        has_venv = (repo / ".venv").exists()

        # Only process Python repos
        if not has_pyproject:
            continue

        if has_uv_lock and has_venv:
            skipped_count += 1
            # print(f"[{repo.name}] SUCCESS Already configured, skipping.")
            continue

        print(f"\n[{repo.name}]  Processing...")
        success = True

        if not has_uv_lock:
            print("  -> Running `uv lock`...")
            ok, out = run_cmd("uv lock", cwd=str(repo))
            if not ok:
                print(f"  ERROR `uv lock` failed:\n{out}")
                success = False

        if success and not has_venv:
            print("  -> Running `uv sync`...")
            ok, out = run_cmd("uv sync", cwd=str(repo))
            if not ok:
                print(f"  ERROR `uv sync` failed:\n{out}")
                success = False

        if success:
            print("  SUCCESS Successfully configured.")
            fixed_count += 1
        else:
            failed_count += 1

    print("\n" + "=" * 50)
    print("Auto-Fix Complete")
    print(f"Successfully Fixed : {fixed_count}")
    print(f"Failed to Fix      : {failed_count}")
    print(f"Already OK         : {skipped_count}")
    print("=" * 50)


if __name__ == "__main__":
    autofix_uv_setup()
