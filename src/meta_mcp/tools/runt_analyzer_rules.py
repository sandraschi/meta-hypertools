"""Declarative rule system for SOTA compliance evaluation (2026).

Evaluates MCP repositories against June 2026 fleet standards from
mcp-central-docs/standards/. Rules are declared as Rule dataclass
instances and evaluated by evaluate_rules().

Standards referenced:
- TOOL_DESIGN_STANDARDS.md (Portmanteau, Prefab, docstring SOTA)
- WEBAPP_SOTA_STANDARDS.md (React/Vite/Bun/Tailwind/Zustand)
- tauri_nsis_building.md (Tauri 2.0, NSIS, embedded backend)
- MCPB_PACKAGING_STANDARDS.md (MCPB layout)
- PACKAGING_STANDARDS.md (llms.txt, glama.json)
- chat_skills_prefab_standard.md (Prefab, dark mode, data-testid)
- session_context_injection.md (cursorrules/claude-plugin)
- playwright_e2e_sota.md (Playwright tests)
- cua_nsis_smoke_testing.md (CUA-NSIS certification)
- NAILED_PC_INSTALL_STANDARD.md (Require-Command, start.bat)
- JUNE_2026_STANDARDS_BAR.md (version floor)
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any


class RuleSeverity(Enum):
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class RuleCategory(Enum):
    VERSION = "version"
    TOOLS = "tools"
    STRUCTURE = "structure"
    WEB = "web"
    TESTING = "testing"
    QUALITY = "quality"
    CI_CD = "ci_cd"
    DOCUMENTATION = "documentation"
    INFRA = "infra"
    SAFETY = "safety"


@dataclass
class Rule:
    id: str
    name: str
    category: RuleCategory
    severity: RuleSeverity
    description: str
    recommendation: str
    check: Callable[[dict[str, Any]], bool]
    score_deduction: int = 0
    score_condition: Callable[[dict[str, Any]], int] | None = None
    condition: Callable[[dict[str, Any]], bool] | None = None
    message_template: str | None = None
    standard_ref: str | None = None

    def evaluate(self, info: dict[str, Any]) -> dict[str, Any] | None:
        if self.condition and not self.condition(info):
            return None
        if not self.check(info):
            return None
        message = self._format_message(info)
        score_deduction = self._calculate_deduction(info)
        return {
            "rule_id": self.id,
            "rule_name": self.name,
            "category": self.category.value,
            "severity": self.severity.value,
            "message": message,
            "recommendation": self.recommendation,
            "score_deduction": score_deduction,
            "standard_ref": self.standard_ref,
        }

    def _format_message(self, info: dict[str, Any]) -> str:
        if self.message_template:
            try:
                return self.message_template.format(**info)
            except KeyError:
                pass
        return self.description

    def _calculate_deduction(self, info: dict[str, Any]) -> int:
        if self.score_condition:
            return self.score_condition(info)
        return self.score_deduction


# ============================================================================
# Helper predicates
# ============================================================================

FASTMCP_LATEST = "3.4.2"
FASTMCP_RUNT_THRESHOLD = "3.4.2"
TOOL_PORTMANTEAU_THRESHOLD = 20


def _version_ge(v: str, threshold: str) -> bool:
    def _norm(s: str) -> list[int]:
        return [int(x) for x in s.split(".") if x.isdigit()] or [0]

    vp = _norm(v)
    tp = _norm(threshold)
    max_l = max(len(vp), len(tp))
    return (vp + [0] * (max_l - len(vp))) >= (tp + [0] * (max_l - len(tp)))


def _fastmcp_too_old(info: dict[str, Any]) -> bool:
    v = info.get("fastmcp_version", "")
    if not v:
        return True
    return not _version_ge(v, FASTMCP_RUNT_THRESHOLD)


def _portmanteau_needed(info: dict[str, Any]) -> bool:
    return info.get("tool_count", 0) > TOOL_PORTMANTEAU_THRESHOLD and not info.get("has_portmanteau", False)


def _tool_count_condition(info: dict[str, Any]) -> bool:
    return info.get("tool_count", 0) > 0


def _large_repo_condition(info: dict[str, Any]) -> bool:
    return info.get("tool_count", 0) >= 10


def _has_webapp(info: dict[str, Any]) -> bool:
    return info.get("has_webapp", False)


def _has_native(info: dict[str, Any]) -> bool:
    return info.get("has_native_dir", False)


def _dynamic_print_deduction(info: dict[str, Any]) -> int:
    c = info.get("print_statement_count", 0)
    return 10 if c > 5 else (5 if c > 0 else 0)


def _dynamic_lazy_error_deduction(info: dict[str, Any]) -> int:
    c = info.get("lazy_error_msg_count", 0)
    return 10 if c >= 5 else (5 if c > 0 else 0)


# ============================================================================
# RULE DEFINITIONS  June 2026 Fleet Standards
# ============================================================================

SOTA_RULES: list[Rule] = [
    # ------------------------------------------------------------------
    # VERSION  FastMCP must be >= 3.4.2
    # ------------------------------------------------------------------
    Rule(
        id="fastmcp_version",
        name="FastMCP Version",
        category=RuleCategory.VERSION,
        severity=RuleSeverity.CRITICAL,
        description="FastMCP version is too old",
        recommendation=f"Upgrade to FastMCP {FASTMCP_LATEST}",
        check=_fastmcp_too_old,
        score_deduction=20,
        message_template="FastMCP {fastmcp_version} < {fastmcp_runt_threshold}",
        standard_ref="JUNE_2026_STANDARDS_BAR.md",
    ),
    Rule(
        id="sampling_support_missing",
        name="MCP Sampling Support",
        category=RuleCategory.VERSION,
        severity=RuleSeverity.WARNING,
        description="Missing MCP sampling (ctx.sample) support",
        recommendation="Add ctx.sample() for agentic reasoning within tools",
        check=lambda i: not i.get("has_sampling_support", False),
        score_deduction=10,
        standard_ref="TOOL_DESIGN_STANDARDS.md 2.1",
    ),
    Rule(
        id="conversational_returns_missing",
        name="Conversational Tool Returns",
        category=RuleCategory.DOCUMENTATION,
        severity=RuleSeverity.WARNING,
        description="Tools lack conversational return pattern (message + data)",
        recommendation="Return dict with 'message' + 'data' keys for dialogic wrapping",
        check=lambda i: not i.get("has_conversational_returns", False),
        score_deduction=10,
        standard_ref="TOOL_DESIGN_STANDARDS.md 4.2",
    ),
    # FastMCP 3.4.2+ capability rules
    Rule(
        id="prompts_missing",
        name="FastMCP Prompts (@mcp.prompt)",
        category=RuleCategory.VERSION,
        severity=RuleSeverity.INFO,
        description="Server does not register @mcp.prompt() prompts",
        recommendation="Add @mcp.prompt() for reusable agent instructions",
        check=lambda i: not i.get("has_mcp_prompts", False),
        condition=_tool_count_condition,
        score_deduction=5,
        standard_ref="SOTA_REQUIREMENTS.md 2.1",
    ),
    Rule(
        id="resources_missing",
        name="FastMCP Resources (@mcp.resource)",
        category=RuleCategory.VERSION,
        severity=RuleSeverity.INFO,
        description="Server does not register @mcp.resource() resources",
        recommendation="Add @mcp.resource() for dynamic data streams",
        check=lambda i: not i.get("has_mcp_resources", False),
        condition=_tool_count_condition,
        score_deduction=5,
        standard_ref="SOTA_REQUIREMENTS.md 2.1",
    ),
    Rule(
        id="output_schema_missing",
        name="FastMCP output_schema Parameter",
        category=RuleCategory.VERSION,
        severity=RuleSeverity.INFO,
        description="Tools do not use output_schema= in @mcp.tool() decorator",
        recommendation="Add output_schema= for machine-readable return shapes",
        check=lambda i: not i.get("has_output_schema", False),
        condition=_tool_count_condition,
        score_deduction=3,
        standard_ref="TOOL_DESIGN_STANDARDS.md 8",
    ),
    Rule(
        id="skills_provider_missing",
        name="FastMCP Skills Provider",
        category=RuleCategory.VERSION,
        severity=RuleSeverity.INFO,
        description="Server does not register a SkillsDirectoryProvider",
        recommendation="Add SkillsDirectoryProvider to expose skill:// resources",
        check=lambda i: not i.get("has_skills_provider", False),
        condition=_tool_count_condition,
        score_deduction=3,
        standard_ref="TOOL_DESIGN_STANDARDS.md 2.3",
    ),
    # ------------------------------------------------------------------
    # TOOLS  portmanteau, help, prefab, dual transport
    # ------------------------------------------------------------------
    Rule(
        id="portmanteau_missing",
        name="Portmanteau Pattern",
        category=RuleCategory.TOOLS,
        severity=RuleSeverity.CRITICAL,
        description=f"Many tools without portmanteau pattern (>{TOOL_PORTMANTEAU_THRESHOLD})",
        recommendation="Refactor to portmanteau tools with operation enum",
        check=_portmanteau_needed,
        score_deduction=25,
        message_template="{tool_count} tools without portmanteau (threshold: {TOOL_PORTMANTEAU_THRESHOLD})",
        standard_ref="TOOL_DESIGN_STANDARDS.md 1",
    ),
    Rule(
        id="help_tool_missing",
        name="Help Tool",
        category=RuleCategory.TOOLS,
        severity=RuleSeverity.CRITICAL,
        description="No help tool for discovery",
        recommendation="Add help() tool returning markdown docs",
        check=lambda i: not i.get("has_help_tool", False),
        condition=_tool_count_condition,
        score_deduction=10,
        standard_ref="mcp_registration.md 1",
    ),
    Rule(
        id="status_tool_missing",
        name="Status/Health Tool",
        category=RuleCategory.TOOLS,
        severity=RuleSeverity.CRITICAL,
        description="No status/health tool",
        recommendation="Add status() or health() tool returning diagnostics",
        check=lambda i: not i.get("has_status_tool", False),
        condition=_tool_count_condition,
        score_deduction=10,
        standard_ref="tauri_nsis_building.md (health endpoint)",
    ),
    Rule(
        id="prefab_coverage_missing",
        name="Prefab UI Coverage",
        category=RuleCategory.TOOLS,
        severity=RuleSeverity.WARNING,
        description="List/status tools without Prefab UI surface",
        recommendation="Add PrefabApp to list, status, and stats tools",
        check=lambda i: not i.get("has_prefab_coverage", False),
        condition=_tool_count_condition,
        score_deduction=10,
        standard_ref="TOOL_DESIGN_STANDARDS.md 4.4",
    ),
    Rule(
        id="dual_transport_missing",
        name="Dual Transport (stdio + HTTP)",
        category=RuleCategory.TOOLS,
        severity=RuleSeverity.WARNING,
        description="Server lacks dual transport (both stdio and streamable HTTP)",
        recommendation="Add --serve mode or MCP_PORT env var detection to run_server.py",
        check=lambda i: not i.get("has_dual_transport", False),
        score_deduction=10,
        standard_ref="tauri_nsis_building.md (Dual Transport Requirement)",
    ),
    # ------------------------------------------------------------------
    # STRUCTURE  MCPB, llms.txt, .env.example, Tauri, port registry
    # ------------------------------------------------------------------
    Rule(
        id="mcpb_missing",
        name="MCPB Bundle (Claude Desktop)",
        category=RuleCategory.STRUCTURE,
        severity=RuleSeverity.WARNING,
        description="No MCPB bundle for Claude Desktop distribution",
        recommendation="Add manifest.json + assets/ + src/ for mcpb pack",
        check=lambda i: not i.get("has_mcpb", False),
        score_deduction=10,
        standard_ref="MCPB_PACKAGING_STANDARDS.md",
    ),
    Rule(
        id="glama_json_missing",
        name="Glama Registry Entry",
        category=RuleCategory.STRUCTURE,
        severity=RuleSeverity.WARNING,
        description="No glama.json for Glama MCP registry",
        recommendation="Add glama.json at repo root for registry indexing",
        check=lambda i: not i.get("has_glama_json", False),
        score_deduction=5,
        standard_ref="PACKAGING_STANDARDS.md 3.1",
    ),
    Rule(
        id="llms_txt_missing",
        name="LLM Index (llms.txt)",
        category=RuleCategory.DOCUMENTATION,
        severity=RuleSeverity.WARNING,
        description="Missing llms.txt for LLM discovery",
        recommendation="Create llms.txt with links + summary referencing llms-full.txt",
        check=lambda i: not i.get("has_llms_txt", False),
        score_deduction=8,
        standard_ref="PACKAGING_STANDARDS.md 5",
    ),
    Rule(
        id="llms_full_missing",
        name="Full LLM Doc (llms-full.txt)",
        category=RuleCategory.DOCUMENTATION,
        severity=RuleSeverity.WARNING,
        description="Missing llms-full.txt with full tool/API docs",
        recommendation="Create llms-full.txt with tools, env, architecture, troubleshooting",
        check=lambda i: not i.get("has_llms_full_txt", False),
        score_deduction=8,
        standard_ref="PACKAGING_STANDARDS.md 5",
    ),
    Rule(
        id="env_example_missing",
        name="Environment Template",
        category=RuleCategory.STRUCTURE,
        severity=RuleSeverity.WARNING,
        description="No .env.example at repo root",
        recommendation="Create .env.example with all config keys documented",
        check=lambda i: not i.get("has_env_example", False),
        score_deduction=5,
        standard_ref="tauri_nsis_building.md (bundle .env.example, NOT .env)",
    ),
    Rule(
        id="tauri_nsis_missing",
        name="Tauri/NSIS Desktop Wrapper",
        category=RuleCategory.STRUCTURE,
        severity=RuleSeverity.INFO,
        description="No Tauri 2.0 wrapper for desktop distribution",
        recommendation="Add native/ with Tauri 2.0 conf and NSIS build pipeline",
        check=lambda i: not i.get("has_native_dir", False),
        condition=_has_webapp,
        score_deduction=5,
        standard_ref="tauri_nsis_building.md",
    ),
    Rule(
        id="port_adjacency_violation",
        name="Port Adjacency",
        category=RuleCategory.STRUCTURE,
        severity=RuleSeverity.WARNING,
        description="Backend/frontend ports not adjacent or outside 10700-11500",
        recommendation="Allocate adjacent ports from 10700-11500 range",
        check=lambda i: not i.get("has_adjacent_ports", True),
        condition=_has_webapp,
        score_deduction=5,
        standard_ref="WEBAPP_PORTS.md (Adjacency Rule)",
    ),
    Rule(
        id="aspec_file_missing",
        name="PyInstaller Spec File",
        category=RuleCategory.STRUCTURE,
        severity=RuleSeverity.WARNING,
        description="No {repo}-backend.spec for PyInstaller build",
        recommendation="Create spec file with strip=False, upx=False, noarchive=True",
        check=lambda i: not i.get("has_pyinstaller_spec", False),
        score_deduction=5,
        standard_ref="tauri_nsis_building.md (spec template)",
    ),
    # ------------------------------------------------------------------
    # WEB  Bun, Biome, TailwindCSS, dark mode, data-testid
    # ------------------------------------------------------------------
    Rule(
        id="bun_missing",
        name="Bun Package Manager",
        category=RuleCategory.WEB,
        severity=RuleSeverity.WARNING,
        description="Using npm instead of fleet-standard Bun",
        recommendation="Switch to Bun: remove package-lock.json, add bun.lock",
        check=lambda i: i.get("using_npm", False) and i.get("has_webapp", False),
        condition=_has_webapp,
        score_deduction=5,
        standard_ref="WEBAPP_SOTA_STANDARDS.md I",
    ),
    Rule(
        id="biome_missing",
        name="Biome Linter (JS/TS)",
        category=RuleCategory.WEB,
        severity=RuleSeverity.WARNING,
        description="No Biome configured for JS/TS linting",
        recommendation="Add biome.json and run biome check --write",
        check=lambda i: not i.get("has_biome", False),
        condition=_has_webapp,
        score_deduction=5,
        standard_ref="WEBAPP_SOTA_STANDARDS.md",
    ),
    Rule(
        id="tailwindcss_missing",
        name="TailwindCSS",
        category=RuleCategory.WEB,
        severity=RuleSeverity.WARNING,
        description="Webapp not using TailwindCSS",
        recommendation="Add TailwindCSS for consistent styling",
        check=lambda i: not i.get("has_tailwindcss", False),
        condition=_has_webapp,
        score_deduction=5,
        standard_ref="WEBAPP_SOTA_STANDARDS.md I",
    ),
    Rule(
        id="zustand_missing",
        name="Zustand State Management",
        category=RuleCategory.WEB,
        severity=RuleSeverity.INFO,
        description="No Zustand for state management",
        recommendation="Add Zustand for lightweight persistent state",
        check=lambda i: not i.get("has_zustand", False),
        condition=_has_webapp,
        score_deduction=3,
        standard_ref="WEBAPP_SOTA_STANDARDS.md I",
    ),
    Rule(
        id="lucide_missing",
        name="Lucide Icons",
        category=RuleCategory.WEB,
        severity=RuleSeverity.INFO,
        description="Not using Lucide React icons",
        recommendation="Replace icon lib with lucide-react",
        check=lambda i: not i.get("has_lucide", False),
        condition=_has_webapp,
        score_deduction=3,
        standard_ref="WEBAPP_SOTA_STANDARDS.md I",
    ),
    Rule(
        id="dark_mode_missing",
        name="Dark Mode (SOTA)",
        category=RuleCategory.WEB,
        severity=RuleSeverity.WARNING,
        description="App not permanently dark (color-scheme: dark missing)",
        recommendation="Set color-scheme: dark and use Zinc/Slate dark palette",
        check=lambda i: not i.get("has_dark_mode", False),
        condition=_has_webapp,
        score_deduction=5,
        standard_ref="chat_skills_prefab_standard.md 7",
    ),
    Rule(
        id="data_testid_missing",
        name="data-testid Attributes",
        category=RuleCategory.WEB,
        severity=RuleSeverity.INFO,
        description="No data-testid attributes on interactive elements",
        recommendation="Add data-testid to KPIs, buttons, nav links for CUA/Playwright",
        check=lambda i: not i.get("has_data_testid", False),
        condition=_has_webapp,
        score_deduction=3,
        standard_ref="chat_skills_prefab_standard.md 1.9",
    ),
    Rule(
        id="framer_motion_missing",
        name="Framer Motion",
        category=RuleCategory.WEB,
        severity=RuleSeverity.INFO,
        description="No Framer Motion animations",
        recommendation="Add Framer Motion for micro-interactions",
        check=lambda i: not i.get("has_framer_motion", False),
        condition=_has_webapp,
        score_deduction=2,
        standard_ref="WEBAPP_SOTA_STANDARDS.md I",
    ),
    # ------------------------------------------------------------------
    # TESTING  pytest, Playwright E2E, CUA-NSIS
    # ------------------------------------------------------------------
    Rule(
        id="tests_missing",
        name="Test Directory",
        category=RuleCategory.TESTING,
        severity=RuleSeverity.CRITICAL,
        description="No test directory",
        recommendation="Add tests/ directory with unit tests",
        check=lambda i: not i.get("has_tests", False),
        condition=_large_repo_condition,
        score_deduction=15,
    ),
    Rule(
        id="pytest_config_missing",
        name="Pytest Configuration",
        category=RuleCategory.TESTING,
        severity=RuleSeverity.WARNING,
        description="No pytest configuration in pyproject.toml",
        recommendation="Add [tool.pytest.ini_options] to pyproject.toml",
        check=lambda i: not i.get("has_pytest_config", False),
        score_deduction=5,
    ),
    Rule(
        id="playwright_e2e_missing",
        name="Playwright E2E Tests",
        category=RuleCategory.TESTING,
        severity=RuleSeverity.WARNING,
        description="No Playwright E2E tests for webapp",
        recommendation="Add webapp/e2e/ with Fleet Audit tests (health + frontend loads)",
        check=lambda i: not i.get("has_playwright_e2e", False),
        condition=_has_webapp,
        score_deduction=10,
        standard_ref="playwright_e2e_sota.md",
    ),
    Rule(
        id="cua_nsis_missing",
        name="CUA-NSIS Smoke Test",
        category=RuleCategory.TESTING,
        severity=RuleSeverity.WARNING,
        description="No CUA-NSIS smoke test for NSIS installer",
        recommendation="Add scripts/cua-smoke.py + just cua-nsis-test recipe",
        check=lambda i: not i.get("has_cua_nsis", False),
        condition=_has_native,
        score_deduction=10,
        standard_ref="cua_nsis_smoke_testing.md",
    ),
    # ------------------------------------------------------------------
    # QUALITY  ruff, logging, bare except, docstring 2026
    # ------------------------------------------------------------------
    Rule(
        id="ruff_missing",
        name="Ruff Linting (Python)",
        category=RuleCategory.QUALITY,
        severity=RuleSeverity.CRITICAL,
        description="No ruff linting configured",
        recommendation="Add [tool.ruff] to pyproject.toml and run ruff check",
        check=lambda i: not i.get("has_ruff", False),
        score_deduction=10,
    ),
    Rule(
        id="logging_missing",
        name="Proper Logging",
        category=RuleCategory.QUALITY,
        severity=RuleSeverity.CRITICAL,
        description="No proper logging (logging.getLogger or structlog)",
        recommendation="Add logging.getLogger or structlog, replace print() calls",
        check=lambda i: not i.get("has_proper_logging", False),
        score_deduction=10,
    ),
    Rule(
        id="print_statements",
        name="Print Statements",
        category=RuleCategory.QUALITY,
        severity=RuleSeverity.WARNING,
        description="Print statements in non-test code",
        recommendation="Replace print() with logger calls",
        check=lambda i: i.get("print_statement_count", 0) > 0,
        score_condition=_dynamic_print_deduction,
        message_template="{print_statement_count} print() calls in non-test code",
    ),
    Rule(
        id="bare_except",
        name="Bare Except Clauses",
        category=RuleCategory.QUALITY,
        severity=RuleSeverity.CRITICAL,
        description="Bare except clauses (>=3)",
        recommendation="Use specific exception types, never bare except:",
        check=lambda i: i.get("bare_except_count", 0) >= 3,
        score_deduction=10,
        message_template="{bare_except_count} bare except clauses",
    ),
    Rule(
        id="lazy_errors",
        name="Non-Informative Error Messages",
        category=RuleCategory.QUALITY,
        severity=RuleSeverity.WARNING,
        description="Non-informative error messages",
        recommendation="Use descriptive error messages with context",
        check=lambda i: i.get("lazy_error_msg_count", 0) > 0,
        score_condition=_dynamic_lazy_error_deduction,
        message_template="{lazy_error_msg_count} non-informative error messages",
    ),
    Rule(
        id="docstring_2026_missing",
        name="Docstring SOTA 2026 (Annotated + Field)",
        category=RuleCategory.DOCUMENTATION,
        severity=RuleSeverity.WARNING,
        description="Not using Annotated[..., Field(description=...)] pattern",
        recommendation="Move Args: block to Annotated Field descriptions, use ## Return / ## Examples",
        check=lambda i: not i.get("has_docstring_2026", False),
        condition=_tool_count_condition,
        score_deduction=10,
        standard_ref="docstrings_sota.md",
    ),
    Rule(
        id="old_style_args_docstrings",
        name="Legacy Args: Docstrings (Pre-3.4.3)",
        category=RuleCategory.DOCUMENTATION,
        severity=RuleSeverity.WARNING,
        description="Tools use old-style Args: blocks instead of Annotated Field descriptions",
        recommendation="Replace Args: with Annotated Field descriptions + ## Return / ## Examples",
        check=lambda i: i.get("has_old_style_args_docstrings", False),
        condition=_tool_count_condition,
        score_deduction=5,
        standard_ref="docstrings_sota.md 1",
    ),
    Rule(
        id="missing_return_format_section",
        name="Missing ## Return Format in Docstrings",
        category=RuleCategory.DOCUMENTATION,
        severity=RuleSeverity.WARNING,
        description="Tool docstrings missing ## Return Format section",
        recommendation="Add ## Return Format section to docstrings showing JSON structure",
        check=lambda i: not i.get("has_return_format_section", False),
        condition=_tool_count_condition,
        score_deduction=5,
        standard_ref="docstrings_sota.md 2",
    ),
    Rule(
        id="missing_examples_section",
        name="Missing ## Examples in Docstrings",
        category=RuleCategory.DOCUMENTATION,
        severity=RuleSeverity.WARNING,
        description="Tool docstrings missing ## Examples section",
        recommendation="Add ## Examples section with 1-3 concrete Python calls",
        check=lambda i: not i.get("has_examples_section", False),
        condition=_tool_count_condition,
        score_deduction=5,
        standard_ref="docstrings_sota.md 2",
    ),
    Rule(
        id="unicode_in_docstrings",
        name="Unicode in Docstrings",
        category=RuleCategory.DOCUMENTATION,
        severity=RuleSeverity.CRITICAL,
        description="Unicode characters found in docstrings (crash risk)",
        recommendation="Replace Unicode with ASCII alternatives",
        check=lambda i: not i.get("ascii_only_docstrings", True),
        score_deduction=15,
    ),
    # ------------------------------------------------------------------
    # CI_CD
    # ------------------------------------------------------------------
    Rule(
        id="ci_missing",
        name="CI/CD Workflows",
        category=RuleCategory.CI_CD,
        severity=RuleSeverity.CRITICAL,
        description="No CI/CD workflows",
        recommendation="Add GitHub Actions workflow with ruff + pytest",
        check=lambda i: not i.get("has_ci", False),
        condition=_large_repo_condition,
        score_deduction=20,
    ),
    Rule(
        id="ci_too_many",
        name="CI Workflow Count",
        category=RuleCategory.CI_CD,
        severity=RuleSeverity.WARNING,
        description="Too many CI workflows (>3)",
        recommendation="Consolidate to single CI workflow",
        check=lambda i: i.get("ci_workflows", 0) > 3,
        score_deduction=5,
        message_template="{ci_workflows} CI workflows (recommend: 1)",
    ),
    Rule(
        id="justfile_missing",
        name="Justfile Recipes",
        category=RuleCategory.CI_CD,
        severity=RuleSeverity.INFO,
        description="No justfile for discoverable recipes",
        recommendation="Add justfile with serve, test, lint, fmt recipes",
        check=lambda i: not i.get("has_justfile", False),
        score_deduction=3,
        standard_ref="PACKAGING_STANDARDS.md 5",
    ),
    # ------------------------------------------------------------------
    # INFRA  start.ps1, port clearing, run_server.py
    # ------------------------------------------------------------------
    Rule(
        id="start_ps1_missing",
        name="Start Script (start.ps1 + start.bat)",
        category=RuleCategory.INFRA,
        severity=RuleSeverity.WARNING,
        description="Missing start.ps1 / start.bat for dev launch",
        recommendation="Add start.ps1 with port zombie clearing + auto-open browser",
        check=lambda i: not i.get("has_start_scripts", False),
        condition=_has_webapp,
        score_deduction=5,
        standard_ref="WEBAPP_PORTS.md (start.ps1 pattern)",
    ),
    Rule(
        id="run_server_py_missing",
        name="PyInstaller Entry Point (run_server.py)",
        category=RuleCategory.INFRA,
        severity=RuleSeverity.WARNING,
        description="Missing run_server.py for PyInstaller build",
        recommendation="Create run_server.py with dual transport (MCP_PORT -> HTTP)",
        check=lambda i: not i.get("has_run_server_py", False),
        score_deduction=5,
        standard_ref="tauri_nsis_building.md (Dual Transport Requirement)",
    ),
    # ------------------------------------------------------------------
    # SAFETY  session context injection, bak/dryrun
    # ------------------------------------------------------------------
    Rule(
        id="session_context_missing",
        name="Session Context Injection",
        category=RuleCategory.SAFETY,
        severity=RuleSeverity.INFO,
        description="No session context (.cursorrules / .claude-plugin / .windsurfrules)",
        recommendation="Add .cursorrules + .claude-plugin/hooks for tool-awareness at session start",
        check=lambda i: not i.get("has_session_context", False),
        condition=_tool_count_condition,
        score_deduction=5,
        standard_ref="session_context_injection.md",
    ),
    Rule(
        id="bak_dryrun_missing",
        name="Batch Mutation Safety (--bak / --dryrun)",
        category=RuleCategory.SAFETY,
        severity=RuleSeverity.INFO,
        description="Fix tools lack --bak backup or --dryrun safety flags",
        recommendation="Add --bak (timestamped .bak) and --dry-run (preview) to all mutation tools",
        check=lambda i: not i.get("has_bak_dryrun_pattern", True),
        condition=_tool_count_condition,
        score_deduction=3,
        standard_ref="GIT_REPOSITORY_SAFETY.md (Batch Mutation Safety)",
    ),
    Rule(
        id="csp_cors_tauri_missing",
        name="CORS Tauri Origins",
        category=RuleCategory.SAFETY,
        severity=RuleSeverity.WARNING,
        description="Backend CORS missing tauri://localhost origins",
        recommendation="Add tauri://localhost, http://tauri.localhost to CORS allow_origins",
        check=lambda i: not i.get("has_tauri_cors", True),
        condition=_has_native,
        score_deduction=5,
        standard_ref="cua_nsis_smoke_testing.md (Tauri CORS Requirement)",
    ),
    Rule(
        id="tauri_bundles_env",
        name="Tauri Bundles .env (Security Leak)",
        category=RuleCategory.SAFETY,
        severity=RuleSeverity.CRITICAL,
        description="tauri.conf.json resources includes .env instead of .env.example",
        recommendation="Change bundle.resources to .env.example, never bundle real .env",
        check=lambda i: i.get("tauri_bundles_env", False),
        condition=_has_native,
        score_deduction=20,
        standard_ref="tauri_nsis_building.md (bundle .env.example, NOT .env)",
    ),
    Rule(
        id="api_base_port_mismatch",
        name="API_BASE Points to Frontend Port",
        category=RuleCategory.INFRA,
        severity=RuleSeverity.WARNING,
        description="API_BASE in api.ts points to frontend port  breaks in Tauri production (no Vite proxy)",
        recommendation="Change API_BASE to backend port (e.g. http://127.0.0.1:BACKEND_PORT)",
        check=lambda i: i.get("api_base_port_mismatch", False),
        condition=_has_native,
        score_deduction=10,
        standard_ref="tauri_nsis_building.md (tauri.conf.json notes)",
    ),
    Rule(
        id="stale_bak_files",
        name="Stale .bak Files in Source Tree",
        category=RuleCategory.QUALITY,
        severity=RuleSeverity.INFO,
        description="Stale .bak files found in src/ or webapp/  cleanup residue",
        recommendation="Remove stale .bak files: git clean or delete them",
        check=lambda i: i.get("stale_bak_file_count", 0) > 0,
        score_deduction=2,
        message_template="{stale_bak_file_count} stale .bak files in source directories",
    ),
    Rule(
        id="console_log_in_js",
        name="console.log in JS/TS (Debug Leak)",
        category=RuleCategory.QUALITY,
        severity=RuleSeverity.WARNING,
        description="console.log calls in JS/TS files  likely debug leftovers",
        recommendation="Remove console.log calls before shipping",
        check=lambda i: i.get("console_log_count", 0) > 3,
        score_deduction=3,
        message_template="{console_log_count} console.log calls in JS/TS files",
    ),
]


# ============================================================================
# Evaluation
# ============================================================================


def evaluate_rules(info: dict[str, Any]) -> dict[str, Any]:
    violations: list[dict[str, Any]] = []
    critical_violations: list[dict[str, Any]] = []
    total_deduction = 0

    for rule in SOTA_RULES:
        violation = rule.evaluate(info)
        if violation:
            violations.append(violation)
            total_deduction += violation["score_deduction"]
            if rule.severity == RuleSeverity.CRITICAL:
                critical_violations.append(violation)

    is_runt = len(critical_violations) > 0

    seen = set()
    unique_reasons = []
    for v in violations:
        m = v["message"]
        if m not in seen:
            seen.add(m)
            unique_reasons.append(m)

    seen_recs = set()
    unique_recommendations = []
    for v in violations:
        r = v["recommendation"]
        if r not in seen_recs:
            seen_recs.add(r)
            unique_recommendations.append(r)

    return {
        "violations": violations,
        "critical_violations": critical_violations,
        "is_runt": is_runt,
        "runt_reasons": unique_reasons,
        "recommendations": unique_recommendations,
        "score_deduction": total_deduction,
        "violation_count": len(violations),
        "critical_count": len(critical_violations),
        "sota_version": FASTMCP_LATEST,
    }


def calculate_sota_score(info: dict[str, Any], base_score: int = 100) -> int:
    result = evaluate_rules(info)
    score = base_score - result["score_deduction"]
    return max(0, min(100, score))


def get_rules_by_category(category: RuleCategory | None = None) -> list[Rule]:
    if category:
        return [r for r in SOTA_RULES if r.category == category]
    return SOTA_RULES.copy()


def get_rule_by_id(rule_id: str) -> Rule | None:
    for rule in SOTA_RULES:
        if rule.id == rule_id:
            return rule
    return None
