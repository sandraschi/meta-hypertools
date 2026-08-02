"""
MCP Server Integration Tools - SOTA Compliant FastMCP 2.14.1+ Tools

This module provides MCP tool wrappers for existing MetaMCP functionality,
implementing enhanced response patterns and Unicode-safe logging.
"""

from pathlib import Path
from typing import Any

# Unicode-safe logging (CRITICAL - no Unicode in logger calls!)
import structlog
from fastmcp import FastMCP

# Import existing tool modules
from .discovery import discover_servers
from .files import list_directory
from .fleet_launcher import launch_fleet_app_tool, list_fleet_apps_tool
from .runt_analyzer import _analyze_repo
from .utility import validate_json

logger = structlog.get_logger(__name__)


def register_discovery_tools(app: FastMCP):
    """Register MCP discovery tools with enhanced response patterns."""

    @app.tool()
    async def discover_mcp_servers(
        search_paths: list[str] | None = None,
        include_inactive: bool = False,
        detailed_scan: bool = True,
    ) -> dict[str, Any]:
        """Discover MCP servers across the system with enhanced analysis.

        Scans configured paths to find MCP servers including Python-based servers,
        Node.js servers, Docker-based servers, and configuration-based servers.
        Provides detailed information about each discovered server including their
        capabilities, tools, and current status.

        Args:
            search_paths: List of paths to search (uses defaults if None)
            include_inactive: Include servers that may not be currently running
            detailed_scan: Perform comprehensive analysis of each server

        Returns:
            Enhanced response with discovered servers and analysis results
        """

        try:
            # Default search paths if not provided
            if not search_paths:
                search_paths = [
                    "d:\\Dev\\repos",
                    "C:\\Users\\*\\AppData\\Roaming\\Claude\\claude_desktop_config.json",
                    "C:\\ProgramData\\Claude",
                ]

            discovered_servers = []
            total_scanned = 0

            for search_path in search_paths:
                try:
                    path = Path(search_path)
                    if path.exists():
                        # Use existing discovery logic
                        servers = discover_servers(str(path), detailed=detailed_scan)
                        discovered_servers.extend(servers)
                        total_scanned += 1
                except Exception as e:
                    logger.warning("Failed to scan path", path=search_path, error=str(e))

            # Analyze discovered servers
            active_servers = [s for s in discovered_servers if s.get("status") == "active"]
            inactive_servers = [s for s in discovered_servers if s.get("status") != "active"]

            return {
                "success": True,
                "operation": "discover_mcp_servers",
                "result": {
                    "total_servers_found": len(discovered_servers),
                    "active_servers": len(active_servers),
                    "inactive_servers": len(inactive_servers),
                    "paths_scanned": total_scanned,
                    "servers": discovered_servers
                    if detailed_scan
                    else [
                        {
                            "name": s.get("name", "Unknown"),
                            "status": s.get("status", "unknown"),
                        }
                        for s in discovered_servers
                    ],
                },
                "summary": f"Discovered {len(discovered_servers)} MCP servers "
                f"({len(active_servers)} active, {len(inactive_servers)} inactive)",
                "recommendations": [
                    "Review inactive servers for potential cleanup",
                    "Update servers to FastMCP 2.14.1+ for enhanced responses",
                    "Check server configurations for optimal performance",
                ],
                "next_steps": [
                    "Use get_server_info() for detailed server analysis",
                    "Use validate_sota_compliance() for standards checking",
                    "Use update_mcp_server() for upgrades",
                ],
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"MCP server discovery failed: {e!s}",
                "error_code": "DISCOVERY_FAILED",
                "recovery_options": [
                    "Check search paths are accessible",
                    "Verify MCP server configurations exist",
                    "Use specific search paths instead of defaults",
                ],
                "diagnostic_info": {
                    "search_paths": search_paths,
                    "error_type": type(e).__name__,
                },
            }

    @app.tool()
    async def get_server_info(server_name: str, server_path: str | None = None) -> dict[str, Any]:
        """Get detailed information about a specific MCP server.

        Provides comprehensive analysis of a single MCP server including its
        configuration, tools, capabilities, and SOTA compliance status.

        Args:
            server_name: Name of the server to analyze
            server_path: Optional path to the server (auto-discovered if None)

        Returns:
            Enhanced response with detailed server information
        """

        try:
            # Find server if path not provided
            if not server_path:
                # Search for server in common locations
                search_paths = [
                    "d:\\Dev\\repos",
                    "C:\\Users\\*\\AppData\\Roaming\\Claude",
                ]
                server_path = None

                for search_path in search_paths:
                    try:
                        path = Path(search_path)
                        if path.exists():
                            # Look for server directory
                            for item in path.rglob(f"*{server_name}*"):
                                if item.is_dir() and (item / "server.py").exists():
                                    server_path = str(item)
                                    break
                        if server_path:
                            break
                    except Exception:
                        continue

            if not server_path:
                return {
                    "success": False,
                    "error": f"Server '{server_name}' not found",
                    "error_code": "SERVER_NOT_FOUND",
                    "recovery_options": [
                        "Check server name spelling",
                        "Provide specific server_path parameter",
                        "Use discover_mcp_servers() to see available servers",
                    ],
                    "available_servers": "Use discover_mcp_servers() to list servers",
                }

            server_path = Path(server_path)
            if not server_path.exists():
                return {
                    "success": False,
                    "error": f"Server path does not exist: {server_path}",
                    "error_code": "PATH_NOT_FOUND",
                }

            # Analyze server
            server_info = {
                "name": server_name,
                "path": str(server_path),
                "exists": True,
                "files": [],
                "configuration": {},
                "tools": [],
                "sota_compliance": {},
            }

            # List server files
            for file_path in server_path.rglob("*.py"):
                relative_path = file_path.relative_to(server_path)
                server_info["files"].append(str(relative_path))

            # Check for key files
            key_files = ["server.py", "pyproject.toml", "manifest.json", "README.md"]
            for key_file in key_files:
                file_path = server_path / key_file
                if file_path.exists():
                    server_info["configuration"][key_file] = {
                        "exists": True,
                        "size": file_path.stat().st_size,
                        "modified": file_path.stat().st_mtime,
                    }

            return {
                "success": True,
                "operation": "get_server_info",
                "result": server_info,
                "summary": f"Retrieved detailed information for '{server_name}'",
                "recommendations": [
                    "Check SOTA compliance for this server",
                    "Update to FastMCP 2.14.1+ if needed",
                    "Review server configuration for optimization",
                ],
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to get server info: {e!s}",
                "error_code": "INFO_RETRIEVAL_FAILED",
                "recovery_options": [
                    "Verify server path is correct",
                    "Check server permissions",
                    "Use discover_mcp_servers() to validate server exists",
                ],
            }


