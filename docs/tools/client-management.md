# 🖥️ Client Management Suite

**Multi-IDE ecosystem control and configuration.**

Manage MCP integrations across the entire development environment from a single source of truth. Supports Claude, Cursor, Windsurf, Zed, and Antigravity.

## Tools

### `read_client_config`
Parse and normalize configuration for a specific client.
- **Args**: `client_name` (str) -> "claude", "cursor", "windsurf", "zed", "antigravity"

### `update_client_config`
Apply changes to a client's configuration file.
- **Features**: Atomic writes, automatic backups (`.backup` files), JSON validation.
- **Args**: `client_name` (str), `updates` (dict), `backup` (bool)

### `add_server_to_client`
Register a new MCP server with a client.
- **Features**: Idempotency (prevents duplicates), path normalization.
- **Args**: `client_name` (str), `server_name` (str), `server_config` (dict)

### `remove_server_from_client`
Cleanly unregister a server.
- **Args**: `client_name` (str), `server_name` (str)

### `validate_client_config`
Check a client's configuration for syntax errors and invalid paths.
- **Args**: `client_name` (str)

### `check_client_integration`
Verify that a client is correctly loading and communicating with registered servers.
- **Args**: `ide_name` (str)

## Supported Clients
- **Claude Desktop**: `%APPDATA%/Claude/claude_desktop_config.json`
- **Cursor**: `%APPDATA%/Cursor/.../mcp.json`
- **Windsurf**: `~/.codeium/windsurf/mcp_config.json`
- **Zed**: `~/.config/zed/settings.json`
- **Antigravity**: Internal configuration
