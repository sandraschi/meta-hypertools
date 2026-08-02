# Meta-MCP User Guide - Natural Language Tutorials

Welcome to meta-mcp, the fleet orchestration server. This guide teaches you
how to use meta-mcp the way the fleet intends: through real workflows, step
by step, in plain language. You do not need to know every tool. You need
the workflows. Read the sections that match what you are trying to do
today, and return when you start a new kind of task.

The fleet is a collection of FastMCP Python servers living under
`D:\Dev\repos`, plus the documentation hub `mcp-central-docs`. Meta-mcp is
the layer that builds, analyzes, and operates that collection. Everything
in this guide assumes you have meta-mcp connected and its tools available.

## Chapter 1 - First Contact

The fastest way to understand what meta-mcp can do is to ask it directly.
Call `help` with no arguments. You will get a flat list of every tool with
a one-line description. Then call `show_mcp_overview` to get the platform
map: which tools belong to which suite, and how the suites relate to the
SOTA standards documents.

Spend two minutes on this. The tool list changes as the fleet evolves, and
the overview page is always fresher than any documentation you have read
before. When you see a tool whose name is a portmanteau - something like
`server_ops` or `pack_ops` - remember that it is a dispatcher: it takes an
`operation` argument that selects the actual behavior. The valid
operations are visible in the tool's schema, so you can discover them
without asking.

## Chapter 2 - Scaffolding Your First Server

This is the most common task. You want a new MCP server, standards-ready,
with zero manual setup. Here is the workflow.

### Step 1: Decide what to build

Ask yourself three questions. First: what domain does the server cover?
Second: does an existing fleet server already cover it? Third: is there a
reference implementation on GitHub you want to imitate?

If you have a reference, run `inspire_repo` with the owner and repository
name. For example, if the user says "I like how that repo organizes its
tools", call `inspire_repo(owner="some-owner", repo="some-repo")`. You get
back an architecture study: the file layout, the entry points, the tool
surface, and the patterns worth copying. If the user wants deeper
reasoning, run `inspire_repo_workflow` instead - it produces a full
scaffold recommendation, not just a summary.

### Step 2: Run the scaffolder

Call `scaffold_mcp_server` with a name, a description, and the feature
flags you want. A sensible default feature set is
`prefab,skills,webapp,ci,tests`: Prefab UI cards for chat surfaces, a
skills directory so IDE agents can load usage instructions, a React
webapp, CI, and tests. If the user only wants a headless server, drop
`webapp`.

The scaffolder creates a complete repository on disk. It includes
`pyproject.toml` with the FastMCP 3.4+ floor, a `justfile` with the
standard recipes, `llms.txt` and `llms-full.txt`, `glama.json`, the MCPB
packaging layout, a CI workflow, and a README that follows the fleet
structure. The generated server already contains example tools so the
repository boots immediately.

### Step 3: Add the real tools

Open the generated `src/{package}/server.py`. Add your tools as functions
decorated with `@mcp.tool()`. Follow the house style: a one-line summary,
`Annotated[T, Field(description="...")]` on every parameter, a
`## Return Format` section, and `## Examples`. If your domain has more
than about twenty operations, consolidate them into a portmanteau tool
with an `operation` parameter typed as a `Literal` of valid operations,
and start the docstring with a `[RATIONALE]` section.

If your tools mostly list things or report status, add a Prefab surface:
either a dedicated `@mcp.tool(app=True)` that renders a card, or return a
`ToolResult` with `structured_content=PrefabApp(...)`. Always keep the
plain text fallback in `content` for hosts that do not render apps.

### Step 4: Add a skill

Create `src/{package}/skills/{name}/SKILL.md`. The skill teaches agents
how to use the server: what the tools do, in what order to call them, and
what the return formats mean. Expose it as an MCP resource so it is
discoverable. The webapp's Chat page will automatically load the primary
skill as its preprompt, so a good skill improves both the IDE experience
and the webapp chat.

