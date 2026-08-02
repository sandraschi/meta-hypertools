import asyncio
import os
import shutil
from typing import Any, ClassVar

import structlog

logger = structlog.get_logger(__name__)


class WisdomTreeBuilder:
    """
    Scaffolds interactive knowledge trees from the ai-games-collection Technical Tree collection.
    """

    TEMPLATES: ClassVar[list[str]] = [
        "technical-roadmap",
        "ai-concepts",
        "git-mastery",
    ]

    def __init__(self, target_path: str = "./wisdom"):
        self.target_path = os.path.abspath(target_path)
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        self.scaffold_script = os.path.join(self.base_dir, "scripts", "wisdom-tree-builder.ps1")

    async def build(self, name: str, template: str) -> dict[str, Any]:
        """
        Executes the PowerShell scaffolding script for wisdom trees.
        """
        if template not in self.TEMPLATES:
            return {
                "success": False,
                "message": "Operation failed",
                "error": f"Invalid template '{template}'. Available: {', '.join(self.TEMPLATES)}",
            }

        if not os.path.exists(self.scaffold_script):
            return {
                "success": False,
                "message": "Operation failed",
                "error": (
                    f"Wisdom tree script not found at {self.scaffold_script}. "
                    "The PowerShell scaffolder was retired - see "
                    "meta_mcp/reports/scripts-assessment-2026-08-02.md."
                ),
            }

        os.makedirs(self.target_path, exist_ok=True)

        pwsh_path = shutil.which("powershell.exe") or shutil.which("pwsh") or "powershell.exe"
        cmd = [
            pwsh_path,
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            self.scaffold_script,
            "-Name",
            name,
            "-Template",
            template,
            "-TargetPath",
            self.target_path,
        ]

        logger.info("building_wisdom_tree", name=name, template=template, command=cmd)

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode().strip()
                logger.error("building_failed", name=name, error=error_msg)
                return {"success": False, "message": "Operation failed", "error": error_msg}

            logger.info("building_complete", name=name)
            return {
                "success": True,
                "path": os.path.join(self.target_path, name),
                "message": f"Successfully scaffolded {template} wisdom tree as {name}",
                "output": stdout.decode().strip(),
            }

        except Exception as e:
            logger.exception("building_exception", name=name)
            return {"success": False, "message": "Operation failed", "error": str(e)}


async def create_wisdom_tree_tool(
    name: str,
    template: str,
    target_path: str = "./wisdom",
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    PORTMANTEAU PATTERN RATIONALE:
    Consolidates multiple knowledge tree templates into a single tool.
    Prevents tool explosion while maintaining deep educational functionality.
    Follows FastMCP 2.14.1+ best practices for SOTA compliance.

    Scaffold an interactive knowledge tree (Wisdom Tree) based on SOTA patterns.

    Args:
        name (str, required): The name of the wisdom tree project.
        template (str, required): The tree template to use. Must be one of:
            "technical-roadmap", "ai-concepts", "git-mastery".
        target_path (str | None): Directory where the tree will be scaffolded. Defaults to "./wisdom".
        config (dict | None): Optional configuration override.

    Returns:
        Enhanced SOTA response with scaffolding status and next steps.
    """
    builder = WisdomTreeBuilder(target_path=target_path)
    result = await builder.build(name=name, template=template)

    if not result.get("success"):
        return {
            "success": False,
            "message": result.get("error", "Unknown error"),
            "operation": "create_wisdom_tree",
            "error": result.get("error", "Unknown error"),
            "summary": f"Failed to scaffold {template} wisdom tree: {result.get('error')}",
            "recovery_options": [
                "Verify the template name matches the available options",
                "Check if the target directory is writable",
                "Ensure PowerShell execution policy allows running scripts",
            ],
            "available_types": builder.TEMPLATES,
        }

    tree_path = result.get("path")
    return {
        "success": True,
        "operation": "create_wisdom_tree",
        "summary": f"Successfully scaffolded {template} wisdom tree as '{name}'",
        "result": {
            "path": tree_path,
            "template": template,
            "name": name,
            "output": result.get("output"),
        },
        "available_types": builder.TEMPLATES,
        "recommendations": [
            f"Navigate to {tree_path} and open index.html in a browser",
            "Use a markdown editor to extend the knowledge nodes",
            "Review the tree structure in the generated JSON data",
        ],
        "next_steps": [
            "Explore the generated knowledge nodes",
            "Add custom nodes to the tech tree",
            "Deploy as a static site for easy sharing",
        ],
    }
