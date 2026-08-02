"""In-memory TTL cache for GitHub repository trees (per inspire_repo session)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from meta_mcp.utils.github_inspiration import RepoRef

DEFAULT_TTL_SECONDS = 300.0


@dataclass
class CachedTreeEntry:
    ref: RepoRef
    branch: str
    tree: list[dict[str, Any]]
    truncated: bool
    fetched_at: float


class RepoInspirationTreeCache:
    """Cache git trees by owner/repo/branch to avoid repeated GitHub API calls."""

    def __init__(self, ttl_seconds: float = DEFAULT_TTL_SECONDS) -> None:
        self._ttl = ttl_seconds
        self._entries: dict[str, CachedTreeEntry] = {}

    @staticmethod
    def make_key(owner: str, repo: str, branch: str) -> str:
        return f"{owner.lower()}/{repo.lower()}@{branch}"

    def get(self, owner: str, repo: str, branch: str) -> CachedTreeEntry | None:
        key = self.make_key(owner, repo, branch)
        entry = self._entries.get(key)
        if not entry:
            return None
        if time.time() - entry.fetched_at > self._ttl:
            del self._entries[key]
            return None
        return entry

    def set(self, owner: str, repo: str, branch: str, entry: CachedTreeEntry) -> None:
        key = self.make_key(owner, repo, branch)
        self._entries[key] = entry

    def clear(self) -> None:
        self._entries.clear()


# Process-wide cache shared by RepoInspirationService instances in one MCP server process
_global_tree_cache = RepoInspirationTreeCache()


def get_tree_cache() -> RepoInspirationTreeCache:
    return _global_tree_cache


# ---- File content cache (same TTL pattern, per-path keys) ----


class FileContentCache:
    def __init__(self, ttl_seconds: float = DEFAULT_TTL_SECONDS) -> None:
        self._ttl = ttl_seconds
        self._entries: dict[str, tuple[float, str]] = {}

    @staticmethod
    def make_key(owner: str, repo: str, branch: str, path: str) -> str:
        return f"{owner.lower()}/{repo.lower()}@{branch}/{path.lstrip('/')}"

    def get(self, owner: str, repo: str, branch: str, path: str) -> str | None:
        key = self.make_key(owner, repo, branch, path)
        entry = self._entries.get(key)
        if not entry:
            return None
        cached_at, content = entry
        if time.time() - cached_at > self._ttl:
            del self._entries[key]
            return None
        return content

    def set(self, owner: str, repo: str, branch: str, path: str, content: str) -> None:
        key = self.make_key(owner, repo, branch, path)
        self._entries[key] = (time.time(), content)

    def clear(self) -> None:
        self._entries.clear()


_global_file_cache = FileContentCache()


def get_file_cache() -> FileContentCache:
    return _global_file_cache
