#!/usr/bin/env python3
"""
MetaMCP REST API Router - Exposes MCP tools via HTTP endpoints.

Provides webapp-accessible REST API for all MCP tool operations.
"""

from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from meta_mcp.services.agent_hub_service import AgentHubService
from meta_mcp.services.analysis_service import AnalysisService
from meta_mcp.services.client_settings_manager import ClientSettingsManager

# Import service classes
from meta_mcp.services.diagnostics_service import DiagnosticsService
from meta_mcp.services.discovery_service import DiscoveryService

# Dynamic routing service (lazy-loading fleet proxy)
from meta_mcp.services.dynamic_router_service import DynamicRouterService
from meta_mcp.services.fleet_cold_install_service import FleetColdInstallService
from meta_mcp.services.fleet_runtime_service import FleetRuntimeService
from meta_mcp.services.fleet_startup_probe_service import FleetStartupProbeService
from meta_mcp.services.heartbeat_service import HeartbeatService
from meta_mcp.services.local_llm_service import LocalLLMService
from meta_mcp.services.repo_packing_service import RepoPackingService
from meta_mcp.services.repo_scanner_service import RepoScannerService
from meta_mcp.services.scaffolding_service import ScaffoldingService
from meta_mcp.services.scheduler_service import SchedulerService
from meta_mcp.services.server_service import ServerService
from meta_mcp.services.token_analysis_service import TokenAnalysisService
from meta_mcp.services.tool_service import ToolService
from meta_mcp.services.toolchains_service import ToolchainService

# Create router
router = APIRouter(prefix="/api/v1", tags=["mcp-tools"])

# Initialize services
diagnostics = DiagnosticsService()
analysis = AnalysisService()
discovery = DiscoveryService()
scaffolding = ScaffoldingService()
server_service = ServerService()
tool_service = ToolService()
repo_scanner = RepoScannerService()
client_manager = ClientSettingsManager()
token_analyzer = TokenAnalysisService()
repo_packer = RepoPackingService()
toolchain_service = ToolchainService()
scheduler_service = SchedulerService()
heartbeat_service = HeartbeatService()
fleet_runtime = FleetRuntimeService()
fleet_startup_probe = FleetStartupProbeService()
fleet_cold_install = FleetColdInstallService()
local_llm = LocalLLMService()
agent_hub = AgentHubService()
dynamic_router = DynamicRouterService()


# Request/Response Models
class ToolRequest(BaseModel):
    """Base model for tool requests."""

    operation: str = Field(..., description="Tool operation to perform")
    repo_path: str | None = Field(None, description="Repository path for operations")


class ServerInspectRequest(BaseModel):
    """Request model for server inspection."""

    command: str
    args: list[str]
    env: dict[str, str] | None = None


class EmojiBusterRequest(ToolRequest):
    """Request model for EmojiBuster operations."""

    scan_mode: str = Field("comprehensive", description="Scan mode: basic, comprehensive, or thorough")
    auto_fix: bool = Field(False, description="Whether to automatically fix issues")
    backup: bool = Field(True, description="Whether to create backups before fixing")


class PowerShellRequest(ToolRequest):
    """Request model for PowerShell operations."""

    scan_mode: str = Field("comprehensive", description="Scan mode")
    include_aliases: bool = Field(True, description="Include alias validation")


class JustfileRequest(BaseModel):
    """Request model for justfile validation."""

    repo_path: str = Field(..., description="Repository path to check")
    fix: bool = Field(False, description="Auto-fix formatting issues")


class RuntAnalyzerRequest(ToolRequest):
    """Request model for Runt Analyzer operations."""

    scan_mode: str = Field("comprehensive", description="Analysis depth")
    include_dependencies: bool = Field(True, description="Include dependency analysis")


class DiscoveryRequest(BaseModel):
    """Request model for Discovery operations."""

    operation: str = Field(..., description="Discovery operation")
    client_type: str | None = Field(None, description="Client type filter")
    discovery_path: str | None = Field(None, description="Path to scan for servers")


