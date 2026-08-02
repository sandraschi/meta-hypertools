"""
EmojiBuster Service - Unicode Logging Crash Prevention and Recovery logic.
"""

import re
from pathlib import Path
from typing import Any

import structlog

from meta_mcp.services.base import MetaMCPService

logger = structlog.get_logger(__name__)

# Unsafe Unicode patterns that cause logging crashes (using escape sequences)
UNSAFE_UNICODE_PATTERNS = [
    # Explicitly targeted high-frequency "crasher" emojis (using hex escapes)
    r"logger\.[a-z_]+\([^)]*[\U0001F680\u26A0\u274C\u2705\U0001F50D\U0001F389\U0001F3C6\U0001F600\U0001F602\U0001F60D\U0001F3AD\U0001F60E]",
    r"print\([^)]*[\U0001F680\u26A0\u274C\u2705\U0001F50D\U0001F389\U0001F3C6\U0001F600\U0001F602\U0001F60D\U0001F3AD\U0001F60E]",
    # General ranges
    r"logger\.[a-z_]+\([^)]*[\U0001F600-\U0001F64F]",  # Emoticons
    r"print\([^)]*[\U0001F600-\U0001F64F]",  # Emoticons in print
    r"logger\.[a-z_]+\([^)]*[\U0001F300-\U0001F5FF]",  # Misc Symbols
    r"print\([^)]*[\U0001F300-\U0001F5FF]",  # Misc Symbols in print
    r"logger\.[a-z_]+\([^)]*[\U0001F680-\U0001F6FF]",  # Transport & Map
    r"print\([^)]*[\U0001F680-\U0001F6FF]",  # Transport & Map in print
    r"logger\.[a-z_]+\([^)]*[\U0001F700-\U0001F77F]",  # Alchemical
    r"print\([^)]*[\U0001F700-\U0001F77F]",  # Alchemical in print
    r"logger\.[a-z_]+\([^)]*[\U0001F780-\U0001F7FF]",  # Geometric
    r"print\([^)]*[\U0001F780-\U0001F7FF]",  # Geometric in print
    r"logger\.[a-z_]+\([^)]*[\U0001F800-\U0001F8FF]",  # Supplemental
    r"print\([^)]*[\U0001F800-\U0001F8FF]",  # Supplemental in print
    r"logger\.[a-z_]+\([^)]*[\U0001F900-\U0001F9FF]",  # Symbols & Pictographs
    r"print\([^)]*[\U0001F900-\U0001F9FF]",  # Symbols & Pictographs in print
    r"logger\.[a-z_]+\([^)]*[\U0001FA00-\U0001FA6F]",  # Chess
    r"print\([^)]*[\U0001FA00-\U0001FA6F]",  # Chess in print
    # Catch-all for ANY non-ASCII in logger/print calls (the ultimate safety)
    r"logger\.[a-z_]+\([^)]*[^\x00-\x7F]",
    r"print\([^)]*[^\x00-\x7F]",
    # Typographic characters that break PowerShell/justfile parsing
    r"[\u2013\u2014\u2018\u2019\u201c\u201d\u2026]",
]

# Safe ASCII replacements (using hex escapes for keys)
UNICODE_REPLACEMENTS = {
    "\U0001f680": "Process",  # Rocket
    "\u26a0": "WARNING",  # Warning sign
    "\u274c": "ERROR",  # Cross mark
    "\u2705": "SUCCESS",  # Check mark
    "\U0001f50d": "DEBUG",  # Search
    "\U0001f389": "Celebration",  # Party popper
    "\U0001f3c6": "Achievement",  # Trophy
    "\U0001f600": "Happy",  # Grinning face
    "\U0001f602": "Laughing",  # Tears of joy
    "\U0001f60d": "Love",  # Heart eyes
    "\U0001f3ad": "Mask",  # Performing arts
    "\U0001f60e": "Cool",  # Sunglasses
    "\U0001f4dd": "Document",  # Memo
    "\U0001f4ca": "Chart",  # Bar chart
    "\U0001f527": "Tools",  # Wrench
    "\U0001f4a1": "Idea",  # Light bulb
    "\U0001f3af": "Target",  # Bulls eye
    "\u2b50": "Star",  # Star
    "\U0001f517": "Link",  # Link
    "\U0001f4c1": "Folder",  # Open folder
    "\U0001f512": "Lock",  # Lock
    "\U0001f310": "Global",  # Globe
    "\U0001f4f1": "Mobile",  # Mobile phone
    "\U0001f4bb": "Computer",  # Laptop
    "\U0001f6a6": "Start",  # Traffic light
    "\u23f8": "Stop",  # Pause button
    "\U0001f504": "Refresh",  # Counter-clockwise arrows
    "\u2b06": "Up",  # Up arrow
    "\u2b07": "Down",  # Down arrow
    "\u2728": "Magic",  # Sparkles
    "\U0001f3a8": "Design",  # Palette
    "\U0001f308": "Rainbow",  # Rainbow
    "\U0001f31f": "Sun",  # Glowing star
    "\U0001f319": "Moon",  # Crescent moon
    "\u26a1": "Bolt",  # High voltage
    "\U0001f525": "Fire",  # Fire
    "\U0001f4a7": "Water",  # Droplet
    "\U0001f30a": "Wave",  # Water wave
    "\u2013": "-",  # En dash
    "\u2014": " - ",  # Em dash
    "\u2018": "'",  # Left single quote
    "\u2019": "'",  # Right single quote
    "\u201c": '"',  # Left double quote
    "\u201d": '"',  # Right double quote
    "\u2026": "...",  # Ellipsis
}


