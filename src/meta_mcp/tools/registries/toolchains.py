from typing import Any, Literal

from fastmcp import FastMCP

from meta_mcp.services.toolchains_service import ToolchainService


def register_toolchain_tools(mcp: FastMCP):
    """Register toolchain management tools with FastMCP."""

    service = ToolchainService()

    @mcp.tool(name="toolchain_ops")
    async def toolchain_portmanteau(
        operation: Literal["list", "create", "delete", "apply", "available"],
        name: str | None = None,
        servers: list[str] | None = None,
        description: str = "",
        toolchain_name: str | None = None,
        client_name: str | None = None,
    ) -> dict[str, Any]:
        """Toolchain preset management (portmanteau).

        [RATIONALE]
        Consolidates 5 related operations into a single tool to prevent tool explosion while enabling full API coverage.

        ## Operations
                - **list**: List saved toolchain presets
                - **create**: Create a new toolchain preset
                - **delete**: Delete a toolchain preset
                - **apply**: Apply a toolchain to a client
                - **available**: List servers available for toolchains

        ## Return Format
        {"success": bool, "operation": str, "message": str}

        ## Examples








        a
        w
        a
        i
        t

        t
        o
        o
        l
        c
        h
        a
        i
        n
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
        l
        i
        s
        t
        "
        )










        a
        w
        a
        i
        t

        t
        o
        o
        l
        c
        h
        a
        i
        n
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
        c
        r
        e
        a
        t
        e
        "
        )
        """
        if operation == "list":
            return await service.list_toolchains()
        elif operation == "create":
            if not name or not servers:
                return {"success": False, "error": "name and servers required"}
            return await service.create_toolchain(name, servers, description)
        elif operation == "delete":
            if not name:
                return {"success": False, "error": "name required"}
            return await service.delete_toolchain(name)
        elif operation == "apply":
            if not toolchain_name or not client_name:
                return {"success": False, "error": "toolchain_name and client_name required"}
            return await service.apply_toolchain(toolchain_name, client_name)
        elif operation == "available":
            return await service.get_available_servers()
        return {"success": False, "error": f"Unknown operation: {operation}"}
