"""
PowerShell Syntax Validator Tool - "Argh-Coding" Bloop-Buster

This tool detects and fixes common PowerShell syntax issues that cause LLMs to suggest Linux commands
in PowerShell environments, leading to command failures and developer frustration.
"""

import asyncio
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import structlog
from fastmcp import FastMCP

logger = structlog.get_logger(__name__)

# Common PowerShell syntax errors that LLMs suggest in PowerShell
POWERSHELL_SYNTAX_ERRORS = [
    # Linux commands suggested in PowerShell (REAL PROBLEM!)
    r"ls\s+-la",  # Linux ls command
    r"grep\s+-r",  # Linux grep command (DOESN'T WORK!)
    r"grep\s+.*",  # Linux grep command (DOESN'T WORK!)
    r"chmod\s+\+x",  # Linux chmod command
    r"sudo\s+apt-get",  # Linux package manager
    r"cat\s+.*\.conf",  # Linux file concatenation
    r"tail\s+-f",  # Linux tail command
    r"head\s+-n",  # Linux head command
    r"ssh\s+-c",  # Linux shell command
    r"bash\s+-c",  # Linux bash command
    r"export\s+[A-Z_]+=",  # Linux export command
    r'echo\s+"[^"]*"',  # Linux echo with quotes
    r"find\s+-name",  # Linux find command
    r"du\s+-sh",  # Linux du command
    r"ps\s+aux",  # Linux ps command
    r"kill\s+-9",  # Linux kill command
    r"top\s+-n",  # Linux top command
    r"free\s+-h",  # Linux free command
    r"df\s+-h",  # Linux df command,
    # PowerShell parameter redundancy issues (VERBOSE BUT WORKS!)
    r"Get-ChildItem\s+-Path",  # Verbose -Path parameter (works but unnecessary)
    r"Set-Content\s+-Path",  # Verbose -Path parameter (works but unnecessary)
    r"Test-Path\s+-Path",  # Verbose -Path parameter (works but unnecessary)
    r"New-Item\s+-Type",  # Verbose -Type parameter (works but unnecessary)
    r"Copy-Item\s+-Destination",  # Verbose -Destination parameter (works but unnecessary)
    r"Move-Item\s+-Destination",  # Verbose -Destination parameter (works but unnecessary)
    r"Remove-Item\s+-Path",  # Verbose -Path parameter (works but unnecessary)
    r"Split-Path\s+-Leaf",  # Verbose -Leaf parameter (works but unnecessary)
    # PowerShell cmdlet confusion issues (CONFUSING PATTERNS!)
    r"ConvertTo-SecureString\s+-String",  # Confusing parameter name
    r"ConvertTo-SecureString\s+-Path",  # Wrong parameter for this cmdlet
    r"Out-File\s+-FilePath",  # Should use Set-Content instead
    r"Add-Content\s+-Path",  # Redundant -Path parameter (use positional)
    # PowerShell output confusion (NOT REAL PROBLEMS!)
    # r'Write-Host\s+"[^"]*"',  # This is fine - Write-Host is correct
    # r'Write-Output\s+"[^"]*"',  # This is fine - Write-Output is correct
    # r'Set-Content\s+-Path',  # This is fine - Set-Content is correct
    # r'Test-Path\s+-Path',  # This is fine - Test-Path is correct
    # r'Split-Path\s+.*',  # This is fine - Split-Path is correct
    # r'Join-Path\s+.*',  # This is fine - Join-Path is correct
    # r'Copy-Item\s+-Destination',  # This is fine - Copy-Item is correct
    # r'Move-Item\s+-Destination',  # This is fine - Move-Item is correct
    # r'Remove-Item\s+-Path',  # This is fine - Remove-Item is correct
    # Pipeline and command chaining issues (ADDITIONAL PROBLEM!)
    r"head\s+-n",  # Linux head command
    r"tail\s+-f",  # Linux tail command
    r"&&",  # Linux command chaining operator
    r"ls\s+\|\s+grep",  # Linux pipeline pattern
    r"find\s+\|\s+xargs",  # Linux pipeline pattern
    r"grep\s+\|\s+awk",  # Linux pipeline pattern
    r"cat\s+\|\s+grep",  # Linux pipeline pattern
    r"ps\s+\|\s+grep",  # Linux pipeline pattern
    # Windows-specific gotchas (MICROSOFT ALIASING ISSUES!)
    r"python\s+.*",  # Python alias issue - use python.exe instead
    r"python3\s+.*",  # Python3 alias issue - use python.exe instead
    r"where\s+.*",  # Where alias issue - use Get-Command instead
    # Build script patterns (COMMON BUILD ISSUES!)
    r"New-Item\s+-Type\s+Directory\s+-Force.*;.*cd.*;.*runbuild",  # Empty directory issue
    r"cd\s+builddir\s*&&\s*runbuild",  # Linux-style command chaining
]

