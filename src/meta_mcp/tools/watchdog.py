"""
MCP Watchdog Tool
Exposes watchdog_service as MCP tools for meta_mcp.
"""

from meta_mcp.services.watchdog_service import (
    WatchdogReport,
    get_default_log_path,
    scan_logs_directory,
)


def register_watchdog_tools(mcp):
    """Register watchdog tools on the FastMCP server instance."""

    @mcp.tool()
    async def watchdog_scan(
        logs_dir: str = "",
        ide: str = "claude_desktop",
        staleness_minutes: int = 30,
        hung_timeout_sec: int = 300,
        include_rotated: bool = False,
        status_filter: str = "",
    ) -> dict:
        """
        Scan MCP server log files and report health status of all servers.

        Detects:
          - HUNG: command started but never completed within timeout
          - CRASHED: Python traceback or ERROR/CRITICAL in log tail
          - STALE: log not written to within staleness window
          - EMPTY: log file is empty (server never started)
          - NO_START: no startup confirmation found in log
          - OK: server appears healthy

        Args:
            logs_dir: Path to logs directory. If empty, uses default for the specified IDE.
            ide: One of claude_desktop, cursor, windsurf, antigravity. Used to pick default logs_dir.
            staleness_minutes: Minutes after which an idle log is flagged STALE (default 30).
            hung_timeout_sec: Seconds after which an unmatched command start is flagged HUNG (default 300).
            include_rotated: If True, also scan rotated log files (e.g. mcp-server-winops1.log).
            status_filter: If set, only return servers matching this status (e.g. 'HUNG,CRASHED,STALE').

        Returns:
            WatchdogReport dict with summary counts and per-server status details.
        """
        path = logs_dir or get_default_log_path(ide)
        report: WatchdogReport = scan_logs_directory(
            logs_dir=path,
            staleness_minutes=staleness_minutes,
            hung_timeout_sec=hung_timeout_sec,
            include_rotated=include_rotated,
        )
        result = report.to_dict()

        # Apply optional status filter
        if status_filter:
            wanted = {s.strip().upper() for s in status_filter.split(",")}
            result["servers"] = [s for s in result["servers"] if s["status"] in wanted]

        return result

    @mcp.tool()
    async def watchdog_status_summary(
        logs_dir: str = "",
        ide: str = "claude_desktop",
    ) -> dict:
        """
        Quick summary of MCP server health  counts only, no per-server detail.
        Useful as a session-start health check.

        Args:
            logs_dir: Path to logs directory. Defaults to claude_desktop logs.
            ide: IDE name for default path resolution.

        Returns:
            Dict with total, ok, stale, hung, crashed, empty, no_start counts
            plus a list of unhealthy server names.
        """
        path = logs_dir or get_default_log_path(ide)
        report = scan_logs_directory(logs_dir=path, staleness_minutes=30, hung_timeout_sec=300)
        unhealthy = [
            {"name": s.name, "status": s.status, "detail": s.detail} for s in report.servers if s.status != "OK"
        ]
        return {
            "generated_at": report.generated_at,
            "logs_dir": report.logs_dir,
            "total": report.total_servers,
            "ok": report.ok,
            "unhealthy_count": report.total_servers - report.ok,
            "stale": report.stale,
            "hung": report.hung,
            "crashed": report.crashed,
            "empty": report.empty,
            "no_start": report.no_start,
            "unhealthy": unhealthy,
        }

    @mcp.tool()
    async def watchdog_known_ide_paths() -> dict:
        """
        Return the known default MCP log paths for all supported IDEs.
        Useful for discovering which IDEs are configured on this machine.

        Returns:
            Dict mapping IDE name to its resolved log path and whether the path exists.
        """
        import os
        from pathlib import Path

        from meta_mcp.services.watchdog_service import IDE_LOG_PATHS

        username = os.environ.get("USERNAME") or os.environ.get("USER") or "user"
        result = {}
        for ide_name, template in IDE_LOG_PATHS.items():
            resolved = template.replace("{username}", username)
            result[ide_name] = {
                "path": resolved,
                "exists": Path(resolved).exists(),
            }
        return result
