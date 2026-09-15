import asyncio
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from meta_mcp.services.base import MetaMCPService
from meta_mcp.services.emoji_buster import EmojiBuster
from meta_mcp.services.powershell_profile_manager import PowerShellProfileManager
from meta_mcp.services.powershell_validator import PowerShellSyntaxValidator


class DiagnosticsService(MetaMCPService):
    """
    Unified diagnostics orchestrator for Meta MCP.
    Consolidates Unicode safety, PowerShell validation, justfile audit, and project health.
    """

    def __init__(self):
        super().__init__()
        self.emoji_buster = EmojiBuster()
        self.ps_validator = PowerShellSyntaxValidator()
        self.ps_profile_manager = PowerShellProfileManager()

    async def run_emojibuster(self, operation: str, repo_path: str, **kwargs) -> dict[str, Any]:
        """Orchestrate EmojiBuster operations."""
        if operation == "scan":
            return await self.emoji_buster.scan_repository(repo_path, kwargs.get("scan_mode", "comprehensive"))
        elif operation == "fix":
            return await self.emoji_buster.fix_unicode_logging(repo_path, kwargs.get("backup", True))
        return self.create_response(False, f"Unsupported operation: {operation}")

    async def run_powershell_tools(self, operation: str, repo_path: str | None = None, **kwargs) -> dict[str, Any]:
        """Orchestrate PowerShell diagnostic tools."""
        if operation == "validate" and repo_path:
            return await self.ps_validator.scan_repository(repo_path, kwargs.get("scan_mode", "comprehensive"))
        elif operation == "profile":
            return await self.ps_profile_manager.create_profile(
                enable_aliases=kwargs.get("include_aliases", True),
                enable_error_handling=True,
                obscure_location=True,
            )
        return self.create_response(False, f"Unsupported operation: {operation}")

    async def validate_justfile(self, repo_path: str, fix: bool = False) -> dict[str, Any]:
        """Audit a repo's justfile for fleet standard compliance."""
        path = Path(repo_path).expanduser().resolve()
        justfile = path / "justfile"
        findings: list[dict[str, Any]] = []
        fixable = False

        if not justfile.is_file():
            return self.create_response(
                False,
                f"No justfile found at {justfile}",
                {
                    "path": str(justfile),
                    "findings": [{"severity": "error", "message": "justfile not found"}],
                    "fixable": False,
                },
            )

        content = justfile.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()

        required_recipes = ["test", "lint", "default", "mcpb-pack"]
        found_recipes = set()
        for line in lines:
            m = re.match(r"^([a-z][a-z0-9_-]+(?:\s+[a-z][a-z0-9_-]+)*):", line)
            if m:
                for name in m.group(1).split():
                    found_recipes.add(name)
        for recipe in required_recipes:
            if recipe not in found_recipes:
                findings.append({"severity": "error", "message": f"Required recipe '{recipe}' not found"})

        compound = re.compile(r"^ {8,}(if|foreach|for|while|switch|try|catch|finally)\b")
        for i, line in enumerate(lines, 1):
            if compound.match(line):
                findings.append(
                    {
                        "severity": "warning",
                        "line": i,
                        "message": f"Inline pwsh at line {i}: '{line.strip()[:40]}'  extract to scripts/*.ps1",
                    }
                )

        if "powershell.exe" not in content and "pwsh.exe" not in content:
            findings.append(
                {
                    "severity": "info",
                    "message": "Missing shell declaration  add 'set windows-shell := [...]'",
                }
            )

        try:
            env = os.environ.copy()
            env["JUST_UNSTABLE"] = "1"
            result = await asyncio.to_thread(
                subprocess.run,
                ["just", "--fmt", "--check", "--justfile", str(justfile)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(path),
                env=env,
            )
            if result.returncode != 0:
                for line in result.stderr.splitlines():
                    if line.strip():
                        findings.append({"severity": "error", "message": line.strip(), "fixable": True})
                fixable = True
        except FileNotFoundError:
            findings.append({"severity": "error", "message": "just CLI not found on PATH"})
        except subprocess.TimeoutExpired:
            findings.append({"severity": "warning", "message": "just --check timed out (30s)"})

        summary = {
            "path": str(justfile),
            "recipe_count": len(found_recipes),
            "recipes": sorted(found_recipes),
            "findings": findings,
            "fixable": fixable,
            "pass": len([f for f in findings if f["severity"] == "error"]) == 0,
        }
        msg = "justfile passes fleet standard" if summary["pass"] else f"{len(findings)} issue(s) found"
        return self.create_response(summary["pass"], msg, summary)
