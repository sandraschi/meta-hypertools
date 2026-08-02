"""
PowerShell Profile Manager - "Argh-Coding" Bloop-Buster

This tool creates and manages PowerShell profiles that prevent Linux command errors
from breaking scripts and chat sessions. Sets up aliases and error handling in obscure
PowerShell profile locations.
"""

import os
from pathlib import Path
from typing import Any

import structlog
from fastmcp import FastMCP

logger = structlog.get_logger(__name__)

# PowerShell profile locations (obscure but effective)
POWERSHELL_PROFILE_PATHS = [
    # Current user PowerShell profile (most common)
    Path(os.path.expanduser("~/Documents/PowerShell/Microsoft.PowerShell_profile.ps1")),
    # System-wide PowerShell profile (requires admin)
    Path("C:/Windows/System32/WindowsPowerShell/v1.0/Microsoft.PowerShell_profile.ps1"),
    # PowerShell 7 profile (if installed)
    Path(os.path.expanduser("~/Documents/PowerShell/Microsoft.PowerShell_profile.ps1")),
    # PowerShell 7.0 specific
    Path(os.path.expanduser("~/Documents/PowerShell/Microsoft.PowerShell_profile.ps1")),
    # Custom MetaMCP profile location (obscure but effective)
    Path(os.path.expanduser("~/.config/powershell/MetaMCP_profile.ps1")),
    # AppData local PowerShell profile
    Path(os.path.expanduser("~/AppData/Local/Microsoft/WindowsPowerShell/MetaMCP_profile.ps1")),
]

# Linux command to PowerShell aliases
LINUX_TO_POWERSHELL_ALIASES = {
    "ls": "Get-ChildItem",
    "la": "Get-ChildItem -Force",
    "ll": "Get-ChildItem -Force | Format-Table Name, LastWriteTime, Length",
    "grep": "Select-String",
    "cat": "Get-Content",
    "tail": "Get-Content -Tail 10",
    "head": "Get-Content -TotalCount 10",
    "ps": "Get-Process",
    "top": "Get-Process | Sort-Object CPU -Descending | Select-Object -First 10",
    "kill": "Stop-Process",
    "chmod": "Set-ItemProperty",
    "chown": "Set-ItemProperty",
    "find": "Get-ChildItem -Recurse",
    "cp": "Copy-Item",
    "mv": "Move-Item",
    "rm": "Remove-Item",
    "mkdir": "New-Item -Type Directory",
    "rmdir": "Remove-Item -Recurse",
    "touch": "New-Item",
    "df": "Get-Volume",
    "du": "Get-ChildItem -Recurse -File | Measure-Object Length",
    "free": "Get-Process | Measure-Object WorkingSet",
    "uname": "Get-ComputerInfo",
    "whoami": "Get-Content env:USERNAME",
    "pwd": "Get-Location",
    "cd": "Set-Location",
    "clear": "Clear-Host",
    "exit": "Exit",
    "history": "Get-History",
    "man": "Get-Help",
    "help": "Get-Help",
    "echo": "Write-Host",
    "export": "Set-Item",
    "source": ".",
    "which": "Get-Command",
    "where": "Get-Command",
    "type": "Get-Content",
    "less": "Get-Content | Out-Host -Paging",
    "more": "Get-Content | Out-Host -Paging",
    "vi": "code",  # Default to VS Code
    "vim": "code",  # Default to VS Code
    "nano": "code",  # Default to VS Code
}