### Step 5: Verify

In the generated repository run `just bootstrap` to install dependencies,
then `just lint` and `just test`. The scaffold ships with a smoke test
that boots the app and checks the health endpoint, so a green test run
means the wiring is correct.

### Step 6: Register ports

Pick backend and frontend ports from the fleet reservoir (10700-11500)
and add them to `mcp-central-docs/operations/WEBAPP_PORTS.md`. Backend and
frontend must be adjacent.

### Step 7: Pack and register

When the server is ready, pack the MCPB bundle with `mcpb pack` so Claude
Desktop users can install it in one click, then use `server_ops` with
`operation=register` to add it to your IDE configuration. Verify with
`server_ops operation=status`.

## Chapter 3 - The Fullstack Webapp

When the user wants a webapp - a dashboard, a control panel, a playground
- run `scaffold_app_fullstack` with the app name, a description, and the
port. The generated project pairs a React 18 frontend with a FastMCP
backend served by uvicorn.

The webapp ships with the mandatory SOTA page set:

- **Dashboard**: a hero section plus KPI cards driven by the health
  endpoint. Every card carries a `data-testid` so automation can find it.
- **Tools**: a dynamic list of the server's registered tools. It must
  never be a hardcoded array - it fetches from the tools API.
- **Skills**: lists the server's skills and renders the SKILL.md content.
- **Chat**: the fleet-standard chat. It loads the primary skill as its
  system prompt, offers personalities, keeps history in localStorage,
  probes local LLM providers, and supports export and clear.
- **Settings**: backend health plus the local LLM provider probe. It
  checks Ollama on port 11434, LM Studio on 1234, and vLLM on 8000, and
  shows detected status per provider.
- **Help**: a page with architecture, ports, and troubleshooting.
- **Logs** and **API Docs**: the log ring buffer viewer and the Swagger
  iframe.

Dark mode is the default. The frontend uses Tailwind, lucide icons, and
zustand for state. Bun is the package manager.

To run the generated webapp: `uv sync` in the repo root, `bun install` in
the webapp directory, then run the start script. The start script clears
port zombies, starts the backend, waits for health, starts the frontend,
and opens the browser.

## Chapter 4 - Fleet Health and the Runt Hunt

The fleet degrades silently. Repos fall behind the standards floor,
dependencies age, documentation rots. Meta-mcp gives you the tools to see
the decay and fix it in waves.

### The scan

Run `analyze_mcp_runts` with the fleet root as the scan path. Ask for
markdown for reading, or JSON if you want to process the result. Add
`deep_scan` when you want source-level checks, not just file-presence
checks. The report lists every repo with its per-category scores and the
specific gaps.

### Reading the report

Categories: FastMCP version floor, MCPB packaging, CI/CD, tests, folder
structure, documentation, root cleanliness, tooling. A repo with a low
MCPB score is missing packaging artifacts - icon, prompts, or manifest. A
repo with a low documentation score is missing README, CHANGELOG,
`llms.txt`, `llms-full.txt`, or `glama.json`. A repo with a low FastMCP
score is running a version below the 3.4 floor or using obsolete
decorator patterns.

### The fix wave

Sort the report by score, lowest first. Fix CRITICAL gaps first: version
floors, broken packaging, missing CI. Then MEDIUM: documentation files,
test scaffolding. Then LOW: cleanliness, tooling polish. After each wave,
re-run the scan and confirm the scores moved. This is the mechanical part
of the assfix workflow - the report is the work list, the re-scan is the
proof.

### Runtime health

The static scan tells you about the repository. `get_fleet_status` tells
you about the running fleet: which webapps are up, which ports respond,
which health endpoints are green. Combine it with `heartbeat_ops` - the
`status` operation gives CPU, memory, and disk; the `ports` operation
lists what is listening on the fleet range. If a webapp is down but the
port is occupied, there is a zombie process - that is the first thing to
clear.