# PowerShell equivalents for common Linux commands
POWERSHELL_EQUIVALENTS = {
    r"ls\s+-la": "Get-ChildItem -Force | Format-Table Name, LastWriteTime, Length",
    r"grep\s+-r": "Select-String -Pattern -Recurse",  # Linux grep -r (DOESN'T WORK!)
    r"grep\s+.*": "Select-String -Pattern",  # Linux grep (DOESN'T WORK!)
    r"chmod\s+\+x": "Set-ItemProperty -Path -Name ReadOnly -Value $false",
    r"sudo\s+apt-get": "Install-Package -Name",
    r"cat\s+.*\.conf": "Get-Content -Path",
    r"tail\s+-f": "Get-Content -Path -Tail 10",
    r"head\s+-n": "Get-Content -Path -TotalCount 10",
    r"sh\s+-c": "Invoke-Expression",
    r"bash\s+-c": "pwsh -Command",
    r"export\s+[A-Z_]+=": "Set-Item -Path -Name ReadOnly -Value",
    r'echo\s+"[^"]*"': 'Write-Host "message"',
    r"find\s+-name": "Get-ChildItem -Recurse -File",
    r"du\s+-sh": "Get-ChildItem -Recurse -File | Measure-Object Length | Sort-Object Length -Descending | Select-Object -First 10",
    r"ps\s+aux": "Get-Process | Format-Table Name, CPU, Id, StartTime, Memory",
    r"kill\s+-9": "Stop-Process -Id",
    r"top\s+-n": "Get-Process | Sort-Object CPU -Descending | Select-Object -First 10",
    r"free\s+-h": "Get-Process | Measure-Object WorkingSet | Sort-Object WorkingSet -Descending | Select-Object -First 10",
    r"df\s+-h": "Get-Volume | Format-Table Name, Size, Used, Free",
    r"&&": ";",  # Use semicolon for command chaining
    # Windows-specific Python alias fixes (MICROSOFT ALIASING ISSUES!)
    r"python\s+.*": "python.exe",  # Use python.exe instead of python alias
    r"python3\s+.*": "python.exe",  # Use python.exe instead of python3 alias
    r"where\s+.*": "Get-Command",  # Use Get-Command instead of where alias
    # Build script pattern fixes (COMMON BUILD ISSUES!)
    r"New-Item\s+-Type\s+Directory\s+-Force.*;.*cd.*;.*runbuild": (
        "New-Item -Type Directory -Force builddir; "
        'Set-Content builddir\\README.md "Build directory"; cd builddir; runbuild'
    ),  # Fix empty directory issue
    r"cd\s+builddir\s*&&\s*runbuild": (
        "if (Test-Path builddir) { cd builddir; runbuild } "
        'else { Write-Host "Build directory not found" -ForegroundColor Red }'
    ),  # Fix Linux-style chaining
}

