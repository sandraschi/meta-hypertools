"""Fleet cold-start probe  wraps fleet_probes/scripts/fleet-webapp-start-probe.ps1."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from typing import Any

from meta_mcp.fleet_paths import (
    probe_cwd,
    startup_manifest,
    startup_probe_script,
    startup_progress_json,
    startup_report_json,
)
from meta_mcp.fleet_paths import (
    repos_root as fleet_repos_root,
)
from meta_mcp.services.base import MetaMCPService

log = logging.getLogger(__name__)

# Probe orchestrator  must not cold-start/teardown itself during a full fleet run.
_PROBE_HOST_REPOS = frozenset({"meta_mcp"})


class FleetStartupProbeService(MetaMCPService):
    """Run full-stack startup probes across the fleet manifest (sequential + teardown)."""

    def __init__(self) -> None:
        super().__init__()
        self._running_proc: subprocess.Popen[str] | None = None
        self._runner_log_handle: Any = None

    def _repos_root(self) -> str:
        return str(fleet_repos_root())

    def _probe_script(self) -> str:
        return str(startup_probe_script())

    def _read_json(self, path: str) -> dict[str, Any] | None:
        if not os.path.isfile(path):
            return None
        try:
            # PowerShell Set-Content -Encoding utf8 writes BOM; utf-8-sig accepts both.
            with open(path, encoding="utf-8-sig") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None

    def _write_json(self, path: str, payload: dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
            f.write("\n")

    def _is_probe_host(self, repo: str) -> bool:
        return repo.strip().lower() in {r.lower() for r in _PROBE_HOST_REPOS}

    def _manifest_row_skipped(self, row: dict[str, Any]) -> bool:
        repo = str(row.get("repo", ""))
        if self._is_probe_host(repo):
            return True
        return bool(row.get("probeSkip"))

    def _broken_repos_from_report(self) -> set[str]:
        report = self._read_json(str(startup_report_json()))
        if not report:
            return set()
        broken: set[str] = set()
        for row in report.get("results") or []:
            if not isinstance(row, dict):
                continue
            outcome = str(row.get("outcome", ""))
            repo = str(row.get("repo", "")).strip()
            if repo and outcome and outcome not in ("stack_ok", "skip"):
                broken.add(repo)
        return broken

    def _manifest_count(self, repo_filter: str = "", *, broken_only: bool = False) -> int:
        data = self._read_json(str(startup_manifest()))
        if not data or not isinstance(data, list):
            return 0
        if repo_filter:
            return sum(1 for row in data if row.get("repo") == repo_filter)
        if broken_only:
            broken = self._broken_repos_from_report()
            if not broken:
                return 0
            return sum(1 for row in data if row.get("repo") in broken and not self._manifest_row_skipped(row))
        return sum(1 for row in data if not self._manifest_row_skipped(row))

    def is_running(self) -> bool:
        if self._running_proc is None:
            log.debug("is_running: no proc tracked")
            return False
        code = self._running_proc.poll()
        if code is not None:
            log.info("is_running: proc PID %d exited code %s", self._running_proc.pid, code)
            self._running_proc = None
            if self._runner_log_handle is not None:
                self._runner_log_handle.close()
                self._runner_log_handle = None
            return False
        progress = self._read_json(str(startup_progress_json()))
        if progress and progress.get("status") == "complete":
            log.info("is_running: progress says complete, clearing proc")
            self._running_proc = None
            if self._runner_log_handle is not None:
                self._runner_log_handle.close()
                self._runner_log_handle = None
            return False
        log.debug(
            "is_running: proc PID %d alive, progress status=%s",
            self._running_proc.pid,
            (progress or {}).get("status", "n/a"),
        )
        return True

    def run_probe(
        self,
        repo_filter: str = "",
        broken_only: bool = False,
        background: bool = True,
    ) -> dict[str, Any]:
        script = self._probe_script()
        if not os.path.isfile(script):
            return self.create_response(False, f"Probe script not found: {script}")

        if self.is_running():
            return self.create_response(False, "Probe already running", {"status": "running"})

        if broken_only and repo_filter:
            return self.create_response(
                False,
                "Cannot combine repo_filter with broken_only.",
                {"status": "rejected"},
            )

        if repo_filter and self._is_probe_host(repo_filter):
            return self.create_response(
                False,
                f"Cannot cold-start probe host '{repo_filter}' from MetaMCP  it is already running this probe.",
                {"status": "rejected", "excluded_repos": sorted(_PROBE_HOST_REPOS)},
            )

        if broken_only:
            broken = self._broken_repos_from_report()
            if not broken:
                return self.create_response(
                    False,
                    "No prior broken repos  run a full fleet probe first.",
                    {"status": "rejected"},
                )

        repos_root = self._repos_root()
        central_root = str(probe_cwd())
        report_dir = str(startup_report_json().parent)
        args = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            script,
            "-ReportDir",
            report_dir,
        ]
        if repo_filter:
            args += ["-RepoFilter", repo_filter]
        elif broken_only:
            args += ["-BrokenOnly"]
        else:
            args += ["-ExcludeRepos", "meta_mcp"]

        env = os.environ.copy()
        env["FLEET_REPOS_ROOT"] = repos_root
        env["FLEET_PROBE_EXCLUDE_REPOS"] = ",".join(sorted(_PROBE_HOST_REPOS))
        for key in ("VIRTUAL_ENV", "PYTHONPATH", "UV_PROJECT_ENVIRONMENT"):
            env.pop(key, None)

        total = self._manifest_count(repo_filter, broken_only=broken_only)
        started_at = __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        probe_mode = "broken_only" if broken_only else ("single" if repo_filter else "full")
        self._write_json(
            str(startup_progress_json()),
            {
                "generatedAt": started_at,
                "status": "running",
                "reposRoot": repos_root,
                "completed": 0,
                "totalExpected": total,
                "currentRepo": repo_filter or "",
                "probeMode": probe_mode,
                "results": [],
            },
        )

        if background:
            runner_log = str(startup_report_json().parent / "fleet-webapp-probe-runner.log")
            os.makedirs(os.path.dirname(runner_log), exist_ok=True)
            log.info("Spawning probe script=%s repos_root=%s report_dir=%s", script, repos_root, report_dir)
            self._runner_log_handle = open(runner_log, "w", encoding="utf-8")
            proc = subprocess.Popen(
                args,
                cwd=central_root,
                env=env,
                stdout=self._runner_log_handle,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0,
            )
            self._running_proc = proc
            if repo_filter:
                label = f"repo {repo_filter}"
            elif broken_only:
                label = f"broken only ({total} repos)"
            else:
                label = "full fleet"
            return self.create_response(
                True,
                f"Probe started ({label}) - poll report for progress",
                {
                    "status": "running",
                    "pid": proc.pid,
                    "total_expected": total,
                    "repo_filter": repo_filter or None,
                    "broken_only": broken_only,
                    "report_path": str(startup_report_json()),
                    "progress_path": str(startup_progress_json()),
                    "runner_log": runner_log,
                    "hint": "Poll GET /api/v1/fleet/startup-probe/report until status=complete",
                },
            )

        result = subprocess.run(
            args,
            cwd=central_root,
            env=env,
            capture_output=True,
            text=True,
            timeout=7200,
        )
        self._running_proc = None
        report = self.get_report()
        ok = result.returncode == 0
        return self.create_response(
            ok,
            "Probe finished" if ok else f"Probe exited {result.returncode}",
            {
                "status": "complete",
                "returncode": result.returncode,
                "stderr_tail": (result.stderr or "")[-2000:],
                **(report.get("data") or {}),
            },
        )

    def get_report(self) -> dict[str, Any]:
        progress = self._read_json(str(startup_progress_json()))
        final = self._read_json(str(startup_report_json()))
        proc_running = self.is_running()
        progress_status = (progress or {}).get("status")

        log.info(
            "get_report: progress=%s final=%s proc_running=%s progress_status=%s",
            "exists" if progress else None,
            "exists" if final else None,
            proc_running,
            progress_status,
        )

        if progress_status == "running":
            if progress:
                if not proc_running:
                    log.warning("Progress says running but process dead  returning interrupted")
                    return self._format_report(progress, "interrupted", from_progress=True)
                log.info(
                    "Progress says running, process alive  returning progress %s/%s",
                    progress.get("completed", 0),
                    progress.get("totalExpected", "?"),
                )
                return self._format_report(progress, "running", from_progress=True)
            if proc_running:
                return self.create_response(
                    True,
                    "Probe starting",
                    {
                        "status": "running",
                        "completed": 0,
                        "total_expected": 0,
                        "summary": {},
                        "results": [],
                        "from_progress": True,
                    },
                )

        if progress and progress_status == "complete" and final:
            return self._format_report(final, "complete")

        if final:
            return self._format_report(final, "complete")

        if progress:
            return self._format_report(progress, progress.get("status", "idle"), from_progress=True)

        return self.create_response(
            True,
            "No probe report yet  run fleet_startup_probe first",
            {"status": "idle", "summary": {}, "results": [], "total_expected": 0, "completed": 0},
        )

    def _format_report(
        self,
        payload: dict[str, Any],
        status: str,
        *,
        from_progress: bool = False,
    ) -> dict[str, Any]:
        results = payload.get("results", [])
        summary = payload.get("summary") or self._summarize(results)
        total = payload.get("totalExpected") or payload.get("total_expected") or len(results)
        completed = payload.get("completed", len(results))
        current_repo = payload.get("currentRepo") or payload.get("current_repo") or ""
        msg = "Probe in progress" if status == "running" else "Probe report loaded"
        if status == "running" and current_repo:
            msg = f"Probing {current_repo} ({completed}/{total})"
        return self.create_response(
            True,
            msg,
            {
                "status": status,
                "generated_at": payload.get("generatedAt") or payload.get("generated_at"),
                "completed": completed,
                "total_expected": total,
                "current_repo": current_repo or None,
                "summary": summary,
                "comparison": payload.get("comparison"),
                "probe_mode": payload.get("probeMode") or payload.get("probe_mode"),
                "results": results,
                "from_progress": from_progress,
            },
        )

    def _summarize(self, results: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in results:
            outcome = row.get("outcome", "unknown")
            counts[outcome] = counts.get(outcome, 0) + 1
            if row.get("teardownOk") is False:
                counts["teardown_fail"] = counts.get("teardown_fail", 0) + 1
        counts["total"] = len(results)
        counts["stack_ok"] = counts.get("stack_ok", 0)
        return counts

    def probe_single_repo(self, repo: str) -> dict[str, Any]:
        return self.run_probe(repo_filter=repo, background=False)
