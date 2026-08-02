"""GitHub remote repo inspiration  filtered trees and token-safe file fetches."""

from __future__ import annotations

import fnmatch
import os
import shutil
import subprocess
from dataclasses import dataclass
from typing import Any
from urllib.parse import unquote, urlparse

MAX_STRUCTURE_FILES = 500
MAX_AUTO_FILES = 10
MAX_EXPLICIT_FILES = 15
TOTAL_CHARS_LIMIT = 80_000
PER_FILE_CHARS_LIMIT = 25_000
SUMMARIZE_STRUCTURE_LINES = 300
SUMMARIZE_SOURCE_CHAR_BUDGET = 50_000

MANIFEST_NAMES = frozenset(
    {
        "package.json",
        "pyproject.toml",
        "setup.py",
        "cargo.toml",
        "go.mod",
        "gemfile",
        "build.gradle",
        "pom.xml",
    }
)

DEFAULT_IGNORES: tuple[str, ...] = (
    ".git",
    "node_modules",
    "bower_components",
    "vendor",
    "venv",
    ".venv",
    "env",
    ".env",
    "dist",
    "build",
    "out",
    ".next",
    ".nuxt",
    ".vuepress",
    ".svelte-kit",
    ".cache",
    ".sass-cache",
    ".parcel-cache",
    "coverage",
    ".nyc_output",
    "__pycache__",
    "*.egg-info",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    "target",
    ".idea",
    ".vscode",
    ".fleet",
    "*.swp",
    "*.swo",
    "*~",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "bun.lockb",
    "Cargo.lock",
    "Gemfile.lock",
    "poetry.lock",
    "composer.lock",
    "uv.lock",
    "go.sum",
    "*.jpg",
    "*.jpeg",
    "*.png",
    "*.gif",
    "*.ico",
    "*.bmp",
    "*.webp",
    "*.svg",
    "*.mp4",
    "*.mov",
    "*.webm",
    "*.avi",
    "*.mkv",
    "*.mp3",
    "*.wav",
    "*.ogg",
    "*.flac",
    "*.ttf",
    "*.otf",
    "*.woff",
    "*.woff2",
    "*.eot",
    "*.zip",
    "*.tar",
    "*.gz",
    "*.rar",
    "*.7z",
    "*.exe",
    "*.dll",
    "*.so",
    "*.dylib",
    "*.bin",
    "*.dat",
    "*.pyc",
    "*.pyo",
    "*.class",
    "*.jar",
    "*.war",
    "*.o",
    "*.a",
    "*.lib",
    "*.wasm",
    "*.log",
    "*.min.js",
    "*.min.css",
    "*.map",
    "CHANGELOG.md",
    "CHANGELOG",
    "CHANGELOG.rst",
    "LICENSE",
    "LICENSE.md",
    "LICENSE.txt",
    "NOTICE",
    "__tests__",
    "__snapshots__",
    "test",
    "tests",
    "fixtures",
    "*.test.ts",
    "*.spec.ts",
    "*.test.tsx",
    "*.spec.tsx",
    "*.test.js",
    "*.spec.js",
    "*.test.jsx",
    "*.spec.jsx",
    "*.test.py",
    "*_test.go",
    "*_test.rs",
    "conftest.py",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    ".github",
    ".circleci",
    ".travis.yml",
    ".DS_Store",
    "Thumbs.db",
    ".editorconfig",
    ".prettierrc",
    ".prettierrc.*",
    ".eslintrc",
    ".eslintrc.*",
    "eslint.config.*",
    ".prettierignore",
    ".eslintignore",
    ".gitattributes",
    ".npmignore",
    ".npmrc",
    ".nvmrc",
    ".node-version",
    ".python-version",
    ".tool-versions",
)

CODE_EXTENSIONS = frozenset(
    {
        ".ts",
        ".tsx",
        ".js",
        ".jsx",
        ".mjs",
        ".cjs",
        ".py",
        ".pyx",
        ".go",
        ".rs",
        ".java",
        ".kt",
        ".kts",
        ".scala",
        ".rb",
        ".erb",
        ".cs",
        ".fs",
        ".c",
        ".cpp",
        ".cc",
        ".h",
        ".hpp",
        ".swift",
        ".lua",
        ".ex",
        ".exs",
        ".clj",
        ".cljs",
        ".zig",
        ".dart",
        ".vue",
        ".svelte",
        ".php",
    }
)


@dataclass(frozen=True)
class RepoRef:
    owner: str
    repo: str
    branch: str | None = None


