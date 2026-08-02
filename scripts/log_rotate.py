#!/usr/bin/env python3
"""
log_rotate.py - Truncate log files to keep only recent lines.

Usage:
  python log_rotate.py <path> <keep_lines>
  python log_rotate.py <path> <keep_lines> --dry-run

Creates a .bak before truncating. Reports lines kept and size saved.
"""

import os
import shutil
import sys
from datetime import datetime


def main():
    if len(sys.argv) < 3:
        print("usage: log_rotate.py <path> <keep_lines> [--dry-run]", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    dry_run = "--dry-run" in sys.argv
    try:
        keep = int(sys.argv[2])
    except ValueError:
        print(f"[ERR] keep_lines must be an integer: {sys.argv[2]}", file=sys.stderr)
        sys.exit(1)

    if keep < 1:
        print(f"[ERR] keep_lines must be >= 1: {keep}", file=sys.stderr)
        sys.exit(1)

    try:
        size_before = os.path.getsize(path)
    except FileNotFoundError:
        print(f"[ERR] File not found: {path}", file=sys.stderr)
        sys.exit(1)

    if size_before == 0:
        print("skip:empty")
        sys.exit(0)

    chunk = keep * 250
    read_bytes = min(size_before, chunk)

    try:
        with open(path, "rb") as f:
            f.seek(max(0, size_before - read_bytes))
            raw = f.read()
    except PermissionError:
        print(f"[ERR] Permission denied reading: {path}", file=sys.stderr)
        sys.exit(1)
    except OSError as e:
        print(f"[ERR] Failed to read {path}: {e}", file=sys.stderr)
        sys.exit(1)

    text = raw.decode("utf-8", errors="replace")
    lines = text.splitlines()

    if len(lines) > 1:
        lines = lines[1:]

    tail = lines[-keep:] if len(lines) > keep else lines
    kept = len(tail)
    size_after = sum(len(line) + 1 for line in tail)

    header = (
        f"# [mcp-watchdog truncated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        f" - kept {kept} of {size_before // 1024}KB log]"
    )
    result = header + "\n" + "\n".join(tail) + "\n"

    if dry_run:
        saved_kb = (size_before - size_after) // 1024
        print(
            f"dry-run: would keep {kept} lines, save {saved_kb}KB ({size_before // 1024}KB -> {size_after // 1024}KB)"
        )
        sys.exit(0)

    bak = path + ".bak"
    try:
        shutil.copy2(path, bak)
    except OSError as e:
        print(f"[ERR] Backup failed: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(result)
    except OSError as e:
        print(f"[ERR] Failed to write {path}: {e}", file=sys.stderr)
        # Restore from backup
        shutil.copy2(bak, path)
        sys.exit(1)

    saved_kb = (size_before - size_after) // 1024
    print(f"ok:{kept} (saved {saved_kb}KB, backup: {bak})")


if __name__ == "__main__":
    main()
