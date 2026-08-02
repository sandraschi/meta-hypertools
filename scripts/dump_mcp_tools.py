"""Print all registered Meta MCP tool names + first line of description (stdio, no server)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Repo root when run as: uv run python scripts/dump_mcp_tools.py
_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_ROOT / "src"))

from meta_mcp.mcp_server import app, initialize_tools


async def main() -> None:
    initialize_tools(app)
    tools = await app.list_tools()
    for t in sorted(tools, key=lambda x: (x.name or "").lower()):
        desc = t.description or ""
        line = desc.splitlines()[0].strip() if desc else ""
        print(f"{t.name}\n  {line}\n")


if __name__ == "__main__":
    asyncio.run(main())
