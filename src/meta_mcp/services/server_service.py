import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from meta_mcp.services.base import MetaMCPService


class ServerService(MetaMCPService):
    """
    Service for managing MCP server lifecycle and execution.

    Provides capabilities to start, stop, monitor, and execute tools
    on MCP servers discovered in the system.
    """

    def __init__(self):
        self.running_servers: dict[str, subprocess.Popen] = {}
        self.server_status: dict[str, dict[str, Any]] = {}

    async def start_server(self, server_path: str, server_type: str = "python") -> dict[str, Any]:
        """Start an MCP server process."""
        try:
            server_path_obj = Path(server_path)

            if not server_path_obj.exists():
                return self.create_response(False, f"Server file not found: {server_path}")

            if server_type == "python":
                cmd = [sys.executable, str(server_path_obj)]
            else:
                return self.create_response(False, f"Unsupported server type: {server_type}")

            # Start the process
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=server_path_obj.parent,
                text=True,
            )

            server_id = f"{server_type}:{server_path}"

            self.running_servers[server_id] = process
            self.server_status[server_id] = {
                "status": "starting",
                "pid": process.pid,
                "start_time": self.get_timestamp(),
            }

            return self.create_response(
                True,
                f"Server started with PID {process.pid}",
                {"server_id": server_id, "pid": process.pid, "status": "starting"},
            )

        except Exception as e:
            return self.create_response(False, f"Failed to start server: {e!s}")

    async def stop_server(self, server_id: str) -> dict[str, Any]:
        """Stop a running MCP server."""
        try:
            if server_id not in self.running_servers:
                return self.create_response(False, f"Server not found: {server_id}")

            process = self.running_servers[server_id]
            process.terminate()

            # Wait for graceful shutdown
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

            # Clean up
            del self.running_servers[server_id]
            if server_id in self.server_status:
                self.server_status[server_id]["status"] = "stopped"
                self.server_status[server_id]["end_time"] = self.get_timestamp()

            return self.create_response(True, f"Server {server_id} stopped successfully")

        except Exception as e:
            return self.create_response(False, f"Failed to stop server: {e!s}")

    async def list_running_servers(self) -> dict[str, Any]:
        """List all currently running MCP servers."""
        running = []
        for server_id, process in self.running_servers.items():
            status_info = self.server_status.get(server_id, {})
            running.append(
                {
                    "server_id": server_id,
                    "pid": process.pid,
                    "status": status_info.get("status", "unknown"),
                    "start_time": status_info.get("start_time"),
                    "poll_status": process.poll(),  # None if running, else exit code
                }
            )

        return self.create_response(
            True,
            f"Found {len(running)} running servers",
            {"servers": running, "count": len(running)},
        )

    async def get_server_status(self, server_id: str) -> dict[str, Any]:
        """Get detailed status of a specific server."""
        if server_id not in self.running_servers:
            return self.create_response(False, f"Server not running: {server_id}")

        process = self.running_servers[server_id]
        status_info = self.server_status.get(server_id, {})

        return self.create_response(
            True,
            f"Server {server_id} status retrieved",
            {
                "server_id": server_id,
                "pid": process.pid,
                "status": status_info.get("status", "unknown"),
                "start_time": status_info.get("start_time"),
                "is_alive": process.poll() is None,
                "exit_code": process.poll(),
            },
        )

    async def execute_tool_on_server(
        self, server_id: str, tool_name: str, parameters: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a tool on a running MCP server."""
        # This is a simplified implementation - in a real system you'd need
        # to establish MCP protocol communication with the running server
        return self.create_response(False, "Tool execution not yet implemented - requires MCP protocol client")

    async def inspect_server(self, command: str, args: list[str], env: dict[str, str] | None = None) -> dict[str, Any]:
        """
        Inspect an MCP server configuration by connecting and listing capabilities.
        Connects via stdio, initializes, lists tools/resources/prompts, and disconnects.
        """
        try:
            # Prepare environment
            server_env = os.environ.copy()
            if env:
                server_env.update(env)

            # Create server parameters
            server_params = StdioServerParameters(command=command, args=args, env=server_env)

            # Connect and inspect
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    # List tools
                    try:
                        tools_result = await session.list_tools()
                        tools = [
                            {
                                "name": t.name,
                                "description": t.description,
                                "inputSchema": t.inputSchema,
                            }
                            for t in tools_result.tools
                        ]
                    except Exception:
                        tools = []

                    # List resources
                    try:
                        resources_result = await session.list_resources()
                        resources = [
                            {
                                "uri": str(r.uri),
                                "name": r.name,
                                "description": r.description,
                                "mimeType": r.mimeType,
                            }
                            for r in resources_result.resources
                        ]
                    except Exception:
                        resources = []

                    # List prompts
                    try:
                        prompts_result = await session.list_prompts()
                        prompts = [
                            {
                                "name": p.name,
                                "description": p.description,
                                "arguments": [
                                    {
                                        "name": a.name,
                                        "description": a.description,
                                        "required": a.required,
                                    }
                                    for a in (p.arguments or [])
                                ],
                            }
                            for p in prompts_result.prompts
                        ]
                    except Exception:
                        prompts = []

                    return self.create_response(
                        True,
                        "Server inspection successful",
                        {"tools": tools, "resources": resources, "prompts": prompts},
                    )

        except Exception as e:
            return self.create_response(False, f"Server inspection failed: {e!s}")
