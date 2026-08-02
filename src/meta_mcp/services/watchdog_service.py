"""
MCP Watchdog Service
Scans Claude Desktop (and other agentic IDE) MCP server log files to detect:
  - Failed startup (no "Starting MCP server" in log, or empty log)
  - Hung commands (started event with no completed event within timeout window)
  - Crashes (Python tracebacks or ERROR/CRITICAL level entries at tail)
  - Stale servers (log not written to in > staleness_minutes)

Designed for Claude Desktop logs but generalizable to Cursor, Windsurf, Antigravity etc.
"""

import os
import re
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Status codes
# ---------------------------------------------------------------------------

STATUS_OK = "OK"
STATUS_STALE = "STALE"
STATUS_HUNG = "HUNG"
STATUS_CRASHED = "CRASHED"
STATUS_EMPTY = "EMPTY"
STATUS_NO_START = "NO_START"
STATUS_UNKNOWN = "UNKNOWN"

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ServerStatus:
    name: str
    log_path: str
    status: str
    detail: str = ""
    last_modified: float = 0.0
    last_modified_ago_min: float = 0.0
    hung_command: str = ""
    hung_since: str = ""
    crash_snippet: str = ""
    log_size_kb: float = 0.0


@dataclass
class WatchdogReport:
    generated_at: str = ""
    logs_dir: str = ""
    total_servers: int = 0
    ok: int = 0
    stale: int = 0
    hung: int = 0
    crashed: int = 0
    empty: int = 0
    no_start: int = 0
    servers: list[ServerStatus] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "generated_at": self.generated_at,
            "logs_dir": self.logs_dir,
            "total_servers": self.total_servers,
            "summary": {
                "ok": self.ok,
                "stale": self.stale,
                "hung": self.hung,
                "crashed": self.crashed,
                "empty": self.empty,
                "no_start": self.no_start,
            },
            "servers": [
                {
                    "name": s.name,
                    "status": s.status,
                    "detail": s.detail,
                    "last_modified_ago_min": round(s.last_modified_ago_min, 1),
                    "log_size_kb": round(s.log_size_kb, 1),
                    "hung_command": s.hung_command,
                    "hung_since": s.hung_since,
                    "crash_snippet": s.crash_snippet,
                    "log_path": s.log_path,
                }
                for s in self.servers
            ],
        }


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# FastMCP / MCP SDK startup line
RE_STARTED = re.compile(r"Starting MCP server", re.IGNORECASE)

# Structured JSON log: command_execution_started / completed
RE_CMD_STARTED = re.compile(r'"event":\s*"command_execution_started"')
RE_CMD_COMPLETED = re.compile(r'"event":\s*"command_execution_completed"')

# Crash indicators
RE_TRACEBACK = re.compile(r"Traceback \(most recent call last\)")
RE_ERROR_LEVEL = re.compile(r'"level":\s*"(error|critical)"', re.IGNORECASE)
RE_EXCEPTION = re.compile(r"(Exception|Error):\s+\S", re.IGNORECASE)

# Timestamp from structured JSON
RE_TIMESTAMP = re.compile(r'"timestamp":\s*"([^"]+)"')


def _extract_timestamp(line: str) -> datetime | None:
    """Try to parse a timestamp from a structured log line."""
    m = RE_TIMESTAMP.search(line)
    if not m:
        return None
    raw = m.group(1)
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


def _read_tail(path: Path, n_lines: int = 80) -> list[str]:
    """Read last n_lines from a potentially large file efficiently."""
    try:
        size = path.stat().st_size
        if size == 0:
            return []
        chunk = min(size, n_lines * 200)  # estimate ~200 chars/line
        with open(path, "rb") as f:
            f.seek(max(0, size - chunk))
            raw = f.read()
        text = raw.decode("utf-8", errors="replace")
        lines = text.splitlines()
        return lines[-n_lines:]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Core analyser
# ---------------------------------------------------------------------------


