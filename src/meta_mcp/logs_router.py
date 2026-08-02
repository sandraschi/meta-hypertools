"""Fleet-standard /api/logs router  query, stats, export, clear."""

from __future__ import annotations

import csv
import io
import json

from fastapi import APIRouter, Query, Response
from fastapi.responses import PlainTextResponse

from meta_mcp.logging_config import _memory_logs

router = APIRouter(prefix="/api/logs", tags=["logs"])

LEVEL_ORDER = {"DEBUG": 0, "INFO": 1, "WARNING": 2, "ERROR": 3}
MAX_ENTRIES = 2000


def _snapshot() -> list[dict]:
    return list(_memory_logs)


@router.get("")
async def query_logs(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    level: str | None = Query(None, description="Min level: DEBUG, INFO, WARNING, ERROR"),
    kind: str | None = Query(None, description="Filter by kind (e.g. tool_call)"),
    search: str | None = Query(None, description="Substring match on detail"),
    sort: str = Query("desc", pattern="^(asc|desc)$"),
    after_id: str | None = Query(None, description="Tail: only entries newer than this id"),
) -> dict:
    all_entries = _snapshot()

    if after_id:
        all_entries = [e for e in all_entries if e.get("id", "") > after_id]

    if level:
        min_ord = LEVEL_ORDER.get(level.upper(), 0)
        all_entries = [e for e in all_entries if LEVEL_ORDER.get(e.get("level", "INFO"), 1) >= min_ord]

    if kind:
        all_entries = [e for e in all_entries if e.get("kind") == kind]

    if search:
        q = search.lower()
        all_entries = [e for e in all_entries if q in e.get("detail", "").lower()]

    all_entries.sort(key=lambda e: e.get("timestamp", ""), reverse=(sort == "desc"))
    total = len(all_entries)
    page = all_entries[offset : offset + limit]

    return {
        "entries": page,
        "total": total,
        "limit": limit,
        "offset": offset,
        "max_entries": MAX_ENTRIES,
        "sort": sort,
    }


@router.get("/stats")
async def log_stats() -> dict:
    all_entries = _snapshot()
    levels: dict[str, int] = {}
    kinds: dict[str, int] = {}
    for e in all_entries:
        lv = e.get("level", "INFO")
        levels[lv] = levels.get(lv, 0) + 1
        kd = e.get("kind", "server")
        kinds[kd] = kinds.get(kd, 0) + 1
    return {
        "total": len(all_entries),
        "max_entries": MAX_ENTRIES,
        "levels": levels,
        "kinds": kinds,
        "oldest": all_entries[0]["timestamp"] if all_entries else None,
        "newest": all_entries[-1]["timestamp"] if all_entries else None,
    }


@router.get("/export")
async def export_logs(
    level: str | None = Query(None),
    kind: str | None = Query(None),
    search: str | None = Query(None),
    format: str = Query("json", pattern="^(json|csv)$"),
) -> Response:
    result = await query_logs(limit=MAX_ENTRIES, level=level, kind=kind, search=search)
    entries = result["entries"]

    if format == "csv":
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=["id", "timestamp", "level", "kind", "detail", "meta"])
        w.writeheader()
        for e in entries:
            row = {k: e.get(k, "") for k in ["id", "timestamp", "level", "kind", "detail"]}
            row["meta"] = json.dumps(e.get("meta", {}))
            w.writerow(row)
        return PlainTextResponse(
            buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=logs.csv"},
        )

    return Response(
        json.dumps(entries, indent=2, default=str),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=logs.json"},
    )


@router.delete("")
async def clear_logs() -> dict:
    count = len(_memory_logs)
    _memory_logs.clear()
    return {"success": True, "deleted": count, "message": f"Cleared {count} log entries"}
