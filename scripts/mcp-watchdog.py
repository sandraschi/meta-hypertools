"""
mcp-watchdog.py
MCP server log health watchdog + log maintenance for Claude Desktop and other agentic IDEs.

USAGE:
    python mcp-watchdog.py [command] [options]

COMMANDS:
    scan        Scan MCP server logs and report health status (default)
    purge       Delete old and rotated log files
    rotate      Truncate oversized active logs to tail
    clean       Run purge + rotate in one pass
    task        Manage Windows Scheduled Task (install / remove)

EXAMPLES:
    python mcp-watchdog.py
    python mcp-watchdog.py scan --ide cursor
    python mcp-watchdog.py scan --logs-dir "C:/custom/path/logs" --stale 60
    python mcp-watchdog.py scan --alert-only --logfile D:/dev/repos/temp/watchdog.log
    python mcp-watchdog.py purge --dry-run
    python mcp-watchdog.py purge --before 2025-11-01 --force
    python mcp-watchdog.py rotate --max-size 2 --keep-lines 3000 --force
    python mcp-watchdog.py clean --force
    python mcp-watchdog.py task --install
    python mcp-watchdog.py task --remove
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# IDE log path registry
# ---------------------------------------------------------------------------

IDE_LOG_PATHS = {
    "claude": Path.home() / "AppData" / "Roaming" / "Claude" / "logs",
    "cursor": Path.home() / "AppData" / "Roaming" / "Cursor" / "logs",
    "windsurf": Path.home() / "AppData" / "Roaming" / "Windsurf" / "logs",
    "antigravity": Path.home() / ".gemini" / "antigravity" / "logs",
    "zed": Path.home() / "AppData" / "Roaming" / "Zed" / "logs",
    "opencode": Path.home() / ".config" / "opencode" / "logs",
}

IDE_ALIASES = {
    "claude_desktop": "claude",
    "claude-desktop": "claude",
}

STATUS_OK = "OK"
STATUS_STALE = "STALE"
STATUS_HUNG = "HUNG"
STATUS_CRASHED = "CRASHED"
STATUS_EMPTY = "EMPTY"
STATUS_NO_START = "NO_START"

STATUS_EMOJI = {
    STATUS_OK: "SUCCESS",
    STATUS_STALE: "",
    STATUS_HUNG: "",
    STATUS_CRASHED: "",
    STATUS_EMPTY: "",
    STATUS_NO_START: "ERROR",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def resolve_ide(ide: str) -> str:
    return IDE_ALIASES.get(ide, ide)


def resolve_logs_dir(ide: str, logs_dir: str | None) -> Path:
    if logs_dir:
        return Path(logs_dir)
    ide = resolve_ide(ide)
    if ide not in IDE_LOG_PATHS:
        print(f"[warn] Unknown IDE '{ide}', falling back to claude", file=sys.stderr)
        ide = "claude"
    return IDE_LOG_PATHS[ide]


def read_tail(path: Path, n_lines: int = 100) -> list[str]:
    """Fast binary-seek tail reader."""
    try:
        size = path.stat().st_size
        if size == 0:
            return []
        chunk = min(size, n_lines * 250)
        with open(path, "rb") as f:
            f.seek(max(0, size - chunk))
            raw = f.read()
        text = raw.decode("utf-8", errors="replace")
        lines = text.splitlines()
        if chunk < size:
            lines = lines[1:]  # drop partial first line
        return lines[-n_lines:]
    except OSError:
        return []


def read_head(path: Path, n_lines: int = 50) -> list[str]:
    try:
        lines = []
        with open(path, encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f):
                if i >= n_lines:
                    break
                lines.append(line.rstrip())
        return lines
    except OSError:
        return []


def ts_from_line(line: str) -> datetime | None:
    m = re.search(r'"timestamp":\s*"([^"]+)"', line)
    if not m:
        return None
    raw = m.group(1)
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Log analysis
# ---------------------------------------------------------------------------


def analyse_log(
    log_path: Path,
    staleness_min: int = 30,
    hung_timeout_sec: int = 300,
) -> dict:
    name = log_path.stem.removeprefix("mcp-server-")
    result = {
        "name": name,
        "status": STATUS_NO_START,
        "detail": "",
        "size_kb": 0.0,
        "age_min": 0.0,
        "hung_command": "",
        "hung_since": "",
        "crash_snippet": "",
        "log_path": str(log_path),
    }
    try:
        stat = log_path.stat()
        result["size_kb"] = round(stat.st_size / 1024, 1)
        result["age_min"] = round((time.time() - stat.st_mtime) / 60, 1)
    except OSError as e:
        result["status"] = "UNKNOWN"
        result["detail"] = str(e)
        return result

    if result["size_kb"] < 0.05:
        result["status"] = STATUS_EMPTY
        result["detail"] = "Log file is empty  server likely never started"
        return result

    tail = read_tail(log_path, 100)
    tail_text = "\n".join(tail)

    # Crash: traceback
    if "Traceback (most recent call last)" in tail_text:
        for i, line in enumerate(reversed(tail)):
            if "Traceback" in line:
                snippet = " | ".join(tail[-(i + 1) :][:5])
                result["crash_snippet"] = snippet[:200]
                break
        result["status"] = STATUS_CRASHED
        result["detail"] = "Python traceback in log tail"
        return result

    # Crash: ERROR/CRITICAL structured log
    error_lines = [line for line in tail if re.search(r'"level":\s*"(error|critical)"', line, re.I)]
    if error_lines:
        result["crash_snippet"] = error_lines[-1][:200]
        result["status"] = STATUS_CRASHED
        result["detail"] = "ERROR/CRITICAL level entry in log tail"
        return result

    # Startup check
    head = read_head(log_path, 50)
    combined = "\n".join(head) + "\n" + tail_text
    if "Starting MCP server" not in combined:
        result["status"] = STATUS_NO_START
        result["detail"] = "No startup confirmation  server may have failed to initialize"
        return result

    # Hung command detection
    now = datetime.now(tz=UTC)
    pending: dict[str, datetime] = {}
    for line in tail:
        if '"event": "command_execution_started"' in line or '"command_execution_started"' in line:
            cmd_m = re.search(r'"name":\s*"([^"]+)"', line)
            cmd = cmd_m.group(1) if cmd_m else "unknown"
            ts = ts_from_line(line)
            if ts:
                pending[cmd] = ts
        elif '"command_execution_completed"' in line:
            cmd_m = re.search(r'"name":\s*"([^"]+)"', line)
            cmd = cmd_m.group(1) if cmd_m else "unknown"
            pending.pop(cmd, None)

    for cmd, started_at in pending.items():
        elapsed = (now - started_at).total_seconds()
        if elapsed > hung_timeout_sec:
            result["status"] = STATUS_HUNG
            result["hung_command"] = cmd
            result["hung_since"] = started_at.isoformat()
            result["detail"] = f"Command '{cmd}' started {int(elapsed)}s ago with no completion"
            return result

    # Stale
    if result["age_min"] > staleness_min:
        result["status"] = STATUS_STALE
        result["detail"] = f"Log not updated in {result['age_min']:.0f} min (threshold: {staleness_min} min)"
        return result

    result["status"] = STATUS_OK
    result["detail"] = "Server appears healthy"
    return result


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_scan(args, log_out):
    logs_dir = resolve_logs_dir(args.ide, getattr(args, "logs_dir", None))
    if not logs_dir.exists():
        print(f"[error] Logs directory not found: {logs_dir}", file=sys.stderr)
        sys.exit(1)

    log_files = sorted(f for f in logs_dir.glob("mcp-server-*.log") if not re.search(r"\d+\.log$", f.name))

    results = [analyse_log(f, staleness_min=args.stale, hung_timeout_sec=args.hung_timeout) for f in log_files]

    if getattr(args, "filter", None):
        allowed = {s.strip().upper() for s in args.filter.split(",") if s.strip()}
        results = [r for r in results if r["status"].upper() in allowed]

    counts = {s: 0 for s in [STATUS_OK, STATUS_STALE, STATUS_HUNG, STATUS_CRASHED, STATUS_EMPTY, STATUS_NO_START]}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1

    if args.json:
        output = json.dumps(
            {
                "generated_at": datetime.now().isoformat(),
                "ide": args.ide,
                "logs_dir": str(logs_dir),
                "summary": counts,
                "servers": results,
            },
            indent=2,
        )
        print(output)
        if log_out:
            log_out.write(output + "\n")
        return

    unhealthy = [r for r in results if r["status"] != STATUS_OK]
    if args.alert_only and not unhealthy:
        return

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header = f"\nMCP Watchdog  {ts}\nIDE: {args.ide}  |  Logs: {logs_dir}\nTotal: {len(results)}  " + "  ".join(
        f"{s}:{counts[s]}" for s in counts if counts[s] > 0
    )
    print(header)
    if log_out:
        log_out.write(header + "\n")

    if not unhealthy:
        msg = f"All {len(results)} MCP servers are healthy."
        print(msg)
        if log_out:
            log_out.write(msg + "\n")
        return

    print("\nUNHEALTHY SERVERS:")
    for r in unhealthy:
        line = f"  {STATUS_EMOJI.get(r['status'], '?')} [{r['status']:<8}] {r['name']}"
        detail = f"           {r['detail']}"
        print(line)
        print(detail)
        if r["hung_command"]:
            print(f"           Hung: {r['hung_command']}  since: {r['hung_since']}")
        if r["crash_snippet"]:
            snip = r["crash_snippet"][:120]
            print(f"           Crash: {snip}")
        if log_out:
            log_out.write(line + "\n" + detail + "\n")


def cmd_purge(args, log_out):
    logs_dir = resolve_logs_dir(args.ide, getattr(args, "logs_dir", None))
    dry_run = not args.force
    cutoff = datetime.strptime(args.before, "%Y-%m-%d")

    all_logs = list(logs_dir.glob("*.log"))
    old_files = [f for f in all_logs if datetime.fromtimestamp(f.stat().st_mtime) < cutoff]
    rotated_files = [f for f in all_logs if re.search(r"\d+\.log$", f.name)]

    to_delete = list({f.name: f for f in old_files + rotated_files}.values())
    total_mb = sum(f.stat().st_size for f in to_delete) / 1024 / 1024

    mode = "DRY RUN" if dry_run else "PURGE"
    print(f"\n{mode}  {len(to_delete)} files ({total_mb:.1f} MB)")
    print(f"  Pre-{args.before}: {len(old_files)}  Rotated (*N.log): {len(rotated_files)}")
    if dry_run:
        print("  (add --force to actually delete)\n")

    deleted = errors = 0
    for f in sorted(to_delete, key=lambda x: x.name):
        mb = f.stat().st_size / 1024 / 1024
        age = (datetime.now() - datetime.fromtimestamp(f.stat().st_mtime)).days
        if dry_run:
            print(f"  WOULD DELETE  {f.name}  ({mb:.1f} MB, {age}d old)")
        else:
            try:
                f.unlink()
                print(f"  DELETED  {f.name}  ({mb:.1f} MB)")
                deleted += 1
            except OSError as e:
                print(f"  ERROR  {f.name}: {e}")
                errors += 1

    summary = f"Purge complete: {deleted} deleted, {errors} errors" if not dry_run else "Dry run complete."
    print(f"\n{summary}")
    if log_out:
        log_out.write(f"{summary}\n")


def cmd_rotate(args, log_out):
    logs_dir = resolve_logs_dir(args.ide, getattr(args, "logs_dir", None))
    dry_run = not args.force
    threshold = args.max_size * 1024 * 1024

    large = sorted(
        (f for f in logs_dir.glob("*.log") if not re.search(r"\d+\.log$", f.name) and f.stat().st_size > threshold),
        key=lambda f: f.stat().st_size,
        reverse=True,
    )

    mode = "DRY RUN" if dry_run else "ROTATE"
    print(f"\n{mode}  {len(large)} active logs >{args.max_size}MB")
    if dry_run:
        print("  (add --force to actually truncate)\n")

    truncated = errors = 0
    script = Path(__file__).parent / "log_rotate.py"
    python = sys.executable

    for f in large:
        mb = round(f.stat().st_size / 1024 / 1024, 1)
        if dry_run:
            print(f"  WOULD TRUNCATE  {f.name}  ({mb} MB -> keep last {args.keep_lines} lines)")
        else:
            try:
                subprocess.run(
                    [python, str(script), str(f), str(args.keep_lines)],
                    check=True,
                    capture_output=True,
                )
                size_after = f.stat().st_size
                new_mb = round(size_after / 1024 / 1024, 1)
                print(f"  TRUNCATED  {f.name}  ({mb} MB -> {new_mb} MB)")
                truncated += 1
            except Exception as e:
                print(f"  ERROR  {f.name}: {e}")
                errors += 1

    summary = f"Rotation complete: {truncated} truncated, {errors} errors" if not dry_run else "Dry run complete."
    print(f"\n{summary}")
    if log_out:
        log_out.write(f"{summary}\n")


def cmd_task(args):
    script = Path(__file__).resolve()
    task_name = "MCP-Watchdog"

    if args.install:
        ide_flag = f"--ide {args.ide}"
        python_bin = sys.executable
        ps_cmd = (
            f'$action = New-ScheduledTaskAction -Execute "{python_bin}" '
            f'-Argument \\"{script} scan {ide_flag} --alert-only\\"; '
            f"$trigger = New-ScheduledTaskTrigger -RepetitionInterval (New-TimeSpan -Minutes 15) -Once -At (Get-Date); "
            f"$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 5) -MultipleInstances IgnoreNew; "
            f'Register-ScheduledTask -TaskName "{task_name}" -Action $action -Trigger $trigger -Settings $settings -Force'
        )
        pwsh_path = shutil.which("powershell") or shutil.which("pwsh") or "powershell"
        result = subprocess.run(
            [pwsh_path, "-NonInteractive", "-Command", ps_cmd],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(f"Scheduled task '{task_name}' installed (runs every 15 min, alert-only).")
        else:
            print(f"Failed to install task: {result.stderr}")

    elif args.remove:
        ps_cmd = f'Unregister-ScheduledTask -TaskName "{task_name}" -Confirm:$false -ErrorAction SilentlyContinue'
        pwsh_path = shutil.which("powershell") or shutil.which("pwsh") or "powershell"
        subprocess.run([pwsh_path, "-NonInteractive", "-Command", ps_cmd])
        print(f"Scheduled task '{task_name}' removed.")

    else:
        print("Use --install or --remove")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    ide_choices = list(IDE_LOG_PATHS.keys()) + list(IDE_ALIASES.keys())

    parser = argparse.ArgumentParser(
        prog="mcp-watchdog",
        description="MCP server log health watchdog + log maintenance for agentic IDEs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    sub = parser.add_subparsers(dest="command", metavar="COMMAND")

    # ---- shared options factory ----
    def add_shared(p):
        p.add_argument(
            "--ide",
            default="claude",
            choices=ide_choices,
            metavar="IDE",
            help=f"IDE to target. One of: {', '.join(IDE_LOG_PATHS)}. Default: claude",
        )
        p.add_argument("--logs-dir", metavar="PATH", help="Override logs directory path")
        p.add_argument("--logfile", metavar="FILE", help="Append output to this file in addition to stdout")

    # ---- scan ----
    p_scan = sub.add_parser("scan", help="Scan MCP logs and report server health (default command)")
    add_shared(p_scan)
    p_scan.add_argument(
        "--stale",
        type=int,
        default=30,
        metavar="MIN",
        help="Minutes before a non-updating log is flagged STALE (default: 30)",
    )
    p_scan.add_argument(
        "--hung-timeout",
        type=int,
        default=300,
        metavar="SEC",
        help="Seconds before an unmatched command start is flagged HUNG (default: 300)",
    )
    p_scan.add_argument("--alert-only", action="store_true", help="Suppress output if all servers are healthy")
    p_scan.add_argument("--json", action="store_true", help="Emit full JSON report to stdout")
    p_scan.add_argument("--filter", metavar="STATUS", help="Comma-separated statuses to show, e.g. HUNG,CRASHED,STALE")

    # ---- purge ----
    p_purge = sub.add_parser("purge", help="Delete old and rotated log files")
    add_shared(p_purge)
    p_purge.add_argument(
        "--before",
        default="2025-10-01",
        metavar="YYYY-MM-DD",
        help="Delete logs last modified before this date (default: 2025-10-01)",
    )
    p_purge.add_argument("--force", action="store_true", help="Actually delete files (default is dry-run)")
    p_purge.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without deleting (default behaviour without --force)",
    )

    # ---- rotate ----
    p_rotate = sub.add_parser("rotate", help="Truncate oversized active logs to tail")
    add_shared(p_rotate)
    p_rotate.add_argument(
        "--max-size", type=float, default=5.0, metavar="MB", help="Truncate logs larger than this many MB (default: 5)"
    )
    p_rotate.add_argument(
        "--keep-lines", type=int, default=5000, metavar="N", help="Lines to keep from tail (default: 5000)"
    )
    p_rotate.add_argument("--force", action="store_true", help="Actually truncate files (default is dry-run)")
    p_rotate.add_argument("--dry-run", action="store_true", help="Show what would be truncated without truncating")

    # ---- clean (purge + rotate) ----
    p_clean = sub.add_parser("clean", help="Run purge + rotate in one pass")
    add_shared(p_clean)
    p_clean.add_argument(
        "--before", default="2025-10-01", metavar="YYYY-MM-DD", help="Purge cutoff date (default: 2025-10-01)"
    )
    p_clean.add_argument(
        "--max-size", type=float, default=5.0, metavar="MB", help="Rotate threshold in MB (default: 5)"
    )
    p_clean.add_argument(
        "--keep-lines", type=int, default=5000, metavar="N", help="Lines to keep from tail (default: 5000)"
    )
    p_clean.add_argument("--force", action="store_true", help="Actually execute (default is dry-run)")
    p_clean.add_argument("--dry-run", action="store_true", help="Show what would happen without doing it")

    # ---- task ----
    p_task = sub.add_parser("task", help="Manage Windows Scheduled Task")
    p_task.add_argument(
        "--ide", default="claude", choices=ide_choices, metavar="IDE", help="IDE for the scheduled scan task"
    )
    p_task.add_argument("--install", action="store_true", help="Install scheduled task")
    p_task.add_argument("--remove", action="store_true", help="Remove scheduled task")

    return parser


def open_logfile(path: str | None):
    if not path:
        return None
    try:
        return open(path, "a", encoding="utf-8")
    except OSError as e:
        print(f"[warn] Cannot open logfile {path}: {e}", file=sys.stderr)
        return None


def main():
    parser = build_parser()
    args = parser.parse_args()

    # Default command is scan
    if not args.command:
        args.command = "scan"
        # Apply scan defaults if not set
        if not hasattr(args, "ide"):
            args.ide = "claude"
        if not hasattr(args, "stale"):
            args.stale = 30
        if not hasattr(args, "hung_timeout"):
            args.hung_timeout = 300
        if not hasattr(args, "alert_only"):
            args.alert_only = False
        if not hasattr(args, "json"):
            args.json = False
        if not hasattr(args, "filter"):
            args.filter = None
        if not hasattr(args, "logfile"):
            args.logfile = None
        if not hasattr(args, "logs_dir"):
            args.logs_dir = None

    log_out = open_logfile(getattr(args, "logfile", None))

    try:
        if args.command == "scan":
            cmd_scan(args, log_out)
        elif args.command == "purge":
            cmd_purge(args, log_out)
        elif args.command == "rotate":
            cmd_rotate(args, log_out)
        elif args.command == "clean":
            cmd_purge(args, log_out)
            cmd_rotate(args, log_out)
        elif args.command == "task":
            cmd_task(args)
        else:
            parser.print_help()
    finally:
        if log_out:
            log_out.close()


if __name__ == "__main__":
    main()
