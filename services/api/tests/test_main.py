import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_root_endpoint():
    """Test the root endpoint returns welcome message."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "TuneTrail" in data["message"]
    assert "documentation" in data


def test_health_check():
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "edition" in data


def test_openapi_json():
    """Test OpenAPI JSON spec is available."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()
    assert spec["info"]["title"] == "TuneTrail API"
    assert "paths" in spec
    assert "components" in spec


def test_docs_redirect():
    """Test that /docs endpoint exists."""
    response = client.get("/docs", follow_redirects=False)
    assert response.status_code in [200, 307]  # 200 for docs, 307 for redirect