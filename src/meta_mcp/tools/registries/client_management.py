from typing import Any, Literal

from fastmcp import FastMCP

from meta_mcp.services.client_settings_manager import ClientSettingsManager


def register_client_management_tools(mcp: FastMCP):
    """Register client management tool suite with FastMCP."""

    service = ClientSettingsManager()

    @mcp.tool(name="client_ops")
    async def client_ops(
        operation: Literal["read", "update", "add_server", "remove_server", "validate", "list"],
        client_name: str | None = None,
        updates: dict[str, Any] | None = None,
        backup: bool = True,
        server_name: str | None = None,
        server_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """IDE client configuration management (portmanteau).

        [RATIONALE]
        Consolidates 6 related operations into a single tool to prevent tool explosion while enabling full API coverage.

        ## Operations
        - **read**: Read a client's MCP configuration file
        - **update**: Update a client's MCP configuration
        - **add_server**: Register a new MCP server in a client config
        - **remove_server**: Remove an MCP server from a client config
        - **validate**: Validate a client's MCP configuration
        - **list**: List all available client configurations

        ## Return Format
        {"success": bool, "operation": str, "message": str}

        ## Examples
        await client_ops(operation="read")
        await client_ops(operation="update")
        """
        if operation == "read":
            return await service.read_client_config(client_name)
        elif operation == "update":
            return await service.update_client_config(client_name, updates or {}, backup)
        elif operation == "add_server":
            return await service.add_server_to_client(client_name, server_name, server_config or {})
        elif operation == "remove_server":
            return await service.remove_server_from_client(client_name, server_name)
        elif operation == "validate":
            return await service.validate_client_config(client_name)
        elif operation == "list":
            return await service.list_client_configs()
