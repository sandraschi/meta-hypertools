# meta-hypertools - user guide

## Tutorial 1: scaffold your first MCP server

Goal: a standards-ready FastMCP server repo in one pass.

1. Open the dashboard Builders page, or call
   `scaffold_ops(operation="mcp_server")` with a project name and target
   directory. Answer the questionnaire: purpose, tools, wrappee (if any),
   webapp or headless.
2. Inspect the generated tree: `pyproject.toml` with uv, `src/<pkg>/`
   with portmanteau tools, `start.ps1` plus `start.bat`, `README.md`,
   `INSTALL.md`, `llms.txt`, `glama.json`, `.mcpbignore`, CI workflow,
   and `mcpb/` staging with manifest and prompts skeleton.
3. Run the gates before celebrating: `ruff check`, `ruff format --check`,
   `pytest`, and for webapps `tsc --noEmit` plus Biome. Fix everything;
   the assfix-zero bar means the first audit finds nothing critical.
4. Register the server in your IDE with `client_ops` (backed up first),
   then verify it answers: Tool Lab, execute `help`, read the overview.
5. Common mistakes: committing before writing `.gitignore` (node_modules
   and `.venv` end up tracked), hardcoding ports instead of reading the
   fleet registry, and shipping mock data in the webapp without MOCK
   badges. Each of these fails the audit; fix them now, not later.

## Tutorial 2: study a repo and steal its architecture (legally)

Goal: learn from a good repository without cloning it.

1. Repo Inspiration, Discover tab: pick a preset (FastMCP ecosystem, Tauri
   apps, RAG starters) or type a query with language and star floor.
   Check cadence (hot means pushed within a week) and rocket badges for
   young fast risers; skip archived or dormant repos for patterns.
2. Star promising repos as faves for later. Click Study this repo on the
   best candidate: run `structure` first for the filtered tree, then
   `files` on the interesting paths (profiles cap the character budget),
   then `patterns` for the architecture pack.
3. For a deeper pass, run `inspire_repo_workflow(goal=...)`: multi-step
   reasoning that ends with a scaffold recommendation naming which
   `scaffold_ops` template fits and what to change.
4. Turn insight into a server: feed the recommendation straight into
   Tutorial 1. Attribute the source repo in your README credits section;
   inspiration is not copying, and licenses still apply.

## Tutorial 3: certify a release before anyone else installs it

Goal: prove boot, install, and standards in that order.

1. Cold-start probe: run `fleet_startup_probe` (dashboard Fleet,
   Cold-start tab). It executes `start.ps1`, waits for health endpoints,
   and flags dirty consoles, 4xx/5xx, and proxy errors. Outcomes are
   `stack_ok`, `stack_degraded`, `start_failed`, or `pages_404`. Fix
   failures before continuing; a release that does not boot is not a
   release.
2. Cold-install probe: run `fleet_cold_install_probe` (default preflight
   checks `INSTALL.md` structure and release assets without installing).
   Host smoke covers Claude Desktop mcpb config and multi-IDE stdio.
   Sandbox execution generates consumer-profile install scripts for naked
   Windows validation where virtualization is available.
3. Standards audit: `analysis_ops(operation="runts")` scores the repo
   against 40-plus rules with P0/P1/P2 remediation. Fix P0s, record the
   `SOTA Score: N/100` line in both report locations, and write the
   timestamp with before/after scores.
4. Ship: pack the `.mcpb` with the fresh-stage script (wipe, recopy,
   checks, pack), verify the archive contents, attach to the release.

## Tutorial 4: operate the fleet day to day

Goal: routine ops without touching config files by hand.

1. Morning check: Dashboard hero KPIs plus heartbeat `pulse` for machine
   health (CPU, memory, ports in range). Anything red gets a `ping` to
   isolate the sick server before restarting it.
2. Recurring work belongs in the scheduler: register named tasks with an
   interval, server, tool, and parameters (for example a nightly
   `analysis_ops` runts scan). List, pause, resume, or cancel from the
   System pages; tasks persist across restarts.
3. Switch whole IDE setups with toolchains: create a preset once
   (`toolchain_ops` create), apply it to swap every client config at once.
   Client edits always back up first; validate after applying.
