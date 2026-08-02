# ⚡ Tool Execution Suite

**Remote tool invocation and orchestration engine.**

Execute tools resident on any connected MCP server from a central control point. This suite acts as a meta-layer, allowing MetaMCP to drive other MCP servers dynamically.

## Tools

### `execute_server_tool`
Execute a specific tool on a target MCP server.
- **Features**: Dynamic parameter validation, timeout handling, error normalization.
- **Args**: `server_id` (str), `tool_name` (str), `parameters` (dict)

### `list_server_tools`
Discover all tools available on a specific server.
- **Returns**: detailed list of tool schemas, descriptions, and argument definitions.
- **Args**: `server_id` (str)

### `validate_tool_parameters`
Dry-run validation of parameters against a tool's JSON schema.
- **Use Case**: Pre-flight checks before executing potentially expensive or side-effect-heavy tools.
- **Args**: `server_id` (str), `tool_name` (str), `parameters` (dict)

### `get_tool_execution_history`
View audit logs of past tool executions.
- **Features**: Track success rates, latency, and parameter usage patterns.
- **Args**: `server_id` (str), `limit` (int)

## Capabilities
- **Remote Invocation**: Call `filesystem` tools on Server A and `browser` tools on Server B from a single interface.
- **Dynamic Forms**: Intelligent UI generation based on tool schemas.
    - **Smart Inputs**: Form fields adapt to `string`, `boolean`, `enum`, and `array` types.
    - **Power User Mode**: Toggle to raw JSON for complex nested object parameters.
- **Type Safety**: Enforces schema validation before requests leave the orchestration layer.
- **Observability**: Complete audit trail of who called what, when, and with what result.
