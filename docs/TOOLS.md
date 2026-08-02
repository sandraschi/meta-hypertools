# Tools overview

Meta MCP exposes **many tools** grouped into **suites**. Each suite is registered in `mcp_server.py` and documented in its own page under **`docs/tools/`**.

## Suite index

| Suite | Focus |
|-------|--------|
| [Dynamic routing](tools/routing.md) | Fleet-wide tool proxy: `meta_route_tool`, capability index, hot-start |
| [Diagnostics](tools/diagnostics.md) | EmojiBuster, PowerShell checks, **`help`** catalog, `show_mcp_overview` |
| [Analysis](tools/analysis.md) | Runt/SOTA scans, analysis depot, MCD export |
| [Discovery](tools/discovery.md) | Find servers and IDE integration health |
| [Scaffolding](tools/scaffolding.md) | New MCP servers, apps, landing pages |
| [Server management](tools/server-management.md) | Start/stop/list MCP processes |
| [Tool execution](tools/tool-execution.md) | Execute tools on connected servers |
| [Repository intelligence](tools/repository-intelligence.md) | Deep scans, scoring |
| [Client management](tools/client-management.md) | IDE MCP config read/write |
| [Toolchains](tools/toolchains.md) | Presets of servers for IDEs |
| [Token analysis](tools/token-analysis.md) | Token counts & context limits |
| [Repository packing](tools/repo-packing.md) | Pack repos for LLMs |
| [Repository inspiration](tools/repo-inspiration.md) | Public GitHub study (`inspire_repo_*`; adapted from [Repomuse](https://www.npmjs.com/package/repomuse)) |
| [Meta / fleet dev](tools/meta-dev.md) | Fleet health, diffs, `MASTER_*` snippets (`meta_dev`) |
| [Demo capture](tools/demo-capture.md) | Playwright walkthrough + Remotion MP4 (`demo_ops`) |

**Also:** **scheduler** and **heartbeat** suites (scheduled tasks and fleet pulse)--see tool list via **`help`** or `just tools`.

## Full list and per-tool docs

- **Index** of all suite pages: **[tools/README.md](tools/README.md)**  
- **Live tool names** (from code): run `uv run python scripts/dump_mcp_tools.py` or **`just tools`**

## Web: Tool Lab

The dashboard **Tool Lab** page loads the catalog from **`GET /api/v1/mcp/catalog`** and runs tools with **`POST /api/v1/tools/execute`** so you can try tools without editing JSON in the IDE.