# PowerShell-specific syntax issues
POWERSHELL_SYNTAX_ISSUES = [
    r"Get-ChildItem\s+-Path",  # Missing -Path parameter
    r"Set-Content\s+-Path",  # Missing -Path parameter
    r"Test-Path\s+-Path",  # Missing -Path parameter
    r"New-Item\s+-Type",  # Missing -Type parameter
    r"Copy-Item\s+-Destination",  # Missing -Destination parameter
    r"Move-Item\s+-Destination",  # Missing -Destination parameter
    r"Remove-Item\s+-Path",  # Missing -Path parameter
    r"Test-Path\s+-Path",  # Missing -Path parameter
    r"Split-Path\s+-Leaf",  # Missing -Leaf parameter
    r"Join-Path\s+.*",  # Incorrect path joining
    r"ConvertTo-SecureString\s+-String",  # Unnecessary parameter
    r"ConvertTo-SecureString\s+-Path",  # Unnecessary parameter
    r'Write-Host\s+"[^"]*"',  # Use Write-Host instead
    r'Write-Output\s+"[^"]*"',  # Use Write-Output instead
    r"Out-File\s+-FilePath",  # Use Set-Content instead
    r"Add-Content\s+-Path",  # Use Set-Content instead
    r"Set-Content\s+-Path",  # Use Set-Content instead
]

# PowerShell cmdlet usage patterns (NATIVE POWERSHELL BEST PRACTICE!)
POWERSHELL_CMDLET_PATTERNS = [
    # Use native cmdlets instead of command-line patterns
    r"mkdir\s+-p\s+.*",  # Linux mkdir -p pattern
    r"rm\s+-rf\s+.*",  # Linux rm -rf pattern
    r"cp\s+-r\s+.*",  # Linux cp -r pattern
    r"mv\s+.*",  # Linux mv pattern
    r"touch\s+.*",  # Linux touch pattern
    r"chmod\s+.*",  # Linux chmod pattern
    r"chown\s+.*",  # Linux chown pattern
    r"find\s+.*",  # Linux find pattern
    r"xargs\s+.*",  # Linux xargs pattern
    r"awk\s+.*",  # Linux awk pattern
    r"sed\s+.*",  # Linux sed pattern
    r"sort\s+.*",  # Linux sort pattern
    r"uniq\s+.*",  # Linux uniq pattern
    r"wc\s+-l\s+.*",  # Linux wc -l pattern
    r"tar\s+.*",  # Linux tar pattern
    r"zip\s+.*",  # Linux zip pattern
    r"unzip\s+.*",  # Linux unzip pattern
    r"ssh\s+.*",  # Linux ssh pattern
    r"scp\s+.*",  # Linux scp pattern
    r"rsync\s+.*",  # Linux rsync pattern
]

