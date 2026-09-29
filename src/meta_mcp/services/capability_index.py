"""SQLite-backed capability index: maps tool names to fleet server endpoints.

Scans the fleet config directory, IDE mcp.json files, and the port registry
to build a sub-second lookup table for dynamic tool routing.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

import structlog

from meta_mcp.models.routing import IndexStats, ServerEndpoint, ToolMapping

logger = structlog.get_logger(__name__)

_DEFAULT_DB_PATH = Path.home() / ".meta_mcp" / "capability_index.sqlite3"


def _default_fleet_roots() -> list[Path]:
    import os as _os

    roots: list[Path] = []
    for _env in (_os.environ.get("FLEET_REPOS_ROOT"), _os.environ.get("REPOS_DIR")):
        if _env:
            roots.append(Path(_env).expanduser())
    roots.append(Path("D:/Dev/repos"))
    # Dedupe, keep order
    seen: set[str] = set()
    out: list[Path] = []
    for _p in roots:
        _k = str(_p).lower()
        if _k not in seen:
            seen.add(_k)
            out.append(_p)
    return out


_DEFAULT_FLEET_ROOTS = _default_fleet_roots()

_DDL = """
CREATE TABLE IF NOT EXISTS capability_index (
    tool_name       TEXT NOT NULL,
    server_name     TEXT NOT NULL,
    host            TEXT DEFAULT '127.0.0.1',
    port            INTEGER,
    command         TEXT,
    cwd             TEXT,
    transport       TEXT DEFAULT 'http',
    description     TEXT,
    input_schema    TEXT,
    last_seen       REAL,
    status          TEXT DEFAULT 'unknown',
    PRIMARY KEY (tool_name, server_name)
);

