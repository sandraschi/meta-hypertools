"""FastMCP server generator that builds from a ToolSurfaceSpec.

Consumes the output of harness_analyze and generates a complete
fleet-conformant FastMCP 3.4+ server with portmanteau tools per
domain group, Prefab cards, SKILL.md, and full fleet surface.

Methodology adapted from the CLI-Anything 7-phase harness workflow
(HKUDS/CLI-Anything, Apache 2.0, arXiv:2606.03854).
"""

from __future__ import annotations

import os
from typing import Any

from meta_mcp.tools.server_builder_sota import (
    generate_sota_package_files,
    generate_sota_pyproject,
    generate_sota_readme,
)
from meta_mcp.utils.harness_analyzer import ToolSurfaceSpec

_ANNOTATION_READ_ONLY = '{"readOnlyHint": True, "destructiveHint": False}'
_ANNOTATION_MUTATING = '{"readOnlyHint": False, "destructiveHint": False}'
_ANNOTATION_DESTRUCTIVE = '{"readOnlyHint": False, "destructiveHint": True}'


def _snake(name: str) -> str:
    return name.lower().replace("-", "_").replace(" ", "_")


def _pascal(name: str) -> str:
    return "".join(word.capitalize() for word in name.replace("-", " ").replace("_", " ").split())


def _backed_op_impl(op: dict[str, Any]) -> str:
    """Generate implementation body for one operation based on backend strategy."""
    name = op["name"]
    params = op.get("params", [])
    param_names = [p["name"] for p in params]
    param_dict = ", ".join(f'"{n}": {n}' for n in param_names)

    return f'''    if operation == "{name}":
        # TODO: implement {name} backend call
        return {{
            "success": True,
            "operation": "{name}",
            "message": "{name} stub — implement backend integration",
            "params": {{{param_dict}}},
        }}'''


def _generate_portmanteau_tool(
    package_name: str,
    group: dict[str, Any],
    backend_engine: str,
) -> str:
    """Generate one portmanteau tool module for a domain group."""
    tool_name = group["name"]
    domain = group["domain"]
    operations = group.get("operations", [])

    if not operations:
        return f'''"""{domain} operations — no operations found."""

from {package_name}.mcp_instance import mcp
'''

    op_names = sorted(op["name"] for op in operations)
    op_literal = "Literal[" + ", ".join(f'"{n}"' for n in op_names) + "]"
    any_mutating = any(op.get("is_mutating", False) for op in operations)
    any_destructive = any(
        "delete" in op["name"].lower() or "remove" in op["name"].lower() or "destroy" in op["name"].lower()
        for op in operations
    )

    if any_destructive:
        annotation = _ANNOTATION_DESTRUCTIVE
    elif any_mutating:
        annotation = _ANNOTATION_MUTATING
    else:
        annotation = _ANNOTATION_READ_ONLY

    param_lines = []
    seen_params: set[str] = set()
    for op in operations:
        for p in op.get("params", []):
            pname = p["name"]
            if pname in seen_params:
                continue
            seen_params.add(pname)
            ptype = p.get("type", "str")
            desc = p.get("desc", pname)
            param_lines.append(f'    {pname}: Annotated[{ptype} | None, Field(description="{desc}")] = None,')

    operation_list = "\n".join(
        f" - **{op['name']}**: {op.get('docstring', '(no description)').split(chr(10))[0][:120]}" for op in operations
    )

    example_ops = operations[:3]
    examples = "\n".join(f'await {tool_name}(operation="{op["name"]}")' for op in example_ops)

    # Generate operation dispatch
    dispatch_blocks = []
    for op in operations:
        dispatch_blocks.append(_backed_op_impl(op))

    dispatch_body = "\n\n".join(dispatch_blocks)
    op_names[0] if op_names else "unknown"

    return f'''"""{domain} portmanteau — auto-generated from source analysis.

[RATIONALE]
Consolidates {len(operations)} {domain.lower()} operations into a single tool
to prevent tool explosion while enabling full API coverage.
"""

from __future__ import annotations

import logging
from typing import Annotated, Literal

from pydantic import Field

from {package_name}.mcp_instance import mcp

logger = logging.getLogger(__name__)


@mcp.tool(annotations={annotation})
async def {tool_name}(
    operation: Annotated[{op_literal}, Field(description="Operation to perform.")],
    {chr(10).join(p for p in param_lines if p)}
) -> dict:
    """{domain} operations for the {package_name} server.

    ## Operations
{operation_list}

    ## Return Format
    {{"success": bool, "operation": str, "message": str}}

    ## Examples
{examples}
    """
    if not operation or not operation.strip():
        return {{
            "success": False,
            "error": "operation is required",
            "valid_operations": {op_names},
        }}

{dispatch_body}

    return {{
        "success": False,
        "error": f"Unknown operation: {{operation}}",
        "valid_operations": {op_names},
    }}
'''