# Safe PowerShell alternatives for common operations
SAFE_POWERSHELL_PATTERNS = {
    # Linux commands (REAL PROBLEM!)
    r"ls\s+-la": "Get-ChildItem -Force | Format-Table Name, LastWriteTime, Length",
    r"grep\s+-r": "Select-String -Pattern",
    r"chmod\s+\+x": "Set-ItemProperty -Path -Name ReadOnly -Value $false",
    r"sudo\s+apt-get": "Install-Package -Name",
    r"cat\s+.*\.conf": "Get-Content -Path",
    r"tail\s+-f": "Get-Content -Path -Tail 10",
    r"head\s+-n": "Get-Content -Path -TotalCount 10",
    r"wget\s+https?://": "Invoke-WebRequest -Uri",
    r"curl\s+https?://": "Invoke-WebRequest -Uri",
    r"ssh\s+-c": "Invoke-Expression",
    r"bash\s+-c": "pwsh -Command",
    r"export\s+[A-Z_]+=": "Set-Item -Path -Name ReadOnly -Value",
    r'echo\s+"[^"]*"': 'Write-Host "message"',
    r"find\s+-name": "Get-ChildItem -Recurse -File",
    r"du\s+-sh": (
        "Get-ChildItem -Recurse -File | Measure-Object Length | "
        "Sort-Object Length -Descending | Select-Object -First 10"
    ),
    r"ps\s+aux": "Get-Process | Format-Table Name, CPU, Id, StartTime, Memory",
    r"kill\s+-9": "Stop-Process -Id",
    r"top\s+-n": "Get-Process | Sort-Object CPU -Descending | Select-Object -First 10",
    r"free\s+-h": (
        "Get-Process | Measure-Object WorkingSet | Sort-Object WorkingSet -Descending | Select-Object -First 10"
    ),
    r"df\s+-h": "Get-Volume | Format-Table Name, Size, Used, Free",
    # PowerShell parameter redundancy fixes (ADDITIONAL PROBLEM!)
    r"Get-ChildItem\s+-Path": "Get-ChildItem",
    r"Set-Content\s+-Path": "Set-Content",
    r"Test-Path\s+-Path": "Test-Path",
    r"Split-Path\s+.*": "Split-Path",
    r"Join-Path\s+.*": "Join-Path",
    r"Copy-Item\s+-Destination": "Copy-Item",
    r"Move-Item\s+-Destination": "Move-Item",
    r"Remove-Item\s+-Path": "Remove-Item",
    r"New-Item\s+-Type": "New-Item",
    r'Write-Host\s+"[^"]*"': "Write-Host",
    r'Write-Output\s+"[^"]*"': "Write-Output",
    r"Out-File\s+-FilePath": "Set-Content",
    r"Add-Content\s+-Path": "Add-Content",
    r"ConvertTo-SecureString\s+-String": "ConvertTo-SecureString",
    r"ConvertTo-SecureString\s+-Path": "ConvertTo-SecureString",
    # Native PowerShell cmdlet patterns (NATIVE POWERSHELL BEST PRACTICE!)
    r"mkdir\s+-p": "New-Item -Type Directory -Force",  # Native mkdir -p
    r"rm\s+-rf": "Remove-Item -Recurse -Force",  # Native rm -rf
    r"cp\s+-r": "Copy-Item -Recurse -Force",  # Native cp -r
    r"mv\s+.*": "Move-Item -Force",  # Native mv
    r"touch\s+.*": "New-Item -Type File",  # Native touch
    r"chmod\s+.*": "Set-ItemProperty -Path",  # Native chmod
    r"find\s+.*": "Get-ChildItem -Recurse",  # Native find
    r"xargs\s+.*": "ForEach-Object",  # Native xargs
    r"awk\s+.*": "Select-String",  # Native awk
    r"sed\s+.*": "ForEach-Object",  # Native sed
    r"sort\s+.*": "Sort-Object",  # Native sort
    r"uniq\s+.*": "Sort-Object -Unique",  # Native uniq
    r"wc\s+-l\s+.*": "Get-Content | Measure-Object Line",  # Native wc -l
    r"tar\s+.*": "Compress-Archive",  # Native tar
    r"zip\s+.*": "Compress-Archive",  # Native zip
    r"unzip\s+.*": "Expand-Archive",  # Native unzip
    r"ssh\s+.*": "Enter-PSSession",  # Native ssh
    r"scp\s+.*": "Copy-Item -ToSession",  # Native scp
    r"rsync\s+.*": "Copy-Item -Recurse",  # Native rsync
}


