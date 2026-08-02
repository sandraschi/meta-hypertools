"""Fleet config file audit  scan repos for agent configs, discovery files, and metadata."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPOS_ROOT = Path(os.environ.get("FLEET_REPOS_ROOT", r"D:\Dev\repos"))
MCD_ROOT = REPOS_ROOT / "mcp-central-docs"

# Config file types: (relative_path, category, description)
CONFIG_TARGETS: list[tuple[str, str, str]] = [
    ("CLAUDE.md", "agent", "Claude Code / opencode behavioral instructions"),
    ("AGENTS.md", "agent", "Agent instruction file"),
    (".cursorrules", "agent", "Cursor IDE rules (repo root)"),
    (".cursor/rules/", "agent", "Cursor rules directory"),
    (".windsurfrules", "agent", "Windsurf rules file"),
    ("llms.txt", "discovery", "LLM discovery index (required)"),
    ("llms-full.txt", "discovery", "Full LLM documentation (required)"),
    ("glama.json", "discovery", "Glama registry manifest"),
    (".env.example", "metadata", "Environment variable template"),
    ("CHANGELOG.md", "metadata", "Changelog / release notes"),
]

CONFIG_PRIORITY = [
    ("Session prompt", "per-session", "Highest  inline instructions"),
    ("<repo>/CLAUDE.md", "per-repo", "Overrides global CLAUDE.md"),
    ("<repo>/.cursorrules", "per-ide", "Cursor-specific rules"),
    ("<repo>/.cursor/rules/*.mdc", "per-ide", "Cursor rules directory"),
    ("<repo>/AGENTS.md", "per-repo", "Agent behavioral file"),
    ("~/.claude/CLAUDE.md", "global", "Lowest  global fallback"),
]


@dataclass
class ConfigFileEntry:
    path: str
    exists: bool
    last_modified: str = ""
    size_bytes: int = 0
    category: str = ""
    description: str = ""


@dataclass
class RepoConfigAudit:
    repo_name: str
    repo_root: str
    files: dict[str, ConfigFileEntry] = field(default_factory=dict)
    mcd_reference_file: str = ""


def get_global_claude_path() -> Path:
    return Path.home() / ".claude" / "CLAUDE.md"


def get_global_agents_path() -> Path:
    return Path.home() / ".claude" / "AGENTS.md"


def scan_repo(repo_path: str) -> RepoConfigAudit:
    """Scan a single repo for all known config files."""
    root = Path(repo_path)
    name = root.name
    audit = RepoConfigAudit(repo_name=name, repo_root=str(root))

    for rel_path, category, desc in CONFIG_TARGETS:
        full = root / rel_path
        entry = ConfigFileEntry(
            path=rel_path,
            exists=full.exists(),
            category=category,
            description=desc,
        )
        if full.exists():
            try:
                stat = full.stat()
                entry.size_bytes = stat.st_size
                dt = datetime.fromtimestamp(stat.st_mtime, tz=UTC)
                entry.last_modified = dt.strftime("%Y-%m-%d %H:%M")
            except OSError:
                pass
        audit.files[rel_path] = entry

    return audit


def scan_fleet(
    repos_root: str | None = None,
    limit: int = 0,
    repo_filter: str = "",
) -> dict[str, Any]:
    """Scan all repos in the fleet root for config files."""
    root = Path(repos_root or REPOS_ROOT)
    if not root.is_dir():
        return {"success": False, "message": f"Repos root not found: {root}"}

    repos: list[RepoConfigAudit] = []
    for entry in sorted(root.iterdir()):
        if not entry.is_dir():
            continue
        name = entry.name
        if name.startswith(".") or name.startswith("_"):
            continue
        if repo_filter and repo_filter.lower() not in name.lower():
            continue
        repos.append(scan_repo(str(entry)))
        if limit > 0 and len(repos) >= limit:
            break

    # Global files
    global_files: dict[str, ConfigFileEntry] = {}
    for gpath, gkey in [
        (get_global_claude_path(), "global_CLAUDE.md"),
        (get_global_agents_path(), "global_AGENTS.md"),
    ]:
        entry = ConfigFileEntry(
            path=str(gpath),
            exists=gpath.exists(),
            category="global",
            description="Global agent behavioral file",
        )
        if gpath.exists():
            try:
                stat = gpath.stat()
                entry.size_bytes = stat.st_size
                dt = datetime.fromtimestamp(stat.st_mtime, tz=UTC)
                entry.last_modified = dt.strftime("%Y-%m-%d %H:%M")
            except OSError:
                pass
        global_files[gkey] = entry

    # Stats
    total = len(repos)
    file_type_counts: dict[str, int] = {}
    for rel_path, _, _ in CONFIG_TARGETS:
        file_type_counts[rel_path] = sum(1 for r in repos if r.files.get(rel_path) and r.files[rel_path].exists)

    return {
        "success": True,
        "total_repos": total,
        "repos": [
            {
                "name": r.repo_name,
                "files": {
                    k: {
                        "exists": v.exists,
                        "last_modified": v.last_modified,
                        "size_bytes": v.size_bytes,
                        "category": v.category,
                        "description": v.description,
                    }
                    for k, v in r.files.items()
                },
            }
            for r in repos
        ],
        "global_files": {
            k: {
                "exists": v.exists,
                "last_modified": v.last_modified,
                "size_bytes": v.size_bytes,
            }
            for k, v in global_files.items()
        },
        "file_type_counts": file_type_counts,
        "config_priority_chain": CONFIG_PRIORITY,
    }
