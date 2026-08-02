from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from meta_mcp.services.capability_router import CapabilityRouter


def register_capability_router_tools(mcp: FastMCP):
    """Register dynamic capability routing suite with FastMCP."""

    router = CapabilityRouter()

    @mcp.tool(name="meta_route_scan")
    async def meta_route_scan(
        force: Annotated[
            bool,
            Field(description="Force a full rebuild of the capability index even if it is fresh"),
        ] = False,
    ) -> dict[str, Any]:
        """Scan the fleet and rebuild the tool-to-server capability index.

        Crawls all repos under the configured repos root, extracts registered
        MCP tool names from Python source decorators and pyproject.toml scripts,
        and stores them in a lightweight SQLite routing table for sub-second lookup.

        ## Return Format
        {
          "success": bool,
          "message": str,
          "data": {"repos_scanned": int, "tools_indexed": int, "server_count": int, "servers": [str]}
        }

        ## Examples
            meta_route_scan()
            meta_route_scan(force=True)
        """
        return await router.scan_fleet(force=force)

    @mcp.tool(name="meta_route_tool")
    async def meta_route_tool(
        tool_name: Annotated[str, Field(description="Name of the MCP tool to invoke on the target server")],
        arguments: Annotated[
            dict[str, Any] | None,
            Field(description="Tool arguments as a dict of parameter names to values"),
        ] = None,
        target_server: Annotated[
            str | None,
            Field(description="Specific server name to route to. If omitted, searched by tool_name"),
        ] = None,
    ) -> dict[str, Any]:
        """Dynamic tool routing proxy -- invoke any fleet MCP tool on demand.

        [RATIONALE]
        Consolidates fleet-wide tool access into a single lazy-loading proxy endpoint.
        The LLM calls this tool instead of statically connecting to 130+ individual
        MCP servers, which would saturate the context window. This portmanteau
        proxies tool calls to the correct fleet server, hot-starting it via subprocess
        if not already running.

        ## Operations
        - **Specify target_server**: fastest path -- looks up the server's port directly
        - **Specify tool_name alone**: searches the capability index for all servers
          that provide the tool, picks the best match, starts its backend if needed,
          and proxies the call

        ## Return Format
        {
          "success": bool,
          "message": str,
          "data": { ... }
        }

        On success, data contains the proxied MCP JSON-RPC response from the target server.
        On failure, message describes the error and data.suggestions offers recovery steps.

        ## Examples
            meta_route_tool(tool_name="search_papers", arguments={"query": "transformers", "limit": 5})
            meta_route_tool(tool_name="list_emails", arguments={"folder": "INBOX"}, target_server="email-mcp")
        """
        return await router.route_tool(
            tool_name=tool_name,
            arguments=arguments,
            target_server=target_server,
        )

    @mcp.tool(name="meta_route_list")
    async def meta_route_list(
        server_name: Annotated[str | None, Field(description="Filter capabilities by server name")] = None,
        tool_query: Annotated[str | None, Field(description="Filter capabilities by tool name substring")] = None,
        operation: Annotated[
            Literal["list", "lookup"],
            Field(description="Operation: 'list' for browsing, 'lookup' for lookup by name"),
        ] = "list",
        tool_name: Annotated[
            str | None, Field(description="Exact tool name to look up (for operation='lookup')")
        ] = None,
        limit: Annotated[int, Field(description="Maximum number of results to return")] = 50,
    ) -> dict[str, Any]:
        """Browse and search the dynamic routing capability index.

        [RATIONALE]
        Consolidates capability listing and tool lookup into one portmanteau
        so agents can discover available fleet tools and locate which server
        provides each one without flooding the context window.

        ## Operations
        - **list**: Browse capabilities by server or tool name filter
        - **lookup**: Find which servers provide a specific tool name

        ## Return Format
        {
          "success": bool,
          "message": str,
          "data": {
            "server_count": int,
            "tool_count": int,
            "capabilities": [{"tool_name": str, "server_name": str, "port": int, "description": str}]
          }
        }

        ## Examples
            meta_route_list(operation="list", tool_query="search")
            meta_route_list(operation="lookup", tool_name="get_paper_details")
            meta_route_list(operation="list", server_name="email-mcp")
        """
        if operation == "lookup" and tool_name:
            matches = await router.lookup_tool(tool_name)
            return {
                "success": True,
                "message": f"Found {len(matches)} server(s) for tool '{tool_name}'",
                "data": {
                    "tool_name": tool_name,
                    "matches": [m.as_dict() for m in matches],
                    "count": len(matches),
                },
            }
        return await router.list_capabilities(
            server_name=server_name,
            tool_query=tool_query,
            limit=limit,
        )

    @mcp.tool(name="meta_route_status")
    async def meta_route_status() -> dict[str, Any]:
        """Report the current state of the dynamic routing index.

        Returns a summary of the capability index: when it was last rebuilt,
        how many tools and servers are indexed, and operational health.

        ## Return Format
        {"success": bool, "message": str, "data": {"fresh": bool, "tool_count": int, "server_count": int}}

        ## Examples
            meta_route_status()
        """
        caps = await router.list_capabilities(limit=1)
        if not caps.get("success"):
            return caps
        tool_count = caps["data"].get("tool_count", 0)
        return {
            "success": True,
            "message": f"Capability router active: {tool_count} tools indexed",
            "data": caps["data"],
        }