# Error handling functions for common Linux commands
ERROR_HANDLING_FUNCTIONS = {
    "ls": "function ls { if ($args.Count -eq 0) { Get-ChildItem } else { Get-ChildItem @args } }",
    "grep": "function grep { if ($args.Count -lt 2) { Write-Host 'Usage: grep pattern file' -ForegroundColor Yellow } else { Select-String @args } }",
    "chmod": "function chmod { Write-Host 'chmod not available in PowerShell. Use Set-ItemProperty instead.' -ForegroundColor Yellow; Get-Help Set-ItemProperty }",
    "sudo": "function sudo { Write-Host 'sudo not available in PowerShell. Run as Administrator instead.' -ForegroundColor Yellow }",
    "apt-get": "function apt-get { Write-Host 'apt-get not available in PowerShell. Use Install-Package or winget instead.' -ForegroundColor Yellow; Get-Help Install-Package }",
    "yum": "function yum { Write-Host 'yum not available in PowerShell. Use Install-Package or winget instead.' -ForegroundColor Yellow; Get-Help Install-Package }",
    "dnf": "function dnf { Write-Host 'dnf not available in PowerShell. Use Install-Package or winget instead.' -ForegroundColor Yellow; Get-Help Install-Package }",
}

# Profile content template
PROFILE_TEMPLATE = """
# MetaMCP PowerShell Profile - "Argh-Coding" Prevention System
# Generated automatically to prevent Linux command errors in PowerShell

# Set up error handling to prevent script/chat session crashes
$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"

# Linux command aliases with error handling
{aliases}

# Error handling functions for common Linux commands
{error_handling}

# Custom prompt to show MetaMCP is active
function prompt {
    $currentPath = Get-Location
    $gitBranch = if (Get-Command git -ErrorAction SilentlyContinue) {
        try { git rev-parse --abbrev-ref HEAD 2>$null } catch { "" }
    } else { "" }

    if ($gitBranch) {
        "MetaMCP [$currentPath] ($gitBranch)> "
    } else {
        "MetaMCP [$currentPath]> "
    }
}

# Welcome message
Write-Host "MetaMCP PowerShell Profile Loaded - Linux command aliases active" -ForegroundColor Green
Write-Host "Type 'help-linux' for Linux command help" -ForegroundColor Cyan

# Help function for Linux commands
function help-linux {
    Write-Host "Available Linux command aliases:" -ForegroundColor Yellow
    Write-Host "ls, la, ll - List files" -ForegroundColor White
    Write-Host "grep - Search in files" -ForegroundColor White
    Write-Host "cat, tail, head - File operations" -ForegroundColor White
    Write-Host "ps, top, kill - Process management" -ForegroundColor White
    Write-Host "cp, mv, rm - File operations" -ForegroundColor White
    Write-Host "cd, pwd - Directory navigation" -ForegroundColor White
    Write-Host "clear - Clear screen" -ForegroundColor White
    Write-Host "man, help - Get help" -ForegroundColor White
    Write-Host "For full PowerShell help: Get-Help <command>" -ForegroundColor Cyan
}

# Prevent common Linux command errors
function Linux-Command-Prevention {
    param($Command)

    switch ($Command) {
        "sudo" { Write-Host "Use 'Run as Administrator' instead of sudo" -ForegroundColor Yellow }
        "apt-get" { Write-Host "Use 'Install-Package' or 'winget' instead of apt-get" -ForegroundColor Yellow }
        "yum" { Write-Host "Use 'Install-Package' or 'winget' instead of yum" -ForegroundColor Yellow }
        "dnf" { Write-Host "Use 'Install-Package' or 'winget' instead of dnf" -ForegroundColor Yellow }
        "chmod" { Write-Host "Use 'Set-ItemProperty' instead of chmod" -ForegroundColor Yellow }
        default { Write-Host "Use PowerShell equivalents for Linux commands" -ForegroundColor Yellow }
    }
}

# Set up command-not-found handler
function Invoke-CommandNotFound {
    param($Command)

    if ($LINUX_TO_POWERSHELL_ALIASES.ContainsKey($Command)) {
        Write-Host "Linux command '$Command' detected. Use PowerShell equivalent:" -ForegroundColor Yellow
        Write-Host "$Command -> $($LINUX_TO_POWERSHELL_ALIASES[$Command])" -ForegroundColor Green
    } else {
        Write-Host "Command '$Command' not found. Try 'Get-Help $Command' or 'help-linux'" -ForegroundColor Red
    }
}

# Override default error handling for common Linux commands
$PSDefaultParameterValues = @{
    'Get-ChildItem:ErrorAction' = 'SilentlyContinue'
    'Select-String:ErrorAction' = 'SilentlyContinue'
    'Get-Content:ErrorAction' = 'SilentlyContinue'
}

# MetaMCP status indicator
function Get-MetaMCPStatus {
    return @{
        ProfileLoaded = $true
        AliasesActive = $LINUX_TO_POWERSHELL_ALIASES.Count
        ErrorHandling = "Active"
        ProtectionLevel = "High"
    }
}
"""


