import datetime
import os
import platform
from typing import Any

import structlog

from meta_mcp.services.base import MetaMCPService
from meta_mcp.services.server_service import ServerService
from meta_mcp.services.tool_service import ToolService

logger = structlog.get_logger(__name__)


class HeartbeatService(MetaMCPService):
    """
    OpenClaw-inspired service for proactive system monitoring and health checks.
    Aggregates data from across the MCP fleet and local system.
    """

    def __init__(self):
        super().__init__()
        self.server_service = ServerService()
        self.tool_service = ToolService()

    async def get_pulse(self, detailed: bool = False) -> dict[str, Any]:
        """
        Generate a 'pulse' summary of the entire system state.
        """
        try:
            now = datetime.datetime.now()

            # 1. Local System Health
            node_label = os.getenv("META_MCP_NODE_LABEL", "").strip() or platform.node()
            health = {
                "timestamp": now.isoformat(),
                "node": node_label,
                "os": f"{platform.system()} {platform.release()}",
                "status": "nominal",
            }

            # 2. MCP Fleet Status
            servers_result = await self.server_service.list_running_servers()
            fleet_info = {"total": 0, "active": 0, "failed": 0}
            if servers_result.get("success"):
                servers = servers_result.get("data", {}).get("servers", [])
                fleet_info["total"] = len(servers)
                fleet_info["active"] = len([s for s in servers if s.get("status") == "running"])
                fleet_info["failed"] = len([s for s in servers if s.get("status") == "failed"])

            pulse_data = {
                "system": health,
                "fleet": fleet_info,
            }

            return self.create_response(True, "Pulse generated", pulse_data)

        except Exception as e:
            logger.error("Failed to generate pulse", error=str(e))
            return self.create_response(False, f"Pulse failed: {e!s}")

    async def ping_fleet(self) -> dict[str, Any]:
        """
        Check connectivity for every running MCP server.
        """
        try:
            servers_result = await self.server_service.list_running_servers()
            results = []

            if not servers_result.get("success"):
                return servers_result

            servers = servers_result.get("data", {}).get("servers", [])
            for server in servers:
                server_id = server.get("id")
                # Try to list tools as a connectivity test
                test = await self.tool_service.list_server_tools(server_id)
                results.append(
                    {
                        "server_id": server_id,
                        "reachable": test.get("success"),
                        "latency": test.get("data", {}).get("execution_time", 0) if test.get("success") else None,
                    }
                )

            return self.create_response(True, "Fleet ping completed", {"results": results})

        except Exception as e:
            logger.error("Fleet ping failed", error=str(e))
            return self.create_response(False, f"Fleet ping failed: {e!s}")
