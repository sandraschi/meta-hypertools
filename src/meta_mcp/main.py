#!/usr/bin/env python3
"""
MetaMCP Web UI/API Server - Main entry point.

Starts the FastAPI web server with MCP integration.
"""

import contextlib
import os
import sys

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# Import MCP server components
from fastmcp.server.http import create_streamable_http_app

from meta_mcp.api_router import router as api_router
from meta_mcp.auth import wurst_auth_middleware
from meta_mcp.logging_config import get_logger, setup_logging
from meta_mcp.logs_router import router as logs_router
from meta_mcp.mcp_server import app as mcp_app
from meta_mcp.session_docs_router import router as session_docs_router
from meta_mcp.standards_router import router as standards_router
from meta_mcp.telemetry import router as telemetry_router

# Use the centralized SOTA logging
setup_logging(log_level="INFO")
logger = get_logger(__name__)

# Build MCP ASGI app at module level for lifespan integration
# route at /mcp matches add_route("/mcp", ...) directly (no mount stripping)
_mcp_asgi = create_streamable_http_app(
    server=mcp_app,
    streamable_http_path="/mcp",
    json_response=False,
    stateless_http=False,
)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up MetaMCP Web Interface...")
    from meta_mcp.mcp_server import initialize_tools

    initialize_tools(mcp_app)
    # Forward lifespan to MCP ASGI app so task group initializes
    if _mcp_asgi is not None and hasattr(_mcp_asgi, "router"):
        async with _mcp_asgi.router.lifespan_context(app):
            yield
    else:
        yield
    logger.info("Shutting down MetaMCP Web Interface...")


def create_fastapi_app():
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="MetaMCP Registry & Orchestrator",
        description="Unified industrial management interface for the MCP server ecosystem.",
        version="0.4.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://127.0.0.1:10719",
            "http://localhost:10719",
            "http://goliath:10719",
            "http://tauri.localhost",
            "https://tauri.localhost",
            "tauri://localhost",
        ],
        allow_origin_regex=r"https?://(?:[a-zA-Z0-9-]+\.ts\.net|.*?\.tail-[a-f0-9]+\.ts\.net|tauri\.localhost|localhost|127\.0\.0\.1|192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|100\.\d{1,3}\.\d{1,3}\.\d{1,3})(?::\d+)?$|^tauri://localhost$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add Wurst-Auth Security Middleware
    app.middleware("http")(wurst_auth_middleware)

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        return {"status": "healthy", "service": "MetaMCP"}

    @app.get("/api/llm/providers")
    async def get_llm_providers():
        import httpx

        providers = []
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get("http://127.0.0.1:11434/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m["name"] for m in data.get("models", [])]
                    providers.append(
                        {
                            "id": "ollama",
                            "label": "Ollama",
                            "base_url": "http://127.0.0.1:11434/v1",
                            "models": models,
                            "needs_key": False,
                        }
                    )
        except Exception:
            providers.append(
                {
                    "id": "ollama",
                    "label": "Ollama",
                    "base_url": "http://127.0.0.1:11434/v1",
                    "models": [],
                    "needs_key": False,
                }
            )
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get("http://127.0.0.1:1234/v1/models")
                if resp.status_code == 200:
                    data = resp.json()
                    models = [m["id"] for m in data.get("data", [])]
                    providers.append(
                        {
                            "id": "lmstudio",
                            "label": "LM Studio",
                            "base_url": "http://127.0.0.1:1234/v1",
                            "models": models,
                            "needs_key": False,
                        }
                    )
        except Exception:
            providers.append(
                {
                    "id": "lmstudio",
                    "label": "LM Studio",
                    "base_url": "http://127.0.0.1:1234/v1",
                    "models": [],
                    "needs_key": False,
                }
            )
        return {"providers": providers}

    # Include API routes
    app.include_router(api_router)
    app.include_router(logs_router)
    app.include_router(telemetry_router)
    app.include_router(session_docs_router)
    app.include_router(standards_router)

    # Add MCP streamable HTTP route directly (no mount, avoids path prefix issues)
    app.add_route("/mcp", _mcp_asgi, methods=["POST"])

    # Mount static files if frontend exists
    # Get the project root directory
    # Script is now at src/meta_mcp/main.py, so we need to go up 2 levels
    script_dir = os.path.dirname(__file__)  # meta_mcp
    src_dir = os.path.dirname(script_dir)  # src
    project_root = os.path.dirname(src_dir)  # project root
    web_path = os.path.join(project_root, "web_sota", "dist")

    if os.path.exists(web_path):
        logger.info(f"Mounting webapp static files from: {web_path}")
        app.mount("/", StaticFiles(directory=web_path, html=True), name="webapp")
    else:
        logger.warning(f"Webapp dist directory not found at: {web_path}")

    return app


# Create global app instance for Uvicorn worker
app = create_fastapi_app()


def main():
    """Main entry point for the web server."""
    # Default configuration
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "10718"))

    # Allow command line override
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            logger.error(f"Invalid port number: {sys.argv[1]}")
            sys.exit(1)

    logger.info(f"Starting MetaMCP Web Server on {host}:{port}")

    # Use the global app instance
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