def register_scaffolding_tools(app: FastMCP):
    """Register MCP scaffolding tools with enhanced response patterns."""

    @app.tool()
    async def create_mcp_server(
        server_name: str,
        server_path: str | None = None,
        template_type: str = "sota",
        author: str = "MetaMCP User",
        description: str = "SOTA-compliant MCP server",
        include_frontend: bool = False,
        fastmcp_version: str = "2.14.1",
    ) -> dict[str, Any]:
        """Create a new SOTA-compliant MCP server with enhanced response patterns.

        Scaffolds a new MCP server following FastMCP 2.14.1+ SOTA standards with
        proper project structure, enhanced response patterns, Unicode-safe logging,
        and comprehensive documentation. Includes optional frontend generation.

        Args:
            server_name: Name for the new MCP server
            server_path: Optional path (auto-generated if None)
            template_type: Template type ("sota", "minimal", "fullstack")
            author: Author name for the project
            description: Server description
            include_frontend: Whether to include frontend scaffolding
            fastmcp_version: FastMCP version target (recommended: 2.14.1+)

        Returns:
            Enhanced response with server creation results and next steps
        """

        try:
            # Generate server path if not provided
            if not server_path:
                server_path = f"d:\\Dev\\repos\\{server_name}"

            server_path = Path(server_path)

            # Check if server already exists
            if server_path.exists():
                return {
                    "success": False,
                    "error": f"Server directory already exists: {server_path}",
                    "error_code": "SERVER_EXISTS",
                    "recovery_options": [
                        "Choose a different server name",
                        "Use update_mcp_server() to upgrade existing server",
                        "Delete existing directory and recreate",
                    ],
                }

            # Use existing server builder functionality
            result = await create_mcp_server(
                server_name=server_name,
                server_path=str(server_path),
                template_type=template_type,
                author=author,
                description=description,
                include_frontend=include_frontend,
                fastmcp_version=fastmcp_version,
            )

            if result.get("success"):
                return {
                    "success": True,
                    "operation": "create_mcp_server",
                    "result": result,
                    "summary": f"Successfully created MCP server '{server_name}' at {server_path}",
                    "recommendations": [
                        "Review generated server structure",
                        "Test server with 'python -m src.server'",
                        "Add custom tools following SOTA patterns",
                        "Update README.md with server-specific information",
                    ],
                    "next_steps": [
                        f"cd {server_path}",
                        "pip install -e .",
                        "python -m src.server",
                        "Test with Claude Desktop or Windsurf",
                    ],
                    "created_files": result.get("files_created", []),
                    "sota_features": result.get("sota_features", []),
                }
            else:
                return result

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to create MCP server: {e!s}",
                "error_code": "CREATION_FAILED",
                "recovery_options": [
                    "Check server path permissions",
                    "Verify template type is valid",
                    "Ensure FastMCP version is supported",
                ],
                "diagnostic_info": {
                    "server_name": server_name,
                    "server_path": server_path,
                    "template_type": template_type,
                    "error_type": type(e).__name__,
                },
            }