class ScaffoldingRequest(BaseModel):
    """Request model for Scaffolding operations."""

    template_type: str = Field(..., description="Template type: mcp_server, landing_page, fullstack, etc.")
    project_name: str = Field(..., description="Name of the project to create")
    output_path: str = Field(..., description="Output directory path")
    features: dict[str, Any] | None = Field(None, description="Additional features/configuration")


class ToolchainCreateRequest(BaseModel):
    name: str
    servers: list[str]
    description: str | None = ""


class ToolchainApplyRequest(BaseModel):
    toolchain_name: str
    client_name: str


class SchedulerRegisterRequest(BaseModel):
    name: str
    interval_seconds: int
    server_id: str
    tool_name: str
    parameters: dict[str, Any] | None = None
    description: str | None = None


class HeartbeatConfigureRequest(BaseModel):
    interval_hours: int = 6


class ExecuteToolRequest(BaseModel):
    """JSON body for POST /api/v1/tools/execute (matches webapp client)."""

    server_id: str = Field("metaops", description="Local Meta MCP id (metaops, meta-mcp, )")
    tool_name: str = Field(..., description="Registered MCP tool name")
    parameters: dict[str, Any] = Field(default_factory=dict)


class FleetAppRequest(BaseModel):
    """Request model for fleet app operations."""

    app_id: str = Field(..., description="ID of the fleet app")


# API Endpoints


@router.post("/diagnostics/emojibuster", summary="Run EmojiBuster Unicode Safety Scanner")
async def run_emojibuster(request: EmojiBusterRequest, background_tasks: BackgroundTasks):
    """Execute EmojiBuster operations for Unicode crash prevention."""
    try:
        result = await diagnostics.run_emojibuster(
            operation=request.operation,
            repo_path=request.repo_path or "*",
            scan_mode=request.scan_mode,
            auto_fix=request.auto_fix,
            backup=request.backup,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"EmojiBuster operation failed: {e!s}") from e