4. Watch token budgets before big embeddings: `token_ops` per-file and
   per-directory estimates plus context-limit checks, so a depot publish
   never blows past model limits by surprise.
5. Pack context for deep work: `pack_ops` bundles a repo into one
   LLM-ready file with a token estimate; `pack_ai` caps to a budget.

## Tutorial 5: chat with the fleet (agent mode)

Goal: let the assistant run tools conversationally, safely.

1. Settings first: run Discovery, pick a model, save. Tool-capable
   models work best (anything with `tools` in the name is a hint); small
   chat-only models answer from memory and skip tools.
2. Pick a personality: MCP Expert teaches, Fleet Operator acts tersely,
   Analyst gathers evidence and cites scores. The skill badge shows the
   live tool count the agent can see.
3. Ask fleet questions in plain language: "which repos decayed?", "probe
   the cold start of X", "what changed in the fleet today?". Read-only
   calls run immediately; the trace under each answer shows every call.
4. Mutating calls pause for approval: the amber card lists each proposed
   call with arguments. Approve selected or deny all; denials are fed
   back so the model replans instead of stalling.
5. Plain chat (agent toggle off) still gets the orientation plus role
   preprompt, so personalities work there too - just without tool calls.

## Tutorial 6: keep the knowledge base useful

Goal: standards, reports, and session docs stay current and readable.

1. Browse Fleet Standards (search, category, detail) instead of guessing
   which rule applies; link the standard, not your memory of it, when
   advising.
2. After every assfix, confirm both report copies exist: the gitignored
   snapshot and the committed `docs/assess-reports/YYYY-MM-DD.md` with
   its score line. The Assess Reports page only shows the committed copy.
3. Prune session docs older than 30 days from the Session Docs page when
   working in a private archive. The shared handbook log refuses pruning
   by design; point `SESSION_DOCS_DIR` at a private dir to manage
   deletions.
4. Publish depot runs worth keeping with `publish_mcd`; regenerable
   snapshots stay out of git by rule.

## Troubleshooting

**Dashboard shows Failed to load / 404 on a new route.** The backend
predates the frontend change: restart it (`start.ps1`, or stop port
10718 and launch `uv run --no-sync -m meta_mcp 10718`). Vite hot-reloads
the frontend by itself.

**`uv run` fails with an access-denied file lock.** The MCP stdio server
holds the venv executable. Launch the backend with `--no-sync` (safe
when dependencies did not change) instead of killing the IDE's server.

**Assess Reports page is empty but timestamps exist.** The registry reads
committed `docs/assess-reports/*.md` with score lines, not timestamps.
Re-run assfix with both report copies enabled; timestamps alone never
render.

**Chat says no model selected.** Settings, Discovery, pick a model from
the dropdown, Save config. A saved model name that no longer exists
shows a re-discovery notice in Chat itself.

**Agent mode never calls tools.** The model likely lacks function-calling
support. Switch to a tool-capable model and retry. Check the trace: zero
iterations with an immediate reply means the model answered from memory.

**Approval card appears for a harmless question.** The gate is
default-deny on unknown operations. Approve if the call is read-only in
effect, or tell the operator which operation name to add to the
read-only set after verifying it mutates nothing.

**GitHub search hits rate limits.** Set `GITHUB_TOKEN` in `.env` (30
requests per minute instead of 10). The token never leaves the server.

**Pre-commit fails on Biome formatting.** Formatting is advisory by
design in this repo; the gate runs `biome lint` only. Run the formatter
manually when convenient, never as a commit blocker.

**A probe leaves ports bound.** `Stop-FleetPortSquatters` clears the
fleet range by port ownership. Never taskkill NSSM children; use the
service manager and verify a new PID owns the port.

## Example dialogues

**Scaffolding.** Human: "I need a Python MCP server wrapping our
inventory CSVs." Assistant: runs the questionnaire (purpose, tools,
headless or webapp), calls `scaffold_ops(operation="mcp_server")`,
reports the tree, runs ruff plus pytest, registers the server in the
IDE, and shows the Tool Lab `help` output as proof of life.

