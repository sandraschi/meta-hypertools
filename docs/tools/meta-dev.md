# Meta / fleet developer tools (`meta_dev`)

Suite registered as **`meta_dev`**. Helpers for fleet operations, config diffs, and local audits. Paths default to **`MCP_CENTRAL_DOCS_ROOT`** (override per tool or env).

| Tool | Purpose |
|------|---------|
| `probe_fleet_health` | HTTP GET `http://127.0.0.1:{port}/health` for each `fleet-registry.json` entry with a `port`. |
| `diff_mcp_configs` | Unified diff of two JSON files (e.g. Cursor configs or snapshots). |
| `export_cursor_mcp_snippet` | One `mcpServers` block from **`MASTER_MCP_CONFIG.json`** (`META_MCP_MASTER_CONFIG` optional). |
| `audit_fastmcp_surface` | Count `@mcp.tool` / `FastMCP(` in a Python tree. |
| `find_orphan_tool_references` | Heuristic low-reference tool names (possible orphans). |
| `tail_log_file` | Last *N* lines of a text file. |
| `env_sanity_check` | Required env keys present (names only). |
| `summarize_server_for_prompt` | Markdown blob for one MASTER server entry. |
| `mcp_changelog_digest` | Head of `CHANGELOG.md` in a repo. |
| `redact_secrets_audit` | Flag suspicious lines (redacted previews). |

Fleet registry shape: top-level **`fleet`** array (see MCP Central Docs `operations/fleet-registry.json`).
