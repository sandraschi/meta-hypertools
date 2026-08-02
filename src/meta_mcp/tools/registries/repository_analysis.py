from typing import Any

from fastmcp import FastMCP

from meta_mcp.services.repo_scanner_service import RepoScannerService
from meta_mcp.tools.adjudicator import benny_handshake, generate_patch, verify_exploit


def register_repository_analysis_tools(mcp: FastMCP):
    """Register repository analysis tool suite with FastMCP."""

    service = RepoScannerService()

    @mcp.tool(name="deep_scan_repo", task=True)
    async def scan_repository_deep(repo_path: str, deep_analysis: bool = False) -> dict[str, Any]:
        """Deep repository scan.

        Perform full spectrum repository analysis including SOTA compliance, dependency health, and quality.
        """
        return await service.scan_repository(repo_path, deep_analysis)

    # Register The Adjudicator Tools
    @mcp.tool(name="verify_exploit")
    async def verify_exploit_tool(vulnerability_id: str, repo_name: str) -> dict[str, Any]:
        """Grounded exploit verification tool.
        Analyzes a reported vulnerability against the CE-AKG and local environment.
        """
        return await verify_exploit(vulnerability_id, repo_name)

    @mcp.tool(name="generate_patch")
    async def generate_patch_tool(vulnerability_id: str, repo_name: str) -> dict[str, Any]:
        """Generate a security patch for a verified exploit.
        Uses CE-AKG insights to ensure the patch doesn't break inter-repo dependencies.
        """
        return await generate_patch(vulnerability_id, repo_name)

    @mcp.tool(name="benny_handshake")
    async def benny_handshake_tool(auth_token: str | None = None) -> dict[str, Any]:
        """The "Benny" Protocol: Physical Interrupt for critical operations.
        Requires a local hardware handshake (presence of .benny_lock) or Wurst-Auth override.
        """
        return await benny_handshake(auth_token)
