"""Fleet-wide ToolBench codemod — fix MCP annotation keys.

Replaces:
  _READ_ONLY   = {"readonly": True}    →  spec keys
  _MUTATING    = {}                    →  spec keys
  _DESTRUCTIVE = {}                    →  spec keys

Usage: uv run python scripts/codemod_annotations.py repo1 repo2 ...
       uv run python scripts/codemod_annotations.py --fleet
"""

import os
import re
import sys
from pathlib import Path

REPOS_ROOT = os.environ.get("FLEET_REPOS_ROOT", os.environ.get("REPOS_ROOT", r"D:\Dev\repos"))

SPEC = {
    "_READ_ONLY": '{"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}',
    "_MUTATING": '{"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False}',
    "_DESTRUCTIVE": '{"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False, "openWorldHint": False}',
}

_VARS = "|".join(SPEC.keys())

# Match: _READ_ONLY = {"readonly": True}
#        _MUTATING = {}
#        _DESTRUCTIVE = {"destructive": True}
_SINGLE_LINE = re.compile(rf"^(\s*)({_VARS})\s*=\s*\{{.*?\}}\s*$", re.MULTILINE)

# Match multi-line dicts (when it spans lines)
_MULTI_LINE = re.compile(
    rf"^(\s*)({_VARS})\s*=\s*\{{.*?\}}",
    re.MULTILINE | re.DOTALL,
)


def fix_file(filepath: str) -> tuple[str, bool]:
    with open(filepath, encoding="utf-8") as f:
        content = f.read()
    changed = False

    def _replace(m: re.Match) -> str:
        nonlocal changed
        indent, var = m.group(1), m.group(2)
        old = m.group(0)
        new = f"{indent}{var} = {SPEC[var]}"
        if new != old:
            changed = True
        return new

    # Try single-line first, then multi-line for the rest
    content = _SINGLE_LINE.sub(_replace, content)
    # For any remaining (multiline), do a second pass
    content = _MULTI_LINE.sub(_replace, content)
    return content, changed


def scan_repo(repo_path: Path) -> int:
    changed = 0
    for src_dir in [repo_path / "src", repo_path / "web_sota" / "src"]:
        if not src_dir.is_dir():
            continue
        for pyf in sorted(src_dir.rglob("*.py")):
            if any(p.startswith(".") or p in (".venv", "node_modules", "__pycache__") for p in pyf.parts):
                continue
            try:
                new_c, c = fix_file(str(pyf))
                if c:
                    pyf.write_text(new_c, encoding="utf-8")
                    print(f"  {pyf.relative_to(repo_path.parent)}")
                    changed += 1
            except Exception as e:
                print(f"  ERR {pyf}: {e}")
    return changed


def main():
    args = sys.argv[1:]
    if not args:
        print("Usage: python codemod_annotations.py repo1 repo2 ...")
        print("       python codemod_annotations.py --fleet")
        sys.exit(1)

    if "--fleet" in args:
        repos = sorted(Path(REPOS_ROOT).iterdir())
        repos = [r for r in repos if r.is_dir() and (r / "pyproject.toml").exists()]
    else:
        repos = [Path(p) for p in args]

    total = 0
    for r in repos:
        if not r.is_dir():
            continue
        c = scan_repo(r)
        if c:
            print(f"=> {r.name}: {c} files")
        total += c

    print(f"\n{total} files changed across {len(repos)} repos")


if __name__ == "__main__":
    main()