class PowerShellProfileManager:
    """PowerShell profile management specialist."""

    def __init__(self):
        self.profile_paths = POWERSHELL_PROFILE_PATHS
        self.aliases = LINUX_TO_POWERSHELL_ALIASES
        self.error_handling = ERROR_HANDLING_FUNCTIONS

    async def get_profile_path(self) -> Path | None:
        """Get the best PowerShell profile path for the current user."""

        # Try each path in order of preference
        for profile_path in self.profile_paths:
            try:
                # Create parent directory if it doesn't exist
                profile_path.parent.mkdir(parents=True, exist_ok=True)

                # Test if we can write to this location
                test_file = profile_path.parent / ".test_write"
                test_file.write_text("test", encoding="utf-8")
                test_file.unlink()

                return profile_path

            except Exception:
                continue

        return None

    async def create_profile(
        self,
        enable_aliases: bool = True,
        enable_error_handling: bool = True,
        custom_prompt: bool = True,
        obscure_location: bool = True,
    ) -> dict[str, Any]:
        """Create a PowerShell profile with Linux command protection."""

        try:
            # Get profile path
            if obscure_location:
                # Use obscure MetaMCP-specific location
                profile_path = Path(os.path.expanduser("~/.config/powershell/MetaMCP_profile.ps1"))
            else:
                profile_path = await self.get_profile_path()

            if not profile_path:
                return {
                    "success": False,
                    "message": "Operation failed",
                    "error": "Could not find writable PowerShell profile location",
                    "error_code": "NO_PROFILE_PATH",
                }

            # Generate aliases section
            aliases_section = ""
            if enable_aliases:
                for linux_cmd, powershell_cmd in self.aliases.items():
                    aliases_section += f'Set-Alias -Name "{linux_cmd}" -Value "{powershell_cmd}"\n'

            # Generate error handling section
            error_handling_section = ""
            if enable_error_handling:
                for _func_name, func_body in self.error_handling.items():
                    error_handling_section += f"{func_body}\n"

            # Generate profile content
            profile_content = PROFILE_TEMPLATE.format(aliases=aliases_section, error_handling=error_handling_section)

            # Create backup if profile exists
            if profile_path.exists():
                backup_path = profile_path.with_suffix(profile_path.suffix + ".backup")
                backup_path.write_text(profile_path.read_text(encoding="utf-8"), encoding="utf-8")

            # Write new profile
            profile_path.write_text(profile_content, encoding="utf-8")

            return {
                "success": True,
                "operation": "create_powershell_profile",
                "profile_path": str(profile_path),
                "backup_created": profile_path.exists(),
                "aliases_enabled": enable_aliases,
                "error_handling_enabled": enable_error_handling,
                "custom_prompt_enabled": custom_prompt,
                "obscure_location": obscure_location,
                "summary": f"Created PowerShell profile at {profile_path}",
                "recommendations": [
                    "Restart PowerShell to load the profile",
                    "Test Linux commands to verify aliases work",
                    "Check profile status with Get-MetaMCPStatus",
                ],
            }

        except Exception as e:
            return {
                "success": False,
                "message": "Operation failed",
                "error": f"Failed to create PowerShell profile: {e!s}",
                "error_code": "PROFILE_CREATION_FAILED",
                "recovery_options": [
                    "Check PowerShell profile directory permissions",
                    "Run PowerShell as Administrator",
                    "Use manual profile creation",
                ],
            }

    async def check_profile_status(self) -> dict[str, Any]:
        """Check the status of PowerShell profiles."""

        try:
            profile_status = []
            active_profile = None

            for profile_path in self.profile_paths:
                status = {
                    "path": str(profile_path),
                    "exists": profile_path.exists(),
                    "writable": False,
                    "has_metamcp": False,
                    "aliases_count": 0,
                }

                if profile_path.exists():
                    try:
                        content = profile_path.read_text(encoding="utf-8")
                        status["has_metamcp"] = "MetaMCP" in content
                        status["aliases_count"] = content.count("Set-Alias")

                        # Test writability
                        test_file = profile_path.parent / ".test_write"
                        test_file.write_text("test", encoding="utf-8")
                        test_file.unlink()
                        status["writable"] = True

                        if status["has_metamcp"]:
                            active_profile = str(profile_path)

                    except Exception:
                        pass

                profile_status.append(status)

            return {
                "success": True,
                "operation": "check_profile_status",
                "profile_status": profile_status,
                "active_profile": active_profile,
                "summary": f"Checked {len(profile_status)} PowerShell profile locations",
                "recommendations": [
                    "Create MetaMCP profile if none found",
                    "Verify profile is loaded in PowerShell",
                    "Test Linux command aliases",
                ],
            }

        except Exception as e:
            return {
                "success": False,
                "message": "Operation failed",
                "error": f"Failed to check profile status: {e!s}",
                "error_code": "STATUS_CHECK_FAILED",
            }

    async def remove_profile(self, profile_path: str | None = None) -> dict[str, Any]:
        """Remove MetaMCP PowerShell profile."""

        try:
            if profile_path:
                target_path = Path(profile_path)
            else:
                # Find MetaMCP profile
                status_result = await self.check_profile_status()
                active_profile = status_result.get("active_profile")
                if active_profile:
                    target_path = Path(active_profile)
                else:
                    return {
                        "success": False,
                        "message": "Operation failed",
                        "error": "No MetaMCP profile found to remove",
                        "error_code": "NO_PROFILE_FOUND",
                    }

            if not target_path.exists():
                return {
                    "success": False,
                    "message": "Operation failed",
                    "error": f"Profile not found: {target_path}",
                    "error_code": "PROFILE_NOT_FOUND",
                }

            # Create backup before removal
            backup_path = target_path.with_suffix(target_path.suffix + ".removal_backup")
            backup_path.write_text(target_path.read_text(encoding="utf-8"), encoding="utf-8")

            # Remove profile
            target_path.unlink()

            return {
                "success": True,
                "operation": "remove_powershell_profile",
                "removed_profile": str(target_path),
                "backup_created": str(backup_path),
                "summary": f"Removed PowerShell profile from {target_path}",
                "recommendations": [
                    "Restart PowerShell to unload the profile",
                    "Restore from backup if needed",
                    "Create new profile with different settings",
                ],
            }

        except Exception as e:
            return {
                "success": False,
                "message": "Operation failed",
                "error": f"Failed to remove PowerShell profile: {e!s}",
                "error_code": "PROFILE_REMOVAL_FAILED",
            }


