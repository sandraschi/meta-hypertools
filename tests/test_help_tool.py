"""Ensure fleet-standard help tool is registered (portmanteau design)."""

import asyncio

from fastmcp import FastMCP

from meta_mcp.tools.registries.diagnostics import register_diagnostics_tools


def test_help_tool_name_registered():
    """The diagnostics suite consolidates help into the diagnostics_ops portmanteau."""
    mcp = FastMCP("test-meta-help")
    register_diagnostics_tools(mcp)

    async def _names() -> set[str]:
        tools = await mcp.list_tools()
        return {getattr(t, "name", "") for t in tools}

    names = asyncio.run(_names())
    assert "diagnostics_ops" in names


def test_help_operation_works():
    """The help operation inside diagnostics_ops returns the tool list."""
    mcp = FastMCP("test-meta-help")
    register_diagnostics_tools(mcp)

    async def _run() -> dict:
        tools = {getattr(t, "name", ""): t for t in await mcp.list_tools()}
        tool = tools["diagnostics_ops"]
        return await tool.fn(operation="help")

    result = asyncio.run(_run())
    assert result["success"] is True
    assert "tools" in result or "message" in result
