# Dev Sandbox Hardening Profile (Stepwise, Optional)

## Intent

Provide practical sandbox hardening that is incremental and reversible.  
Goal: reduce blast radius from poisoned dependencies/tools without locking developers out.

## Operating Principle

- sandboxing is risk reduction, not bulletproof isolation
- all controls are opt-in by profile
- every profile includes rollback and break-glass options

## Profiles

## Profile 0 - Baseline (Default)

Low friction, immediate value.

- use isolated virtual env per project
- use lockfiles and pinned versions
- no production credentials in dev shell
- dependency cooling-off policy active (default hold)
- daily snapshot or backup of dev VM/project state

When to use:

- general day-to-day development

## Profile 1 - Balanced

Moderate hardening for risky dependency work.

- disable host shared folders by default
- disable bidirectional clipboard unless needed
- route dev traffic through allow-listed proxy where possible
- use short-lived scoped tokens only
- run scanner preflight before dependency upgrades
- canary test upgrades in disposable VM snapshot first

When to use:

- dependency refresh days
- testing new tools from unknown trust level

## Profile 2 - Strict

High containment, higher friction.

- no host folder mounts
- no host clipboard/drag-drop
- network egress allow-list only
- disposable VM per test batch
- no long-lived secrets at all
- strict scanner gate before install/use

When to use:

- evaluating untrusted packages/tools
- incident-response validation

## Profile 3 - Quarantine Lab (Emergency)

Containment mode for suspected compromise analysis.

- isolated VM/network segment
- no host integrations
- no direct internet except controlled mirror/forensics endpoints
- full command/process/network logging
- immutable evidence capture before cleanup

When to use:

- suspicious package execution
- IOC validation and triage

## Rollout Pattern (Recommended)

Step up only when needed:

- baseline -> balanced -> strict -> quarantine

Step down after stability window:

- strict -> balanced -> baseline

## Lockout Prevention and Break-Glass

Every hardening change should preserve a safe fallback:

- maintain one known-good VM snapshot
- keep one documented emergency admin path
- keep rollback script/checklist for profile controls
- never rotate all access methods at once
- test recovery path monthly

## Suspected Poisoned Dependency Playbook (Fast Path)

1. isolate host/VM from network
2. revoke and rotate potentially exposed credentials
3. preserve evidence/logs
4. rebuild from known-good snapshot/image
5. restore project state from pre-incident backup
6. validate with scanner suite before reconnecting

## MetaMCP Integration Hooks

- `dynamic_security_assess` should accept `sandbox_profile`:
  - `baseline | balanced | strict | quarantine`
- reports should record:
  - profile used
  - host integration status
  - network policy mode
  - secrets policy mode

## Minimal Automation TODO

- profile toggles as machine-readable config
- profile validator before assessment run
- rollback helper script for each profile
- monthly recovery drill reminder

## Agentic Sandbox Job Workflow (Recommended)

Use one repeatable job lifecycle:

1. **Start sandbox**
   - create fresh VM snapshot/instance
   - apply selected profile (`baseline | balanced | strict | quarantine`)
2. **Bootstrap dev tools**
   - install pinned toolchain from approved manifest
   - verify checksums/signatures where available
3. **Run dev activity**
   - execute tests/scans/builds inside sandbox only
   - keep secrets scope minimal and time-limited
4. **Collect outputs**
   - write all logs/reports/artifacts to one sandbox output directory
   - export only that directory to host
5. **Teardown**
   - power off and destroy disposable instance or revert snapshot
   - rotate any temporary credentials issued for the run

Suggested output path convention:

- sandbox local: `C:\sandbox_out\`
- host imported: `D:\Dev\repos\_sandbox_runs\<run_id>\`

## WSB/VM Automation Notes

- use scripted provisioning for reproducibility
- keep setup scripts versioned and signed/hashed internally
- avoid ad hoc manual installs inside long-lived images
- include a pre-exit checklist to ensure artifacts exported before teardown

## Gated Access Presets (Optional)

Define explicit access toggles per run:

- `local_llm_access`: `disabled | proxy_bridged | direct_host`
- `gpu_access_4090`: `disabled | enabled`
- `docker_access`: `disabled | socket_proxy | host_engine`
- `github_access`: `disabled | read_only | read_write`

Recommended defaults by profile:

- `baseline`: local_llm=`proxy_bridged`, gpu=`enabled`, docker=`socket_proxy`, github=`read_only`
- `balanced`: local_llm=`proxy_bridged`, gpu=`enabled`, docker=`socket_proxy`, github=`read_only`
- `strict`: local_llm=`disabled`, gpu=`disabled` (unless required), docker=`disabled`, github=`disabled|read_only`
- `quarantine`: all disabled unless explicitly approved for forensic reason

### Notes

- `proxy_bridged` is preferred over direct host bridge for Ollama/local LLMs.
- `socket_proxy` is preferred over direct Docker engine access.
- `github_read_write` should require explicit run justification.

## Start Questionnaire (Pre-Run Gate)

Before sandbox start, answer:

1. What is the run objective? (`test | scan | upgrade | incident`)
2. Is untrusted code/dependency involved? (`yes/no`)
3. Required local LLM access level? (`disabled | proxy_bridged | direct_host`)
4. Is RTX 4090/GPU access required? (`yes/no`)
5. Docker access required? (`none | socket_proxy | host_engine`)
6. GitHub access needed? (`none | read_only | read_write`)
7. Any production credentials required? (`should be no`)
8. Desired profile? (`baseline | balanced | strict | quarantine`)
9. Rollback snapshot verified? (`yes/no`)
10. Output folder set? (`yes/no`)

If answers conflict with selected profile, escalate profile or reduce access.
