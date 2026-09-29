"""Dual-mode entry: MCP stdio server (default) or HTTP API (--http).

- No flags  -> stdio MCP server for Claude Desktop / IDEs (meta_mcp.mcp_server).
- --http     -> uvicorn HTTP bridge for Tauri sidecar / dashboard backend.

Top-level imports stay light on purpose (argparse only): the MCPB
import-verification runs this file without calling main(), and heavy
imports stay deferred inside each branch.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))


# PyInstaller lazy-import traps (fleet Tauri protocol)
import _datetime  # noqa: E402, F401
import _strptime  # noqa: E402, F401

# Eager package bootstrap: freeze the `mcp` import chain before fastmcp
# touches it (frozen `mcp/__init__.py` lazy imports fail silently).
import mcp.types  # noqa: E402, F401


def main() -> None:
    # Frozen exe (PyInstaller/Tauri): sys.argv holds frozen paths, not CLI
    # flags, so translate spawn env into args BEFORE argparse. Without this
    # the entry falls through to stdio and the backend never serves HTTP.
    if getattr(sys, "frozen", False):
        port = os.environ.get("MCP_PORT") or os.environ.get("PORT")
        if port:
            sys.argv = ["run_server.py", "--http", "--port", str(port)]
    parser = argparse.ArgumentParser(description="MetaMCP dual-mode entry: stdio MCP (default) or HTTP bridge")
    parser.add_argument("--http", action="store_true", help="Run HTTP instead of MCP stdio")
    parser.add_argument("--port", type=int, default=10718)
    args = parser.parse_args()

    if args.http:
        import uvicorn
        from meta_mcp.main import create_fastapi_app

        uvicorn.run(create_fastapi_app(), host="127.0.0.1", port=args.port, log_level="info")
    else:
        from meta_mcp.mcp_server import main as stdio_main

        stdio_main()


if __name__ == "__main__":
    main()
