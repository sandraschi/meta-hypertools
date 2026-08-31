"""Fleet Ops job runner - catalog-driven script execution with live status.

Starts curated fleet scripts (ops_catalog.py) as background processes, tracks
jobs in memory (log files on disk), and serves a reports browser over the
mcp-central-docs scripts/out directory.

Jobs die with the backend process; log files and script reports persist.
"""

from __future__ import annotations

import re
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from meta_mcp.fleet_paths import fleet_local_root
from meta_mcp.ops_catalog import build_argv, catalog_dicts, command_preview, get_script, mcd_root, meta_mcp_root
from meta_mcp.services.base import MetaMCPService

CREATE_NO_WINDOW = 0x08000000
REPORT_MAX_BYTES = 2_000_000
JOB_MAX_AGE_SECONDS = 24 * 3600


class FleetOpsService(MetaMCPService):
    """Run curated fleet scripts as tracked background jobs."""

    def __init__(self) -> None:
        super().__init__()
        self._jobs: dict[str, dict[str, Any]] = {}
        self._procs: dict[str, subprocess.Popen] = {}
        self._lock = threading.Lock()
        self._log_dir = fleet_local_root() / "ops-logs"
        self._log_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ utils

    def _report_dir(self) -> Path:
        mcd_out = mcd_root() / "scripts" / "out"
        if mcd_out.is_dir():
            return mcd_out
        local_out = meta_mcp_root() / "reports"
        local_out.mkdir(parents=True, exist_ok=True)
        return local_out

    def _job_path(self, job_id: str) -> Path:
        return self._log_dir / f"{job_id}.log"

    def _sweep_finished(self) -> None:
        with self._lock:
            now = time.time()
            for job_id, job in list(self._jobs.items()):
                proc = self._procs.get(job_id)
                if proc is not None and proc.poll() is not None:
                    self._procs.pop(job_id, None)
                    job["exit_code"] = proc.returncode
                    job["status"] = "done" if proc.returncode == 0 else "failed"
                    job["finished_at"] = now
                if (
                    job.get("status") in ("done", "failed", "killed")
                    and now - (job.get("finished_at") or now) > JOB_MAX_AGE_SECONDS
                ):
                    self._jobs.pop(job_id, None)
                    self._procs.pop(job_id, None)

    def _public_job(self, job_id: str) -> dict[str, Any]:
        job = dict(self._jobs[job_id])
        job["id"] = job_id
        log_path = self._job_path(job_id)
        job["log_tail"] = self._log_tail(log_path, 60)
        job["log_path"] = str(log_path)
        return job

    def _log_tail(self, path: Path, n: int) -> str:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            return "\n".join(lines[-n:])
        except OSError:
            return ""

    # ------------------------------------------------------------------ API

    def catalog(self) -> dict[str, Any]:
        return self.create_response(True, f"{len(catalog_dicts())} fleet scripts", {"scripts": catalog_dicts()})

    def start_job(self, script_id: str, params: dict[str, Any]) -> dict[str, Any]:
        entry = get_script(script_id)
        if entry is None:
            return self.create_response(
                False, "Unknown script", error_type="not_found", errors=[f"script_id={script_id}"]
            )
        cwd = meta_mcp_root() if entry.get("cwd") == "meta_mcp" else mcd_root()
        argv = build_argv(script_id, params or {})
        job_id = uuid.uuid4().hex[:8]
        log_path = self._job_path(job_id)
        log_fh = open(log_path, "w", encoding="utf-8", errors="replace")
        try:
            proc = subprocess.Popen(
                argv,
                cwd=str(cwd),
                stdout=log_fh,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                creationflags=CREATE_NO_WINDOW,
            )
        except OSError as e:
            log_fh.close()
            return self.create_response(False, f"Failed to start: {e}", error_type="spawn")
        with self._lock:
            self._procs[job_id] = proc
            self._jobs[job_id] = {
                "script_id": script_id,
                "name": entry["name"],
                "status": "running",
                "exit_code": None,
                "started_at": time.time(),
                "finished_at": None,
                "command": " ".join(f'"{a}"' if " " in a else a for a in argv),
            }
        return self.create_response(
            True,
            f"Started {entry['name']} (job {job_id})",
            {"job": self._public_job(job_id), "command": command_preview(script_id, params or {})},
        )

    def list_jobs(self) -> dict[str, Any]:
        self._sweep_finished()
        jobs = [self._public_job(j) for j in self._jobs]
        jobs.sort(key=lambda j: j["started_at"], reverse=True)
        return self.create_response(True, f"{len(jobs)} jobs", {"jobs": jobs})

    def job_status(self, job_id: str) -> dict[str, Any]:
        self._sweep_finished()
        if job_id not in self._jobs:
            return self.create_response(False, "Job not found", error_type="not_found")
        return self.create_response(True, "Job status", {"job": self._public_job(job_id)})

    def kill_job(self, job_id: str) -> dict[str, Any]:
        self._sweep_finished()
        proc = self._procs.get(job_id)
        if proc is None:
            return self.create_response(False, "Job not running or already finished", error_type="not_found")
        try:
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, timeout=30)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        with self._lock:
            self._procs.pop(job_id, None)
            if job_id in self._jobs:
                self._jobs[job_id]["status"] = "killed"
                self._jobs[job_id]["finished_at"] = time.time()
        return self.create_response(True, f"Killed job {job_id}", {"job": self._public_job(job_id)})

    def list_reports(self) -> dict[str, Any]:
        report_dir = self._report_dir()
        if not report_dir.is_dir():
            return self.create_response(True, "No reports yet", {"reports": []})
        rows = []
        for path in sorted(report_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True):
            if not path.is_file() or path.suffix not in (".json", ".md"):
                continue
            if path.name in ("fleet-webapp-report.progress.json", "fleet-webapp-sweep.progress.json"):
                continue
            if path.stat().st_size > REPORT_MAX_BYTES:
                continue
            rows.append(
                {
                    "name": path.name,
                    "kind": path.suffix.lstrip("."),
                    "size": path.stat().st_size,
                    "mtime": path.stat().st_mtime,
                }
            )
        return self.create_response(True, f"{len(rows)} reports", {"reports": rows[:80]})

    def report_content(self, filename: str) -> dict[str, Any]:
        if not filename or not re.fullmatch(r"[A-Za-z0-9._-]+", filename):
            return self.create_response(False, "Invalid filename", error_type="validation")
        report_dir = self._report_dir().resolve()
        path = (report_dir / filename).resolve()
        if path.parent != report_dir or not path.is_file():
            return self.create_response(False, "Report not found", error_type="not_found")
        if path.suffix not in (".json", ".md") or path.stat().st_size > REPORT_MAX_BYTES:
            return self.create_response(False, "Not a report file", error_type="validation")
        try:
            content = path.read_text(encoding="utf-8-sig", errors="replace")
        except OSError as e:
            return self.create_response(False, f"Read failed: {e}", error_type="read")
        return self.create_response(
            True, path.name, {"name": path.name, "kind": path.suffix.lstrip("."), "content": content}
        )
