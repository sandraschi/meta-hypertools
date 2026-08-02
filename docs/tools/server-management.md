# 🏗️ Server Management Suite

**Lifecycle control and process orchestration for MCP servers.**

This suite provides enterprise-grade management of MCP server processes, treating them as first-class citizens with PID tracking, resource monitoring, and graceful lifecycle handling.

## Tools

### `start_mcp_server`
Launch an MCP server process with robust monitoring.
- **Features**: Capture proper PID, validated environments, cross-platform subprocess handling.
- **Args**: `command` (str), `args` (list), `env` (dict)

### `stop_mcp_server`
Gracefully terminate an MCP server.
- **Features**: SIGTERM/SIGKILL escalation, cleanup of orphaned processes.
- **Args**: `server_id` (str)

### `list_running_servers`
Get a snapshot of all currently managed MCP server processes.
- **Returns**: List of active servers with PIDs, start times, and status.

### `get_server_status`
Retrieve detailed health and performance metrics for a specific server.
- **Metrics**: CPU usage, memory consumption, uptime, connection status.
- **Args**: `server_id` (str)

## Key Features
- **Process Control**: Real PID tracking ensures you're managing the actual server, not a wrapper.
- **Cross-Platform**: Handles Windows job objects and Unix process groups correctly.
- **Resource Monitoring**: Live stats on CPU/RAM usage to catch leaks.
- **Isolation**: Each server runs in its own process space for stability.

### `inspect_server_capabilities` (New in 3.3.0)
Deep drill-down into a server's exposed features.
- **Tools**: List all available executable tools.
- **Resources**: View exposed URI templates and static resources.
- **Prompts**: List available prompt templates.