**Study.** Human: "Find me a good RAG chatbot to learn from." Assistant:
searches the Local LLM preset, filters cadence hot, studies structure
then patterns of the top hit, and summarizes three portable ideas (chunk
pipeline, eval harness, streaming UI) with file references.

**Certify.** Human: "Is 0.5.2 shippable?" Assistant: runs the cold-start
probe (stack_ok with one dirty-console warning), preflights cold-install
(docs complete, bundle present), runs runts (score 72, two P1s), fixes
the P1s, re-scores to 88, writes both report copies plus timestamp, and
packs the bundle.

**Operate.** Human: "Swap my IDEs to the review toolchain and schedule a
nightly audit." Assistant: applies the toolchain preset (backs up
clients, validates), registers a nightly `analysis_ops` runts task, and
confirms both with output quotes.

**Chat triage.** Human: "Why is the fleet dashboard red?" Assistant
(agent mode): pulses heartbeat, pings the fleet, finds one stopped
server, restarts it after approval, and reports the trace: pulse, ping,
start, with the approval card shown for the restart.

## Advanced topics

**Keeping three surfaces in parity.** Every feature ships three times:
MCP tool, REST endpoint, dashboard page. The catalog at
`GET /api/v1/mcp/catalog` is the contract the Tool Lab forms render
from; if a tool works over MCP but has no REST route, dashboard users
cannot reach it, and that is a gap, not a design. When adding a tool,
register the portmanteau, add the route, add the page or card, and update
`docs/TOOLS.md` plus `llms-full.txt` in the same change.

**Authoring a portmanteau.** One tool per domain, `operation` as a
Literal discriminator, one implementation module per operation group.
Read-only operations (list, get, status, probe, search, stats) run
anywhere including the agent loop without approval; mutating operations
pause for confirmation there. Descriptions are one line plus a longer
help body; the first line is what models see in the catalog, so front-load
the verb. Validate parameters against the schema before executing and
return the standard envelope with actionable messages.

**LLM providers and keys.** Local engines (Ollama, LM Studio) need no
keys and are probed live. Cloud providers need keys saved through the
Settings key UI into the server keystore (0600 file, env var wins when
set); the Test button reports honest 401/403 instead of fake success.
Curated model names are best-effort snapshots shown only until a keyed
live list replaces them. Saving a key never hijacks the active
provider/model pair.

**Releasing the MCPB bundle.** The pack script wipes `mcpb/src`, recopies
`src/<package>/` preserving the package directory, syncs
`assets/prompts/` from the repo source of truth, runs the mechanical
checks (entry import resolves inside the stage, hatch paths exist, no
bytecode or backups, launch serves), then packs. Never edit the stage by
hand, never commit it, never pack over a stale tree. Verify the archive
contents before attaching it to a release; the manifest tool list should
name portmanteaus with real descriptions, not auto-dumped internals.

**Fleet conventions worth memorizing.** Five files per commit and per
script invocation; timestamped backups before touching three or more
files; ports from the registry, never invented; dates from the
environment, never guessed; ASCII in generated prose artifacts; reports
as regenerable snapshots with committed registry copies where a UI reads
them; session logs as shared history with retention. These rules exist
because the fleet already paid for each violation once.

## Dashboard page guide

**Dashboard.** Hero KPIs (tools, servers, categories), health summary,
quick actions. Start here every session; red means heartbeat then ping
before anything else.

**Chat.** Agent mode on for fleet work (trace plus approval card),
personalities from the server list, skill badge with live tool count.
Plain mode for questions with orientation plus role preprompt. Export
transcripts before long investigations end; history caps at 100 messages.

**Builders.** Wizards for every scaffold template including Spec Kit;
questionnaire first for unfamiliar project shapes. Outputs land as
complete repos, never snippets. Verify gates before registering the
result in any IDE.

**Analysis.** SOTA Check cards per repo, Fleet Status runtime audit,
Scrubbers for unicode, PowerShell, and justfile issues, token analysis
for budgets. Remediation output groups P0/P1/P2 with fix steps; work
P0s first on failing repos.

**Fleet Ops and Script Center.** Curated scripts with parameter forms,
live consoles with PID and elapsed time, safe termination, elucidated
report inspector for JSON artifacts. Probes run here with progress and
final reports; broken-only reruns save hours on large fleets.

