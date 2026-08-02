"""Proxy Fritz (fleet-agent-mcp) and RoboFang REST/MCP surfaces for the MetaMCP dashboard."""

from __future__ import annotations

import os
from typing import Any

import httpx
from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

from meta_mcp.services.base import MetaMCPService
from meta_mcp.services.tool_result_codec import serialize_tool_result

FRITZ_HTTP_BASE = os.environ.get("FRITZ_HTTP_BASE", "http://127.0.0.1:10996").rstrip("/")
FRITZ_MCP_URL = os.environ.get("FRITZ_MCP_URL", f"{FRITZ_HTTP_BASE}/mcp/").rstrip("/") + "/"
ROBOFANG_HTTP_BASE = os.environ.get("ROBOFANG_HTTP_BASE", "http://127.0.0.1:10870").rstrip("/")

COWORKER_TOOLS = (
    "coworker_fleet_pulse",
    "coworker_inbox_briefing",
    "coworker_day_prep",
    "coworker_docs_drift",
    "coworker_weekly_report_pdf",
    "coworker_board_pack",
    "coworker_cursor_spend_watch",
    "coworker_artifact_pack",
    "coworker_bootstrap",
)


class AgentHubService(MetaMCPService):
    """Read Fritz/RoboFang status and trigger coworker flows from the web dashboard."""

    def __init__(self) -> None:
        super().__init__()
        self._timeout = httpx.Timeout(30.0, connect=5.0)

    async def _get_json(self, url: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, dict) else {"data": data}

    async def _post_json(self, url: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(url, json=body or {})
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, dict) else {"data": data}

    async def _fritz_mcp_call(self, tool: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        transport = StreamableHttpTransport(FRITZ_MCP_URL)
        async with Client(transport) as client:
            result = await client.call_tool(tool, arguments or {})
            payload = serialize_tool_result(result)
            if isinstance(payload, dict):
                return payload
            return {"success": True, "result": payload}

    async def get_fritz_overview(self) -> dict[str, Any]:
        online = False
        status: dict[str, Any] = {}
        whoami: dict[str, Any] = {}
        tasks: dict[str, Any] = {}
        tools: dict[str, Any] = {}
        errors: list[str] = []

        try:
            status = await self._get_json(f"{FRITZ_HTTP_BASE}/api/status")
            online = True
        except Exception as exc:
            errors.append(f"status: {exc}")

        if online:
            for label, path, bucket in (
                ("whoami", "/api/whoami", "whoami"),
                ("tasks", "/api/tasks", "tasks"),
                ("tools", "/api/tools", "tools"),
            ):
                try:
                    data = await self._get_json(f"{FRITZ_HTTP_BASE}{path}")
                    if bucket == "whoami":
                        whoami = data
                    elif bucket == "tasks":
                        tasks = data
                    else:
                        tools = data
                except Exception as exc:
                    errors.append(f"{label}: {exc}")

        flows: dict[str, Any] = {}
        if online:
            try:
                flows = await self._fritz_mcp_call("coworker_list_flows")
            except Exception as exc:
                errors.append(f"flows: {exc}")

        return self.create_response(
            online,
            "Fritz online" if online else "Fritz offline  start fleet-agent-mcp on :10996",
            {
                "online": online,
                "base_url": FRITZ_HTTP_BASE,
                "mcp_url": FRITZ_MCP_URL,
                "status": status,
                "whoami": whoami,
                "tasks": tasks,
                "tools": tools,
                "flows": flows,
                "coworker_tools": list(COWORKER_TOOLS),
                "errors": errors,
            },
            errors=errors or None,
        )

    async def run_fritz_coworker(self, tool: str, deliver: bool = True) -> dict[str, Any]:
        if tool not in COWORKER_TOOLS:
            return self.create_response(
                False,
                f"Unknown coworker tool: {tool}",
                {"allowed": list(COWORKER_TOOLS)},
            )
        args: dict[str, Any] = {}
        if tool != "coworker_bootstrap" and tool != "coworker_list_flows":
            args["deliver"] = deliver
        try:
            result = await self._fritz_mcp_call(tool, args)
            ok = bool(result.get("success", True))
            return self.create_response(ok, result.get("message", f"Ran {tool}"), result)
        except Exception as exc:
            self.logger.exception("fritz_coworker_failed", tool=tool)
            return self.create_response(False, f"Fritz tool failed: {exc}", {"error": str(exc)})

    async def get_robofang_overview(self) -> dict[str, Any]:
        online = False
        health: dict[str, Any] = {}
        status: dict[str, Any] = {}
        hands: dict[str, Any] = {}
        routines: dict[str, Any] = {}
        errors: list[str] = []

        health_paths = (
            f"{ROBOFANG_HTTP_BASE}/api/system/health",
            f"{ROBOFANG_HTTP_BASE}/health",
        )
        for path in health_paths:
            try:
                health = await self._get_json(path)
                online = True
                break
            except Exception as exc:
                errors.append(f"{path}: {exc}")

        if online:
            for label, path, bucket in (
                ("status", "/api/system/status", "status"),
                ("hands", "/api/hands", "hands"),
                ("routines", "/api/routines", "routines"),
            ):
                try:
                    data = await self._get_json(f"{ROBOFANG_HTTP_BASE}{path}")
                    if bucket == "status":
                        status = data
                    elif bucket == "hands":
                        hands = data
                    else:
                        routines = data
                except Exception as exc:
                    errors.append(f"{label}: {exc}")

        return self.create_response(
            online,
            "RoboFang online" if online else "RoboFang offline  start robofang-hub on :10870",
            {
                "online": online,
                "base_url": ROBOFANG_HTTP_BASE,
                "health": health,
                "status": status,
                "hands": hands,
                "routines": routines,
                "errors": errors,
            },
            errors=errors or None,
        )

    async def run_robofang_routine(self, routine_id: str) -> dict[str, Any]:
        try:
            result = await self._post_json(f"{ROBOFANG_HTTP_BASE}/api/routines/{routine_id}/run")
            ok = bool(result.get("success", True))
            return self.create_response(ok, result.get("message", f"Routine {routine_id} started"), result)
        except Exception as exc:
            self.logger.exception("robofang_routine_failed", routine_id=routine_id)
            return self.create_response(False, f"RoboFang routine failed: {exc}", {"error": str(exc)})
