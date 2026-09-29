"""
MetaMCP Session Docs Router - browse/read/prune session docs.

Read bridge to the session-docs data directory (SESSION_DOCS_DIR env,
handbook operations/session-log, or legacy mcp-agent-session-summaries).
Pruning is cutoff-only (DELETE ?before=YYYY-MM-DD), top-level *.md files:
subdirectories such as aiwatcher/ are never touched.
"""

from __future__ import annotations

import datetime
import os
import re
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException

from meta_mcp.fleet_paths import optional_mcp_central_docs

router = APIRouter(prefix="/api/v1/session-docs", tags=["session-docs"])

_LEGACY_DOCS_DIR = Path(r"D:\Dev\repos\mcp-agent-session-summaries\data\sessions")


def _docs_dir() -> Path:
    raw = os.environ.get("SESSION_DOCS_DIR", "").strip()
    if raw:
        cand = Path(raw).expanduser()
        if cand.is_dir():
            return cand
        raise HTTPException(status_code=500, detail=f"Session docs dir not found: {cand}")
    mcd = optional_mcp_central_docs()
    if mcd is not None:
        cand = mcd / "operations" / "session-log"
        if cand.is_dir():
            return cand
    if _LEGACY_DOCS_DIR.is_dir():
        return _LEGACY_DOCS_DIR
    raise HTTPException(
        status_code=500,
        detail="Session docs not found (tried SESSION_DOCS_DIR, handbook session-log, legacy dir)",
    )


@router.get("")
def list_session_docs() -> dict:
    """List session documentation files (name, size, modified)."""
    docs = _docs_dir()
    entries = []
    for p in sorted(docs.glob("*.md")):
        st = p.stat()
        entries.append(
            {
                "name": p.name,
                "size_bytes": st.st_size,
                "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime)),
            }
        )
    return {"success": True, "data": {"docs": entries, "count": len(entries)}}


_DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})")


def _doc_date(p: Path) -> str:
    """Doc date: YYYY-MM-DD filename prefix when present, else mtime date."""
    m = _DATE_PREFIX.match(p.name)
    if m:
        return m.group(1)
    return datetime.date.fromtimestamp(p.stat().st_mtime).isoformat()


@router.delete("")
def prune_session_docs(before: str = "") -> dict:
    """Delete top-level *.md docs older than a cutoff date (YYYY-MM-DD).

    Cutoff is mandatory and strictly enforced: docs with doc-date < before
    are deleted, everything else (including subdirectories such as aiwatcher/)
    is left alone. Returns deleted + kept counts and the deleted names.
    """
    docs = _docs_dir()
    try:
        cutoff = datetime.date.fromisoformat(before.strip())
    except ValueError:
        raise HTTPException(status_code=400, detail="Query param 'before' is required as YYYY-MM-DD")
    deleted: list[str] = []
    kept = 0
    for p in sorted(docs.glob("*.md")):
        if not p.is_file():
            kept += 1
            continue
        if datetime.date.fromisoformat(_doc_date(p)) < cutoff:
            try:
                p.unlink()
                deleted.append(p.name)
            except OSError as exc:
                raise HTTPException(status_code=500, detail=f"Delete failed for {p.name}: {exc}")
        else:
            kept += 1
    return {
        "success": True,
        "data": {"deleted": deleted, "deleted_count": len(deleted), "kept_count": kept, "before": before.strip()},
    }


@router.get("/{filename}")
def read_session_doc(filename: str) -> dict:
    """Read one session documentation file as raw markdown."""
    docs = _docs_dir()
    if not filename.endswith(".md"):
        raise HTTPException(status_code=400, detail="Only .md files are allowed")
    target = (docs / filename).resolve()
    if not str(target).startswith(str(docs.resolve())) or not target.is_file():
        raise HTTPException(status_code=404, detail=f"Session doc not found: {filename}")
    content = target.read_text(encoding="utf-8")
    return {"success": True, "data": {"name": filename, "content": content}}