**Repo Inspiration.** Discover tab for search with presets, faves, and
popularity markers; Study tab for structure, files, and patterns
chapters plus the agentic workflow. Suggested subpaths and language
hints appear after the first run; large-repo mode summarizes directories
instead of drowning the context.

**Assess Reports.** Registry stats cards plus the searchable, sortable,
paginated leporello list with score badges and GitHub blob links to full
reports. Filter Needs work under 60 for triage order.

**Fleet Standards.** Searchable card grid with status badges and detail
view across all handbook standards; honest empty state when the handbook
clone is absent.

**Session Docs.** Searchable session log with grid/list toggle and
prune-by-cutoff for private archives; the shared handbook log refuses
pruning by design.

**Tool Lab.** Execute any catalog tool through auto-rendered forms with
Pretty/Raw JSON output. Validate parameters before destructive runs.

**Servers, Routing, Scheduler, Heartbeat, Toolchains, Clients.**
Lifecycle and configuration surfaces with the same list-page standard
everywhere: search, filter, sort, paginate, count.

**Settings.** LLM provider discovery with model picker and key vault,
path overrides (fleet root, handbook, session docs), onboarding cues.
**Logs** streams the ring buffer with level filters. **Help** covers
setup, recovery, and where each standard lives.

## API cookbook

List providers, then models, then chat. Discovery is
`POST /api/v1/llm/models` with provider and base URL; chat is
`POST /api/v1/llm/chat` with provider, base URL, model, and messages.
Agent mode is `POST /api/v1/chat/agent` with history, personality id,
and max iterations (1-10); mutating calls return `needs_confirmation`
with a run id and pending list, resumed via
`POST /api/v1/chat/agent/confirm` with approved call ids. Denied calls
feed back as user denials so the model replans. Context (personalities,
tool catalog, orientation) comes from `GET /api/v1/chat/context`.

Execute tools with `POST /api/v1/tools/execute` carrying server id
(`metaops` for local), tool name, and parameters; validate first with
`POST /api/v1/tools/validate`. Browse schemas at
`GET /api/v1/mcp/catalog` and per-server at
`GET /api/v1/servers/{id}/tools`. Fleet jobs start at
`POST /api/v1/fleet/ops/jobs` with status tails at
`GET /api/v1/fleet/ops/jobs/{id}`; kill runaway jobs rather than
abandoning them. Scheduler tasks register with name, interval, server,
tool, and parameters; heartbeats pulse machine health on demand or on
schedule.

Reports and docs read plainly: assess registry list/get/stats,
standards list/get, session-docs list/read plus cutoff prune, fleet
startup and cold-install run/report pairs. All responses use the
success/message/data envelope; failures raise with detail strings, not
stack traces. Timeouts are generous for model calls (300s) and tight
for discovery (30s); set client timeouts to match the route.

## Environment reference

`HOST` and `PORT` bind the backend (defaults 127.0.0.1:10718).
`FLEET_REPOS_ROOT` (fallback `REPOS_DIR`) locates the fleet checkout;
the handbook resolves from `MCP_CENTRAL_DOCS_ROOT` or the standard
layouts. `SESSION_DOCS_DIR` selects the session archive; unset means
the handbook log with pruning disabled. `GITHUB_TOKEN` lifts discovery
rate limits. `WURST_AUTH_TOKEN` guards fleet start/stop/restart;
unset means local-dev bypass on your own machine only. Builder
overrides (`META_MCP_TASKS_FILE`, `META_MCP_FULLSTACK_SCRIPT`,
`META_MCP_WEBSHOP_SCRIPT`) redirect generated paths without code
changes. Copy `.env.example` to `.env` and keep `.env` out of git;
every variable is documented there with its default.

## Migration and upgrade runbook

**New machine setup.** Install Python 3.12+, uv, Bun, and PowerShell 7;
clone the repo; copy `.env.example` to `.env` and set the fleet root,
handbook path, tokens, and auth; run `uv sync --group dev`; execute
`start.ps1` and confirm both ports answer; run Discovery in Settings and
save a model; register IDE clients with `client_ops`; run the heartbeat
pulse as a smoke test. Budget an hour including downloads.

