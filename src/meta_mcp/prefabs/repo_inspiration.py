"""Prefab-UI card for inspire_repo structure results."""

from __future__ import annotations

from typing import Any

from prefab_ui.components import Badge, Card, CardContent, CardHeader, CardTitle, Metric, Row, Text


def _unwrap_data(result: dict[str, Any]) -> dict[str, Any]:
    if not result.get("success", True) and "data" not in result:
        return result
    data = result.get("data")
    return data if isinstance(data, dict) else result


def build_inspire_structure_card(result: dict[str, Any]) -> Card:
    """Visual card for GitHub repo structure study (list/status surface)."""
    data = _unwrap_data(result)
    owner = str(data.get("owner", ""))
    repo = str(data.get("repo", ""))
    branch = str(data.get("branch", ""))
    profile = str(data.get("profile", "standard"))
    subpath = (data.get("subpath") or "").strip()
    total = data.get("total_source_files")
    shown = data.get("shown_files")
    large = bool(data.get("large_repo_mode"))
    truncated = bool(data.get("tree_truncated_by_github"))
    rate = data.get("rate_limit_remaining")
    cached = data.get("tree_cached")

    title = f"{owner}/{repo} structure"
    message = str(result.get("message", "") or data.get("text", ""))[:200]

    with Card(css_class="max-w-lg") as view:
        with CardHeader():
            CardTitle(title)
            Text(f"branch {branch}  profile {profile}", css_class="text-sm text-muted-foreground")
            Badge("GitHub inspiration")
            if cached:
                Badge("Tree cached")
            if large:
                Badge("Large repo mode")
            if truncated:
                Badge("API truncated")
        with CardContent():
            Row(
                children=[
                    Metric(label="Repository", value=f"{owner}/{repo}"[:48]),
                    Metric(label="Source files", value=str(total if total is not None else "")),
                    Metric(label="Shown", value=str(shown if shown is not None else "")),
                ]
            )
            Row(
                children=[
                    Metric(label="Rate limit", value=str(rate if rate is not None else "n/a")),
                ]
            )
            if subpath:
                Text(f"Subpath: {subpath[:80]}", css_class="text-sm")
            hints = data.get("hints") or []
            if isinstance(hints, list) and hints:
                hint_line = "; ".join(str(h)[:80] for h in hints[:2])
                if len(hints) > 2:
                    hint_line += f" (+{len(hints) - 2} more)"
                Text(hint_line, css_class="text-sm")
            if message:
                Text(message, css_class="text-sm text-muted-foreground mt-2")

    return view
