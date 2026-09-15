from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_check_endpoint():
    """Health exposes operational status only, never secrets."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "fixhome-ai-service"
    assert "engine" in data
    assert "version" in data
    serialized = str(data).lower()
    assert "api_key" not in serialized
    assert "secret" not in serialized
    assert "weights" not in serialized


def test_catalog_endpoint_lists_closed_vocabulary():
    response = client.get("/api/v1/meta/catalog")
    assert response.status_code == 200
    data = response.json()
    assert len(data["deviceTypes"]) > 0
    assert len(data["visibleConditions"]) > 0
    assert all(item["nameVi"] for item in data["deviceTypes"])
