"""
Assess reports tool suite - scan fleet repos for assess-fix reports.

Operations:
  list:  Scan all repos for .assess-fix-timestamp + latest docs/assess-reports/
  get:   Read a specific repo's latest assess report content
  stats: Aggregate summary across all assessed repos
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Literal

from fastmcp import FastMCP

FLEET_ROOT = Path("D:/Dev/repos")


def _find_timestamp(repo: Path) -> dict[str, Any] | None:
    ts_file = repo / ".assess-fix-timestamp"
    if not ts_file.is_file():
        return None
    try:
        data = json.loads(ts_file.read_text(encoding="utf-8"))
        return {"repo": repo.name, **data}
    except (json.JSONDecodeError, OSError):
        return {"repo": repo.name, "error": "invalid timestamp"}


def _find_latest_report(repo: Path) -> dict[str, Any] | None:
    report_dir = repo / "docs" / "assess-reports"
    if not report_dir.is_dir():
        return None
    reports = sorted(report_dir.glob("*.md"), reverse=True)
    if not reports:
        return None
    latest = reports[0]
    text = latest.read_text(encoding="utf-8")
    score_match = re.search(r"SOTA Score:\s*(\d+)/100", text)
    score = int(score_match.group(1)) if score_match else None
    return {
        "repo": repo.name,
        "report_date": latest.stem,
        "report_path": str(latest.relative_to(FLEET_ROOT)),
        "score": score,
        "preview": text[:500],
    }


def register_assess_reports_tools(mcp: FastMCP):
    """Register assess reports suite with FastMCP."""

    @mcp.tool(name="assess_reports_ops")
    async def assess_reports_ops(
        operation: Literal["list", "get", "stats"],
        repo_name: str | None = None,
    ) -> dict[str, Any]:
        """Scan and read assess-fix reports across all fleet repos.

        [RATIONALE]
        Consolidates report discovery, detail reads, and aggregate stats
        into one tool to keep the tool surface lean.

        ## Operations
        - **list**: All repos with assess-fix-timestamp markers
        - **get**: Full report text + metadata for one repo (requires repo_name)
        - **stats**: Aggregate counts and average score across all assessed repos

        ## Return Format
        {"success": bool, "operation": str, "reports": [...], "total": int, ...}

        ## Examples
        await assess_reports_ops(operation="list")
        await assess_reports_ops(operation="get", repo_name="email-mcp")
        await assess_reports_ops(operation="stats")
        """
        if operation == "list":
            results = []
            for entry in sorted(FLEET_ROOT.iterdir()):
                if not entry.is_dir() or entry.name.startswith("."):
                    continue
                ts = _find_timestamp(entry)
                report = _find_latest_report(entry)
                if ts or report:
                    results.append(
                        {
                            "repo": entry.name,
                            "timestamp": ts,
                            "latest_report": report,
                        }
                    )
            return {"success": True, "operation": "list", "reports": results, "total": len(results)}

        if operation == "get":
            if not repo_name:
                return {"success": False, "error": "repo_name required for get operation"}
            repo = FLEET_ROOT / repo_name
            if not repo.is_dir():
                return {"success": False, "error": f"Repo '{repo_name}' not found at {FLEET_ROOT}"}
            ts = _find_timestamp(repo)
            report = _find_latest_report(repo)
            full_text = ""
            if report:
                report_file = FLEET_ROOT / report["report_path"]
                if report_file.is_file():
                    full_text = report_file.read_text(encoding="utf-8")
            return {
                "success": True,
                "operation": "get",
                "repo": repo_name,
                "timestamp": ts,
                "report": report,
                "full_text": full_text,
            }

        if operation == "stats":
            scores = []
            total = 0
            for entry in sorted(FLEET_ROOT.iterdir()):
                if not entry.is_dir() or entry.name.startswith("."):
                    continue
                ts = _find_timestamp(entry)
                if ts:
                    total += 1
                report = _find_latest_report(entry)
                if report and report["score"] is not None:
                    scores.append(report["score"])
            avg_score = round(sum(scores) / len(scores), 1) if scores else None
            return {
                "success": True,
                "operation": "stats",
                "total_assessed": total,
                "total_with_reports": len(scores),
                "average_score": avg_score,
                "min_score": min(scores) if scores else None,
                "max_score": max(scores) if scores else None,
            }

        return {"success": False, "error": f"Unknown operation: {operation}"}
