from typing import Any, Literal

from fastmcp import FastMCP

from meta_mcp.services.repo_packing_service import RepoPackingService


def register_repo_packing_tools(mcp: FastMCP):
    """Register repository packing tool suite with FastMCP."""

    service = RepoPackingService()

    @mcp.tool(name="pack_ops")
    async def pack_portmanteau(
        operation: Literal["pack", "pack_ai"],
        repo_path: str,
        output_format: str = "xml",
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        max_tokens: int = 100000,
    ) -> dict[str, Any]:
        """Repository packing for LLM context (portmanteau).

        [RATIONALE]
        Consolidates 2 related operations into a single tool to prevent tool explosion while enabling full API coverage.

        ## Operations
                - **pack**: Consolidate repo into a single file
                - **pack_ai**: Auto-select files to fit within token limits

        ## Return Format
        {"success": bool, "operation": str, "message": str}

        ## Examples








        a
        w
        a
        i
        t

        p
        a
        c
        k
        _
        o
        p
        s
        (
        o
        p
        e
        r
        a
        t
        i
        o
        n
        =
        "
        p
        a
        c
        k
        "
        )










        a
        w
        a
        i
        t

        p
        a
        c
        k
        _
        o
        p
        s
        (
        o
        p
        e
        r
        a
        t
        i
        o
        n
        =
        "
        p
        a
        c
        k
        _
        a
        i
        "
        )
        """
        if operation == "pack":
            return await service.pack_repository(repo_path, output_format, include_patterns, exclude_patterns)
        elif operation == "pack_ai":
            return await service.pack_for_ai_consumption(repo_path, max_tokens)
        return {"success": False, "error": f"Unknown operation: {operation}"}