@router.post("/diagnostics/powershell", summary="Run PowerShell Validation Tools")
async def run_powershell_tools(request: PowerShellRequest):
    """Execute PowerShell validation and management operations."""
    try:
        result = await diagnostics.run_powershell_tools(
            operation=request.operation,
            repo_path=request.repo_path,
            scan_mode=request.scan_mode,
            include_aliases=request.include_aliases,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PowerShell operation failed: {e!s}") from e


@router.post("/diagnostics/justfile", summary="Validate justfile Fleet Standards")
async def validate_justfile(request: JustfileRequest):
    """Audit a repository's justfile for fleet standard compliance."""
    try:
        result = await diagnostics.validate_justfile(
            repo_path=request.repo_path,
            fix=request.fix,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Justfile validation failed: {e!s}") from e


@router.post("/analysis/runt-analyzer", summary="Run Repository Health Analysis")
async def run_runt_analyzer(request: RuntAnalyzerRequest):
    """Execute repository health and SOTA compliance analysis."""
    try:
        result = await analysis.run_runt_analyzer(
            operation=request.operation,
            repo_path=request.repo_path or ".",
            scan_mode=request.scan_mode,
            include_dependencies=request.include_dependencies,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Runt analyzer failed: {e!s}") from e


@router.post("/analysis/repo-status", summary="Get Detailed Repository Status")
async def get_repo_status(request: ToolRequest):
    """Get comprehensive repository health and status information."""
    try:
        result = await analysis.get_repo_status(repo_path=request.repo_path or ".", operation=request.operation)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Repository status check failed: {e!s}") from e


@router.post("/discovery/servers", summary="Discover MCP Servers")
async def discover_servers(request: DiscoveryRequest):
    """Discover and analyze MCP servers across the system."""
    try:
        result = await discovery.discover_servers_api(
            operation=request.operation,
            client_type=request.client_type,
            discovery_path=request.discovery_path,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server discovery failed: {e!s}") from e


@router.post("/discovery/client-integration", summary="Check Client Integration Status")
async def check_client_integration(request: DiscoveryRequest):
    """Check MCP client integration health across IDEs."""
    try:
        result = await discovery.check_client_integration(operation=request.operation, client_type=request.client_type)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Client integration check failed: {e!s}") from e


@router.post("/scaffolding/create", summary="Create Project Scaffolding")
async def create_scaffolding(request: ScaffoldingRequest, background_tasks: BackgroundTasks):
    """Generate project scaffolding based on templates."""
    try:
        result = await scaffolding.create_project(
            template_type=request.template_type,
            project_name=request.project_name,
            output_path=request.output_path,
            features=request.features or {},
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scaffolding creation failed: {e!s}") from e


@router.get("/health/detailed", summary="Get Detailed System Health")
async def get_detailed_health():
    """Get comprehensive system health information."""
    try:
        # Get health from all services
        health_data = {
            "diagnostics": await diagnostics.get_health_status(),
            "analysis": await analysis.get_health_status(),
            "discovery": await discovery.get_health_status(),
            "scaffolding": await scaffolding.get_health_status(),
            "server_management": await server_service.get_health_status(),
            "tool_execution": await tool_service.get_health_status(),
            "repository_analysis": await repo_scanner.get_health_status(),
            "client_management": await client_manager.get_health_status(),
            "token_analysis": await token_analyzer.get_health_status(),
            "repo_packing": await repo_packer.get_health_status(),
        }

        # Determine overall status
        all_healthy = all(service.get("healthy", False) for service in health_data.values())

        return {
            "success": all_healthy,
            "message": "System health check completed",
            "data": health_data,
            "timestamp": "2026-01-19T03:00:00Z",
            "services_count": len(health_data),
            "healthy_services": sum(1 for s in health_data.values() if s.get("healthy", False)),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Health check failed: {e!s}") from e


@router.get("/tools/list", summary="List Available MCP Tools")
async def list_available_tools():
    """Get a comprehensive list of all available MCP tools."""
    try:
        tools = {
            "diagnostics": {
                "emojibuster": {
                    "description": "Unicode safety scanner and fixer",
                    "operations": ["scan", "fix"],
                    "parameters": ["repo_path", "scan_mode", "auto_fix", "backup"],
                },
                "powershell_tools": {
                    "description": "PowerShell validation and management",
                    "operations": ["validate", "profile"],
                    "parameters": ["repo_path", "scan_mode", "include_aliases"],
                },
                "justfile_tools": {
                    "description": "Justfile fleet standard validation",
                    "operations": ["validate"],
                    "parameters": ["repo_path", "fix"],
                },
            },
            "analysis": {
                "runt_analyzer": {
                    "description": "Repository health and SOTA compliance",
                    "operations": ["analyze", "status"],
                    "parameters": ["repo_path", "scan_mode", "include_dependencies"],
                },
                "repo_status": {
                    "description": "Detailed repository status",
                    "operations": ["status", "health"],
                    "parameters": ["repo_path"],
                },
            },
            "discovery": {
                "servers": {
                    "description": "MCP server discovery",
                    "operations": ["scan", "list"],
                    "parameters": ["client_type"],
                },
                "client_integration": {
                    "description": "Client integration health",
                    "operations": ["check", "diagnose"],
                    "parameters": ["client_type"],
                },
            },
            "scaffolding": {
                "create": {
                    "description": "Project scaffolding generation",
                    "operations": [
                        "mcp_server",
                        "landing_page",
                        "fullstack",
                        "webshop",
                        "game",
                        "wisdom_tree",
                    ],
                    "parameters": [
                        "template_type",
                        "project_name",
                        "output_path",
                        "features",
                    ],
                }
            },
            "server_management": {
                "start_server": {
                    "description": "Start MCP server processes",
                    "operations": ["start"],
                    "parameters": ["server_path", "server_type"],
                },
                "stop_server": {
                    "description": "Stop running MCP servers",
                    "operations": ["stop"],
                    "parameters": ["server_id"],
                },
                "list_servers": {
                    "description": "List running MCP servers",
                    "operations": ["list"],
                    "parameters": [],
                },
                "server_status": {
                    "description": "Get server status and health",
                    "operations": ["status"],
                    "parameters": ["server_id"],
                },
            },
            "tool_execution": {
                "execute_tool": {
                    "description": "Execute tools on MCP servers",
                    "operations": ["execute"],
                    "parameters": ["server_id", "tool_name", "parameters"],
                },
                "list_server_tools": {
                    "description": "List tools available on servers",
                    "operations": ["list"],
                    "parameters": ["server_id"],
                },
                "validate_parameters": {
                    "description": "Validate tool parameters",
                    "operations": ["validate"],
                    "parameters": ["server_id", "tool_name", "parameters"],
                },
                "tool_history": {
                    "description": "Get tool execution history",
                    "operations": ["history"],
                    "parameters": ["server_id", "tool_name", "limit"],
                },
            },
            "repository_analysis": {
                "scan_repository": {
                    "description": "Deep repository analysis",
                    "operations": ["scan"],
                    "parameters": ["repo_path", "deep_analysis"],
                },
            },
            "client_management": {
                "read_config": {
                    "description": "Read client MCP configuration",
                    "operations": ["read"],
                    "parameters": ["client_name"],
                },
                "update_config": {
                    "description": "Update client MCP configuration",
                    "operations": ["update"],
                    "parameters": ["client_name", "updates", "backup"],
                },
                "add_server": {
                    "description": "Add server to client config",
                    "operations": ["add"],
                    "parameters": ["client_name", "server_name", "server_config"],
                },
                "remove_server": {
                    "description": "Remove server from client config",
                    "operations": ["remove"],
                    "parameters": ["client_name", "server_name"],
                },
                "validate_config": {
                    "description": "Validate client configuration",
                    "operations": ["validate"],
                    "parameters": ["client_name"],
                },
                "list_configs": {
                    "description": "List all client configurations",
                    "operations": ["list"],
                    "parameters": [],
                },
            },
            "token_analysis": {
                "analyze_file_tokens": {
                    "description": "Analyze token usage in specific files",
                    "operations": ["analyze"],
                    "parameters": ["file_path"],
                },
                "analyze_directory_tokens": {
                    "description": "Analyze token usage across directories",
                    "operations": ["analyze"],
                    "parameters": ["dir_path", "extensions"],
                },
                "estimate_context_limits": {
                    "description": "Estimate LLM context limit compatibility",
                    "operations": ["estimate"],
                    "parameters": ["token_count"],
                },
            },
            "repo_packing": {
                "pack_repository": {
                    "description": "Pack repository into AI-friendly formats",
                    "operations": ["pack"],
                    "parameters": [
                        "repo_path",
                        "output_format",
                        "include_patterns",
                        "exclude_patterns",
                    ],
                },
                "pack_repository_for_ai": {
                    "description": "Pack repository optimized for AI consumption",
                    "operations": ["pack"],
                    "parameters": ["repo_path", "max_tokens"],
                },
            },
        }

        return {
            "success": True,
            "message": "Available tools retrieved successfully",
            "data": tools,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Tool listing failed: {e!s}") from e


# Server Management Endpoints
@router.post("/servers/start", summary="Start MCP Server")
async def start_server(server_path: str, server_type: str = "python"):
    """Start an MCP server process."""
    result = await server_service.start_server(server_path, server_type)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("message"))
    return result


@router.post("/servers/stop", summary="Stop MCP Server")
async def stop_server(server_id: str):
    """Stop a running MCP server."""
    result = await server_service.stop_server(server_id)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("message"))
    return result


@router.get("/servers/list", summary="List Running Servers")
async def list_running_servers():
    """List all currently running MCP servers."""
    return await server_service.list_running_servers()


@router.get("/servers/{server_id}/status", summary="Get Server Status")
async def get_server_status(server_id: str):
    """Get detailed status of a specific server."""
    result = await server_service.get_server_status(server_id)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message"))
    return result


@router.post("/servers/inspect", summary="Inspect Server Configuration")
async def inspect_server(request: ServerInspectRequest):
    """Inspect an MCP server configuration."""
    result = await server_service.inspect_server(request.command, request.args, request.env)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("message"))
    return result


# Tool Execution Endpoints
@router.post("/tools/execute", summary="Execute Tool on Server")
async def execute_tool(request: ExecuteToolRequest):
    """Execute a registered tool on the in-process Meta MCP server (local)."""
    result = await tool_service.execute_tool(request.server_id, request.tool_name, request.parameters)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("message"))
    return result


@router.get("/mcp/catalog", summary="Live MCP tool catalog (JSON Schema)")
async def get_mcp_tool_catalog():
    """Tools + parameter schemas for interactive web UI (DynamicForm)."""
    result = await tool_service.get_mcp_catalog()
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("message"))
    return result


@router.get("/servers/{server_id}/tools", summary="List Server Tools")
async def list_server_tools(server_id: str):
    """List all tools available on a specific server."""
    result = await tool_service.list_server_tools(server_id)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("message"))
    return result


@router.post("/tools/validate", summary="Validate Tool Parameters")
async def validate_tool_parameters(server_id: str, tool_name: str, parameters: dict[str, Any]):
    """Validate parameters for a tool execution."""
    result = await tool_service.validate_tool_parameters(server_id, tool_name, parameters)
    return result


@router.get("/tools/history", summary="Get Tool Execution History")
async def get_tool_history(server_id: str, tool_name: str | None = None, limit: int = 10):
    """Get execution history for tools on a server."""
    result = await tool_service.get_tool_history(server_id, tool_name, limit)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("message"))
    return result


