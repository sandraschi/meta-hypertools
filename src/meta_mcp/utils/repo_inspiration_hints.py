"""Monorepo and truncated-tree hints for repo inspiration (Phase B)."""

from __future__ import annotations

from collections import Counter

LARGE_REPO_FILE_THRESHOLD = 2000
MAX_SUBPATH_SUGGESTIONS = 8
MAX_DIRECTORY_ROWS = 40

# Prefer package-like roots over noise
_SUBPATH_SKIP = frozenset(
    {
        "docs",
        "doc",
        "test",
        "tests",
        "examples",
        "example",
        "scripts",
        "tools",
        ".github",
        "assets",
        "static",
        "public",
        "vendor",
    }
)


def is_large_repo_context(*, truncated_github: bool, path_count: int) -> bool:
    return truncated_github or path_count >= LARGE_REPO_FILE_THRESHOLD


def infer_language_hint_from_tree(tree: list[dict]) -> str | None:
    """Guess primary language from manifest filenames in the tree (no fetch)."""
    paths = {(item.get("path") or "").lower() for item in tree if item.get("type") == "blob"}
    if paths & {"pyproject.toml", "setup.py", "requirements.txt"}:
        return "python"
    if "cargo.toml" in paths:
        return "rust"
    if "go.mod" in paths:
        return "go"
    if paths & {"package.json", "pnpm-workspace.yaml"}:
        return "typescript"
    if "build.gradle" in paths or "pom.xml" in paths:
        return "java"
    if "gemfile" in paths:
        return "ruby"
    return None


def directory_counts(paths: list[str]) -> list[tuple[str, int]]:
    """Count source files per top-level directory (or file at repo root)."""
    counts: Counter[str] = Counter()
    for path in paths:
        parts = path.replace("\\", "/").split("/")
        key = parts[0] if len(parts) > 1 else "(root files)"
        counts[key] += 1
    return counts.most_common(MAX_DIRECTORY_ROWS)


def build_directory_summary_text(paths: list[str]) -> str:
    rows = directory_counts(paths)
    if not rows:
        return "_No paths in scope._"
    lines = ["Top-level areas (file counts):", ""]
    for name, count in rows:
        lines.append(f"   {name}: {count} files")
    lines.extend(
        [
            "",
            "For monorepos, rerun with inspire_repo(..., subpath=<folder>) to narrow scope.",
        ]
    )
    return "\n".join(lines)


def suggest_subpaths(paths: list[str], limit: int = MAX_SUBPATH_SUGGESTIONS) -> list[str]:
    """Suggest subpath values ranked by file count (skips low-value roots)."""
    counts: Counter[str] = Counter()
    for path in paths:
        parts = path.replace("\\", "/").split("/")
        if len(parts) < 2:
            continue
        top = parts[0]
        if top.lower() in _SUBPATH_SKIP:
            continue
        counts[top] += 1
        if len(parts) >= 2:
            two = f"{parts[0]}/{parts[1]}"
            if parts[1].lower() not in _SUBPATH_SKIP:
                counts[two] += 1

    ranked = [sp for sp, _ in counts.most_common(limit * 2) if sp not in _SUBPATH_SKIP and not sp.startswith(".")]
    seen: set[str] = set()
    out: list[str] = []
    for sp in ranked:
        if sp in seen:
            continue
        seen.add(sp)
        out.append(sp)
        if len(out) >= limit:
            break
    return out


def build_study_hints(
    *,
    owner: str,
    repo: str,
    branch: str,
    truncated_github: bool,
    path_count: int,
    subpath: str | None,
    gitingest_url: str,
    suggested_subpaths: list[str],
    suggested_language_hint: str | None,
) -> list[str]:
    hints: list[str] = []
    large = is_large_repo_context(truncated_github=truncated_github, path_count=path_count)

    if truncated_github:
        hints.append(
            "GitHub API returned tree truncated=true  the file list may be incomplete. "
            "Use subpath= to scope a folder, or gitingest for a full ingest."
        )
    if large and not subpath:
        hints.append(
            f"Large repository ({path_count} source files in scope). "
            "Prefer profile=brief and a subpath (e.g. src/) instead of a full tree."
        )
    if suggested_subpaths and not subpath:
        hints.append("Suggested subpath values: " + ", ".join(suggested_subpaths[:6]))
    if suggested_language_hint:
        hints.append(f"Detected manifest suggests language_hint={suggested_language_hint!r} for auto file pick.")
    if gitingest_url:
        hints.append(f"Full-repo ingest link: {gitingest_url}")
    hints.append(
        f"Local clone of {owner}/{repo}? Use pack_mcp_repository or repository_analysis on disk  "
        "inspire_repo is for remote public study only."
    )
    hints.append(
        "Fleet: git-github gitingest_* tools convert GitHub URLs to digest links when you need verbatim dumps."
    )
    return hints
