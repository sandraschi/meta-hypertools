"""
Webshop Builder for MakerMCP.
Supports MedusaJS and Next.js Commerce templates.
"""

import asyncio
import os
from pathlib import Path
from typing import Any


class WebshopBuilder:
    """
    Scaffolds production-ready e-commerce platforms.
    """

    def __init__(self, script_path: Path | None = None):
        if script_path is not None:
            self.script_path = script_path
        else:
            raw = os.environ.get("META_MCP_WEBSHOP_SCRIPT", "").strip()
            if raw:
                self.script_path = Path(raw).expanduser()
            else:
                self.script_path = Path(__file__).resolve().parents[3] / "scripts" / "webshop-builder.ps1"

    async def create_shop(
        self,
        shop_name: str,
        template: str = "medusa",  # medusa, nextjs-commerce
        description: str = "A premium e-commerce store",
        output_path: str = ".",
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create a new webshop using the specified template.
        """
        if not self.script_path.exists():
            # If the script doesn't exist yet, we'll need to create it or handle it
            return {
                "success": False,
                "message": "Operation failed",
                "error": f"Webshop builder script not found at {self.script_path}",
            }

        cmd = [
            "pwsh",
            "-File",
            str(self.script_path),
            "-ShopName",
            shop_name,
            "-Template",
            template,
            "-Description",
            description,
            "-OutputPath",
            output_path,
        ]

        if config:
            import json
            import tempfile

            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                json.dump(config, f)
                cmd.extend(["-ConfigPath", f.name])

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                return {
                    "success": True,
                    "shop_path": str(Path(output_path) / shop_name),
                    "message": f"Webshop '{shop_name}' created successfully using {template}.",
                }
            else:
                return {
                    "success": False,
                    "message": "Operation failed",
                    "error": stderr.decode().strip() or stdout.decode().strip(),
                    "exit_code": process.returncode,
                }
        except Exception as e:
            return {"success": False, "message": "Operation failed", "error": str(e)}


async def create_webshop_tool(
    name: str,
    template: str = "medusa",
    description: str = "A premium e-commerce store",
    target_path: str = "./shops",
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    PORTMANTEAU PATTERN RATIONALE:
    Consolidates disparate e-commerce scaffolding workflows into a single interface.
    Enables rapid deployment of production-ready shops while reducing tool complexity.
    Follows FastMCP 2.14.1+ best practices for SOTA compliance.

    Scaffold a SOTA-compliant e-commerce webshop.

    Args:
        name (str, required): The name of the webshop project.
        template (str): The e-commerce template to use. Options: "medusa", "nextjs-commerce". Defaults to "medusa".
        description (str): Brief description of the store.
        target_path (str): Directory where the shop will be created. Defaults to "./shops".
        config (dict | None): Optional configuration override for the shop setup.

    Returns:
        Enhanced SOTA response with shop creation status and next steps.
    """
    builder = WebshopBuilder()
    result = await builder.create_shop(
        shop_name=name,
        template=template,
        description=description,
        output_path=target_path,
        config=config,
    )

    if not result.get("success"):
        return {
            "success": False,
            "message": result.get("error", "Unknown error"),
            "operation": "create_webshop",
            "error": result.get("error", "Unknown error"),
            "summary": f"Failed to scaffold {template} shop: {result.get('error')}",
            "recovery_options": [
                "Verify that 'npx' is installed and accessible",
                "Check if the target path is writable",
                "Ensure you have an active internet connection for package installation",
            ],
            "available_types": ["medusa", "nextjs-commerce"],
        }

    shop_path = result.get("shop_path")
    return {
        "success": True,
        "operation": "create_webshop",
        "summary": f"Successfully scaffolded {template} shop as '{name}'",
        "result": {
            "path": shop_path,
            "template": template,
            "name": name,
            "description": description,
        },
        "available_types": ["medusa", "nextjs-commerce"],
        "recommendations": [
            f"Navigate to {shop_path} and follow the README instructions",
            "Initialize your store with 'medusa user' if using Medusa",
            "Connect your frontend to the newly created backend",
        ],
        "next_steps": [
            "Install dependencies using 'npm install' or 'yarn'",
            "Configure environment variables in the .env file",
            "Start the development server",
        ],
    }