**Moving the fleet root.** Set `FLEET_REPOS_ROOT` (or `REPOS_DIR`) in
`.env`, restart the backend, re-run discovery and the routing reindex,
and re-probe cold-start on the moved repos. Manifests and depots under
`~/.meta_mcp/` follow automatically because they resolve the root at
runtime. Verify Assess Reports counts match the previous root before
deleting anything at the old path.

**Rotating keys.** Replace `GITHUB_TOKEN` and cloud LLM keys in `.env`
first, then clear the server keystore entries through Settings (save
then clear then save the new key), then press Test on each provider and
confirm honest success. Never rotate by editing files that might be
committed; env plus keystore only. Revoke the old keys at the provider
dashboard after the new ones verify.

**Updating IDEs.** Apply the current toolchain preset rather than
hand-editing each client; validate every client afterwards and diff the
backups the tooling wrote. When adding a new IDE to the fleet, register
one server, smoke it in Tool Lab, then apply the full preset.

**Backup and restore.** Back up `~/.meta_mcp/` (depots, tasks, keystore),
all `docs/assess-reports/` directories that matter, `.env` (to a vault,
never git), and IDE client configs via `client_ops` read. Restore is the
reverse: lay down the checkout, restore state, re-run discovery and
probes, and compare report counts. Test restores on a scratch user
profile yearly; an untested backup is a rumor.

**Version upgrades.** Read the changelog Unreleased section, run the
full gates before and after (`ruff`, `pytest`, `tsc`, Biome), re-probe
cold-start plus one cold-install preflight, and re-verify the bundle
checks if MCPB ships this release. Keep the previous venv until the new
one serves; roll back by checking out the prior commit and resyncing.

## Frequently asked questions

**Do I need the handbook clone?** No for runtime; yes for the Standards
browser and session-log fallback. Set `MCP_CENTRAL_DOCS_ROOT` when you
want those pages populated.

**Which model should I pick?** Any tool-capable model for agent mode;
anything for plain chat. Local Ollama models keep everything on-machine;
cloud keys buy bigger context windows.

**Why did the agent ask approval for a read?** The gate is default-deny
on unknown operation names. If the operation is read-only in effect,
approve it and tell the operator to add the name to the read-only set.

**Where do reports go?** Snapshots under `reports/` (ignored),
registry copies under `docs/assess-reports/` (committed), depot runs
under `~/.meta_mcp/analysis/`, probe reports under `~/.meta_mcp/fleet/`.

**Can I run the dashboard without the MCP server?** The dashboard needs
the backend on 10718; the stdio server is a separate entry for IDEs.
`start.ps1` launches both surfaces together.

**How do I add a new fleet script?** Drop it in the catalog source with
a parameter schema; it appears in Fleet Ops with an auto-rendered form,
live console, and elucidated reports. No frontend code required.

**What breaks most often?** Stale ports (squatters), moved repos without
reindex, expired keys surfacing as honest 401s, and committing without
running the gates. The troubleshooting section above covers each.

**Is my data sent anywhere?** Local models: no. Cloud providers: prompts
go to the keyed provider only. GitHub search sends queries to the API.
Nothing phones home besides those explicit integrations.

**How do I contribute a preset?** Add the query, label, and sort to the
server preset list with a one-line justification; presets are shared by
all clients, so keep them broadly useful, not personal.

**Who do I ask for help?** Dashboard Help page, `help()` tool, the
handbook standards, then the repo issues. Include gate output and the
relevant trace when reporting; screenshots of amber cards beat prose.

## Copy-paste cookbook

Nightly audit plus morning glance: register a scheduler task running
`analysis_ops` runts at 02:00, then read Assess Reports stats with the
Needs-work filter over coffee. Total hands-on time under five minutes.

New hire IDE setup: apply the team toolchain preset to their machine,
validate all clients, run Discovery in Settings, save the house model,
and hand them the Builders page with the questionnaire. One command
plus two screens.

Pre-release sweep: cold-start probe, cold-install preflight, runts
audit, fix P0s, re-score, write both report copies plus timestamp,
pack the bundle, verify the archive, attach to the release. The same
order every time; checklists beat memory.