def _generate_tool_registration(package_name: str, group_names: list[str]) -> str:
    """Generate tool_registration.py that imports all domain tools."""
    imports = "\n".join(f"from {package_name}.tools.{g} import {g}" for g in group_names)
    return f'''"""Auto-generated tool registration — imports trigger decorator registration."""

{imports}

# All imports above register their @mcp.tool() decorators at import time.
# FastMCP discovers registered tools automatically.
'''


def _generate_skill_md(server_name: str, spec: ToolSurfaceSpec) -> str:
    """Generate SKILL.md from the tool surface spec."""
    tool_list = "\n".join(f"- **{g.name}**: {g.domain} ({len(g.operations)} operations)" for g in spec.tool_groups)
    op_details = ""
    for g in spec.tool_groups:
        op_details += f"\n### {g.domain}\n"
        for op in g.operations:
            doc = (op.docstring or "(no description)").split("\n")[0][:100]
            op_details += f"- `{op.name}` — {doc}\n"

    return f"""# {_pascal(server_name)} Agent Skill

{spec.software_name} harness — auto-generated from source analysis.

**Backend:** {spec.backend_engine} | **State:** {spec.state_model} | **Language:** {spec.language}

## Tools
{tool_list}
{op_details}

## Quick start
```powershell
uv sync
uv run python -m {spec.software_name}
```
"""


def _generate_prefabs(package_name: str, spec: ToolSurfaceSpec) -> str:
    """Generate Prefab UI status card for the server."""
    sn = spec.software_name.replace("-", "_")
    status_tool_name = f"show_{sn}_status_card"
    group_summary = ", ".join(f"{g.name} ({len(g.operations)})" for g in spec.tool_groups)

    return f'''"""Prefab UI cards for {spec.software_name}."""

from __future__ import annotations

from fastmcp.server.server import ToolResult
from prefab_ui import PrefabApp
from prefab_ui.components import Card, CardContent, CardHeader, Heading, Metric, Row, Text

from {package_name}.mcp_instance import mcp


@mcp.tool(app=True)
async def {status_tool_name}() -> ToolResult:
    """Show {spec.software_name} status as a rich Prefab card."""
    tools = await mcp.list_tools() if hasattr(mcp, "list_tools") else []
    tool_count = len(tools) if tools else 0

    with PrefabApp(title="{spec.software_name} Status") as app:
        Heading("{spec.software_name}")
        Row(
            Metric(label="Server", value="{spec.software_name}"),
            Metric(label="Version", value="0.1.0"),
            Metric(label="Tools", value=str(tool_count)),
        )
        Row(
            Metric(label="Backend", value="{spec.backend_engine}"),
            Metric(label="State Model", value="{spec.state_model}"),
            Metric(label="Groups", value="{len(spec.tool_groups)}"),
        )
        Card(
            CardHeader("Tool Groups"),
            CardContent(
                Text("{group_summary}")
            ),
        )

    return ToolResult(
        content=f"{{spec.software_name}}\\nv0.1.0\\n{{tool_count}} tools\\nbacked: {{spec.backend_engine}}",
        structured_content=app,
    )
'''


def _generate_backend_strategy(package_name: str, engine: str, details: dict[str, Any]) -> dict[str, str]:
    """Generate backend integration module based on engine type."""
    files: dict[str, str] = {}

    if engine == "subprocess":
        files[
            f"src/{package_name}/backend.py"
        ] = '''"""Subprocess backend — execute commands against the target application."""

from __future__ import annotations

import logging
import shutil
import subprocess

logger = logging.getLogger(__name__)


def find_executable(name: str) -> str | None:
    """Locate executable on PATH."""
    return shutil.which(name)


def run_command(
    executable: str,
    args: list[str],
    *,
    timeout: int = 30,
    capture: bool = True,
    check: bool = True,
) -> dict:
    """Execute a subprocess command and return structured output."""
    if not find_executable(executable):
        return {
            "success": False,
            "error": f"{executable} not found on PATH",
            "recovery_options": [f"Install {executable} and ensure it is on PATH"],
        }
    cmd = [executable] + args
    logger.info("running: %s", " ".join(cmd))
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            timeout=timeout,
            check=check,
        )
        return {
            "success": True,
            "stdout": result.stdout.strip(),
            "stderr": result.stderr.strip(),
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"Command timed out after {timeout}s",
        }
    except subprocess.CalledProcessError as exc:
        return {
            "success": False,
            "error": str(exc),
            "stderr": exc.stderr.strip() if exc.stderr else "",
            "returncode": exc.returncode,
        }
'''
    elif engine == "rest_api":
        files[f"src/{package_name}/backend.py"] = '''"""REST API backend — httpx async client for the target service."""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


async def api_get(endpoint: str, *, timeout: float = 10.0) -> dict:
    """GET request with structured response."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(endpoint)
            resp.raise_for_status()
            return {
                "success": True,
                "data": resp.json() if "application/json" in resp.headers.get("content-type", "") else resp.text,
                "status": resp.status_code,
            }
    except httpx.HTTPStatusError as exc:
        return {
            "success": False,
            "error": str(exc),
            "status": exc.response.status_code,
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


async def api_post(endpoint: str, payload: dict, *, timeout: float = 10.0) -> dict:
    """POST request with structured response."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(endpoint, json=payload)
            resp.raise_for_status()
            return {
                "success": True,
                "data": resp.json() if "application/json" in resp.headers.get("content-type", "") else resp.text,
                "status": resp.status_code,
            }
    except httpx.HTTPStatusError as exc:
        return {
            "success": False,
            "error": str(exc),
            "status": exc.response.status_code,
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}
'''
    else:
        files[f"src/{package_name}/backend.py"] = '''"""Direct import backend — call the target package directly."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# TODO: import the actual target package modules here
# from target_package import core_module
'''

    return files