# Repository Analysis Endpoints
@router.post("/repos/scan", summary="Scan Repository")
async def scan_repository(repo_path: str, deep_analysis: bool = False):
    """Perform comprehensive repository analysis."""
    result = await repo_scanner.scan_repository(repo_path, deep_analysis)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("message"))
    return result


@router.get("/analysis/fleet", summary="Universal Repo Fleet Analysis")
async def get_fleet_analysis(scan_path: str | None = None, export_mcd: bool = False):
    """Perform multi-dimensional analysis across all repositories in a directory."""
    from meta_mcp.tools.fleet_analyzer import analyze_fleet

    try:
        result = await analyze_fleet(scan_path)
        if not result.get("success"):
            raise HTTPException(status_code=500, detail=result.get("error"))
        if export_mcd:
            from meta_mcp.services.analysis_depot_service import AnalysisDepotService

            result = {**result, "mcd_export": AnalysisDepotService().export_to_mcd()}
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Fleet analysis failed: {e!s}") from e


@router.post("/analysis/publish", summary="Publish analysis depot to MCD")
async def publish_analysis_depot(run_id: str | None = None):
    """Export a depot run to mcp-central-docs/projects/analysis/."""
    from meta_mcp.services.analysis_depot_service import AnalysisDepotService

    result = AnalysisDepotService().export_to_mcd(run_id=run_id)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message") or result.get("error"))
    return result