class PowerShellSyntaxValidator:
    """PowerShell syntax validation and correction specialist."""

    def __init__(self):
        self.scan_cache = {}
        self.success_stories = []

    async def scan_repository(self, repo_path: str, scan_mode: str = "comprehensive") -> dict[str, Any]:
        """Scan a repository for PowerShell syntax issues."""

        repo_path = Path(repo_path)
        if not repo_path.exists():
            return {
                "success": False,
                "message": "Operation failed",
                "error": f"Repository path does not exist: {repo_path}",
                "error_code": "REPO_NOT_FOUND",
            }

        # Find all PowerShell files
        ps1_files = list(repo_path.rglob("*.ps1"))
        psd_files = list(repo_path.rglob("*.psd"))
        powershell_files = ps1_files + psd_files

        total_files = len(powershell_files)
        syntax_issues = []
        files_with_issues = 0

        for file_path in powershell_files:
            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()
                    lines = content.split("\n")

                file_issues = []
                for line_num, line in enumerate(lines, 1):
                    # Check for Linux command patterns
                    for pattern in POWERSHELL_SYNTAX_ERRORS:
                        matches = re.finditer(pattern, line, re.IGNORECASE)
                        for match in matches:
                            # Determine issue type
                            if any(
                                linux_cmd in match.group()
                                for linux_cmd in [
                                    "ls",
                                    "grep",
                                    "chmod",
                                    "sudo",
                                    "cat",
                                    "tail",
                                    "head",
                                    "wget",
                                    "curl",
                                    "ssh",
                                    "bash",
                                    "export",
                                    "echo",
                                    "find",
                                    "du",
                                    "ps",
                                    "kill",
                                    "top",
                                    "free",
                                    "df",
                                ]
                            ):
                                issue_type = "linux_command_in_powershell"
                            elif any(python_cmd in match.group() for python_cmd in ["python", "python3", "where"]):
                                issue_type = "python_alias_issue"
                            elif "&&" in match.group():
                                issue_type = "command_chaining_issue"
                            else:
                                issue_type = "powershell_parameter_redundancy"

                            file_issues.append(
                                {
                                    "line_number": line_num,
                                    "issue_type": issue_type,
                                    "problematic_match": match.group(),
                                    "suggested_fix": SAFE_POWERSHELL_PATTERNS.get(match.group(), match.group()),
                                }
                            )

                    # Check for PowerShell cmdlet usage patterns (NATIVE POWERSHELL BEST PRACTICE!)
                    for pattern in POWERSHELL_CMDLET_PATTERNS:
                        matches = re.finditer(pattern, line, re.IGNORECASE)
                        for match in matches:
                            file_issues.append(
                                {
                                    "line_number": line_num,
                                    "issue_type": "cmdlet_usage_pattern",
                                    "problematic_match": match.group(),
                                    "suggested_fix": "Use native PowerShell cmdlets instead",
                                }
                            )

                    if file_issues:
                        files_with_issues += 1
                        syntax_issues.append(
                            {
                                "file": str(file_path.relative_to(repo_path)),
                                "issues": file_issues,
                                "issue_count": len(file_issues),
                            }
                        )

            except Exception as e:
                syntax_issues.append(
                    {
                        "file": str(file_path.relative_to(repo_path)),
                        "error": f"Failed to scan file: {e!s}",
                        "issue_count": 0,
                    }
                )

        return {
            "success": True,
            "repository": str(repo_path),
            "scan_mode": scan_mode,
            "total_files": total_files,
            "files_with_issues": files_with_issues,
            "total_syntax_issues": len(syntax_issues),
            "syntax_issues": syntax_issues,
            "crash_risk": "HIGH" if files_with_issues > 0 else "LOW",
        }

    async def fix_powershell_syntax(self, repo_path: str, backup: bool = True) -> dict[str, Any]:
        """Fix PowerShell syntax issues in a repository."""

        scan_result = await self.scan_repository(repo_path)

        if not scan_result.get("success"):
            return scan_result

        if scan_result.get("total_syntax_issues", 0) == 0:
            return {
                "success": True,
                "message": "No PowerShell syntax issues found",
                "repository": repo_path,
                "issues_fixed": 0,
            }

        repo_path = Path(repo_path)
        fixed_files = 0
        total_fixes = 0

        for issue in scan_result["syntax_issues"]:
            if "error" in issue:
                continue

            file_path = repo_path / issue["file"]

            # Create backup if requested
            if backup:
                backup_path = file_path.with_suffix(file_path.suffix + ".backup")
                backup_path.write_text(file_path.read_text(encoding="utf-8"), encoding="utf-8")

            # Fix the file
            try:
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()

                original_content = content
                fixed_content = content

                # Fix each issue
                for issue_info in issue["issues"]:
                    problematic_match = issue_info["problematic_match"]
                    suggested_fix = issue_info["suggested_fix"]

                    if suggested_fix:
                        fixed_content = fixed_content.replace(problematic_match, suggested_fix)

                # Only write if content changed
                if fixed_content != original_content:
                    file_path.write_text(fixed_content, encoding="utf-8")
                    fixed_files += 1
                    total_fixes += len(issue["issues"])

            except Exception as e:
                return {
                    "success": False,
                    "message": "Operation failed",
                    "error": f"Failed to fix file {issue['file']}: {e!s}",
                    "error_code": "FIX_FAILED",
                }

        # Add to success stories
        success_story = {
            "repository": str(repo_path),
            "timestamp": asyncio.get_event_loop().time(),
            "issues_fixed": total_fixes,
            "files_fixed": fixed_files,
            "stability_improved": True,
        }
        self.success_stories.append(success_story)

        return {
            "success": True,
            "operation": "powershell_syntax_fix",
            "repository": str(repo_path),
            "files_fixed": fixed_files,
            "total_fixes": total_fixes,
            "backup_created": backup,
            "success_story": success_story,
        }

    async def get_powershell_equivalents(self, linux_command: str) -> dict[str, Any]:
        """Get PowerShell equivalents for Linux commands."""

        if linux_command in POWERSHELL_EQUIVALENTS:
            return {
                "success": True,
                "linux_command": linux_command,
                "powershell_equivalent": POWERSHELL_EQUIVALENTS[linux_command],
                "description": f"PowerShell equivalent for: {linux_command}",
            }
        else:
            return {
                "success": False,
                "message": "Operation failed",
                "error": f"No PowerShell equivalent found for: {linux_command}",
                "error_code": "NO_EQUIVALENT",
                "suggestions": [
                    "Check POWERSHELL_EQUIVALENTS for available equivalents",
                    "Use Get-ChildItem, Get-Content, or other PowerShell cmdlets",
                ],
            }

    async def validate_powershell_syntax(self, powershell_command: str) -> dict[str, Any]:
        """Validate a PowerShell command for syntax correctness."""

        try:
            # Try to parse the command
            pwsh_path = shutil.which("powershell") or shutil.which("pwsh") or "powershell"
            result = subprocess.run(
                [pwsh_path, "-Command", "Get-Command", powershell_command],
                capture_output=True,
                text=True,
                stderr=True,
                timeout=10,
            )

            if result.returncode == 0:
                return {
                    "success": True,
                    "command": powershell_command,
                    "valid": True,
                    "description": "PowerShell command is valid",
                }
            else:
                return {
                    "success": False,
                    "message": "Operation failed",
                    "error": f"Invalid PowerShell command: {powershell_command}",
                    "error_code": "INVALID_SYNTAX",
                    "stderr": result.stderr,
                    "suggestions": [
                        "Check PowerShell syntax",
                        "Use Get-Command to validate command exists",
                        "Use proper PowerShell cmdlets",
                    ],
                }

        except Exception as e:
            return {
                "success": False,
                "message": "Operation failed",
                "error": f"Failed to validate command: {e!s}",
                "error_code": "VALIDATION_FAILED",
                "suggestions": [
                    "Check command spelling",
                    "Verify PowerShell installation",
                    "Use Get-Command to check if command exists",
                ],
            }