def register_analysis_tools(app: FastMCP):
    """Register MCP analysis tools with enhanced response patterns."""

    @app.tool()
    async def analyze_runts(
        repo_paths: list[str] | None = None,
        include_recommendations: bool = True,
        detailed_analysis: bool = True,
    ) -> dict[str, Any]:
        """Analyze repositories for SOTA compliance and identify "runts" needing upgrades.

        Scans MCP repositories to identify those that need upgrades to SOTA standards.
        Evaluates FastMCP version compliance, tool quality, documentation standards,
        and overall project health. Provides specific recommendations for improvements.

        Args:
            repo_paths: List of repository paths (auto-discovers if None)
            include_recommendations: Include upgrade recommendations
            detailed_analysis: Perform comprehensive analysis

        Returns:
            Enhanced response with analysis results and upgrade recommendations
        """

        try:
            # Auto-discover repositories if not provided
            if not repo_paths:
                repo_paths = [
                    "d:\\Dev\\repos\\mcp-central-docs",
                    "d:\\Dev\\repos\\qbt-mcp",
                ]

            analysis_results = []
            total_repos = len(repo_paths)
            runts_found = 0
            sota_compliant = 0

            for repo_path in repo_paths:
                try:
                    result = await _analyze_repo(repo_path=repo_path, detailed=detailed_analysis)

                    if result.get("success"):
                        analysis_results.append(result)

                        if result.get("is_runt", False):
                            runts_found += 1
                        elif result.get("sota_score", 0) >= 80:
                            sota_compliant += 1

                except Exception as e:
                    analysis_results.append(
                        {
                            "repository": repo_path,
                            "success": False,
                            "message": "Analysis failed",
                            "error": str(e),
                        }
                    )

            # Generate summary
            summary = (
                f"Analyzed {total_repos} repositories: {runts_found} runts needing upgrades, "
                f"{sota_compliant} SOTA compliant"
            )

            response = {
                "success": True,
                "operation": "analyze_runts",
                "result": {
                    "total_repositories": total_repos,
                    "runts_found": runts_found,
                    "sota_compliant": sota_compliant,
                    "need_upgrades": runts_found,
                    "analysis_results": analysis_results,
                },
                "summary": summary,
            }

            if include_recommendations:
                response["recommendations"] = [
                    "Prioritize upgrading runts with high tool counts",
                    "Focus on repositories with FastMCP version issues",
                    "Implement SOTA patterns for enhanced responses",
                    "Add Unicode-safe logging to prevent crashes",
                ]

                if runts_found > 0:
                    response["next_steps"] = [
                        "Use update_mcp_server() for each identified runt",
                        "Review detailed analysis for specific issues",
                        "Implement recommended changes incrementally",
                        "Validate upgrades with analyze_runts() again",
                    ]

            return response

        except Exception as e:
            return {
                "success": False,
                "error": f"Repository analysis failed: {e!s}",
                "error_code": "ANALYSIS_FAILED",
                "recovery_options": [
                    "Check repository paths are accessible",
                    "Verify repository permissions",
                    "Analyze repositories individually",
                ],
            }


