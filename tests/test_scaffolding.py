"""Scaffolding service tests  spec-kit project creation."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

from meta_mcp.services.scaffolding_service import ScaffoldingService


@pytest.fixture
def svc():
    return ScaffoldingService()


@pytest.mark.asyncio
async def test_spec_kit_specify_not_found(svc):
    with patch("shutil.which", return_value=None):
        result = await svc.create_project(
            template_type="spec_kit",
            project_name="test-spec",
            output_path="/tmp",
            features={"ai_integration": "opencode"},
        )
    assert result["success"] is False
    assert "specify CLI not found" in result["message"]


@pytest.mark.asyncio
async def test_spec_kit_subprocess_success(svc, tmp_path):
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = "Project created"
    mock_proc.stderr = ""

    with patch("shutil.which", return_value="/usr/bin/specify"):
        with patch("subprocess.run", return_value=mock_proc):
            result = await svc.create_project(
                template_type="spec_kit",
                project_name="test-spec",
                output_path=str(tmp_path),
                features={"ai_integration": "opencode"},
            )
    assert result["success"] is True
    assert "test-spec" in result["message"]
    assert result["data"]["data"]["ai_integration"] == "opencode"
    assert "project_path" in result["data"]["data"]


@pytest.mark.asyncio
async def test_spec_kit_default_integration(svc, tmp_path):
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = ""
    mock_proc.stderr = ""

    with patch("shutil.which", return_value="/usr/bin/specify"):
        with patch("subprocess.run", return_value=mock_proc):
            result = await svc.create_project(
                template_type="spec_kit",
                project_name="default-spec",
                output_path=str(tmp_path),
                features={},
            )
    assert result["success"] is True
    assert result["data"]["data"]["ai_integration"] == "opencode"


@pytest.mark.asyncio
async def test_spec_kit_subprocess_failure(svc, tmp_path):
    mock_proc = MagicMock()
    mock_proc.returncode = 1
    mock_proc.stdout = ""
    mock_proc.stderr = "Something went wrong"

    with patch("shutil.which", return_value="/usr/bin/specify"):
        with patch("subprocess.run", return_value=mock_proc):
            result = await svc.create_project(
                template_type="spec_kit",
                project_name="fail-spec",
                output_path=str(tmp_path),
                features={"ai_integration": "claude"},
            )
    assert result["success"] is False
    assert "specify init failed" in result["message"]


@pytest.mark.asyncio
async def test_spec_kit_timeout(svc, tmp_path):
    with patch("shutil.which", return_value="/usr/bin/specify"):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["specify"], timeout=180)):
            result = await svc.create_project(
                template_type="spec_kit",
                project_name="timeout-spec",
                output_path=str(tmp_path),
                features={"ai_integration": "cursor"},
            )
    assert result["success"] is False
    assert "timed out" in result["message"]


@pytest.mark.asyncio
async def test_spec_kit_unknown_integration_fallback(svc, tmp_path):
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_proc.stdout = ""
    mock_proc.stderr = ""

    with patch("shutil.which", return_value="/usr/bin/specify"):
        with patch("subprocess.run", return_value=mock_proc):
            result = await svc.create_project(
                template_type="spec_kit",
                project_name="weird-spec",
                output_path=str(tmp_path),
                features={"ai_integration": "nonexistent_agent"},
            )
    assert result["success"] is True
    assert result["data"]["data"]["ai_integration"] == "nonexistent_agent"


@pytest.mark.asyncio
async def test_unsupported_template_type(svc):
    result = await svc.create_project(
        template_type="nonexistent",
        project_name="foo",
        output_path="/tmp",
        features={},
    )
    assert result["success"] is False
    assert "Unsupported template type" in result["message"]
