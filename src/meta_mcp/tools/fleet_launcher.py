from typing import Any

import structlog

from meta_mcp.services.fleet_runtime_service import FleetRuntimeService

from .decorators import ToolCategory, tool

logger = structlog.get_logger(__name__)

# Single instance for the application
runtime_service = FleetRuntimeService()


@tool(
    name="audit_fleet_runtime",
    description=("Deep audit of fleet webapp runtime: registry analysis, port ping, and health endpoint check."),
    category=ToolCategory.SYSTEM,
)
async def audit_fleet_runtime_tool() -> dict[str, Any]:
    """Audit the fleet runtime status."""
    return await runtime_service.audit_fleet()


@tool(
    name="start_fleet_app",
    description="Launch a fleet application by its ID using the central starts catalog.",
    category=ToolCategory.SYSTEM,
)
async def start_fleet_app_tool(app_id: str) -> dict[str, Any]:
    """Start a fleet application."""
    return await runtime_service.start_app(app_id)


@tool(
    name="stop_fleet_app",
    description="Stop a fleet application by killing the process listening on its registered port.",
    category=ToolCategory.SYSTEM,
)
async def stop_fleet_app_tool(app_id: str) -> dict[str, Any]:
    """Stop a fleet application."""
    return await runtime_service.stop_app(app_id)


# For backward compatibility (optional but good practice during migration)
@tool(
    name="list_fleet_apps",
    description="List all available fleet web applications (Shortcut for audit_fleet_runtime).",
    category=ToolCategory.SYSTEM,
)
async def list_fleet_apps_tool() -> dict[str, Any]:
    """List fleet apps (Legacy wrapper for audit)."""
    return await runtime_service.audit_fleet()


@tool(
    name="launch_fleet_app",
    description="Launch a fleet web application (Shortcut for start_fleet_app).",
    category=ToolCategory.SYSTEM,
)
async def launch_fleet_app_tool(app_id: str) -> dict[str, Any]:
    """Launch a fleet app (Legacy wrapper for start)."""
    return await runtime_service.start_app(app_id)