def register_file_tools(app: FastMCP):
    """Register file management tools with enhanced response patterns."""

    @app.tool()
    async def list_directory_contents(
        directory_path: str,
        show_hidden: bool = False,
        include_metadata: bool = True,
        max_depth: int = 3,
    ) -> dict[str, Any]:
        """List directory contents with enhanced metadata and filtering options.

        Provides comprehensive directory listing with file metadata, size information,
        and modification times. Supports filtering by file type and depth control.

        Args:
            directory_path: Path to directory to list
            show_hidden: Include hidden files and directories
            include_metadata: Include detailed file metadata
            max_depth: Maximum depth for recursive listing

        Returns:
            Enhanced response with directory contents and metadata
        """

        try:
            path = Path(directory_path)

            if not path.exists():
                return {
                    "success": False,
                    "error": f"Directory does not exist: {directory_path}",
                    "error_code": "DIRECTORY_NOT_FOUND",
                    "recovery_options": [
                        "Check directory path spelling",
                        "Verify directory exists",
                        "Use absolute path instead of relative",
                    ],
                }

            if not path.is_dir():
                return {
                    "success": False,
                    "error": f"Path is not a directory: {directory_path}",
                    "error_code": "NOT_DIRECTORY",
                    "recovery_options": [
                        "Verify path points to a directory",
                        "Use file operations for files instead",
                    ],
                }

            # Use existing file listing functionality
            result = await list_directory(
                directory_path=directory_path,
                show_hidden=show_hidden,
                include_metadata=include_metadata,
                max_depth=max_depth,
            )

            return {
                "success": True,
                "operation": "list_directory_contents",
                "result": result,
                "summary": f"Listed contents of {directory_path}",
                "recommendations": [
                    "Use read_file() to examine specific files",
                    "Use write_file() to create or modify files",
                    "Check file permissions if access issues occur",
                ],
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to list directory: {e!s}",
                "error_code": "LISTING_FAILED",
                "recovery_options": [
                    "Check directory permissions",
                    "Verify path is accessible",
                    "Use absolute path for system directories",
                ],
            }


def register_utility_tools(app: FastMCP):
    """Register utility tools with enhanced response patterns."""

    @app.tool()
    async def validate_json_structure(
        json_data: str, schema_name: str | None = None, strict_mode: bool = False
    ) -> dict[str, Any]:
        """Validate JSON structure and format with enhanced error reporting.

        Validates JSON syntax, structure, and optionally against a schema.
        Provides detailed error reporting with line numbers and specific issues.
        Supports both syntax validation and structural validation.

        Args:
            json_data: JSON string to validate
            schema_name: Optional schema name for structural validation
            strict_mode: Enable strict validation mode

        Returns:
            Enhanced response with validation results and recommendations
        """

        try:
            # Use existing validation functionality
            result = await validate_json(json_data=json_data, schema_name=schema_name, strict_mode=strict_mode)

            return {
                "success": True,
                "operation": "validate_json_structure",
                "result": result,
                "summary": "JSON validation completed",
                "recommendations": [
                    "Fix any identified syntax or structure issues",
                    "Use format_text() for JSON formatting",
                    "Consider schema validation for complex structures",
                ]
                if result.get("valid")
                else [
                    "Correct syntax errors identified in validation",
                    "Review line numbers for specific issues",
                    "Use JSON linter for automated fixing",
                ],
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"JSON validation failed: {e!s}",
                "error_code": "VALIDATION_FAILED",
                "recovery_options": [
                    "Check JSON syntax for basic errors",
                    "Use online JSON validator for complex issues",
                    "Simplify JSON structure for testing",
                ],
            }


def register_all_meta_tools(app: FastMCP):
    """Register all MetaMCP tools with SOTA compliance."""

    logger.info("Registering MetaMCP tools with SOTA FastMCP 2.14.1+ compliance")

    # Register tool categories
    register_discovery_tools(app)
    register_scaffolding_tools(app)
    register_analysis_tools(app)
    register_file_tools(app)
    register_utility_tools(app)

    # Register Fleet Launcher tools
    @app.tool(name="list_fleet_apps")
    async def list_fleet_apps():
        """List all available fleet web applications and their current status."""
        return await list_fleet_apps_tool()

    @app.tool(name="launch_fleet_app")
    async def launch_fleet_app(app_id: str):
        """Launch a fleet web application by ID."""
        return await launch_fleet_app_tool(app_id)

    logger.info("MetaMCP tools registration complete - Enhanced response patterns enabled")
