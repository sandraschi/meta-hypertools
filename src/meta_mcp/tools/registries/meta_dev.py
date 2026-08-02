"""Meta / fleet developer helper tools."""

from __future__ import annotations

from typing import Any, Literal

from fastmcp import FastMCP

from meta_mcp.tools import meta_dev_impl as impl


def register_meta_dev_tools(mcp: FastMCP) -> None:
    """Register fleet/meta helper tools."""

    @mcp.tool(name="meta_dev_ops")
    async def meta_dev_ops(
        operation: Literal[
            "probe",
            "diff",
            "snippet",
            "audit_surface",
            "orphans",
            "tail",
            "env",
            "summarize",
            "changelog",
            "redact",
        ],
        central_docs_root: str | None = None,
        timeout_sec: float = 3.0,
        max_checks: int = 150,
        path_a: str | None = None,
        path_b: str | None = None,
        server_key: str | None = None,
        repo_path: str | None = None,
        min_hits: int = 1,
        file_path: str | None = None,
        lines: int = 120,
        required_keys: list[str] | None = None,
    ) -> dict[str, Any]:
        """Fleet developer and meta-operation helpers (portmanteau).

        [RATIONALE]
        Consolidates 10 related operations into a single tool to prevent
        tool explosion while enabling full API coverage.

        ## Operations
        - **probe**: Health-check all port-mapped fleet servers
        - **diff**: Diff two MCP configuration files
        - **snippet**: Export a server config snippet for manual IDE setup
        - **audit_surface**: Count FastMCP decorators in a repo
        - **orphans**: Find tool functions with few internal references
        - **tail**: Tail a log file
        - **env**: Check required environment variables exist
        - **summarize**: Generate a Markdown summary of a server config
        - **changelog**: Extract latest CHANGELOG entries
        - **redact**: Heuristically find and redact secrets in a file

        ## Return Format
        {"success": bool, "operation": str, "message": str}

        ## Examples
        await meta_dev_ops(operation="probe")
        await meta_dev_ops(operation="diff")
        """
        if operation == "probe":
            return await impl.probe_fleet_health_impl(central_docs_root, timeout_sec, max_checks)
        elif operation == "diff":
            return impl.diff_mcp_configs_impl(path_a, path_b)
        elif operation == "snippet":
            return impl.export_cursor_mcp_snippet_impl(server_key)
        elif operation == "audit_surface":
            return impl.audit_fastmcp_surface_impl(repo_path)
        elif operation == "orphans":
            return impl.find_orphan_tool_references_impl(repo_path, min_hits)
        elif operation == "tail":
            return impl.tail_log_file_impl(file_path, lines)
        elif operation == "env":
            return impl.env_sanity_check_impl(required_keys)
        elif operation == "summarize":
            return impl.summarize_server_for_prompt_impl(server_key)
        elif operation == "changelog":
            return impl.mcp_changelog_digest_impl(repo_path)
        elif operation == "redact":
            return impl.redact_secrets_audit_impl(file_path)
