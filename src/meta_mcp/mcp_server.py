#!/usr/bin/env python3
"""
MetaMCP - The Ultimate "Argh-Coding" Bloat-Buster.

Refactored Service-Oriented Architecture (Phase 4).
SOTA FastMCP 3.2+ compliant with decentralized tool registration and lifecycle management.
"""

import contextlib
import logging
import os
import sys

# 1. Force Binary Mode (Prevent CRLF corruption on Windows)
if os.name == "nt":
    try:
        import msvcrt

        msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
        msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    except (ImportError, OSError, AttributeError):
        pass

# 2. Industrial Logging (FastMCP 3.2 Standard)
from meta_mcp.logging_config import get_logger, setup_logging

setup_logging(log_level="INFO")

# Suppress noisy loggers for clean "Bashing" telemetry
for logger_name in [
    "mcp.server.lowlevel.server",
    "fastmcp",
    "uvicorn",
    "watchfiles",
    "docket",
]:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

from fastmcp import FastMCP
from fastmcp.server import create_proxy

# Core Infrastructure
from meta_mcp.registry import MetaMCPRegistry
from meta_mcp.tools.registries.analysis import register_analysis_tools
from meta_mcp.tools.registries.assess_reports import register_assess_reports_tools
from meta_mcp.tools.registries.client_management import register_client_management_tools
from meta_mcp.tools.registries.config_audit import register_config_audit_tools

# Tool Registries
from meta_mcp.tools.registries.demo_capture import register_demo_capture_tools
from meta_mcp.tools.registries.diagnostics import register_diagnostics_tools
from meta_mcp.tools.registries.discovery import register_discovery_tools
from meta_mcp.tools.registries.fleet import register_fleet_tools
from meta_mcp.tools.registries.harness import register_harness_tools
from meta_mcp.tools.registries.heartbeat import register_heartbeat_tools
from meta_mcp.tools.registries.meta_dev import register_meta_dev_tools
from meta_mcp.tools.registries.ollama import register_ollama_tools
from meta_mcp.tools.registries.repo_inspiration import register_repo_inspiration_tools
from meta_mcp.tools.registries.repo_packing import register_repo_packing_tools
from meta_mcp.tools.registries.repository_analysis import (
    register_repository_analysis_tools,
)
from meta_mcp.tools.registries.routing import register_routing_tools
from meta_mcp.tools.registries.scaffolding import register_scaffolding_tools
from meta_mcp.tools.registries.scheduler import register_scheduler_tools
from meta_mcp.tools.registries.server_management import register_server_management_tools
from meta_mcp.tools.registries.token_analysis import register_token_analysis_tools
from meta_mcp.tools.registries.tool_execution import register_tool_execution_tools
from meta_mcp.tools.registries.toolchains import register_toolchain_tools

logger = get_logger(__name__)


def initialize_tools(mcp: FastMCP):
    """Dynamically load and register all tool suites."""
    registry = MetaMCPRegistry(mcp)

    registry.register_suite("diagnostics", register_diagnostics_tools)
    registry.register_suite("analysis", register_analysis_tools)
    registry.register_suite("assess_reports", register_assess_reports_tools)
    registry.register_suite("discovery", register_discovery_tools)
    registry.register_suite("scaffolding", register_scaffolding_tools)
    registry.register_suite("server_management", register_server_management_tools)
    registry.register_suite("tool_execution", register_tool_execution_tools)
    registry.register_suite("repository_analysis", register_repository_analysis_tools)
    registry.register_suite("client_management", register_client_management_tools)
    registry.register_suite("config_audit", register_config_audit_tools)
    registry.register_suite("token_analysis", register_token_analysis_tools)
    registry.register_suite("repo_packing", register_repo_packing_tools)
    registry.register_suite("repo_inspiration", register_repo_inspiration_tools)
    registry.register_suite("toolchains", register_toolchain_tools)
    scheduler_service = registry.register_suite("scheduler", register_scheduler_tools)
    logger.debug("scheduler_service from registry", scheduler_service=str(scheduler_service))
    # We assign to a private attribute or rely on registry state
    mcp.scheduler_service = scheduler_service
    registry.register_suite("heartbeat", register_heartbeat_tools)
    registry.register_suite("meta_dev", register_meta_dev_tools)
    registry.register_suite("fleet", register_fleet_tools)
    registry.register_suite("harness", register_harness_tools)
    registry.register_suite("ollama", register_ollama_tools)
    registry.register_suite("demo_capture", register_demo_capture_tools)
    registry.register_suite("routing", register_routing_tools)
    logger.info(
        "MetaMCP Modular Suites Loaded Successfully",
        suites=registry.get_registered_suites(),
    )


@contextlib.asynccontextmanager
async def server_lifespan(mcp: FastMCP):
    """Handle server startup and tool registration."""
    initialize_tools(mcp)

    # Start scheduler background loop if present
    if hasattr(mcp, "scheduler_service") and mcp.scheduler_service:
        await mcp.scheduler_service.start()

        # Register default proactive heartbeat (every 6 hours)
        await mcp.scheduler_service.register_task(
            name="System Heartbeat",
            interval_seconds=6 * 3600,
            server_id="metaops",
            tool_name="heartbeat_ops",
            parameters={"operation": "pulse", "detailed": True},
            description="Default proactive system pulse log.",
        )
        logger.info("Scheduler service started and heartbeat task registered")

    yield  # Server runs here

    # Shutdown logic
    if hasattr(mcp, "scheduler_service") and mcp.scheduler_service:
        await mcp.scheduler_service.stop()
        logger.info("Scheduler service stopped")


# Initialize FastMCP with Optimized Instructions and Lifespan
app = FastMCP(
    "MetaMCP",
    instructions="""
# MetaMCP Ecosystem Orchestrator [SOTA 3.2]
Industrial-grade MCP server lifecycle management, client integration, and ecosystem analysis.
Suites: Server Management, Tool Execution, Repository Analysis, Client Management, Scaffolding, Diagnostics, Discovery.

**Discovery:** Call **help** (no arguments) to list every tool.
Use **show_mcp_overview** for a short overview.
Repo study: **inspire_repo_help** / **inspire_repo_structure_card**.
    """,
    version="1.4.0",  # SOTA 3.2 Modernization
    lifespan=server_lifespan,
)

# MCP Bridge: proxy tools from remote MCP servers via MCP_BRIDGE_URLS
_bridge_proxies = []
bridge_urls = os.getenv("MCP_BRIDGE_URLS", "")
if bridge_urls:
    for url in bridge_urls.split(","):
        url = url.strip()
        if url:
            try:
                app.add_provider(create_proxy(url))
                _bridge_proxies.append(url)
            except Exception:
                pass


def main():
    """Main entry point for the MetaMCP server."""
    app.run(transport="stdio")


if __name__ == "__main__":
    main()
