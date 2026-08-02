from typing import Any, Literal

from fastmcp import FastMCP

from meta_mcp.services.server_service import ServerService


def register_server_management_tools(mcp: FastMCP):
    """Register server management tool suite with FastMCP."""

    service = ServerService()

    @mcp.tool(name="server_ops")
    async def server_portmanteau(
        operation: Literal["start", "stop", "list", "status"],
        server_path: str | None = None,
        server_type: str = "python",
        server_id: str | None = None,
    ) -> dict[str, Any]:
        """MCP server process lifecycle (portmanteau).

        [RATIONALE]
        Consolidates 4 related operations into a single tool to prevent tool explosion while enabling full API coverage.

        ## Operations
                - **start**: Launch an MCP server process
                - **stop**: Terminate a running MCP server
                - **list**: List all running MCP servers
                - **status**: Get detailed status for one server

        ## Return Format
        {"success": bool, "operation": str, "message": str}

        ## Examples








        a
        w
        a
        i
        t

        s
        e
        r
        v
        e
        r
        _
        o
        p
        s
        (
        o
        p
        e
        r
        a
        t
        i
        o
        n
        =
        "
        s
        t
        a
        r
        t
        "
        )










        a
        w
        a
        i
        t

        s
        e
        r
        v
        e
        r
        _
        o
        p
        s
        (
        o
        p
        e
        r
        a
        t
        i
        o
        n
        =
        "
        s
        t
        o
        p
        "
        )
        """
        if operation == "start":
            if not server_path:
                return {"success": False, "error": "server_path required"}
            return await service.start_server(server_path, server_type)
        elif operation == "stop":
            if not server_id:
                return {"success": False, "error": "server_id required"}
            return await service.stop_server(server_id)
        elif operation == "list":
            return await service.list_running_servers()
        elif operation == "status":
            if not server_id:
                return {"success": False, "error": "server_id required"}
            return await service.get_server_status(server_id)
        return {"success": False, "error": f"Unknown operation: {operation}"}