def parse_github_url(raw_url: str) -> RepoRef | None:
    """Parse github.com owner/repo URLs (optional /tree/branch)."""
    raw = (raw_url or "").strip()
    if not raw:
        return None
    if not raw.startswith("http"):
        raw = f"https://{raw}"
    try:
        parsed = urlparse(raw)
    except ValueError:
        return None
    host = (parsed.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    if host != "github.com":
        return None
    parts = [p for p in parsed.path.strip("/").split("/") if p]
    if len(parts) < 2:
        return None
    owner, repo = parts[0], parts[1]
    branch: str | None = None
    if len(parts) >= 4 and parts[2] == "tree":
        branch = unquote(parts[3])
    return RepoRef(owner=owner, repo=repo.removesuffix(".git"), branch=branch)


def github_auth_token() -> str | None:
    """Resolve GitHub token from env or gh CLI (does not override env with invalid tokens)."""
    for key in ("GITHUB_TOKEN", "GH_TOKEN"):
        val = (os.environ.get(key) or "").strip()
        if val:
            return val
    gh_path = shutil.which("gh")
    if not gh_path:
        return None
    try:
        proc = subprocess.run(
            [gh_path, "auth", "token"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    except (subprocess.TimeoutExpired, OSError):
        pass
    return None


def should_ignore(path: str, extra: list[str] | None = None) -> bool:
    """Return True if path matches inspiration noise filters."""
    normalized = path.replace("\\", "/").lstrip("/")
    if not normalized:
        return False
    parts = normalized.split("/")
    basename = parts[-1]
    patterns = list(DEFAULT_IGNORES) + (extra or [])
    for pattern in patterns:
        if pattern.startswith("*"):
            if fnmatch.fnmatch(basename, pattern) or fnmatch.fnmatch(normalized, pattern):
                return True
        elif pattern in parts or basename == pattern:
            return True
        elif fnmatch.fnmatch(normalized, pattern):
            return True
    return False


_LANGUAGE_HINT_EXTENSIONS: dict[str, str] = {
    "python": ".py",
    "typescript": ".ts",
    "javascript": ".js",
    "go": ".go",
    "rust": ".rs",
    "java": ".java",
    "kotlin": ".kt",
    "csharp": ".cs",
    "ruby": ".rb",
    "php": ".php",
    "swift": ".swift",
    "scala": ".scala",
    "lua": ".lua",
}


def _extension_for_language_hint(hint: str) -> str | None:
    key = hint.strip().lower().lstrip(".")
    if not key:
        return None
    if key in _LANGUAGE_HINT_EXTENSIONS:
        return _LANGUAGE_HINT_EXTENSIONS[key]
    if key.startswith("."):
        return key
    return f".{key}"


def score_file(path: str, language_hint: str | None = None) -> int:
    """Rank paths for smart auto-selection (higher = more architecturally relevant)."""
    lower = path.lower()
    parts = lower.split("/")
    filename = parts[-1] if parts else ""
    ext = f".{filename.rsplit('.', 1)[-1]}" if "." in filename else ""
    score = 50 if ext in CODE_EXTENSIONS else 5
    core_dirs = {
        "src",
        "lib",
        "core",
        "pkg",
        "internal",
        "app",
        "server",
        "api",
        "routes",
        "middleware",
        "services",
        "models",
        "controllers",
        "handlers",
        "utils",
        "helpers",
    }
    if any(p in core_dirs for p in parts):
        score += 30
    entry_names = {
        "index",
        "main",
        "app",
        "server",
        "mod",
        "lib",
        "router",
        "routes",
        "middleware",
        "handler",
        "controller",
        "service",
        "model",
        "schema",
        "config",
        "database",
        "db",
    }
    base_name = filename.rsplit(".", 1)[0] if "." in filename else filename
    if base_name in entry_names:
        score += 25
    depth = len(parts)
    if depth == 1:
        score += 15
    elif depth == 2:
        score += 12
    elif depth == 3:
        score += 8
    else:
        score += max(0, 5 - depth)
    low_value_dirs = {
        "examples",
        "example",
        "samples",
        "sample",
        "demo",
        "demos",
        "docs",
        "documentation",
        "scripts",
        "bin",
    }
    if any(p in low_value_dirs for p in parts):
        score -= 30
    if ext in {".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env"} and base_name not in entry_names:
        score -= 20
    if language_hint:
        want = _extension_for_language_hint(language_hint)
        if want and lower.endswith(want):
            score += 40
    return score


def smart_pick_files(paths: list[str], count: int, language_hint: str | None = None) -> list[str]:
    ranked = sorted(
        ((p, score_file(p, language_hint)) for p in paths),
        key=lambda x: x[1],
        reverse=True,
    )
    return [p for p, _ in ranked[:count]]


def render_tree(paths: list[str]) -> str:
    sorted_paths = sorted(paths)
    lines: list[str] = []
    prev_parts: list[str] = []
    for p in sorted_paths:
        parts = p.split("/")
        depth = len(parts) - 1
        common = 0
        while common < len(prev_parts) and common < depth and prev_parts[common] == parts[common]:
            common += 1
        for i in range(common, depth):
            lines.append("  " * i + f"[dir]  {parts[i]}/")
        lines.append("  " * depth + f"[file]  {parts[-1]}")
        prev_parts = parts[:depth]
    return "\n".join(lines)


def filter_blob_paths(tree: list[dict[str, Any]], extra_ignores: list[str] | None = None) -> list[str]:
    paths: list[str] = []
    for item in tree:
        if item.get("type") != "blob":
            continue
        path = item.get("path") or ""
        if path and not should_ignore(path, extra_ignores):
            paths.append(path)
    return paths


def match_target_files(all_paths: list[str], target_files: list[str]) -> list[str]:
    matched: list[str] = []
    for item_path in all_paths:
        for target in target_files:
            t_norm = target.replace("\\", "/").lstrip("/")
            if item_path == t_norm or item_path.endswith(f"/{t_norm}"):
                matched.append(item_path)
                break
    return matched


def truncate_content(content: str, limit: int, note: str = "... [truncated]") -> str:
    if len(content) <= limit:
        return content
    return content[:limit] + f"\n\n{note}"


def api_error_message(status: int, context: str) -> str:
    if status in (401, 403):
        return (
            f"{context}: GitHub API access denied ({status}). "
            "Private repos need a valid token (GITHUB_TOKEN, GH_TOKEN, or gh auth login)."
        )
    if status == 404:
        return f"{context}: Repository not found (404). Check the URL and visibility."
    if status == 429:
        return f"{context}: GitHub API rate limit (429). Set GITHUB_TOKEN or run gh auth login."
    return f"{context}: GitHub API returned HTTP {status}."


def build_structure_text(owner: str, repo: str, branch: str, paths: list[str], total_files: int) -> str:
    shown = paths[:MAX_STRUCTURE_FILES]
    trunc_note = ""
    if total_files > MAX_STRUCTURE_FILES:
        trunc_note = (
            f"\nwarning:   Showing {MAX_STRUCTURE_FILES} of {total_files} files. "
            "Use inspire_repo_files with target_files for specific paths.\n"
        )
    return "\n".join(
        [
            f"[repo]  Repository: {owner}/{repo}  (branch: {branch})",
            f"files:  {len(shown)} source files"
            + (f" ({total_files} total)" if total_files > MAX_STRUCTURE_FILES else ""),
            trunc_note,
            "" * 60,
            render_tree(shown),
            "" * 60,
            "",
            "tip:  Next steps:",
            "   inspire_repo_files  read source for specific paths (or auto-pick core files)",
            "   inspire_repo_patterns  structure + manifests + key files for architecture study",
            "",
            "warning:   Read to understand patterns  adapt ideas; do not copy verbatim.",
        ]
    )


def build_files_text(
    owner: str,
    repo: str,
    branch: str,
    file_paths: list[str],
    file_contents: list[tuple[str, str | None, str | None]],
) -> str:
    parts = [
        f"[repo]  {owner}/{repo}  (branch: {branch})",
        f"[dir]  Fetching {len(file_paths)} file(s)  inspiration context only",
        "" * 60,
    ]
    total_chars = 0
    truncated_early = False
    for path, content, err in file_contents:
        if err:
            parts.append(f"warning:   Could not fetch {path}: {err}")
            continue
        if not content:
            continue
        body = truncate_content(content, PER_FILE_CHARS_LIMIT, "... [file truncated  too large]")
        parts.extend(["", f" FILE: {path} ", "", body, "", f" END: {path} "])
        total_chars += len(body)
        if total_chars > TOTAL_CHARS_LIMIT:
            truncated_early = True
            break
    if truncated_early:
        parts.append("")
        parts.append("warning:   Output stopped early (token budget). Request fewer or more specific target_files.")
    parts.extend(["", "" * 60, "tip:  Use as design inspiration  understand patterns; do not copy verbatim."])
    return "\n".join(parts)


def build_patterns_text(
    owner: str,
    repo: str,
    branch: str,
    all_paths: list[str],
    readme: str,
    manifest_block: str,
    source_block: str,
) -> str:
    structure_slice = "\n".join(all_paths[:SUMMARIZE_STRUCTURE_LINES])
    more_note = ""
    if len(all_paths) > SUMMARIZE_STRUCTURE_LINES:
        more_note = f"\n... and {len(all_paths) - SUMMARIZE_STRUCTURE_LINES} more files"
    sections = [
        "# MetaMCP  Architecture & Pattern Analysis (inspiration)",
        "",
        f"You are analyzing **{owner}/{repo}** as a reference for inspiration.",
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
        "",
        "---",
        "",
        f"## Repository: {owner}/{repo} (branch: {branch})",
        "",
        f"### Directory Structure ({len(all_paths)} source files)",
        "",
        structure_slice + more_note,
    ]
    if readme:
        sections.extend(["", "### Project README", "", readme])
    if manifest_block:
        sections.extend(["", "### Project Manifest", manifest_block])
    sections.extend(
        [
            "",
            "### Key Source Code",
            "",
            "Auto-selected architecturally significant files:",
            "",
            source_block or "_Could not load key files. Use inspire_repo_files with target_files._",
        ]
    )
    return "\n".join(sections)