## Chapter 5 - Wrapping Existing Code with the Harness

You have a Python script collection, a library, or a tool you want to
expose as an MCP server without hand-writing every tool. The harness
pipeline does this in three passes.

### Pass 1: Analyze

Call `harness_analyze` with the path to the source tree. Meta-mcp parses
the AST and produces a spec: the modules, classes, functions, and their
signatures, with candidate tool mappings. Review the spec with the user.
If the tree contains a giant module that should be split, or a helper
module that should be private, say so before generating - it is cheaper to
fix the spec than the generated code.

### Pass 2: Generate

Call `harness_generate` with the spec and a name. The result is a
FastMCP server whose tool surface is derived from the analysis. Functions
that look like tools - public, documented, with simple signatures - become
tools. The generation is deterministic from the spec, so the same spec
always produces the same server.

### Pass 3: Refine

Call `harness_refine` with the generated server path and the spec. The
gap analysis reports functions that did not become tools, tools that do
not match their source signatures, and modules that were skipped
entirely. Iterate: fix the gaps, regenerate or hand-patch, re-run refine
until the gap list is empty or the user accepts the remaining items
explicitly.

### When the harness is the wrong tool

The harness is for wrapping existing code. If you are starting from a
blank page, use `scaffold_mcp_server` instead. If you are wrapping a
host application that must be running (Blender, GIMP, a game engine),
remember the harness only generates the server - the host integration
still needs design work, and the SOTA guidance for host-app wrappers
applies.

## Chapter 6 - Release Certification

Before a release wave, run the probes. They catch the failures that unit
tests never see.

### Startup probe

`fleet_startup_probe` with the scope you care about. It starts the fleet
backends in a controlled way and reports boot success, crash traces, and
hangs. Run this the day before a release. A crash here means the frozen
binary or the source entry point broke since the last release.

### Cold install probe

`fleet_cold_install_probe` simulates what a new user experiences: it
validates that `INSTALL.md` exists and follows the fleet structure,
checks that the GitHub release actually carries the `.mcpb` asset with the
expected name, and runs a stdio smoke test following the install
instructions for Cursor, Windsurf, Antigravity, Zed, and OpenCode. A
failure here means the release would be uninstallable for someone - fix it
before shipping.

### Registration sweep

After the probes pass, sweep the IDE registrations with `server_ops`. Use
`operation=list` to see the current state across configs, then
`operation=register` for servers that moved or were added, and
`operation=status` to confirm the binaries resolve.

## Chapter 7 - Everyday Operations

### Switching toolchains

The fleet has more servers than any IDE should load at once. Toolchain
presets solve this: a preset is a named set of servers. `toolchain_ops`
with `operation=list` shows the presets. `operation=apply` with a preset
name rewrites the active config to enable exactly that set. `operation=create`
captures the current config as a new preset - do this after you have tuned
a setup you like, so you can return to it later.

### Scheduling background work

`scheduler_ops` manages background jobs. Create a job with
`operation=add`, a name, a command, and a schedule in cron form. List
with `operation=list`. Test with `operation=run_now` - it triggers the
job immediately without waiting for the schedule. Pause and resume with
the obvious operations. Remove with `operation=remove`.

### Packing a repo for context

When you need to hand a large repository to a model in a single message,
`pack_ops` with `operation=pack` builds a single text bundle with a
manifest header. Check the size and token estimate with `operation=info`
before embedding it. If the bundle is too large, `token_ops` can find the
heaviest files: `operation=repo` estimates the whole tree, and the per-file
estimates tell you what to trim.

### Token budgeting

Before embedding files in a prompt, run `token_ops` with `operation=file`
on the candidates. The estimates are heuristic - they are guidance, not a
meter - but they catch the embarrassing case of embedding a five-megabyte
log file. Budget roughly: a single context window fits about the contents
of two or three typical source files.

## Chapter 8 - Troubleshooting

