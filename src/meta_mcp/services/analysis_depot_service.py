"""Persistent analysis depot and export to mcp-central-docs (MCD)."""

from __future__ import annotations

import json
import os
import re
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from meta_mcp.fleet_paths import optional_mcp_central_docs
from meta_mcp.services.base import MetaMCPService
from meta_mcp.tools.scan_formatter import format_repo_status_markdown, format_scan_result_markdown

ScanKind = Literal["fleet_runts", "fleet_multidim", "repo_status"]

DEFAULT_LOCAL_DEPOT = Path.home() / ".meta_mcp" / "analysis"
MCD_ANALYSIS_SECTION = "projects/analysis"


def _utc_run_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def _slug(name: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9._-]+", "-", name.strip().lower())
    return s.strip("-") or "unknown"


def _atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _atomic_write_json(path: Path, data: Any) -> None:
    _atomic_write_text(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


class AnalysisDepotService(MetaMCPService):
    """Store scan runs locally and publish summaries to mcp-central-docs."""

    def __init__(self) -> None:
        super().__init__()
        self._local_root = Path(os.environ.get("META_MCP_ANALYSIS_DEPOT", str(DEFAULT_LOCAL_DEPOT))).expanduser()

    def local_root(self) -> Path:
        return self._local_root

    def mcd_root(self) -> Path | None:
        return optional_mcp_central_docs()

    def mcd_analysis_dir(self) -> Path | None:
        root = self.mcd_root()
        if not root:
            return None
        return root / MCD_ANALYSIS_SECTION

    def _index_path(self) -> Path:
        return self._local_root / "index.json"

    def _load_index(self) -> dict[str, Any]:
        path = self._index_path()
        if not path.is_file():
            return {"version": 1, "runs": [], "latest_run_id": None}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {"version": 1, "runs": [], "latest_run_id": None}

    def _save_index(self, index: dict[str, Any]) -> None:
        _atomic_write_json(self._index_path(), index)

    def create_backup(self) -> str | None:
        """Create a timestamped .bak of the latest analysis run index (Batch Mutation Safety)."""
        path = self._index_path()
        if not path.is_file():
            return None
        from datetime import datetime as _dt

        ts = _dt.now().strftime("%Y%m%d_%H%M%S")
        bak_path = path.with_name(f"index_{ts}.json.bak")
        _atomic_write_text(bak_path, path.read_text(encoding="utf-8"))
        return str(bak_path)

    def _run_dir(self, run_id: str) -> Path:
        return self._local_root / "runs" / run_id

    def persist_run(
        self,
        kind: ScanKind,
        payload: dict[str, Any],
        *,
        scan_path: str | None = None,
        repo_name: str | None = None,
    ) -> dict[str, Any]:
        """Write a scan run to the local depot and update the index."""
        if kind == "repo_status" and not payload.get("success", True):
            return self.create_response(False, "Refusing to persist failed repo status", payload)

        if kind != "repo_status" and not payload.get("success", True):
            return self.create_response(False, "Refusing to persist failed fleet scan", payload)

        run_id = _utc_run_id()
        run_dir = self._run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)

        base_name = {
            "fleet_runts": "fleet-runts",
            "fleet_multidim": "fleet-multidim",
            "repo_status": f"repo-{_slug(repo_name or payload.get('name', 'repo'))}",
        }[kind]

        json_path = run_dir / f"{base_name}.json"
        md_path = run_dir / f"{base_name}.md"

        stamp = time.time()
        if "timestamp" not in payload:
            payload = {**payload, "timestamp": stamp}

        _atomic_write_json(json_path, payload)

        if kind == "repo_status":
            md_body = format_repo_status_markdown(payload)
        elif kind == "fleet_runts":
            md_body = format_scan_result_markdown(payload)
        else:
            md_body = self._format_fleet_multidim_markdown(payload)

        header = self._markdown_header(kind, run_id, scan_path, repo_name)
        _atomic_write_text(md_path, header + md_body)

        manifest = {
            "run_id": run_id,
            "kind": kind,
            "scan_path": scan_path or payload.get("scan_path"),
            "repo_name": repo_name or payload.get("name"),
            "created_at": stamp,
            "files": {
                "json": str(json_path.relative_to(self._local_root)).replace("\\", "/"),
                "markdown": str(md_path.relative_to(self._local_root)).replace("\\", "/"),
            },
        }
        _atomic_write_json(run_dir / "manifest.json", manifest)

        index = self._load_index()
        index["runs"] = [manifest, *index.get("runs", [])][:200]
        index["latest_run_id"] = run_id
        self._save_index(index)

        latest_ptr = self._local_root / "latest.json"
        _atomic_write_json(
            latest_ptr,
            {"run_id": run_id, "kind": kind, "manifest": manifest},
        )

        return self.create_response(
            True,
            f"Persisted {kind} run {run_id}",
            {
                "run_id": run_id,
                "local_dir": str(run_dir),
                "json": str(json_path),
                "markdown": str(md_path),
                "kind": kind,
            },
        )

    def list_runs(self, limit: int = 20) -> dict[str, Any]:
        index = self._load_index()
        runs = list(index.get("runs", []))[: max(1, min(limit, 200))]
        return self.create_response(
            True,
            f"{len(runs)} run(s)",
            {
                "depot_root": str(self._local_root),
                "latest_run_id": index.get("latest_run_id"),
                "runs": runs,
            },
        )

    def get_run(self, run_id: str, *, format: str = "json") -> dict[str, Any] | str:
        run_dir = self._run_dir(run_id)
        manifest_path = run_dir / "manifest.json"
        if not manifest_path.is_file():
            return self.create_response(False, f"Unknown run_id: {run_id}")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        json_rel = manifest.get("files", {}).get("json", "")
        json_path = self._local_root / json_rel
        if not json_path.is_file():
            return self.create_response(False, f"Missing payload for run {run_id}")

        payload = json.loads(json_path.read_text(encoding="utf-8"))
        if format == "markdown":
            md_rel = manifest.get("files", {}).get("markdown", "")
            md_path = self._local_root / md_rel
            if md_path.is_file():
                return md_path.read_text(encoding="utf-8")
            kind = manifest.get("kind", "fleet_runts")
            if kind == "repo_status":
                return format_repo_status_markdown(payload)
            if kind == "fleet_runts":
                return format_scan_result_markdown(payload)
            return self._format_fleet_multidim_markdown(payload)

        return self.create_response(True, f"Run {run_id}", {"manifest": manifest, "data": payload})

    def export_to_mcd(
        self,
        *,
        run_id: str | None = None,
        update_project_snapshots: bool = True,
    ) -> dict[str, Any]:
        """Publish a depot run into mcp-central-docs/projects/analysis/."""
        central = self.mcd_root()
        if not central or not central.is_dir():
            return self.create_response(
                False,
                "mcp-central-docs not configured (optional export only).",
                {
                    "recovery_options": [
                        "Set MCP_CENTRAL_DOCS_ROOT",
                        "Clone sandraschi/mcp-central-docs",
                    ],
                },
            )

        index = self._load_index()
        rid = run_id or index.get("latest_run_id")
        if not rid:
            return self.create_response(False, "No runs in depot  run analyze_mcp_runts first")

        run_dir = self._run_dir(rid)
        manifest_path = run_dir / "manifest.json"
        if not manifest_path.is_file():
            return self.create_response(False, f"Unknown run_id: {rid}")

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        kind = manifest.get("kind", "fleet_runts")
        json_rel = manifest.get("files", {}).get("json", "")
        md_rel = manifest.get("files", {}).get("markdown", "")
        json_path = self._local_root / json_rel
        md_path = self._local_root / md_rel
        if not json_path.is_file() or not md_path.is_file():
            return self.create_response(False, f"Run {rid} files missing")

        mcd_dir = self.mcd_analysis_dir()
        mcd_run_dir = mcd_dir / "runs" / rid
        mcd_run_dir.mkdir(parents=True, exist_ok=True)

        payload = json.loads(json_path.read_text(encoding="utf-8"))
        md_text = md_path.read_text(encoding="utf-8")

        written: list[str] = []

        _atomic_write_json(mcd_run_dir / json_path.name, payload)
        written.append(str(mcd_run_dir / json_path.name))
        _atomic_write_json(mcd_run_dir / "manifest.json", manifest)
        written.append(str(mcd_run_dir / "manifest.json"))
        _atomic_write_text(mcd_run_dir / md_path.name, md_text)
        written.append(str(mcd_run_dir / md_path.name))

        _atomic_write_json(mcd_dir / "latest.json", {"run_id": rid, "kind": kind, "manifest": manifest})
        written.append(str(mcd_dir / "latest.json"))

        latest_md_name = {
            "fleet_runts": "FLEET_RUNTS_LATEST.md",
            "fleet_multidim": "FLEET_MULTIDIM_LATEST.md",
            "repo_status": "REPO_STATUS_LATEST.md",
        }[kind if kind in ("fleet_runts", "fleet_multidim", "repo_status") else "fleet_runts"]

        _atomic_write_text(mcd_dir / latest_md_name, md_text)
        written.append(str(mcd_dir / latest_md_name))

        self._refresh_mcd_index(mcd_dir, index)

        project_updates: list[str] = []
        if update_project_snapshots and kind in ("fleet_runts", "fleet_multidim"):
            project_updates = self._export_per_repo_snapshots(central, payload, rid, kind)

        manifest["mcd_exported"] = True
        manifest["mcd_paths"] = written
        _atomic_write_json(mcd_run_dir / "manifest.json", manifest)

        return self.create_response(
            True,
            f"Exported run {rid} to MCD projects/analysis",
            {
                "run_id": rid,
                "kind": kind,
                "mcd_section": str(mcd_dir),
                "files_written": written,
                "project_snapshots": project_updates,
            },
        )

    def _refresh_mcd_index(self, mcd_dir: Path, local_index: dict[str, Any]) -> None:
        lines = [
            "# Fleet analysis index (MetaMCP depot)",
            "",
            f"**Depot (local):** `{self._local_root}`",
            f"**Latest run:** `{local_index.get('latest_run_id') or ''}`",
            "",
            "| Run ID | Kind | Scan path | Repo |",
            "|--------|------|-----------|------|",
        ]
        for run in local_index.get("runs", [])[:30]:
            lines.append(
                f"| `{run.get('run_id', '')}` | {run.get('kind', '')} | "
                f"`{run.get('scan_path') or ''}` | {run.get('repo_name') or ''} |"
            )
        lines.extend(
            [
                "",
                "Refresh: call MCP tool `publish_analysis_to_mcd` or `analyze_mcp_runts` with `export_mcd=true`.",
                "",
            ]
        )
        _atomic_write_text(mcd_dir / "INDEX.md", "\n".join(lines))

        readme = mcd_dir / "README.md"
        if not readme.is_file():
            _atomic_write_text(
                readme,
                "\n".join(
                    [
                        "# Fleet repository analysis (MetaMCP)",
                        "",
                        "Published snapshots from **MetaMCP** `analyze_mcp_runts`, `analyze_fleet`, and "
                        "`show_mcp_status`  not hand-edited.",
                        "",
                        "| File | Content |",
                        "|------|---------|",
                        "| [INDEX.md](./INDEX.md) | Run history |",
                        "| [FLEET_RUNTS_LATEST.md](./FLEET_RUNTS_LATEST.md) | Latest MCP runt/SOTA scan |",
                        "| [FLEET_MULTIDIM_LATEST.md](./FLEET_MULTIDIM_LATEST.md) | Latest multidim fleet scan |",
                        "| [latest.json](./latest.json) | Pointer to latest run |",
                        "| [runs/](./runs/) | Archived runs by UTC id |",
                        "| [repos/](./repos/) | Per-repo snapshots when `projects/<name>/` exists |",
                        "",
                    ]
                ),
            )

    def _export_per_repo_snapshots(
        self,
        central: Path,
        payload: dict[str, Any],
        run_id: str,
        kind: str,
    ) -> list[str]:
        """Write ANALYSIS_SNAPSHOT.md under mcp-central-docs/projects/<repo>/ when present."""
        projects = central / "projects"
        repos_dir = self.mcd_analysis_dir() / "repos"
        repos_dir.mkdir(parents=True, exist_ok=True)
        updated: list[str] = []

        entries: list[dict[str, Any]] = []
        if kind == "fleet_runts":
            entries = list(payload.get("runts") or []) + list(payload.get("sota_repos") or [])
        elif kind == "fleet_multidim":
            entries = list(payload.get("repositories") or [])

        for entry in entries:
            name = entry.get("name") or Path(entry.get("path", "")).name
            if not name:
                continue
            slug = _slug(name)
            block = self._repo_snapshot_markdown(name, entry, run_id, kind)
            repo_copy = repos_dir / f"{slug}.md"
            _atomic_write_text(repo_copy, block)
            updated.append(str(repo_copy))

            project_dir = projects / name
            if not project_dir.is_dir():
                project_dir = projects / slug
            if project_dir.is_dir():
                snap = project_dir / "ANALYSIS_SNAPSHOT.md"
                _atomic_write_text(snap, block)
                updated.append(str(snap))

        return updated

    @staticmethod
    def _markdown_header(
        kind: ScanKind,
        run_id: str,
        scan_path: str | None,
        repo_name: str | None,
    ) -> str:
        when = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
        lines = [
            f"<!-- meta-mcp-analysis run_id={run_id} kind={kind} -->",
            "",
            f"*Generated by MetaMCP analysis depot  {when}*",
            "",
        ]
        if scan_path:
            lines.append(f"**Scan path:** `{scan_path}`")
        if repo_name:
            lines.append(f"**Repository:** `{repo_name}`")
        if scan_path or repo_name:
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _repo_snapshot_markdown(name: str, entry: dict[str, Any], run_id: str, kind: str) -> str:
        when = datetime.now(UTC).strftime("%Y-%m-%d")
        score = entry.get("sota_score", entry.get("mcp", {}).get("sota_score", ""))
        fmv = entry.get("fastmcp_version", entry.get("mcp", {}).get("fastmcp_version", ""))
        classification = entry.get("classification", entry.get("status_label", ""))
        lines = [
            f"# {name}  analysis snapshot",
            "",
            f"**Last exported:** {when}  **Run:** `{run_id}`  **Source:** `{kind}`",
            "",
            "| Field | Value |",
            "|-------|-------|",
            f"| SOTA score | {score} |",
            f"| FastMCP | {fmv} |",
            f"| Classification | {classification} |",
            "",
            f"**Path:** `{entry.get('path', '')}`",
            "",
            "Full fleet context: [../analysis/FLEET_RUNTS_LATEST.md](../analysis/FLEET_RUNTS_LATEST.md) "
            "or [../analysis/FLEET_MULTIDIM_LATEST.md](../analysis/FLEET_MULTIDIM_LATEST.md).",
            "",
        ]
        reasons = entry.get("runt_reasons") or []
        if reasons:
            lines.append("## Issues")
            lines.extend(f"- {r}" for r in reasons[:12])
            lines.append("")
        recs = entry.get("recommendations") or []
        if recs:
            lines.append("## Recommendations")
            lines.extend(f"- {r}" for r in recs[:12])
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _format_fleet_multidim_markdown(result: dict[str, Any]) -> str:
        if not result.get("success"):
            return f"# Fleet analysis failed\n\n**Error:** {result.get('error', 'Unknown')}\n"

        md = [
            "# Fleet multi-dimensional analysis",
            "",
            f"- **Scan path:** `{result.get('scan_path', 'N/A')}`",
            f"- **Repositories:** {result.get('total_repositories', 0)}",
            f"- **Duration:** {result.get('duration_seconds', '')}s",
            "",
            "## Repositories",
            "",
        ]
        for repo in result.get("repositories") or []:
            mcp = repo.get("mcp") or {}
            md.append(f"### {repo.get('name', 'unknown')}")
            md.append(f"- **Classification:** {repo.get('classification', '')}")
            md.append(f"- **FastMCP:** {mcp.get('fastmcp_version', '')}")
            md.append(f"- **SOTA score:** {mcp.get('sota_score', '')}")
            git = repo.get("git") or {}
            if git:
                md.append(f"- **Git:** {git.get('status', git.get('health', ''))}")
            md.append("")
        return "\n".join(md)
