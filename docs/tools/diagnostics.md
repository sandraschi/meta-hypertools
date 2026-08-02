# Diagnostics suite

**System health, safety, validation, and tool discovery.**

## Tools

### `help` (fleet discovery)

Lists every registered MetaMCP tool (name + first line of docstring).

| Parameter | Description |
|-----------|-------------|
| `query` | Optional substring filter on name or description |
| `max_tools` | Cap results (default 2000) |

**Aliases:** `list_mcp_tools`, `find_mcp_tools`

HTTP equivalent when the API is running: `GET /api/v1/mcp/catalog`

### `show_mcp_overview`

Short platform overview: version, suites, next steps (repo inspiration, fleet launcher, registry refresh).

Some clients surface this under legacy naming; the registered tool name is **`show_mcp_overview`**.

### `scan_mcp_unicode` (`emojibuster`)

Scans codebases for dangerous Unicode literals (emoji in source). Prefer hex escapes for cross-platform safety.

| Parameter | Description |
|-----------|-------------|
| `operation` | `scan` or `fix` |
| `repo_path` | Path or `*` |
| `auto_fix` | Required `True` for fix mode |

### `validate_mcp_pwsh` (`powershell_tools`)

Validates PowerShell scripts against Windows-native cmdlet usage.

### `audit_mcp_implementation` (`implementation_honesty_checker`)

Detects stub/mock/placeholder implementations in a tree.

### `open_mcp_launcher` (`open_fleet_starts_launcher`)

Opens the MCP Fleet Starts UI (Windows; default [http://127.0.0.1:10796](http://127.0.0.1:10796)).

### `refresh_mcp_fleet` (`generate_fleet_starts_launcher`)

Regenerates fleet registry metadata under `mcp-central-docs`.

| `operation` | Script |
|-------------|--------|
| `fastmcp_only` | `tools/sync_fleet_fastmcp.py` |
| `full_registry` | `tools/generate_fleet_registry.py` |

## Concepts

- **Safe Scanner:** No raw emoji literals in fleet Python source where terminals break.
- **Environment validation:** Match Python, PATH, and dependencies to project expectations before bulk edits.