def analyse_log(log_path: Path, staleness_minutes: int = 30, hung_timeout_sec: int = 300) -> ServerStatus:
    """Analyse a single MCP server log file and return a ServerStatus."""
    name = log_path.stem.removeprefix("mcp-server-")
    status = ServerStatus(name=name, log_path=str(log_path))

    # ---- basic file info ----
    try:
        stat = log_path.stat()
        status.log_size_kb = stat.st_size / 1024
        status.last_modified = stat.st_mtime
        age_sec = time.time() - stat.st_mtime
        status.last_modified_ago_min = age_sec / 60
    except OSError as e:
        status.status = STATUS_UNKNOWN
        status.detail = f"Cannot stat file: {e}"
        return status

    # ---- empty log ----
    if status.log_size_kb < 0.05:
        status.status = STATUS_EMPTY
        status.detail = "Log file is empty or near-empty  server likely never started"
        return status

    tail = _read_tail(log_path, n_lines=100)
    tail_text = "\n".join(tail)

    # ---- crash detection ----
    if RE_TRACEBACK.search(tail_text):
        # Find the traceback snippet (last occurrence)
        for i, line in enumerate(reversed(tail)):
            if RE_TRACEBACK.search(line):
                snippet_lines = tail[-(i + 1) :][:6]
                status.crash_snippet = " | ".join(snippet_lines)
                break
        status.status = STATUS_CRASHED
        status.detail = "Python traceback detected in log tail"
        return status

    # Check for error/critical level structured log entries
    error_lines = [line for line in tail if RE_ERROR_LEVEL.search(line)]
    if error_lines:
        status.crash_snippet = error_lines[-1][:200]
        status.status = STATUS_CRASHED
        status.detail = "ERROR/CRITICAL level entry in log tail"
        return status

    # ---- startup check ----
    # Read first 50 lines for startup confirmation
    first_lines: list[str] = []
    try:
        with open(log_path, encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if i >= 50:
                    break
                first_lines.append(line)
    except OSError:
        pass

    all_text = "\n".join(first_lines)
    if not RE_STARTED.search(all_text) and not RE_STARTED.search(tail_text):
        status.status = STATUS_NO_START
        status.detail = "No 'Starting MCP server' found  startup may have failed"
        return status

    # ---- hung command detection ----
    # Scan tail for unmatched started/completed pairs
    now = datetime.now(tz=UTC)
    pending_started: dict[str, datetime] = {}

    for line in tail:
        if RE_CMD_STARTED.search(line):
            ts = _extract_timestamp(line)
            # extract command name if present
            cmd_match = re.search(r'"name":\s*"([^"]+)"', line)
            cmd = cmd_match.group(1) if cmd_match else "unknown"
            if ts:
                pending_started[cmd] = ts
        elif RE_CMD_COMPLETED.search(line):
            cmd_match = re.search(r'"name":\s*"([^"]+)"', line)
            cmd = cmd_match.group(1) if cmd_match else "unknown"
            pending_started.pop(cmd, None)

    for cmd, started_at in pending_started.items():
        elapsed = (now - started_at).total_seconds()
        if elapsed > hung_timeout_sec:
            status.status = STATUS_HUNG
            status.hung_command = cmd
            status.hung_since = started_at.isoformat()
            status.detail = f"Command '{cmd}' started {int(elapsed)}s ago with no completion"
            return status

    # ---- stale check ----
    if status.last_modified_ago_min > staleness_minutes:
        status.status = STATUS_STALE
        status.detail = (
            f"Log not updated in {status.last_modified_ago_min:.0f} min (threshold: {staleness_minutes} min)"
        )
        return status

    status.status = STATUS_OK
    status.detail = "Server appears healthy"
    return status


# ---------------------------------------------------------------------------
# Directory scanner
# ---------------------------------------------------------------------------


def scan_logs_directory(
    logs_dir: str | Path,
    staleness_minutes: int = 30,
    hung_timeout_sec: int = 300,
    include_rotated: bool = False,
) -> WatchdogReport:
    """
    Scan a directory of MCP server log files and return a WatchdogReport.

    Args:
        logs_dir: Path to the Claude (or other IDE) logs directory
        staleness_minutes: Minutes after which a non-updating log is flagged STALE
        hung_timeout_sec: Seconds after which an unmatched started event is flagged HUNG
        include_rotated: If False (default), skip files ending in digits (e.g. log1, log2)
    """
    logs_path = Path(logs_dir)
    report = WatchdogReport(
        generated_at=datetime.now().isoformat(),
        logs_dir=str(logs_path),
    )

    if not logs_path.exists():
        return report

    log_files = sorted(logs_path.glob("mcp-server-*.log"))

    if not include_rotated:
        # Skip rotated logs like mcp-server-winops1.log, mcp-server-winops2.log etc.
        log_files = [f for f in log_files if not re.search(r"\d+\.log$", f.name)]

    for log_file in log_files:
        s = analyse_log(log_file, staleness_minutes=staleness_minutes, hung_timeout_sec=hung_timeout_sec)
        report.servers.append(s)
        if s.status == STATUS_OK:
            report.ok += 1
        elif s.status == STATUS_STALE:
            report.stale += 1
        elif s.status == STATUS_HUNG:
            report.hung += 1
        elif s.status in (STATUS_CRASHED, STATUS_UNKNOWN):
            report.crashed += 1
        elif s.status == STATUS_EMPTY:
            report.empty += 1
        elif s.status == STATUS_NO_START:
            report.no_start += 1

    report.total_servers = len(report.servers)
    return report


# ---------------------------------------------------------------------------
# Convenience: known IDE log paths
# ---------------------------------------------------------------------------

IDE_LOG_PATHS: dict[str, str] = {
    "claude_desktop": r"C:\Users\{username}\AppData\Roaming\Claude\logs",
    "cursor": r"C:\Users\{username}\AppData\Roaming\Cursor\logs",
    "windsurf": r"C:\Users\{username}\AppData\Roaming\Windsurf\logs",
    "antigravity": r"C:\Users\{username}\.gemini\antigravity\logs",
    "opencode": r"C:\Users\{username}\.config\opencode\logs",
}


def get_default_log_path(ide: str = "claude_desktop") -> str:
    """Return the default MCP logs path for a given IDE, with username expanded."""
    username = os.environ.get("USERNAME") or os.environ.get("USER") or "user"
    template = IDE_LOG_PATHS.get(ide, IDE_LOG_PATHS["claude_desktop"])
    return template.replace("{username}", username)
