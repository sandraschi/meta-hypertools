"""
MetaMCP Session Docs Router - browse/read mcp-agent-session-summaries docs.

Read-only bridge to the session-docs MCP server's data directory
(D:/Dev/repos/mcp-agent-session-summaries/data/sessions). Override the
directory with the SESSION_DOCS_DIR env var.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/api/v1/session-docs", tags=["session-docs"])

_DEFAULT_DOCS_DIR = Path(
    os.environ.get(
        "SESSION_DOCS_DIR",
        r"D:\Dev\repos\mcp-agent-session-summaries\data\sessions",
    )
)


def _docs_dir() -> Path:
    if not _DEFAULT_DOCS_DIR.is_dir():
        raise HTTPException(status_code=500, detail=f"Session docs dir not found: {_DEFAULT_DOCS_DIR}")
    return _DEFAULT_DOCS_DIR


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
