"""Dynamic capabilities index  SQLite-backed tool-to-server mapping for lazy-loading proxy.

Scans fleet manifests and optional per-repo tool schemas to build a lightweight
index that maps semantic tool names (and keyword queries) to specific local MCP
server endpoints. This enables the meta_route_tool proxy to hot-start sub-servers
on demand without saturating the LLM context window with static mcp.json definitions.

Design: single-table SQLite, WAL mode, async-safe via aiosqlite connection pool.
Index rebuild is idempotent and non-blocking.
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

from meta_mcp.fleet_paths import fleet_local_root

_INDEX_FILENAME = "dynamic_routing_index.sqlite"
_DEFAULT_INDEX_DIR = fleet_local_root()
_SCHEMA_VERSION = 1

# MCP endpoints exposed by fleet servers for tool schema discovery
_TOOL_CATALOG_PATHS = (
    "/api/v1/mcp/catalog",
    "/api/tools",
    "/mcp/tools",
)


def _default_index_path() -> Path:
    d = Path(os.environ.get("META_MCP_ROUTER_INDEX_DIR", str(_DEFAULT_INDEX_DIR)))
    d.mkdir(parents=True, exist_ok=True)
    return d / _INDEX_FILENAME


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS routing (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tool_name TEXT NOT NULL COLLATE NOCASE,
            server_repo TEXT NOT NULL,
            server_port INTEGER NOT NULL,
            server_host TEXT NOT NULL DEFAULT '127.0.0.1',
            transport TEXT NOT NULL DEFAULT 'http',
            startup_command TEXT,
            health_path TEXT DEFAULT '/health',
            tool_schema TEXT,
            server_status TEXT DEFAULT 'unknown',
            last_seen REAL NOT NULL DEFAULT 0,
            provenance TEXT NOT NULL DEFAULT 'manifest',
            UNIQUE(tool_name, server_repo, transport)
        )
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_routing_tool ON routing(tool_name, server_status)
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_routing_repo ON routing(server_repo)
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS index_meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "INSERT OR REPLACE INTO index_meta(key, value) VALUES ('schema_version', ?)",
        (str(_SCHEMA_VERSION),),
    )
    conn.commit()


class RouterIndex:
    """Async-safe SQLite index of tool capabilities across the fleet."""

    def __init__(self, index_path: Path | None = None):
        self._path = index_path or _default_index_path()
        self._lock = asyncio.Lock()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._path), timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def ensure_schema(self) -> None:
        conn = self._connect()
        try:
            _init_schema(conn)
        finally:
            conn.close()

    async def insert_tool(
        self,
        tool_name: str,
        server_repo: str,
        server_port: int,
        *,
        server_host: str = "127.0.0.1",
        transport: str = "http",
        startup_command: str | None = None,
        health_path: str = "/health",
        tool_schema: dict[str, Any] | None = None,
        provenance: str = "manifest",
    ) -> None:
        async with self._lock:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._insert_sync,
                tool_name,
                server_repo,
                server_port,
                server_host,
                transport,
                startup_command,
                health_path,
                tool_schema,
                provenance,
            )

    def _insert_sync(
        self,
        tool_name: str,
        server_repo: str,
        server_port: int,
        server_host: str,
        transport: str,
        startup_command: str | None,
        health_path: str,
        tool_schema: dict[str, Any] | None,
        provenance: str,
    ) -> None:
        conn = self._connect()
        try:
            schema_json = json.dumps(tool_schema) if tool_schema else None
            conn.execute(
                """INSERT OR REPLACE INTO routing
                   (tool_name, server_repo, server_port, server_host, transport,
                    startup_command, health_path, tool_schema, last_seen, provenance)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    tool_name,
                    server_repo,
                    server_port,
                    server_host,
                    transport,
                    startup_command,
                    health_path,
                    schema_json,
                    time.time(),
                    provenance,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    async def query_tools(
        self,
        tool_name: str | None = None,
        *,
        server_repo: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        async with self._lock:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._query_sync, tool_name, server_repo, limit)

    _COLUMNS = (
        "tool_name, server_repo, server_port, server_host, transport, "
        "startup_command, health_path, tool_schema, server_status, provenance"
    )

    def _query_sync(
        self,
        tool_name: str | None,
        server_repo: str | None,
        limit: int,
    ) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            params: list[Any] = []
            where_parts: list[str] = []
            if tool_name:
                where_parts.append("tool_name LIKE ?")
                params.append(f"%{tool_name}%")
            if server_repo:
                where_parts.append("server_repo = ?")
                params.append(server_repo)
            if where_parts:
                sql = (
                    "SELECT "
                    + self._COLUMNS
                    + " FROM routing WHERE "
                    + " AND ".join(where_parts)
                    + " ORDER BY last_seen DESC LIMIT ?"
                )
            else:
                sql = "SELECT " + self._COLUMNS + " FROM routing ORDER BY last_seen DESC LIMIT ?"
            rows = conn.execute(sql, [*params, limit]).fetchall()
            return [
                {
                    "tool_name": r[0],
                    "server_repo": r[1],
                    "server_port": r[2],
                    "server_host": r[3],
                    "transport": r[4],
                    "startup_command": r[5],
                    "health_path": r[6],
                    "tool_schema": json.loads(r[7]) if r[7] else None,
                    "server_status": r[8],
                    "provenance": r[9],
                }
                for r in rows
            ]
        finally:
            conn.close()

    async def get_server_tools(self, server_repo: str) -> list[dict[str, Any]]:
        return await self.query_tools(server_repo=server_repo, limit=500)

    async def mark_server_status(self, server_repo: str, status: str) -> None:
        async with self._lock:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._mark_server_status_sync, server_repo, status)

    def _mark_server_status_sync(self, server_repo: str, status: str) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "UPDATE routing SET server_status = ? WHERE server_repo = ?",
                (status, server_repo),
            )
            conn.commit()
        finally:
            conn.close()

    async def clear_all(self) -> None:
        async with self._lock:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._clear_all_sync)

    def _clear_all_sync(self) -> None:
        conn = self._connect()
        try:
            conn.execute("DELETE FROM routing")
            conn.commit()
        finally:
            conn.close()

    async def stats(self) -> dict[str, Any]:
        async with self._lock:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._stats_sync)

    def _stats_sync(self) -> dict[str, Any]:
        conn = self._connect()
        try:
            tool_count = conn.execute("SELECT COUNT(*) FROM routing").fetchone()[0]
            server_count = conn.execute("SELECT COUNT(DISTINCT server_repo) FROM routing").fetchone()[0]
            return {
                "tool_count": tool_count,
                "server_count": server_count,
                "index_path": str(self._path),
            }
        finally:
            conn.close()

    async def search_semantic(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Fuzzy keyword search across tool names and server repos."""
        terms = [t.strip().lower() for t in query.split() if t.strip()]
        if not terms:
            return []
        async with self._lock:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._search_semantic_sync, terms, limit)

    def _search_semantic_sync(self, terms: list[str], limit: int) -> list[dict[str, Any]]:
        conn = self._connect()
        try:
            params = [f"%{t}%" for t in terms]
            where_clause = " OR ".join(["tool_name LIKE ?" for _ in terms])
            sql = "SELECT " + self._COLUMNS + " FROM routing WHERE " + where_clause + " ORDER BY last_seen DESC LIMIT ?"
            rows = conn.execute(sql, [*params, limit]).fetchall()
            return [
                {
                    "tool_name": r[0],
                    "server_repo": r[1],
                    "server_port": r[2],
                    "server_host": r[3],
                    "transport": r[4],
                    "startup_command": r[5],
                    "health_path": r[6],
                    "tool_schema": json.loads(r[7]) if r[7] else None,
                    "server_status": r[8],
                    "provenance": r[9],
                }
                for r in rows
            ]
        finally:
            conn.close()
