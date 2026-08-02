# Harness Generation — CLI-Anything Integration

Auto-generate FastMCP 3.4+ servers from existing Python source code using
methodology adapted from the CLI-Anything 7-phase harness workflow.

**Reference:** [CLI-Anything: Towards Agent-Native Computer Use](https://arxiv.org/abs/2606.03854)  
Yuhao Yang, Tianyu Fan, Chao Huang. HKUDS Lab. June 2026.  
**License:** Apache 2.0 — [github.com/HKUDS/CLI-Anything](https://github.com/HKUDS/CLI-Anything)  
**Fleet integration plan:** `mcp-central-docs/projects/CLI_ANYTHING_INTEGRATION_PLAN.md`

---

## Concept

CLI-Anything proposes that the dominant GUI-agent paradigm (screenshot -> click -> observe)
is fundamentally misaligned with how LLMs work best. Instead of forcing agents to navigate
pixel-based UIs, the paper argues for **agent-native interfaces**: structured commands,
explicit state, deterministic feedback.

Their methodology is a 7-phase workflow for an AI coding agent to read a target application's
source code and produce a Python Click CLI harness. The fleet adaptation generates
**FastMCP 3.4+ servers with portmanteau tools** instead of Click CLIs, and adds fleet-specific
curation rules, domain grouping, and Prefab UI surfaces.

---

## Adapted Workflow

| CLI-Anything Phase | Fleet Adaptation | Tool |
|---|---|---|
| **Phase 0-1**: Source acquisition + codebase analysis | AST walk of Python source to extract function signatures, class hierarchies, CLI argument definitions | `harness_analyze` |
| **Phase 2**: CLI architecture design | Domain grouping (same-file heuristic), portmanteau tool structure, backend strategy detection | `harness_analyze` |
| **Phase 3**: Implementation | FastMCP server generation: portmanteau tools with `operation: Literal[...]`, Prefab cards, SKILL.md, dual transport | `harness_generate` |
| **Phase 4-5**: Test planning + implementation | Test stubs per tool group (not yet automated) | — |
| **Phase 6-6.5**: Test documentation + SKILL.md generation | SKILL.md and Prefab status card auto-generated from spec | `harness_generate` |
| **Phase 7**: Packaging | PyInstaller spec, mcpb manifest, justfile | `harness_generate` (with `include_nsis`) |

---

## Fleet Extensions Beyond CLI-Anything

| Extension | What it adds |
|-----------|-------------|
| **Curation rules** | Drops private helpers, getters/setters, stubs, test files. `full=True` exposes everything. |
| **Domain grouping** | Groups extracted functions by source file stem, produces `ToolGroup` objects. |
| **Backend detection** | Auto-detects subprocess/REST API/direct-import/CLI-wrapper strategies. |
| **Portmanteau output** | Generates `operation: Literal[...]` discriminators per the fleet tool design standard. |
| **Prefab UI cards** | `show_*_status_card` Prefab surface for chat-based UIs. |
| **Gap analysis** | `harness_refine` diffs generated servers against updated source (non-destructive). |
| **SOTA docstrings** | Generated docstrings include `[RATIONALE]`, `## Operations`, `## Return Format`, `## Examples`. |

---

## Tools

### `harness_analyze`

Reads Python source, extracts all public function signatures, groups them by domain,
detects backend strategy, and produces a `ToolSurfaceSpec`. Supports curation
(full=False, default) which drops stubs, getters, private helpers, and test files.

```
harness_analyze(source_path="D:/tools/my-cli", source_type="local")
  -> ToolSurfaceSpec with 5 tool groups, 12 operations, backend: subprocess
```

### `harness_generate`

Consumes a `ToolSurfaceSpec` and writes a complete FastMCP 3.4+ server to disk.
Generates ~23 files: portmanteau tools, Prefab cards, SKILL.md, backend strategy module,
dual transport, mcpb manifest.

```
harness_generate(spec_dict=spec, target_path="D:/repos/my-server")
  -> 23 files, 3 tool groups, 8 operations
```

### `harness_refine`

Compares the generated server's tool surface against a fresh `harness_analyze` of
the original source. Reports missing groups and operations. Can add missing tools
non-destructively (never modifies existing files).

```
harness_refine(operation="gap", server_path="./output", source_path="./src")
  -> GapReport with 2 missing groups, 5 missing operations
harness_refine(operation="add", server_path="./output", source_path="./src")
  -> Added 2 tool groups
```

---

## Attribution

This integration is adapted from:

> **CLI-Anything: Towards Agent-Native Computer Use**  
> Yuhao Yang, Tianyu Fan, Chao Huang  
> arXiv:2606.03854, June 2026  
> https://github.com/HKUDS/CLI-Anything — Apache 2.0

The 7-phase workflow methodology is used with modifications for the FastMCP ecosystem:
portmanteau tool generation instead of Click CLIs, Prefab UI instead of REPL skins,
and fleet-specific curation rules instead of full-exposure generation.
