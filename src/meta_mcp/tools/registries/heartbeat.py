from typing import Any, Literal

from fastmcp import FastMCP

from meta_mcp.services.heartbeat_service import HeartbeatService
from meta_mcp.services.pipeline_liveness_service import PipelineLivenessService


def register_heartbeat_tools(mcp: FastMCP):
    """Register heartbeat tool suite with FastMCP."""

    service = HeartbeatService()
    pipeline_service = PipelineLivenessService()

    @mcp.tool(name="heartbeat_ops")
    async def heartbeat_portmanteau(
        operation: Literal["pulse", "ping", "liveness", "proactive"],
        detailed: bool = False,
        stale_hours: int = 48,
        interval_hours: int = 6,
    ) -> dict[str, Any]:
        """System health monitoring (portmanteau).

        [RATIONALE]
        Consolidates 4 related operations into a single tool to prevent tool explosion while enabling full API coverage.

        ## Operations
                - **pulse**: Generate a system health summary
                - **ping**: Verify connectivity to all fleet servers
                - **liveness**: Check open-weight pipeline liveness
                - **proactive**: Schedule automated health pulse

        ## Return Format
        {"success": bool, "operation": str, "message": str}

        ## Examples








        a
        w
        a
        i
        t

        h
        e
        a
        r
        t
        b
        e
        a
        t
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
        p
        u
        l
        s
        e
        "
        )










        a
        w
        a
        i
        t

        h
        e
        a
        r
        t
        b
        e
        a
        t
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
        p
        i
        n
        g
        "
        )
        """
        if operation == "pulse":
            return await service.get_pulse(detailed)
        elif operation == "ping":
            return await service.ping_fleet()
        elif operation == "liveness":
            return await pipeline_service.check_all(stale_hours=stale_hours)
        elif operation == "proactive":
            if hasattr(mcp, "scheduler_service") and mcp.scheduler_service:
                return await mcp.scheduler_service.register_task(
                    name="Proactive Heartbeat",
                    interval_seconds=interval_hours * 3600,
                    server_id="metaops",
                    tool_name="heartbeat_ops",
                    parameters={"operation": "pulse", "detailed": True},
                    description="Automated system heartbeat pulse log.",
                )
            return service.create_response(False, "Scheduler service not available.")
        return {"success": False, "error": f"Unknown operation: {operation}"}

    return service
