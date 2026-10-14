from typing import Any, Literal

from fastmcp import FastMCP

from meta_mcp.services.fleet_cold_install_service import FleetColdInstallService
from meta_mcp.services.fleet_runtime_service import FleetRuntimeService
from meta_mcp.services.fleet_startup_probe_service import FleetStartupProbeService
from meta_mcp.services.mcp_protocol_probe_service import McpProtocolProbeService


def register_fleet_tools(mcp: FastMCP):
    """Register industrial fleet management tools with FastMCP."""

    service = FleetRuntimeService()
    probe_service = FleetStartupProbeService()
    cold_install_service = FleetColdInstallService()
    protocol_probe_service = McpProtocolProbeService()

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
            "protocol_probe",
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
        url: str | None = None,
    ) -> dict[str, Any]:
        """Fleet application lifecycle and probing (portmanteau).

        [RATIONALE]
        Consolidates 8 related operations into a single tool to prevent tool explosion while enabling full API coverage.

        ## Operations
        - **status**: Audit all fleet apps
        - **launch**: Start a fleet app via its start.ps1
        - **stop**: Stop a fleet app by its port
        - **startup_probe**: Cold-start probe: parse start.ps1, health check
        - **startup_report**: Load the latest startup probe report
        - **install_probe**: Cold-install probe: preflight, mcpb, stdio smoke
        - **install_report**: Load the latest install probe report
        - **protocol_probe**: Check stateless-MCP2 vs legacy compat for a streamable-HTTP `/mcp` URL (wraps `mcp-explorer doctor` via `uvx`). Requires `url`.

        ## Return Format
        {"success": bool, "operation": str, "message": str}

        ## Examples
        await fleet_ops(operation="status")
        await fleet_ops(operation="launch")
        await fleet_ops(operation="protocol_probe", url="http://127.0.0.1:10718/mcp")
        """
        if operation == "protocol_probe":
            return protocol_probe_service.doctor(url or "")
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
