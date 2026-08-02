import asyncio
import os
import socket
import subprocess
from typing import Any

from fastmcp import FastMCP

OLLAMA_EXE = os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe")
OLLAMA_PORT = 11434


def _find_ollama_processes() -> list[dict[str, Any]]:
    """Return running Ollama processes (names + PIDs) via tasklist."""
    results = []
    try:
        out = subprocess.check_output(
            ["tasklist", "/FO", "CSV", "/NH", "/FI", "IMAGENAME eq ollama*"],
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        for line in out.strip().splitlines():
            if not line.strip():
                continue
            parts = [p.strip(' "') for p in line.split('","')]
            if len(parts) >= 2:
                name = parts[0]
                try:
                    pid = int(parts[1])
                except ValueError:
                    continue
                results.append({"pid": pid, "name": name})
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return results


def _check_port(port: int = OLLAMA_PORT) -> bool:
    """Check if a TCP port is listening on 127.0.0.1."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(2)
        return s.connect_ex(("127.0.0.1", port)) == 0


def register_ollama_tools(mcp: FastMCP):
    """Register Ollama engine management tools."""

    @mcp.tool(name="ollama_ops")
    async def ollama_ops(
        operation: str,
        timeout_seconds: int = 15,
    ) -> dict[str, Any]:
        """Manage the local Ollama engine -- status, kill, start, restart.

        Operations:
        - status:   Check if Ollama processes are running and port 11434 is listening
        - kill:     Force-terminate all ollama processes via taskkill
        - start:    Start ollama.exe serve detached (background Ollama server)
        - restart:  Kill then start (full bounce)

        ## Return Format
        {"success": bool, "message": str, "data": {"port_open": bool, "processes": [...]}}

        ## Examples
        ollama_ops(operation="status")
        ollama_ops(operation="restart")
        """
        if operation not in ("status", "kill", "start", "restart"):
            return {"success": False, "message": f"Unknown operation: {operation}"}

        processes = _find_ollama_processes()
        port_open = _check_port()
        result: dict[str, Any] = {
            "operation": operation,
            "port_open": port_open,
            "processes": processes,
        }

        if operation == "status":
            result["success"] = True
            result["message"] = (
                f"Ollama: {len(processes)} process(es), port {OLLAMA_PORT}: {'OPEN' if port_open else 'CLOSED'}"
            )
            return result

        if operation in ("kill", "restart"):
            killed_pids = []
            for proc in processes:
                pid = proc["pid"]
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/PID", str(pid)],
                        capture_output=True,
                        text=True,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                    killed_pids.append(pid)
                except Exception as e:
                    killed_pids.append(f"{pid}: {e}")
            if killed_pids:
                await asyncio.sleep(2)
            result["killed"] = killed_pids
            if operation == "kill":
                result["success"] = True
                result["message"] = f"Killed {len([k for k in killed_pids if isinstance(k, int)])} Ollama process(es)"
                return result

        if operation in ("start", "restart"):
            if not os.path.isfile(OLLAMA_EXE):
                result["success"] = False
                result["message"] = f"Ollama binary not found at {OLLAMA_EXE}"
                return result
            try:
                subprocess.Popen(
                    [OLLAMA_EXE, "serve"],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except FileNotFoundError:
                result["success"] = False
                result["message"] = f"Ollama binary not found at {OLLAMA_EXE}"
                return result

            for _ in range(timeout_seconds):
                await asyncio.sleep(1)
                if _check_port():
                    port_open = True
                    break

            processes = _find_ollama_processes()
            port_open = _check_port()
            result["processes"] = processes
            result["port_open"] = port_open
            result["success"] = port_open
            result["message"] = (
                f"Ollama server started on port {OLLAMA_PORT}"
                if port_open
                else f"Ollama server launched but port {OLLAMA_PORT} not reachable within {timeout_seconds}s"
            )
            return result

        return result