# Client Management Endpoints
@router.get("/clients/{client_name}/config", summary="Read Client Config")
async def read_client_config(client_name: str):
    """Read MCP configuration for a specific client."""
    result = await client_manager.read_client_config(client_name)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message"))
    return result


@router.post("/clients/{client_name}/config", summary="Update Client Config")
async def update_client_config(client_name: str, updates: dict[str, Any], backup: bool = True):
    """Update MCP configuration for a specific client."""
    result = await client_manager.update_client_config(client_name, updates, backup)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("message"))
    return result


@router.post("/clients/{client_name}/servers", summary="Add Server to Client")
async def add_server_to_client(client_name: str, server_name: str, server_config: dict[str, Any]):
    """Add an MCP server to a client's configuration."""
    result = await client_manager.add_server_to_client(client_name, server_name, server_config)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("message"))
    return result


@router.delete("/clients/{client_name}/servers/{server_name}", summary="Remove Server from Client")
async def remove_server_from_client(client_name: str, server_name: str):
    """Remove an MCP server from a client's configuration."""
    result = await client_manager.remove_server_from_client(client_name, server_name)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message"))
    return result


@router.post("/clients/{client_name}/validate", summary="Validate Client Config")
async def validate_client_config(client_name: str):
    """Validate a client's MCP configuration."""
    result = await client_manager.validate_client_config(client_name)
    return result


