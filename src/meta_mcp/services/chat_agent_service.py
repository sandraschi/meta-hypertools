"""Agentic chat loop for the fleet control center.

Builds the system preprompt (orientation + personality + live tool catalog),
runs a bounded function-call loop against the local/cloud LLM, executes called
tools in-process via ToolService, and returns the final reply with a trace.

This is the first real agent loop in the fleet: earlier chat surfaces
(incl. the arxiv-mcp pilot) only do skills-in-preprompt text chat.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from meta_mcp.services.base import MetaMCPService
from meta_mcp.services.local_llm_service import LocalLLMService
from meta_mcp.services.tool_service import ToolService

PERSONALITIES: list[dict[str, str]] = [
    {
        "id": "mcp-expert",
        "label": "MCP Expert",
        "prompt": (
            "You are an expert on MCP servers and this fleet. Explain what tools do, "
            "chain them to answer questions, and teach as you go. Prefer read-only "
            "operations (list/stats/get/status) for questions; narrate what mutating "
            "operations did after running them."
        ),
    },
    {
        "id": "fleet-operator",
        "label": "Fleet Operator",
        "prompt": (
            "You are a fleet operator. Act first, explain briefly after. Keep answers "
            "terse: what you ran, what it returned, next suggested step. Ask before "
            "fleet-wide mutating operations (scaffolding, bulk deletes, restarts)."
        ),
    },
    {
        "id": "analyst",
        "label": "Analyst",
        "prompt": (
            "You are a careful analyst. Gather evidence with read-only tools before "
            "concluding anything. Cite tool names and scores. Never claim an action "
            "was taken unless the tool trace shows it."
        ),
    },
]

SYSTEM_BASE = (
    "You are MetaMCP, the fleet control-center assistant running on Goliath "
    "(Windows 11, {tz}; local time {now}). You operate the local MCP tool stack: "
    "server discovery and probing, scaffolding, analysis, assess reports, "
    "scheduler, and fleet operations. {tool_count} tools are available as "
    "functions — call them when the user asks about the fleet instead of "
    "guessing. Answer from tool results, never from memory. Be concise."
)

MAX_RESULT_CHARS = 4000
TRACE_PREVIEW_CHARS = 300


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit] + "…[truncated]"


class ChatAgentService(MetaMCPService):
    """System prompt building + bounded tool-call loop."""

    def __init__(self) -> None:
        super().__init__()
        self._llm = LocalLLMService()
        self._tools = ToolService()

    async def _catalog(self) -> list[dict[str, Any]]:
        result = await self._tools.get_mcp_catalog()
        data = result.get("result") or result.get("data") or {}
        return [t for t in data.get("tools", []) if t.get("name")]

    def _tool_definitions(self, catalog: list[dict[str, Any]]) -> list[dict[str, Any]]:
        defs = []
        for t in catalog:
            schema = t.get("inputSchema") or t.get("parameters")
            if not isinstance(schema, dict) or "properties" not in schema:
                schema = {"type": "object", "properties": {}}
            desc = str(t.get("description") or "")[:400]
            defs.append(
                {"type": "function", "function": {"name": t["name"], "description": desc, "parameters": schema}}
            )
        return defs

    def _orientation(self, tool_count: int) -> str:
        now = datetime.now(ZoneInfo("Europe/Vienna")).strftime("%Y-%m-%d %H:%M")
        return SYSTEM_BASE.format(tz="Europe/Vienna", now=now, tool_count=tool_count)

    def _system_prompt(self, personality_id: str, catalog: list[dict[str, Any]]) -> str:
        base = self._orientation(len(catalog))
        persona = next((p for p in PERSONALITIES if p["id"] == personality_id), PERSONALITIES[0])
        lines = [f"- {t['name']}: {str(t.get('description') or '').splitlines()[0][:120]}" for t in catalog]
        catalog_txt = "\n".join(lines) if lines else "(no tools registered)"
        return f"{base}\n\n## Role\n{persona['prompt']}\n\n## Tools\n{catalog_txt}"

    async def context(self) -> dict[str, Any]:
        """Personalities + compact tool catalog for chat clients."""
        catalog = await self._catalog()
        compact = [
            {"name": t["name"], "description": str(t.get("description") or "").splitlines()[0][:160]} for t in catalog
        ]
        return self.create_response(
            True,
            f"Chat context: {len(PERSONALITIES)} personalities, {len(catalog)} tools",
            {
                "personalities": PERSONALITIES,
                "tools": compact,
                "tool_count": len(catalog),
                "orientation": self._orientation(len(catalog)),
            },
        )

    async def run(
        self,
        provider: str,
        base_url: str,
        model: str,
        history: list[dict[str, Any]],
        personality_id: str = "mcp-expert",
        max_iterations: int = 5,
    ) -> dict[str, Any]:
        """Run the agent loop. Returns reply + trace + iterations."""
        max_iterations = max(1, min(int(max_iterations or 5), 10))
        catalog = await self._catalog()
        if not catalog:
            return self.create_response(False, "No tools registered — agent mode needs the tool catalog")
        system = self._system_prompt(personality_id, catalog)
        definitions = self._tool_definitions(catalog)
        is_ollama = (provider or "ollama").strip().lower() == "ollama"

        messages: list[dict[str, Any]] = [{"role": "system", "content": system}]
        messages.extend(history or [])
        trace: list[dict[str, Any]] = []
        reply = ""

        for iteration in range(1, max_iterations + 1):
            res = await self._llm.chat_with_tools(provider, base_url, model, messages, definitions)
            if not res.get("success"):
                return self.create_response(
                    False, res.get("message", "LLM call failed"), {"trace": trace, "iterations": iteration}
                )
            data = res.get("data") or {}
            reply = data.get("content") or data.get("reply") or ""
            calls = data.get("tool_calls") or []
            if not calls:
                return self.create_response(
                    True, "Agent loop complete", {"reply": reply, "trace": trace, "iterations": iteration}
                )
            if is_ollama:
                messages.append(
                    {
                        "role": "assistant",
                        "content": reply,
                        "tool_calls": [{"function": {"name": c["name"], "arguments": c["arguments"]}} for c in calls],
                    }
                )
            else:
                messages.append(
                    {
                        "role": "assistant",
                        "content": reply,
                        "tool_calls": [
                            {
                                "id": c["id"],
                                "type": "function",
                                "function": {"name": c["name"], "arguments": json.dumps(c["arguments"])},
                            }
                            for c in calls
                        ],
                    }
                )
            for call in calls:
                name = call.get("name", "")
                args = call.get("arguments") or {}
                exec_res = await self._tools.execute_tool("metaops", name, args)
                ok = bool(exec_res.get("success"))
                payload = exec_res.get("result") or exec_res.get("data") or exec_res
                result_txt = _truncate(json.dumps(payload, default=str), MAX_RESULT_CHARS)
                trace.append({"name": name, "args": args, "ok": ok, "preview": result_txt[:TRACE_PREVIEW_CHARS]})
                if is_ollama:
                    messages.append({"role": "tool", "content": result_txt})
                else:
                    messages.append({"role": "tool", "tool_call_id": call.get("id", ""), "content": result_txt})

        return self.create_response(
            True,
            f"Agent loop stopped after {max_iterations} iterations",
            {"reply": reply, "trace": trace, "iterations": max_iterations},
        )
