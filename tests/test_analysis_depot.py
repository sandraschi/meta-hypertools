"""Analysis depot persistence and MCD export."""

import json
from pathlib import Path

import pytest

from meta_mcp.services.analysis_depot_service import AnalysisDepotService


@pytest.fixture
def depot_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    local = tmp_path / "depot"
    central = tmp_path / "mcp-central-docs"
    (central / "projects" / "meta_mcp").mkdir(parents=True)
    monkeypatch.setenv("META_MCP_ANALYSIS_DEPOT", str(local))
    monkeypatch.setenv("MCP_CENTRAL_DOCS_ROOT", str(central))
    return local, central


def test_persist_and_export_fleet_runts(depot_dirs):
    _local, central = depot_dirs
    svc = AnalysisDepotService()
    payload = {
        "success": True,
        "scan_path": str(central / "projects"),
        "summary": {"total_mcp_repos": 1, "runts": 0, "sota": 1},
        "runts": [],
        "sota_repos": [
            {
                "name": "meta_mcp",
                "path": str(central / "projects" / "meta_mcp"),
                "sota_score": 90,
                "fastmcp_version": "3.2.0",
                "status_label": "SOTA",
            }
        ],
        "timestamp": 1_700_000_000.0,
    }
    saved = svc.persist_run("fleet_runts", payload, scan_path=payload["scan_path"])
    assert saved["success"] is True
    run_id = saved["data"]["run_id"]

    exported = svc.export_to_mcd(run_id=run_id)
    assert exported["success"] is True

    mcd = central / "projects" / "analysis"
    assert (mcd / "FLEET_RUNTS_LATEST.md").is_file()
    assert (mcd / "runs" / run_id / "fleet-runts.json").is_file()
    assert (mcd / "repos" / "meta_mcp.md").is_file()
    assert (central / "projects" / "meta_mcp" / "ANALYSIS_SNAPSHOT.md").is_file()


def test_list_runs(depot_dirs):
    local, _central = depot_dirs
    svc = AnalysisDepotService()
    svc.persist_run("fleet_runts", {"success": True, "summary": {}, "runts": [], "sota_repos": []})
    listed = svc.list_runs()
    assert listed["success"] is True
    assert len(listed["data"]["runs"]) >= 1
    assert (local / "index.json").is_file()
    index = json.loads((local / "index.json").read_text(encoding="utf-8"))
    assert index.get("latest_run_id")
