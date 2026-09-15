import asyncio
import os
import subprocess
import time
import urllib.request
from importlib.metadata import version as _pkg_version
from typing import Any, Literal

from fastmcp import Context, FastMCP

from meta_mcp.fleet_paths import meta_mcp_web_start_script, meta_mcp_web_url, optional_mcp_central_docs
from meta_mcp.services.diagnostics_service import DiagnosticsService
from meta_mcp.services.fleet_runtime_service import FleetRuntimeService
from meta_mcp.services.implementation_honesty_service import ImplementationHonestyService


def register_diagnostics_tools(mcp: FastMCP):
    """Register diagnostic tool suite with FastMCP."""

    service = DiagnosticsService()
    honesty_service = ImplementationHonestyService()

    async def _tool_catalog_impl(
        query: str | None,
        max_tools: int,
    ) -> dict[str, Any]:
        try:
            raw = await mcp.list_tools()
        except Exception as e:
            return {
                "success": False,
                "message": "Operation failed",
                "error": f"list_tools failed: {e}",
                "recovery_options": ["Restart Meta MCP", "Check FastMCP version"],
            }

        q = (query or "").strip().lower()
        cap = max(1, min(2000, int(max_tools)))
        rows: list[dict[str, Any]] = []
        for t in raw:
            name = getattr(t, "name", "") or ""
            desc = getattr(t, "description", None) or ""
            if q and q not in name.lower() and q not in (desc or "").lower():
                continue
            first = (desc.splitlines()[0] if desc else "").strip()
            if len(first) > 800:
                first = first[:800] + ""
            rows.append({"name": name, "description": first or None})
        rows.sort(key=lambda x: str(x.get("name", "")).lower())
        matched = len(rows)
        truncated = matched > cap
        if truncated:
            rows = rows[:cap]

        return {
            "success": True,
            "registered": len(raw),
            "matched": matched,
            "returned": len(rows),
            "truncated": truncated,
            "tools": rows,
            "note": (
                "Every tool: name + first line of docstring. "
                "Call help with no arguments for the full list. "
                "Optional query= filters by substring. "
                "HTTP API: GET /tools/list when the Meta MCP server is up."
            ),
        }

    @mcp.tool(name="diagnostics_ops")
    async def diagnostics_ops(
        operation: Literal["help", "overview", "unicode", "pwsh", "justfile", "audit_impl", "launcher", "refresh"],
        query: str | None = None,
        max_tools: int = 2000,
        sub_operation: str = "scan",
        repo_path: str | None = None,
        scan_mode: str = "comprehensive",
        auto_fix: bool = False,
        backup: bool = True,
        include_aliases: bool = True,
        fix: bool = False,
        target_path: str | None = None,
        mode: str = "audit",
        include_extensions: list[str] | None = None,
        max_findings: int = 500,
        baseline_path: str | None = None,
        url: str | None = None,
        start_if_down: bool = True,
        wait_seconds: int = 30,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Diagnostics, tool discovery, and standards validation (portmanteau).

        [RATIONALE]
        Consolidates 8 related operations into a single tool to prevent tool explosion while enabling full API coverage.

        ## Operations
        - **help**: List all registered MetaMCP tools
        - **overview**: Show MetaMCP platform overview and suite status
        - **unicode**: Scan for Unicode emoji that break Windows loggers
        - **pwsh**: Validate PowerShell scripts for native cmdlet compliance
        - **justfile**: Validate a justfile for fleet standards
        - **audit_impl**: Detect stub/mock/placeholder implementations
        - **launcher**: Open MetaMCP dashboard in the default browser
        - **refresh**: Sync fleet-webapp-manifest.json from repos

        ## Return Format
        {"success": bool, "operation": str, "message": str}

        ## Examples
        await diagnostics_ops(operation="help")
        await diagnostics_ops(operation="overview")
        """
        if operation == "help":
            return await _tool_catalog_impl(query, max_tools)
        elif operation == "overview":
            return await meta_mcp_help()
        elif operation == "unicode":
            return await emojibuster(
                operation=sub_operation,
                repo_path=repo_path or "*",
                scan_mode=scan_mode,
                auto_fix=auto_fix,
                backup=backup,
            )
        elif operation == "pwsh":
            return await powershell_tools(
                operation=sub_operation,
                repo_path=repo_path,
                scan_mode=scan_mode,
                include_aliases=include_aliases,
            )
        elif operation == "justfile":
            return await justfile_tools(
                repo_path=repo_path,
                fix=fix,
            )
        elif operation == "audit_impl":
            return await implementation_honesty_checker(
                target_path=target_path,
                mode=mode,
                include_extensions=include_extensions,
                max_findings=max_findings,
                baseline_path=baseline_path,
            )
        elif operation == "launcher":
            return await open_fleet_starts_launcher(
                url=url,
                start_if_down=start_if_down,
                wait_seconds=wait_seconds,
            )
        elif operation == "refresh":
            return await generate_fleet_starts_launcher(
                operation=sub_operation,
                dry_run=dry_run,
            )

    async def meta_mcp_help() -> dict[str, Any]:
        """Show MetaMCP platform overview. Legacy alias -- use diagnostics_ops(operation='overview')."""
        try:
            ver = _pkg_version("meta_mcp")
        except Exception:
            ver = "unknown"

        return {
            "success": True,
            "package": "meta_mcp",
            "version": ver,
            "summary": (
                "MetaMCP is a Swiss-army-knife MCP orchestrator: builders (scaffold_*), "
                "analyzers (runts, analyze_fleet, depot), scrubbers (Unicode, pwsh, stubs, secrets), "
                "fleet probes (cold-start, cold-install Phase 2b), repo inspiration, and dashboard."
            ),
            "suites": [
                "diagnostics",
                "analysis",
                "discovery",
                "scaffolding",
                "server_management",
                "tool_execution",
                "repository_analysis",
                "client_management",
                "token_analysis",
                "repo_packing",
                "repo_inspiration",
                "fleet_probes",
                "toolchains",
                "scheduler",
                "heartbeat",
            ],
            "highlights": {
                "builders": (
                    "scaffold_mcp_server, scaffold_app_fullstack, scaffold_landing_page -- dashboard Builders page"
                ),
                "analyzers": (
                    "analyze_mcp_runts, analyze_fleet, show_mcp_status, analyze_mcp_codebase; "
                    "analysis depot (~/.meta_mcp/analysis/); optional publish_analysis_to_mcd"
                ),
                "scrubbers": ("scan_mcp_unicode, validate_mcp_pwsh, audit_mcp_implementation, redact_secrets_audit"),
                "repo_inspiration": (
                    "inspire_repo(operation=structure|files|patterns|help) -- study public GitHub repos "
                    "without cloning; dashboard Repo Inspiration; docs/tools/repo-inspiration.md"
                ),
                "cold_install_phase_2b": (
                    "fleet_cold_install_probe -- preflight, mcpb (Claude only), multi-IDE stdio smoke; "
                    "execute=true generates sandbox scripts (guest run pending)"
                ),
                "cold_start_probe": (
                    "fleet_startup_probe -- batch start.ps1 health; Phase 2c Playwright UI smoke planned"
                ),
            },
            "fleet_probe_docs": {
                "architecture": "docs/fleet/FLEET_PROBE_ARCHITECTURE.md",
                "cold_install_probe": "docs/fleet/FLEET_COLD_INSTALL_PROBE.md",
                "phases_2b_2c": "docs/fleet/FLEET_COLD_INSTALL_PHASES_2B_2C.md",
                "program_tracker": "docs/fleet/FLEET_COLD_INSTALL_TODO.md",
                "scripts": "fleet_probes/README.md",
            },
            "next_steps": {
                "list_all_tools": "Call help() with no arguments -- lists every tool.",
                "builders": "scaffold_mcp_server / dashboard Builders; docs/tools/scaffolding.md",
                "analyzers": "analyze_mcp_runts, analyze_fleet; dashboard Analysis; docs/tools/analysis.md",
                "scrubbers": "scan_mcp_unicode, validate_mcp_pwsh, audit_mcp_implementation; Tool Lab",
                "repo_inspiration": "inspire_repo_help(); inspire_repo_structure_card; /repo-inspiration in dashboard.",
                "cold_install": (
                    "fleet_cold_install_probe / GET fleet cold-install report; "
                    "docs/fleet/FLEET_COLD_INSTALL_PROBE.md; Execute needs virtualization-mcp."
                ),
                "cold_start": (
                    "fleet_startup_probe / Fleet Cold-start tab; "
                    "Phase 2c Playwright -- docs/fleet/FLEET_COLD_INSTALL_PHASES_2B_2C.md"
                ),
                "fleet_analysis": "analyze_mcp_runts; publish_analysis_to_mcd when handbook root configured.",
                "local_llm": "Web dashboard Settings -- models via POST /api/v1/llm/models (Ollama/LM Studio proxy).",
                "fleet_starts_ui": f"open_fleet_starts_launcher() opens {meta_mcp_web_url()} (MetaMCP dashboard).",
                "refresh_fleet_registry": (
                    "generate_fleet_starts_launcher(operation='fastmcp_only' merges new repos; "
                    "'full_registry' rescans FLEET_REPOS_ROOT). No mcp-central-docs required."
                ),
            },
            "recommendations": [
                "Read README.md -- badges, GitHub description/topics, sandboxed cold-install, repo inspiration.",
                "INSTALL.md for stdio MCP, HTTP transport, and fleet probe env vars.",
                "help(query='keyword') narrows the catalog; list_mcp_tools and find_mcp_tools are aliases.",
                "MCP prompts: inspire_repo_study, meta_mcp_fleet_discovery. Skills: resource://meta-mcp/repo-inspiration/skills.",
            ],
        }

    async def emojibuster(
        operation: str,
        repo_path: str = "*",
        scan_mode: str = "comprehensive",
        auto_fix: bool = False,
        backup: bool = True,
        ctx: Context | None = None,
    ) -> dict[str, Any]:
        """Audit repository Unicode safety. Legacy alias -- use diagnostics_ops(operation='unicode')."""
        if operation == "fix" and not auto_fix:
            return service.create_response(False, "Auto-fix requires confirmation. Set auto_fix=True.")

        return await service.run_emojibuster(operation, repo_path, scan_mode=scan_mode, backup=backup)

    async def powershell_tools(
        operation: str,
        repo_path: str | None = None,
        scan_mode: str = "comprehensive",
        include_aliases: bool = True,
    ) -> dict[str, Any]:
        """Audit PowerShell native standards. Legacy alias -- use diagnostics_ops(operation='pwsh')."""
        return await service.run_powershell_tools(
            operation, repo_path, scan_mode=scan_mode, include_aliases=include_aliases
        )

    async def justfile_tools(
        repo_path: str,
        fix: bool = False,
    ) -> dict[str, Any]:
        """Audit justfile fleet standards. Legacy alias -- use diagnostics_ops(operation='justfile')."""
        return await service.validate_justfile(repo_path, fix=fix)

    async def implementation_honesty_checker(
        target_path: str,
        mode: str = "audit",
        include_extensions: list[str] | None = None,
        max_findings: int = 500,
        baseline_path: str | None = None,
    ) -> dict[str, Any]:
        """Detect stub implementations. Legacy alias -- use diagnostics_ops(operation='audit_impl')."""
        return await honesty_service.scan(
            target_path=target_path,
            mode=mode,
            include_extensions=include_extensions,
            max_findings=max_findings,
            baseline_path=baseline_path,
        )

    async def open_fleet_starts_launcher(
        url: str | None = None,
        start_if_down: bool = True,
        wait_seconds: int = 30,
    ) -> dict[str, Any]:
        """Launch fleet management UI. Legacy alias -- use diagnostics_ops(operation='launcher')."""
        url = (url or meta_mcp_web_url()).rstrip("/") + "/"

        if os.name != "nt":
            return {
                "success": False,
                "message": "Operation failed",
                "error": "This tool currently supports Windows hosts only.",
                "recovery_options": ["Open the URL manually from your client"],
            }

        wait_seconds = max(1, min(300, int(wait_seconds)))

        def _health_ok() -> bool:
            for suffix in ("/health", "/api/health", "/api/v1/health"):
                try:
                    with urllib.request.urlopen(  # noqa: S310
                        url.rstrip("/") + suffix, timeout=2
                    ) as r:
                        if 200 <= int(getattr(r, "status", 200)) < 500:
                            return True
                except Exception:
                    continue
            return False

        started = False
        if start_if_down and not _health_ok():
            start_ps1 = meta_mcp_web_start_script()
            if not start_ps1.is_file():
                return {
                    "success": False,
                    "message": "Operation failed",
                    "error": f"MetaMCP start script not found: {start_ps1}",
                    "recovery_options": [
                        "Set META_MCP_START_PS1 to web_sota/start.ps1",
                        f"Open {url} manually",
                    ],
                }
            try:
                subprocess.Popen(
                    [
                        "powershell",
                        "-NoProfile",
                        "-ExecutionPolicy",
                        "Bypass",
                        "-File",
                        str(start_ps1),
                    ],
                    cwd=str(start_ps1.parent),
                    creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0),
                )
                started = True
            except Exception as e:
                return {
                    "success": False,
                    "message": "Operation failed",
                    "error": f"Failed to start MetaMCP dashboard: {e}",
                    "recovery_options": [
                        f"Run {start_ps1} manually",
                        f"Open {url} manually",
                    ],
                }

            deadline = time.time() + wait_seconds
            while time.time() < deadline:
                if _health_ok():
                    break
                await asyncio.sleep(1)

        try:
            os.startfile(url)  # type: ignore[attr-defined]  # noqa: S606
        except Exception as e:
            return {
                "success": False,
                "message": "Operation failed",
                "error": f"Failed to open browser: {e}",
                "recovery_options": [f"Open {url} manually"],
            }

        return {
            "success": True,
            "result": {"url": url, "started_server": started},
            "message": "Launcher opened in default browser.",
        }

    async def generate_fleet_starts_launcher(
        operation: str = "fastmcp_only",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Sync fleet registry metadata. Legacy alias -- use diagnostics_ops(operation='refresh')."""
        op = (operation or "fastmcp_only").strip().lower().replace("-", "_")
        full_rescan = op in ("full_registry", "full", "regenerate", "generate_fleet_registry")
        merge_only = op in ("fastmcp_only", "fastmcp", "sync_fastmcp", "merge")
        if not full_rescan and not merge_only:
            return {
                "success": False,
                "message": "Operation failed",
                "error": f"Unknown operation: {operation!r}",
                "recovery_options": ["Use fastmcp_only or full_registry"],
            }

        runtime = FleetRuntimeService()
        try:
            result = await asyncio.to_thread(
                runtime.refresh_manifest_from_repos,
                dry_run=dry_run,
                full_rescan=full_rescan,
            )
        except Exception as e:
            return {
                "success": False,
                "message": "Operation failed",
                "error": str(e),
                "recovery_options": [
                    "Set FLEET_REPOS_ROOT to your fleet checkout root",
                    "Run refresh with dry_run=True first",
                ],
            }

        ok = result.get("success", False)
        handbook = optional_mcp_central_docs()
        recovery: list[str] = []
        if not ok:
            recovery.append("Ensure FLEET_REPOS_ROOT points at your *-mcp repos")
            if handbook:
                recovery.append(f"Optional handbook sync still available under {handbook}")
        return {
            "success": ok,
            "result": result,
            "message": (
                "Fleet manifest refreshed from repo scan."
                if ok and not dry_run
                else "Dry-run manifest refresh completed."
                if ok
                else "Manifest refresh failed."
            ),
            "recovery_options": recovery,
        }
