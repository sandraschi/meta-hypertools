"""Serialize FastMCP ToolResult / MCP tool listings for REST responses."""

from __future__ import annotations

import json
from typing import Any


def serialize_tool_result(tr: Any) -> Any:
    """Turn a ToolResult (or similar) into JSON-serializable data."""
    if tr is None:
        return None
    if hasattr(tr, "structured_content") and tr.structured_content is not None:
        return tr.structured_content
    if hasattr(tr, "content") and tr.content:
        chunks: list[str] = []
        for c in tr.content:
            text = getattr(c, "text", None)
            if text is not None:
                chunks.append(text)
            else:
                chunks.append(str(c))
        blob = "\n".join(chunks).strip()
        if not blob:
            return None
        try:
            return json.loads(blob)
        except json.JSONDecodeError:
            return {"raw_text": blob}
    return str(tr)


def mcp_tool_to_catalog_entry(tool: Any) -> dict[str, Any]:
    """Map a FastMCP tool listing entry to catalog + DynamicForm schema."""
    name = getattr(tool, "name", None) or ""
    desc = getattr(tool, "description", None) or ""
    params = getattr(tool, "parameters", None)
    schema: dict[str, Any] | None
    if isinstance(params, dict):
        schema = params
    else:
        schema = None
    return {
        "name": name,
        "description": desc.strip(),
        "parameters": schema,
        "inputSchema": schema,
    }
