"""Routing models for the dynamic capability router."""

from typing import Any

from pydantic import BaseModel, Field


class ServerEndpoint(BaseModel):
    """A reachable MCP server endpoint in the fleet."""

    server_name: str = Field(description="Fleet server name, e.g. arxiv-mcp")
    host: str = Field(default="127.0.0.1", description="Bind address")
    port: int | None = Field(default=None, description="HTTP port, if dual-transport")
    command: str | None = Field(default=None, description="Stdio launch command, e.g. uv run arxiv-mcp-server")
    cwd: str | None = Field(default=None, description="Working directory for the command")
    transport: str = Field(default="http", description="http | stdio")


class ToolMapping(BaseModel):
    """A tool name mapped to its fleet server endpoint."""

    tool_name: str = Field(description="Tool name as registered in the MCP server")
    server: ServerEndpoint = Field(description="Target server endpoint")
    description: str | None = Field(default=None, description="Tool description from schema")
    input_schema: dict[str, Any] | None = Field(default=None, description="JSON Schema for parameters")
    last_seen: float | None = Field(default=None, description="Unix timestamp of last index")
    status: str = Field(default="unknown", description="online | offline | unknown")


class RouteRequest(BaseModel):
    """A routing request from the agent."""

    tool_name: str = Field(description="Target MCP tool name")
    arguments: dict[str, Any] | None = Field(default_factory=dict, description="Tool parameters")
    target_server: str | None = Field(default=None, description="Explicit server override (optional)")


class RouteResult(BaseModel):
    """Routing result returned to the agent."""

    success: bool = Field(description="Whether the tool call succeeded")
    tool_name: str = Field(description="Tool that was invoked")
    server: str = Field(description="Server that handled the call")
    result: Any = Field(default=None, description="Tool return payload")
    latency_ms: float = Field(default=0.0, description="Round-trip latency in milliseconds")
    error: str | None = Field(default=None, description="Error message on failure")
    suggestions: list[str] | None = Field(default=None, description="Recovery suggestions")


class IndexStats(BaseModel):
    """Capability index health statistics."""

    total_tools: int = Field(default=0, description="Total tool entries indexed")
    total_servers: int = Field(default=0, description="Distinct server count")
    online_count: int = Field(default=0, description="Servers confirmed reachable")
    offline_count: int = Field(default=0, description="Servers confirmed unreachable")
    last_full_index: float | None = Field(default=None, description="Timestamp of last full re-index")
