# Supply Chain Scanner Notes (2026-03)

## Context

Recent incidents (including the compromised `litellm` PyPI releases) reinforce that repo scanning must include supply-chain malware detection, not only code quality and MCP protocol/interface checks.

## Incident Reference: LiteLLM

Security reporting indicates compromised PyPI versions (`1.82.7`, `1.82.8`) in March 2026 with credential-stealing behavior.  
Operational takeaway: treat package ingestion and update workflows as a high-risk path, even for popular projects.

## Recommended Scanner Stack for MetaMCP Integration

Use layered scanners with distinct strengths:

### 1) Malicious Package Heuristics

- **GuardDog** (`DataDog/guarddog`)
- Best for: suspicious package behavior and metadata patterns
- Role in MetaMCP: malware-oriented supply-chain lane

### 2) Known Vulnerability Auditing

- **pip-audit** (PyPA) and/or **OSV-Scanner**
- Best for: CVE/advisory-backed vulnerable dependencies
- Role in MetaMCP: dependency vulnerability baseline lane

### 3) Code Security Rules

- **Semgrep** and **CodeQL**
- Best for: risky code patterns, taint paths, query-based security checks
- Role in MetaMCP: repo code risk lane (complements MCP-specific scanners)

### 4) Container/Image Supply Chain

- **Trivy** (with pinned and trusted execution path)
- Best for: image/package/IaC vulnerability and misconfiguration scanning
- Role in MetaMCP: runtime/deployment lane

### 5) Agentic Governance/Policy Layer

- **DefenseClaw** (`cisco-ai-defense/defenseclaw`)
- Best for: governance/policy-oriented security workflows
- Role in MetaMCP: advisory enrichment lane first, gating candidate later

## MetaMCP Mapping

Map external scanners into adapter classes under dynamic assessment:

- `adapter_guarddog`
- `adapter_pip_audit`
- `adapter_osv`
- `adapter_semgrep`
- `adapter_codeql`
- `adapter_trivy`
- `adapter_defenseclaw` (advisory trial mode initially)

All adapters should emit the same normalized finding schema used by dynamic assessment reports.

## DefenseClaw Adoption Rule

- start as **advisory-only** for 2-4 weeks
- collect quality metrics:
  - false-positive rate
  - reproducibility
  - remediation usefulness
- promote to blocking gate only if trial quality is acceptable

## Practical Controls (Immediate)

- pin dependency versions in CI and production builds
- require lockfiles and verify integrity before install
- run malware-heuristic scan before vuln scan in release lane
- quarantine suspicious dependency updates until manual review
- keep an emergency denylist for compromised package versions

## Dependency Upgrade Cooling-Off Policy

Adopt delayed rollout by default for dependency/tooling upgrades:

- **Default hold period:** 7 days after upstream release before production adoption.
- **Exception path:** critical security fix with documented CVE risk may bypass hold after explicit approval.
- **Pre-adoption checks during hold:**
  - scan release notes/issues for incident signals
  - monitor ecosystem chatter for breakage or compromise indicators
  - run full scanner suite in staging against candidate version
- **Progressive rollout:**
  - dev/test first
  - canary subset
  - full rollout only after no critical findings/regressions

Rationale: reduce exposure to same-day supply-chain compromises and unstable releases while still keeping dependencies reasonably current.

## Proposed CI Lanes

- **PR lane**: quick malware heuristics + changed-deps vulnerability audit
- **Nightly lane**: full dependency tree + semgrep/codeql
- **Release lane**: full suite + signed artifacts + immutable report archive

## Caveats

- no single scanner catches all supply-chain compromise patterns
- malware heuristics can be noisy; require reviewer workflow
- scanner tools themselves are part of supply chain and must be pinned/verified
