# Dynamic routing

> **Version**: 0.5.0 | **MCP tools**: `meta_route_tool`, `meta_search_capabilities`, `meta_routing_status`, `meta_routing_reindex`, `meta_routing_servers`

Lazy-loading proxy for the 130+ MCP server fleet. Resolves tool names to fleet server endpoints via a SQLite capability index, hot-starts sub-servers via subprocess if offline, proxies MCP JSON-RPC calls over HTTP, and returns the result.

## Motivation

With 130+ fleet servers, static `mcp.json` definitions saturate the LLM context window. The dynamic router acts as a single-entry-point proxy: the agent calls `meta_route_tool` with a tool name and arguments, and the router handles server discovery, activation, and call forwarding transparently.

## Tools

### `meta_route_tool`

Unified entry point for routing any tool call to any fleet MCP server.

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `tool_name` | string | yes | Target MCP tool name |
| `arguments` | dict | no | Tool parameters (default: `{}`) |
| `target_server` | string | no | Explicit server override (e.g. `"arxiv-mcp"`) |

**Flow:**
1. Look up `tool_name` in the SQLite capability index
2. If `target_server` is given, prefer that match
3. Check if the server is reachable (TCP probe + MCP `initialize` handshake)
4. If offline, hot-start via `uv run` subprocess with `MCP_PORT` env var
5. POST MCP JSON-RPC `tools/call` to `http://127.0.0.1:{port}/mcp`
6. Return the result with latency measurement

**Examples:**
```python
meta_route_tool(tool_name="search_papers", arguments={"query": "kv cache optimization", "limit": 5})
meta_route_tool(
    tool_name="plex_media", target_server="plex-mcp", arguments={"operation": "search", "query": "Inception"}
)
```

### `meta_search_capabilities`

Search the capability index for tools matching a query string. Returns tool names with server endpoints, descriptions, and online/offline status.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | -- | Search query |
| `limit` | int | 20 | Max results (1-100) |

### `meta_routing_status`

Report capability index health: total tools indexed, distinct servers, online/offline counts, running server processes, and last full index timestamp.

### `meta_routing_reindex`

Force a full fleet capability re-index. Clears the SQLite index, re-scans all fleet repo directories and IDE `mcp.json` config files, probes running HTTP servers for their tool lists.

### `meta_routing_servers`

List all fleet servers discovered by the capability index. Each entry includes tool count, last-seen timestamp, status, host, port, command, and transport type.

## Architecture

```
meta_route_tool(tool_name, arguments)
    -> routing.py (MCP tool)
        -> DynamicRouterService (REST API parity)
            -> DynamicRouter / RouterIndex (SQLite)
                -> Lookup: tool_name -> (server, port)
                -> Hot-start: subprocess + MCP_PORT
                -> Proxy: POST http://127.0.0.1:{port}/mcp
```

### Capability index (SQLite)

Schema: `capability_index` table with columns `tool_name`, `server_name`, `host`, `port`, `command`, `transport`, `description`, `input_schema`, `last_seen`, `status`.

Indexes: `tool_name` (primary), `server_name`, `status`.

Stored at `~/.meta_mcp/capability_index.sqlite3`. WAL mode, concurrent-safe.

### Fleet scanning

On first use (lazy indexing):
1. Scan `D:/Dev/repos/` for repos with `pyproject.toml`
2. Read project name from `pyproject.toml` → derive `uv run {name}-server` command
3. Look up port from fleet port registry (hardcoded map of ~50 known servers)
4. Probe running HTTP servers via `POST {port}/mcp` with MCP `tools/list` JSON-RPC
5. Scan IDE `mcp.json` files (Cursor, Claude Desktop, Windsurf, Antigravity) for stdio-configured servers

### Hot-start

1. Subprocess launch via `uv run {package}-server` with `MCP_PORT` and `MCP_HOST` env vars
2. Poll port readiness (up to 30s, 1s intervals)
3. TCP connect + MCP initialize handshake to confirm the server is serving

## REST API

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/routing/call` | Route a tool call |
| GET | `/api/v1/routing/status` | Index health + running servers |
| POST | `/api/v1/routing/rebuild` | Force full fleet re-index |
| GET | `/api/v1/routing/search` | Search capability index |

## Source files

| File | Purpose |
|------|---------|
| `src/meta_mcp/models/routing.py` | Pydantic models |
| `src/meta_mcp/services/capability_index.py` | SQLite-backed capability index |
| `src/meta_mcp/services/dynamic_router.py` | Core routing engine |
| `src/meta_mcp/services/dynamic_router_service.py` | REST API service layer |
| `src/meta_mcp/tools/registries/routing.py` | MCP tool registration |
