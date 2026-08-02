# Architecture

Meta MCP is one **Python package** with three main ways in:

1. **stdio MCP** — `meta-mcp-server` for IDEs and agents.  
2. **HTTP** — FastAPI app: REST for the dashboard, **MCP streamable HTTP** mounted at **`/mcp`**, and optional static files for the SPA.  
3. **Scripts** — e.g. `scripts/dump_mcp_tools.py` for listing tools without a long-lived server.

## High-level diagram

```
┌─────────────────────────────────────────────────────────────┐
│  IDE / Claude Desktop          Browser (web_sota)        │
│         │                              │                        │
│    stdio MCP                    HTTP + WS (Vite proxy)      │
│         │                              │                        │
│         ▼                              ▼                        │
│  meta_mcp.mcp_server          meta_mcp.main.app             │
│  FastMCP "MetaMCP"            FastAPI + same FastMCP        │
│         │                              │                        │
│         └──────────────┬───────────────┘                        │
│                        ▼                                        │
│              Tool registries (suites)                           │
│              diagnostics, analysis, …, meta_dev                 │
│                        │                                        │
│                        ▼                                        │
│              Services (optional)                                │
│              (servers, discovery, toolchains, …)              │
└─────────────────────────────────────────────────────────────┘
```

## Key modules

| Area | Role |
|------|------|
| **`src/meta_mcp/mcp_server.py`** | Builds the FastMCP app, **`initialize_tools()`** registers all suites. |
| **`src/meta_mcp/main.py`** | FastAPI lifespan: initializes tools, mounts **`/mcp`**, static **`web_sota/dist`**, includes **`api_router`**. |
| **`src/meta_mcp/api_router.py`** | REST: diagnostics, discovery, **tool catalog**, **execute tool**, etc. |
| **`src/meta_mcp/tools/registries/`** | One registrar per suite (e.g. `heartbeat`, `meta_dev`). |
| **`src/meta_mcp/services/`** | Longer-lived logic (server process table, tool bridge, …). |

## REST vs MCP tools

- **MCP clients** (stdio or HTTP) use the **native MCP protocol** (`list_tools`, `call_tool`).  
- **Web dashboard** uses **REST**: e.g. **`GET /api/v1/mcp/catalog`** and **`POST /api/v1/tools/execute`** with a JSON body. Execution targets the **in-process** Meta MCP app for the configured server id (e.g. `metaops`).

## Web UI

- **Source:** `web_sota/` (Vite + React).  
- **Production:** `npm run build` → **`web_sota/dist`**; FastAPI serves it when that folder exists.  
- **Dev:** Vite on **10719** (see `vite.config.ts`), proxying API and MCP to the backend.

## Configuration

- **Ports:** `HOST` / `PORT` env vars for `meta-mcp`.  
- **Fleet / docs paths:** some tools read **`MCP_CENTRAL_DOCS_ROOT`** or **`META_MCP_MASTER_CONFIG`** (see [tools/meta-dev.md](tools/meta-dev.md)).
