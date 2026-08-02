# Dynamic Security Plan and TODO (MetaMCP)

## Objective

Implement a fleet-ready dynamic security assessment capability in MetaMCP that complements static scanners and validates runtime behavior.

## Working Assumptions

- static analysis remains part of baseline controls
- dynamic analysis focuses on exploitability and runtime safety signals
- all results are best-effort telemetry, not formal proofs

## Milestone Plan

## M0 - Alignment and Design Freeze (1-2 days)

- [ ] approve `docs/DYNAMIC_SECURITY_ASSESSMENT_BLUEPRINT.md` as baseline design
- [ ] approve `docs/schemas/SCANNER_ADAPTER_CONTRACT.md` as adapter baseline
- [ ] decide initial output schema fields (finding id, severity, evidence, repro, owner)
- [ ] define severity policy for CI gates (`critical/high` block policy)

## M1 - Minimal Viable Dynamic Assessor (3-5 days)

- [ ] add orchestration entrypoint: `dynamic_security_assess`
- [ ] support one transport (`stdio`) first
- [ ] implement interface lens checks:
  - [ ] initialize/list tools
  - [ ] schema parse and required-param checks
  - [ ] minimal invocation smoke tests
- [ ] emit JSON report artifact with run metadata
- [ ] add repo detector for `webapp` / `web_sota`

## M2 - Behavioral Probe Layer (4-7 days)

- [ ] add malformed and boundary payload suites
- [ ] add taint-style probes for sensitive operations (command/file/network paths)
- [ ] add assertion engine for expected-denial tests
- [ ] include confidence score based on evidence completeness

## M2.5 - Webapp Dynamic Lane (3-6 days)

- [ ] dependency integrity checks (lockfile + install sanity)
- [ ] startup checks for frontend/backend in test mode
- [ ] backend connectivity validation from frontend config/proxy
- [ ] route smoke checks (top-level routes)
- [ ] port schema validation (policy + adjacency expectations)
- [ ] optional Playwright walkthrough profile
- [ ] capture artifacts (console errors, network failures, screenshots)

## M3 - Static Correlation + Adapters (3-5 days)

- [ ] adapter for `mcp-scanner` output ingestion
- [ ] adapter for `skill-scanner` output ingestion
- [ ] adapter for `guarddog` (malicious package heuristics)
- [ ] adapter for `pip-audit` and/or `osv-scanner` (known vuln feed)
- [ ] adapter for `defenseclaw` (advisory-only trial)
- [ ] correlation logic by tool name/capability and severity
- [ ] normalize everything into one finding schema

## M3.5 - DefenseClaw Trial and Graduation (2-4 weeks)

- [ ] run `adapter_defenseclaw` in advisory-only mode
- [ ] collect trial metrics (false positives, reproducibility, actionability)
- [ ] define graduation thresholds for CI gate eligibility
- [ ] decide: stay advisory, promote to gate, or remove

## M4 - `test_me` Contract and Pilot Adoption (3-6 days)

- [ ] publish `test_me` contract spec doc in `docs/`
- [ ] implement `test_me` in one pilot server repo
- [ ] validate dynamic assessor handshake with `test_me`
- [ ] document fallback behavior when `test_me` is missing

## M5 - CI Templates and Governance (2-4 days)

- [ ] add reusable workflow template for PR quick lane
- [ ] add nightly deep-lane template
- [ ] add webapp lane template for repos with `webapp`/`web_sota`
- [ ] add suppression governance format:
  - [ ] required reason
  - [ ] owner
  - [ ] expiry date
- [ ] add failing gate for new unsuppressed high/critical findings
- [ ] implement dependency cooling-off policy (default 7-day hold) with exception workflow for urgent CVEs

## M6 - Hardening and Scale (ongoing)

- [ ] add `http/sse` transport support
- [ ] add sandbox profile for aggressive probes
- [ ] add flaky-test quarantine rules
- [ ] add trend metrics dashboard (mttr, findings/week, suppression debt)
- [ ] implement startup questionnaire gate for local LLM, 4090, Docker, and GitHub access scopes

## First Candidate Pilot Repos

- [ ] `D:\Dev\repos\robofang`
- [ ] `D:\Dev\repos\email-mcp`
- [ ] `D:\Dev\repos\ocr-mcp`

## Deliverables Checklist

- [ ] orchestrator tool(s) merged
- [ ] report schema documented
- [ ] at least one successful end-to-end pilot run
- [ ] CI workflow template validated
- [ ] webapp dynamic lane validated in at least one pilot repo
- [ ] docs linked from main `README.md`

## Open Decisions

- [ ] should dynamic probes run in-process vs external harness by default?
- [ ] how strict should default gate be in first month?
- [ ] do we require `test_me` for "production ready" classification?
- [ ] where to persist historical reports (repo artifact vs central store)?
- [ ] should Playwright walkthroughs be mandatory in release lane?

## Notes

- prioritize determinism and reproducibility over probe breadth in early versions
- keep destructive checks opt-in and isolated
- treat third-party scanner scores as context, not source-of-truth gates
- webapp checks should fail fast on startup/connectivity before running deep probes
