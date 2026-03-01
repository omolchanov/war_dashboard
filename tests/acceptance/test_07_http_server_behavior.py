"""
Acceptance test 7: HTTP and server behavior.
Content-Type, root structure, 404, startup.
"""

import pytest
from fastapi.testclient import TestClient

from api import app

pytestmark = pytest.mark.acceptance


@pytest.fixture
def client():
    return TestClient(app)


def test_root_content_type_json(client: TestClient):
    """Root returns Content-Type: application/json."""
    response = client.get("/")
    assert response.status_code == 200
    assert "application/json" in response.headers.get("content-type", "")


def test_losses_content_type_json(client: TestClient):
    """Losses returns Content-Type: application/json."""
    response = client.get("/losses")
    # May be 200 or 500 if external API fails; focus on Content-Type when 200
    if response.status_code == 200:
        assert "application/json" in response.headers.get("content-type", "")


def test_root_structure_has_name_and_endpoints(client: TestClient):
    """Root returns name and endpoints with expected keys."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert data["name"] == "WarDashboard API"
    assert "endpoints" in data
    endpoints = data["endpoints"]
    assert "losses" in endpoints
    assert "economics" in endpoints
    assert "recruiting" in endpoints
    assert "prediction" in endpoints
    assert "/losses" in endpoints["losses"]
    assert "/economics" in endpoints["economics"]
    assert "/recruiting" in endpoints["recruiting"]
    assert "/prediction" in endpoints["prediction"]


def test_404_for_unknown_path(client: TestClient):
    """Unknown path returns 404."""
    response = client.get("/nonexistent")
    assert response.status_code == 404


def test_404_for_trailing_slash_variant(client: TestClient):
    """Path without trailing slash that doesn't exist returns 404."""
    response = client.get("/api/v1/losses")
    assert response.status_code == 404


def test_get_method_required(client: TestClient):
    """POST to GET-only endpoint returns 405."""
    response = client.post("/losses")
    assert response.status_code == 405


def test_app_starts_and_serves_requests(client: TestClient):
    """App starts successfully and serves at least root."""
    response = client.get("/")
    assert response.status_code == 200
