from typing import Any, Literal

from fastmcp import FastMCP

from meta_mcp.services.scheduler_service import SchedulerService


def register_scheduler_tools(mcp: FastMCP):
    """Register scheduler tool suite with FastMCP."""

    service = SchedulerService()

    @mcp.tool(name="scheduler_ops")
    async def scheduler_portmanteau(
        operation: Literal["schedule", "list", "cancel"],
        name: str | None = None,
        interval_seconds: int | None = None,
        server_id: str | None = None,
        tool_name: str | None = None,
        parameters: dict[str, Any] | None = None,
        description: str | None = None,
        task_id: str | None = None,
    ) -> dict[str, Any]:
        """Background task scheduling (portmanteau).

        [RATIONALE]
        Consolidates 3 related operations into a single tool to prevent tool explosion while enabling full API coverage.

        ## Operations
                - **schedule**: Register a recurring MCP tool execution
                - **list**: Show all active scheduled tasks
                - **cancel**: Remove a scheduled task by ID

        ## Return Format
        {"success": bool, "operation": str, "message": str}

        ## Examples








        a
        w
        a
        i
        t

        s
        c
        h
        e
        d
        u
        l
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
        c
        h
        e
        d
        u
        l
        e
        "
        )










        a
        w
        a
        i
        t

        s
        c
        h
        e
        d
        u
        l
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
        l
        i
        s
        t
        "
        )
        """
        if operation == "schedule":
            if not all([name, interval_seconds, server_id, tool_name]):
                return {"success": False, "error": "name, interval_seconds, server_id, tool_name required for schedule"}
            return await service.register_task(name, interval_seconds, server_id, tool_name, parameters, description)
        elif operation == "list":
            return await service.list_tasks()
        elif operation == "cancel":
            if not task_id:
                return {"success": False, "error": "task_id required for cancel"}
            return await service.cancel_task(task_id)
        return {"success": False, "error": f"Unknown operation: {operation}"}

    return service
