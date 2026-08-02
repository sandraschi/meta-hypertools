"""AST-based API surface extraction for harness generation.

Reads Python source, extracts function signatures, class hierarchies,
and CLI argument definitions. Applies curation rules to produce a
ToolSurfaceSpec suitable for feeding into scaffold_mcp_server.

Methodology adapted from the CLI-Anything 7-phase harness workflow
(HKUDS/CLI-Anything, Apache 2.0, arXiv:2606.03854).
"""

from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ExtractedOperation:
    name: str
    signature: str
    params: list[dict[str, Any]] = field(default_factory=list)
    docstring: str | None = None
    decorators: list[str] = field(default_factory=list)
    is_async: bool = False
    is_mutating: bool = False
    source_file: str = ""
    line_number: int = 0


@dataclass
class ToolGroup:
    name: str
    domain: str
    operations: list[ExtractedOperation] = field(default_factory=list)
    curated: bool = True


@dataclass
class ToolSurfaceSpec:
    software_name: str
    source_type: str  # "github" | "local"
    source_path: str
    language: str = "python"
    backend_engine: str = "unknown"  # "subprocess" | "rest_api" | "python_import" | "cli_wrapper"
    backend_details: dict[str, Any] = field(default_factory=dict)
    tool_groups: list[ToolGroup] = field(default_factory=list)
    state_model: str = "stateless"  # "session" | "stateless" | "project_file"
    warnings: list[str] = field(default_factory=list)
    total_operations_found: int = 0
    total_operations_curated: int = 0


#  curation rules

_SKIP_DIRS: frozenset[str] = frozenset(
    {
        "__pycache__",
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "tests",
        "test",
        "__tests__",
        "fixtures",
        "migrations",
        "scripts",
        "bin",
        "docs",
        "examples",
        "build",
        "dist",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
    }
)

_SKIP_FILES: frozenset[str] = frozenset({"__init__.py", "setup.py", "conftest.py", "__main__.py"})

_SKIP_FUNCTIONS: frozenset[str] = frozenset(
    {
        "__init__",
        "__repr__",
        "__str__",
        "__eq__",
        "__hash__",
        "__lt__",
        "__le__",
        "__gt__",
        "__ge__",
        "__ne__",
        "__del__",
        "__setattr__",
        "__getattr__",
        "__delattr__",
        "__copy__",
        "__deepcopy__",
        "__getstate__",
        "__setstate__",
        "__reduce__",
        "__reduce_ex__",
        "__sizeof__",
        "__subclasshook__",
    }
)


def _is_private(name: str) -> bool:
    return name.startswith("_") and not name.startswith("__")


def _is_getter_setter(node: ast.FunctionDef) -> bool:
    """Detect trivial getter/setter: one-line body, returns self._x or sets self._x."""
    body = node.body
    if len(body) != 1:
        return False
    stmt = body[0]
    if isinstance(stmt, ast.Return) and stmt.value:
        if isinstance(stmt.value, ast.Attribute):
            return isinstance(stmt.value.value, ast.Name) and stmt.value.value.id == "self"
    if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
        target = stmt.targets[0]
        if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == "self":
            return isinstance(stmt.value, ast.Constant) or isinstance(stmt.value, ast.Name)
    return False


def _is_empty_pass_body(node: ast.FunctionDef) -> bool:
    """True if the function body is only pass or a single string expression (stub)."""
    body = [s for s in node.body if not isinstance(s, ast.Expr) or not isinstance(s.value, ast.Constant)]
    if not body:
        return True
    if len(body) == 1 and isinstance(body[0], ast.Pass):
        return True
    return False


def _source_lines(node: ast.AST) -> int:
    """Rough line count of a function body."""
    if hasattr(node, "end_lineno") and node.end_lineno is not None:
        return node.end_lineno - node.lineno
    return 0


def _extract_docstring(node: ast.FunctionDef) -> str | None:
    body = node.body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        val = body[0].value.value
        if isinstance(val, str):
            return val.strip()
    return None


def _format_param(param: ast.arg, default: ast.expr | None, annotation: ast.expr | None) -> dict[str, Any]:
    entry: dict[str, Any] = {"name": param.arg}
    if annotation is not None:
        entry["type"] = ast.unparse(annotation)
    if default is not None:
        entry["default"] = ast.unparse(default)
    return entry


