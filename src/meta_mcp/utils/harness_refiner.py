"""Gap analysis and incremental refinement for harness-generated MCP servers.

Compares a running MCP server's tool surface against a fresh source analysis
and provides non-destructive incremental improvement.

Refinement phase adapted from the CLI-Anything 7-phase harness workflow
(HKUDS/CLI-Anything, Apache 2.0, arXiv:2606.03854).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class GapReport:
    software_name: str
    server_path: str
    source_path: str
    existing_tool_names: list[str] = field(default_factory=list)
    missing_groups: list[str] = field(default_factory=list)
    missing_operations: dict[str, list[str]] = field(default_factory=dict)
    unchanged_groups: list[str] = field(default_factory=list)
    total_missing: int = 0
    total_existing: int = 0
    total_available: int = 0


def _extract_existing_tool_names(server_path: str) -> list[str]:
    """Scan a generated server's tools directory for existing tool modules."""
    tools_dir = os.path.join(server_path, "src", "tools") if server_path else ""
    if not os.path.isdir(tools_dir):
        # Try package-style path
        parts = Path(server_path).parts
        for i in range(len(parts)):
            candidate = os.path.join(*parts[: i + 1], "src", "tools")
            if os.path.isdir(candidate):
                tools_dir = candidate
                break

    if not os.path.isdir(tools_dir):
        return []

    existing: list[str] = []
    for fname in sorted(os.listdir(tools_dir)):
        if (
            fname.endswith(".py")
            and not fname.startswith("_")
            and fname not in ("help_tools.py", "chat_tool.py", "agentic_workflow.py")
        ):
            existing.append(fname.replace(".py", ""))
    return existing


def diff_against_source(
    server_path: str,
    source_path: str,
    software_name: str = "",
) -> GapReport:
    """Compare existing server tools against a fresh source analysis.

    Args:
        server_path: Path to the generated MCP server.
        source_path: Path to the original source code.
        software_name: Override name for the analysis.

    Returns:
        GapReport with missing groups and operations.
    """
    from meta_mcp.utils.harness_analyzer import generate_tool_surface_spec

    existing = _extract_existing_tool_names(server_path)
    spec = generate_tool_surface_spec(
        source_path=source_path,
        source_type="local",
        software_name=software_name,
        full=False,
    )

    existing_set = set(existing)
    spec_groups = {g.name: [op.name for op in g.operations] for g in spec.tool_groups}

    missing_groups: list[str] = []
    missing_operations: dict[str, list[str]] = {}
    unchanged_groups: list[str] = []

    for group_name, op_names in spec_groups.items():
        if group_name not in existing_set:
            missing_groups.append(group_name)
            missing_operations[group_name] = op_names
        else:
            unchanged_groups.append(group_name)

    total_missing = sum(len(ops) for ops in missing_operations.values())

    return GapReport(
        software_name=spec.software_name,
        server_path=server_path,
        source_path=source_path,
        existing_tool_names=existing,
        missing_groups=missing_groups,
        missing_operations=missing_operations,
        unchanged_groups=unchanged_groups,
        total_missing=total_missing,
        total_existing=len(existing),
        total_available=len(spec.tool_groups),
    )


def add_missing_tools(
    server_path: str,
    report: GapReport,
    *,
    group_filter: list[str] | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Add missing tool modules to an existing harness-generated server.

    Non-destructive: never modifies existing tool files. Only creates NEW files
    for groups that don't already exist in the server.

    Args:
        server_path: Path to the generated MCP server.
        report: GapReport from diff_against_source.
        group_filter: Only add these specific groups (None = all missing).
        dry_run: If True, don't write files, just report what would be created.

    Returns:
        dict with added groups, file paths, and operation counts.
    """
    from meta_mcp.utils.harness_analyzer import generate_tool_surface_spec
    from meta_mcp.utils.server_builder_from_spec import _generate_portmanteau_tool

    spec = generate_tool_surface_spec(
        source_path=report.source_path,
        source_type="local",
        software_name=report.software_name,
        full=False,
    )

    # Find the package name from the server's existing structure
    src_dir = os.path.join(server_path, "src")
    package_name = ""
    if os.path.isdir(src_dir):
        for entry in os.listdir(src_dir):
            if os.path.isdir(os.path.join(src_dir, entry)) and os.path.isfile(
                os.path.join(src_dir, entry, "__init__.py")
            ):
                package_name = entry
                break

    if not package_name:
        package_name = report.software_name.replace("-", "_").lower()

    tools_dir = os.path.join(server_path, "src", package_name, "tools")
    if not os.path.isdir(tools_dir):
        os.makedirs(tools_dir, exist_ok=True)

    target_groups = group_filter if group_filter else report.missing_groups
    spec_group_lookup = {g.name: g for g in spec.tool_groups}

    added: list[dict[str, Any]] = []
    for group_name in target_groups:
        group = spec_group_lookup.get(group_name)
        if not group:
            continue

        tool_path = os.path.join(tools_dir, f"{group_name}.py")
        if os.path.exists(tool_path):
            continue

        code = _generate_portmanteau_tool(
            package_name,
            {
                "name": group.name,
                "domain": group.domain,
                "operations": [
                    {
                        "name": op.name,
                        "params": op.params,
                        "docstring": op.docstring,
                        "is_async": op.is_async,
                        "is_mutating": op.is_mutating,
                    }
                    for op in group.operations
                ],
            },
            spec.backend_engine,
        )

        if not dry_run:
            with open(tool_path, "w", encoding="utf-8") as fh:
                fh.write(code)

        added.append(
            {
                "group_name": group.name,
                "domain": group.domain,
                "file_path": tool_path,
                "operation_count": len(group.operations),
                "dry_run": dry_run,
            }
        )

    # Update tool_registration.py to include new imports
    reg_path = os.path.join(server_path, "src", package_name, "tool_registration.py")
    if os.path.exists(reg_path) and added:
        new_imports = "\n".join(f"from {package_name}.tools.{a['group_name']} import {a['group_name']}" for a in added)
        if not dry_run:
            with open(reg_path, "a", encoding="utf-8") as fh:
                fh.write("\n" + new_imports + "\n")

    return {
        "success": True,
        "message": f"{'Would add' if dry_run else 'Added'} {len(added)} tool group(s)",
        "added": added,
        "dry_run": dry_run,
        "total_operations_added": sum(a["operation_count"] for a in added),
    }


def gap_report_to_dict(report: GapReport) -> dict[str, Any]:
    """Serialize a GapReport to a dict."""
    return {
        "software_name": report.software_name,
        "server_path": report.server_path,
        "source_path": report.source_path,
        "existing_tool_names": report.existing_tool_names,
        "missing_groups": report.missing_groups,
        "missing_operations": report.missing_operations,
        "unchanged_groups": report.unchanged_groups,
        "total_missing": report.total_missing,
        "total_existing": report.total_existing,
        "total_available": report.total_available,
    }
