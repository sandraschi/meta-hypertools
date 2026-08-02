"""PyInstaller + Tauri sidecar entry  HTTP API on port 10718."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))


# PyInstaller lazy-import traps (fleet Tauri protocol)
import _datetime  # noqa: E402, F401
import _strptime  # noqa: E402, F401


def main() -> None:
    parser = argparse.ArgumentParser(description="MetaMCP HTTP web bridge")
    parser.add_argument("--http", action="store_true", help="Run HTTP (required for Tauri)")
    parser.add_argument("--port", type=int, default=10718)
    args = parser.parse_args()

    if not args.http:
        parser.error("Tauri sidecar requires --http")

    import uvicorn

    from meta_mcp.main import create_fastapi_app

    uvicorn.run(create_fastapi_app(), host="127.0.0.1", port=args.port, log_level="info")


if __name__ == "__main__":
    main()
