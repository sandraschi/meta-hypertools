"""Curated catalog of fleet operation scripts for the Fleet Ops UI.

Each entry encodes the script's parameters as a form schema so users never
need to remember CLI syntax. The UI renders the form, POSTs the values, and
the backend builds the argv via the entry's build_args function.

Add a script = add one entry (params + build_args). Command previews are
generated from the same builder, so the UI always shows the exact command
it is about to run.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any

from meta_mcp.fleet_paths import repos_root


def _which(*candidates: str, fallback: str = "") -> str:
    for name in candidates:
        found = shutil.which(name)
        if found:
            return found
    for path in candidates:
        if Path(path).is_file():
            return path
    return fallback


UV = _which("uv", r"C:\Users\sandr\.local\bin\uv.exe", fallback="uv")
PWSH = "powershell.exe"
JUST = _which("just", r"C:\Users\scoop\shims\just.exe", fallback="just")


def meta_mcp_root() -> Path:
    """Root directory of meta_mcp repository."""
    return Path(__file__).resolve().parents[2]


def mcd_root() -> Path:
    """mcp-central-docs handbook: env override, then repos/mcp-central-docs."""
    raw = os.environ.get("MCP_CENTRAL_DOCS_ROOT", "").strip()
    if raw:
        path = Path(raw).expanduser()
        if path.is_dir():
            return path
    candidate = repos_root() / "mcp-central-docs"
    if candidate.is_dir():
        return candidate
    # Fallback to current repository if mcp-central-docs is not available
    return meta_mcp_root()


def _sweep_args(params: dict[str, Any]) -> list[str]:
    args: list[str] = []
    filt = str(params.get("filter", "") or "").strip()
    if filt:
        args += ["--filter", filt]
    level = str(params.get("level", "A") or "A")
    args += ["--level", level]
    try:
        workers = max(1, min(16, int(params.get("workers", 4) or 4)))
    except (TypeError, ValueError):
        workers = 4
    args += ["--workers", str(workers)]
    keep = str(params.get("keep", "") or "").strip()
    if keep:
        args += ["--keep", keep]
    if params.get("no_keep"):
        args += ["--no-keep"]
    return args


def _probe_args(params: dict[str, Any]) -> list[str]:
    args: list[str] = []
    if params.get("broken_only"):
        args += ["-BrokenOnly"]
    filt = str(params.get("filter", "") or "").strip()
    if filt:
        args += ["-RepoFilter", filt]
    return args


def _smoke_args(params: dict[str, Any]) -> list[str]:
    args: list[str] = []
    filt = str(params.get("filter", "") or "").strip()
    if filt:
        args += ["-RepoFilter", filt]
    return args


def _cold_install_args(params: dict[str, Any]) -> list[str]:
    return _probe_args(params)


def _freeform_args(params: dict[str, Any]) -> list[str]:
    raw = str(params.get("recipe", "") or "").strip()
    return [] if not raw else raw.split()


def _watchdog_args(params: dict[str, Any]) -> list[str]:
    cmd = str(params.get("command", "scan") or "scan")
    args = [cmd]
    ide = str(params.get("ide", "claude") or "claude")
    args += ["--ide", ide]
    filt = str(params.get("filter", "") or "").strip()
    if filt:
        args += ["--filter", filt]
    try:
        stale = int(params.get("stale", 60) or 60)
        args += ["--stale", str(stale)]
    except (TypeError, ValueError):
        pass
    try:
        hung = int(params.get("hung_timeout", 300) or 300)
        args += ["--hung-timeout", str(hung)]
    except (TypeError, ValueError):
        pass
    if params.get("kill"):
        args += ["--kill"]
    if params.get("json"):
        args += ["--json"]
    return args


def _standards_args(params: dict[str, Any]) -> list[str]:
    args: list[str] = []
    repo = str(params.get("repo_path", ".") or ".").strip()
    args += ["-RepoPath", repo]
    if params.get("check_all", True):
        args += ["-CheckAll"]
    return args


def _swapper_args(params: dict[str, Any]) -> list[str]:
    args: list[str] = []
    tier = str(params.get("tier", "tier1") or "tier1").strip()
    if tier:
        args.append(tier)
    if params.get("dry_run"):
        args.append("--dry-run")
    return args


def _codemod_args(params: dict[str, Any]) -> list[str]:
    mode = str(params.get("mode", "fleet") or "fleet")
    if mode == "fleet":
        return ["--fleet"]
    repo = str(params.get("repo", "meta_mcp") or "meta_mcp").strip()
    return ["--repo", repo] if repo else ["--fleet"]


def _empty_args(params: dict[str, Any]) -> list[str]:
    return []


CATALOG: list[dict[str, Any]] = [
    {
        "id": "webapp-sweep",
        "name": "Fleet Webapp Sweep",
        "category": "Fleet Ops & Probes",
        "description": (
            "Cold-start + headless browser click-through per repo: backend health, frontend, "
            "connected badge, sidebar nav walk with screenshots, diagnostics. Token-lean, "
            "deterministic; report in scripts/out/fleet-webapp-sweep-*.{json,md}. Teardown is "
            "mandatory for non-keep repos; keep_running from the config stays up."
        ),
        "cwd": "mcd",
        "argv": [
            UV,
            "run",
            "--with",
            "playwright",
            "--with",
            "httpx",
            "--quiet",
            "python",
            "scripts/fleet-webapp-sweep.py",
        ],
        "build_args": _sweep_args,
        "danger": "Starts and tears down webapp stacks fleet-wide (kept repos stay up).",
        "params": [
            {
                "name": "filter",
                "label": "Repo filter",
                "kind": "text",
                "default": "",
                "placeholder": "e.g. chitchat - empty runs all repos",
                "hint": "Substring match on repo name",
            },
            {
                "name": "level",
                "label": "Level",
                "kind": "select",
                "default": "A",
                "options": [
                    {"value": "A", "label": "A - headless DOM (fast, default)"},
                    {"value": "B", "label": "B - CUA + Tesseract clickthrough"},
                ],
                "hint": "Level B delegates to the repo's own cua-webapp-test.py",
            },
            {
                "name": "workers",
                "label": "Workers",
                "kind": "number",
                "default": "4",
                "hint": "Parallel repos (1-16); CPU/OCR bound, keep low",
            },
            {
                "name": "keep",
                "label": "Keep running",
                "kind": "text",
                "default": "",
                "placeholder": "repo1,repo2 - empty uses config keep_running",
                "hint": "Comma list; these stacks stay up after the run",
            },
            {
                "name": "no_keep",
                "label": "Tear down everything",
                "kind": "bool",
                "default": False,
                "hint": "Kill previously kept stacks too; nothing left running",
            },
        ],
    },
    {
        "id": "startup-probe",
        "name": "Fleet Startup Probe (HTTP)",
        "category": "Fleet Ops & Probes",
        "description": (
            "Parse-check start.ps1, start each stack, probe backend + frontend + Vite proxy, "
            "analyze dirty logs, teardown. Report: scripts/out/fleet-webapp-report.{json,md}. "
            "Faster than the sweep (no browser) - good first triage."
        ),
        "cwd": "mcd",
        "argv": [PWSH, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts/fleet-webapp-start-probe.ps1"],
        "build_args": _probe_args,
        "danger": "Starts and tears down webapp stacks fleet-wide.",
        "params": [
            {
                "name": "filter",
                "label": "Repo filter",
                "kind": "text",
                "default": "",
                "placeholder": "e.g. arxiv-mcp - empty runs all",
                "hint": "Repo name or wildcard like a*",
            },
            {
                "name": "broken_only",
                "label": "Broken only",
                "kind": "bool",
                "default": False,
                "hint": "Re-probe only repos that failed the last run",
            },
        ],
    },
    {
        "id": "basic-smoke-all",
        "name": "Fleet Basic Smoke (all repos)",
        "category": "Fleet Ops & Probes",
        "description": (
            "Sequential HTTP smoke across every manifest repo: start backend+webapp, health "
            "check, kill, next. No browser, no OCR - the fastest full-fleet pass/fail."
        ),
        "cwd": "mcd",
        "argv": [PWSH, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts/fleet-basic-smoke-all.ps1"],
        "build_args": _smoke_args,
        "danger": "Starts and tears down every stack in sequence.",
        "params": [
            {
                "name": "filter",
                "label": "Repo filter",
                "kind": "text",
                "default": "",
                "placeholder": "optional single repo",
                "hint": "Run one repo only",
            },
        ],
    },
    {
        "id": "cold-install-probe",
        "name": "Fleet Cold-Install Probe",
        "category": "Fleet Ops & Probes",
        "description": (
            "Validates naked-PC installability: INSTALL.md preflight, optional mcpb bundle + "
            "multi-IDE stdio smoke. Report: scripts/out/fleet-cold-install-report.{json,md}."
        ),
        "cwd": "mcd",
        "argv": [PWSH, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts/fleet-cold-install-probe.ps1"],
        "build_args": _cold_install_args,
        "danger": "",
        "params": [
            {
                "name": "filter",
                "label": "Repo filter",
                "kind": "text",
                "default": "",
                "placeholder": "optional single repo",
                "hint": "Repo name",
            },
            {
                "name": "broken_only",
                "label": "Broken only",
                "kind": "bool",
                "default": False,
                "hint": "Re-probe failed repos only",
            },
        ],
    },
    {
        "id": "mcp-watchdog",
        "name": "MCP Server Watchdog",
        "category": "Diagnostics & Health",
        "description": (
            "Scans, inspects, and troubleshoots IDE MCP server log files for hangs, crashes, and stale sessions."
        ),
        "cwd": "meta_mcp",
        "argv": [UV, "run", "python", "scripts/mcp-watchdog.py"],
        "build_args": _watchdog_args,
        "danger": "",
        "params": [
            {
                "name": "command",
                "label": "Action",
                "kind": "select",
                "default": "scan",
                "options": [
                    {"value": "scan", "label": "scan - Quick status check on all logs"},
                    {"value": "watch", "label": "watch - Real-time tail and alerting"},
                    {"value": "tail", "label": "tail - Stream logs for single server"},
                    {"value": "clean", "label": "clean - Remove empty and dead log files"},
                    {"value": "rotate", "label": "rotate - Archive large log files"},
                    {"value": "purge", "label": "purge - Delete stale logs"},
                ],
                "hint": "Watchdog operation mode",
            },
            {
                "name": "ide",
                "label": "Target IDE",
                "kind": "select",
                "default": "claude",
                "options": [
                    {"value": "claude", "label": "Claude Desktop"},
                    {"value": "antigravity", "label": "Antigravity"},
                    {"value": "cursor", "label": "Cursor"},
                    {"value": "windsurf", "label": "Windsurf"},
                    {"value": "zed", "label": "Zed"},
                    {"value": "opencode", "label": "OpenCode"},
                ],
                "hint": "Target client environment",
            },
            {
                "name": "filter",
                "label": "Status filter",
                "kind": "text",
                "default": "",
                "placeholder": "e.g. HUNG,CRASHED",
                "hint": "Comma-separated status filter (OK, STALE, HUNG, CRASHED, EMPTY)",
            },
            {
                "name": "stale",
                "label": "Stale threshold (mins)",
                "kind": "number",
                "default": "60",
                "hint": "Minutes since last log write to consider stale",
            },
            {
                "name": "kill",
                "label": "Auto-kill hung processes",
                "kind": "bool",
                "default": False,
                "hint": "Kill processes identified as hung",
            },
        ],
    },
    {
        "id": "check-repo-standards",
        "name": "Check Repo Standards (SOTA)",
        "category": "Repository Standards",
        "description": (
            "Validates repository compliance with SOTA standards "
            "(pyproject, justfile, AGENTS.md, gitignore, webapp setup)."
        ),
        "cwd": "meta_mcp",
        "argv": [PWSH, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts/check-repo-standards.ps1"],
        "build_args": _standards_args,
        "danger": "",
        "params": [
            {
                "name": "repo_path",
                "label": "Repository Path",
                "kind": "text",
                "default": ".",
                "placeholder": "e.g. . or D:\\Dev\\repos\\calibre-mcp",
                "hint": "Path to the repository to validate",
            },
            {
                "name": "check_all",
                "label": "Run all checks",
                "kind": "bool",
                "default": True,
                "hint": "Execute complete verification suite",
            },
        ],
    },
    {
        "id": "audit-uv",
        "name": "Audit Fleet uv Setup",
        "category": "Package & Tool Management",
        "description": "Audits all MCP repositories for uv.lock, pyproject.toml, and virtual environment compliance.",
        "cwd": "meta_mcp",
        "argv": [UV, "run", "python", "scripts/audit_uv.py"],
        "build_args": _empty_args,
        "danger": "",
        "params": [],
    },
    {
        "id": "autofix-uv",
        "name": "Auto-Fix Fleet uv Setup",
        "category": "Package & Tool Management",
        "description": "Runs uv lock and uv sync across repositories with missing locks.",
        "cwd": "meta_mcp",
        "argv": [UV, "run", "python", "scripts/autofix_uv.py"],
        "build_args": _empty_args,
        "danger": "Executes uv lock and sync across repositories.",
        "params": [],
    },
    {
        "id": "mcp-swapper",
        "name": "MCP Swapper (Tier Switcher)",
        "category": "Package & Tool Management",
        "description": "Activates or deactivates MCP server tiers in Antigravity client configuration.",
        "cwd": "meta_mcp",
        "argv": [UV, "run", "python", "scripts/mcp-swapper.py"],
        "build_args": _swapper_args,
        "danger": "Modifies active MCP servers in Antigravity mcp_config.json.",
        "params": [
            {
                "name": "tier",
                "label": "Target Tier",
                "kind": "select",
                "default": "tier1",
                "options": [
                    {"value": "tier1", "label": "Tier 1 - Core & High Priority Tools"},
                    {"value": "tier2", "label": "Tier 2 - Media, Home & Extended Tools"},
                    {"value": "tier3", "label": "Tier 3 - Heavy 3D/VR Tools"},
                    {"value": "all", "label": "All - Enable All Configured Servers"},
                ],
                "hint": "Tier of MCP servers to activate",
            },
            {
                "name": "dry_run",
                "label": "Dry Run",
                "kind": "bool",
                "default": False,
                "hint": "Preview changes without modifying config file",
            },
        ],
    },
    {
        "id": "repo-stats",
        "name": "Repository & MCP Tools Stats",
        "category": "Diagnostics & Health",
        "description": "Calculates fleet size, tool counts, languages, and lines of code across fleet servers.",
        "cwd": "meta_mcp",
        "argv": [UV, "run", "python", "scripts/repo_stats.py"],
        "build_args": _empty_args,
        "danger": "",
        "params": [],
    },
    {
        "id": "kill-zombies",
        "name": "Kill Port Squatters & Stale Workers",
        "category": "Fleet Ops & Maintenance",
        "description": "Safely terminates orphaned background workers and frees occupied meta-mcp ports (10718/10719).",
        "cwd": "meta_mcp",
        "argv": [PWSH, "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", "scripts/kill-zombies.ps1"],
        "build_args": _empty_args,
        "danger": "Terminates stale meta-mcp processes and squatting ports.",
        "params": [],
    },
    {
        "id": "codemod-annotations",
        "name": "Codemod FastMCP Annotations",
        "category": "Repository Standards",
        "description": (
            "Applies standard readOnlyHint, destructiveHint, and idempotentHint annotations to FastMCP tools."
        ),
        "cwd": "meta_mcp",
        "argv": [UV, "run", "python", "scripts/codemod_annotations.py"],
        "build_args": _codemod_args,
        "danger": "Edits Python source code in target repository or fleet-wide.",
        "params": [
            {
                "name": "mode",
                "label": "Scope",
                "kind": "select",
                "default": "single_repo",
                "options": [
                    {"value": "single_repo", "label": "Single Repository"},
                    {"value": "fleet", "label": "Fleet-wide (all repos)"},
                ],
                "hint": "Scope of annotation codemod",
            },
            {
                "name": "repo",
                "label": "Repository Name",
                "kind": "text",
                "default": "meta_mcp",
                "placeholder": "e.g. meta_mcp or calibre-mcp",
                "hint": "Target repository if single repo mode",
            },
        ],
    },
    {
        "id": "just-recipe",
        "name": "Run a just recipe",
        "category": "Fleet Ops & Probes",
        "description": "Freeform just runner against the mcp-central-docs justfile (recipes, not shell).",
        "cwd": "mcd",
        "argv": [JUST],
        "build_args": _freeform_args,
        "danger": "",
        "params": [
            {
                "name": "recipe",
                "label": "Recipe + args",
                "kind": "text",
                "default": "",
                "placeholder": "e.g. fleet-webapp-sweep chitchat",
                "hint": "Exactly as typed at the terminal",
            },
        ],
    },
]

_CATALOG_BY_ID = {entry["id"]: entry for entry in CATALOG}


def get_script(script_id: str) -> dict[str, Any] | None:
    return _CATALOG_BY_ID.get(script_id)


def build_argv(script_id: str, params: dict[str, Any]) -> list[str]:
    entry = get_script(script_id)
    if entry is None:
        raise KeyError(script_id)
    return [*entry["argv"], *entry["build_args"](params)]


def command_preview(script_id: str, params: dict[str, Any]) -> str:
    argv = build_argv(script_id, params)
    return " ".join(f'"{a}"' if " " in a else a for a in argv)


def catalog_dicts() -> list[dict[str, Any]]:
    """Catalog serialized for the UI: params only, build_args stays server-side."""
    out: list[dict[str, Any]] = []
    for entry in CATALOG:
        out.append(
            {
                "id": entry["id"],
                "name": entry["name"],
                "category": entry.get("category", "Fleet Ops & Probes"),
                "description": entry["description"],
                "cwd": entry["cwd"],
                "params": entry["params"],
                "danger": entry.get("danger", ""),
            }
        )
    return out
