from pathlib import Path
from typing import Any


def analyze_docker_readiness(repo_path: Path) -> dict[str, Any]:
    """Analyze the Docker readiness of a repository."""
    result = {"has_dockerfile": False, "has_compose": False, "is_dockerized": False}

    dockerfile = repo_path / "Dockerfile"
    compose_yml = repo_path / "docker-compose.yml"
    compose_yaml = repo_path / "docker-compose.yaml"

    if dockerfile.exists() and dockerfile.is_file():
        result["has_dockerfile"] = True

    if (compose_yml.exists() and compose_yml.is_file()) or (compose_yaml.exists() and compose_yaml.is_file()):
        result["has_compose"] = True

    result["is_dockerized"] = result["has_dockerfile"] or result["has_compose"]

    return result
