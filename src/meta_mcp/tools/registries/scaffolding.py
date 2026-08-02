from typing import Any, Literal

from fastmcp import Context, FastMCP

from meta_mcp.services.scaffolding_service import ScaffoldingService


def register_scaffolding_tools(mcp: FastMCP):
    """Register scaffolding tool suite with FastMCP."""

    service = ScaffoldingService()

    @mcp.tool(name="scaffold_ops")
    async def scaffold_ops(
        operation: Literal[
            "fullstack",
            "landing_page",
            "mcp_server",
            "webshop",
            "game",
            "wisdom_tree",
            "tauri_nsis",
            "questionnaire",
            "tiiny_site",
        ],
        config: Any = None,
        ctx: Context | None = None,
        name: str | None = None,
        description: str | None = None,
        author: str = "MCP Studio",
        repository_path: str = ".",
        license_type: str = "MIT",
        include_frontend: bool = False,
        frontend_type: str = "fullstack",
        include_nsis: bool = False,
        include_mcpb: bool = True,
        build_mcpb: bool = True,
        dual_connect: bool = False,
        include_prd: bool = True,
        include_changelog: bool = True,
        include_prompts: bool = True,
        repo_root: str = "",
        repo_name: str = "",
        backend_port: int = 0,
        frontend_port: int = 0,
        mode: str = "scaffold",
        repo_list: str = "",
    ) -> dict[str, Any]:
        """Project scaffolding and code generation (portmanteau).

        [RATIONALE]
        Consolidates 8 related operations into a single tool to prevent tool explosion while enabling full API coverage.

        ## Operations
                - **fullstack**: Generate a FastAPI + React fullstack app
                - **landing_page**: Generate a responsive marketing landing page
                - **mcp_server**: Generate a SOTA-compliant FastMCP server repo
                - **webshop**: Generate an e-commerce platform
                - **game**: Generate a browser-based game
                - **wisdom_tree**: Generate a knowledge tree interface
                - **tauri_nsis**: Add a Tauri 2.0 NSIS native wrapper to a repo
                - **questionnaire**: Show interactive scaffold config card
                - **tiiny_site**: Scaffold a static page and deploy to tiiny.host

        ## Return Format
        {"success": bool, "operation": str, "message": str}

        ## Examples

        await scaffold_ops(operation='fullstack', config={...})
        await scaffold_ops(operation='landing_page', config={...})
        await scaffold_ops(operation='mcp_server', name='my-server', description='...')
        await scaffold_ops(operation='tauri_nsis', repo_root='D:/Dev/repos/my-mcp')
        await scaffold_ops(operation='questionnaire')
        """

        if operation == "fullstack":
            if config is None:
                return {"success": False, "error": "config required for fullstack"}
            return await service.create_fullstack_app(config, ctx)
        elif operation == "landing_page":
            if config is None:
                return {"success": False, "error": "config required for landing_page"}
            return await service.create_landing_page(config, ctx)
        elif operation == "mcp_server":
            if not name:
                return {"success": False, "error": "name required for mcp_server"}
            return await service.create_mcp_server(
                name=name,
                description=description or "",
                author=author,
                repository_path=repository_path,
                license_type=license_type,
                include_frontend=include_frontend,
                frontend_type=frontend_type,
                include_nsis=include_nsis,
                include_mcpb=include_mcpb,
                build_mcpb=build_mcpb,
                dual_connect=dual_connect,
                include_prd=include_prd,
                include_changelog=include_changelog,
                include_prompts=include_prompts,
            )
        elif operation == "webshop":
            if config is None:
                return {"success": False, "error": "config required for webshop"}
            return await service.create_webshop(config, ctx)
        elif operation == "game":
            if config is None:
                return {"success": False, "error": "config required for game"}
            return await service.create_game(config, ctx)
        elif operation == "wisdom_tree":
            if config is None:
                return {"success": False, "error": "config required for wisdom_tree"}
            return await service.create_wisdom_tree(config, ctx)
        elif operation == "tauri_nsis":
            return await create_tauri_nsis(
                repo_root=repo_root,
                repo_name=repo_name,
                backend_port=backend_port,
                frontend_port=frontend_port,
                mode=mode,
                repo_list=repo_list,
            )
        elif operation == "tiiny_site":
            if not name:
                return {"success": False, "error": "name required for tiiny_site"}
            return await service.create_tiiny_site(
                site_name=name,
                title=description or "My Page",
                output_path=repository_path if repository_path != "." else None,
                deploy=include_frontend,
            )
        elif operation == "questionnaire":
            return await show_scaffold_questionnaire()
        return {"success": False, "error": f"Unknown operation: {operation}"}

    async def create_tauri_nsis(
        repo_root: str = "",
        repo_name: str = "",
        backend_port: int = 0,
        frontend_port: int = 0,
        mode: str = "scaffold",
        repo_list: str = "",
    ) -> dict[str, Any]:
        """Add or manage a Tauri 2.0 NSIS native wrapper. Legacy alias -- use scaffold_ops(operation='tauri_nsis')."""
        import asyncio
        import os
        import subprocess

        script = os.path.join(
            os.path.dirname(__file__), "..", "..", "..", "..", "..", "mcp-central-docs", "scripts", "scaffold-tauri.ps1"
        )
        fallback = r"D:\Dev\repos\mcp-central-docs\scripts\scaffold-tauri.ps1"
        if not os.path.exists(script) and os.path.exists(fallback):
            script = fallback
        if not os.path.exists(script):
            return {"success": False, "error": "scaffold-tauri.ps1 not found"}

        cmd = ["pwsh", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", script, "-Mode", mode]
        if mode == "batch":
            if not repo_list:
                return {"success": False, "error": "repo_list required for batch mode"}
            cmd.extend(["-RepoList", repo_list])
        else:
            if not repo_root or not repo_name or not backend_port:
                return {"success": False, "error": "repo_root, repo_name, backend_port required"}
            cmd.extend(["-RepoRoot", repo_root, "-RepoName", repo_name, "-BackendPort", str(backend_port)])
            if frontend_port > 0:
                cmd.extend(["-FrontendPort", str(frontend_port)])

        timeout = 600 if mode in ("build", "test", "batch") else 30
        try:
            proc = await asyncio.create_subprocess_exec(*cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except TimeoutError:
            return {"success": False, "error": f"Timed out after {timeout}s", "mode": mode}
        except Exception as e:
            return {"success": False, "error": str(e), "mode": mode}

        out = stdout.decode("utf-8", errors="replace")
        err = stderr.decode("utf-8", errors="replace")

        # Parse report lines
        report = []
        for line in out.split("\n"):
            line = line.strip()
            for prefix, status in [("+", "OK"), ("?", "WARN"), ("-", "SKIP"), ("X", "ERR"), ("~", "DRY")]:
                if line.startswith(f"  {prefix} [") and "] " in line:
                    rest = line[len(f"  {prefix} [") :]
                    cat, detail = rest.split("] ", 1)
                    report.append({"status": status, "category": cat.strip(), "detail": detail})
                    break

        errors = sum(1 for r in report if r["status"] == "ERR")
        warnings = sum(1 for r in report if r["status"] == "WARN")
        return {
            "success": (proc.returncode or 0) == 0,
            "mode": mode,
            "exit_code": proc.returncode or 0,
            "report": report,
            "errors": errors,
            "warnings": warnings,
            "stderr": err[:2000] if err else "",
        }

    async def show_scaffold_questionnaire() -> dict[str, Any]:
        """Show the MCP server scaffold questionnaire as an interactive Prefab card."""
        from prefab_ui import PrefabApp
        from prefab_ui.components import (
            Card,
            CardContent,
            Checkbox,
            Heading,
            Input,
            Muted,
            P,
            Separator,
            Small,
        )

        app = PrefabApp()

        with app:
            with Card(title="MCP Server Scaffold Questionnaire"):
                with CardContent():
                    P("Configure your new SOTA 2026 MCP server.")
                    Separator()
                    Heading("Required", level=3)
                    Input(name="name", label="Server Name", placeholder="e.g. my-awesome-server", required=True)
                    Input(
                        name="description", label="Description", placeholder="What does this server do?", required=True
                    )
                    Separator()
                    Heading("Core Features", level=3)
                    Checkbox(name="include_frontend", label="Vite + React webapp")
                    Small("Generates web_sota/ with a full React dashboard.")
                    Checkbox(name="include_nsis", label="Tauri 2.0 + NSIS native installer")
                    Small("Creates native/ with Cargo.toml, build.ps1, PyInstaller spec.")
                    Checkbox(name="dual_connect", label="Dual transport (stdio + HTTP)")
                    Small("Adds --http, REST API endpoints. Required for Tauri.")
                    Separator()
                    Heading("Packaging", level=3)
                    Checkbox(name="include_mcpb", label="mcpb manifest (Claude Desktop)", default=True)
                    Checkbox(name="include_prd", label="PRD.md template", default=True)
                    Separator()
                    Heading("Author", level=3)
                    Input(name="author", label="Author", placeholder="Your name", value="MCP Studio")
                    Separator()
                    with Card(size="sm"):
                        with CardContent():
                            Muted(
                                "Call scaffold_mcp_server with your chosen params. Default: stdio-only Python package."
                            )

            Separator()

            with Card(title="Harness from Source (CLI-Anything)"):
                with CardContent():
                    P("Auto-generate a FastMCP server from an existing Python codebase.")
                    Muted(
                        "AST analysis extracts function signatures, domains, and backend "
                        "strategy. Produces portmanteau tools with SOTA-compliant docstrings."
                    )
                    Separator()
                    Heading("Source", level=3)
                    Input(
                        name="source_path", label="Source path", placeholder="D:/tools/my-cli or https://github.com/o/r"
                    )
                    Small("Local directory or GitHub URL. Python source required.")
                    Input(name="software_name", label="Software name (optional)", placeholder="Auto-detected from path")
                    Small("Used for package name and tool prefixes. snake_case recommended.")
                    Checkbox(name="full_extraction", label="Full extraction (no curation)")
                    Small("Skip curation -- expose every public function. Default: curated subset.")
                    Separator()
                    Heading("Output", level=3)
                    Input(name="target_path", label="Target path", placeholder="D:/repos/my-generated-server")
                    Small("Where to write the generated FastMCP 3.4+ server.")
                    Separator()
                    with Card(size="sm"):
                        with CardContent():
                            Muted(
                                "Workflow: 1) harness_analyze(source_path)  "
                                "2) harness_generate(spec, target_path)  "
                                "3) harness_refine(operation='gap') for iterations."
                            )

        return app