@router.get("/clients/configs", summary="List Client Configurations")
async def list_client_configs():
    """List all available client configurations."""
    return await client_manager.list_client_configs()


# Token Analysis Endpoints
@router.post("/tokens/analyze-file", summary="Analyze File Tokens")
async def analyze_file_tokens(file_path: str):
    """Analyze token usage in a specific file."""
    result = await token_analyzer.analyze_file_tokens(file_path)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message"))
    return result


@router.post("/tokens/analyze-directory", summary="Analyze Directory Tokens")
async def analyze_directory_tokens(dir_path: str, extensions: list[str] | None = None):
    """Analyze token usage across files in a directory."""
    result = await token_analyzer.analyze_directory_tokens(dir_path, extensions)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("message"))
    return result


@router.post("/tokens/context-limits", summary="Estimate Context Limits")
async def estimate_context_limits(token_count: int):
    """Estimate how tokens fit within LLM context limits."""
    return await token_analyzer.estimate_context_limits(token_count)


# Repository Packing Endpoints
@router.post("/repos/pack", summary="Pack Repository")
async def pack_repository(
    repo_path: str,
    output_format: str = "xml",
    include_patterns: list[str] | None = None,
    exclude_patterns: list[str] | None = None,
):
    """Pack repository contents into AI-friendly format."""
    result = await repo_packer.pack_repository(repo_path, output_format, include_patterns, exclude_patterns)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("message"))
    return result


@router.post("/repos/pack-for-ai", summary="Pack Repository for AI")
async def pack_repository_for_ai(repo_path: str, max_tokens: int = 100000):
    """Pack repository optimized for AI consumption with token limits."""
    result = await repo_packer.pack_for_ai_consumption(repo_path, max_tokens)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("message"))
    return result


# Toolchain Endpoints
@router.get("/toolchains/list", summary="List All Toolchains")
async def list_toolchains():
    """List all saved toolchain presets."""
    result = await toolchain_service.list_toolchains()
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("message"))
    return result


@router.post("/toolchains/create", summary="Create Toolchain Preset")
async def create_toolchain(request: ToolchainCreateRequest):
    """Create a new toolchain preset with a list of server definitions."""
    result = await toolchain_service.create_toolchain(request.name, request.servers, request.description)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("message"))
    return result


@router.delete("/toolchains/{name}", summary="Delete Toolchain Preset")
async def delete_toolchain(name: str):
    """Delete a toolchain preset."""
    result = await toolchain_service.delete_toolchain(name)
    if not result.get("success"):
        raise HTTPException(status_code=404, detail=result.get("message"))
    return result


@router.post("/toolchains/apply", summary="Apply Toolchain Preset")
async def apply_toolchain(request: ToolchainApplyRequest):
    """Apply a toolchain preset to an IDE client."""
    result = await toolchain_service.apply_toolchain(request.toolchain_name, request.client_name)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("message"))
    return result


@router.get("/toolchains/available_servers", summary="Get Available Servers")
async def get_available_servers():
    """Get the list of all available servers in the MASTER config."""
    result = await toolchain_service.get_available_servers()
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("message"))
    return result


@router.get("/health", summary="Simple Health Check")
async def health_check():
    """Perform a simple health check."""
    return {"status": "healthy", "service": "MetaMCP-API"}


# Scheduler Endpoints
@router.post("/scheduler/tasks", summary="Register Scheduled Task")
async def register_scheduled_task(request: SchedulerRegisterRequest):
    """Register a new recurring task in the scheduler."""
    return await scheduler_service.register_task(
        request.name,
        request.interval_seconds,
        request.server_id,
        request.tool_name,
        request.parameters,
        request.description,
    )


@router.get("/scheduler/tasks", summary="List Scheduled Tasks")
async def list_scheduled_tasks():
    """List all registered scheduled tasks."""
    return await scheduler_service.list_tasks()


@router.delete("/scheduler/tasks/{task_id}", summary="Cancel Scheduled Task")
async def cancel_scheduled_task(task_id: str):
    """Cancel and remove a scheduled task."""
    return await scheduler_service.cancel_task(task_id)


