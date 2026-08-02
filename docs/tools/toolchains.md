# Toolchains & Config Switcher

The **Toolchains** suite lets you define named profiles (presets) of MCP servers and apply them to any supported IDE client in one click. This replaces manual `claude_desktop_config.json` editing and eliminates duplicate/stale entries from multi-agent config writes.

## How it works

1. **Server pool** — all available servers are read from `{REPOS_DIR}/mcp-central-docs/operations/MASTER_MCP_CONFIG.json` (the fleet master config).
2. **Profiles** — named collections of server names stored in `~/.meta_mcp_toolchains.json`.
3. **Apply** — writes the selected profile's servers (with their full config from master) to the target client's config file, with automatic backup. Full replace of `mcpServers` — restart the client after applying.

## Supported clients

`claude` · `cursor` · `windsurf` · `antigravity` · `zed`

## Web UI

Navigate to **Toolchains** in the sidebar of the meta_mcp webapp (port 10718). The page provides:

- Server picker with search/filter across all master-config servers
- Create named profile with optional description
- Apply any profile to any client with one click
- Expand a profile card to see its server list
- Delete profiles

## MCP tools (stdio)

| Tool | Description |
|------|-------------|
| `list_toolchains` | List all saved profiles |
| `create_toolchain` | Create a new profile (`name`, `servers[]`, `description`) |
| `delete_toolchain` | Delete a profile by name |
| `apply_toolchain` | Apply a profile to a client (`toolchain_name`, `client_name`) |
| `get_available_servers` | List all servers in MASTER_MCP_CONFIG |

## REST API

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/toolchains/list` | List profiles |
| `POST` | `/api/v1/toolchains/create` | Create profile |
| `DELETE` | `/api/v1/toolchains/{name}` | Delete profile |
| `POST` | `/api/v1/toolchains/apply` | Apply profile to client |
| `GET` | `/api/v1/toolchains/available_servers` | Server pool from master config |

## Files

| File | Role |
|------|------|
| `src/meta_mcp/services/toolchains_service.py` | Backend CRUD + apply logic |
| `src/meta_mcp/tools/registries/client_management.py` | MCP tool registrations |
| `src/meta_mcp/api_router.py` | REST endpoints (`/api/v1/toolchains/*`) |
| `web_sota/src/pages/Toolchains.tsx` | React UI |
| `~/.meta_mcp_toolchains.json` | Profile store (auto-created) |
| `mcd/operations/MASTER_MCP_CONFIG.json` | Server pool source |

## Typical workflow

```
# 1. Open webapp at http://localhost:10718 → Toolchains
# 2. Click "New Preset", name it e.g. "coding"
# 3. Pick servers: filesystem-mcp, git-github-mcp, meta_mcp, fastsearch-mcp, windows-operations-mcp
# 4. Save
# 5. Select target client "claude", click Apply
# 6. Restart Claude Desktop
```

## Notes

- Apply does a **full replace** of the client's server list — servers not in the profile are removed.
- Missing servers (in profile but not in master config) are skipped with a warning, not a failure.
- A timestamped backup of the target config is created automatically before each apply.
