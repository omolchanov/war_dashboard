"""
Acceptance test 6: Empty and sparse data.
All empty, partial data, single-quarter responses.
"""

import importlib
from unittest.mock import patch

import pandas as pd
import pytest

from fastapi.testclient import TestClient

from api import app

app_module = importlib.import_module("api.app")
pytestmark = pytest.mark.acceptance


@pytest.fixture
def client():
    return TestClient(app)


def test_losses_empty_list_when_no_data(client):
    """Losses returns [] when pipeline returns empty DataFrame."""
    empty = pd.DataFrame(columns=["period", "year", "quarter", "personnel", "uav", "air_defense_systems"])
    with patch.object(app_module, "get_losses_grouped_quarterly", return_value=empty):
        response = client.get("/losses")
    assert response.status_code == 200
    assert response.json() == []


def test_economics_empty_list_when_no_data(client):
    """Economics returns [] when pipeline returns empty DataFrame."""
    empty = pd.DataFrame(columns=[
        "period", "year", "gdp_growth", "inflation", "debt_pct_gdp",
        "trade_pct_gdp", "balance_of_trade", "budget_balance_pct_gdp", "urals_oil_price",
    ])
    with patch.object(app_module, "get_economics_grouped_quarterly", return_value=empty):
        response = client.get("/economics")
    assert response.status_code == 200
    assert response.json() == []


def test_recruiting_empty_list_when_no_data(client):
    """Recruiting returns [] when pipeline returns empty DataFrame."""
    empty = pd.DataFrame(columns=[
        "period", "year", "quarter",
        "contracts_signed_avg_per_quarter", "contracts_min_avg_per_quarter", "contracts_max_avg_per_quarter",
        "source",
    ])
    with patch.object(app_module, "get_recruiting", return_value=empty):
        response = client.get("/recruiting")
    assert response.status_code == 200
    assert response.json() == []


def test_prediction_empty_results_when_no_prediction(client):
    """Prediction returns empty results when get_prediction_results returns []."""
    with patch.object(app_module, "get_prediction_results", return_value=[]):
        response = client.get("/prediction")
    assert response.status_code == 200
    data = response.json()
    assert data["results"] == []


def test_single_quarter_losses_returns_one_record(client):
    """Single quarter of losses returns one-record list."""
    df = pd.DataFrame({
        "period": pd.to_datetime(["2022-01-01"]),
        "year": [2022],
        "quarter": [1],
        "personnel": [100],
        "uav": [5],
        "air_defense_systems": [1],
    })
    with patch.object(app_module, "get_losses_grouped_quarterly", return_value=df):
        response = client.get("/losses")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["period"] == "2022-01-01"


def test_single_quarter_economics_returns_one_record(client):
    """Single quarter of economics returns one-record list."""
    df = pd.DataFrame({
        "period": pd.to_datetime(["2022-01-01"]),
        "year": [2022],
        "gdp_growth": [-2.0],
        "inflation": [20.0],
        "debt_pct_gdp": [18.5],
        "trade_pct_gdp": [35.0],
        "balance_of_trade": [2.0e11],
        "budget_balance_pct_gdp": [-2.5],
        "urals_oil_price": [85.0],
    })
    with patch.object(app_module, "get_economics_grouped_quarterly", return_value=df):
        response = client.get("/economics")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1


def test_partial_recruiting_losses_and_economics_full(client):
    """Recruiting empty but losses/economics have data; each endpoint behaves correctly."""
    losses_df = pd.DataFrame({
        "period": pd.to_datetime(["2022-01-01"]),
        "year": [2022],
        "quarter": [1],
        "personnel": [100],
        "uav": [5],
        "air_defense_systems": [1],
    })
    economics_df = pd.DataFrame({
        "period": pd.to_datetime(["2022-01-01"]),
        "year": [2022],
        "gdp_growth": [-2.0],
        "inflation": [20.0],
        "debt_pct_gdp": [18.5],
        "trade_pct_gdp": [35.0],
        "balance_of_trade": [2.0e11],
        "budget_balance_pct_gdp": [-2.5],
        "urals_oil_price": [85.0],
    })
    recruiting_empty = pd.DataFrame(columns=[
        "period", "year", "quarter",
        "contracts_signed_avg_per_quarter", "contracts_min_avg_per_quarter", "contracts_max_avg_per_quarter",
        "source",
    ])
    pred_results = [{"model": "Exponential smoothing", "predicted_end_quarter": "2028Q3"}]

    with (
        patch.object(app_module, "get_losses_grouped_quarterly", return_value=losses_df),
        patch.object(app_module, "get_economics_grouped_quarterly", return_value=economics_df),
        patch.object(app_module, "get_recruiting", return_value=recruiting_empty),
        patch.object(app_module, "get_prediction_results", return_value=pred_results),
    ):
        r_losses = client.get("/losses")
        r_economics = client.get("/economics")
        r_recruiting = client.get("/recruiting")
        r_prediction = client.get("/prediction")

    assert r_losses.status_code == 200 and len(r_losses.json()) == 1
    assert r_economics.status_code == 200 and len(r_economics.json()) == 1
    assert r_recruiting.status_code == 200 and r_recruiting.json() == []
    assert r_prediction.status_code == 200 and len(r_prediction.json()["results"]) == 1