Study sprint: pick a Discover preset, star three candidates, study
structure of each, deep-dive patterns on the winner, run the agentic
workflow for a scaffold recommendation, and scaffold on Friday. Learning
compounds when it ends in a repo.

Spring cleaning: prune private session archives past 30 days, clear
resolved scheduler tasks, delete stale toolchains, reindex routing,
and confirm report counts match the fleet size. Quarterly, one hour.

Triage pile: filter Assess Reports to Needs work, sort by score
ascending, open the lowest, work its P0 list, re-run its audit, and
move on. Smallest number first keeps momentum honest.

Demo prep: toolchain to demo preset, launch the app, open its dashboard,
rehearse the three clicks that matter, and keep the logs page open on a
second screen. Audiences forgive slow; they do not forgive red.

Offboarding a repo: cancel its scheduler tasks, remove it from IDE
clients, archive the final assess report, and drop it from manifests.
Four steps, no orphans left behind.

## Release and support notes

Ship with the checklist, not with confidence. A release needs green
cold-start, green install preflight, a runts score at or above the bar
with P0s cleared, both report copies plus timestamp committed, a
fresh-staged verified bundle attached, and a changelog entry written
before the tag, not after. Anything deferred goes in the notes
explicitly with the next version named.

Support matrix, plainly: Windows 11 with PowerShell 7 is Tier 1 and
tested every release. Other platforms run the Python backend wherever
uv runs, but the PowerShell automation and port tooling assume Windows;
expect to adapt scripts elsewhere. Claude Desktop takes the MCPB
bundle; Cursor, Windsurf, Antigravity, Zed, and OpenCode take stdio;
VS Code Copilot takes stdio in agent mode. Browsers only need the
dashboard URL. Small local models chat; tool-capable models agent.

End of life is explicit, never silent. A deprecated tool warns for one
minor version with its replacement named, then leaves with a changelog
line and a migration note. Removed endpoints answer 410 with the
successor path where one exists. Old bundles stay attached to their
releases so pinned consumers keep working; nothing is yanked
retroactively.

Feedback loops close the system. Report template gaps when a real
failure has no row for it. Propose read-only set additions with proof
the operation mutates nothing. Suggest presets that stay useful to
strangers, not just your week. File issues with gate output and traces
attached; the fastest fixes start from a reproducible report, and the
second fastest from a good log line.

## Power-user tips

Learn the catalog shortcut first: `help()` lists everything, and the
Tool Lab turns any entry into a form. Keep three browser tabs pinned
during fleet work: Assess Reports filtered to Needs work, the Fleet Ops
job console, and Logs at warning level. Name scheduler tasks like
releases (`nightly-runts`, `weekly-depot-cleanup`) so a stranger can
read the schedule cold.

Batch repetitive checks with broken-only reruns instead of full sweeps;
the fleet is large and your evening is short. Export transcripts of
decisions made in agent mode into session docs the same day; memory of
why fades faster than memory of what. Review the approval card
arguments character by character before approving mutating calls; the
gate shows you everything the model intends, which is exactly when
attention pays most.

Keep a personal Discover preset list in faves rather than retyping
queries; star generously, prune ruthlessly. Mirror the Unreleased
changelog habit in your own repos: write the entry when the change
lands, not at release time, and future you will actually know what
shipped. Finally, treat every red dashboard as a question with an
answer, not a mood: pulse, ping, list, read the trace, fix the named
thing. Calm fleets are operated, not wished for.

## How to read this guide

Match depth to the task, not to your curiosity. Brief profile for a
single question (one tutorial section, one tool call). Standard profile
for real work (the full tutorial plus its troubleshooting rows). Deep
profile for releases and migrations (everything above plus the advanced
topics and the runbooks). Skim the cookbook monthly; commands rot slower
than memory. When a section references a dashboard page, open it
alongside the text; when it references a tool, run the read-only form
first in Tool Lab before any mutating variant. Guides are read in
order the first time and jumped into by heading forever after, which is
why every section states its goal up front. If a step fails, the
troubleshooting section answers in the same vocabulary as the tutorial
that sent you there.

Revisit this guide after each release; the fleet moves monthly.