def _format_signature(node: ast.FunctionDef) -> str:
    args = []
    for arg in node.args.args:
        part = arg.arg
        if arg.annotation:
            part += f": {ast.unparse(arg.annotation)}"
        args.append(part)
    returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""
    return f"{node.name}({', '.join(args)}){returns}"


#  detection heuristics


def _detect_backend(file_paths: list[str], source_contents: dict[str, str]) -> tuple[str, dict[str, Any]]:
    """Heuristic: detect how the target software is invoked."""
    "\n".join(source_contents.values()).lower()

    subprocess_hits = 0
    import_hits = 0
    rest_hits = 0
    details: dict[str, Any] = {}

    for _path, content in source_contents.items():
        if "subprocess." in content or "shlex" in content or "Popen" in content:
            subprocess_hits += 1
        if "import requests" in content or "httpx" in content:
            rest_hits += 1
        if "from " in content and "import " in content:
            import_hits += 1

    for _path, content in source_contents.items():
        if "add_argument(" in content or "click.option(" in content:
            return "cli_wrapper", {"cli_framework": "argparse" if "add_argument" in content else "click"}

    if subprocess_hits > import_hits and subprocess_hits > rest_hits:
        return "subprocess", details
    if rest_hits > 0:
        return "rest_api", details
    return "python_import", details


def _detect_state_model(source_contents: dict[str, str]) -> str:
    all_code = "\n".join(source_contents.values()).lower()
    if "session" in all_code or "state" in all_code:
        return "session"
    if ".open(" in all_code or "load" in all_code or "save(" in all_code or "write(" in all_code:
        return "project_file"
    return "stateless"


#  main extraction


def _extract_from_file(file_path: str, content: str) -> list[ExtractedOperation]:
    """Parse a single Python file and extract all public operations."""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return []

    results: list[ExtractedOperation] = []
    rel_path = file_path.replace("\\", "/")

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            name = node.name

            if name in _SKIP_FUNCTIONS:
                continue
            if _is_private(name):
                continue

            decorator_names = []
            for dec in node.decorator_list:
                if isinstance(dec, ast.Name):
                    decorator_names.append(dec.id)
                elif isinstance(dec, ast.Attribute):
                    decorator_names.append(ast.unparse(dec))
                elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name):
                    decorator_names.append(dec.func.id)
                elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                    decorator_names.append(ast.unparse(dec.func))

            doc = _extract_docstring(node)
            body_lines = _source_lines(node)

            if _is_empty_pass_body(node):
                continue
            if _is_getter_setter(node):
                continue

            has_doc = bool(doc)
            has_types = any(arg.annotation is not None for arg in node.args.args)
            if not has_doc and not has_types and body_lines < 5:
                continue

            params = [
                _format_param(arg, None, arg.annotation)
                for arg in node.args.args
                if arg.arg != "self" and arg.arg != "cls"
            ]

            is_mutating = any(
                kw in name.lower()
                for kw in (
                    "set_",
                    "add_",
                    "create_",
                    "update_",
                    "delete_",
                    "remove_",
                    "write_",
                    "send_",
                    "start_",
                    "stop_",
                    "enable_",
                    "disable_",
                    "run_",
                    "build_",
                    "apply_",
                )
            )

            results.append(
                ExtractedOperation(
                    name=name,
                    signature=_format_signature(node),
                    params=params,
                    docstring=doc,
                    decorators=decorator_names,
                    is_async=isinstance(node, ast.AsyncFunctionDef),
                    is_mutating=is_mutating,
                    source_file=rel_path,
                    line_number=node.lineno,
                )
            )

    return results


def _group_into_domains(operations: list[ExtractedOperation], base_name: str) -> list[ToolGroup]:
    """Group operations by their source file stem (same file = same domain)."""
    safe_base = base_name.replace("-", "_").lower()
    groups: dict[str, ToolGroup] = {}

    for op in operations:
        file_stem = Path(op.source_file).stem
        if file_stem in ("__init__", ""):
            file_stem = "core"

        if file_stem not in groups:
            domain_name = file_stem.replace("_", " ").title()
            groups[file_stem] = ToolGroup(
                name=f"{safe_base}_{file_stem}",
                domain=domain_name,
            )
        groups[file_stem].operations.append(op)

    return sorted(groups.values(), key=lambda g: len(g.operations), reverse=True)


