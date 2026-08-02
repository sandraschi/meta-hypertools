import asyncio
import os
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class GameMaker:
    """
    Scaffolds retro games from the games-app collection.
    """

    TEMPLATES = [
        "asteroids",
        "blackjack",
        "chess",
        "pacman",
        "tetris",
        "breakout",
        "pong",
    ]

    def __init__(self, target_path: str = "./games"):
        self.target_path = os.path.abspath(target_path)
        # Repo root: src/meta_mcp/tools/gamemaker.py  4 levels up
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        self.scaffold_script = os.path.join(self.base_dir, "scripts", "gamemaker-builder.ps1")

    async def scaffold(self, name: str, template: str) -> dict[str, Any]:
        """
        Executes the PowerShell scaffolding script.
        """
        if template not in self.TEMPLATES:
            return {
                "success": False,
                "error": f"Invalid template '{template}'. Available: {', '.join(self.TEMPLATES)}",
            }

        if not os.path.exists(self.scaffold_script):
            return {
                "success": False,
                "error": (
                    f"Game scaffolding script not found at {self.scaffold_script}. "
                    "The PowerShell scaffolder was retired - see "
                    "meta_mcp/reports/scripts-assessment-2026-08-02.md."
                ),
            }

        os.makedirs(self.target_path, exist_ok=True)

        cmd = [
            "powershell.exe",
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

        logger.info("scaffolding_game", name=name, template=template, command=cmd)

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode().strip()
                logger.error("scaffolding_failed", name=name, error=error_msg)
                return {"success": False, "message": "Operation failed", "error": error_msg}

            logger.info("scaffolding_complete", name=name)
            return {
                "success": True,
                "path": os.path.join(self.target_path, name),
                "message": f"Successfully scaffolded {template} game as {name}",
                "output": stdout.decode().strip(),
            }

        except Exception as e:
            logger.exception("scaffolding_exception", name=name)
            return {"success": False, "message": "Operation failed", "error": str(e)}


async def create_game_tool(
    name: str,
    template: str,
    target_path: str = "./games",
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    PORTMANTEAU PATTERN RATIONALE:
    Consolidates multiple game scaffolding templates into a single tool.
    Prevents tool explosion while maintaining full functionality.
    Follows FastMCP 2.14.1+ best practices for SOTA compliance.

    Scaffold an interactive retro game based on SOTA patterns.

    Args:
        name (str, required): The name of the game project.
        template (str, required): The game template to use. Must be one of:
            "asteroids", "blackjack", "chess", "pacman", "tetris", "breakout", "pong", "snake", "space-invaders".
        target_path (str | None): Directory where the game will be scaffolded. Defaults to "./games".
        config (dict | None): Optional configuration override.

    Returns:
        Enhanced SOTA response with scaffolding status and next steps.
    """
    maker = GameMaker(target_path=target_path)
    result = await maker.scaffold(name=name, template=template)

    if not result.get("success"):
        return {
            "success": False,
            "operation": "create_game",
            "error": result.get("error", "Unknown error"),
            "summary": f"Failed to scaffold {template} game: {result.get('error')}",
            "recovery_options": [
                "Verify the template name matches the available options",
                "Check if the target directory is writable",
                "Ensure PowerShell execution policy allows running scripts",
            ],
            "available_types": maker.TEMPLATES,
        }

    game_path = result.get("path")
    return {
        "success": True,
        "operation": "create_game",
        "summary": f"Successfully scaffolded {template} game as '{name}'",
        "result": {
            "path": game_path,
            "template": template,
            "name": name,
            "output": result.get("output"),
        },
        "available_types": maker.TEMPLATES,
        "recommendations": [
            f"Navigate to {game_path} and open index.html in a browser",
            "Use the 'typora' tool if available to edit game assets",
            "Customize the game logic in script.js",
        ],
        "next_steps": [
            "Open the game in a browser to test",
            "Configure a local dev server for faster iteration",
            "Add custom sprites or sound effects",
        ],
    }
