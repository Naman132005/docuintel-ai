"""Phase 1 — Health endpoint tests."""


def test_root(client):
    """GET / returns 200 with the project welcome message."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "DocuIntel AI" in data["message"]


def test_health_status(client):
    """GET /api/v1/health returns 200 with status 'healthy'."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_health_has_timestamp(client):
    """Health response includes a non-empty timestamp."""
    response = client.get("/api/v1/health")
    data = response.json()
    assert "timestamp" in data
    assert len(data["timestamp"]) > 0


def test_health_has_version(client):
    """Health response version matches the configured version."""
    response = client.get("/api/v1/health")
    data = response.json()
    assert data["version"] == "0.1.0"
