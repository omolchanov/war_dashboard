"""
Acceptance test 1: Full-stack happy path (no mocks).
Uses real pipelines; hits external APIs. May be slow and requires network.
"""

import pytest
from fastapi.testclient import TestClient

from api import app

pytestmark = pytest.mark.acceptance


@pytest.fixture
def client():
    return TestClient(app)


def test_root_returns_200(client: TestClient):
    """Root endpoint returns 200."""
    response = client.get("/")
    assert response.status_code == 200


def test_root_returns_api_info(client: TestClient):
    """Root returns API name and endpoints."""
    response = client.get("/")
    data = response.json()
    assert data["name"] == "WarDashboard API"
    assert "endpoints" in data
    assert "losses" in data["endpoints"]
    assert "economics" in data["endpoints"]
    assert "recruiting" in data["endpoints"]
    assert "prediction" in data["endpoints"]


def test_losses_returns_200_and_valid_json(client: TestClient):
    """Losses endpoint returns 200 and valid JSON list."""
    response = client.get("/losses")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1, "Expected at least one quarter of losses data"
    record = data[0]
    assert "period" in record
    assert "year" in record
    assert "quarter" in record
    assert "personnel" in record
    assert "uav" in record
    assert "air_defense_systems" in record


def test_economics_returns_200_and_valid_json(client: TestClient):
    """Economics endpoint returns 200 and valid JSON list."""
    response = client.get("/economics")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1, "Expected at least one quarter of economics data"
    record = data[0]
    expected_keys = {
        "period",
        "year",
        "gdp_growth",
        "inflation",
        "debt_pct_gdp",
        "trade_pct_gdp",
        "balance_of_trade",
        "budget_balance_pct_gdp",
        "urals_oil_price",
    }
    assert expected_keys.issubset(set(record.keys()))


def test_recruiting_returns_200_and_valid_json(client: TestClient):
    """Recruiting endpoint returns 200 and valid JSON list."""
    response = client.get("/recruiting")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if data:
        record = data[0]
        expected_keys = {
            "period",
            "year",
            "quarter",
            "contracts_signed_avg_per_quarter",
            "contracts_min_avg_per_quarter",
            "contracts_max_avg_per_quarter",
            "source",
        }
        assert expected_keys.issubset(set(record.keys()))


def test_prediction_returns_200_and_results(client: TestClient):
    """Prediction endpoint returns 200 and results list."""
    response = client.get("/prediction")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert isinstance(data["results"], list)
    for record in data["results"]:
        assert "model" in record
        assert "predicted_end_quarter" in record
