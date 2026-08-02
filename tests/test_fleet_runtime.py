import subprocess

import pytest

from meta_mcp.services.fleet_runtime_service import FleetRuntimeService


@pytest.fixture
def mock_runtime_apps():
    return [
        {
            "id": "test-app-healthy",
            "label": "test-app-healthy",
            "port": 9991,
            "frontend_port": 0,
            "health_path": "/health",
            "repo_path": "/tmp/test-app-healthy",
            "start_path": "web_sota/start.ps1",
            "tags": ["backend"],
        },
        {
            "id": "test-app-deficient",
            "label": "test-app-deficient",
            "port": 9992,
            "frontend_port": 0,
            "health_path": "/health",
            "repo_path": "/tmp/test-app-deficient",
            "start_path": "web_sota/start.ps1",
            "tags": ["backend"],
        },
        {
            "id": "test-app-offline",
            "label": "test-app-offline",
            "port": 9993,
            "frontend_port": 0,
            "health_path": "/health",
            "repo_path": "/tmp/test-app-offline",
            "start_path": "web_sota/start.ps1",
            "tags": ["backend"],
        },
    ]


@pytest.mark.asyncio
async def test_audit_fleet_logic(mocker, mock_runtime_apps, tmp_path):
    """Verify that audit_fleet correctly classifies Healthy, Deficient, and Offline states."""
    service = FleetRuntimeService()
    manifest = tmp_path / "fleet-webapp-manifest.json"
    manifest.write_text("[]", encoding="utf-8")

    mocker.patch.object(service, "_manifest_path", return_value=manifest)
    mocker.patch("meta_mcp.services.fleet_runtime_service.load_runtime_apps", return_value=mock_runtime_apps)
    mocker.patch.object(service, "_check_port", side_effect=lambda p: p != 9993)
    mocker.patch.object(
        service,
        "_check_health",
        side_effect=lambda p, hp=None: {"status": "healthy"} if p == 9991 else {"status": "deficient"},
    )

    result = await service.audit_fleet()

    assert result["success"] is True
    data = result["data"]
    assert data["total_apps"] == 3
    assert data["healthy"] == 1
    assert data["deficient"] == 1
    assert data["offline"] == 1


@pytest.mark.asyncio
async def test_start_app_subprocess_call(mocker, tmp_path):
    """Verify start_app triggers start.ps1 via subprocess."""
    service = FleetRuntimeService()
    start_dir = tmp_path / "test-app" / "web_sota"
    start_dir.mkdir(parents=True)
    start_ps1 = start_dir / "start.ps1"
    start_ps1.write_text("$BackendPort = 10701", encoding="utf-8")

    mocker.patch(
        "meta_mcp.services.fleet_runtime_service.find_runtime_app",
        return_value={
            "id": "test-app",
            "repo_path": "/tmp/test-app",
            "start_path": "web_sota/start.ps1",
        },
    )
    mocker.patch(
        "meta_mcp.services.fleet_runtime_service.resolve_start_script",
        return_value=start_ps1,
    )
    mock_popen = mocker.patch("subprocess.Popen")

    result = await service.start_app("test-app")
    assert result["success"] is True

    args, _ = mock_popen.call_args
    assert args[0][-1] == str(start_ps1)
    assert "powershell" in args[0][0].lower()


@pytest.mark.asyncio
async def test_stop_app_logic(mocker):
    """Verify stop_app finds the PID via netstat and kills it."""
    service = FleetRuntimeService()

    mocker.patch(
        "meta_mcp.services.fleet_runtime_service.find_runtime_app",
        return_value={"id": "test-app", "port": 8080},
    )
    mocker.patch(
        "subprocess.check_output",
        return_value=b"  TCP    0.0.0.0:8080           0.0.0.0:0              LISTENING       1234\r\n",
    )
    mock_run = mocker.patch("subprocess.run")

    result = await service.stop_app("test-app")

    assert result["success"] is True
    mock_run.assert_called_once()
    args, _ = mock_run.call_args
    assert "1234" in args[0]


@pytest.mark.asyncio
async def test_stop_app_no_process(mocker):
    """Verify stop_app handles cases where no process is found on the port."""
    service = FleetRuntimeService()

    mocker.patch(
        "meta_mcp.services.fleet_runtime_service.find_runtime_app",
        return_value={"id": "offline-app", "port": 9993},
    )
    mocker.patch("subprocess.check_output", side_effect=subprocess.CalledProcessError(1, "netstat"))

    result = await service.stop_app("offline-app")
    assert result["success"] is True
    assert "No active process" in result["message"]


@pytest.mark.asyncio
async def test_find_zombies_logic(mocker):
    """Verify that _find_zombies correctly identifies unregistered ports in the fleet range."""
    service = FleetRuntimeService()

    registered_apps = [{"id": "app1", "port": 10701}]
    mock_output = (
        b"  TCP    0.0.0.0:10701          0.0.0.0:0              LISTENING       1111\r\n"
        b"  TCP    0.0.0.0:10705          0.0.0.0:0              LISTENING       2222\r\n"
        b"  TCP    0.0.0.0:8080           0.0.0.0:0              LISTENING       3333\r\n"
    )

    mock_process = mocker.Mock()
    mock_process.communicate = mocker.AsyncMock(return_value=(mock_output, b""))
    mocker.patch("asyncio.create_subprocess_shell", return_value=mock_process)

    zombies = await service._find_zombies(registered_apps)

    assert len(zombies) == 1
    assert zombies[0]["port"] == 10705
    assert zombies[0]["pid"] == "2222"
