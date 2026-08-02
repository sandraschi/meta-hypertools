# Meta MCP: Technical Debt & Future Roadmap

This document provides a critical assessment of the current Meta MCP codebase and outlines strategic directions for future development, focusing on modularity, functionality gaps, and expansion opportunities.

## I. Technical Debt: Current State & Red Flags

### 1. The "God Server" Pattern (`mcp_server.py`)
- **Debt Level**: **CRITICAL**
- **Analysis**: At over 2,200 lines, `mcp_server.py` is an architectural bottleneck. It combines server initialization, transport handling, complex portmanteau tool logic, and schema definitions in a single file.
- **Risk**: High maintenance cost, potential for regression during small changes, and violation of the Single Responsibility Principle.
- **Recommendation**: Refactor into a decentralized registration pattern. Move tool logic to `services/` and tool definitions to `tools/registration/`.

### 2. Service Inconsistency
- **Debt Level**: **MODERATE**
- **Analysis**: Several service modules exist in `src/meta_mcp/services/` (e.g., `discovery.py`, `sota.py`), but `mcp_server.py` often implements parallel logic or interacts with them inconsistently.
- **Recommendation**: Unify logic into these service classes. Tools should merely be "thin" wrappers over service methods.

### 3. Hardcoded Assumptions
- **Debt Level**: **LOW/MODERATE**
- **Analysis**: While recently improved, many tools still make assumptions about the host environment (e.g., location of Claude config, default dev roots like `d:/Dev/repos`).
- **Recommendation**: Implement a formal `Settings` class (Pydantic-based) that loads from a centralized `meta-mcp.json` or environment variables.

---

## II. Functionality Gaps

### 1. SOTA "Fixer" Limitation
- **Current**: Meta MCP is excellent at *detecting* SOTA non-compliance and *fixing* Unicode issues (EmojiBuster).
- **Gap**: It lacks automated fixes for other common violations, such as missing tool docstrings, incorrect export patterns, or suboptimal Pydantic models.
- **Opportunity**: A `sota_fix` operation that performs AST-based transformations to bring code into compliance.

### 2. Multi-IDE SOTA Sync
- **Current**: Individual tools can check client integration state.
- **Gap**: No automated way to *propagate* a server configuration change across all installed clients (e.g., updating a port once and having it reflect in Claude, Cursor, and Zed simultaneously).

### 3. mcpb (MCP Bundle) Lifecycle
- **Current**: Minimal support for the `.mcpb` standard mentioned in documents.
- **Gap**: No tools for packaging, signing, or validating MCP bundles for distribution.

---

## III. Expansion Opportunities

### 1. Performance Profiler
A tool to automatically run benchmarks against MCP tools, measuring:
- Latency (p50, p99)
- Memory peak during execution
- Argument validation overhead

### 2. Interactive Scaffolding Wizard
Instead of static templates, an interactive `ctx.elicit()` based wizard that asks about:
- Persistence requirements
- Desired transports (Stdio vs. HTTP)
- Required authentication layers
- Generation of matching `mcp_config.json` snippets

### 3. Security Auditor
An automated scanner for MCP-specific security risks:
- Path traversal in file-based tools
- Command injection in PowerShell tools
- Schema exposure of sensitive internal fields

### 4. Cross-System Bridge
Tools to facilitate service discovery and tool execution across *different* host machines on a local network (e.g., running a tool on a Linux desktop from a Windows laptop).

---

> [!TIP]
> Prioritizing the **Modularization of mcp_server.py** will yield the highest ROI for future expansions by allowing multiple developers to work on tool suites independently without merge conflicts in a single giant file.
