"""MCP tool registration: harness analysis and generation tools."""

from __future__ import annotations

import os
from typing import Any, Literal

from fastmcp import Context, FastMCP

from meta_mcp.utils.harness_analyzer import (
    ToolSurfaceSpec,
    generate_tool_surface_spec,
    spec_to_dict,
)
from meta_mcp.utils.harness_refiner import (
    add_missing_tools,
    diff_against_source,
    gap_report_to_dict,
)
from meta_mcp.utils.server_builder_from_spec import generate_server_from_spec


def _dict_to_spec(d: dict[str, Any]) -> ToolSurfaceSpec:
    """Reconstruct a ToolSurfaceSpec from a dict (for MCP tool input)."""
    from meta_mcp.utils.harness_analyzer import (
        ExtractedOperation,
        ToolGroup,
    )

    groups = []
    for g in d.get("tool_groups", []):
        ops = []
        for o in g.get("operations", []):
            ops.append(
                ExtractedOperation(
                    name=o.get("name", ""),
                    signature=o.get("signature", ""),
                    params=o.get("params", []) or [],
                    docstring=o.get("docstring"),
                    decorators=o.get("decorators", []) or [],
                    is_async=o.get("is_async", False),
                    is_mutating=o.get("is_mutating", False),
                    source_file=o.get("source_file", ""),
                    line_number=o.get("line_number", 0),
                )
            )
        groups.append(
            ToolGroup(
                name=g.get("name", ""),
                domain=g.get("domain", ""),
                operations=ops,
                curated=g.get("curated", True),
            )
        )

    return ToolSurfaceSpec(
        software_name=d.get("software_name", "unknown"),
        source_type=d.get("source_type", "local"),
        source_path=d.get("source_path", ""),
        language=d.get("language", "python"),
        backend_engine=d.get("backend_engine", "unknown"),
        backend_details=d.get("backend_details", {}),
        tool_groups=groups,
        state_model=d.get("state_model", "stateless"),
        warnings=d.get("warnings", []) or [],
        total_operations_found=d.get("total_operations_found", 0),
        total_operations_curated=d.get("total_operations_curated", 0),
    )


