"""Register fleet SOTA surface: prompts, prefab tools, MCP resources (Phase D)."""

from __future__ import annotations

import logging
import os
from typing import Annotated, Any

from fastmcp import FastMCP
from pydantic import Field

logger = logging.getLogger(__name__)

SKILLS_MD = """# MetaMCP  repo inspiration skills (fleet 2026)

## When to use
- Study a **public GitHub** repo for patterns (no local clone)
- Compare OSS layout before scaffolding a new MCP server
- Multi-step study: `inspire_repo_workflow` when the host supports MCP sampling

## Workflows
1. **Structure first**: `inspire_repo(operation=structure)` or `inspire_repo_structure_card`
2. **Large monorepos**: use `subpath=` from `data.suggested_subpaths` / `data.hints`
3. **Files**: `inspire_repo(operation=files)` with `target_files` or auto-pick
4. **Patterns pack**: `inspire_repo(operation=patterns)` for README + manifest + prompt
5. **Agentic**: `inspire_repo_workflow(goal=..., url=...)`

## Discovery
- `help()`  full MetaMCP tool catalog
- `show_mcp_overview`  suite overview (tool name: `meta_mcp_help` in some clients)
- `inspire_repo_help`  inspiration parameter reference

## Credit
Workflow adapted from Repomuse (MIT, praveene3127); implemented natively in Python.
"""


def _prefab_enabled() -> bool:
    return os.environ.get("META_MCP_PREFAB_APPS", "1").strip().lower() not in (
        "0",
        "false",
        "no",
        "off",
    )


def register_fleet_surface(mcp: FastMCP, *, inspiration_service: Any | None = None) -> None:
    """Attach prompts, resources, and optional prefab tools."""

    @mcp.prompt()
    def inspire_repo_study(
        url: Annotated[str, Field(description="GitHub repository URL")] = "https://github.com/owner/repo",
        goal: Annotated[str, Field(description="What to learn from the repo")] = "architecture patterns",
    ) -> str:
        """Prompt template for structured GitHub repo inspiration."""
        return (
            f"Study {url} for: {goal}. "
            "Call inspire_repo(operation=structure) first; use subpath if large_repo_mode. "
            "Then files or inspire_repo_workflow; summarize patterns  do not paste code verbatim."
        )

    @mcp.prompt()
    def meta_mcp_fleet_discovery() -> str:
        """Prompt template for MetaMCP tool and fleet discovery."""
        return (
            "Call help() to list MetaMCP tools. Use show_mcp_overview for suites. "
            "For fleet launcher UI: open_mcp_launcher. For registry refresh: refresh_mcp_fleet."
        )

    @mcp.resource("resource://meta-mcp/repo-inspiration/skills")
    def meta_mcp_repo_inspiration_skills() -> str:
        return SKILLS_MD

    @mcp.resource("resource://meta-mcp/capabilities")
    def meta_mcp_capabilities() -> str:
        return (
            "meta-mcp: FastMCP 3.2+, repo inspiration (inspire_repo), fleet orchestration, "
            "diagnostics, scaffolding, prefab structure card, MCP prompts/skills, web dashboard. "
            "Transports: stdio, HTTP. API default port 10718."
        )

    if not _prefab_enabled():
        logger.info("Prefab apps disabled (META_MCP_PREFAB_APPS=0)")
        logger.info("Fleet surface registered: prompts, resources (prefab skipped)")
        return

    try:
        from fastmcp.tools import ToolResult
        from prefab_ui.app import PrefabApp
        from prefab_ui.components import Card, CardContent, CardHeader, CardTitle, Text
    except ImportError as e:
        logger.info("Prefab unavailable  pip install prefab-ui (%s)", e)
        logger.info("Fleet surface registered: prompts, resources (prefab skipped)")
        return

    from meta_mcp.prefabs.repo_inspiration import build_inspire_structure_card

    svc = inspiration_service

    @mcp.tool(
        name="inspire_repo_structure_card",
        app=True,
        annotations={"readOnlyHint": True, "destructiveHint": False},
    )
    async def inspire_repo_structure_card(
        url: Annotated[str, Field(description="GitHub repository URL")],
        subpath: Annotated[str | None, Field(description="Folder filter within repo")] = None,
        branch: Annotated[str | None, Field(description="Branch name")] = None,
        profile: Annotated[str, Field(description="brief | standard | deep")] = "standard",
        max_chars: Annotated[int | None, Field(description="Optional character cap")] = None,
    ):
        """GitHub repo structure as a Prefab card (fleet list/status surface).

        Plain-text fallback is included for hosts that do not render MCP Apps.
        """
        if svc is None:
            from meta_mcp.services.repo_inspiration_service import RepoInspirationService

            active = RepoInspirationService()
        else:
            active = svc

        result = await active.inspire_structure(
            url,
            subpath=subpath,
            branch=branch,
            profile=profile,
            max_chars=max_chars,
        )
        if not result.get("success"):
            summary = str(result.get("message") or result.get("error") or "Structure fetch failed")
            with Card(css_class="max-w-md") as view:
                with CardHeader():
                    CardTitle("Structure unavailable")
                with CardContent():
                    Text(summary)
            return ToolResult(content=summary, structured_content=PrefabApp(view=view, title="Error"))

        data = result.get("data") or {}
        summary = str(data.get("text") or result.get("message") or "")[:4000]
        card = build_inspire_structure_card(result)
        return ToolResult(
            content=summary or f"Structure for {data.get('owner')}/{data.get('repo')}",
            structured_content=PrefabApp(view=card, title=f"{data.get('owner')}/{data.get('repo')}"),
        )

    logger.info("Fleet surface registered: prompts, resources, inspire_repo_structure_card")
