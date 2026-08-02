from typing import Any, Literal

from fastmcp import FastMCP

from meta_mcp.services.analysis_depot_service import AnalysisDepotService
from meta_mcp.services.analysis_service import AnalysisService
from meta_mcp.tools.repomix_analyzer import RepomixAnalysisService


def register_analysis_tools(mcp: FastMCP):
    """Register analysis tool suite with FastMCP."""

    service = AnalysisService()
    repomix_service = RepomixAnalysisService()
    depot = AnalysisDepotService()

    @mcp.tool(name="analysis_ops")
    async def analysis_ops(
        operation: Literal["runts", "status", "codebase", "list_depot", "get_depot_run", "publish_mcd"],
        scan_path: str | None = None,
        repo_path: str | None = None,
        format: str = "json",
        export_mcd: bool = False,
        use_cache: bool = True,
        analysis_type: str = "overview",
        include_patterns: list[str] | None = None,
        exclude_patterns: list[str] | None = None,
        compression_enabled: bool = True,
        limit: int = 20,
        run_id: str | None = None,
        update_project_snapshots: bool = True,
        dry_run: bool = False,
        create_bak: bool = False,
    ) -> dict[str, Any] | str:
        """Repository analysis and SOTA compliance (portmanteau).

        [RATIONALE]
        Consolidates 6 related operations into a single tool to prevent tool explosion while enabling full API coverage.

        ## Operations
        - **runts**: Scan repos for SOTA compliance gaps
        - **status**: Get detailed SOTA compliance for one repo
        - **codebase**: Deep codebase analysis via Repomix
        - **list_depot**: List archived analysis runs in the depot
        - **get_depot_run**: Load a specific analysis run from the depot
        - **publish_mcd**: Export analysis results to mcp-central-docs

        ## Safety Flags
        - **dry_run**: Preview operations without persisting results (default False)
        - **create_bak**: Create timestamped .bak files before any mutation (default False)

        ## Return Format
        {"success": bool, "operation": str, "message": str}

        ## Examples
        await analysis_ops(operation="runts")
        await analysis_ops(operation="status", dry_run=True)
        await analysis_ops(operation="runts", create_bak=True)
        """
        if operation == "runts":
            if dry_run:
                return {
                    "success": True,
                    "operation": "runts",
                    "dry_run": True,
                    "message": f"[DRY-RUN] Scan {scan_path or 'default path'}. dry_run=False to execute.",
                }
            result = await service.analyze_repositories(
                scan_path=scan_path,
                format=format,
                use_cache=use_cache,
            )
            if export_mcd and isinstance(result, dict) and result.get("success"):
                if create_bak:
                    depot.create_backup()
                export = depot.export_to_mcd()
                if isinstance(result, dict):
                    result = {**result, "mcd_export": export}
            if isinstance(result, dict):
                result["create_bak"] = create_bak
            return result
        elif operation == "status":
            if dry_run:
                return {
                    "success": True,
                    "operation": "status",
                    "dry_run": True,
                    "message": f"[DRY-RUN] Would analyze repo at {repo_path}. dry_run=False to execute.",
                }
            result = await service.analyze_single_repo(repo_path, format=format)
            if export_mcd and isinstance(result, dict) and result.get("success"):
                depot.export_to_mcd()
            return result
        elif operation == "codebase":
            if dry_run:
                return {
                    "success": True,
                    "operation": "codebase",
                    "dry_run": True,
                    "message": f"[DRY-RUN] Would analyze {repo_path} with repomix. dry_run=False to execute.",
                }
            return await repomix_service.analyze_with_repomix(
                repo_path=repo_path,
                analysis_type=analysis_type,
                include_patterns=include_patterns,
                exclude_patterns=exclude_patterns,
                compression_enabled=compression_enabled,
            )
        elif operation == "list_depot":
            return depot.list_runs(limit=limit)
        elif operation == "get_depot_run":
            return depot.get_run(run_id, format=format)
        elif operation == "publish_mcd":
            if dry_run:
                return {
                    "success": True,
                    "operation": "publish_mcd",
                    "dry_run": True,
                    "message": "[DRY-RUN] Would export analysis results to mcd. dry_run=False to execute.",
                }
            return depot.export_to_mcd(
                run_id=run_id,
                update_project_snapshots=update_project_snapshots,
            )
