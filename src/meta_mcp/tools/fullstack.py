"""
Fullstack Application Builder for MetaMCP.
Wraps the SOTA Fullstack App Builder PowerShell script.
"""

import asyncio
from pathlib import Path
from typing import Any

from .decorators import ToolCategory, tool


@tool(
    name="create_fullstack_app",
    description="""Scaffold a new production-ready fullstack application.

    Creates a modern web application with:
    - React/Next.js frontend
    - FastMCP server backend
    - AI ChatBot features
    - MCP Client dashboard
    - Monitoring and CI/CD setup""",
    category=ToolCategory.DEVELOPMENT,
    tags=["fullstack", "webapp", "scaffold", "react"],
    estimated_runtime="30-60s",
)
async def create_fullstack_app_tool(
    name: str,
    description: str = "A modern fullstack application",
    author: str = "Developer",
    target_path: str = "./apps",
    include_ai: bool = True,
    include_mcp: bool = True,
    include_mcp_server: bool = True,
    include_pwa: bool = True,
    include_monitoring: bool = True,
) -> dict[str, Any]:
    """Scaffold a new fullstack application."""
    builder = FullstackAppBuilder()
    return await builder.create_app(
        app_name=name,
        description=description,
        author=author,
        output_path=target_path,
        include_ai=include_ai,
        include_mcp=include_mcp,
        include_mcp_server=include_mcp_server,
        include_pwa=include_pwa,
        include_monitoring=include_monitoring,
    )


class FullstackAppBuilder:
    """
    Orchestrates the creation of production-ready fullstack applications.
    """

    def __init__(self, script_path: Path | None = None):
        # Default to the known location if not provided
        self.script_path = script_path or Path("d:/Dev/repos/meta_mcp/scripts/fullstack-builder.ps1")

    async def create_app(
        self,
        app_name: str,
        description: str = "A modern fullstack application",
        author: str = "SOTA Builder",
        output_path: str = ".",
        config: dict[str, Any] | None = None,
        config_path: str | None = None,
        include_ai: bool = True,
        include_mcp: bool = True,
        include_pwa: bool = True,
        include_monitoring: bool = True,
        include_mcp_server: bool = True,
    ) -> dict[str, Any]:
        """
        Scaffold a new fullstack application using the PowerShell script.
        """
        if not self.script_path.exists():
            return {
                "success": False,
                "message": "Operation failed",
                "error": f"Builder script not found at {self.script_path}",
            }

        # Build PowerShell command
        # We use -Interactive:$false to ensure it runs non-interactively
        cmd = [
            "pwsh",
            "-File",
            str(self.script_path),
            "-AppName",
            app_name,
            "-Description",
            description,
            "-Author",
            author,
            "-OutputPath",
            output_path,
            "-Interactive:$false",
        ]

        # Handle advanced configuration from JSON
        if config_path:
            cmd.extend(["-ConfigPath", config_path])
        elif config:
            # We would typically write this to a temp file and pass it
            # For now, let's assume the PS script can handle a JSON string or we handle it here
            import json
            import tempfile

            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                json.dump(config, f)
                temp_config_path = f.name
                cmd.extend(["-ConfigPath", temp_config_path])
                # We should handle cleanup of this temp file later

        # Add feature flags
        if include_ai:
            cmd.append("-IncludeAI")
        if include_mcp:
            cmd.append("-IncludeMCP")
        if include_pwa:
            cmd.append("-IncludePWA")
        if include_monitoring:
            cmd.append("-IncludeMonitoring")
        if include_mcp_server:
            cmd.append("-IncludeMCPServer")

        try:
            # Run the script in the background
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                return {
                    "success": True,
                    "app_path": str(Path(output_path) / app_name),
                    "message": f"Fullstack application '{app_name}' created successfully.",
                }
            else:
                return {
                    "success": False,
                    "message": "Operation failed",
                    "error": stderr.decode().strip() or stdout.decode().strip(),
                    "exit_code": process.returncode,
                }

        except Exception as e:
            return {"success": False, "message": "Operation failed", "error": str(e)}
