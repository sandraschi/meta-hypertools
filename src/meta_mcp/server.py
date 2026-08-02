"""
ASGI entry point for uvicorn (web_sota backend).

Use: uvicorn meta_mcp.server:app --host 127.0.0.1 --port ...
"""

from meta_mcp.main import app

__all__ = ["app"]
