"""Demo capture — plan, record, render, and help for fleet webapp walkthrough videos."""

from __future__ import annotations

from typing import Any, Literal

from fastmcp import FastMCP

from meta_mcp.services.demo_capture_service import DemoCaptureService


def register_demo_capture_tools(mcp: FastMCP) -> None:
    """Register demo capture portmanteau and legacy helpers."""

    service = DemoCaptureService()

    @mcp.tool(name="demo_ops")
    async def demo_ops(
        operation: Literal["help", "plan", "record", "render", "health"],
        app_id: str | None = None,
        repo_path: str | None = None,
        description: str = "Showcase the dashboard, then visit each major page.",
        screenshots: bool = True,
        video: bool = True,
        start_if_needed: bool = True,
        timeout_sec: int = 90,
        render_mp4: bool = False,
        video_path: str | None = None,
        title: str | None = None,
        subtitle: str = "",
    ) -> dict[str, Any]:
        """Fleet webapp demo capture (portmanteau).

        Remote-control a fleet webapp, capture Playwright walkthrough, and optionally
        render a polished MP4 via Remotion (title overlay, H.264 output).

        ## Operations
        - **help**: Explain the demo capture pipeline and prerequisites
        - **plan**: Scan routes/testids and build demo config.json
        - **record**: Start stack (or reuse), run Playwright capture, return artifact paths
        - **render**: Remotion post-production — Playwright .webm → MP4 with title card
        - **health**: Wait until manifest backend + frontend ports are ready

        ## Examples
        await demo_ops(operation="plan", app_id="inkscape-mcp")
        await demo_ops(operation="record", app_id="inkscape-mcp", render_mp4=True)
        await demo_ops(operation="render", app_id="inkscape-mcp", title="Inkscape MCP Tour")
        """
        if operation == "help":
            return {
                "success": True,
                "operation": "help",
                "message": "Demo capture: Playwright record + optional Remotion MP4 render.",
                "data": {
                    "pipeline": [
                        "1. demo_ops(plan) — scan routes + data-testid → config.json",
                        "2. demo_ops(record) — start/reuse stack, Playwright → .webm + PNGs",
                        "3. demo_ops(render) — Remotion title overlay → docs/screenshots/{repo}-demo.mp4",
                        "4. Or record(render_mp4=True) to run steps 2+3 in one call",
                    ],
                    "bundled_template": "meta_mcp/demo_capture_templates/",
                    "remotion_template": "meta_mcp/demo_capture_templates/remotion/",
                    "per_repo_output": "scripts/screencast/ (Remotion project), docs/screenshots/*.mp4",
                    "prerequisites": [
                        "Node.js + npm/npx on PATH",
                        "npx playwright install chromium (once per machine)",
                        "Remotion render pulls @remotion/cli on first npm install in scripts/screencast/",
                    ],
                    "nssm_repos": "NSSM-backed backends use -FrontendOnly when starting for capture.",
                },
            }
        if operation == "plan":
            result = service.plan_config(app_id=app_id, repo_path=repo_path, description=description)
            result["operation"] = "plan"
            return result
        if operation == "health":
            if not app_id:
                return {"success": False, "operation": "health", "message": "app_id is required"}
            result = await service.runtime.wait_for_health(app_id, timeout_sec=timeout_sec)
            result["operation"] = "health"
            return result
        if operation == "render":
            result = await service.render(
                app_id=app_id,
                repo_path=repo_path,
                video_path=video_path,
                title=title,
                subtitle=subtitle or description,
            )
            result["operation"] = "render"
            return result
        if operation == "record":
            result = await service.record(
                app_id=app_id,
                repo_path=repo_path,
                description=description,
                screenshots=screenshots,
                video=video,
                start_if_needed=start_if_needed,
                timeout_sec=timeout_sec,
                render_mp4=render_mp4,
                subtitle=subtitle or description,
            )
            result["operation"] = "record"
            return result
        return {"success": False, "operation": operation, "message": f"Unknown operation: {operation}"}

    @mcp.tool(name="generate_demo_script")
    async def generate_demo_script(
        repo_path: str,
        description: str = "Showcase the dashboard, then visit each major page.",
    ) -> dict[str, Any]:
        """Generate a config.json for the fleet demo-capture template (legacy alias for demo_ops plan).

        Prefer demo_ops(operation=\"plan\", repo_path=...) for new integrations.
        """
        result = service.plan_config(repo_path=repo_path, description=description)
        if not result.get("success"):
            return {"success": False, "error": result.get("message")}
        data = result["data"]
        return {
            "success": True,
            "message": result["message"],
            "result": data["config"],
            "data": {
                "routes_found": data["routes_found"],
                "testids_found": 0,
                "config_json": data["config_json"],
            },
        }

    @mcp.tool(name="demo_capture_help")
    async def demo_capture_help() -> dict[str, Any]:
        """Explain how the demo capture system works (legacy alias — prefer demo_ops help)."""
        return await demo_ops(operation="help")