### "The scaffolder produced a repo, but `just bootstrap` fails"

The generated repo needs uv and a network connection on first sync. Check
that `uv` is on PATH and that the machine is online. If the failure is a
specific package, the version floor in `pyproject.toml` may be newer than
what the mirror has - report the package name and the error.

### "The webapp loads but the backend dot stays red"

The frontend polls the backend health endpoint. A red dot means the
backend is not reachable: either it is not running, or it is on a
different port than the frontend expects. Check the ports in the generated
`vite.config.ts` and `start.ps1`. They must match the adjacent pair from
the registry.

### "The chat page says no provider detected"

The chat probes Ollama, LM Studio, and vLLM on their default ports. Start
the provider first. On this machine Ollama is the usual choice - start it,
wait for it to answer on port 11434, then reload the chat page.

### "The runt scan flags a repo I just fixed"

The scan reads the repository on disk, so if the fix was not saved, or
was saved to a different repo, the scan still sees the old state. Re-run
after the fix is committed. If the flag persists, read the specific issue
message - the checker is specific about what it finds.

### "A portmanteau tool does not know my operation"

Read the schema of the tool. Portmanteaus expose their valid operations
as a Literal enum in the schema - the operation you want either exists
there or it does not. If it does not, the operation was never implemented;
do not guess at synonyms. Tell the user the valid set and ask how to
proceed.

### "The harness produced a server with wrong signatures"

Run `harness_refine` and read the gap list. Signature mismatches usually
mean the analysis pass missed a dynamic pattern - the source uses
`getattr` dispatch, or the functions are decorated in a way the AST pass
does not resolve. Patch the spec entry by hand and regenerate rather than
editing the generated server directly; the spec is the source of truth.

## Chapter 9 - A Full Day with Meta-MCP

Here is a realistic day, to show how the pieces combine.

Morning: run `get_fleet_status` to see what survived the night. A webapp
is down - `heartbeat_ops operation=ports` shows a zombie on its port. Kill
the zombie, restart the app.

Mid-morning: the user wants a new server inspired by a GitHub project.
Run `inspire_repo_workflow`, review the recommendation, run
`scaffold_mcp_server` with the suggested features, then add the domain
tools following the portmanteau pattern. Run `just lint` and `just test`
in the new repo.

Afternoon: a release wave is coming. Run `fleet_startup_probe`, fix the
two repos that crash on boot. Run `fleet_cold_install_probe` on the repos
that ship installers; one is missing its `.mcpb` asset - pack it and push
the release. Sweep registrations with `server_ops`.

Late afternoon: the user asks "what is our fleet doing about standards?"
Run `analyze_mcp_runts` with deep scan, produce the work list, fix the
CRITICAL items, re-run to show the improvement. Schedule a weekly job with
`scheduler_ops` so the digest runs itself.

End of day: pack the day's session notes with `pack_ops` for the
hand-off document. That is the fleet way: everything meta, everything
repeatable, everything honest.

## Chapter 10 - Working With Generated Servers

When you review a server that meta-mcp scaffolded, check it against the
six design principles: portmanteau consolidation for large domains,
rationale docstrings, schema-first parameters, conversational returns,
honest failures, and bounded work. The scaffold is a starting point, not a
finish line. The generated example tools are placeholders to be replaced;
the structure around them is the deliverable.

Keep the skill updated as tools change. A stale skill misleads every agent
that loads it, which is worse than no skill at all. The same applies to
the MCPB prompts: `system.md`, `user.md`, and `examples.json` are part of
the package and must reflect the shipped tool surface. When a tool is
renamed or removed, update the prompts in the same change.

## Chapter 11 - Standards Quick Reference

When you work with meta-mcp you are working against the SOTA 2026
standards. This chapter is the cheat sheet you will actually use. The full
documents live in `mcp-central-docs/standards/`.

### Version floors

