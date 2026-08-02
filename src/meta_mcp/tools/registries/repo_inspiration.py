from typing import Any, Literal

from fastmcp import Context, FastMCP

from meta_mcp.services.repo_inspiration_service import RepoInspirationService
from meta_mcp.utils.repo_inspiration_profiles import INSPIRE_REPO_HELP


def register_repo_inspiration_tools(mcp: FastMCP) -> None:
    """Register remote GitHub repo inspiration tools (public or token-authenticated)."""

    service = RepoInspirationService()

    @mcp.tool(name="inspire_repo")
    async def inspire_repo(
        operation: Literal["structure", "files", "patterns", "help"],
        url: str,
        target_files: list[str] | None = None,
        subpath: str | None = None,
        branch: str | None = None,
        profile: str = "standard",
        max_chars: int | None = None,
        language_hint: str | None = None,
        include_globs: list[str] | None = None,
        exclude_globs: list[str] | None = None,
    ) -> dict[str, Any]:
        """Study a public GitHub repo without cloning (portmanteau).

        operation: structure | files | patterns | help
        Returns data.text (compat) and data.chapters[] with id, title, kind, body.
        Workflow adapted from Repomuse (MIT, praveene3127).
        """
        return await service.inspire_repo(
            operation,
            url,
            target_files,
            subpath=subpath,
            branch=branch,
            profile=profile,
            max_chars=max_chars,
            language_hint=language_hint,
            include_globs=include_globs,
            exclude_globs=exclude_globs,
        )

    @mcp.tool(name="inspire_repo_structure")
    async def inspire_repo_structure(
        url: str,
        subpath: str | None = None,
        branch: str | None = None,
        profile: str = "standard",
        max_chars: int | None = None,
        include_globs: list[str] | None = None,
        exclude_globs: list[str] | None = None,
    ) -> dict[str, Any]:
        """Get a filtered file tree of a GitHub repository.

        Fetches via GitHub API (no local clone). Noise (node_modules, lockfiles, binaries)
        is excluded. Use before inspire_repo_files. Read for inspiration -- not to copy.
        """
        return await service.inspire_structure(
            url,
            subpath=subpath,
            branch=branch,
            profile=profile,
            max_chars=max_chars,
            include_globs=include_globs,
            exclude_globs=exclude_globs,
        )

    @mcp.tool(name="inspire_repo_files")
    async def inspire_repo_files(
        url: str,
        target_files: list[str] | None = None,
        subpath: str | None = None,
        branch: str | None = None,
        profile: str = "standard",
        max_chars: int | None = None,
        language_hint: str | None = None,
        include_globs: list[str] | None = None,
        exclude_globs: list[str] | None = None,
    ) -> dict[str, Any]:
        """Read source files from a GitHub repository for design inspiration.

        Pass target_files for explicit paths (partial suffixes allowed). Omit to auto-select
        core architectural files. Output capped by profile for token safety.
        """
        return await service.inspire_files(
            url,
            target_files,
            subpath=subpath,
            branch=branch,
            profile=profile,
            max_chars=max_chars,
            language_hint=language_hint,
            include_globs=include_globs,
            exclude_globs=exclude_globs,
        )

    @mcp.tool(name="inspire_repo_patterns")
    async def inspire_repo_patterns(
        url: str,
        subpath: str | None = None,
        branch: str | None = None,
        profile: str = "standard",
        max_chars: int | None = None,
        language_hint: str | None = None,
        include_globs: list[str] | None = None,
        exclude_globs: list[str] | None = None,
    ) -> dict[str, Any]:
        """Build an architecture study pack for a GitHub repository.

        Returns structure, README, manifest, and auto-selected entry-point sources wrapped
        in an analysis prompt. The calling agent should summarize patterns -- not paste code.
        """
        return await service.inspire_patterns(
            url,
            subpath=subpath,
            branch=branch,
            profile=profile,
            max_chars=max_chars,
            language_hint=language_hint,
            include_globs=include_globs,
            exclude_globs=exclude_globs,
        )

    @mcp.tool(name="inspire_repo_workflow")
    async def inspire_repo_workflow(
        goal: str,
        url: str,
        subpath: str | None = None,
        branch: str | None = None,
        profile: str = "brief",
        max_paths: int = 5,
        max_chars: int | None = None,
        language_hint: str | None = None,
        include_globs: list[str] | None = None,
        exclude_globs: list[str] | None = None,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """Agentic multi-step repo study: structure  pick paths  files  patterns  synthesis.

        Uses MCP sampling (ctx.sample) when the host supports it; otherwise deterministic path pick.
        """
        return await service.inspire_repo_workflow(
            url,
            goal,
            subpath=subpath,
            branch=branch,
            profile=profile,
            max_paths=max_paths,
            max_chars=max_chars,
            language_hint=language_hint,
            include_globs=include_globs,
            exclude_globs=exclude_globs,
            ctx=ctx,
        )

    @mcp.tool(name="inspire_repo_help")
    async def inspire_repo_help() -> dict[str, Any]:
        """Parameter reference for inspire_repo and related inspiration tools.

        Returns the same help text as inspire_repo(operation=help). See docs/tools/repo-inspiration.md.
        """
        return {
            "success": True,
            "message": "inspire_repo help",
            "data": {
                "text": INSPIRE_REPO_HELP,
                "chapters": [
                    {
                        "id": "help",
                        "title": "inspire_repo help",
                        "kind": "hint",
                        "body": INSPIRE_REPO_HELP,
                    }
                ],
                "operation": "help",
            },
        }

    from meta_mcp.fleet_surface import register_fleet_surface

    register_fleet_surface(mcp, inspiration_service=service)
