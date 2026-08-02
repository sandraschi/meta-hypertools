import shutil
import subprocess
from pathlib import Path
from typing import Any

from meta_mcp.services.base import MetaMCPService
from meta_mcp.tools.fullstack import create_fullstack_app_tool
from meta_mcp.tools.gamemaker import create_game_tool
from meta_mcp.tools.landing_page_builder import create_landing_page
from meta_mcp.tools.server_builder import create_mcp_server
from meta_mcp.tools.tiiny_host import scaffold_tiiny_site
from meta_mcp.tools.webshop import create_webshop_tool
from meta_mcp.tools.wisdom import create_wisdom_tree_tool


class ScaffoldingService(MetaMCPService):
    """
    Service for scaffolding new projects and applications.
    """

    async def create_fullstack_app(self, config: Any, ctx: Any | None = None) -> dict[str, Any]:
        """Create a fullstack application with FastAPI and React."""
        return await create_fullstack_app_tool(
            name=getattr(config, "name", "fullstack-app"),
            description=getattr(config, "description", "A modern fullstack application"),
            author=getattr(config, "author", "Developer"),
            target_path=getattr(config, "target_path", "."),
            include_ai=getattr(config, "include_ai", True),
            include_mcp=getattr(config, "include_mcp", True),
            include_mcp_server=getattr(config, "include_mcp_server", True),
            include_pwa=getattr(config, "include_pwa", True),
            include_monitoring=getattr(config, "include_monitoring", True),
        )

    async def create_landing_page(self, config: Any, ctx: Any | None = None) -> dict[str, Any]:
        """Create a responsive landing page."""
        result = await create_landing_page(
            project_name=getattr(config, "project_name", "landing-page"),
            hero_title=getattr(config, "hero_title", "The Next Big Thing"),
            hero_subtitle=getattr(
                config,
                "hero_subtitle",
                "Revolutionizing the way you do things. Built in a cave. Powered by caffeine.",
            ),
            github_url=getattr(config, "github_url", "https://github.com"),
            target_path=getattr(config, "target_path", "."),
            author_name=getattr(config, "author_name", "Joe Shmoe"),
            author_bio=getattr(
                config,
                "author_bio",
                "I build things in my subterranean headquarters. Powered by free meals and cola courtesy of mum.",
            ),
            show_locally=getattr(config, "show_locally", False),
        )
        return {"success": True, "result": result} if isinstance(result, str) else result

    async def create_mcp_server(
        self,
        name: str,
        description: str,
        author: str = "MCP Studio",
        repository_path: str = ".",
        license_type: str = "MIT",
        include_ci: bool = True,
        include_tests: bool = True,
        include_docs: bool = True,
        include_frontend: bool = False,
        frontend_type: str = "fullstack",
        include_nsis: bool = False,
        include_mcpb: bool = True,
        build_mcpb: bool = True,
        dual_connect: bool = False,
        include_prd: bool = True,
        include_changelog: bool = True,
        include_prompts: bool = True,
    ) -> dict[str, Any]:
        """Scaffold a new SOTA-compliant MCP server repository."""
        # NOTE: include_ci/include_tests/include_docs are accepted in the signature
        # for API compatibility but not forwarded  the builder generates all three
        # unconditionally (CI, tests, docs are always scaffolded).
        # repository_path is the full target dir; builder expects target_path as parent.
        # E.g. repository_path="D:/Dev/repos/my-server"  target_path="D:/Dev/repos"
        target = str(Path(repository_path).parent) if repository_path and repository_path != "." else repository_path

        return await create_mcp_server(
            server_name=name,
            description=description,
            author=author,
            target_path=target,
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

    async def create_webshop(self, config: Any, ctx: Any | None = None) -> dict[str, Any]:
        """Create a fullstack webshop application."""
        return await create_webshop_tool(
            name=getattr(config, "name", "webshop"),
            template=getattr(config, "template", "medusa"),
            description=getattr(config, "description", "A premium e-commerce store"),
            target_path=getattr(config, "target_path", "."),
            config=getattr(config, "backend_config", None),
        )

    async def create_game(self, config: Any, ctx: Any | None = None) -> dict[str, Any]:
        """Create a browser-based game."""
        return await create_game_tool(
            name=getattr(config, "name", "game"),
            template=getattr(config, "template", "asteroids"),
            target_path=getattr(config, "target_path", "."),
        )

    async def create_wisdom_tree(self, config: Any, ctx: Any | None = None) -> dict[str, Any]:
        """Create an interactive knowledge tree."""
        return await create_wisdom_tree_tool(
            name=getattr(config, "name", "wisdom-tree"),
            template=getattr(config, "template", "technical-roadmap"),
            target_path=getattr(config, "target_path", "."),
        )

    async def create_tiiny_site(
        self,
        site_name: str,
        title: str = "My Page",
        content: str = "<p>Hello from tiiny.host!</p>",
        output_path: str | None = None,
        deploy: bool = False,
        email: str | None = None,
    ) -> dict[str, Any]:
        """Scaffold (and optionally deploy) a static page to tiiny.host."""
        return scaffold_tiiny_site(
            site_name=site_name,
            title=title,
            content=content,
            output_path=output_path,
            deploy=deploy,
            email=email,
        )

    async def create_project(
        self,
        template_type: str,
        project_name: str,
        output_path: str,
        features: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a project using the specified template type."""
        try:
            # Create a simple config object for the existing methods
            class Config:
                def __init__(self, **kwargs):
                    for key, value in kwargs.items():
                        setattr(self, key, value)

            config = Config(
                name=project_name,
                project_name=project_name,
                target_path=output_path,
                **features,
            )

            if template_type == "mcp_server":
                result = await self.create_mcp_server(
                    name=project_name,
                    description=features.get("description", f"MCP Server for {project_name}"),
                    author=features.get("author", "MetaMCP"),
                    repository_path=output_path,
                    **{k: v for k, v in features.items() if k not in ["name", "description", "author"]},
                )
            elif template_type == "landing_page":
                result = await self.create_landing_page(config)
            elif template_type == "fullstack":
                result = await self.create_fullstack_app(config)
            elif template_type == "webshop":
                result = await self.create_webshop(config)
            elif template_type == "game":
                result = await self.create_game(config)
            elif template_type == "wisdom_tree":
                result = await self.create_wisdom_tree(config)
            elif template_type == "tiiny_site":
                result = await self.create_tiiny_site(
                    site_name=project_name,
                    title=features.get("title", "My Page"),
                    content=features.get("content", "<p>Hello from tiiny.host!</p>"),
                    output_path=output_path or None,
                    deploy=features.get("deploy", False),
                    email=features.get("email"),
                )
            elif template_type == "spec_kit":
                ai_integration = features.get("ai_integration", "opencode")
                result = self._create_spec_kit_project(project_name, output_path, ai_integration)
            else:
                return self.create_response(False, f"Unsupported template type: {template_type}")

            if result.get("success"):
                return self.create_response(True, f"Project '{project_name}' created successfully", result)
            else:
                return self.create_response(
                    False,
                    f"Project creation failed: {result.get('message', 'Unknown error')}",
                    result,
                )

        except Exception as e:
            return self.create_response(False, f"Project creation failed: {e!s}")

    def _create_spec_kit_project(self, project_name: str, output_path: str, ai_integration: str) -> dict[str, Any]:
        """Run ``specify init`` to scaffold a Spec Kit project."""
        target = Path(output_path) / project_name

        specify_path = shutil.which("specify")
        if not specify_path:
            return self.create_response(
                False,
                "specify CLI not found. Install with: uv tool install specify-cli --from git+https://github.com/github/spec-kit.git",
            )

        cmd = [
            specify_path,
            "init",
            project_name,
            "--ai",
            ai_integration,
            "--ignore-agent-tools",
        ]

        try:
            proc = subprocess.run(
                cmd,
                cwd=output_path,
                capture_output=True,
                text=True,
                timeout=180,
            )
            if proc.returncode == 0:
                return self.create_response(
                    True,
                    f"Spec Kit project '{project_name}' scaffolded",
                    {
                        "project_path": str(target),
                        "ai_integration": ai_integration,
                    },
                )
            stderr = (proc.stderr or "")[:500]
            stdout = (proc.stdout or "")[:500]
            return self.create_response(
                False,
                f"specify init failed (exit {proc.returncode}): {stderr or stdout}",
            )
        except subprocess.TimeoutExpired:
            return self.create_response(False, "specify init timed out after 180s")
        except Exception as e:
            return self.create_response(False, f"specify init error: {e!s}")
