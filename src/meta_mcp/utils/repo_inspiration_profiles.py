"""Profile limits and structured chapters for repo inspiration (Phase A)."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from typing import Any, Literal

from meta_mcp.utils.github_inspiration import (
    MAX_STRUCTURE_FILES,
    build_files_text,
    render_tree,
    truncate_content,
)

ChapterKind = Literal[
    "overview", "tree", "manifest", "manifest-secondary", "readme", "source", "prompt", "file", "hint", "repo_meta"
]

VALID_PROFILES = frozenset({"brief", "standard", "deep"})


@dataclass(frozen=True)
class ProfileLimits:
    structure_max_shown: int
    auto_files: int
    explicit_files: int
    total_chars: int
    per_file_chars: int
    pattern_structure_lines: int
    pattern_source_files: int
    pattern_source_budget: int
    readme_limit: int
    manifest_limit: int


PROFILE_LIMITS: dict[str, ProfileLimits] = {
    "brief": ProfileLimits(
        structure_max_shown=200,
        auto_files=5,
        explicit_files=10,
        total_chars=40_000,
        per_file_chars=12_000,
        pattern_structure_lines=80,
        pattern_source_files=3,
        pattern_source_budget=20_000,
        readme_limit=5_000,
        manifest_limit=4_000,
    ),
    "standard": ProfileLimits(
        structure_max_shown=MAX_STRUCTURE_FILES,
        auto_files=10,
        explicit_files=15,
        total_chars=80_000,
        per_file_chars=25_000,
        pattern_structure_lines=300,
        pattern_source_files=8,
        pattern_source_budget=50_000,
        readme_limit=10_000,
        manifest_limit=8_000,
    ),
    "deep": ProfileLimits(
        structure_max_shown=MAX_STRUCTURE_FILES,
        auto_files=15,
        explicit_files=20,
        total_chars=100_000,
        per_file_chars=30_000,
        pattern_structure_lines=400,
        pattern_source_files=12,
        pattern_source_budget=70_000,
        readme_limit=12_000,
        manifest_limit=10_000,
    ),
}


def normalize_profile(profile: str | None) -> str:
    key = (profile or "standard").strip().lower()
    return key if key in VALID_PROFILES else "standard"


def get_profile_limits(profile: str | None) -> ProfileLimits:
    return PROFILE_LIMITS[normalize_profile(profile)]


def apply_subpath_filter(paths: list[str], subpath: str | None) -> list[str]:
    if not subpath or not subpath.strip():
        return paths
    prefix = subpath.strip().replace("\\", "/").strip("/")
    if not prefix:
        return paths
    return [p for p in paths if p == prefix or p.startswith(f"{prefix}/")]


def filter_path_globs(
    paths: list[str],
    include_globs: list[str] | None,
    exclude_globs: list[str] | None,
) -> list[str]:
    result = paths
    if include_globs:
        inc = [g.strip() for g in include_globs if g.strip()]
        if inc:
            result = [p for p in result if any(fnmatch.fnmatch(p, g) for g in inc)]
    if exclude_globs:
        exc = [g.strip() for g in exclude_globs if g.strip()]
        if exc:
            result = [p for p in result if not any(fnmatch.fnmatch(p, g) for g in exc)]
    return result


def gitingest_url(owner: str, repo: str, branch: str, subpath: str | None = None) -> str:
    base = f"https://gitingest.com/{owner}/{repo}"
    if subpath and subpath.strip():
        sp = subpath.strip().replace("\\", "/").strip("/")
        return f"{base}/tree/{branch}/{sp}"
    return f"{base}/tree/{branch}"


def make_chapter(chapter_id: str, title: str, kind: ChapterKind, body: str) -> dict[str, str]:
    return {
        "id": chapter_id,
        "title": title,
        "kind": kind,
        "body": body.strip(),
    }


def chapters_to_text(chapters: list[dict[str, Any]], *, footer_hints: list[str] | None = None) -> str:
    parts: list[str] = []
    for ch in chapters:
        body = (ch.get("body") or "").strip()
        if not body:
            continue
        kind = ch.get("kind", "")
        title = ch.get("title", "")
        if kind in ("source", "file", "manifest", "readme"):
            parts.extend(["", f" {title} ", "", body, "", f" END {title} "])
        elif kind == "prompt":
            parts.append(body)
        else:
            parts.append(body)
    if footer_hints:
        parts.extend(["", "" * 60, *footer_hints])
    return "\n".join(parts)


def compose_structure_chapters(
    owner: str,
    repo: str,
    branch: str,
    paths: list[str],
    total_files: int,
    limits: ProfileLimits,
    *,
    subpath: str | None = None,
    truncated_github: bool = False,
    large_repo_mode: bool = False,
    directory_summary: str | None = None,
    study_hints: list[str] | None = None,
    repo_meta: dict[str, Any] | None = None,
) -> tuple[list[dict[str, str]], str]:
    shown = paths[: limits.structure_max_shown]
    sub_note = f"\n[subpath] Subpath filter: {subpath.strip()}" if subpath and subpath.strip() else ""
    trunc_note = ""
    if total_files > limits.structure_max_shown:
        trunc_note = (
            f"\nwarning:   Showing {limits.structure_max_shown} of {total_files} files. "
            "Use inspire_repo(operation=files) with target_files for specific paths.\n"
        )
    if large_repo_mode:
        trunc_note += (
            "\nwarning:   Large or truncated tree  see directory summary and data.hints for subpath suggestions.\n"
        )
    overview = "\n".join(
        [
            f"[repo]  Repository: {owner}/{repo}  (branch: {branch}){sub_note}",
            f"files:  {len(shown)} source files"
            + (f" ({total_files} total)" if total_files > limits.structure_max_shown else ""),
            trunc_note,
        ]
    ).strip()
    chapters: list[dict[str, str]] = [
        make_chapter("overview", f"{owner}/{repo}", "overview", overview),
    ]
    if large_repo_mode and directory_summary:
        chapters.append(
            make_chapter("dir-summary", "Top-level directories", "tree", directory_summary),
        )
        tree_title = "Sample paths (capped)"
        tree_body = render_tree(shown[: min(len(shown), 120)])
    else:
        tree_title = "Source file tree"
        tree_body = render_tree(shown)
    chapters.append(make_chapter("tree", tree_title, "tree", tree_body))
    if truncated_github:
        chapters.append(
            make_chapter(
                "hint-github-trunc",
                "GitHub API tree truncated",
                "hint",
                "GitHub returned truncated=true for this tree. Very large repos may omit paths. "
                "Try subpath=src or a narrower folder.",
            )
        )
    if study_hints:
        chapters.append(
            make_chapter(
                "hints",
                "Study hints",
                "hint",
                "\n".join(f" {h}" for h in study_hints),
            )
        )
    if repo_meta:
        meta_lines = [
            f"Description: {repo_meta.get('description') or '(none)'}",
            f"Language: {repo_meta.get('language') or '(unknown)'}",
            f"License: {repo_meta.get('license') or '(not specified)'}",
            f"Stars: {repo_meta.get('stars', 0):,}",
            f"Archived: {repo_meta.get('archived', False)}",
            f"Last push: {repo_meta.get('updated_at', '')[:10] if repo_meta.get('updated_at') else '(unknown)'}",
        ]
        if repo_meta.get("topics"):
            meta_lines.append(f"Topics: {', '.join(repo_meta['topics'])}")
        if repo_meta.get("homepage"):
            meta_lines.append(f"Homepage: {repo_meta['homepage']}")
        chapters.append(make_chapter("repo-meta", "Repository metadata", "repo_meta", "\n".join(meta_lines)))
    footer = [
        "",
        "tip:  Next steps:",
        "   inspire_repo(operation=files)  read source paths or auto-pick core files",
        "   inspire_repo(operation=patterns)  architecture study pack",
        "",
        "warning:   Read to understand patterns  adapt ideas; do not copy verbatim.",
    ]
    text_parts = [overview, trunc_note]
    if large_repo_mode and directory_summary:
        text_parts.extend(["" * 60, directory_summary])
    text_parts.extend(["" * 60, tree_body, "" * 60, *footer])
    if study_hints:
        text_parts.extend(["", "tip:  Hints:", *[f"   {h}" for h in study_hints]])
    text = "\n".join(text_parts)
    return chapters, text


def compose_patterns_chapters(
    owner: str,
    repo: str,
    branch: str,
    all_paths: list[str],
    readme: str,
    manifest_entries: list[tuple[str, str]],
    source_blocks: list[tuple[str, str]],
    limits: ProfileLimits,
    *,
    subpath: str | None = None,
    profile: str = "standard",
) -> tuple[list[dict[str, str]], str]:
    structure_slice = "\n".join(all_paths[: limits.pattern_structure_lines])
    more_note = ""
    if len(all_paths) > limits.pattern_structure_lines:
        more_note = f"\n... and {len(all_paths) - limits.pattern_structure_lines} more files"
    sub_line = f" (subpath: {subpath})" if subpath and subpath.strip() else ""
    prompt_body = "\n".join(
        [
            "# MetaMCP  Architecture & Pattern Analysis (inspiration)",
            "",
            f"You are analyzing **{owner}/{repo}**{sub_line} as a reference (profile: {profile}).",
            "Below: directory structure, manifest, and key source files.",
            "",
            "Your task:",
            "1. **What kind of project is this?**",
            "2. **How is the code organized?**",
            "3. **What design patterns are used?**",
            "4. **What is the tech stack?**",
            "5. **How does execution flow?** (entry  routing  handlers)",
            "",
            "warning:   Explain IDEAS and PATTERNS. Do not reproduce code verbatim.",
        ]
    )
    chapters: list[dict[str, str]] = [
        make_chapter("prompt", "Analysis prompt", "prompt", prompt_body),
        make_chapter(
            "overview",
            f"{owner}/{repo}@{branch}",
            "overview",
            f"Repository: {owner}/{repo}\nBranch: {branch}\nSource files in scope: {len(all_paths)}",
        ),
        make_chapter(
            "tree",
            f"Directory structure ({len(all_paths)} files)",
            "tree",
            structure_slice + more_note,
        ),
    ]
    if readme:
        chapters.append(make_chapter("readme", "README", "readme", readme))
    for manifest_path, manifest_body in manifest_entries:
        kind_label = "manifest" if manifest_entries[-1][0] == manifest_path else "manifest-secondary"
        chapters.append(make_chapter(f"manifest-{manifest_path}", manifest_path, kind_label, manifest_body))
    for path, body in source_blocks:
        chapters.append(make_chapter(f"source-{path}", path, "source", body))
    if not source_blocks:
        chapters.append(
            make_chapter(
                "source-empty",
                "Key source code",
                "hint",
                "_Could not load key files. Use inspire_repo(operation=files) with target_files._",
            )
        )

    manifest_block = ""
    for manifest_path, manifest_body in manifest_entries:
        manifest_block += f"\n {manifest_path} \n{manifest_body}\n END {manifest_path} \n"
    source_block = ""
    for path, body in source_blocks:
        source_block += f"\n {path} \n{body}\n END {path} \n"

    sections = [prompt_body, "", "---", "", f"## Repository: {owner}/{repo} (branch: {branch})", ""]
    sections.extend(
        [
            f"### Directory Structure ({len(all_paths)} source files)",
            "",
            structure_slice + more_note,
        ]
    )
    if readme:
        sections.extend(["", "### Project README", "", readme])
    if manifest_block:
        sections.extend(["", "### Project Manifests", manifest_block])
    sections.extend(
        [
            "",
            "### Key Source Code",
            "",
            "Auto-selected architecturally significant files:",
            "",
            source_block or "_Could not load key files._",
        ]
    )
    text = "\n".join(sections)
    return chapters, text


def compose_files_chapters(
    owner: str,
    repo: str,
    branch: str,
    file_paths: list[str],
    file_contents: list[tuple[str, str | None, str | None]],
    limits: ProfileLimits,
) -> tuple[list[dict[str, str]], str]:
    overview = "\n".join(
        [
            f"[repo]  {owner}/{repo}  (branch: {branch})",
            f"[dir]  Fetching {len(file_paths)} file(s)  inspiration context only",
            "" * 60,
        ]
    )
    chapters: list[dict[str, str]] = [
        make_chapter("overview", f"{owner}/{repo}", "overview", overview),
    ]
    for path, content, err in file_contents:
        if err:
            chapters.append(make_chapter(f"err-{path}", path, "hint", f"warning:   Could not fetch {path}: {err}"))
            continue
        if content:
            body = truncate_content(content, limits.per_file_chars, "... [file truncated  too large]")
            chapters.append(make_chapter(f"file-{path}", path, "file", body))

    text = build_files_text(
        owner,
        repo,
        branch,
        file_paths,
        [(p, truncate_content(c, limits.per_file_chars) if c else None, e) for p, c, e in file_contents],
    )
    if limits.total_chars < 80_000:
        if len(text) > limits.total_chars:
            text = text[: limits.total_chars] + "\n\nwarning:   Output capped by profile max_chars budget."
    return chapters, text


INSPIRE_REPO_HELP = """# inspire_repo  GitHub inspiration (no clone)

**Operations:** `structure` | `files` | `patterns` | `help` (multi-step: `inspire_repo_workflow`)

| Param | Description |
|-------|-------------|
| url | `https://github.com/owner/repo` or `github.com/o/r` |
| operation | What to fetch |
| subpath | Limit to folder (e.g. `src`) |
| branch | Override branch (else URL `/tree/branch` or default) |
| profile | `brief` \\| `standard` \\| `deep`  output size |
| target_files | For `files`: explicit paths |
| max_chars | Optional cap (overrides profile total_chars when lower) |
| language_hint | Boost auto-pick for language (e.g. `python`, `typescript`) |
| include_globs | Only paths matching globs |
| exclude_globs | Drop paths matching globs |

**Legacy aliases:** inspire_repo_structure, inspire_repo_files, inspire_repo_patterns

**Response:** `data.text` (compat) + `data.chapters[]` with `{id, title, kind, body}`.

Kinds: overview, tree, manifest, readme, source, prompt, file, hint.

Credit: workflow adapted from Repomuse (MIT, praveene3127).
"""