# Heartbeat Endpoints
@router.get("/heartbeat/pulse", summary="Get System Pulse")
async def get_heartbeat_pulse(detailed: bool = False):
    """Generate a system-wide pulse summary."""
    return await heartbeat_service.get_pulse(detailed)


@router.get("/heartbeat/ping", summary="Ping Fleet")
async def ping_heartbeat_fleet():
    """Check connectivity of all MCP servers in the fleet."""
    return await heartbeat_service.ping_fleet()


@router.post("/heartbeat/proactive", summary="Configure Proactive Heartbeat")
async def configure_proactive_heartbeat(request: HeartbeatConfigureRequest):
    """Schedule a recurring proactive heartbeat pulse."""
    # This requires the global scheduler instance which we might not have conveniently here
    # but we can call it through the tool which we just added.
    # For now, let's keep it consistent with the tool implementation.
    return {
        "success": False,
        "message": "Please use the 'heartbeat_configure_proactive' tool directly.",
    }


# Fleet Management Endpoints
@router.get("/fleet/runtime", summary="Audit Fleet Runtime Status")
async def audit_fleet_runtime():
    """Perform a deep audit of the fleet runtime (Ping + Health)."""
    return await fleet_runtime.audit_fleet()


@router.post("/fleet/start", summary="Start Fleet Application")
async def start_fleet_app(request: FleetAppRequest):
    """Start a fleet application via its .bat script."""
    return await fleet_runtime.start_app(request.app_id)


@router.post("/fleet/stop", summary="Stop Fleet Application")
async def stop_fleet_app(request: FleetAppRequest):
    """Stop a fleet application by killing its port process."""
    return await fleet_runtime.stop_app(request.app_id)


class FleetStartupProbeRequest(BaseModel):
    repo_filter: str = Field("", description="Single repo folder name, or empty for full fleet")
    broken_only: bool = Field(
        False,
        description="Re-probe repos that failed in the last report (not stack_ok or skip)",
    )
    background: bool = Field(True, description="Run all repos in background (recommended)")


@router.get("/fleet/startup-probe/report", summary="Fleet cold-start probe report")
async def fleet_startup_probe_report():
    """Latest cold-start probe progress or final report."""
    return fleet_startup_probe.get_report()


@router.post("/fleet/startup-probe/run", summary="Run fleet cold-start probe")
async def fleet_startup_probe_run(request: FleetStartupProbeRequest):
    """Parse-check start.ps1, start app, probe backend + frontend + Vite proxy."""
    return fleet_startup_probe.run_probe(
        repo_filter=request.repo_filter,
        broken_only=request.broken_only,
        background=request.background,
    )


class FleetColdInstallRequest(BaseModel):
    repo_filter: str = Field("", description="Single repo folder name, or empty for full fleet")
    broken_only: bool = Field(
        False,
        description="Re-probe repos that failed in the last cold-install report",
    )
    background: bool = Field(True, description="Run asynchronously (recommended)")
    preflight_only: bool = Field(True, description="INSTALL.md preflight only (no sandbox execute)")
    execute: bool = Field(False, description="Generate/run sandbox install scripts via virt-mcp")
    test_mcpb: bool = Field(False, description="Check mcpb availability and optional smoke")
    host_mcpb_smoke: bool = Field(
        False,
        description="Stdio smoke via host Claude Desktop config (requires -TestMcpb)",
    )
    batch_size: int = Field(0, description="Limit repos probed (0 = all matching filter)")
    mcp_clients: str = Field(
        "",
        description="Comma-separated IDE client ids (claude,cursor,windsurf,antigravity,zed,opencode); empty=all",
    )


@router.get("/fleet/cold-install/report", summary="Fleet cold-install probe report")
async def fleet_cold_install_report():
    """Latest cold-install probe progress or final report."""
    return fleet_cold_install.get_report()


