def test_health_check(api_client):
    """Verify the basic health endpoint is public."""
    response = api_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_telemetry_status_public(api_client):
    """Verify system status is public."""
    response = api_client.get("/api/telemetry/status")
    assert response.status_code == 200
    assert response.json()["industrialized"] is True


def test_telemetry_logs_protected(api_client, monkeypatch):
    """Verify logs require Wurst-Auth."""
    monkeypatch.setenv("WURST_AUTH_TOKEN", "test-wurst-token")
    response = api_client.get("/api/telemetry/logs")
    assert response.status_code == 403  # Forbidden without header


def test_telemetry_logs_authorized(api_client, auth_headers):
    """Verify logs accessible with correct X-Wurst-Auth."""
    response = api_client.get("/api/telemetry/logs", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_logging_bashing_logic():
    """Verify the SOTABashFormatter correctly injects icons."""
    import logging

    from meta_mcp.logging_config import SOTABashFormatter, get_icon

    formatter = SOTABashFormatter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="test.py",
        lineno=1,
        msg="Server starting and initializing",
        args=(),
        exc_info=None,
    )

    formatted = formatter.format(record)
    # Check if a START icon or fallback is present
    start_icon = get_icon("START")
    assert start_icon in formatted
