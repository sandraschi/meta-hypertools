from typing import Any, Literal

from fastmcp import FastMCP

from meta_mcp.services.token_analysis_service import TokenAnalysisService


def register_token_analysis_tools(mcp: FastMCP):
    """Register token analysis tool suite with FastMCP."""

    service = TokenAnalysisService()

    @mcp.tool(name="token_ops")
    async def token_portmanteau(
        operation: Literal["analyze_file", "analyze_dir", "context_limits"],
        file_path: str | None = None,
        dir_path: str | None = None,
        extensions: list[str] | None = None,
        token_count: int | None = None,
    ) -> dict[str, Any]:
        """Token usage analysis for files and directories (portmanteau).

        [RATIONALE]
        Consolidates 3 related operations into a single tool to prevent tool explosion while enabling full API coverage.

        ## Operations
                - **analyze_file**: Count tokens in a single file
                - **analyze_dir**: Recursive token audit of a directory
                - **context_limits**: Check token count against LLM context windows

        ## Return Format
        {"success": bool, "operation": str, "message": str}

        ## Examples








        a
        w
        a
        i
        t

        t
        o
        k
        e
        n
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
        a
        n
        a
        l
        y
        z
        e
        _
        f
        i
        l
        e
        "
        )










        a
        w
        a
        i
        t

        t
        o
        k
        e
        n
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
        a
        n
        a
        l
        y
        z
        e
        _
        d
        i
        r
        "
        )
        """
        if operation == "analyze_file":
            if not file_path:
                return {"success": False, "error": "file_path required"}
            return await service.analyze_file_tokens(file_path)
        elif operation == "analyze_dir":
            if not dir_path:
                return {"success": False, "error": "dir_path required"}
            return await service.analyze_directory_tokens(dir_path, extensions)
        elif operation == "context_limits":
            if token_count is None:
                return {"success": False, "error": "token_count required"}
            return await service.estimate_context_limits(token_count)
        return {"success": False, "error": f"Unknown operation: {operation}"}
