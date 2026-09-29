"""GitHub repo discovery for Repo Inspiration (search + presets + faves data).

Wraps the public GitHub repository search API and maps results to
popularity markers the webapp can render: stars, forks, watchers, open
issues, license, archived flag, cadence (from pushed_at), and a
"rocket" flag (young repo with outsized stars).

Auth is optional: GITHUB_TOKEN env raises the rate limit (30 req/min
vs 10 unauthenticated). No key? Still works, slower.
"""

from __future__ import annotations

import datetime
import os
from typing import Any
from zoneinfo import ZoneInfo

import aiohttp

from meta_mcp.services.base import MetaMCPService

GITHUB_API = "https://api.github.com"

PRESETS: list[dict[str, str]] = [
    {"id": "mcp-trending", "label": "MCP servers, trending", "q": "mcp server in:name,description", "sort": "stars"},
    {"id": "mcp-python", "label": "MCP servers in Python", "q": "mcp-server", "language": "Python", "sort": "stars"},
    {"id": "fastmcp", "label": "FastMCP ecosystem", "q": "fastmcp", "sort": "stars"},
    {"id": "tauri-apps", "label": "Tauri apps", "q": "tauri", "language": "Rust", "sort": "stars"},
    {"id": "rag-starters", "label": "RAG starters", "q": "rag chatbot", "language": "Python", "sort": "stars"},
    {"id": "local-llm", "label": "Local LLM frontends", "q": "ollama webui OR ollama client", "sort": "stars"},
    {"id": "fresh-rockets", "label": "Fresh rockets", "q": "created:>2026-03-01 stars:>200", "sort": "stars"},
    {
        "id": "mcp-typescript",
        "label": "MCP in TypeScript",
        "q": "model-context-protocol",
        "language": "TypeScript",
        "sort": "updated",
    },
]

ROCKET_MAX_AGE_DAYS = 180
ROCKET_MIN_STARS = 200


def _parse_dt(raw: str | None) -> datetime.datetime | None:
    if not raw:
        return None
    try:
        return datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _markers(item: dict[str, Any], now: datetime.datetime) -> dict[str, Any]:
    stars = int(item.get("stargazers_count") or 0)
    created = _parse_dt(item.get("created_at"))
    pushed = _parse_dt(item.get("pushed_at"))
    age_days = (now - created).days if created else None
    idle_days = (now - pushed).days if pushed else None
    if idle_days is None:
        cadence = "unknown"
    elif idle_days <= 7:
        cadence = "hot"
    elif idle_days <= 30:
        cadence = "active"
    elif idle_days <= 180:
        cadence = "quiet"
    else:
        cadence = "dormant"
    rocket = bool(age_days is not None and age_days <= ROCKET_MAX_AGE_DAYS and stars >= ROCKET_MIN_STARS)
    return {
        "stars": stars,
        "forks": int(item.get("forks_count") or 0),
        "watchers": int(item.get("watchers_count") or 0),
        "open_issues": int(item.get("open_issues_count") or 0),
        "license": (item.get("license") or {}).get("spdx_id"),
        "archived": bool(item.get("archived")),
        "language": item.get("language"),
        "topics": list(item.get("topics") or []),
        "created_at": item.get("created_at"),
        "pushed_at": item.get("pushed_at"),
        "cadence": cadence,
        "rocket": rocket,
    }


class RepoDiscoveryService(MetaMCPService):
    """GitHub search proxy + presets (backend holds the token, not the browser)."""

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/vnd.github+json", "User-Agent": "meta-mcp-inspire"}
        token = os.environ.get("GITHUB_TOKEN", "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def presets(self) -> dict[str, Any]:
        return self.create_response(True, f"{len(PRESETS)} discovery presets", {"presets": PRESETS})

    async def search(
        self,
        q: str = "",
        language: str = "",
        topic: str = "",
        min_stars: int = 0,
        sort: str = "stars",
        order: str = "desc",
        per_page: int = 12,
    ) -> dict[str, Any]:
        query = (q or "").strip()
        if language.strip():
            query += f" language:{language.strip()}"
        if topic.strip():
            query += f" topic:{topic.strip()}"
        if min_stars and min_stars > 0:
            query += f" stars:>={int(min_stars)}"
        if not query:
            return self.create_response(False, "Empty query — type something or pick a preset")
        if sort not in ("stars", "forks", "updated"):
            sort = "stars"
        if order not in ("asc", "desc"):
            order = "desc"
        per_page = max(1, min(int(per_page or 12), 30))

        now = datetime.datetime.now(ZoneInfo("Europe/Vienna"))
        timeout = aiohttp.ClientTimeout(total=30)
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    f"{GITHUB_API}/search/repositories",
                    headers=self._headers(),
                    params={"q": query, "sort": sort, "order": order, "per_page": per_page},
                ) as resp:
                    remaining = resp.headers.get("X-RateLimit-Remaining")
                    if resp.status == 403:
                        return self.create_response(
                            False,
                            "GitHub rate limit hit — set GITHUB_TOKEN or wait a minute",
                            {"rate_limit_remaining": remaining},
                        )
                    if resp.status != 200:
                        body = await resp.text()
                        return self.create_response(False, f"GitHub search HTTP {resp.status}", {"detail": body[:300]})
                    data = await resp.json()
        except aiohttp.ClientError as exc:
            return self.create_response(False, f"GitHub search failed: {exc!s}")

        items = []
        for item in data.get("items") or []:
            items.append(
                {
                    "full_name": item.get("full_name", ""),
                    "url": item.get("html_url", ""),
                    "description": item.get("description") or "",
                    "default_branch": item.get("default_branch") or "main",
                    **_markers(item, now),
                }
            )
        return self.create_response(
            True,
            f"{len(items)} repos (of {data.get('total_count', 0)} matches)",
            {"repos": items, "total_count": data.get("total_count", 0), "rate_limit_remaining": remaining},
        )