class EmojiBuster(MetaMCPService):
    """Unicode logging crash prevention specialist."""

    def __init__(self):
        super().__init__()
        self.success_stories = []

    async def scan_repository(self, repo_path: str, scan_mode: str = "comprehensive") -> dict[str, Any]:
        """Scan a repository for Unicode logging issues."""
        repo_path = Path(repo_path)
        if not repo_path.exists():
            return self.create_response(False, f"Repository path does not exist: {repo_path}")

        python_files = list(repo_path.rglob("*.py"))
        unicode_issues = []
        files_with_unicode = 0

        for file_path in python_files:
            try:
                # Basic scan for demonstration - logic ported from tools/emojibuster.py
                with open(file_path, encoding="utf-8") as f:
                    content = f.read()
                    lines = content.split("\n")

                file_issues = []
                for line_num, line in enumerate(lines, 1):
                    for match in re.finditer(r"[^\x00-\x7F]", line):
                        file_issues.append(
                            {
                                "line_number": line_num,
                                "line_content": line.strip(),
                                "unsafe_match": match.group(),
                                "hex_match": hex(ord(match.group())),
                                "risk_level": "critical"
                                if re.search(r"(logger\.[a-z_]+|print)\s*\(", line)
                                else "advisory",
                            }
                        )

                if file_issues:
                    files_with_unicode += 1
                    unicode_issues.append(
                        {
                            "file": str(file_path.relative_to(repo_path)),
                            "issues": file_issues,
                            "issue_count": len(file_issues),
                        }
                    )
            except Exception as e:
                self.logger.error(f"Failed to scan file {file_path}: {e}")

        return self.create_response(
            True,
            "Scan completed",
            {
                "repository": str(repo_path),
                "scan_mode": scan_mode,
                "total_files": len(python_files),
                "files_with_unicode": files_with_unicode,
                "total_unicode_issues": len(unicode_issues),
                "unicode_issues": unicode_issues,
                "crash_risk": "HIGH" if files_with_unicode > 0 else "LOW",
            },
        )

    async def fix_unicode_logging(self, repo_path: str, backup: bool = True) -> dict[str, Any]:
        """Fix Unicode logging issues in a repository."""
        scan_response = await self.scan_repository(repo_path)
        if not scan_response["success"]:
            return scan_response

        data = scan_response["data"]
        if data["total_unicode_issues"] == 0:
            return self.create_response(True, "No Unicode logging issues found", {"issues_fixed": 0})

        repo_path_obj = Path(repo_path)
        fixed_files = 0
        total_fixes = 0

        for issue in data["unicode_issues"]:
            file_path = repo_path_obj / issue["file"]
            if backup:
                backup_path = file_path.with_suffix(file_path.suffix + ".backup")
                backup_path.write_text(file_path.read_text(encoding="utf-8"), encoding="utf-8")

            try:
                content = file_path.read_text(encoding="utf-8")
                original_content = content
                for unicode_char, replacement in UNICODE_REPLACEMENTS.items():
                    content = content.replace(unicode_char, replacement)
                content = re.sub(r"[^\x00-\x7F]+", "", content)

                if content != original_content:
                    file_path.write_text(content, encoding="utf-8")
                    fixed_files += 1
                    total_fixes += issue["issue_count"]
            except Exception as e:
                return self.create_response(False, f"Failed to fix file {issue['file']}: {e}")

        return self.create_response(
            True,
            "Fixes applied successfully",
            {
                "repository": repo_path,
                "files_fixed": fixed_files,
                "total_fixes": total_fixes,
                "backup_created": backup,
            },
        )
