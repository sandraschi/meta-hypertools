"""
Global configuration constants and environment handling for MetaMCP.
"""

import os
from pathlib import Path


def _resolve_repos_path() -> str:
    raw = os.getenv("REPOS_DIR", "").strip()
    if raw:
        return str(Path(raw).expanduser().resolve())
    return str((Path.home() / "repos").resolve())


DEFAULT_REPOS_PATH = _resolve_repos_path()
