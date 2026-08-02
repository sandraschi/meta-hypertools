# Remote repository inspiration suite

**Study public GitHub repos from inside MetaMCP** — filtered trees, token-safe file fetches, and architecture prompts for agents. No local clone; read for **patterns**, not copy-paste.

## Credit

Design and behavior are adapted from **[Repomuse](https://www.npmjs.com/package/repomuse)** (MIT, [praveene3127](https://www.npmjs.com/~praveene3127)) — an MCP server that fetches public GitHub repositories as inspiration context. MetaMCP implements the same workflow **natively in Python** (`aiohttp` + GitHub REST / raw) so the fleet does not need a separate `npx repomuse` process.

## When to use

| Need | Use |
|------|-----|
| Explore **any public** OSS repo (e.g. Calibre, FastAPI) | `inspire_repo` or `inspire_repo_*` |
| Pack **local** fleet repo for LLM context | [Repository packing](repo-packing.md) (`pack_mcp_*`) |
| Live full-tree digest URL | [git-github-mcp](https://github.com/sandraschi/git-github-mcp) `gitingest_*` or [Gitingest](https://gitingest.com) |
| Versioned fleet entry point | Repo `llms.txt` + `llms-full.txt` |

## Tools

### `inspire_repo` (portmanteau — preferred)

| `operation` | Purpose |
|-------------|---------|
| `structure` | Filtered file tree |
| `files` | Explicit or auto-picked sources |
| `patterns` | Architecture study pack |
| `help` | Parameter reference |

**Shared parameters:** `url`, optional `subpath`, `branch`, `profile` (`brief` \| `standard` \| `deep`), `max_chars`, `language_hint` (files/patterns auto-pick), `include_globs`, `exclude_globs`, `target_files` (files only).

**Response (Phase A):** `data.text` (backward compatible) plus `data.chapters[]` — each `{ id, title, kind, body }` with kinds `overview`, `tree`, `manifest`, `readme`, `source`, `prompt`, `file`, `hint`. Also `data.gitingest_url`, `data.tree_cached`, `data.profile`.

**Tree cache:** Git trees are cached in-process for **5 minutes** per `owner/repo@branch` so structure → files → patterns in one session reuses one GitHub tree fetch.

### Phase B — monorepo and huge repos

When `tree_truncated_by_github` or more than **2000** source files in scope:

- `data.large_repo_mode` is true
- `data.directory_summary` — per top-level folder file counts
- `data.suggested_subpaths` — ranked folder paths to pass as `subpath`
- `data.hints[]` — truncation, gitingest, local `pack_mcp_*` guidance
- `data.suggested_language_hint` — inferred from manifest filenames in the tree (auto-used for file pick when `language_hint` omitted)
- `data.rate_limit_remaining` — from GitHub API headers when available

Structure output switches to directory summary + capped sample tree instead of a flat 500-path listing.

### Phase C — `inspire_repo_workflow`

Multi-step agentic study in one call:

1. `structure` (brief)
2. Path pick — MCP **sampling** when the host supports `ctx.sample`, else deterministic smart-pick
3. `files` for selected paths
4. `patterns` (brief)
5. Optional synthesis chapter via sampling

**Args:** `goal`, `url`, optional `subpath`, `branch`, `profile`, `max_paths` (default 5).

Returns `workflow_steps`, `selected_files`, `sampling_used`, merged `chapters[]`.

### Phase D — Prefab card, prompts, skills

| Surface | Purpose |
|---------|---------|
| `inspire_repo_structure_card` | MCP App (Prefab) for structure — metrics + badges; plain-text `content` fallback |
| `inspire_repo_help` | Standalone parameter reference (same text as `operation=help`) |
| Prompt `inspire_repo_study` | Template for goal-driven repo study |
| Prompt `meta_mcp_fleet_discovery` | Template for `help` / fleet launcher discovery |
| `resource://meta-mcp/repo-inspiration/skills` | Workflow skill markdown |
| `resource://meta-mcp/capabilities` | Short capability summary |

Disable Prefab tool registration with `META_MCP_PREFAB_APPS=0` (prompts/resources still register).

### Legacy aliases

`inspire_repo_structure`, `inspire_repo_files`, `inspire_repo_patterns` accept the same optional parameters and return the same shape.

### Profiles

| Profile | Typical use |
|---------|-------------|
| `brief` | README + manifest + ~3 sources (~40k chars) |
| `standard` | Default (~80k chars, 500 tree paths) |
| `deep` | Larger caps (~100k chars, more auto-picked files) |

## Authentication

- **Public repos:** Works without a token (GitHub **60** requests/hour per IP)
- **Higher limits / private repos:** Set `GITHUB_TOKEN` or `GH_TOKEN`, or rely on **`gh auth login`** (MetaMCP falls back to `gh auth token` when env vars are unset)
- **Do not** put expired tokens in Cursor `mcp.json` — they override `gh` and cause **401** errors

## Example prompts

- *"`inspire_repo(operation=structure, url=...)` on kovidgoyal/calibre"*
- *"`inspire_repo(operation=patterns, profile=brief, url=...)` and summarize architecture"*
- *"`inspire_repo(operation=files, subpath=src, language_hint=python, url=...)`"*

## Web dashboard

Open **Repo Inspiration** in `web_sota` (sidebar). Uses `inspire_repo` with subpath/profile controls; prefers server `chapters[]` when present, else client-side split on headings.

**Tool Lab** also exposes the same tools but renders raw JSON — use **Repo Inspiration** for human review.

## Implementation

- **Suite:** `repo_inspiration` (registered in `mcp_server.py`)
- **Service:** `src/meta_mcp/services/repo_inspiration_service.py`
- **Filters / scoring:** `src/meta_mcp/utils/github_inspiration.py`
- **Profiles / chapters:** `src/meta_mcp/utils/repo_inspiration_profiles.py`
- **Tree cache:** `src/meta_mcp/utils/repo_inspiration_cache.py`
- **UI:** `web_sota/src/pages/RepoInspiration.tsx`, `web_sota/src/utils/splitInspirationChapters.ts`
- **Prefab:** `src/meta_mcp/prefabs/repo_inspiration.py`, `src/meta_mcp/fleet_surface.py`