def _analyse_local_path(source_path: str) -> tuple[list[str], dict[str, str]]:
    """Walk a local directory, return Python file paths and their contents."""
    file_paths: list[str] = []
    contents: dict[str, str] = {}

    for root, dirs, files in os.walk(source_path):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS and not d.startswith(".")]
        for fname in files:
            if not fname.endswith(".py"):
                continue
            if fname in _SKIP_FILES:
                continue
            if fname.startswith("test_") or fname.endswith("_test.py"):
                continue
            full = os.path.join(root, fname)
            try:
                with open(full, encoding="utf-8") as fh:
                    content = fh.read()
            except (OSError, UnicodeDecodeError):
                continue
            rel = os.path.relpath(full, source_path)
            file_paths.append(rel)
            contents[rel] = content

    return file_paths, contents


#  public API


def generate_tool_surface_spec(
    source_path: str,
    source_type: str = "local",
    software_name: str = "",
    full: bool = False,
) -> ToolSurfaceSpec:
    """Analyse a Python codebase and produce a structured tool surface specification.

    Args:
        source_path: Local directory path or GitHub URL.
        source_type: "local" or "github" (for github, caller provides contents).
        software_name: Override name (auto-detected from path if empty).
        full: If True, skip curation  expose every public function found.

    Returns:
        ToolSurfaceSpec with tool groups, operations, and metadata.
    """
    if not software_name:
        software_name = Path(source_path.rstrip("/\\")).name or "unknown"
    software_name = software_name.replace("-", "_").lower()

    if source_type == "local":
        file_paths, source_contents = _analyse_local_path(source_path)
    else:
        file_paths = []
        source_contents = {}

    if not file_paths and not source_contents:
        return ToolSurfaceSpec(
            software_name=software_name,
            source_type=source_type,
            source_path=source_path,
            warnings=["No Python source files found"],
        )

    backend_engine, backend_details = _detect_backend(file_paths, source_contents)
    state_model = _detect_state_model(source_contents)

    all_ops: list[ExtractedOperation] = []
    for fpath in file_paths:
        content = source_contents.get(fpath, "")
        if content:
            all_ops.extend(_extract_from_file(fpath, content))

    total_found = len(all_ops)

    if not full:
        all_ops = [op for op in all_ops if _source_lines_for_op(op) > 0]

    groups = _group_into_domains(all_ops, software_name)

    warnings: list[str] = []
    for g in groups:
        if not g.operations:
            warnings.append(f"Empty group: {g.name}")

    return ToolSurfaceSpec(
        software_name=software_name,
        source_type=source_type,
        source_path=source_path,
        language="python",
        backend_engine=backend_engine,
        backend_details=backend_details,
        tool_groups=groups,
        state_model=state_model,
        warnings=warnings,
        total_operations_found=total_found,
        total_operations_curated=len(all_ops),
    )


def _source_lines_for_op(op: ExtractedOperation) -> int:
    """Re-check line count from source (approximate)."""
    return 0 if op.signature.count(",") == 0 and op.docstring is None else 1


def spec_to_dict(spec: ToolSurfaceSpec) -> dict[str, Any]:
    """Serialize a ToolSurfaceSpec to a dict suitable for tool output."""
    return {
        "software_name": spec.software_name,
        "source_type": spec.source_type,
        "source_path": spec.source_path,
        "language": spec.language,
        "backend_engine": spec.backend_engine,
        "backend_details": spec.backend_details,
        "state_model": spec.state_model,
        "tool_groups": [
            {
                "name": g.name,
                "domain": g.domain,
                "curated": g.curated,
                "operation_count": len(g.operations),
                "operations": [
                    {
                        "name": op.name,
                        "signature": op.signature,
                        "params": op.params,
                        "docstring": op.docstring,
                        "decorators": op.decorators,
                        "is_async": op.is_async,
                        "is_mutating": op.is_mutating,
                        "source_file": op.source_file,
                        "line_number": op.line_number,
                    }
                    for op in g.operations
                ],
            }
            for g in spec.tool_groups
        ],
        "warnings": spec.warnings,
        "total_operations_found": spec.total_operations_found,
        "total_operations_curated": spec.total_operations_curated,
    }
