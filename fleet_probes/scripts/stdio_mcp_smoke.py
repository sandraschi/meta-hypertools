#!/usr/bin/env python3
"""Minimal MCP stdio smoke: spawn command, send initialize, expect JSON-RPC response.

v2 (2026-06-10)  teardown fixes after the 108-repo cold-start leak:
1. TREE kill (taskkill /T /F on Windows) in a finally block. The old
   proc.terminate()/kill() only hit the direct child  for `uv run <server>`
   that killed uv.exe and orphaned the server python grandchild on EVERY run,
   including successful ones.
2. Reader threads + queue for stdout/stderr. The old blocking
   proc.stdout.readline() ignored the deadline while a silent child was alive,
   and the undrained stderr pipe could fill and block the child (uv sync is
   chatty on stderr). Deadline is now always honored.
3. stdin is closed before the kill: well-behaved MCP servers exit on stdin
   EOF, so the tree-kill is usually just a safety net.
"""

from __future__ import annotations

import argparse
import json
import os
import queue
import subprocess
import sys
import threading
import time
from typing import Any

_STDERR_CAP = 200  # max stderr lines retained


def _pump(stream, q: queue.Queue) -> None:
    try:
        for line in iter(stream.readline, ""):
            q.put(line)
    except Exception:
        pass
    finally:
        q.put(None)  # EOF sentinel


def _kill_tree(proc: subprocess.Popen) -> None:
    """Kill the child and ALL descendants. Never raises."""
    if proc.poll() is not None:
        return
    # Graceful hint first: MCP servers exit on stdin EOF.
    try:
        if proc.stdin and not proc.stdin.closed:
            proc.stdin.close()
    except Exception:
        pass
    try:
        proc.wait(timeout=1)
        return
    except Exception:
        pass
    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/T", "/F", "/PID", str(proc.pid)],
                capture_output=True,
                timeout=10,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except Exception:
            pass
    try:
        proc.kill()
    except Exception:
        pass
    try:
        proc.wait(timeout=5)
    except Exception:
        pass


def run_smoke(
    command: str,
    args: list[str],
    timeout_sec: float = 10.0,
    *,
    env: dict[str, str] | None = None,
    cwd: str | None = None,
) -> dict[str, Any]:
    init_msg = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "fleet-cold-install-smoke", "version": "0.2.0"},
        },
    }
    child_env = os.environ.copy()
    if env:
        child_env.update(env)
    proc = subprocess.Popen(
        [command, *args],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=child_env,
        cwd=cwd or None,
    )
    assert proc.stdin is not None
    assert proc.stdout is not None
    assert proc.stderr is not None

    out_q: queue.Queue = queue.Queue()
    err_lines: list[str] = []

    def _pump_err(stream) -> None:
        try:
            for line in iter(stream.readline, ""):
                if len(err_lines) < _STDERR_CAP:
                    err_lines.append(line.rstrip())
        except Exception:
            pass

    threading.Thread(target=_pump, args=(proc.stdout, out_q), daemon=True).start()
    threading.Thread(target=_pump_err, args=(proc.stderr,), daemon=True).start()

    lines: list[str] = []
    try:
        proc.stdin.write(json.dumps(init_msg) + "\n")
        proc.stdin.flush()

        deadline = time.time() + timeout_sec
        while True:
            remaining = deadline - time.time()
            if remaining <= 0:
                break
            try:
                line = out_q.get(timeout=min(remaining, 0.5))
            except queue.Empty:
                if proc.poll() is not None and out_q.empty():
                    break
                continue
            if line is None:  # stdout EOF
                break
            stripped = line.strip()
            if not stripped:
                continue
            lines.append(stripped)
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict) and payload.get("jsonrpc") == "2.0":
                return {
                    "ok": True,
                    "response": payload,
                    "log": "\n".join(lines[-20:]),
                }

        return {
            "ok": False,
            "error": "No valid JSON-RPC response within timeout",
            "log": "\n".join([*lines, *err_lines][-30:]),
        }
    finally:
        # ALWAYS tear down the whole process tree (uv + server python + anything else).
        _kill_tree(proc)


def main() -> int:
    parser = argparse.ArgumentParser(description="MCP stdio initialize smoke test")
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--cwd", default="")
    parser.add_argument("--env", action="append", default=[], help="KEY=VALUE (repeatable)")
    parser.add_argument(
        "remainder",
        nargs=argparse.REMAINDER,
        help="Server command after optional '--' (e.g. -- uv run my-mcp)",
    )
    ns = parser.parse_args()
    tokens = list(ns.remainder or [])
    if tokens and tokens[0] == "--":
        tokens = tokens[1:]
    if not tokens:
        parser.error("missing server command (use -- before command if it starts with -)")
    command = tokens[0]
    args = tokens[1:]
    env_map: dict[str, str] = {}
    for item in ns.env:
        if "=" in item:
            k, v = item.split("=", 1)
            env_map[k] = v
    result = run_smoke(
        command,
        args,
        ns.timeout,
        env=env_map or None,
        cwd=ns.cwd or None,
    )
    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
