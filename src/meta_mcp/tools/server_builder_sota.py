"""FastMCP 3.4 fleet SOTA templates for scaffold_mcp_server."""

# ruff: noqa: E501, F821  - code generator templates; placeholders are template variables

from __future__ import annotations

from datetime import datetime


def _env_prefix(package_name: str) -> str:
    return package_name.upper()


def generate_sota_package_files(
    server_name: str,
    package_name: str,
    description: str,
    author: str,
    *,
    dual_connect: bool = False,
) -> dict[str, str]:
    """Return relative path -> content for a fleet 2026 MCP server layout."""
    pascal = "".join(word.capitalize() for word in server_name.split("-"))
    env_prefix = _env_prefix(package_name)
    status_card_tool = f"{server_name.replace('-', '_')}_status_card"
    http_condition = (
        "if args.http or os.getenv('MCP_TRANSPORT', '').lower() == 'http':" if dual_connect else "if args.http:"
    )

    files: dict[str, str] = {}

    files[f"src/{package_name}/__init__.py"] = f'"""{description}"""\n\n__version__ = "0.1.0"\n'

    files[f"src/{package_name}/config.py"] = f'''"""Multi-provider LLM configuration - local + cloud."""

from __future__ import annotations

import os
import socket
from dataclasses import dataclass


@dataclass
class LLMProvider:
    """LLM provider with endpoint, model, and API key."""
    provider: str          # ollama | lmstudio | openai | anthropic | google
    base_url: str
    model: str
    api_key: str | None = None

    @property
    def is_local(self) -> bool:
        return self.provider in ("ollama", "lmstudio")


# Preset provider profiles
PRESETS: dict[str, LLMProvider] = {{
    "ollama": LLMProvider(
        provider="ollama",
        base_url="http://127.0.0.1:11434/v1",
        model="llama3.2",
    ),
    "lmstudio": LLMProvider(
        provider="lmstudio",
        base_url="http://127.0.0.1:1234/v1",
        model="local-model",
    ),
    "openai": LLMProvider(
        provider="openai",
        base_url="https://api.openai.com/v1",
        model="gpt-4o",
    ),
    "anthropic": LLMProvider(
        provider="anthropic",
        base_url="https://api.anthropic.com/v1",
        model="claude-sonnet-4-20250514",
    ),
    "google": LLMProvider(
        provider="google",
        base_url="https://generativelanguage.googleapis.com/v1beta",
        model="gemini-2.5-flash",
    ),
}}


def detect_local_provider() -> LLMProvider | None:
    """Auto-detect local LLM providers via TCP health check."""
    for name in ("ollama", "lmstudio"):
        preset = PRESETS[name]
        try:
            host = preset.base_url.split("://")[1].split(":")[0]
            port = int(preset.base_url.split(":")[-1].split("/")[0])
            s = socket.socket()
            s.settimeout(0.5)
            s.connect((host, port))
            s.close()
            return preset
        except Exception:
            pass
    return None


def get_llm_config() -> LLMProvider:
    """Get the active LLM provider from env vars or auto-detection.

    Environment variables:
        {env_prefix}_LLM_PROVIDER   - ollama | lmstudio | openai | anthropic | google
        {env_prefix}_LLM_BASE_URL   - override API base URL
        {env_prefix}_LLM_MODEL      - override model name
        {env_prefix}_LLM_API_KEY    - API key (required for cloud providers)
    """
    provider_name = os.getenv("{env_prefix}_LLM_PROVIDER", "").lower()

    if provider_name and provider_name in PRESETS:
        preset = PRESETS[provider_name]
        return LLMProvider(
            provider=provider_name,
            base_url=os.getenv("{env_prefix}_LLM_BASE_URL", preset.base_url),
            model=os.getenv("{env_prefix}_LLM_MODEL", preset.model),
            api_key=os.getenv("{env_prefix}_LLM_API_KEY") or preset.api_key,
        )

    # Auto-detect local provider
    local = detect_local_provider()
    if local:
        model = os.getenv("{env_prefix}_LLM_MODEL", local.model)
        return LLMProvider(provider=local.provider, base_url=local.base_url, model=model)

    # Fallback: Ollama default
    return PRESETS["ollama"]
'''

    files[f"src/{package_name}/sampling.py"] = f'''"""FastMCP sampling handler - delegates to LLM client."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from {package_name}.config import get_llm_config

logger = logging.getLogger(__name__)

try:
    from fastmcp import Context
except ImportError:
    from fastmcp.server.context import Context  # type: ignore[attr-defined]


class SamplingHandler:
    """Route MCP sampling to the configured LLM provider."""

    def __init__(self) -> None:
        self._config = get_llm_config()

    async def __call__(
        self,
        context: Context,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        del context
        payload: dict[str, Any] = {{"model": self._config.model, "messages": messages}}
        if tools:
            payload["tools"] = tools

        headers: dict[str, str] = {{}}
        if self._config.api_key:
            headers["Authorization"] = f"Bearer {{self._config.api_key}}"

        async with httpx.AsyncClient(
            base_url=self._config.base_url,
            headers=headers,
            timeout=120.0,
        ) as client:
            response = await client.post("/chat/completions", json=payload)
            response.raise_for_status()
            return response.json()
'''

    files[f"src/{package_name}/llm_client.py"] = f'''"""Unified LLM client - routes to local or cloud providers."""

# ruff: noqa: E501  - generated payload lines exceed 120 chars

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

import httpx

from {package_name}.config import LLMProvider, get_llm_config

logger = logging.getLogger(__name__)


class LLMClient:
    """Unified chat client for all LLM providers.

    Supports: Ollama, LM Studio (local), OpenAI, Anthropic, Google (cloud).
    Provider-specific API format adaptation is handled transparently.
    """

    def __init__(self, provider: LLMProvider | None = None) -> None:
        self.provider = provider or get_llm_config()

    # -- Chat completion (non-streaming) --

    async def chat(
        self,
        prompt: str,
        system: str | None = None,
        history: list[dict[str, str]] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        """Send a chat completion and return the response dict."""
        messages: list[dict[str, str]] = []
        if system:
            messages.append({{"role": "system", "content": system}})
        if history:
            messages.extend(history)
        messages.append({{"role": "user", "content": prompt}})

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                if self.provider.provider == "anthropic":
                    return await self._chat_anthropic(client, messages, temperature, max_tokens)
                if self.provider.provider == "google":
                    return await self._chat_google(client, prompt, system, temperature, max_tokens)
                return await self._chat_openai_compat(client, messages, temperature, max_tokens)
        except httpx.HTTPError as e:
            logger.error("LLM chat failed: %s", e)
            return {{"error": str(e), "content": "", "model": self.provider.model}}

    async def _chat_openai_compat(
        self, client: httpx.AsyncClient, messages: list, temperature: float, max_tokens: int,
    ) -> dict[str, Any]:
        headers = {{}}
        if self.provider.api_key:
            headers["Authorization"] = f"Bearer {{self.provider.api_key}}"
        resp = await client.post(
            f"{{self.provider.base_url.rstrip('/')}}/chat/completions",
            json={{"model": self.provider.model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}},
            headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data.get("choices", [{{}}])[0].get("message", {{}}).get("content", "")
        return {{"success": True, "content": content, "model": self.provider.model, "provider": self.provider.provider}}

    async def _chat_anthropic(
        self, client: httpx.AsyncClient, messages: list, temperature: float, max_tokens: int,
    ) -> dict[str, Any]:
        system = next((m["content"] for m in messages if m["role"] == "system"), None)
        user_msgs = [m for m in messages if m["role"] != "system"]
        headers = {{
            "x-api-key": self.provider.api_key or "",
            "anthropic-version": "2023-06-01",
        }}
        body = {{
            "model": self.provider.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": user_msgs,
        }}
        if system:
            body["system"] = system
        resp = await client.post(
            f"{{self.provider.base_url.rstrip('/')}}/messages",
            json=body, headers=headers,
        )
        resp.raise_for_status()
        data = resp.json()
        content = "".join(b.get("text", "") for b in data.get("content", []))
        return {{"success": True, "content": content, "model": self.provider.model, "provider": "anthropic"}}

    async def _chat_google(
        self, client: httpx.AsyncClient, prompt: str, system: str | None, temperature: float, max_tokens: int,
    ) -> dict[str, Any]:
        api_key = self.provider.api_key or ""
        contents = [{{"parts": [{{"text": prompt}}], "role": "user"}}]
        if system:
            contents.insert(0, {{"parts": [{{"text": system}}], "role": "user"}})
        resp = await client.post(
            f"{{self.provider.base_url.rstrip('/')}}/models/{{self.provider.model}}:generateContent",
            params={{"key": api_key}},
            json={{"contents": contents, "generationConfig": {{"temperature": temperature, "maxOutputTokens": max_tokens}}}},
        )
        resp.raise_for_status()
        data = resp.json()
        content = "".join(
            p.get("text", "") for c in data.get("candidates", [])
            for p in c.get("content", {{}}).get("parts", [])
        )
        return {{"success": True, "content": content, "model": self.provider.model, "provider": "google"}}

    # -- Streaming chat (SSE) --

    async def chat_stream(
        self, prompt: str, system: str | None = None, history: list[dict[str, str]] | None = None,
        temperature: float = 0.7, max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        """Stream chat completion tokens."""
        messages: list[dict[str, str]] = []
        if system:
            messages.append({{"role": "system", "content": system}})
        if history:
            messages.extend(history)
        messages.append({{"role": "user", "content": prompt}})

        async with httpx.AsyncClient(timeout=300.0) as client:
            headers = {{}}
            if self.provider.api_key:
                headers["Authorization"] = f"Bearer {{self.provider.api_key}}"
            async with client.stream(
                "POST",
                f"{{self.provider.base_url.rstrip('/')}}/chat/completions",
                json={{"model": self.provider.model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens, "stream": True}},
                headers=headers,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        try:
                            chunk = json.loads(line[6:])
                            delta = chunk.get("choices", [{{}}])[0].get("delta", {{}}).get("content", "")
                            if delta:
                                yield delta
                        except json.JSONDecodeError:
                            pass

    # -- Health check --

    async def health(self) -> dict[str, Any]:
        """Test connectivity to the configured LLM provider."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{{self.provider.base_url.rstrip('/')}}/models")
                return {{"reachable": resp.status_code < 500, "provider": self.provider.provider, "model": self.provider.model}}
        except Exception as e:
            return {{"reachable": False, "provider": self.provider.provider, "error": str(e)}}
'''

    files[f"src/{package_name}/web.py"] = f'''"""FastAPI REST API - health, diagnostics, tools, chat."""

from __future__ import annotations

import json
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from {package_name} import __version__
from {package_name}.config import get_llm_config
from {package_name}.llm_client import LLMClient

logger = logging.getLogger(__name__)

app = FastAPI(
    title="{pascal}",
    version=__version__,
    description="{description}",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:{port}",
        "http://localhost:{port}",
        "http://tauri.localhost",
        "https://tauri.localhost",
        "tauri://localhost",
    ],
    allow_origin_regex=r"https?://(?:[a-zA-Z0-9-]+\\.ts\\.net|.*?\\.tail-[a-f0-9]+\\.ts\\.net|tauri\\.localhost|localhost|127\\.0\\.0\\.1|192\\.168\\.\\d{1, 3}\\.\\d{1, 3}|10\\.\\d{1, 3}\\.\\d{1, 3}\\.\\d{1, 3}|100\\.\\d{1, 3}\\.\\d{1, 3}\\.\\d{1, 3})(?::\\d+)?$|^tauri://localhost$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health ──

@app.get("/health")
async def health():
    """Basic health check."""
    return {{"status": "ok", "server": "{server_name}", "version": __version__}}


@app.get("/api/v1/diagnostics")
async def diagnostics():
    """Full system diagnostics - LLM, tools, system info."""
    llm_config = get_llm_config()
    client = LLMClient(llm_config)
    llm_health = await client.health()

    # Discover tools from the MCP singleton
    tool_names: list[str] = []
    try:
        from {package_name}.mcp_instance import get_mcp
        mcp = get_mcp()
        tools_list = await mcp.list_tools()
        tool_names = [t.name for t in tools_list] if tools_list else []
    except Exception:
        pass

    return {{
        "server": "{server_name}",
        "version": __version__,
        "status": "ok",
        "llm": {{
            "provider": llm_config.provider,
            "model": llm_config.model,
            "is_local": llm_config.is_local,
            **llm_health,
        }},
        "tools": tool_names,
        "tool_count": len(tool_names),
    }}


@app.get("/api/v1/tools")
async def list_tools():
    """List all registered MCP tools with their schemas."""
    try:
        from {package_name}.mcp_instance import get_mcp
        mcp = get_mcp()
        tools = await mcp.list_tools()
        return {{
            "success": True,
            "tools": [{{"name": t.name, "description": t.description}} for t in tools] if tools else [],
            "count": len(tools) if tools else 0,
        }}
    except Exception as e:
        return {{"success": False, "error": str(e)}}


# ── Chat ──

class ChatRequest(BaseModel):
    prompt: str
    system: str | None = None
    history: list[dict[str, str]] = Field(default_factory=list)
    temperature: float = 0.7
    max_tokens: int = 2048
    provider: str | None = None
    model: str | None = None
    stream: bool = False


@app.post("/api/v1/chat")
async def chat(req: ChatRequest):
    """Chat with the configured LLM provider."""
    config = get_llm_config()
    if req.provider and req.provider != config.provider:
        from {package_name}.config import LLMProvider, PRESETS  # noqa: I001
        preset = PRESETS.get(req.provider)
        if not preset:
            raise HTTPException(400, f"Unknown provider: {{req.provider}}")
        config = LLMProvider(
            provider=req.provider,
            base_url=preset.base_url,
            model=req.model or preset.model,
        )
    elif req.model:
        config = LLMProvider(provider=config.provider, base_url=config.base_url, model=req.model)

    client = LLMClient(config)

    if req.stream:
        async def _stream():
            async for token in client.chat_stream(
                req.prompt, system=req.system, history=req.history,
                temperature=req.temperature, max_tokens=req.max_tokens,
            ):
                yield f"data: {{json.dumps({{'token': token}})}}\\n\\n"
            yield "data: [DONE]\\n\\n"
        return StreamingResponse(_stream(), media_type="text/event-stream")

    result = await client.chat(
        req.prompt, system=req.system, history=req.history,
        temperature=req.temperature, max_tokens=req.max_tokens,
    )
    return result


@app.get("/api/v1/providers")
async def list_providers():
    """List available LLM providers with their presets."""
    from {package_name}.config import PRESETS, detect_local_provider
    local = detect_local_provider()
    return {{
        "providers": [
            {{"name": k, "base_url": v.base_url, "model": v.model, "is_local": v.is_local}}
            for k, v in PRESETS.items()
        ],
        "active": get_llm_config().provider,
        "local_detected": local.provider if local else None,
    }}
'''

    files[f"src/{package_name}/mcp_instance.py"] = f'''"""FastMCP singleton - single initialization point."""

from __future__ import annotations

import logging
import threading
from typing import Optional

from fastmcp import FastMCP

from {package_name} import __version__
from {package_name}.sampling import SamplingHandler

logger = logging.getLogger(__name__)

mcp: FastMCP | None = None


class _Singleton:
    _instance: Optional["_Singleton"] = None
    _lock = threading.Lock()
    _initialized = False

    def __new__(cls) -> "_Singleton":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._init()
        return cls._instance

    def _init(self) -> None:
        if self._initialized:
            return
        sampling_handler = SamplingHandler()
        self.mcp = FastMCP(
            name="{server_name}",
            version=__version__,
            sampling_handler=sampling_handler,
            sampling_handler_behavior="fallback",
            instructions=(
                "{description} "
                "Prefer prefab card tools for inventories and health. "
                "Use agentic_{package_name}_workflow when the client supports sampling."
            ),
            on_duplicate="replace",
        )
        global mcp
        mcp = self.mcp
        from {package_name}.tool_registration import register_all_tools

        register_all_tools(self.mcp)
        self._initialized = True
        logger.info("FastMCP initialized: %s v%s", self.mcp.name, self.mcp.version)


def get_mcp() -> FastMCP:
    inst = _Singleton()
    if inst.mcp is None:
        raise RuntimeError("FastMCP failed to initialize")
    return inst.mcp
'''

    files[f"src/{package_name}/tool_registration.py"] = f'''"""Register tools and fleet surface after FastMCP exists."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_registered = False


def register_all_tools(mcp=None) -> None:
    global _registered
    if _registered:
        return

    if mcp is None:
        from {package_name}.mcp_instance import get_mcp

        mcp = get_mcp()

    # Tool imports trigger decorator registration - keep in order
    import {package_name}.tools.agentic_workflow as _aw  # noqa: F401, I001
    import {package_name}.tools.help_tools as _ht  # noqa: F401
    import {package_name}.tools.chat_tool as _ct  # noqa: F401
    from {package_name}.fleet_surface import register_fleet_surface

    register_fleet_surface(mcp)
    _registered = True
    logger.info("Tools and fleet surface registered")
'''

    files[f"src/{package_name}/prefabs.py"] = f'''"""Prefab-UI card builders."""

from __future__ import annotations

from prefab_ui.components import Badge, Card, Metric, Row


def build_status_card(payload: dict) -> Card:
    healthy = payload.get("healthy", True)
    return Card(
        title="{pascal} Status",
        badges=[Badge(label="Healthy" if healthy else "Degraded")],
        children=[
            Row(
                children=[
                    Metric(label="Version", value=str(payload.get("version", "0.1.0"))),
                    Metric(label="Tools", value=str(payload.get("tool_count", "-"))),
                ]
            )
        ],
    )
'''

    files[f"src/{package_name}/fleet_surface.py"] = f'''"""MCP prompts, skills resource, and prefab tools."""

from __future__ import annotations

import logging
from typing import Annotated

from pydantic import Field

logger = logging.getLogger(__name__)

SKILLS_MD = """# {pascal} skills (fleet 2026)

## When to use
- Day-to-day operations via portmanteau tools
- Multi-step flows: prefer `agentic_{package_name}_workflow` when sampling is available

## Workflows
1. **Health**: `{server_name}_status_card` or `status`
2. **Discovery**: `help`
3. **Agentic**: `agentic_{package_name}_workflow` for natural-language orchestration
"""


def register_fleet_surface(mcp) -> None:
    @mcp.prompt()
    def {package_name}_session(goal: Annotated[str, Field(description="What to accomplish")] = "inspect") -> str:
        return (
            f"Using {server_name}: {{goal}}. Start with status or prefab cards, "
            "then chain portmanteau tools. Use agentic workflow for multi-step tasks."
        )

    @mcp.resource("resource://{server_name}/skills")
    def {package_name}_skills() -> str:
        return SKILLS_MD

    @mcp.resource("resource://{server_name}/capabilities")
    def {package_name}_capabilities() -> str:
        return (
            "{server_name}: FastMCP 3.4+, sampling (Ollama/LM Studio), "
            "agentic_{package_name}_workflow, prefab cards, MCP prompts/skills. "
            "CodeMode: --agentic flag."
        )

    @mcp.tool(annotations={{"readOnlyHint": True, "destructiveHint": False}})
    async def {status_card_tool}():
        """Server health as a Prefab card."""
        from {package_name}.prefabs import build_status_card
        from {package_name}.tools.help_tools import status

        result = await status()
        payload = result if isinstance(result, dict) else {{"message": str(result)}}
        payload.setdefault("version", "0.1.0")
        return build_status_card(payload)

    logger.info("Fleet surface registered: prompts, skills, prefab")
'''

    files[f"src/{package_name}/transport.py"] = f'''"""Dual transport + optional CodeMode (--agentic)."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os

logger = logging.getLogger(__name__)


def _parse_args(server_name: str) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=f"{{server_name}} - FastMCP 3.4")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--stdio", action="store_true", help="STDIO mode (default)")
    group.add_argument("--http", action="store_true", help="HTTP streamable mode")
    parser.add_argument("--host", default=os.getenv("MCP_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MCP_PORT", "10800")))
    parser.add_argument("--path", default=os.getenv("MCP_PATH", "/mcp"))
    parser.add_argument(
        "--agentic",
        action="store_true",
        help="Enable CodeMode agentic discovery",
    )
    parser.add_argument("--debug", action="store_true")
    return parser.parse_args()


async def run_async(mcp_app, server_name: str) -> None:
    args = _parse_args(server_name)
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    agentic = args.agentic or os.getenv("MCP_AGENTIC", "").lower() in ("true", "1", "yes")
    if agentic:
        try:
            from fastmcp.experimental.transforms.code_mode import CodeMode

            CodeMode().attach(mcp_app)
            logger.info("CodeMode enabled")
        except ImportError as exc:
            logger.warning("CodeMode unavailable: %s", exc)

    {http_condition}
        await mcp_app.run_http_async(
            host=args.host,
            port=args.port,
            path=args.path,
            show_banner=False,
        )
    else:
        await mcp_app.run_stdio_async(show_banner=False)


def run(mcp_app, server_name: str) -> None:
    asyncio.run(run_async(mcp_app, server_name))
'''

    files[f"src/{package_name}/server.py"] = f'''"""MCP server entry point."""

from __future__ import annotations

from {package_name}.mcp_instance import get_mcp
from {package_name}.transport import run


def main() -> None:
    run(get_mcp(), "{server_name}")


if __name__ == "__main__":
    main()
'''

    files[f"src/{package_name}/__main__.py"] = f'''"""python -m {package_name}"""

from {package_name}.server import main

if __name__ == "__main__":
    main()
'''

    files[f"src/{package_name}/tools/__init__.py"] = '"""Tool modules - imported by tool_registration."""\n'

    files[f"src/{package_name}/tools/help_tools.py"] = f'''"""Core help and status tools."""

from __future__ import annotations

from {package_name}.mcp_instance import mcp


@mcp.tool()
async def help() -> dict:
    """List capabilities and fleet surface for {pascal}."""
    return {{
        "success": True,
        "message": "{description}",
        "tools": ["help", "status", "agentic_{package_name}_workflow", "{status_card_tool}"],
        "resources": ["resource://{server_name}/skills", "resource://{server_name}/capabilities"],
        "codemode": "Pass --agentic or set MCP_AGENTIC=1 for CodeMode discovery",
    }}


@mcp.tool()
async def status() -> dict:
    """Server health and version."""
    from {package_name} import __version__

    tools = await mcp.list_tools() if hasattr(mcp, "list_tools") else []
    count = len(tools) if tools else 0
    return {{
        "success": True,
        "healthy": True,
        "version": __version__,
        "tool_count": count,
        "message": "{pascal} operational",
    }}
'''

    files[
        f"src/{package_name}/tools/chat_tool.py"
    ] = f'''"""LLM chat tool - local or cloud provider via unified client."""

# ruff: noqa: E501  - Field descriptions are verbose by design

from __future__ import annotations

import logging
from typing import Annotated

from pydantic import Field

from {package_name}.config import get_llm_config
from {package_name}.llm_client import LLMClient
from {package_name}.mcp_instance import mcp

logger = logging.getLogger(__name__)


@mcp.tool(annotations={{"readOnlyHint": True, "destructiveHint": False}})
async def chat(
    prompt: Annotated[str, Field(description="The message or question to send to the LLM.")],
    system: Annotated[str | None, Field(description="Optional system prompt to set context.")] = None,
    provider: Annotated[str | None, Field(description="Override provider: ollama, lmstudio, openai, anthropic, google.")] = None,
    model: Annotated[str | None, Field(description="Override model name.")] = None,
    temperature: Annotated[float, Field(description="Sampling temperature 0.0-2.0.", ge=0.0, le=2.0)] = 0.7,
    max_tokens: Annotated[int, Field(description="Max tokens in response.", ge=1, le=32768)] = 2048,
) -> dict:
    """Chat with the configured LLM provider (local or cloud).

    Uses the unified LLM client which auto-detects local providers (Ollama, LM Studio)
    and supports cloud providers (OpenAI, Anthropic, Google Gemini) via API keys.

    The provider and model can be overridden per-request.

    ## Return Format
    {{"success": bool, "content": str, "model": str, "provider": str}}

    ## Examples
    await chat(prompt="What is the capital of Austria?")
    await chat(prompt="Explain quantum computing in 3 sentences", system="Be concise.")
    await chat(prompt="Hello", provider="openai", model="gpt-4o")
    await chat(prompt="Describe Vienna", temperature=0.3)
    """
    if not prompt.strip():
        return {{"success": False, "error": "prompt is required"}}

    config = get_llm_config()

    # Provider override
    if provider and provider != config.provider:
        from {package_name}.config import LLMProvider, PRESETS  # noqa: I001
        preset = PRESETS.get(provider)
        if not preset:
            return {{"success": False, "error": f"Unknown provider: {{provider}}. Valid: {{', '.join(PRESETS)}}"}}
        config = LLMProvider(
            provider=provider,
            base_url=preset.base_url,
            model=model or preset.model,
        )
    elif model:
        config = LLMProvider(
            provider=config.provider,
            base_url=config.base_url,
            model=model,
        )

    client = LLMClient(config)

    try:
        result = await client.chat(
            prompt=prompt,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        if "error" in result:
            return result
        return {{
            "success": True,
            "content": result.get("content", ""),
            "model": result.get("model", config.model),
            "provider": result.get("provider", config.provider),
        }}
    except Exception as e:
        logger.error("Chat tool failed: %s", e)
        return {{
            "success": False,
            "error": str(e),
            "recovery_options": [
                "Check LLM provider is running and reachable",
                "Set {package_name.upper()}_LLM_PROVIDER to override auto-detection",
                "For cloud providers, set the corresponding API key env var",
            ],
        }}
'''

    files[f"src/{package_name}/tools/agentic_workflow.py"] = f'''"""SEP-1577 agentic workflow via client sampling."""

from __future__ import annotations

import logging

from fastmcp import Context

from {package_name}.mcp_instance import mcp

logger = logging.getLogger(__name__)


@mcp.tool()
async def agentic_{package_name}_workflow(
    workflow_prompt: str,
    available_tools: list[str] | None = None,
    max_iterations: int = 5,
    ctx: Context | None = None,
) -> dict:
    """Run a multi-step workflow using FastMCP sampling when the client supports it."""
    if not workflow_prompt.strip():
        return {{
            "success": False,
            "message": "Operation failed",
            "error": "workflow_prompt is required",
            "sampling_used": False,
        }}

    tools = available_tools or ["help", "status"]
    if ctx is not None and hasattr(ctx, "sample"):
        try:
            response = await ctx.sample(
                messages=[{{"role": "user", "content": workflow_prompt}}],
                tools=tools,
                max_tokens=2048,
            )
            return {{
                "success": True,
                "message": "Agentic workflow completed via sampling",
                "sampling_used": True,
                "result": response,
            }}
        except Exception as exc:
            logger.warning("Sampling failed: %s", exc)

    return {{
        "success": True,
        "message": "Structured fallback - use a sampling-capable MCP host for full agentic loops",
        "sampling_used": False,
        "suggested_tools": tools,
        "workflow_prompt": workflow_prompt,
        "max_iterations": max_iterations,
    }}
'''

    files[f"skills/{server_name}/SKILL.md"] = f"""# {pascal} Agent Skill

{description}

## FastMCP 3.4 surface
- Sampling via `{env_prefix}_SAMPLING_BASE_URL` (Ollama/LM Studio)
- `agentic_{package_name}_workflow` for multi-step tasks
- Prefab: `{status_card_tool}`
- CodeMode: `--agentic` or `MCP_AGENTIC=1`

## Quick start
```powershell
uv sync
uv run python -m {package_name}
```
"""

    files["mcpb/manifest.json"] = f'''{{
  "manifest_version": "0.3",
  "name": "{server_name}",
  "version": "0.1.0",
  "description": "{description}",
  "author": {{
    "name": "{author}"
  }},
  "license": "MIT",
  "server": {{
    "type": "python",
    "entry_point": "src/{package_name}/__main__.py",
    "mcp_config": {{
      "command": "uv",
      "args": ["--directory", "${{__dirname}}", "run", "python", "-m", "{package_name}"],
      "env": {{
        "PYTHONUNBUFFERED": "1"
      }}
    }}
  }}
}}
'''

    return files


