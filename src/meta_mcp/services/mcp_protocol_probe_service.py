"""MCP protocol compatibility probe -- wraps the mcp-explorer CLI (https://github.com/simonw/mcp-explorer)
via `uvx` (isolated environment; mcp-explorer requires mcp>=2.0, incompatible with this repo's
fastmcp[tasks]<4 pin on mcp<2.0, so it cannot be a direct dependency)."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from typing import Any

from meta_mcp.services.base import MetaMCPService

log = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 30


class McpProtocolProbeService(MetaMCPService):
    """Check stateless-MCP2 vs legacy protocol compatibility for a streamable-HTTP MCP endpoint."""

    def _uvx_path(self) -> str | None:
        return shutil.which("uvx")

    def doctor(self, url: str) -> dict[str, Any]:
        """Run `mcp-explorer doctor <url> --json` and return the parsed compatibility report."""
        if not url or not url.strip():
            return self.create_response(False, "url is required")

        uvx = self._uvx_path()
        if not uvx:
            return self.create_response(
                False,
                "uvx not found on PATH -- install uv (https://docs.astral.sh/uv/)",
                {"recovery_options": ["Install uv", "Re-run once `uvx --version` works"]},
            )

        args = [uvx, "mcp-explorer", "doctor", url.strip(), "--json"]
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=_TIMEOUT_SECONDS,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except subprocess.TimeoutExpired:
            return self.create_response(
                False,
                f"mcp-explorer doctor timed out after {_TIMEOUT_SECONDS}s probing {url}",
                {"url": url},
            )
        except OSError as e:
            return self.create_response(False, f"Failed to launch mcp-explorer: {e}", {"url": url})

        stdout = (result.stdout or "").strip()
        try:
            report = json.loads(stdout) if stdout else {}
        except json.JSONDecodeError:
            report = {"raw_stdout": stdout}

        healthy = bool(report.get("healthy")) if isinstance(report, dict) else False
        msg = f"{url}: {'healthy' if healthy else 'unhealthy'}"
        return self.create_response(
            True,
            msg,
            {
                "url": url,
                "returncode": result.returncode,
                "report": report,
                "stderr_tail": (result.stderr or "")[-1000:],
            },
        )
