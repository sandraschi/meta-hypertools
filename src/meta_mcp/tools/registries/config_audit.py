"""MCP tool: fleet config audit -- scan repos for agent configs and discovery files."""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from meta_mcp.utils.fleet_config_audit import scan_fleet


def register_config_audit_tools(mcp: FastMCP) -> None:

    @mcp.tool(name="fleet_config_audit")
    async def fleet_config_audit(
        repo_filter: str = "",
        limit: int = 0,
    ) -> dict[str, Any]:
        """Scan all fleet repos for config files (CLAUDE.md, AGENTS.md, .cursorrules, llms.txt, glama.json, etc.).

        Returns a structured report showing which config files exist in each repo,
        their last modified dates, and the override priority chain for behavioral files.

        ## Return Format
        {"success": bool, "total_repos": int, "repos": [...], "file_type_counts": {...}, "config_priority_chain": [...]}

        ## Examples
        fleet_config_audit()
        fleet_config_audit(repo_filter="mcp", limit=10)
        """
        return scan_fleet(repo_filter=repo_filter, limit=limit)
