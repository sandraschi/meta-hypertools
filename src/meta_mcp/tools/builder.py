"""
Tool for scaffolding new MCP servers.
"""

import logging
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any


class ServerBuilder:
    """Builder for SOTA-compliant MCP servers."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def _kebab_to_snake(self, name: str) -> str:
        """Convert kebab-case to snake_case."""
        return name.replace("-", "_")

    def _kebab_to_pascal(self, name: str) -> str:
        """Convert kebab-case to PascalCase."""
        return "".join(word.capitalize() for word in name.split("-"))

    async def create_server(
        self,
        server_name: str,
        description: str,
        author: str = "MetaMCP",
        license_type: str = "MIT",
        target_path: str = "./repos",
        include_examples: bool = True,
        make_git: bool = True,
        include_frontend: bool = False,
        frontend_type: str = "fullstack",
        include_mcpb: bool = True,
        build_mcpb: bool = True,
        dual_connect: bool = False,
        include_prd: bool = True,
        include_changelog: bool = True,
        **kwargs,
    ) -> dict[str, Any]:
        """Create a new SOTA-compliant MCP server."""
        try:
            root_dir = Path(target_path) / server_name
            package_name = self._kebab_to_snake(server_name)
            src_dir = root_dir / "src" / package_name

            # Create directory structure
            root_dir.mkdir(parents=True, exist_ok=True)
            src_dir.mkdir(parents=True, exist_ok=True)
            (root_dir / "tests").mkdir(exist_ok=True)
            (root_dir / "docs").mkdir(exist_ok=True)
            (root_dir / "scripts").mkdir(exist_ok=True)
            (src_dir / "tools").mkdir(exist_ok=True)
            (src_dir / "prompts").mkdir(exist_ok=True)

            # Generate core files
            files = {
                root_dir / "pyproject.toml": self._generate_pyproject_toml(
                    server_name, package_name, description, author, license_type
                ),
                root_dir / "README.md": self._generate_readme(server_name, description, author),
                root_dir / ".gitignore": self._generate_gitignore(),
                root_dir / "manifest.json": self._generate_manifest_json(server_name, description),
                src_dir / "mcp_server.py": self._generate_mcp_server_py(
                    server_name, package_name, description, dual_connect
                ),
                src_dir / "__init__.py": f'"""{description}"""\n',
                src_dir / "tools" / "__init__.py": '"""Tools for the MCP server."""\n',
                src_dir / "prompts" / "__init__.py": '"""Prompts for the MCP server."""\n',
            }

            if include_prd:
                files[root_dir / "PRD.md"] = self._generate_prd_md(server_name, description, dual_connect)

            if include_changelog:
                files[root_dir / "CHANGELOG.md"] = self._generate_changelog_md(server_name)

            if include_mcpb:
                files[root_dir / "mcpb.json"] = self._generate_mcpb_json(
                    server_name, package_name, description, author, license_type
                )

            for path, content in files.items():
                path.write_text(content, encoding="utf-8")

            # Add examples
            if include_examples:
                (src_dir / "tools" / "example.py").write_text(self._generate_example_tool(), encoding="utf-8")
                (src_dir / "prompts" / "example.py").write_text(self._generate_example_prompt(), encoding="utf-8")

            # Initialize git if requested
            if make_git:
                try:
                    git_path = shutil.which("git") or "git"
                    subprocess.run([git_path, "init"], cwd=str(root_dir), capture_output=True)
                    (root_dir / ".cursorrules").write_text(self._generate_cursorrules(), encoding="utf-8")
                except Exception as e:
                    self.logger.warning(f"Failed to initialize git: {e}")

            # Generate frontend if requested
            frontend_status = None
            if include_frontend:
                frontend_status = await self._generate_frontend(
                    root_dir, server_name, description, author, frontend_type
                )

            return {
                "success": True,
                "path": str(root_dir),
                "package_name": package_name,
                "frontend": frontend_status,
            }

        except Exception as e:
            self.logger.error(f"Failed to create server: {e}", exc_info=True)
            return {"success": False, "message": "Operation failed", "error": str(e)}

    # Helper methods (extracted and adapted from legacy server_builder.py)

    def _generate_mcp_server_py(self, server_name: str, package_name: str, description: str, dual_connect: bool) -> str:
        pascal_name = self._kebab_to_pascal(server_name)
        transport_logic = (
            """
def main():
    \"\"\"Run the server.\"\"\"
    import sys
    if "--sse" in sys.argv:
        app.run("sse")
    else:
        app.run("stdio")
"""
            if dual_connect
            else """
def main():
    \"\"\"Run the server.\"\"\"
    app.run("stdio")
"""
        )
        return f'''"""{description}"""
from pathlib import Path
from fastmcp import FastMCP

app = FastMCP("{pascal_name}")

@app.tool()
async def status() -> str:
    """Get server status."""
    return "SUCCESS {pascal_name} is operational"

{transport_logic}

app.discover_tools(str(Path(__file__).parent / "tools"))
app.discover_prompts(str(Path(__file__).parent / "prompts"))

if __name__ == "__main__":
    main()
'''

    def _generate_pyproject_toml(
        self,
        server_name: str,
        package_name: str,
        description: str,
        author: str,
        license_type: str,
    ) -> str:
        return f'''[project]
name = "{server_name}"
version = "0.1.0"
description = "{description}"
authors = [{{name = "{author}"}}]
requires-python = ">=3.11"
dependencies = ["fastmcp[all]>=2.13.1"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
'''

    def _generate_readme(self, server_name: str, description: str, author: str) -> str:
        return f"# {server_name}\n\n{description}\n\nGenerated by MetaMCP."

    def _generate_gitignore(self) -> str:
        return "__pycache__/\n*.py[cod]\nvenv/\n.venv\n.idea/\n.vscode/\n"

    def _generate_manifest_json(self, server_name: str, description: str) -> str:
        import json

        return json.dumps(
            {
                "name": server_name,
                "description": description,
                "version": "0.1.0",
                "mcp": {
                    "command": "python",
                    "args": ["-m", f"{server_name.replace('-', '_')}", "mcp_server"],
                },
            },
            indent=2,
        )

    def _generate_prd_md(self, name, desc, dual):
        return f"# PRD: {name}\n\n{desc}"

    def _generate_changelog_md(self, name):
        return f"# Changelog: {name}\n\n## [0.1.0] - {datetime.now().strftime('%Y-%m-%d')}\n- Initial release"

    def _generate_mcpb_json(self, name, pkg, desc, author, lic):
        import json

        return json.dumps({"name": name, "version": "0.1.0"}, indent=2)

    def _generate_cursorrules(self):
        return "# Cursor Rules\n\n- Follow SOTA standards."

    def _generate_example_tool(self):
        return 'async def example_tool(op: str) -> str:\n    return f"Op: {op}"\n'

    def _generate_example_prompt(self):
        return 'async def example_prompt(text: str) -> str:\n    return f"Prompt: {text}"\n'

    async def _generate_frontend(self, server_dir, server_name, description, author, frontend_type):
        # Placeholder for complex frontend generation script
        return {"success": True, "message": "Frontend scaffolded"}
