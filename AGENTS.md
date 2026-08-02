# meta_mcp Agent Context

Fleet MCP server - the meta layer that scaffolds, wraps, probes, audits,
and operates the fleet. See `justfile` for recipes.

## Quick Ref

```powershell
uv run pytest tests/ -q      # 65 tests
just lint                     # ruff check + format
just health                   # standards checker v2 (self-audit 10/10)
just mcpb-pack                # MCPB bundle (3-4-100 gate)
just serve                    # full stack via start.ps1
```

## Ports

| Port | Service |
|------|---------|
| 10718 | Backend (FastAPI + FastMCP HTTP /mcp) |
| 10719 | Frontend (Vite, web_sota) |

## Tool patterns

- Portmanteau-first: `analysis_ops(operation="runts")`, `scaffold_ops`,
  `server_ops`, `diagnostics_ops`, etc. Operations are Literal enums in
  schemas.
- Scaffolding entry points live in `src/meta_mcp/tools/` (server_builder_sota.py,
  fullstack.py, gamemaker.py, wisdom.py, webshop.py).
- `scripts/fullstack-builder.ps1` - 2768-line monolith generator (keep it
  monolithic, that is the point).
- `scripts/check-repo-standards.ps1` - SOTA checker v2 (synced with
  mcp-central-docs/sota-scripts/repo-standards/).

## Key files

| File | Purpose |
|------|---------|
| `src/meta_mcp/main.py` | FastAPI app + auth middleware |
| `src/meta_mcp/auth.py` | X-Wurst-Auth protection (fleet start/stop) |
| `src/meta_mcp/mcp_server.py` | FastMCP tool suites |
| `mcpb/` | MCPB bundle dir (pack.ps1 syncs src in) |
| `web_sota/` | React dashboard (10719) |
| `fleet_probes/` | Probe scripts (cold-start, cold-install) |

## Demo capture

Fleet webapp screencasts: **`demo_ops`** in MCP (`plan` -> `record` -> `render`).
Full doc: **`docs/tools/demo-capture.md`**.