@router.post("/fleet/cold-install/run", summary="Run fleet cold-install probe")
async def fleet_cold_install_run(request: FleetColdInstallRequest):
    """INSTALL.md preflight, mcpb release check, optional sandbox/mcpb smoke."""
    return fleet_cold_install.run_probe(
        repo_filter=request.repo_filter,
        broken_only=request.broken_only,
        background=request.background,
        preflight_only=request.preflight_only,
        execute=request.execute,
        test_mcpb=request.test_mcpb,
        host_mcpb_smoke=request.host_mcpb_smoke,
        batch_size=request.batch_size,
        mcp_clients=request.mcp_clients,
    )


# Fritz (fleet-agent-mcp) + RoboFang agent hub
@router.get("/agent-hub/fritz", summary="Fritz overview  status, tasks, coworker flows")
async def agent_hub_fritz_overview():
    return await agent_hub.get_fritz_overview()


class FritzCoworkerRequest(BaseModel):
    tool: str = Field(..., description="coworker_* MCP tool name")
    deliver: bool = Field(True, description="Email report when SMTP configured")


@router.post("/agent-hub/fritz/coworker", summary="Run a Fritz coworker flow now")
async def agent_hub_fritz_coworker(request: FritzCoworkerRequest):
    return await agent_hub.run_fritz_coworker(request.tool, deliver=request.deliver)


@router.get("/agent-hub/robofang", summary="RoboFang overview  health, hands, routines")
async def agent_hub_robofang_overview():
    return await agent_hub.get_robofang_overview()


class RobofangRoutineRunRequest(BaseModel):
    routine_id: str = Field(..., description="Routine id from /api/routines")


@router.post("/agent-hub/robofang/routine/run", summary="Run a RoboFang routine now")
async def agent_hub_robofang_routine_run(request: RobofangRoutineRunRequest):
    return await agent_hub.run_robofang_routine(request.routine_id)


# Local LLM bridge (web dashboard  avoids browser CORS to Ollama/LM Studio)
class LLMModelsRequest(BaseModel):
    provider: str = Field("ollama", description="ollama | lmstudio | openai")
    base_url: str = Field(..., description="e.g. http://localhost:11434")


class LLMChatRequest(BaseModel):
    provider: str = Field("ollama")
    base_url: str = Field(...)
    model: str = Field(...)
    messages: list[dict[str, str]] = Field(default_factory=list)


@router.post("/llm/models", summary="List local LLM models")
async def list_local_llm_models(request: LLMModelsRequest):
    """Proxy model discovery to Ollama /v1/models (no browser CORS)."""
    result = await local_llm.list_models(request.provider, request.base_url)
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("message"))
    return result


@router.post("/llm/chat", summary="Chat with local LLM")
async def chat_local_llm(request: LLMChatRequest):
    """Proxy chat to Ollama /api/chat or OpenAI-compatible /v1/chat/completions."""
    result = await local_llm.chat(
        request.provider,
        request.base_url,
        request.model,
        request.messages,
    )
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("message"))
    return result


#  Dynamic Routing (lazy-loading fleet proxy)


class RouteToolRequest(BaseModel):
    """JSON body for POST /api/v1/routing/call."""

    target_server: str = Field("", description="MCP server repo name, empty for auto-discovery")
    tool_name: str = Field(..., description="Tool name to invoke")
    arguments: dict[str, Any] = Field(default_factory=dict)


@router.post("/routing/call", summary="Route tool call to fleet MCP server")
async def route_tool_call(request: RouteToolRequest):
    """Proxy a tool call to a fleet MCP server with automatic hot-start."""
    result = await dynamic_router.route_tool(
        target_server=request.target_server,
        tool_name=request.tool_name,
        arguments=request.arguments,
    )
    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("message"))
    return result


@router.get("/routing/status", summary="Dynamic routing index status")
async def routing_status():
    """Return routing index stats and running server processes."""
    return await dynamic_router.get_routing_status()


@router.post("/routing/rebuild", summary="Rebuild dynamic routing index")
async def rebuild_routing_index():
    """Force a full fleet scan and index rebuild."""
    return await dynamic_router.rebuild_index()


@router.get("/routing/search", summary="Search fleet tools via dynamic index")
async def search_routing_tools(q: str = "", limit: int = 20):
    """Fuzzy keyword search across all indexed fleet tools."""
    return await dynamic_router.search_tools(query=q, limit=limit)
