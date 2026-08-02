import json
import re
from pathlib import Path
from typing import Any

import tomli


def analyze_security_orchestration(repo_path: Path) -> dict[str, dict[str, Any]]:
    """Analyze security hardening, authentication, and orchestration frameworks in a repository."""
    result = {
        "security": {
            "has_auth": False,
            "auth_providers": [],
            "prompt_injection_hardening": False,
            "has_security_md": False,
            "secrets_management": [],
        },
        "orchestration": {
            "has_workflows": False,
            "has_supervisors": False,
            "sampling_enabled": False,
            "openfang_integration": False,
            "agent_frameworks": [],
        },
    }

    # -- Security Analysis --

    # Check SECURITY.md
    if (repo_path / "SECURITY.md").exists():
        result["security"]["has_security_md"] = True

    dependencies = set()

    # Extract dependencies from requirements.txt
    req_file = repo_path / "requirements.txt"
    if req_file.exists():
        try:
            content = req_file.read_text(encoding="utf-8")
            for line in content.splitlines():
                line = line.strip().lower()
                if line and not line.startswith("#"):
                    pkg_name = re.split(r"[=><~]=?", line)[0].strip()
                    dependencies.add(pkg_name)
        except Exception:
            pass

    # Extract dependencies from pyproject.toml
    pyproject_file = repo_path / "pyproject.toml"
    if pyproject_file.exists():
        try:
            content = pyproject_file.read_text(encoding="utf-8")
            config = tomli.loads(content)
            deps = config.get("project", {}).get("dependencies", [])
            for dep in deps:
                pkg_name = re.split(r"[=><~=@]", dep)[0].strip().lower()
                dependencies.add(pkg_name)
        except Exception:
            pass

    # Extract dependencies from package.json (Web apps) for Auth & Secrets
    has_package_json = False
    pkg_deps = {}
    for pkg_path in [
        repo_path / "dashboard" / "package.json",
        repo_path / "web_sota" / "package.json",
        repo_path / "package.json",
    ]:
        if pkg_path.exists():
            has_package_json = True
            try:
                content = pkg_path.read_text(encoding="utf-8")
                pkg_data = json.loads(content)
                deps = {
                    **(pkg_data.get("dependencies", {})),
                    **(pkg_data.get("devDependencies", {})),
                }
                for dep in deps.keys():
                    dependencies.add(dep.lower())
                    pkg_deps[dep.lower()] = True
            except Exception:
                pass

    # Auth Detection
    if "fastapi-users" in dependencies or "python-jose" in dependencies or "pyjwt" in dependencies:
        result["security"]["has_auth"] = True
        result["security"]["auth_providers"].append("jwt")
    if "auth0" in dependencies or "authlib" in dependencies:
        result["security"]["has_auth"] = True
        result["security"]["auth_providers"].append("oauth2")

    if has_package_json:
        if "next-auth" in pkg_deps or "@auth/core" in pkg_deps:
            result["security"]["has_auth"] = True
            result["security"]["auth_providers"].append("next-auth")
        if "@clerk/clerk-react" in pkg_deps or "@clerk/nextjs" in pkg_deps:
            result["security"]["has_auth"] = True
            result["security"]["auth_providers"].append("clerk")

    # Prompt Hardening (Bastion/Guardrails)
    if "nemoguardrails" in dependencies or "bastion" in dependencies or "lakera-guard" in dependencies:
        result["security"]["prompt_injection_hardening"] = True

    # Secrets Management
    if "python-dotenv" in dependencies or "dotenv" in dependencies:
        result["security"]["secrets_management"].append("dotenv")
    if "hvac" in dependencies:  # HashiCorp Vault
        result["security"]["secrets_management"].append("vault")

    # -- Orchestration Analysis --

    # Check Workflows directory
    workflows_dirs = [
        repo_path / ".agents" / "workflows",
        repo_path / ".agent" / "workflows",
        repo_path / "_agents" / "workflows",
        repo_path / "_agent" / "workflows",
    ]
    for wdir in workflows_dirs:
        if wdir.exists() and wdir.is_dir() and any(wdir.iterdir()):
            result["orchestration"]["has_workflows"] = True
            break

    # Check Agent Frameworks
    if "langchain" in dependencies or "langgraph" in dependencies:
        result["orchestration"]["agent_frameworks"].append("langchain")
        result["orchestration"]["has_supervisors"] = True  # General assumption for LangGraph uses
    if "crewai" in dependencies:
        result["orchestration"]["agent_frameworks"].append("crewai")
        result["orchestration"]["has_supervisors"] = True
    if "autogen" in dependencies:
        result["orchestration"]["agent_frameworks"].append("autogen")
        result["orchestration"]["has_supervisors"] = True

    # OpenFang & Sampling
    src_dir = repo_path / "src"
    if src_dir.exists():
        # Quick recursive scan for `ctx.sample()` or `openfang`
        for py_file in src_dir.rglob("*.py"):
            try:
                content = py_file.read_text(encoding="utf-8")
                if "ctx.sample(" in content or "FastMCP.sample" in content:
                    result["orchestration"]["sampling_enabled"] = True
                if "openfang" in content:
                    result["orchestration"]["openfang_integration"] = True
            except UnicodeDecodeError:
                pass

    return result
