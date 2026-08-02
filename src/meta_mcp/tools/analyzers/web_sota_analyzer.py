import json
from pathlib import Path
from typing import Any


def analyze_web_sota(repo_path: Path) -> dict[str, Any]:
    """Analyze the Web SOTA compliance and tech stack of a repository."""
    result = {
        "has_web_sota_dir": False,
        "has_start_script_ps1": False,
        "has_start_script_bat": False,
        "frontend_framework": None,
        "styling": None,
        "components": [],
        "bundler": None,
        "is_sota_ui": False,
    }

    # Base checks
    web_dir = repo_path / "web_sota"
    dashboard_dir = repo_path / "dashboard"
    web_app_dir = (
        web_dir
        if web_dir.exists() and web_dir.is_dir()
        else (dashboard_dir if dashboard_dir.exists() and dashboard_dir.is_dir() else None)
    )

    if web_app_dir:
        result["has_web_sota_dir"] = True

        if (web_app_dir / "start.ps1").exists():
            result["has_start_script_ps1"] = True

        if (web_app_dir / "start.bat").exists():
            result["has_start_script_bat"] = True

        package_json = web_app_dir / "package.json"

        # Analyze package.json
        if package_json.exists() and package_json.is_file():
            try:
                content = package_json.read_text(encoding="utf-8")
                pkg = json.loads(content)
                deps = {
                    **(pkg.get("dependencies", {})),
                    **(pkg.get("devDependencies", {})),
                }

                # Frontend Framework
                if "next" in deps:
                    result["frontend_framework"] = "nextjs"
                elif "react" in deps:
                    result["frontend_framework"] = "react"
                elif "vue" in deps:
                    result["frontend_framework"] = "vue"
                elif "svelte" in deps:
                    result["frontend_framework"] = "svelte"

                # Styling
                if "tailwindcss" in deps:
                    result["styling"] = "tailwind"
                elif "@mui/material" in deps:
                    result["styling"] = "mui"
                elif "styled-components" in deps:
                    result["styling"] = "styled-components"

                # Components
                if "lucide-react" in deps:
                    result["components"].append("lucide-react")
                if "framer-motion" in deps:
                    result["components"].append("framer-motion")
                if "clsx" in deps and "tailwind-merge" in deps:
                    # Common indicator of shadcn/ui
                    components_ui = web_app_dir / "components" / "ui"
                    if components_ui.exists() and components_ui.is_dir():
                        result["components"].append("shadcn")

                # Bundler
                if "vite" in deps:
                    result["bundler"] = "vite"
                elif "webpack" in deps:
                    result["bundler"] = "webpack"
                elif result["frontend_framework"] == "nextjs":
                    result["bundler"] = "next"

                # Evaluate IS SOTA UI
                if (
                    result["frontend_framework"] in ["react", "nextjs"]
                    and result["styling"] == "tailwind"
                    and "shadcn" in result["components"]
                ):
                    result["is_sota_ui"] = True

            except Exception:
                pass

    return result
