# Spec Kit Integration — GitHub's SDD Toolkit

**Added:** 2026-07-03
**Upstream:** [github/spec-kit](https://github.com/github/spec-kit) (MIT license)
**Installed via:** `uv tool install specify-cli --from git+https://github.com/github/spec-kit.git`
**Fleet doc:** `mcp-central-docs/integrations/spec-kit.md`

---

## Overview

MetaMCP integrates GitHub's **Spec Kit** — a Spec-Driven Development (SDD) toolkit that
replaces ad-hoc "vibe coding" with a structured, artifact-driven workflow. Instead of a
single prompt that generates code directly, SDD breaks development into seven phases, each
producing a persistent, version-controlled Markdown artifact:

```
constitution → specify → clarify → plan → tasks → implement
                                                      ↓
                                              converge (post-impl gap analysis)
```

This is complementary to MetaMCP's existing `scaffold_ops(operation='mcp_server')` which
generates fleet-standard templates directly. Spec Kit front-loads planning — it helps you
decide *what* to build before the template generator builds it.

---

## How It Works in MetaMCP

### Webapp (Builders page)

The Builders page has a **Spec Kit (SDD)** card (Rocket icon, cyan accent). Clicking opens
a dedicated modal with:

| Field | Description |
|-------|-------------|
| Project Name | Directory name for the new project |
| Output Path | Parent directory (e.g., `D:\Dev\repos`) |
| AI Coding Agent | OpenCode (default), Claude Code, GitHub Copilot, Cursor, Gemini CLI |

On submit, the frontend calls `POST /api/v1/scaffolding/create` with `template_type: "spec_kit"`
and `features.ai_integration`. The backend runs:

```powershell
specify init <project_name> --ai <integration> --here
```

This scaffolds a project directory at `{output_path}/{project_name}/` containing:

```
{project_name}/
├── .specify/
│   ├── memory/
│   │   └── constitution.md          # Created by /speckit.constitution
│   ├── scripts/
│   │   └── bash/
│   │       ├── check-prerequisites.sh
│   │       ├── common.sh
│   │       ├── create-new-feature.sh
│   │       ├── setup-plan.sh
│   │       └── setup-tasks.sh
│   └── templates/
│       ├── plan-template.md
│       ├── spec-template.md
│       └── tasks-template.md
└── .opencode/commands/              # Or .claude/commands/, .github/copilot-instructions.md
    ├── speckit.constitution.md
    ├── speckit.specify.md
    ├── speckit.clarify.md
    ├── speckit.plan.md
    ├── speckit.analyze.md
    ├── speckit.checklist.md
    ├── speckit.tasks.md
    ├── speckit.implement.md
    ├── speckit.converge.md
    └── speckit.taskstoissues.md
```

### MCP Tool

```python
scaffold_ops(
    operation="spec_kit",
    project_name="my-server",
    output_path="D:\\Dev\\repos",
    features={"ai_integration": "opencode"},
)
```

---

## The SDD Workflow (7 Phases)

### 1. `/speckit.constitution`
Establish project governing principles — coding standards, test requirements, performance
goals, UX consistency. Output: `.specify/memory/constitution.md`

### 2. `/speckit.specify`
Describe **what** you want to build — user stories, functional requirements, acceptance
criteria. No tech stack. Output: `specs/{feature}/spec.md`

### 3. `/speckit.clarify`
Structured Q&A to resolve underspecified areas **before** planning. Sequential, coverage-based
questioning that records answers in a Clarifications section.

### 4. `/speckit.plan`
Declare tech stack and architecture. Produces implementation detail documents:
`plan.md`, `data-model.md`, `contracts/`, `research.md`, `quickstart.md`

### 5. `/speckit.analyze`
Cross-artifact consistency & coverage analysis between spec, plan, and tasks.

### 6. `/speckit.tasks`
Break the plan into dependency-ordered, actionable tasks with file paths and parallel
execution markers `[P]`. Output: `specs/{feature}/tasks.md`

### 7. `/speckit.implement`
Execute all tasks in dependency order. Validates prerequisites exist, then iterates
through the task list.

### Optional: `/speckit.converge`
Post-implementation gap analysis — compares codebase against spec/plan/tasks and appends
remaining work as new tasks.

---

## When to Use Spec Kit vs. Traditional Scaffolding

| Use Spec Kit when | Use scaffold_ops(operation='mcp_server') when |
|---|---|
| Greenfield project — no existing codebase | You know exactly what you need (standard MCP server) |
| Complex feature — multi-file, multi-endpoint | Single-file or simple feature |
| Team handoffs — spec survives agent changes | Rapid hot-reload iteration (Playwright loop) |
| Compliance — need documented traceability | Exploratory spike |
| IDE-hopping — spec Markdown travels with you | Trivial change (update dep, add docstring) |

### Hybrid approach (recommended)

1. Use **Spec Kit** to define the spec and plan
2. Layer **`scaffold_ops(operation='mcp_server')`** for fleet-standard files (justfile, llms.txt, glama.json)
3. Use **`harness_generate`** to auto-generate tool scaffolding from a Python API surface
4. Run **fleet verification gates** (ruff, tsc --noEmit, pytest, cua-nsis-test)

---

## Supported AI Integrations

| Integration | Spec Kit flag | What it generates |
|-------------|-------------|-------------------|
| **OpenCode** | `--ai opencode` | `.opencode/commands/speckit.*.md` |
| **Claude Code** | `--ai claude` | `.claude/commands/speckit.*.md` |
| **GitHub Copilot** | `--ai copilot` | `.github/prompts/speckit.*.prompt.md` |
| **Cursor** | `--ai cursor` (via Claude) | `.cursor/commands/speckit.*.md` |
| **Gemini CLI** | `--ai gemini` | Agent commands directory |

OpenCode is the fleet default since it's provider-agnostic, MIT-licensed, and supports
local Ollama models on the RTX 4090.

---

## Extensions, Presets & Bundles

Spec Kit is composable. Beyond the core SDD commands, you can layer:

- **Extensions** — add new commands (e.g., Jira integration, compliance checklists)
- **Presets** — customize templates (e.g., enforce fleet stack: React/Vite/Bun/Tailwind/Zustand/FastMCP)
- **Bundles** — role-based curated sets (product manager, security researcher, developer)

```powershell
specify extension search     # Browse available
specify preset add <name>    # Install a preset
specify bundle install <id>  # Full role setup
```

A **fleet preset** (future) would customize Spec Kit's templates to auto-generate fleet-standard
files (justfile, llms.txt, glama.json, start.ps1, etc.) as part of the plan/implement phases.

---

## Relationship to Fleet Workflow

The fleet's `workflow_2026.md` already practices a 4-phase loop:

```
EXPLORE → PLAN → IMPLEMENT → COMMIT & VERIFY
```

Spec Kit formalizes this and **persists each phase to disk**:

| Fleet Phase | Spec Kit Equivalent | Advantage |
|-------------|-------------------|-----------|
| EXPLORE | `/speckit.specify` + `/speckit.clarify` | Structured spec file, coverage Q&A |
| PLAN | `/speckit.plan` + `/speckit.analyze` | Data model, contracts, research, validation |
| IMPLEMENT | `/speckit.tasks` + `/speckit.implement` | Dependency-ordered tasks with `[P]` markers |
| VERIFY | `/speckit.converge` | Gap analysis between codebase and plan |

What Spec Kit adds that the fleet workflow doesn't:
- **Persistent artifact chain** — plans survive context resets
- **Cross-artifact validation** — plan covers every spec requirement
- **GitHub issue generation** — `/speckit.taskstoissues`
- **Extensions/presets ecosystem** — community-contributed workflows

What the fleet already has that Spec Kit doesn't:
- Playwright E2E testing (`playwright_e2e_sota.md`)
- CUA-NSIS smoke testing (`cua_nsis_smoke_testing.md`)
- Tauri/NSIS build pipeline
- Fleet port registry & webapp SLOP

---

## Prerequisites

- Python 3.11+ (met — fleet has 3.13)
- `uv` (met — fleet standard)
- `specify-cli` installed via `uv tool install`
- Git (met)

---

## Links

- [github/spec-kit](https://github.com/github/spec-kit) — upstream repo
- [Spec Kit docs](https://github.github.io/spec-kit/) — official documentation
- [mcp-central-docs/integrations/spec-kit.md](../../mcp-central-docs/integrations/spec-kit.md) — fleet integration doc
- [Fleet workflow (workflow_2026.md)](../../mcp-central-docs/standards/rules/workflow_2026.md)

---

*Last updated: 2026-07-03*
