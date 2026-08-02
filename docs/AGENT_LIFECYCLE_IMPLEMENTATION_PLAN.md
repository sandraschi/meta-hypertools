# Agent Lifecycle Implementation Plan

**Target**: meta-mcp
**Date**: 2026-02-08
**Status**: Plan – implement today

---

## Goal

Add agent lifecycle tools to meta-mcp: start, deploy, await agents (and later swarms). meta-mcp already orchestrates MCP servers and tool execution; agent orchestration is the next meta layer.

---

## Architecture

### New Components

| Component | Purpose |
|-----------|---------|
| `AgentService` | Manages agent state, spawns background tasks, tracks completion |
| `agent_orchestration` registry | Registers agent tools with FastMCP |
| `AgentState` model | agent_id, status, started_at, completed_at, result, error, agent_type, params |

### Tool Suite: Agent Orchestration

| Tool | Purpose |
|------|---------|
| `start_agent` | Start an agent; returns agent_id, status, estimated_wait_seconds |
| `get_agent_status` | Poll status (running, completed, failed); non-blocking |
| `get_agent_report` | Fetch completion report when status=completed |
| `stop_agent` | Terminate running agent |
| `list_agents` | List all agents with status |

### Response Format (ANTIPATTERN compliance)

No vague fluff. Structured returns with:

- `agent_id`, `status`, `message` (concrete)
- `recovery_options` when applicable
- `estimated_wait_seconds` for long runners
- Clear instruction: "Wait for completion before get_agent_report. Do not retry immediately."

---

## Phase 1: MVP (Today)

### 1.1 Agent types (MVP)

**Type A: `tool_chain`** – Run a sequence of tools on a server.

- `start_agent(agent_type="tool_chain", server_id=..., tool_calls=[{tool, params}, ...])`
- AgentService spawns asyncio task that calls `execute_server_tool` for each, collects results
- Store result in AgentState

**Type B: `server_async`** – Delegate to a server tool that returns job_id.

- `start_agent(agent_type="server_async", server_id=..., tool_name=..., params=...)`
- Call `execute_server_tool`; if response has `agent_id`/`job_id`, store and poll via server's status tool
- Requires convention: server exposes `get_agent_status(job_id)` or similar

For today: **Type A only** (tool_chain). Type B when we have a server that follows the convention.

### 1.2 Storage

- In-memory `Dict[str, AgentState]` keyed by agent_id
- agent_id = `f"agent_{uuid4().hex[:12]}"`
- No persistence for MVP; restart clears state

### 1.3 File structure

```
src/meta_mcp/
  services/
    agent_service.py      # NEW: AgentService class
  tools/
    registries/
      agent_orchestration.py   # NEW: register_agent_orchestration_tools
  models/
    agent.py             # NEW: AgentState, AgentStatus enum (or in agent_service)
```

### 1.4 Integration

- Add `register_agent_orchestration_tools` to `mcp_server.py`
- Add to registry: `registry.register_suite("agent_orchestration", register_agent_orchestration_tools)`
- Add docs entry in `docs/tools/agent-orchestration.md`

---

## Phase 2: Persistence + More agent types

- SQLite or JSON file for AgentState
- Survive meta-mcp restart
- Type B (server_async) when we have a compliant server

---

## Phase 3: Swarms

- `start_agent_swarm(agent_type, params_list)` → multiple agent_ids
- `get_swarm_status(swarm_id)` → aggregate status
- `get_swarm_report(swarm_id)` → combined report when all complete

---

## Implementation Order (Today)

1. **AgentState model** – dataclass or Pydantic
2. **AgentService** – start (spawn task), get_status, get_report, stop, list
3. **Registry** – agent_orchestration.py with 5 tools
4. **Wire into mcp_server.py**
5. **Docs** – agent-orchestration.md
6. **Test** – manual: start_agent(tool_chain), get_status, get_report

---

## Example: start_agent return (tool_chain)

```json
{
  "success": true,
  "operation": "agent_started",
  "agent_id": "agent_a1b2c3d4e5f6",
  "status": "running",
  "message": "Agent started. Tool chain has 3 steps. Do not fetch report until status=completed.",
  "recovery_options": [
    "Poll get_agent_status(agent_id) every 10s",
    "Only call get_agent_report(agent_id) when status is 'completed'",
    "Do not retry start_agent immediately"
  ],
  "estimated_wait_seconds": 60
}
```

---

## Dependencies

- Existing: `ToolService` for execute_server_tool
- Existing: `ServerService` for server list/status
- New: `uuid` for agent_id
- New: `asyncio.create_task` for background agent execution

---

## Cross-Utilization: Dark App Factory

**Repo**: `D:\Dev\repos\dark-app-factory`

Dark App Factory implements the Software Factory pattern: Foreman (specs) -> Worker (code) -> DTU (mocks) -> Judge (satisfaction). Each phase is long-running (LLM calls, file I/O). Natural fit for meta-mcp agents.

### Integration Options

| Direction | Mechanism | Benefit |
|-----------|-----------|---------|
| **meta-mcp runs Dark App Factory as agent** | `start_agent(agent_type="dark_factory", vibe_path=..., output_dir=...)` spawns `factory.py run` as background task | LLM/IDE triggers full factory run via meta-mcp; waits non-blocking; fetches report (specs + code + verdict) |
| **Dark App Factory phases as agent types** | Foreman, Worker, Judge each = agent type. `start_agent(agent_type="foreman", vibe_path=...)` etc. | Granular control: run Foreman only, or Worker+Judge after manual spec edit |
| **meta-mcp tools for Dark App Factory CLI** | meta-mcp exposes `run_dark_factory`, `foreman_plan`, `worker_build`, `judge_verify` | Orchestrate factory from any MCP client (Cursor, Claude) without running python scripts |
| **DTU as MCP server** | Expose `dtu/main.py` as FastMCP server with tools: `mock_stripe`, `mock_auth` | meta-mcp starts DTU; Worker/Judge call mocks via meta-mcp tool execution |
| **Worker uses meta-mcp** | Worker calls `execute_server_tool(advanced-memory, adn_search, {...})` for pattern lookup | Knowledge-augmented code generation; write research notes to advanced-memory during build |

### Agent Type: `dark_factory`

```python
start_agent(
    agent_type="dark_factory",
    vibe_path="vibe.md",
    specs_path="specs/specs.md",
    output_dir="output",
)
# Returns: agent_id, estimated_wait_seconds=300 (Foreman ~1min, Worker ~5min, Judge ~1min)
# get_agent_report: specs path, output dir, verdict, satisfaction score
```

### Implementation Order

1. MVP: meta-mcp `tool_chain` agent (no dark-app-factory coupling)
2. Add `dark_factory` agent type: subprocess or asyncio wrapper around `factory.py run`
3. Later: DTU as MCP server; Worker MCP client for advanced-memory
