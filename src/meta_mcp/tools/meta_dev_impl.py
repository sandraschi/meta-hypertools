"""Implementations for meta_dev fleet / tooling helpers."""

from __future__ import annotations

import difflib
import json
import os
import re
import time
from pathlib import Path
from typing import Any

import aiohttp

from meta_mcp.fleet_paths import fleet_registry_path, master_mcp_config_path


def _fleet_registry_path(central_docs_root: str | None) -> Path:
    if central_docs_root:
        candidate = Path(central_docs_root) / "operations" / "fleet-registry.json"
        if candidate.is_file():
            return candidate
    return fleet_registry_path()


def _master_config_path() -> Path:
    return master_mcp_config_path()


async def probe_fleet_health_impl(
    central_docs_root: str | None,
    timeout_sec: float,
    max_checks: int,
) -> dict[str, Any]:
    """HTTP GET /health for each fleet entry that has a port."""
    reg_path = _fleet_registry_path(central_docs_root)
    if not reg_path.is_file():
        return {"success": False, "message": "Operation failed", "error": f"fleet-registry not found: {reg_path}"}

    try:
        data = json.loads(reg_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return {"success": False, "message": "Operation failed", "error": f"Invalid JSON in {reg_path}: {e}"}

    fleet = data.get("fleet") if isinstance(data, dict) else None
    if fleet is None and isinstance(data, list):
        fleet = data
    if not isinstance(fleet, list):
        return {
            "success": False,
            "error": "Unexpected fleet-registry shape (expected fleet array).",
        }

    results: list[dict[str, Any]] = []
    timeout = aiohttp.ClientTimeout(total=timeout_sec)
    checked = 0

    async with aiohttp.ClientSession(timeout=timeout) as session:
        for entry in fleet[:max_checks]:
            if not isinstance(entry, dict):
                continue
            port = entry.get("port")
            if port is None:
                continue
            try:
                p = int(port)
            except (TypeError, ValueError):
                continue
            url = f"http://127.0.0.1:{p}/health"
            t0 = time.perf_counter()
            try:
                async with session.get(url) as resp:
                    elapsed_ms = (time.perf_counter() - t0) * 1000
                    checked += 1
                    body_preview = ""
                    try:
                        text = await resp.text()
                        body_preview = text[:500]
                    except Exception:
                        pass
                    results.append(
                        {
                            "id": entry.get("id"),
                            "port": p,
                            "url": url,
                            "status": resp.status,
                            "ok": 200 <= resp.status < 300,
                            "elapsed_ms": round(elapsed_ms, 2),
                            "body_preview": body_preview,
                        }
                    )
            except Exception as e:
                elapsed_ms = (time.perf_counter() - t0) * 1000
                checked += 1
                results.append(
                    {
                        "id": entry.get("id"),
                        "port": p,
                        "url": url,
                        "status": None,
                        "ok": False,
                        "elapsed_ms": round(elapsed_ms, 2),
                        "error": str(e),
                    }
                )

    up = sum(1 for r in results if r.get("ok"))
    return {
        "success": True,
        "registry": str(reg_path),
        "checked": checked,
        "reachable": up,
        "results": results,
    }


def diff_mcp_configs_impl(path_a: str, path_b: str) -> dict[str, Any]:
    """Unified diff of two JSON files."""
    pa, pb = Path(path_a), Path(path_b)
    if not pa.is_file():
        return {"success": False, "message": "Operation failed", "error": f"Missing file A: {pa}"}
    if not pb.is_file():
        return {"success": False, "message": "Operation failed", "error": f"Missing file B: {pb}"}
    try:
        a_obj = json.loads(pa.read_text(encoding="utf-8"))
        b_obj = json.loads(pb.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return {"success": False, "message": "Operation failed", "error": f"JSON parse error: {e}"}

    a_lines = json.dumps(a_obj, indent=2, sort_keys=True).splitlines(keepends=True)
    b_lines = json.dumps(b_obj, indent=2, sort_keys=True).splitlines(keepends=True)
    diff = difflib.unified_diff(
        a_lines,
        b_lines,
        fromfile=str(pa),
        tofile=str(pb),
        lineterm="",
    )
    text = "".join(diff)
    return {
        "success": True,
        "path_a": str(pa),
        "path_b": str(pb),
        "unified_diff": text,
        "diff_line_count": len(text.splitlines()),
    }


def export_cursor_mcp_snippet_impl(server_key: str) -> dict[str, Any]:
    """One mcpServers entry from MASTER_MCP_CONFIG.json."""
    master = _master_config_path()
    if not master.is_file():
        return {"success": False, "message": "Operation failed", "error": f"MASTER config not found: {master}"}
    try:
        cfg = json.loads(master.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return {"success": False, "message": "Operation failed", "error": str(e)}

    servers = cfg.get("mcpServers") or cfg.get("mcp_servers") or {}
    if server_key not in servers:
        keys = list(servers.keys())[:40]
        return {
            "success": False,
            "error": f"Unknown server key {server_key!r}",
            "sample_keys": keys,
        }
    block = {server_key: servers[server_key]}
    snippet = json.dumps({"mcpServers": block}, indent=2)
    return {"success": True, "server_key": server_key, "snippet": snippet, "source": str(master)}


def audit_fastmcp_surface_impl(repo_path: str) -> dict[str, Any]:
    """Count @mcp.tool and FastMCP( in a Python tree."""
    root = Path(repo_path)
    if not root.is_dir():
        return {"success": False, "message": "Operation failed", "error": f"Not a directory: {root}"}

    mcp_tool_decls = 0
    fastmcp_inits = 0
    files_scanned = 0

    tool_re = re.compile(r"@mcp\.tool\b")
    fastmcp_re = re.compile(r"\bFastMCP\s*\(")

    for p in root.rglob("*.py"):
        if ".venv" in p.parts or "node_modules" in p.parts:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        files_scanned += 1
        mcp_tool_decls += len(tool_re.findall(text))
        fastmcp_inits += len(fastmcp_re.findall(text))

    return {
        "success": True,
        "repo_path": str(root),
        "files_scanned": files_scanned,
        "mcp_tool_decorators": mcp_tool_decls,
        "fastmcp_constructors": fastmcp_inits,
    }


def find_orphan_tool_references_impl(repo_path: str, min_hits: int) -> dict[str, Any]:
    """Heuristic: async def names registered with @mcp.tool with low reference count."""
    root = Path(repo_path)
    if not root.is_dir():
        return {"success": False, "message": "Operation failed", "error": f"Not a directory: {root}"}

    tool_funcs: dict[str, int] = {}
    decl_re = re.compile(r"^\s*@mcp\.tool", re.MULTILINE)
    async_def_re = re.compile(r"^\s*async\s+def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", re.MULTILINE)
    sync_def_re = re.compile(r"^\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", re.MULTILINE)

    for p in root.rglob("*.py"):
        if ".venv" in p.parts:
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if "@mcp.tool" not in text:
            continue
        for m in decl_re.finditer(text):
            chunk = text[m.end() : m.end() + 800]
            fn_m = async_def_re.search(chunk) or sync_def_re.search(chunk)
            if fn_m:
                name = fn_m.group(1)
                tool_funcs[name] = tool_funcs.get(name, 0) + 1

    combined = "\n".join(
        p.read_text(encoding="utf-8", errors="replace") for p in root.rglob("*.py") if ".venv" not in p.parts
    )

    orphans: list[dict[str, Any]] = []
    for name in sorted(tool_funcs.keys()):
        hits = len(re.findall(rf"\b{re.escape(name)}\b", combined))
        if hits <= min_hits:
            orphans.append({"name": name, "hits": hits, "registrations": tool_funcs[name]})

    return {
        "success": True,
        "repo_path": str(root),
        "min_hits_threshold": min_hits,
        "orphan_candidates": orphans,
        "count": len(orphans),
    }


def tail_log_file_impl(file_path: str, lines: int) -> dict[str, Any]:
    """Last N lines of a text file."""
    path = Path(file_path)
    if not path.is_file():
        return {"success": False, "message": "Operation failed", "error": f"Not a file: {path}"}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return {"success": False, "message": "Operation failed", "error": str(e)}

    all_lines = text.splitlines()
    n = max(1, min(lines, 5000))
    tail = all_lines[-n:]
    return {
        "success": True,
        "path": str(path),
        "lines_returned": len(tail),
        "content": "\n".join(tail),
    }


def env_sanity_check_impl(required_keys: list[str]) -> dict[str, Any]:
    """Check env keys exist (names only)."""
    missing = [k for k in required_keys if k and k not in os.environ]
    return {
        "success": len(missing) == 0,
        "checked": len(required_keys),
        "missing": missing,
    }


def summarize_server_for_prompt_impl(server_key: str) -> dict[str, Any]:
    """Markdown-ish summary of one MASTER server entry."""
    master = _master_config_path()
    if not master.is_file():
        return {"success": False, "message": "Operation failed", "error": f"MASTER config not found: {master}"}
    cfg = json.loads(master.read_text(encoding="utf-8"))
    servers = cfg.get("mcpServers") or cfg.get("mcp_servers") or {}
    if server_key not in servers:
        return {"success": False, "message": "Operation failed", "error": f"Unknown server key {server_key!r}"}
    entry = servers[server_key]
    lines = [
        f"## MCP server `{server_key}`",
        "",
        f"```json\n{json.dumps(entry, indent=2)}\n```",
    ]
    return {
        "success": True,
        "markdown": "\n".join(lines),
        "server_key": server_key,
    }


def mcp_changelog_digest_impl(repo_path: str) -> dict[str, Any]:
    """First ~100 lines of CHANGELOG.md."""
    root = Path(repo_path)
    ch = root / "CHANGELOG.md"
    if not ch.is_file():
        ch = root / "CHANGELOG"
    if not ch.is_file():
        return {"success": False, "message": "Operation failed", "error": f"No CHANGELOG.md under {root}"}
    lines = ch.read_text(encoding="utf-8", errors="replace").splitlines()
    head = lines[:120]
    return {
        "success": True,
        "path": str(ch),
        "line_count": len(head),
        "content": "\n".join(head),
    }


_SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[^\s'\"]{3,}"),
    re.compile(r"(?i)Bearer\s+[A-Za-z0-9\-._~+/]+=*"),
    re.compile(r"(?i)sk-[A-Za-z0-9]{10,}"),
)


def redact_secrets_audit_impl(file_path: str) -> dict[str, Any]:
    """Flag suspicious lines (redacted previews)."""
    path = Path(file_path)
    if not path.is_file():
        return {"success": False, "message": "Operation failed", "error": f"Not a file: {path}"}
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    findings: list[dict[str, Any]] = []
    for i, line in enumerate(lines, start=1):
        for pat in _SECRET_PATTERNS:
            if pat.search(line):
                redacted = line[:80]
                redacted = re.sub(r"(?i)(key|token|secret|password)(=|:)\s*\S+", r"\1=<redacted>", redacted)
                findings.append({"line": i, "preview_redacted": redacted})
                break
    return {
        "success": True,
        "path": str(path),
        "findings": findings[:200],
        "finding_count": len(findings),
    }
