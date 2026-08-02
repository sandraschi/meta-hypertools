"""Supervisor: aggregate pipeline liveness from arxiv, aiwatcher, and vla-mcp."""

from __future__ import annotations

from typing import Any

import aiohttp

from meta_mcp.services.base import MetaMCPService

_ARXIV_LIVENESS = "http://127.0.0.1:10770/api/pipeline/liveness"
_AIWATCHER_LIVENESS = "http://127.0.0.1:10946/api/pipeline/liveness"
_VLA_LIVENESS = "http://127.0.0.1:11024/api/pipeline/liveness"


class PipelineLivenessService(MetaMCPService):
    """HTTP probe of both pipeline endpoints; surfaces critical alerts for supervisors."""

    async def check_all(self, *, stale_hours: int = 48) -> dict[str, Any]:
        stale_hours = max(1, int(stale_hours))
        params = {"stale_hours": str(stale_hours)}
        timeout = aiohttp.ClientTimeout(total=15)
        services: dict[str, Any] = {}
        alerts: list[dict[str, Any]] = []

        async with aiohttp.ClientSession(timeout=timeout) as session:
            for key, url in (
                ("arxiv_mcp", _ARXIV_LIVENESS),
                ("aiwatcher_mcp", _AIWATCHER_LIVENESS),
                ("vla_mcp", _VLA_LIVENESS),
            ):
                try:
                    async with session.get(url, params=params) as resp:
                        if resp.status != 200:
                            body = await resp.text()
                            raise RuntimeError(f"HTTP {resp.status}: {body[:200]}")
                        data = await resp.json()
                    services[key] = data
                    for alert in data.get("alerts") or []:
                        alerts.append({**alert, "source": key})
                except Exception as exc:
                    services[key] = {"success": False, "message": str(exc), "healthy": False, "error": str(exc)}
                    alerts.append(
                        {
                            "severity": "critical",
                            "code": "PIPELINE_PROBE_FAILED",
                            "source": key,
                            "message": f"Failed to probe {url}: {exc}",
                            "detail": {"url": url},
                        }
                    )

        critical = [a for a in alerts if a.get("severity") == "critical"]
        healthy = not critical and all(s.get("healthy", False) for s in services.values() if s.get("success", True))

        return self.create_response(
            True,
            "Pipeline liveness check complete",
            {
                "healthy": healthy,
                "stale_hours": stale_hours,
                "critical_count": len(critical),
                "alert_count": len(alerts),
                "alerts": alerts,
                "services": services,
            },
        )