FastMCP must be 3.4 or newer in every server's `pyproject.toml`. The
scaffolder enforces this; the runt scan checks it. If you find a server
below the floor, upgrade it and re-run its tests - FastMCP 3.x has had
behavior changes between minor versions, and tests are the safety net.

### The portmanteau pattern

A domain with more than roughly twenty operations gets one tool with an
`operation` parameter typed as a `Literal`. The enum is the catalog. The
docstring starts with `[RATIONALE]`. Every operation is implemented - no
stubs. The registry stays compact and the agent discovers operations from
the schema.

### Docstring style

One-line summary. No `Args:` block - parameter documentation lives in
`Annotated[T, Field(description="...")]`. Mandatory sections: `## Return
Format` with the exact JSON shape, and `## Examples` with one to three
concrete calls. Optional: Notes and Errors with " - " bullets. Never use
f-strings inside docstrings.

### Return contract

Every tool returns a dict with `success`, a `message` that reads like a
sentence, and `data`. Failures add `error` and, where useful,
`recovery_options`. Tools that list things return bounded pages with
continuation parameters - never unbounded arrays.

### The 3-4-100 packaging rule

Every MCPB bundle ships `assets/icon.png` (256 by 256 pixels),
`assets/prompts/system.md` (at least 3000 words of capabilities),
`assets/prompts/user.md` (at least 4000 words of tutorials), and
`assets/prompts/examples.json` (at least 100 structured tool call
examples). The runt scan enforces the word counts, not just file
presence.

### The two-track distribution

Every user-facing server ships two install paths: an `.mcpb` bundle for
Claude Desktop users, and a start script (or Tauri installer) for the full
app experience. The `.mcpb` does not replace the start script. Both are
mandatory.

### Webapp conventions

React 18, Vite, Tailwind, dark mode by default, lucide icons, zustand for
state, Bun for the package manager. The AppLayout has a retractable
sidebar with the collapse toggle at the top and a fixed topbar with a
health dot. Pages: Dashboard, Tools (dynamic discovery only), Skills,
Chat, Settings, Help, Logs, API Docs. Every interactive element carries a
`data-testid`.

### Ports

Webapp ports come from the reservoir 10700-11500. Backend and frontend
are adjacent. The forbidden ports - 3000, 5000, 5173, 8000, 8080 - are
never used for fleet webapps. When you scaffold, the port you choose must
be added to the registry document so nothing collides.

### PowerShell rules

Fleet scripts run on PowerShell 7+. No em dashes in scripts. No `&&` or
`||` chains. No `rm -rf` - use `Remove-Item -Recurse -Force`. No `ls`,
`cat`, `grep`, or `tail` - use the cmdlet equivalents. Every destructive
script supports a dry-run switch. When you write a generated start script,
it must clear port zombies before binding.

### The New Repo Gate

A new server repo is not done until it passes the gate: FastMCP 3.4+
floor, uv with a committed lockfile, a justfile with discoverable recipes,
`llms.txt` and `llms-full.txt`, `glama.json`, the MCPB layout with the
3-4-100 prompts, CI, README and INSTALL, the portmanteau pattern where
applicable, Prefab UI for list and status tools, and tests. The scaffolder
produces all of this in one pass. Do not ship a runt and iterate ten
times - the gate exists so the first version is the real version.

## Chapter 12 - Case Studies

### Case study: the wrappee migration

A user has a local CLI tool written in Python and wants it usable from
Claude Desktop. The workflow: `harness_analyze` on the CLI's source
produces a spec. Review shows the CLI's argument parser maps cleanly to
tool parameters, but one module is a private helper with internal state -
it should not become tools. `harness_generate` with the adjusted spec
produces the server. `harness_refine` flags two functions whose signatures
changed between the analysis and generation - a regeneration fixes them.
The user tests the server, packs the MCPB bundle, and registers it in
Claude Desktop. Total effort: minutes, not days.

### Case study: the release wave

