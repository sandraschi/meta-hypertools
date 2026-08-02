"""
PowerShell Profile Manager Service logic.
"""

import os
from pathlib import Path
from typing import Any

from meta_mcp.services.base import MetaMCPService


class PowerShellProfileManager(MetaMCPService):
    """PowerShell profile management specialist."""

    def __init__(self):
        super().__init__()
        self.profile_paths = [
            Path(os.path.expanduser("~/Documents/PowerShell/Microsoft.PowerShell_profile.ps1")),
            Path(os.path.expanduser("~/.config/powershell/MetaMCP_profile.ps1")),
        ]

    async def create_profile(
        self,
        enable_aliases: bool = True,
        enable_error_handling: bool = True,
        obscure_location: bool = True,
    ) -> dict[str, Any]:
        """Create a PowerShell profile with Linux command protection."""
        try:
            if obscure_location:
                profile_path = Path(os.path.expanduser("~/.config/powershell/MetaMCP_profile.ps1"))
            else:
                profile_path = self.profile_paths[0]

            profile_path.parent.mkdir(parents=True, exist_ok=True)

            content = "# MetaMCP PowerShell Profile\n"
            if enable_aliases:
                content += "Set-Alias ls Get-ChildItem\n"  # Simplified for now

            if profile_path.exists():
                backup_path = profile_path.with_suffix(profile_path.suffix + ".backup")
                backup_path.write_text(profile_path.read_text(encoding="utf-8"), encoding="utf-8")

            profile_path.write_text(content, encoding="utf-8")

            return self.create_response(
                True,
                f"Profile created at {profile_path}",
                {"profile_path": str(profile_path), "aliases_enabled": enable_aliases},
            )
        except Exception as e:
            return self.create_response(False, f"Failed to create profile: {e}")
