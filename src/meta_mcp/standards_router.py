"""
MetaMCP Standards Router - browse/read mcp-central-docs standards.

Read-only bridge to the handbook's standards directory
(<mcd>/standards/**/*.md). Resolved via MCP_CENTRAL_DOCS_ROOT env var,
then <FLEET_REPOS_ROOT>/mcp-central-docs. The handbook is optional:
when absent the list endpoint returns available=False so the webapp
can show an honest empty state instead of fake content.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, HTTPException

from meta_mcp.fleet_paths import optional_mcp_central_docs

router = APIRouter(prefix="/api/v1/standards", tags=["standards"])

_CACHE: dict[str, object] = {"at": 0.0, "entries": []}
_CACHE_TTL = 300.0


def _standards_dir():
    mcd = optional_mcp_central_docs()
    if mcd is None:
        return None
    std = mcd / "standards"
    if not std.is_dir():
        return None
    return std


def _parse_frontmatter(text: str) -> dict[str, str]:
    """Minimal frontmatter parser (no yaml dependency)."""
    meta: dict[str, str] = {}
    if not text.startswith("---"):
        return meta
    lines = text.splitlines()
    for line in lines[1:]:
        stripped = line.strip()
        if stripped in ("---", "..."):
            break
        if stripped.startswith("#") or ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        meta[key.strip()] = value.strip().strip('"').strip("'")
    return meta


def _scan() -> list[dict]:
    std = _standards_dir()
    if std is None:
        return []
    now = time.time()
    if now - float(_CACHE["at"]) < _CACHE_TTL and _CACHE["entries"]:
        return list(_CACHE["entries"])  # type: ignore[arg-type]
    entries = []
    for p in sorted(std.rglob("*.md")):
        try:
            rel = p.relative_to(std).as_posix()
        except ValueError:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        meta = _parse_frontmatter(text)
        st = p.stat()
        entries.append(
            {
                "path": rel,
                "name": p.name,
                "title": meta.get("title") or p.stem.replace("-", " ").replace("_", " "),
                "category": meta.get("category", ""),
                "status": meta.get("status", ""),
                "audience": meta.get("audience", ""),
                "last_updated": meta.get("last_updated", ""),
                "size_bytes": st.st_size,
                "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime)),
            }
        )
    _CACHE["at"] = now
    _CACHE["entries"] = entries
    return entries


@router.get("")
def list_standards(q: str = "", category: str = "") -> dict:
    """List all standards with frontmatter metadata (card data)."""
    std = _standards_dir()
    if std is None:
        return {
            "success": True,
            "data": {
                "available": False,
                "standards": [],
                "count": 0,
                "hint": "Handbook not found. Clone mcp-central-docs next to "
                "your repos root or set MCP_CENTRAL_DOCS_ROOT.",
            },
        }
    entries = _scan()
    if q:
        needle = q.lower()
        entries = [e for e in entries if needle in e["title"].lower() or needle in e["path"].lower()]
    if category:
        entries = [e for e in entries if e["category"] == category]
    categories = sorted({e["category"] for e in _scan() if e["category"]})
    return {
        "success": True,
        "data": {
            "available": True,
            "standards": entries,
            "count": len(entries),
            "categories": categories,
            "root": str(std),
        },
    }


@router.get("/{rel_path:path}")
def read_standard(rel_path: str) -> dict:
    """Read one standard file as raw markdown (+ metadata)."""
    std = _standards_dir()
    if std is None:
        raise HTTPException(status_code=404, detail="Handbook not found")
    if not rel_path.endswith(".md"):
        raise HTTPException(status_code=400, detail="Only .md files are allowed")
    target = (std / rel_path).resolve()
    if not str(target).startswith(str(std.resolve())) or not target.is_file():
        raise HTTPException(status_code=404, detail=f"Standard not found: {rel_path}")
    text = target.read_text(encoding="utf-8")
    return {
        "success": True,
        "data": {"path": rel_path, "meta": _parse_frontmatter(text), "content": text},
    }
