# 🕵️ Discovery Suite

**Ecosystem visualization and integration scanning.**

Tools to find what's running, what's installed, and how everything is connected. Discovery is the first step in managing a complex MCP environment.

## Tools

### `discover_servers`
Scan the filesystem and process table for MCP servers.
- **Search**: Recursively looks for `mcp.json`, `pyproject.toml` with `fastmcp` dependencies, and running python processes matching known MCP patterns.
- **Args**: `discovery_paths` (list[str])

### `list_running_servers`
(Shared with Server Management) - Shows currently active processes.

### `check_client_integration`
Audit the connection between a client (e.g., Cursor) and its registered servers.
- **Checks**: Config settings, path validity, and server responsiveness.
- **Args**: `ide_name` (str)

## Capabilities
- **Zombie Detection**: Identifies server processes that are running but not registered in any client.
- **Config Auditing**: Finds discrepancies between what *should* be running (config) and what *is* running.
- **Multi-System View**: Aggregates views from different IDEs into a single system map.
