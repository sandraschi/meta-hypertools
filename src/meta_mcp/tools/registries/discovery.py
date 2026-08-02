from typing import Any, Literal

from fastmcp import FastMCP

from meta_mcp.services.discovery_service import DiscoveryService


def register_discovery_tools(mcp: FastMCP):
    """Register discovery tool suite with FastMCP."""

    service = DiscoveryService()

    @mcp.tool(name="discovery_ops")
    async def discovery_ops(
        operation: Literal["servers", "ide"],
        discovery_paths: list[str] | None = None,
        ide_name: str | None = None,
    ) -> list[dict[str, Any]] | dict[str, Any]:
        """MCP server and IDE integration discovery (portmanteau).

        [RATIONALE]
        Consolidates 2 related operations into a single tool to prevent tool explosion while enabling full API coverage.

        ## Operations
        - **servers**: Discover MCP servers on the local filesystem
        - **ide**: Audit a specific IDE's MCP integration status

        ## Return Format
        {"success": bool, "operation": str, "message": str}

        ## Examples
        await discovery_ops(operation="servers")
        await discovery_ops(operation="ide")
        """
        if operation == "servers":
            return await service.discover_servers(discovery_paths)
        elif operation == "ide":
            return await service.check_integration(ide_name)
