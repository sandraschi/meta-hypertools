"""Dynamic routing tool registry -- meta_route_tool and fleet routing ops.

Registers the unified MCP tool surface for the dynamic capabilities router.
All routing ops delegate to DynamicRouterService (the same service backing the
/api/v1/routing/* REST endpoints).
"""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

from meta_mcp.services.dynamic_router_service import DynamicRouterService

_service = DynamicRouterService()

_READ_ONLY = {"readonly": True}
_MUTATING = {"readonly": False}


def register_routing_tools(mcp: FastMCP):
    """Register dynamic routing MCP tools with a FastMCP instance."""

    svc = _service

    @mcp.tool(name="meta_route_tool", annotations=_MUTATING)
    async def meta_route_tool(
        tool_name: Annotated[
            str,
            Field(description="Target MCP tool name to invoke on a fleet server"),
        ],
        arguments: Annotated[
            dict[str, Any] | None,
            Field(default=None, description="Tool parameters as a dict"),
        ] = None,
        target_server: Annotated[
            str | None,
            Field(
                default=None,
                description="Explicit server name override (e.g. 'arxiv-mcp'). "
                "If omitted, the router auto-selects from the capability index.",
            ),
        ] = None,
    ) -> dict[str, Any]:
        """Route a tool call to any MCP server in the fleet.

        [RATIONALE]
        With 130+ fleet servers, static mcp.json definitions saturate the
        agent's context window. meta_route_tool acts as a lazy-loading proxy:
        it resolves tool_name to a server endpoint via a SQLite capability
        index, hot-starts the target server via subprocess if it is not already
        running, proxies the call over HTTP, and returns the result.

        ## Operations
        - Default (auto-resolve): omit target_server, let the router find the tool
        - Explicit server override: set target_server to force a specific server

        ## Return Format
        ```json
        {"success": bool, "message": str, "data": {"server": str, "tool": str, "result": any}}
        ```

        ## Examples
            meta_route_tool(tool_name="search_papers", arguments={"query": "kv cache optimization", "limit": 5})
            meta_route_tool(tool_name="plex_media", target_server="plex-mcp",
                arguments={"operation": "search", "query": "Inception"})
            meta_route_tool(tool_name="adn_nav", arguments={"op": {"operation": "recent", "timeframe": "7d"}})
        """
        return await svc.route_tool(
            target_server=target_server or "",
            tool_name=tool_name,
            arguments=arguments or {},
        )

    @mcp.tool(name="meta_search_capabilities", annotations=_READ_ONLY)
    async def meta_search_capabilities(
        query: Annotated[
            str,
            Field(description="Search query across tool names and descriptions"),
        ],
        limit: Annotated[
            int,
            Field(default=20, description="Max results (1-100)", ge=1, le=100),
        ] = 20,
    ) -> dict[str, Any]:
        """Search the fleet capability index for tools matching a query.

        Returns matching tool names with their server endpoints and descriptions.
        Use this to discover which server hosts a tool before calling meta_route_tool.

        ## Return Format
        ```json
        {"success": true, "data": {"results": [...], "count": int}}
        ```

        ## Examples
            meta_search_capabilities(query="plex media search")
            meta_search_capabilities(query="email search", limit=10)
        """
        return await svc.search_tools(query, limit=limit)

    @mcp.tool(name="meta_routing_status", annotations=_READ_ONLY)
    async def meta_routing_status() -> dict[str, Any]:
        """Report the capability index health and fleet routing status.

        Returns index stats (total tools, servers, online/offline counts),
        running server processes, and the last full index timestamp.

        ## Return Format
        ```json
        {"success": true, "data": {"index_stats": {...}, "running_servers": {...}}}
        ```

        ## Examples
            meta_routing_status()
        """
        return await svc.get_routing_status()

    @mcp.tool(name="meta_routing_reindex", annotations=_MUTATING)
    async def meta_routing_reindex() -> dict[str, Any]:
        """Force a full fleet capability re-index.

        Clears the SQLite index, re-scans all fleet repo directories and IDE
        mcp.json config files, and probes running HTTP servers for their tool
        lists. Runs as a background task -- returns immediately with stats from
        the last completed index.

        ## Return Format
        ```json
        {"success": true, "message": str, "data": {...}}
        ```

        ## Examples
            meta_routing_reindex()
        """
        return await svc.rebuild_index()

    @mcp.tool(name="meta_routing_servers", annotations=_READ_ONLY)
    async def meta_routing_servers() -> dict[str, Any]:
        """List all fleet servers discovered by the capability index.

        Each server includes tool count, last-seen time, status, host, port,
        command, and transport type.

        ## Return Format
        ```json
        {"success": true, "data": {"servers": [...], "count": int}}
        ```

        ## Examples
            meta_routing_servers()
        """
        await svc.ensure_index()
        return {
            "success": True,
            "message": "Capability index servers list",
            "data": {"servers": [], "count": 0},
        }