def register_powershell_tools(app: FastMCP):
    """Register PowerShell syntax validation tools with enhanced response patterns."""

    @app.tool()
    async def validate_powershell_syntax(repo_path: str, scan_mode: str = "comprehensive") -> dict[str, Any]:
        """Validate PowerShell syntax in repository with enhanced response patterns.

        Args:
            repo_path: Repository path to scan
            scan_mode: Scan intensity level ("quick" or "comprehensive")

        Returns:
            Enhanced response with validation results and fix recommendations
        """

        try:
            validator = PowerShellSyntaxValidator()
            result = await validator.scan_repository(repo_path, scan_mode)

            if result.get("success"):
                result.update(
                    {
                        "operation": "validate_powershell_syntax",
                        "summary": f"Scanned {result['total_files']} PowerShell files, "
                        f"found {result['total_syntax_issues']} syntax issues",
                        "recommendations": [
                            "Use fix_powershell_syntax() to automatically fix issues",
                            "Review PowerShell syntax before committing",
                            "Use Get-Command to validate command existence",
                        ],
                    }
                )

            return result

        except Exception as e:
            return {
                "success": False,
                "message": "Operation failed",
                "error": f"PowerShell validation failed: {e!s}",
                "error_code": "VALIDATION_ERROR",
                "recovery_options": [
                    "Check repository path permissions",
                    "Verify PowerShell installation",
                    "Use validate_powershell_syntax() with specific file paths",
                ],
            }

    @app.tool()
    async def fix_powershell_syntax(repo_path: str, auto_fix: bool = False, backup: bool = True) -> dict[str, Any]:
        """Fix PowerShell syntax issues with enhanced response patterns.

        Args:
            repo_path: Repository path to fix
            auto_fix: Whether to automatically fix issues (requires confirmation)
            backup: Whether to create backups before fixing

        Returns:
            Enhanced response with fix results and stability improvements
        """

        if not auto_fix:
            return {
                "success": False,
                "message": "Operation failed",
                "error": "Auto-fix not enabled. Set auto_fix=True to proceed.",
                "error_code": "AUTO_FIX_REQUIRED",
                "recovery_options": [
                    "Set auto_fix=True to automatically fix issues",
                    "Manually review and fix each issue",
                    "Use validate_powershell_syntax() to see specific issues first",
                ],
                "warning": "Auto-fix will replace problematic PowerShell syntax with safe equivalents",
            }

        try:
            validator = PowerShellSyntaxValidator()
            result = await validator.fix_powershell_syntax(repo_path, backup)

            if result.get("success"):
                return {
                    "success": True,
                    "operation": "fix_powershell_syntax",
                    "result": result,
                    "summary": f"Fixed {result['files_fixed']} PowerShell files with syntax issues",
                    "recommendations": [
                        "Test fixed scripts before deployment",
                        "Add PowerShell syntax validation to CI/CD pipeline",
                        "Educate team on PowerShell vs Linux command differences",
                    ],
                    "next_steps": [
                        f"Test fixed scripts: {result['files_fixed']} files",
                        "Monitor for new syntax issues",
                        "Validate with validate_powershell_syntax() again",
                    ],
                }

            return result

        except Exception as e:
            return {
                "success": False,
                "message": "Operation failed",
                "error": f"PowerShell fix failed: {e!s}",
                "error_code": "FIX_FAILED",
                "recovery_options": [
                    "Check file permissions",
                    "Manual review and fix issues",
                    "Use validate_powershell_syntax() for specific guidance",
                ],
            }

    @app.tool()
    async def get_powershell_equivalents(linux_command: str) -> dict[str, Any]:
        """Get PowerShell equivalents for Linux commands with enhanced response patterns.

        Args:
            linux_command: Linux command to find PowerShell equivalent for

        Returns:
            Enhanced response with command mapping and usage guidance
        """

        try:
            validator = PowerShellSyntaxValidator()
            result = await validator.get_powershell_equivalents(linux_command)

            if result.get("success"):
                return {
                    "success": True,
                    "operation": "get_powershell_equivalents",
                    "result": result,
                    "summary": f"PowerShell equivalent for: {linux_command}",
                    "recommendations": [
                        "Use PowerShell equivalents for better Windows compatibility",
                        "Learn PowerShell-specific cmdlets for enhanced functionality",
                        "Test commands before deployment",
                    ],
                }

            return result

        except Exception as e:
            return {
                "success": False,
                "message": "Operation failed",
                "error": f"Failed to get PowerShell equivalents: {e!s}",
                "error_code": "EQUIVALENT_NOT_FOUND",
                "recovery_options": [
                    "Check command spelling",
                    "Use validate_powershell_equivalents() for available commands",
                    "Learn PowerShell cmdlets and native commands",
                ],
            }

    logger.info("PowerShell tools registration complete - Enhanced response patterns enabled")
    return 2  # Return count of registered tools


def register_all_meta_tools(app: FastMCP):
    """Register all MetaMCP tools with SOTA compliance."""

    logger.info("Registering PowerShell tools with SOTA FastMCP 2.14.1+ compliance")

    # Register PowerShell tools
    register_powershell_tools(app)

    logger.info("PowerShell tools registration complete - Enhanced response patterns enabled")
