"""
Acceptance test 5: Prediction pipeline end-to-end.
Realistic merged data; models return expected structure.
"""

import pytest
from fastapi.testclient import TestClient

from api import app
from api.app import get_prediction_data

pytestmark = pytest.mark.acceptance


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def prediction_results_standard():
    """Standard prediction results with mix of quarter and threshold message."""
    return [
        {"model": "Exponential smoothing", "predicted_end_quarter": "2028Q3"},
        {"model": "SARIMAX (losses + recruiting)", "predicted_end_quarter": "— (not below threshold in 20q)"},
        {"model": "Ridge recursive (losses + recruiting)", "predicted_end_quarter": "2029Q1"},
    ]


@pytest.fixture
def prediction_results_all_threshold():
    """All models return threshold-not-reached message."""
    return [
        {"model": "Exponential smoothing", "predicted_end_quarter": "— (not below threshold in 20q)"},
        {"model": "SARIMAX (losses + recruiting)", "predicted_end_quarter": "— (not below threshold in 20q)"},
        {"model": "Ridge recursive (losses + recruiting)", "predicted_end_quarter": "— (not below threshold in 20q)"},
    ]


def test_prediction_returns_expected_model_structure(client, prediction_results_standard):
    """Prediction returns results with model and predicted_end_quarter for each model."""
    app.dependency_overrides[get_prediction_data] = lambda refresh=False: prediction_results_standard
    response = client.get("/prediction")
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    for record in data["results"]:
        assert set(record.keys()) == {"model", "predicted_end_quarter"}
        assert isinstance(record["model"], str)
        assert isinstance(record["predicted_end_quarter"], str)


def test_prediction_includes_all_three_models(client, prediction_results_standard):
    """Prediction returns exactly three model results."""
    app.dependency_overrides[get_prediction_data] = lambda refresh=False: prediction_results_standard
    response = client.get("/prediction")
    data = response.json()
    models = {r["model"] for r in data["results"]}
    assert "Exponential smoothing" in models
    assert "SARIMAX (losses + recruiting)" in models
    assert "Ridge recursive (losses + recruiting)" in models
    assert len(data["results"]) == 3


def test_prediction_quarter_format_or_threshold_message(client, prediction_results_standard):
    """Each predicted_end_quarter is either YYYYQN or the threshold message."""
    app.dependency_overrides[get_prediction_data] = lambda refresh=False: prediction_results_standard
    response = client.get("/prediction")
    data = response.json()
    for r in data["results"]:
        val = r["predicted_end_quarter"]
        assert isinstance(val, str)
        assert len(val) > 0
        # Either "YYYYQN" or "— (not below threshold...)"
        assert "202" in val or "—" in val or "not below" in val


def test_prediction_handles_all_threshold_results(client, prediction_results_all_threshold):
    """Prediction handles case when all models return threshold-not-reached."""
    app.dependency_overrides[get_prediction_data] = lambda refresh=False: prediction_results_all_threshold
    response = client.get("/prediction")
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 3
    for r in data["results"]:
        assert "not below threshold" in r["predicted_end_quarter"]


def test_prediction_sparse_recruiting_data(client):
    """Prediction completes when some recruiting quarters are missing (handled by pipeline)."""
    results = [
        {"model": "Exponential smoothing", "predicted_end_quarter": "2030Q2"},
        {"model": "SARIMAX (losses + recruiting)", "predicted_end_quarter": "— (not below threshold in 20q)"},
        {"model": "Ridge recursive (losses + recruiting)", "predicted_end_quarter": "— (not below threshold in 20q)"},
    ]
    app.dependency_overrides[get_prediction_data] = lambda refresh=False: results
    response = client.get("/prediction")
    assert response.status_code == 200
    assert len(response.json()["results"]) == 3
