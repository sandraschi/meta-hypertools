# Scanner Adapter Contract (MetaMCP)

## Purpose

Define a single adapter contract so heterogeneous scanners (MCP-specific, supply-chain, code, container, dynamic) can plug into MetaMCP and produce comparable outputs.

## Design Principles

- one normalized finding schema across all adapters
- deterministic adapter metadata (name, version, mode, config hash)
- graceful degradation on adapter errors
- explicit evidence and reproducibility fields

## Adapter Responsibilities

Each adapter must:

- declare capabilities and required inputs
- execute scanner command/API safely
- normalize raw output into MetaMCP finding schema
- emit adapter diagnostics (timings, failures, partial coverage)

## Adapter Interface (Conceptual)

```python
class ScannerAdapter(Protocol):
    adapter_id: str
    adapter_version: str

    def capabilities(self) -> dict: ...
    def validate_config(self, config: dict) -> list[str]: ...
    def run(self, target: dict, config: dict) -> "AdapterRunResult": ...
    def normalize(self, raw_result: dict, context: dict) -> "NormalizedAdapterOutput": ...
```

## Required Adapter Metadata

- `adapter_id` (example: `adapter_guarddog`)
- `adapter_version`
- `scanner_name`
- `scanner_version`
- `execution_mode` (`local_cli | api | container`)
- `config_fingerprint` (hash of effective config)
- `started_at`, `finished_at`, `duration_ms`

## Normalized Output Schema (Core)

### `AdapterRunResult`

- `success`: bool
- `partial`: bool
- `errors`: list of adapter-level errors
- `warnings`: list of adapter-level warnings
- `raw_artifact_paths`: list of saved raw outputs
- `normalized`: `NormalizedAdapterOutput`

### `NormalizedAdapterOutput`

- `coverage`
  - `target_type` (`repo | dependency_tree | mcp_endpoint | container | webapp`)
  - `scope_summary`
  - `confidence` (0-100)
- `findings`: list[`NormalizedFinding`]
- `stats`
  - counts by severity
  - total scanned items
  - skipped items

### `NormalizedFinding`

- `finding_id` (stable per adapter+signal where possible)
- `source_adapter_id`
- `category` (`supply_chain | code_security | mcp_interface | mcp_behavior | webapp | runtime`)
- `severity` (`critical | high | medium | low | info`)
- `title`
- `summary`
- `evidence`
  - `snippet` (optional)
  - `location` (file/path/tool/dependency/url)
  - `raw_reference` (pointer to raw artifact record)
- `impact`
- `likelihood`
- `affected_asset`
- `repro_steps` (list)
- `recommended_actions` (list)
- `tags` (list)
- `suppression_eligible` (bool)

## Severity Mapping Rules

Adapters must map native severity to MetaMCP levels using explicit tables.

Example:

- unknown/highest scanner severity without mapping => `high` fallback + warning
- "malicious package suspected" should map minimum `high`
- confirmed credential-stealer payload should map `critical`

## Error Handling Contract

Adapter errors must be explicit and non-silent:

- `config_error`: invalid adapter config
- `runtime_error`: scanner execution failure
- `parse_error`: raw output could not be parsed
- `timeout_error`: exceeded configured timeout
- `dependency_error`: required binary/image unavailable

A failed adapter should not crash the full orchestration unless marked `required=true`.

## Safety and Execution Requirements

- run scanners with pinned versions where possible
- forbid implicit network egress unless explicitly enabled
- redact secrets from logs/artifacts
- preserve raw output for audit, but never expose secrets in summaries
- support timeout and cancellation

## Target Descriptor Contract

All adapters receive a normalized `target` object:

- `target_id`
- `target_type`
- `repo_path` (if local)
- `mcp_endpoint` (if remote)
- `dependency_manifest_paths` (if present)
- `webapp_paths` (`webapp`, `web_sota` when present)

## Minimal Adapter Set (Phase 1)

- `adapter_mcp_scanner`
- `adapter_skill_scanner`
- `adapter_guarddog`
- `adapter_pip_audit`
- `adapter_osv` (optional if pip-audit with OSV backend already used)

## Optional Adapter Set (Phase 2+)

- `adapter_semgrep`
- `adapter_codeql`
- `adapter_trivy`
- `adapter_playwright_checks`
- `adapter_defenseclaw` (start advisory-only trial before any gate use)

## Advisory Trial Rule (DefenseClaw)

For `adapter_defenseclaw`, use a staged graduation path:

1. run in advisory mode only (no CI blocking)
2. collect 2-4 weeks of findings and triage outcomes
3. evaluate:
   - false-positive rate
   - reproducibility of findings
   - remediation actionability
4. promote to gate candidate only if quality thresholds are met

## Suppression and Governance Hooks

Normalized finding must support suppression matching keys:

- `source_adapter_id`
- `finding_id`
- `affected_asset`
- `rule_or_signature` (if available)

Suppression record fields (outside adapter, in orchestration layer):

- reason
- owner
- created_at
- expires_at

## Output Compatibility

Orchestration layer should render normalized output to:

- JSON (canonical)
- Markdown (human review)
- SARIF (where applicable)

Adapters may provide SARIF directly, but MetaMCP should still normalize into canonical JSON.

## Acceptance Criteria

- at least 3 adapters emit valid normalized findings
- same issue class from different adapters can be correlated by asset/tag/category
- adapter failures are visible without collapsing entire assessment run
- raw artifacts and normalized report remain cross-referencable
