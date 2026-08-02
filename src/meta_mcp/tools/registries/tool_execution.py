from typing import Any

from fastmcp import FastMCP

from meta_mcp.services.tool_service import ToolService


def register_tool_execution_tools(mcp: FastMCP):
    """Register tool execution tool suite with FastMCP."""

    service = ToolService()

    @mcp.tool(name="execute_mcp_tool")
    async def execute_server_tool(
        server_id: str, tool_name: str, parameters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Execute server tool.

        Invoke a specific tool on a target MCP server with the provided parameters via standardized transport.
        """
        return await service.execute_tool(server_id, tool_name, parameters or {})

    @mcp.tool(name="list_mcp_tools")
    async def list_server_tools(server_id: str) -> dict[str, Any]:
        """List server tools.

        Retrieve a comprehensive registry of all tools available for execution on the target MCP server.
        """
        return await service.list_server_tools(server_id)

    @mcp.tool(name="validate_tool_schema")
    async def validate_tool_parameters(server_id: str, tool_name: str, parameters: dict[str, Any]) -> dict[str, Any]:
        """Validate tool parameters.

        Verify provided arguments against the tool's input schema to ensure structural and logical compliance.
        """
        return await service.validate_tool_parameters(server_id, tool_name, parameters)

    @mcp.tool(name="show_tool_history")
    async def get_tool_execution_history(
        server_id: str, tool_name: str | None = None, limit: int = 10
    ) -> dict[str, Any]:
        """Get execution history.

        Retrieve the chronological ledger of previous tool executions for auditing and performance analysis.
        """
        return await service.get_tool_history(server_id, tool_name, limit)
