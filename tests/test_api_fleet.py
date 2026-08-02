from unittest.mock import patch


def test_get_fleet_runtime_structure(api_client, auth_headers, mock_runtime_service):
    """Verify the fleet runtime API returns the industrialized SOTA structure."""
    with patch("meta_mcp.api_router.fleet_runtime", mock_runtime_service):
        response = api_client.get("/api/v1/fleet/runtime", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "apps" in data["data"]


def test_fleet_start_auth_required(api_client, monkeypatch):
    """Verify that starting an app requires Wurst-Auth."""
    monkeypatch.setenv("WURST_AUTH_TOKEN", "test-wurst-token")
    response = api_client.post("/api/v1/fleet/start", json={"app_id": "test-app"})
    # Protected by AuthMiddleware should return 401/403
    assert response.status_code in [401, 403]


def test_fleet_start_authorized(api_client, auth_headers, mock_runtime_service):
    """Verify that starting an app works with correct headers."""
    with patch("meta_mcp.api_router.fleet_runtime", mock_runtime_service):
        response = api_client.post("/api/v1/fleet/start", json={"app_id": "test-app"}, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["success"] is True


def test_fleet_stop_authorized(api_client, auth_headers, mock_runtime_service):
    """Verify that stopping an app works with correct headers."""
    with patch("meta_mcp.api_router.fleet_runtime", mock_runtime_service):
        response = api_client.post("/api/v1/fleet/stop", json={"app_id": "test-app"}, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["success"] is True


def test_fleet_invalid_action(api_client, auth_headers, mock_runtime_service):
    """Verify error handling for invalid app IDs."""
    with patch("meta_mcp.api_router.fleet_runtime", mock_runtime_service):
        mock_runtime_service.start_app.return_value = {"success": False, "error": "Not Found"}

        response = api_client.post("/api/v1/fleet/start", json={"app_id": "non-existent"}, headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["success"] is False
