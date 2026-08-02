"""Fleet cold-install probe  wraps fleet_probes/scripts/fleet-cold-install-probe.ps1."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any

from meta_mcp.fleet_paths import (
    cold_install_manifest,
    cold_install_probe_script,
    cold_install_progress_json,
    cold_install_report_json,
    probe_cwd,
)
from meta_mcp.fleet_paths import (
    repos_root as fleet_repos_root,
)
from meta_mcp.services.base import MetaMCPService


class FleetColdInstallService(MetaMCPService):
    """Run INSTALL.md preflight, mcpb checks, and optional sandbox install probes."""

    def __init__(self) -> None:
        super().__init__()
        self._running_proc: subprocess.Popen[str] | None = None
        self._runner_log_handle: Any = None

    def _repos_root(self) -> str:
        return str(fleet_repos_root())

    def _probe_script(self) -> str:
        return str(cold_install_probe_script())

    def _read_json(self, path: str) -> dict[str, Any] | None:
        if not os.path.isfile(path):
            return None
        try:
            with open(path, encoding="utf-8-sig") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None

    def _write_json(self, path: str, payload: dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
            f.write("\n")

    def _broken_repos_from_report(self) -> set[str]:
        report = self._read_json(str(cold_install_report_json()))
        if not report:
            return set()
        broken: set[str] = set()
        for row in report.get("results") or []:
            if not isinstance(row, dict):
                continue
            repo = str(row.get("repo", "")).strip()
            if not repo:
                continue
            outcome = str(row.get("outcome", ""))
            mcpb = str(row.get("mcpbOutcome", ""))
            if outcome and outcome not in ("install_ok", "preflight_ok", "skip"):
                broken.add(repo)
            if mcpb and mcpb not in ("mcpb_ok", "mcpb_no_package", ""):
                broken.add(repo)
        return broken

    def _manifest_count(
        self,
        repo_filter: str = "",
        *,
        broken_only: bool = False,
    ) -> int:
        data = self._read_json(str(cold_install_manifest()))
        if not data or not isinstance(data, list):
            return 0
        if repo_filter:
            return sum(1 for row in data if row.get("repo") == repo_filter)
        if broken_only:
            broken = self._broken_repos_from_report()
            if not broken:
                return 0
            return sum(1 for row in data if row.get("repo") in broken and not row.get("probeSkip"))
        return sum(1 for row in data if not row.get("probeSkip"))

    def is_running(self) -> bool:
        if self._running_proc is None:
            return False
        code = self._running_proc.poll()
        if code is not None:
            self._running_proc = None
            if self._runner_log_handle is not None:
                self._runner_log_handle.close()
                self._runner_log_handle = None
            return False
        progress = self._read_json(str(cold_install_progress_json()))
        if progress and progress.get("status") == "complete":
            self._running_proc = None
            if self._runner_log_handle is not None:
                self._runner_log_handle.close()
                self._runner_log_handle = None
            return False
        return True

    def run_probe(
        self,
        repo_filter: str = "",
        broken_only: bool = False,
        background: bool = True,
        *,
        preflight_only: bool = True,
        execute: bool = False,
        test_mcpb: bool = False,
        host_mcpb_smoke: bool = False,
        batch_size: int = 0,
        mcp_clients: str = "",
    ) -> dict[str, Any]:
        script = self._probe_script()
        if not os.path.isfile(script):
            return self.create_response(False, f"Probe script not found: {script}")

        if self.is_running():
            return self.create_response(False, "Cold-install probe already running", {"status": "running"})

        if broken_only and repo_filter:
            return self.create_response(
                False,
                "Cannot combine repo_filter with broken_only.",
                {"status": "rejected"},
            )

        if broken_only:
            broken = self._broken_repos_from_report()
            if not broken:
                return self.create_response(
                    False,
                    "No prior broken repos  run a full cold-install probe first.",
                    {"status": "rejected"},
                )

        repos_root = self._repos_root()
        central_root = str(probe_cwd())
        args = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            script,
        ]
        if repo_filter:
            args += ["-RepoFilter", repo_filter]
        elif broken_only:
            args += ["-BrokenOnly"]
        if batch_size > 0:
            args += ["-BatchSize", str(batch_size)]
        if execute:
            args += ["-Execute"]
        elif preflight_only:
            args += ["-PreflightOnly"]
        if test_mcpb:
            args += ["-TestMcpb"]
        if host_mcpb_smoke:
            args += ["-HostMcpbSmoke"]
        if mcp_clients.strip():
            args += ["-McpClients", mcp_clients.strip()]

        env = os.environ.copy()
        env["FLEET_REPOS_ROOT"] = repos_root
        for key in ("VIRTUAL_ENV", "PYTHONPATH", "UV_PROJECT_ENVIRONMENT"):
            env.pop(key, None)

        total = self._manifest_count(repo_filter, broken_only=broken_only)
        if batch_size > 0 and total > batch_size:
            total = batch_size

        started_at = __import__("datetime").datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        probe_mode = "broken_only" if broken_only else ("single" if repo_filter else "full")
        self._write_json(
            str(cold_install_progress_json()),
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
            runner_log = str(cold_install_report_json().parent / "fleet-cold-install-probe-runner.log")
            os.makedirs(os.path.dirname(runner_log), exist_ok=True)
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
                f"Cold-install probe started ({label})  poll report for progress",
                {
                    "status": "running",
                    "pid": proc.pid,
                    "total_expected": total,
                    "repo_filter": repo_filter or None,
                    "broken_only": broken_only,
                    "preflight_only": preflight_only and not execute,
                    "execute": execute,
                    "test_mcpb": test_mcpb,
                    "host_mcpb_smoke": host_mcpb_smoke,
                    "report_path": str(cold_install_report_json()),
                    "progress_path": str(cold_install_progress_json()),
                    "runner_log": runner_log,
                    "hint": "Poll GET /api/v1/fleet/cold-install/report until status=complete",
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
            "Cold-install probe finished" if ok else f"Probe exited {result.returncode}",
            {
                "status": "complete",
                "returncode": result.returncode,
                "stderr_tail": (result.stderr or "")[-2000:],
                **(report.get("data") or {}),
            },
        )

    def get_report(self) -> dict[str, Any]:
        progress = self._read_json(str(cold_install_progress_json()))
        final = self._read_json(str(cold_install_report_json()))
        proc_running = self.is_running()
        progress_status = (progress or {}).get("status")

        if progress_status == "running":
            if progress:
                if not proc_running:
                    return self._format_report(progress, "interrupted", from_progress=True)
                return self._format_report(progress, "running", from_progress=True)
            if proc_running:
                return self.create_response(
                    True,
                    "Cold-install probe starting",
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
            "No cold-install report yet  run fleet_cold_install_probe first",
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
        msg = "Cold-install probe in progress" if status == "running" else "Cold-install report loaded"
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
                "preflight_only": payload.get("preflightOnly"),
                "execute": payload.get("execute"),
                "test_mcpb": payload.get("testMcpb"),
                "results": results,
                "from_progress": from_progress,
            },
        )

    def _summarize(self, results: list[dict[str, Any]]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in results:
            outcome = row.get("outcome", "unknown")
            counts[outcome] = counts.get(outcome, 0) + 1
            mcpb = row.get("mcpbOutcome") or row.get("mcpb_outcome")
            if mcpb:
                counts[str(mcpb)] = counts.get(str(mcpb), 0) + 1
        counts["total"] = len(results)
        counts["preflight_ok"] = counts.get("preflight_ok", 0)
        counts["mcpb_ok"] = counts.get("mcpb_ok", 0)
        return counts
