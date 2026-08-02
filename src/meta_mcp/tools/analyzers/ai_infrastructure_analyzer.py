import json
import re
from pathlib import Path
from typing import Any

import tomli


def analyze_ai_infrastructure(repo_path: Path) -> dict[str, dict[str, Any]]:
    """Analyze AI providers, RAG databases, and Observability tools in a repository."""
    result = {
        "ai": {
            "provider": None,
            "tools": [],
            "has_rag": False,
            "rag_tools": [],
            "has_agents": False,
        },
        "infrastructure": {"databases": [], "observability": [], "message_brokers": []},
    }

    dependencies = set()

    # Extract dependencies from requirements.txt
    req_file = repo_path / "requirements.txt"
    if req_file.exists():
        try:
            content = req_file.read_text(encoding="utf-8")
            for line in content.splitlines():
                line = line.strip().lower()
                if line and not line.startswith("#"):
                    # Basic extraction, strip version constraints
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

    # Extract dependencies from package.json (Web apps)
    package_json = repo_path / "dashboard" / "package.json"
    if not package_json.exists():
        package_json = repo_path / "web_sota" / "package.json"

    if package_json.exists():
        try:
            content = package_json.read_text(encoding="utf-8")
            pkg_data = json.loads(content)
            deps = {
                **(pkg_data.get("dependencies", {})),
                **(pkg_data.get("devDependencies", {})),
            }
            for dep in deps.keys():
                dependencies.add(dep.lower())
        except Exception:
            pass

    # -- AI Analysis --

    # Providers
    is_cloud = False
    is_local = False

    if "google-genai" in dependencies or "@google/genai" in dependencies or "vertexai" in dependencies:
        result["ai"]["tools"].append("gemini")
        is_cloud = True

    if "anthropic" in dependencies or "@anthropic-ai/sdk" in dependencies:
        result["ai"]["tools"].append("claude")
        is_cloud = True

    if "openai" in dependencies:
        result["ai"]["tools"].append("openai")
        is_cloud = True

    if "ollama" in dependencies:
        result["ai"]["tools"].append("ollama")
        is_local = True

    if is_cloud and is_local:
        result["ai"]["provider"] = "mixed"
    elif is_cloud:
        result["ai"]["provider"] = "cloud"
    elif is_local:
        result["ai"]["provider"] = "local"

    # RAG
    if "lancedb" in dependencies or "vectordb" in dependencies:
        result["ai"]["has_rag"] = True
        result["ai"]["rag_tools"].append("lancedb")

    if "faiss-cpu" in dependencies or "faiss-gpu" in dependencies:
        result["ai"]["has_rag"] = True
        result["ai"]["rag_tools"].append("faiss")

    if "chromadb" in dependencies:
        result["ai"]["has_rag"] = True
        result["ai"]["rag_tools"].append("chroma")

    # -- Infrastructure Analysis --

    # Databases
    if "psycopg2" in dependencies or "asyncpg" in dependencies or "pg" in dependencies:
        result["infrastructure"]["databases"].append("postgres")
    if "redis" in dependencies or "aioredis" in dependencies:
        result["infrastructure"]["databases"].append("redis")
    if "sqlite3" in dependencies or "aiosqlite" in dependencies:
        result["infrastructure"]["databases"].append("sqlite")
    if "pymongo" in dependencies or "motor" in dependencies or "mongoose" in dependencies:
        result["infrastructure"]["databases"].append("mongodb")

    # Observability
    if "structlog" in dependencies:
        result["infrastructure"]["observability"].append("structlog")
    if "prometheus_client" in dependencies or "prom-client" in dependencies:
        result["infrastructure"]["observability"].append("prometheus")
    if "sentry-sdk" in dependencies or "@sentry/node" in dependencies:
        result["infrastructure"]["observability"].append("sentry")

    # Message Brokers
    if "pika" in dependencies or "aio_pika" in dependencies or "amqplib" in dependencies:
        result["infrastructure"]["message_brokers"].append("rabbitmq")
    if "kafka-python" in dependencies or "confluent-kafka" in dependencies or "kafkajs" in dependencies:
        result["infrastructure"]["message_brokers"].append("kafka")

    return result
