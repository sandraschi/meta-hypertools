from __future__ import annotations

from typing import Any

from meta_mcp.services.base import MetaMCPService
from meta_mcp.services.tool_result_codec import mcp_tool_to_catalog_entry, serialize_tool_result

_LOCAL_SERVER_IDS = frozenset(
    {
        "",
        "metaops",
        "meta-mcp",
        "meta_mcp",
        "metamcp",
        "local",
        "meta",
    }
)


def _is_local_meta_server(server_id: str | None) -> bool:
    return (server_id or "").strip().lower() in _LOCAL_SERVER_IDS


class ToolService(MetaMCPService):
    """
    Execute tools on the in-process Meta MCP FastMCP app (HTTP API use case).

    Remote MCP processes are not invoked here; use MCP clients from the host IDE instead.
    """

    async def execute_tool(
        self,
        server_id: str,
        tool_name: str,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run a registered tool on the local Meta MCP server."""
        if not _is_local_meta_server(server_id):
            return self.create_response(
                False,
                f"HTTP execution supports only the local Meta MCP app (server_id={server_id!r}).",
                {"hint": "Use server_id metaops, meta-mcp, or leave default."},
            )

        try:
            from meta_mcp.mcp_server import app as mcp_app

            raw = await mcp_app.call_tool(tool_name, parameters or {})
            payload = serialize_tool_result(raw)
            msg = f"Tool {tool_name} executed successfully"
            resp = self.create_response(True, msg, payload)
            resp["result"] = payload
            return resp
        except Exception as e:
            self.logger.exception("tool_execute_failed", tool=tool_name)
            err = self.create_response(False, f"Tool execution failed: {e}", {"error": str(e)})
            err["result"] = {"success": False, "message": "Operation failed", "error": str(e)}
            return err

    async def list_server_tools(self, server_id: str) -> dict[str, Any]:
        """List tools with JSON Schema parameters for the local Meta MCP app."""
        if not _is_local_meta_server(server_id):
            return self.create_response(
                False,
                f"Listing supports only the local Meta MCP app (server_id={server_id!r}).",
                {},
            )

        try:
            from meta_mcp.mcp_server import app as mcp_app

            listed = await mcp_app.list_tools()
            tools = [mcp_tool_to_catalog_entry(t) for t in listed]
            data = {"server_id": server_id, "tools": tools, "count": len(tools)}
            resp = self.create_response(True, f"Retrieved {len(tools)} tools from {server_id}", data)
            resp["result"] = data
            return resp
        except Exception as e:
            self.logger.exception("list_server_tools_failed")
            return self.create_response(False, f"Failed to list tools: {e}", {})

    async def validate_tool_parameters(
        self, server_id: str, tool_name: str, parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Light validation against the tool JSON Schema (local Meta MCP only)."""
        if not _is_local_meta_server(server_id):
            return self.create_response(False, f"Unsupported server_id: {server_id!r}")

        tools_result = await self.list_server_tools(server_id)
        if not tools_result.get("success"):
            return tools_result

        tools = (tools_result.get("data") or {}).get("tools", [])
        tool_info = next((t for t in tools if t.get("name") == tool_name), None)
        if not tool_info:
            return self.create_response(False, f"Tool {tool_name} not found on server {server_id}")

        schema = tool_info.get("inputSchema") or tool_info.get("parameters")
        if not isinstance(schema, dict) or "properties" not in schema:
            return self.create_response(True, "No JSON Schema properties; skipping validation")

        validation_errors: list[str] = []
        props = schema.get("properties") or {}
        required = set(schema.get("required") or [])

        for param_name, prop in props.items():
            if not isinstance(prop, dict):
                continue
            typ = prop.get("type")
            if param_name in required and param_name not in parameters:
                validation_errors.append(f"Missing required parameter: {param_name}")
                continue
            if param_name not in parameters:
                continue
            value = parameters[param_name]
            if typ == "integer" and value is not None and not isinstance(value, int):
                if isinstance(value, str) and value.isdigit():
                    continue
                validation_errors.append(f"Parameter {param_name} must be an integer")
            elif typ == "number" and value is not None and not isinstance(value, (int, float)):
                validation_errors.append(f"Parameter {param_name} must be a number")
            elif typ == "string" and value is not None and not isinstance(value, str):
                validation_errors.append(f"Parameter {param_name} must be a string")
            elif typ == "boolean" and value is not None and not isinstance(value, bool):
                validation_errors.append(f"Parameter {param_name} must be a boolean")
            elif typ == "array" and value is not None and not isinstance(value, list):
                validation_errors.append(f"Parameter {param_name} must be an array")

        if validation_errors:
            return self.create_response(False, "Parameter validation failed", {"errors": validation_errors})

        return self.create_response(True, "Parameters validated successfully")

    async def get_tool_history(self, server_id: str, tool_name: str | None = None, limit: int = 10) -> dict[str, Any]:
        """Execution history is not persisted in-process; return an empty placeholder."""
        return self.create_response(
            True,
            "No persistent tool history in the HTTP bridge (in-process Meta MCP).",
            {
                "server_id": server_id,
                "tool_name": tool_name,
                "history": [],
                "count": 0,
                "limit": limit,
            },
        )

    async def get_mcp_catalog(self) -> dict[str, Any]:
        """Full tool catalog with JSON Schema for web UI forms."""
        return await self.list_server_tools("metaops")