# ── public API ──────────────────────────────────────────────────


def generate_server_from_spec(
    spec: ToolSurfaceSpec,
    target_path: str,
    *,
    author: str = "MetaMCP Harness Generator",
    license_type: str = "MIT",
    include_nsis: bool = False,
) -> dict[str, Any]:
    """Generate a complete FastMCP 3.4+ server from a ToolSurfaceSpec.

    Args:
        spec: Output from harness_analyze / generate_tool_surface_spec.
        target_path: Directory where the generated server is written.
        author: Author name for pyproject.toml and README.
        license_type: License identifier.
        include_nsis: Whether to scaffold native/ Tauri+NSIS wrapper.

    Returns:
        dict with success, generated_path, file_count, and warnings.
    """
    server_name = spec.software_name
    package_name = server_name.replace("-", "_").lower()

    if not spec.tool_groups:
        return {
            "success": False,
            "message": "No tool groups in spec — run harness_analyze first",
            "error_type": "invalid_input",
            "data": {},
        }

    # Build the base SOTA package files
    files = generate_sota_package_files(
        server_name=server_name,
        package_name=package_name,
        description=f"Auto-generated FastMCP server for {server_name}",
        author=author,
        dual_connect=True,
    )

    # Replace the generic tool_registration with spec-driven version
    group_names = [g.name for g in spec.tool_groups]
    files[f"src/{package_name}/tool_registration.py"] = _generate_tool_registration(package_name, group_names)

    # Generate one portmanteau tool per domain group
    for group in spec.tool_groups:
        tool_code = _generate_portmanteau_tool(
            package_name,
            {
                "name": group.name,
                "domain": group.domain,
                "operations": [
                    {
                        "name": op.name,
                        "params": op.params,
                        "docstring": op.docstring,
                        "is_async": op.is_async,
                        "is_mutating": op.is_mutating,
                    }
                    for op in group.operations
                ],
            },
            spec.backend_engine,
        )
        files[f"src/{package_name}/tools/{group.name}.py"] = tool_code

    # Replace SKILL.md with spec-driven version
    files[f"skills/{server_name}/SKILL.md"] = _generate_skill_md(server_name, spec)

    # Generate Prefab card
    files[f"src/{package_name}/prefabs.py"] = _generate_prefabs(package_name, spec)

    # Add backend strategy module
    backend_files = _generate_backend_strategy(package_name, spec.backend_engine, spec.backend_details)
    files.update(backend_files)

    # Write all files to disk
    written = 0
    for rel_path, content in files.items():
        full_path = os.path.join(target_path, rel_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as fh:
            fh.write(content)
        written += 1

    # Write pyproject.toml
    pyproject_path = os.path.join(target_path, "pyproject.toml")
    os.makedirs(target_path, exist_ok=True)
    with open(pyproject_path, "w", encoding="utf-8") as fh:
        fh.write(
            generate_sota_pyproject(
                package_name,
                f"Auto-generated FastMCP server for {server_name}",
                author,
                license_type,
            )
        )
    written += 1

    # Write README
    readme_path = os.path.join(target_path, "README.md")
    with open(readme_path, "w", encoding="utf-8") as fh:
        fh.write(
            generate_sota_readme(
                server_name,
                package_name,
                f"Auto-generated FastMCP server for {server_name}",
                author,
            )
        )
    written += 1

    return {
        "success": True,
        "message": (
            f"Generated {server_name} server: {written} files, "
            f"{len(spec.tool_groups)} tool groups, "
            f"{spec.total_operations_curated} operations"
        ),
        "data": {
            "generated_path": os.path.abspath(target_path),
            "file_count": written,
            "tool_groups": len(spec.tool_groups),
            "operations": spec.total_operations_curated,
            "backend_engine": spec.backend_engine,
            "warnings": spec.warnings,
        },
    }
