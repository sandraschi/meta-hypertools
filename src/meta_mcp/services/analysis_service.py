from typing import Any

from meta_mcp.services.base import MetaMCPService
from meta_mcp.tools.mcp_repo_analyzer import analyze_runts, get_repo_status


class AnalysisService(MetaMCPService):
    """
    Service for analyzing repositories and identifying SOTA "runts".
    """

    async def analyze_repositories(
        self,
        scan_path: str | None = None,
        format: str = "json",
        use_cache: bool = True,
    ) -> dict[str, Any] | str:
        """Analyze broad paths for MCP repositories."""
        return await analyze_runts(scan_path=scan_path, format=format, use_cache=use_cache)

    async def analyze_single_repo(self, repo_path: str, format: str = "json") -> dict[str, Any] | str:
        """Analyze a specific repository for SOTA compliance."""
        return await get_repo_status(repo_path, format=format)

    async def run_runt_analyzer(self, operation: str, repo_path: str, **kwargs) -> dict[str, Any]:
        """Run runt analyzer operations."""
        if operation == "analyze":
            result = await self.analyze_repositories(scan_path=repo_path)
            if isinstance(result, dict):
                return self.create_response(True, "Repository analysis completed", result)
            else:
                return self.create_response(False, "Analysis failed")
        elif operation == "status":
            result = await self.analyze_single_repo(repo_path)
            if isinstance(result, dict):
                return self.create_response(True, "Repository status retrieved", result)
            else:
                return self.create_response(False, "Status check failed")
        return self.create_response(False, f"Unsupported operation: {operation}")

    async def get_repo_status(self, repo_path: str, operation: str = "status") -> dict[str, Any]:
        """Get repository status information."""
        try:
            result = await self.analyze_single_repo(repo_path)
            if isinstance(result, dict):
                return self.create_response(True, "Repository status retrieved", result)
            else:
                return self.create_response(False, "Failed to get repository status")
        except Exception as e:
            return self.create_response(False, f"Repository status check failed: {e!s}")