def generate_sota_pyproject(
    package_name: str,
    description: str,
    author: str,
    license_type: str,
) -> str:
    return f'''[project]
name = "{package_name}"
version = "0.1.0"
description = "{description}"
authors = [{{name = "{author}"}}]
requires-python = ">=3.12"
readme = "README.md"
license = {{text = "{license_type}"}}
dependencies = [
    "fastmcp>=3.2,<4",
    "prefab-ui>=0.18.0",
    "httpx>=0.27",
    "pydantic>=2.0",
    "structlog>=24.0",
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8",
    "pytest-asyncio>=0.23",
    "ruff>=0.15",
]

[project.scripts]
{package_name} = "{package_name}.server:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/{package_name}"]

[tool.ruff]
line-length = 120
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "W"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
'''


def generate_sota_readme(server_name: str, package_name: str, description: str, author: str) -> str:
    status_card_tool = f"{server_name.replace('-', '_')}_status_card"
    return f"""# {server_name}

{description}

**Stack:** Python 3.12+ · FastMCP 3.4 · FastAPI · prefab-ui · Multi-provider LLM · Sampling · CodeMode (`--agentic`)

## Install

```powershell
uv sync --extra dev
pre-commit install
```

## Run

```powershell
# stdio (Claude Desktop / Cursor)
uv run python -m {package_name}

# HTTP + REST API (Tauri / webapp / direct access)
uv run python -m {package_name} --http --port 10800

# CodeMode agentic discovery
uv run python -m {package_name} --agentic

# Dev launcher (auto-opens browser)
.\\start.ps1
```

## LLM Providers

Auto-detects local providers (Ollama on :11434, LM Studio on :1234).
Configure via environment variables:

| Variable | Purpose |
|----------|---------|
| `{package_name.upper()}_LLM_PROVIDER` | ollama \\| lmstudio \\| openai \\| anthropic \\| google |
| `{package_name.upper()}_LLM_MODEL` | Override model name |
| `{package_name.upper()}_LLM_API_KEY` | API key (cloud providers) |

Cloud providers detect their standard env vars: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`.

## API Endpoints (HTTP mode)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| GET | `/api/v1/diagnostics` | Full diagnostics (LLM, tools, system) |
| GET | `/api/v1/tools` | List all MCP tools |
| GET | `/api/v1/providers` | List LLM providers + presets |
| POST | `/api/v1/chat` | Chat with LLM (supports streaming) |

## Fleet Surface

| Feature | Entry |
|---------|--------|
| Help | `help` tool |
| Status | `status` tool |
| Prefab card | `{status_card_tool}` |
| Chat | `chat` tool (multi-provider LLM) |
| Agentic | `agentic_{package_name}_workflow` |
| Skills | `resource://{server_name}/skills` |
| Capabilities | `resource://{server_name}/capabilities` |
| CodeMode | `--agentic` or `MCP_AGENTIC=1` |

## License

MIT © {datetime.now().year} {author}
"""