CREATE INDEX IF NOT EXISTS idx_tool_name ON capability_index(tool_name);
CREATE INDEX IF NOT EXISTS idx_server_name ON capability_index(server_name);
CREATE INDEX IF NOT EXISTS idx_status ON capability_index(status);
"""


class CapabilityIndex:
    """SQLite cache mapping tool names to MCP server endpoints."""

    def __init__(self, db_path: Path | str | None = None):
        self._db_path = Path(db_path) if db_path else _DEFAULT_DB_PATH
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.executescript(_DDL)
            self._conn.commit()
        return self._conn

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    # ------------------------------------------------------------------
    # Indexing
    # ------------------------------------------------------------------

    def upsert(self, mapping: ToolMapping) -> None:
        """Insert or update a single tool mapping."""
        self.conn.execute(
            """INSERT OR REPLACE INTO capability_index
               (tool_name, server_name, host, port, command, cwd, transport,
                description, input_schema, last_seen, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                mapping.tool_name,
                mapping.server.server_name,
                mapping.server.host,
                mapping.server.port,
                mapping.server.command,
                mapping.server.cwd,
                mapping.server.transport,
                mapping.description,
                json.dumps(mapping.input_schema) if mapping.input_schema else None,
                mapping.last_seen or time.time(),
                mapping.status,
            ),
        )
        self.conn.commit()

    def upsert_batch(self, mappings: list[ToolMapping]) -> None:
        """Bulk insert/update tool mappings."""
        ts = time.time()
        rows = [
            (
                m.tool_name,
                m.server.server_name,
                m.server.host,
                m.server.port,
                m.server.command,
                m.server.cwd,
                m.server.transport,
                m.description,
                json.dumps(m.input_schema) if m.input_schema else None,
                m.last_seen or ts,
                m.status,
            )
            for m in mappings
        ]
        self.conn.executemany(
            """INSERT OR REPLACE INTO capability_index
               (tool_name, server_name, host, port, command, cwd, transport,
                description, input_schema, last_seen, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        self.conn.commit()
        logger.info("capability_index_bulk_upsert", count=len(mappings))

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def lookup(self, tool_name: str) -> list[ToolMapping]:
        """Find all server mappings for a tool name."""
        rows = self.conn.execute("SELECT * FROM capability_index WHERE tool_name = ?", (tool_name,)).fetchall()
        return [self._row_to_mapping(r) for r in rows]

    def lookup_exact(self, tool_name: str, server_name: str | None = None) -> ToolMapping | None:
        """Exact lookup; if server_name is given, prefers that match."""
        if server_name:
            row = self.conn.execute(
                "SELECT * FROM capability_index WHERE tool_name = ? AND server_name = ?",
                (tool_name, server_name),
            ).fetchone()
            if row:
                return self._row_to_mapping(row)

        row = self.conn.execute(
            "SELECT * FROM capability_index WHERE tool_name = ? ORDER BY last_seen DESC LIMIT 1",
            (tool_name,),
        ).fetchone()
        return self._row_to_mapping(row) if row else None

    def search(self, query: str, limit: int = 20) -> list[ToolMapping]:
        """Full-text search across tool names and descriptions."""
        rows = self.conn.execute(
            """SELECT * FROM capability_index
               WHERE tool_name LIKE ? OR description LIKE ?
               LIMIT ?""",
            (f"%{query}%", f"%{query}%", limit),
        ).fetchall()
        return [self._row_to_mapping(r) for r in rows]

    def servers_summary(self) -> list[dict[str, Any]]:
        """Distinct servers with tool counts and status."""
        rows = self.conn.execute(
            """SELECT server_name, COUNT(*) AS tool_count, MAX(status) AS status,
                      MAX(last_seen) AS last_seen, MAX(host) AS host, MAX(port) AS port,
                      MAX(command) AS command, MAX(transport) AS transport
               FROM capability_index
               GROUP BY server_name
               ORDER BY server_name"""
        ).fetchall()
        return [dict(r) for r in rows]

    def stats(self) -> IndexStats:
        """Return index health statistics."""
        total_tools = self.conn.execute("SELECT COUNT(*) FROM capability_index").fetchone()[0]
        total_servers = self.conn.execute("SELECT COUNT(DISTINCT server_name) FROM capability_index").fetchone()[0]
        online = self.conn.execute("SELECT COUNT(*) FROM capability_index WHERE status = 'online'").fetchone()[0]
        offline = self.conn.execute("SELECT COUNT(*) FROM capability_index WHERE status = 'offline'").fetchone()[0]

        row = self.conn.execute("SELECT MAX(last_seen) FROM capability_index").fetchone()
        return IndexStats(
            total_tools=total_tools,
            total_servers=total_servers,
            online_count=online,
            offline_count=offline,
            last_full_index=float(row[0]) if row[0] else None,
        )

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def purge_server(self, server_name: str) -> int:
        """Remove all entries for a server. Returns count removed."""
        cur = self.conn.execute("DELETE FROM capability_index WHERE server_name = ?", (server_name,))
        self.conn.commit()
        return cur.rowcount

    def update_status(self, server_name: str, status: str) -> None:
        self.conn.execute(
            "UPDATE capability_index SET status = ?, last_seen = ? WHERE server_name = ?",
            (status, time.time(), server_name),
        )
        self.conn.commit()

    def clear(self) -> None:
        self.conn.execute("DELETE FROM capability_index")
        self.conn.commit()
        logger.info("capability_index_cleared")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_mapping(row: sqlite3.Row) -> ToolMapping:
        schema_raw = row["input_schema"]
        input_schema = json.loads(schema_raw) if schema_raw else None
        return ToolMapping(
            tool_name=row["tool_name"],
            server=ServerEndpoint(
                server_name=row["server_name"],
                host=row["host"] or "127.0.0.1",
                port=row["port"],
                command=row["command"],
                cwd=row["cwd"],
                transport=row["transport"] or "http",
            ),
            description=row["description"],
            input_schema=input_schema,
            last_seen=row["last_seen"],
            status=row["status"] or "unknown",
        )
