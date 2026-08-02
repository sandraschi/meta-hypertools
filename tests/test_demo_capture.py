"""Tests for demo capture config builders and service orchestration."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from meta_mcp.services.demo_capture_service import DemoCaptureService
from meta_mcp.utils.demo_capture_config import build_demo_config, scan_routes


@pytest.fixture
def sample_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "sample-mcp"
    app_tsx = repo / "web_sota" / "src" / "App.tsx"
    app_tsx.parent.mkdir(parents=True)
    app_tsx.write_text(
        """
        <Route path="/" element={<DashboardPage />} />
        <Route path="/tools" element={<ToolsPage />} />
        """,
        encoding="utf-8",
    )
    (repo / "web_sota" / "package.json").write_text("{}", encoding="utf-8")
    start_ps1 = repo / "web_sota" / "start.ps1"
    start_ps1.write_text("$BackendPort = 11028\n$FrontendPort = 11029\n", encoding="utf-8")
    return repo


def test_build_demo_config(sample_repo: Path):
    config = build_demo_config(sample_repo, description="Show dashboard and tools")
    assert config["backend_port"] == 11028
    assert config["frontend_port"] == 11029
    assert len(config["pages"]) >= 1
    assert any(step["action"] == "goto" for step in config["video_steps"])


def test_scan_routes(sample_repo: Path):
    routes = scan_routes(sample_repo)
    paths = {r["path"] for r in routes}
    assert "/" in paths
    assert "/tools" in paths


def test_plan_config(sample_repo: Path):
    service = DemoCaptureService()
    result = service.plan_config(repo_path=str(sample_repo))
    assert result["success"] is True
    assert result["data"]["config"]["frontend_port"] == 11029


def test_materialize_e2e(sample_repo: Path):
    service = DemoCaptureService()
    config = build_demo_config(sample_repo)
    info = service.materialize_e2e(sample_repo, config)
    e2e = Path(info["e2e_dir"])
    assert (e2e / "config.json").is_file()
    assert (e2e / "demo-video.ts").is_file()
    assert (e2e / "playwright.demo.config.ts").is_file()
    written = json.loads((e2e / "config.json").read_text(encoding="utf-8"))
    assert written["frontend_port"] == 11029


@pytest.mark.asyncio
async def test_record_without_start(mocker, sample_repo: Path):
    service = DemoCaptureService()
    mocker.patch.object(service, "_run_playwright", return_value={"success": True, "returncode": 0})
    mocker.patch(
        "meta_mcp.services.demo_capture_service.find_runtime_app",
        return_value=None,
    )

    result = await service.record(
        repo_path=str(sample_repo),
        start_if_needed=False,
        screenshots=True,
        video=False,
    )
    assert result["success"] is True
    assert "artifacts" in result["data"]


def test_materialize_screencast(sample_repo: Path, tmp_path: Path):
    service = DemoCaptureService()
    source = tmp_path / "capture.webm"
    source.write_bytes(b"webm")
    info = service.materialize_screencast(
        sample_repo,
        title="Sample Demo",
        subtitle="Dashboard tour",
        source_webm=source,
    )
    screencast = Path(info["screencast_dir"])
    assert (screencast / "package.json").is_file()
    assert (screencast / "src" / "DemoComposition.tsx").is_file()
    assert (screencast / "public" / "source.webm").is_file()
    assert Path(info["output_mp4"]).name == "sample-mcp-demo.mp4"


@pytest.mark.asyncio
async def test_render_with_mocked_remotion(mocker, sample_repo: Path, tmp_path: Path):
    service = DemoCaptureService()
    webm = tmp_path / "walk.webm"
    webm.write_bytes(b"webm")
    mocker.patch.object(
        service,
        "_run_remotion_render",
        return_value={"success": True, "output_mp4": str(sample_repo / "docs" / "screenshots" / "sample-mcp-demo.mp4")},
    )
    (sample_repo / "docs" / "screenshots").mkdir(parents=True)
    (sample_repo / "docs" / "screenshots" / "sample-mcp-demo.mp4").write_bytes(b"mp4")

    result = await service.render(repo_path=str(sample_repo), video_path=str(webm), title="Sample")
    assert result["success"] is True
    assert result["data"]["artifacts"]["mp4"]
