from typing import Any, Literal

from fastmcp import FastMCP

from meta_mcp.services.fleet_cold_install_service import FleetColdInstallService
from meta_mcp.services.fleet_runtime_service import FleetRuntimeService
from meta_mcp.services.fleet_startup_probe_service import FleetStartupProbeService


def register_fleet_tools(mcp: FastMCP):
    """Register industrial fleet management tools with FastMCP."""

    service = FleetRuntimeService()
    probe_service = FleetStartupProbeService()
    cold_install_service = FleetColdInstallService()

    @mcp.tool(name="fleet_ops")
    async def fleet_ops(
        operation: Literal[
            "status",
            "launch",
            "stop",
            "startup_probe",
            "startup_report",
            "install_probe",
            "install_report",
        ],
        app_id: str | None = None,
        repo_filter: str = "",
        background: bool = True,
        broken_only: bool = False,
        preflight_only: bool = True,
        execute: bool = False,
        test_mcpb: bool = False,
        host_mcpb_smoke: bool = False,
        batch_size: int = 0,
        mcp_clients: str = "",
    ) -> dict[str, Any]:
        """Fleet application lifecycle and probing (portmanteau).

        [RATIONALE]
        Consolidates 7 related operations into a single tool to prevent tool explosion while enabling full API coverage.

        ## Operations
        - **status**: Audit all fleet apps
        - **launch**: Start a fleet app via its start.ps1
        - **stop**: Stop a fleet app by its port
        - **startup_probe**: Cold-start probe: parse start.ps1, health check
        - **startup_report**: Load the latest startup probe report
        - **install_probe**: Cold-install probe: preflight, mcpb, stdio smoke
        - **install_report**: Load the latest install probe report

        ## Return Format
        {"success": bool, "operation": str, "message": str}

        ## Examples
        await fleet_ops(operation="status")
        await fleet_ops(operation="launch")
        """
        if operation == "status":
            return await service.audit_fleet()
        elif operation == "launch":
            return await service.start_app(app_id)
        elif operation == "stop":
            return await service.stop_app(app_id)
        elif operation == "startup_probe":
            return probe_service.run_probe(repo_filter=repo_filter, background=background)
        elif operation == "startup_report":
            return probe_service.get_report()
        elif operation == "install_probe":
            return cold_install_service.run_probe(
                repo_filter=repo_filter,
                broken_only=broken_only,
                background=background,
                preflight_only=preflight_only,
                execute=execute,
                test_mcpb=test_mcpb,
                host_mcpb_smoke=host_mcpb_smoke,
                batch_size=batch_size,
                mcp_clients=mcp_clients,
            )
        elif operation == "install_report":
            return cold_install_service.get_report()
