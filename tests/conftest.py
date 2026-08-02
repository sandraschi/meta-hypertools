import os
import sys

import pytest
from fastapi.testclient import TestClient

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from meta_mcp.main import app
from meta_mcp.mcp_server import app as mcp_app


@pytest.fixture
def api_client():
    """Fixture for testing the FastAPI web interface."""
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture
def auth_headers(monkeypatch):
    """Standard security headers for Wurst-Auth."""
    from meta_mcp.auth import WURST_AUTH_HEADER

    monkeypatch.setenv("WURST_AUTH_TOKEN", "test-wurst-token")
    return {WURST_AUTH_HEADER: "test-wurst-token"}


@pytest.fixture
def mcp_client():
    """Fixture for testing FastMCP tools directly."""
    return mcp_app


@pytest.fixture
def mock_fleet_registry():
    """Provides a controlled set of apps for runtime testing."""
    return [
        {"id": "test-app-healthy", "name": "Healthy Test App", "port": 9991, "tags": ["test", "backend"]},
        {"id": "test-app-deficient", "name": "Deficient Test App", "port": 9992, "tags": ["test"]},
        {"id": "test-app-offline", "name": "Offline Test App", "port": 9993, "tags": ["test"]},
    ]


@pytest.fixture
def mock_runtime_service(mocker):
    """Mocks the FleetRuntimeService for API integration tests."""
    from meta_mcp.services.fleet_runtime_service import FleetRuntimeService

    # We use mocker (pytest-mock) to easily patch methods
    service = FleetRuntimeService()
    service.audit_fleet = mocker.AsyncMock(
        return_value={
            "success": True,
            "data": {
                "total_apps": 1,
                "healthy": 1,
                "deficient": 0,
                "offline": 0,
                "zombies": 0,
                "apps": [{"id": "mock-app", "label": "Mock App", "port": 8080, "status": "healthy"}],
                "zombie_ports": [],
            },
        }
    )
    service.start_app = mocker.AsyncMock(return_value={"success": True, "message": "Started"})
    service.stop_app = mocker.AsyncMock(return_value={"success": True, "message": "Stopped"})
    return service