def register_harness_tools(mcp: FastMCP) -> None:
    """Register harness analysis and generation MCP tools."""

    @mcp.tool(name="harness_analyze")
    async def harness_analyze(
        source_path: str,
        source_type: Literal["local", "github"] = "local",
        software_name: str = "",
        full: bool = False,
    ) -> dict[str, Any]:
        """Analyse a codebase and produce a structured tool surface specification.

        Reads Python source files, extracts function signatures and domain groupings,
        and produces a ToolSurfaceSpec suitable for harness_generate.

        Curation (full=False): drops private helpers, getters/setters, stubs, and
        test files. full=True exposes every public function found.

        ## Return Format
        {"success": bool, "data": {"spec": ToolSurfaceSpec}}

        ## Examples
        harness_analyze(source_path="D:/tools/pandoc-wrapper")
        harness_analyze(source_path="https://github.com/o/r", source_type="github")
        harness_analyze(source_path="./mycli", full=True)
        """
        if not source_path or not source_path.strip():
            return {
                "success": False,
                "message": "source_path is required",
                "error_type": "invalid_input",
                "data": {},
            }

        try:
            spec = generate_tool_surface_spec(
                source_path=source_path,
                source_type=source_type,
                software_name=software_name.strip() if software_name else "",
                full=full,
            )
            return {
                "success": True,
                "message": (
                    f"Analysed {spec.software_name}: {spec.total_operations_curated} curated "
                    f"operations across {len(spec.tool_groups)} tool groups"
                    f" (found {spec.total_operations_found} total, "
                    f"backend: {spec.backend_engine}, state: {spec.state_model})"
                ),
                "data": {
                    "spec": spec_to_dict(spec),
                    "warnings": spec.warnings,
                },
                "tool_group_count": len(spec.tool_groups),
                "operation_count": spec.total_operations_curated,
            }
        except Exception as exc:
            return {
                "success": False,
                "message": f"Analysis failed: {exc!s}",
                "error_type": "unknown",
                "data": {},
            }

    @mcp.tool(name="harness_generate")
    async def harness_generate(
        spec_dict: dict[str, Any],
        target_path: str,
        author: str = "MetaMCP Harness Generator",
        license_type: str = "MIT",
        include_nsis: bool = False,
    ) -> dict[str, Any]:
        """Generate a fleet-conformant FastMCP server from a ToolSurfaceSpec.

        Takes the spec output from harness_analyze and generates a complete
        FastMCP 3.4+ server with portmanteau tools per domain group, Prefab
        cards, SKILL.md, dual transport, and full fleet surface.

        The generated server follows all SOTA 2026 standards: portmanteau
        pattern, Pydantic v2, docstring protocol, annotations, Prefab UI,
        mcpb packaging, and justfile recipes.

        ## Return Format
        {"success": bool, "message": str, "data": {"generated_path": str, "file_count": int, ...}}

        ## Examples
        harness_generate(spec_dict=spec, target_path="D:/repos/my-harness")
        harness_generate(spec_dict=spec, target_path="./output", include_nsis=True)
        """
        if not spec_dict or not spec_dict.get("tool_groups"):
            return {
                "success": False,
                "message": "spec_dict with tool_groups is required -- run harness_analyze first",
                "error_type": "invalid_input",
                "data": {},
            }

        target = target_path.strip()
        if not target:
            return {
                "success": False,
                "message": "target_path is required",
                "error_type": "invalid_input",
                "data": {},
            }

        try:
            spec = _dict_to_spec(spec_dict)
            result = generate_server_from_spec(
                spec=spec,
                target_path=target,
                author=author.strip() or "MetaMCP Harness Generator",
                license_type=license_type.strip() or "MIT",
                include_nsis=include_nsis,
            )
            return result
        except Exception as exc:
            return {
                "success": False,
                "message": f"Generation failed: {exc!s}",
                "error_type": "unknown",
                "data": {},
            }

    @mcp.tool(name="harness_refine")
    async def harness_refine(
        operation: Literal["gap", "add"],
        server_path: str,
        source_path: str,
        software_name: str = "",
        group_filter: list[str] | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Iteratively improve a harness-generated MCP server.

        Compares the current server tool surface against a fresh source analysis
        and provides non-destructive incremental improvement.

        - **gap**: Re-analyse source, diff against existing tools. Returns
          missing groups and operations that could be added.
        - **add**: Add missing tool groups from gap analysis. Never modifies
          existing tool files -- only creates new ones.

        ## Return Format
        gap:  {"success": bool, "data": {"report": GapReport}}
        add:  {"success": bool, "data": {"added": [...], "dry_run": bool}}

        ## Examples
        harness_refine(operation="gap", server_path="./output", source_path="./src")
        harness_refine(operation="add", server_path="./output", source_path="./src")
        harness_refine(operation="add", server_path="./output", source_path="./src",
                       group_filter=["myapp_export"], dry_run=True)
        """
        server = server_path.strip()
        source = source_path.strip()
        if not server or not source:
            return {
                "success": False,
                "message": "server_path and source_path are required",
                "error_type": "invalid_input",
                "data": {},
            }

        try:
            if operation == "gap":
                report = diff_against_source(
                    server_path=server,
                    source_path=source,
                    software_name=software_name.strip(),
                )
                report_dict = gap_report_to_dict(report)
                return {
                    "success": True,
                    "message": (
                        f"Gap analysis: {report.total_existing} existing groups, "
                        f"{len(report.missing_groups)} missing "
                        f"({report.total_missing} operations)"
                    ),
                    "data": {
                        "report": report_dict,
                    },
                }
            elif operation == "add":
                report = diff_against_source(
                    server_path=server,
                    source_path=source,
                    software_name=software_name.strip(),
                )
                if not report.missing_groups:
                    return {
                        "success": True,
                        "message": "No missing tools -- server is up to date",
                        "data": {},
                    }
                result = add_missing_tools(
                    server_path=server,
                    report=report,
                    group_filter=group_filter,
                    dry_run=dry_run,
                )
                return result
            else:
                return {
                    "success": False,
                    "message": f'Unknown operation "{operation}". Use gap or add.',
                    "error_type": "invalid_input",
                    "data": {},
                }
        except Exception as exc:
            return {
                "success": False,
                "message": f"Refinement failed: {exc!s}",
                "error_type": "unknown",
                "data": {},
            }
