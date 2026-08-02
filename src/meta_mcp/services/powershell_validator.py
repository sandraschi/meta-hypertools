"""
PowerShell Syntax Validator Service - "Argh-Coding" Bloop-Buster logic.
"""

import re
from pathlib import Path
from typing import Any

from meta_mcp.services.base import MetaMCPService

# Logic ported from tools/powershell_validator.py
POWERSHELL_SYNTAX_ERRORS = [
    r"ls\s+-la",
    r"grep\s+-r",
    r"grep\s+.*",
    r"chmod\s+\+x",
    r"sudo\s+apt-get",
    r"cat\s+.*\.conf",
    r"tail\s+-f",
    r"head\s+-n",
    r"ssh\s+-c",
    r"bash\s+-c",
    r"export\s+[A-Z_]+=",
    r'echo\s+"[^"]*"',
    r"find\s+-name",
    r"du\s+-sh",
    r"ps\s+aux",
    r"kill\s+-9",
    r"top\s+-n",
    r"free\s+-h",
    r"df\s+-h",
    r"&&",
]

SAFE_POWERSHELL_PATTERNS = {
    r"ls\s+-la": "Get-ChildItem -Force | Format-Table Name, LastWriteTime, Length",
    r"grep\s+-r": "Select-String -Pattern",
    r"chmod\s+\+x": "Set-ItemProperty -Path -Name ReadOnly -Value $false",
    r"sudo\s+apt-get": "Install-Package -Name",
    r"cat\s+.*\.conf": "Get-Content -Path",
    r"tail\s+-f": "Get-Content -Path -Tail 10",
    r"head\s+-n": "Get-Content -Path -TotalCount 10",
    r"&&": ";",
}


class PowerShellSyntaxValidator(MetaMCPService):
    """PowerShell syntax validation and correction specialist."""

    async def scan_repository(self, repo_path: str, scan_mode: str = "comprehensive") -> dict[str, Any]:
        """Scan a repository for PowerShell syntax issues."""
        repo_path_obj = Path(repo_path)
        if not repo_path_obj.exists():
            return self.create_response(False, f"Repository path does not exist: {repo_path}")

        ps_files = list(repo_path_obj.rglob("*.ps1")) + list(repo_path_obj.rglob("*.psd"))
        syntax_issues = []
        files_with_issues = 0

        for file_path in ps_files:
            try:
                content = file_path.read_text(encoding="utf-8")
                lines = content.split("\n")
                file_issues = []
                for line_num, line in enumerate(lines, 1):
                    for pattern in POWERSHELL_SYNTAX_ERRORS:
                        if re.search(pattern, line, re.IGNORECASE):
                            file_issues.append(
                                {
                                    "line_number": line_num,
                                    "problematic_match": pattern,
                                    "suggested_fix": SAFE_POWERSHELL_PATTERNS.get(pattern, "Check PowerShell syntax"),
                                }
                            )
                if file_issues:
                    files_with_issues += 1
                    syntax_issues.append(
                        {
                            "file": str(file_path.relative_to(repo_path_obj)),
                            "issues": file_issues,
                            "issue_count": len(file_issues),
                        }
                    )
            except Exception as e:
                self.logger.error(f"Failed to scan {file_path}: {e}")

        return self.create_response(
            True,
            "PowerShell scan completed",
            {
                "repository": repo_path,
                "total_files": len(ps_files),
                "files_with_issues": files_with_issues,
                "total_syntax_issues": len(syntax_issues),
                "syntax_issues": syntax_issues,
            },
        )

    async def fix_powershell_syntax(self, repo_path: str, backup: bool = True) -> dict[str, Any]:
        """Fix PowerShell syntax issues in a repository."""
        scan_response = await self.scan_repository(repo_path)
        if not scan_response["success"]:
            return scan_response

        data = scan_response["data"]
        repo_path_obj = Path(repo_path)
        fixed_files = 0
        total_fixes = 0

        for issue in data["syntax_issues"]:
            file_path = repo_path_obj / issue["file"]
            if backup:
                backup_path = file_path.with_suffix(file_path.suffix + ".backup")
                backup_path.write_text(file_path.read_text(encoding="utf-8"), encoding="utf-8")

            try:
                content = file_path.read_text(encoding="utf-8")
                original_content = content
                for issue_info in issue["issues"]:
                    pattern = issue_info["problematic_match"]
                    fix = issue_info["suggested_fix"]
                    content = re.sub(pattern, fix, content, flags=re.IGNORECASE)

                if content != original_content:
                    file_path.write_text(content, encoding="utf-8")
                    fixed_files += 1
                    total_fixes += issue["issue_count"]
            except Exception as e:
                return self.create_response(False, f"Failed to fix {issue['file']}: {e}")

        return self.create_response(
            True,
            "PowerShell fixes applied",
            {
                "repository": repo_path,
                "files_fixed": fixed_files,
                "total_fixes": total_fixes,
            },
        )
