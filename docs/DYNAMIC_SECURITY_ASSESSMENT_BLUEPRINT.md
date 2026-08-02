# Dynamic Security Assessment Blueprint for MetaMCP

## Why This Exists

Static scanning is necessary but limited. It can detect risky patterns, weak metadata, and likely anti-patterns, but it cannot fully validate runtime behavior under realistic tool execution.

For MCP ecosystems, two properties are both required:

- **Interface quality**: clients can discover tools and call them with correct parameters.
- **Payload safety**: actual tool behavior stays within policy under hostile or malformed input.

A server that fails interface quality is unusable.  
A server that fails payload safety is dangerous.  
MetaMCP should assess both.

## Goal

Extend MetaMCP with a fleet-grade dynamic assessor that orchestrates:

- static scanners (`mcp-scanner`, `skill-scanner`) where applicable
- dynamic execution probes and adversarial test runs
- webapp/runtime checks when a repo includes `webapp` or `web_sota`
- normalized evidence and risk scoring

This turns MetaMCP into a practical control-plane assessor, not only a metadata/indexing orchestrator.

## Scope

### In Scope (Phase 1)

- dynamic checks against MCP servers reachable via stdio/http/sse
- interface quality checks (discoverability, schema validity, invocation consistency)
- payload safety probes (input abuse, boundary stress, side-effect policy checks)
- webapp assessment lane for repos with `webapp`/`web_sota`:
  - dependency health (missing deps, install integrity)
  - route smoke checks
  - backend connectivity checks
  - port schema and adjacency validation
  - optional Playwright walkthroughs
- optional consumption of third-party scan outputs
- normalized report artifact for CI and human review

### Out of Scope (initial)

- full formal verification of tool safety
- heavy exploit simulation requiring privileged destructive operations
- universal support for every external scanner API from day one

## Core Concept: Two-Lens Dynamic Assessment

Every target is scored through two independent lenses:

- **Lens A: Interface Reliability**
  - can client initialize and list tools?
  - are schemas valid and parameters usable?
  - do invocation failures return actionable errors?
- **Lens B: Behavioral Safety**
  - do tools execute beyond declared intent?
  - do tainted inputs reach privileged actions?
  - can high-impact actions bypass expected controls?

Passing Lens A does not imply passing Lens B.

## Proposed MetaMCP Capability Surface

### 1) `dynamic_security_assess`

Primary orchestration tool for dynamic assessment.

Suggested high-level arguments:

- `target`: local repo path, server url, or managed server id
- `transport`: `stdio | http | sse | auto`
- `profile`: `quick | balanced | deep`
- `include_static`: bool
- `include_fuzz`: bool
- `include_prompt_injection_probes`: bool
- `safety_mode`: `safe | moderate | aggressive`
- `report_format`: `summary | detailed | json | sarif`
- `output_path`: optional file path

Output shape:

- `success`
- `assessment_id`
- `scores` (`interface`, `behavior`, `overall`)
- `findings` normalized with severity and evidence
- `repro_steps`
- `recommendations`
- `artifacts` (logs, traces, raw scanner outputs)
- `webapp_checks` (when applicable)

### 2) `dynamic_security_status`

Returns current/last run status and pointers to artifacts.

### 3) `dynamic_security_report`

Fetches finalized report in requested format.

### 4) `dynamic_security_cancel`

Stops long-running assessment safely.

### 5) `dynamic_security_profiles`

Lists built-in assessment profiles and what each enables.

## Proposed `test_me` Contract for Target Servers

Optional but strongly recommended contract exposed by target MCP servers:

- tool name: `test_me` (or alias `self_test`)
- no destructive side effects
- returns structured diagnostics:
  - capability inventory
  - schema health checks
  - dependency readiness
  - policy/guardrail declarations
  - synthetic invocation checks (safe fixtures)

Benefits:

- deterministic handshake for dynamic harnesses
- easier triage when a server is misconfigured vs vulnerable
- improved CI reproducibility

## Assessment Pipeline (Reference)

1. **Target Prep**
   - resolve target type
   - launch/connect safely
   - capture environment metadata
2. **Interface Sweep**
   - initialize/list tools/prompts/resources
   - validate schema and parameter contract
   - run basic happy-path invocations
3. **Behavioral Probes**
   - malformed input cases
   - boundary payloads
   - taint-flow probes toward sensitive operations
   - indirect instruction probes where applicable
4. **Webapp Lane (conditional)**
   - detect `webapp`/`web_sota` directories
   - verify lockfile/dependency integrity
   - start stack in test mode and validate backend handshake
   - run route smoke checks and capture errors
   - run optional Playwright walkthroughs for critical flows
5. **Policy Assertions**
   - verify expected denials and confirmations
   - verify logging/audit traces were emitted
6. **Static Correlation (optional)**
   - ingest static outputs and correlate by tool/route
7. **Scoring and Reporting**
   - normalize findings
   - compute lens scores
   - emit artifacts and remediation guidance

## Webapp Assessment Profile (if `webapp` or `web_sota` exists)

### Mandatory checks

- dependency install check against lockfile
- frontend boot and backend boot health checks
- backend base url wiring and connectivity validation
- route smoke checks for top-level paths
- port policy checks against fleet standards

### Optional checks

- Playwright walkthrough for key user paths
- console/network error budget assertions
- screenshot artifacts for failure diagnostics

### Typical finding classes

- missing or stale dependencies
- broken route registration
- frontend-backend API mismatch
- invalid/misaligned port assignment
- startup scripts not clearing/using expected ports

## Scoring Model (Starter)

Use a transparent model with independent dimensions:

- `interface_score` (0-100)
- `behavior_score` (0-100)
- `operational_confidence` (0-100, based on evidence completeness)

Derived `overall_score` should be constrained by worst critical findings (hard caps).

Example policy:

- any unsuppressed critical => overall <= 39
- any unsuppressed high => overall <= 69

## Safety Controls for the Assessor Itself

- default `safe` mode forbids destructive probes
- strict network/file/path allow-lists for test harness
- sandboxed execution where possible
- explicit "consent required" mode for high-impact operations
- complete audit trail for every attempted probe

## External Tooling Integration Strategy

Integrate external scanners as adapters, not core dependencies:

- scanner adapters emit normalized finding schema
- adapter failures degrade gracefully without halting entire run
- pin versions in CI profiles for reproducibility

Potential adapters:

- `mcp-scanner`
- `skill-scanner`
- protocol fuzzers / testbench tools

## CI/CD Integration Pattern

Three lanes:

- **PR quick lane**: interface checks + lightweight behavior probes + webapp smoke checks
- **nightly lane**: deeper dynamic probes + optional fuzzing + Playwright walkthrough
- **release lane**: full profile, policy gate, immutable artifact archive, and webapp evidence pack

## Deliverables

- MetaMCP dynamic assessor tools (orchestration + status/reporting)
- `test_me` contract spec (fleet recommendation)
- reusable CI templates
- baseline suppression governance (reason + owner + expiry)

## Risks and Constraints

- false positives/negatives remain possible
- dynamic tests can be flaky without deterministic fixtures
- incomplete server observability reduces confidence score
- hostile probes can trigger rate limits or defensive blocks

## Definition of Done (Initial)

- one end-to-end dynamic assessment run on at least two real MCP repos
- JSON report with reproducible evidence and remediation hints
- CI template validated in one pilot repo
- documented suppression process with expiry policy