A user is about to release ten updated servers. The sequence:
`fleet_startup_probe` boots all ten from source; two crash - one is a
missing import introduced by an upgrade, the other is a stale port
binding. Both are fixed in minutes. `fleet_cold_install_probe` checks the
install path of the three that ship installers; one release is missing
its `.mcpb` asset, so the pack step is re-run before pushing. `server_ops`
with `operation=list` shows registrations across Cursor, Claude, and
opencode; two servers moved ports, so their registrations are updated.
The wave ships without a single user-facing failure.

### Case study: the standards recovery

A quarterly audit shows thirty repos below the standards floor. The user
runs `analyze_mcp_runts` with deep scan and gets a scored report. The
first wave fixes the CRITICALs: five repos on FastMCP 2.x get upgraded,
four repos missing CI get workflows, three repos with broken MCPB layouts
get repacked. The second wave fixes documentation: `fleet_config_audit`
lists every repo missing `llms.txt` or `glama.json`, and those files are
generated. The re-scan shows the fleet average moving from "NEEDS WORK"
to "GOOD". The pattern - scan, fix in waves, re-scan - becomes the
quarterly rhythm.

## Chapter 13 - Operation Encyclopedia

The portmanteau tools accept an `operation` argument. This chapter lists
the operations you will reach for most often, grouped by tool, so you can
act without a discovery round trip.

### server_ops

`list` shows every MCP server currently registered in the IDE configs it
manages, including where each one is registered. `register` adds a new
entry or updates an existing one; pass the server name and the target
config such as `cursor`, `claude`, or `opencode`. `remove` deletes an
entry - it takes a backup of the config first. `status` reports the
registration state and whether the target binary actually exists on disk;
use it after every register to confirm the entry resolves.

### scheduler_ops

`add` creates a background job with a name, a command, and a cron-style
schedule. `list` shows all jobs with their next run times. `run_now`
triggers a job immediately - the fastest way to verify a new job actually
works. `pause` and `resume` stop and restart a job without losing its
definition. `remove` deletes a job for good.

### toolchain_ops

`list` shows the presets and the server set each one enables. `create`
captures the current active config as a new preset - do this when you
have tuned a combination you want to keep. `apply` switches the active
config to a preset, disabling servers outside it. `delete` removes a
preset you no longer need.

### heartbeat_ops

`status` returns CPU, memory, disk, and boot time in one call. `processes`
lists the fleet's running processes with memory footprints - useful for
finding the memory hog. `ports` lists everything listening on the fleet
port range, which is the first stop when something fails to bind.

### pack_ops

`pack` builds a single context bundle from a repository path, with a
manifest header describing the contents. `info` reports the bundle's
size and token estimate so you can decide whether it fits the context
window before embedding.

### token_ops

`file` estimates the token cost of a single file. `repo` estimates a
whole tree and can highlight the heaviest files. `bundle` estimates an
existing pack bundle. All estimates are labeled as heuristics - use them
for budgeting, not metering.

### get_fleet_status

This tool takes no operations - it is a single action that probes the
fleet webapp registry and reports which apps are up, which are down, and
which respond with errors. Run it first whenever the user asks whether
the fleet is healthy.

### analyze_mcp_runts

The scan tool: pass a path, a format (`markdown` or `json`), and whether
to run the deep source-level scan. The result is the scored report that
drives fix waves. It is the mechanical core of the standards recovery
case study from the previous chapter.

Keep this chapter handy during operations. The most common mistake is
guessing at an operation name that does not exist; when in doubt, read
the tool schema - the enum there is the definitive list, and this chapter
is just the curated subset of what you will use daily.

## Conclusion

Meta-mcp turns fleet maintenance from a chore into a repeatable process:
scaffold with standards baked in, wrap existing code with the harness,
scan for decay, probe before releases, and operate with presets and
schedules. Whenever a task feels repetitive, ask whether meta-mcp has a
tool for it - and remember that `help` and `show_mcp_overview` are always
the cheapest first call.
