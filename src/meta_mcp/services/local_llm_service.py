"""Proxy local Ollama / OpenAI-compatible LLM endpoints for the web dashboard."""

from __future__ import annotations

import json
from typing import Any, Literal

import aiohttp

from meta_mcp.services.base import MetaMCPService

Provider = Literal["ollama", "lmstudio", "openai"]


class LocalLLMService(MetaMCPService):
    """Server-side bridge so the browser avoids CORS on localhost inference APIs."""

    @staticmethod
    def _normalize_base(base_url: str) -> str:
        return (base_url or "").strip().rstrip("/")

    async def list_models(self, provider: str, base_url: str) -> dict[str, Any]:
        provider_key = (provider or "ollama").strip().lower()
        base = self._normalize_base(base_url)
        if not base:
            return self.create_response(False, "base_url is required")

        timeout = aiohttp.ClientTimeout(total=30)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                if provider_key == "ollama":
                    url = f"{base}/api/tags"
                    async with session.get(url) as resp:
                        if resp.status != 200:
                            body = await resp.text()
                            return self.create_response(
                                False,
                                f"Ollama returned HTTP {resp.status}",
                                {"detail": body[:500]},
                            )
                        data = await resp.json()
                    models = [
                        {
                            "id": m.get("name", ""),
                            "object": "model",
                            "created": 0,
                            "owned_by": "ollama",
                        }
                        for m in (data.get("models") or [])
                        if m.get("name")
                    ]
                else:
                    url = f"{base}/v1/models"
                    async with session.get(url) as resp:
                        if resp.status != 200:
                            body = await resp.text()
                            return self.create_response(
                                False,
                                f"OpenAI-compatible API returned HTTP {resp.status}",
                                {"detail": body[:500]},
                            )
                        data = await resp.json()
                    models = list(data.get("data") or [])

            return self.create_response(
                True,
                f"Discovered {len(models)} model(s)",
                {"models": models, "provider": provider_key, "base_url": base},
            )
        except aiohttp.ClientError as exc:
            return self.create_response(
                False,
                f"Cannot reach {provider_key} at {base}: {exc!s}",
                {"hint": "Start Ollama or LM Studio and verify the base URL."},
            )

    async def chat(
        self,
        provider: str,
        base_url: str,
        model: str,
        messages: list[dict[str, str]],
    ) -> dict[str, Any]:
        provider_key = (provider or "ollama").strip().lower()
        base = self._normalize_base(base_url)
        model_name = (model or "").strip()
        if not base:
            return self.create_response(False, "base_url is required")
        if not model_name:
            return self.create_response(
                False,
                "model is required  run Discovery on Settings and select a model",
            )
        if not messages:
            return self.create_response(False, "messages cannot be empty")

        timeout = aiohttp.ClientTimeout(total=300)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                if provider_key == "ollama":
                    url = f"{base}/api/chat"
                    payload = {"model": model_name, "messages": messages, "stream": False}
                    async with session.post(url, json=payload) as resp:
                        if resp.status != 200:
                            body = await resp.text()
                            return self.create_response(
                                False,
                                f"Ollama chat HTTP {resp.status}",
                                {"detail": body[:500]},
                            )
                        data = await resp.json()
                    content = (data.get("message") or {}).get("content") or ""
                else:
                    url = f"{base}/v1/chat/completions"
                    payload = {"model": model_name, "messages": messages, "stream": False}
                    async with session.post(url, json=payload) as resp:
                        if resp.status != 200:
                            body = await resp.text()
                            return self.create_response(
                                False,
                                f"Chat API HTTP {resp.status}",
                                {"detail": body[:500]},
                            )
                        data = await resp.json()
                    choices = data.get("choices") or []
                    content = ""
                    if choices:
                        content = (choices[0].get("message") or {}).get("content") or ""

            return self.create_response(
                True,
                "Chat completion",
                {"content": content, "model": model_name, "provider": provider_key},
            )
        except aiohttp.ClientError as exc:
            return self.create_response(False, f"Chat request failed: {exc!s}")

    async def chat_with_tools(
        self,
        provider: str,
        base_url: str,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Chat with function-calling.

        Returns reply plus normalized tool_calls [{id, name, arguments(dict)}].
        Empty tool_calls = final answer. Ollama native (/api/chat) and
        OpenAI-compatible (/v1/chat/completions) wire formats are normalized
        to the same shape.
        """
        provider_key = (provider or "ollama").strip().lower()
        base = self._normalize_base(base_url)
        model_name = (model or "").strip()
        if not base:
            return self.create_response(False, "base_url is required")
        if not model_name:
            return self.create_response(
                False,
                "model is required — run Discovery on Settings and select a model",
            )
        if not messages:
            return self.create_response(False, "messages cannot be empty")

        timeout = aiohttp.ClientTimeout(total=300)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                if provider_key == "ollama":
                    url = f"{base}/api/chat"
                    payload: dict[str, Any] = {
                        "model": model_name,
                        "messages": messages,
                        "tools": tools,
                        "stream": False,
                    }
                    async with session.post(url, json=payload) as resp:
                        if resp.status != 200:
                            body = await resp.text()
                            return self.create_response(
                                False,
                                f"Ollama chat HTTP {resp.status}",
                                {"detail": body[:500]},
                            )
                        data = await resp.json()
                    msg = data.get("message") or {}
                    calls: list[dict[str, Any]] = []
                    for i, tc in enumerate(msg.get("tool_calls") or []):
                        fn = tc.get("function", {})
                        args = fn.get("arguments", {})
                        if isinstance(args, str):
                            try:
                                args = json.loads(args)
                            except json.JSONDecodeError:
                                args = {"_raw": args}
                        if not isinstance(args, dict):
                            args = {"_raw": str(args)}
                        calls.append({"id": f"call_{i}", "name": fn.get("name", ""), "arguments": args})
                    content = msg.get("content") or ""
                else:
                    url = f"{base}/v1/chat/completions"
                    payload = {"model": model_name, "messages": messages, "tools": tools}
                    async with session.post(url, json=payload) as resp:
                        if resp.status != 200:
                            body = await resp.text()
                            return self.create_response(
                                False,
                                f"Chat API HTTP {resp.status}",
                                {"detail": body[:500]},
                            )
                        data = await resp.json()
                    choices = data.get("choices") or []
                    content = ""
                    calls = []
                    if choices:
                        msg = choices[0].get("message") or {}
                        content = msg.get("content") or ""
                        for i, tc in enumerate(msg.get("tool_calls") or []):
                            fn = tc.get("function", {})
                            raw_args = fn.get("arguments") or "{}"
                            try:
                                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
                            except json.JSONDecodeError:
                                args = {"_raw": raw_args}
                            if not isinstance(args, dict):
                                args = {"_raw": str(args)}
                            calls.append(
                                {"id": tc.get("id", f"call_{i}"), "name": fn.get("name", ""), "arguments": args}
                            )

            return self.create_response(
                True,
                "Chat with tools completed",
                {"content": content, "tool_calls": calls, "model": model_name, "provider": provider_key},
            )
        except aiohttp.ClientError as exc:
            return self.create_response(False, f"Chat request failed: {exc!s}")
