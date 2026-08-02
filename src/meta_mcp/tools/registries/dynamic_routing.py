"""Dynamic capabilities routing tools  lazy-loading proxy for the MCP server fleet.

Registers the meta_route_tool portmanteau and supporting tools for the
dynamic routing layer. These tools allow an LLM agent to discover and invoke
tools on any fleet MCP server without preloading all 130+ server definitions.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from meta_mcp.services.dynamic_router_service import DynamicRouterService


def register_dynamic_routing_tools(mcp: FastMCP):
    """Register dynamic routing tools with FastMCP."""
    service = DynamicRouterService()

    @mcp.tool(
        name="meta_route_tool",
        annotations={"readOnlyHint": False, "destructiveHint": False},
    )
    async def meta_route_tool(
        target_server: Annotated[
            str,
            Field(
                description=(
                    "Target MCP server repo name (e.g. 'arxiv-mcp'). Use empty string to auto-discover from index."
                )
            ),
        ] = "",
        tool_name: Annotated[
            str,
            Field(description="Name of the tool to invoke on the target server."),
        ] = "",
        arguments: Annotated[
            dict[str, Any] | None,
            Field(description="Tool arguments as a JSON-compatible dict."),
        ] = None,
    ) -> dict[str, Any]:
        """Route a tool call to a fleet MCP server with automatic hot-start.

        [RATIONALE]
        Consolidates the fleet's 130+ MCP servers into a single lazy-loading proxy.
        The LLM agent discovers and invokes tools on any fleet server through one
        entry point, without preloading static mcp.json definitions that would
        saturate the context window.

        ## Operations
        - **Direct route**: Provide target_server + tool_name to route a call
        - **Auto-discovery**: Omit target_server to search the fleet index
        - **Status**: Use operation status below for routing health

        ## Return Format
        ```json
        {"success": bool, "message": str, "data": {"server": str, "tool": str, "result": any}}
        ```

        ## Examples
        ```python
        # Route a search to arxiv-mcp
        meta_route_tool(
            target_server="arxiv-mcp",
            tool_name="search_papers",
            arguments={"query": "attention mechanisms", "limit": 5},
        )

        # Auto-discover the right server for a tool
        meta_route_tool(tool_name="list_emails", arguments={"folder": "INBOX", "limit": 10})
        ```
        """
        return await service.route_tool(
            target_server=target_server,
            tool_name=tool_name,
            arguments=arguments or {},
        )

    @mcp.tool(
        name="routing_ops",
        annotations={"readOnlyHint": False, "destructiveHint": False},
    )
    async def routing_ops(
        operation: Literal[
            "status",
            "rebuild_index",
            "search_tools",
            "shutdown_servers",
        ],
        query: Annotated[
            str | None,
            Field(description="Search query for 'search_tools' operation (fuzzy keyword match)."),
        ] = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Dynamic routing management and fleet tool discovery.

        [RATIONALE]
        Provides operational control over the dynamic routing layer: index rebuild,
        semantic tool search across the fleet, and server lifecycle management.

        ## Operations
        - **status**: Index stats, server count, running processes
        - **rebuild_index**: Force a full fleet scan and index rebuild
        - **search_tools**: Fuzzy search for tools across all indexed servers
        - **shutdown_servers**: Terminate all managed sub-server processes

        ## Return Format
        ```json
        {"success": bool, "message": str, "data": {"index_stats": {...}, "running_servers": {...}}}
        ```

        ## Examples
        ```python
        routing_ops(operation="status")
        routing_ops(operation="search_tools", query="email search smtp")
        routing_ops(operation="rebuild_index")
        ```
        """
        if operation == "status":
            return await service.get_routing_status()
        elif operation == "rebuild_index":
            return await service.rebuild_index()
        elif operation == "search_tools":
            return await service.search_tools(query or "", limit)
        elif operation == "shutdown_servers":
            await service.shutdown()
            return {"success": True, "message": "All managed servers terminated"}