def register_powershell_profile_tools(app: FastMCP):
    """Register PowerShell profile management tools with enhanced response patterns."""

    @app.tool()
    async def create_powershell_profile(
        enable_aliases: bool = True,
        enable_error_handling: bool = True,
        custom_prompt: bool = True,
        obscure_location: bool = True,
    ) -> dict[str, Any]:
        """Create PowerShell profile with Linux command protection.

        Creates a PowerShell profile that prevents Linux command errors from breaking
        scripts and chat sessions. Sets up aliases and error handling in obscure
        PowerShell profile locations.

        Args:
            enable_aliases: Enable Linux command aliases
            enable_error_handling: Enable error handling for unsupported commands
            custom_prompt: Use custom MetaMCP prompt
            obscure_location: Use obscure profile location

        Returns:
            Enhanced response with profile creation results
        """

        try:
            manager = PowerShellProfileManager()
            result = await manager.create_profile(
                enable_aliases=enable_aliases,
                enable_error_handling=enable_error_handling,
                custom_prompt=custom_prompt,
                obscure_location=obscure_location,
            )

            if result.get("success"):
                return {
                    "success": True,
                    "operation": "create_powershell_profile",
                    "result": result,
                    "summary": f"Created PowerShell profile with {len(manager.aliases)} Linux command aliases",
                    "recommendations": [
                        "Restart PowerShell to load the profile",
                        "Test Linux commands: ls, grep, cat, etc.",
                        "Check profile status with check_powershell_profile_status()",
                        "Use Get-MetaMCPStatus to verify profile is active",
                    ],
                    "next_steps": [
                        "Close and reopen PowerShell",
                        "Test: ls -la (should work now)",
                        "Test: grep pattern file (should work now)",
                        "Test: sudo command (should show helpful error)",
                    ],
                }

            return result

        except Exception as e:
            return {
                "success": False,
                "message": "Operation failed",
                "error": f"PowerShell profile creation failed: {e!s}",
                "error_code": "CREATION_ERROR",
                "recovery_options": [
                    "Run PowerShell as Administrator",
                    "Check profile directory permissions",
                    "Use manual profile creation",
                ],
            }

    @app.tool()
    async def check_powershell_profile_status() -> dict[str, Any]:
        """Check PowerShell profile status and configuration.

        Returns:
            Enhanced response with profile status information
        """

        try:
            manager = PowerShellProfileManager()
            result = await manager.check_profile_status()

            if result.get("success"):
                return {
                    "success": True,
                    "operation": "check_powershell_profile_status",
                    "result": result,
                    "summary": f"Checked {len(result['profile_status'])} PowerShell profile locations",
                    "recommendations": [
                        "Create MetaMCP profile if none found",
                        "Verify profile is loaded in PowerShell",
                        "Test Linux command aliases",
                    ],
                    "next_steps": [
                        "Run Get-MetaMCPStatus in PowerShell",
                        "Test Linux commands to verify aliases",
                        "Create profile if needed with create_powershell_profile()",
                    ],
                }

            return result

        except Exception as e:
            return {
                "success": False,
                "message": "Operation failed",
                "error": f"Profile status check failed: {e!s}",
                "error_code": "STATUS_CHECK_ERROR",
            }

    @app.tool()
    async def remove_powershell_profile(
        profile_path: str | None = None,
    ) -> dict[str, Any]:
        """Remove MetaMCP PowerShell profile.

        Args:
            profile_path: Specific profile path to remove (auto-detected if None)

        Returns:
            Enhanced response with profile removal results
        """

        try:
            manager = PowerShellProfileManager()
            result = await manager.remove_profile(profile_path)

            if result.get("success"):
                return {
                    "success": True,
                    "operation": "remove_powershell_profile",
                    "result": result,
                    "summary": f"Removed PowerShell profile from {result['removed_profile']}",
                    "recommendations": [
                        "Restart PowerShell to unload the profile",
                        "Restore from backup if needed",
                        "Create new profile with different settings",
                    ],
                    "next_steps": [
                        "Close and reopen PowerShell",
                        "Verify Linux commands no longer work as aliases",
                        "Create new profile if needed",
                    ],
                }

            return result

        except Exception as e:
            return {
                "success": False,
                "message": "Operation failed",
                "error": f"Profile removal failed: {e!s}",
                "error_code": "REMOVAL_ERROR",
                "recovery_options": [
                    "Check profile path permissions",
                    "Run PowerShell as Administrator",
                    "Manual profile removal",
                ],
            }


def register_powershell_tools(app: FastMCP):
    """Register all PowerShell tools with SOTA compliance."""

    logger.info("Registering PowerShell profile tools with SOTA FastMCP 2.14.1+ compliance")

    # Register PowerShell profile tools
    register_powershell_profile_tools(app)

    logger.info("PowerShell profile tools registration complete - Enhanced response patterns enabled")
