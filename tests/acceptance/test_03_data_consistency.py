"""
Acceptance test 3: Data consistency across endpoints.
Period overlap, chronological order, prediction merge compatibility.
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


@pytest.fixture
def consistent_losses_df():
    """Losses data covering 2022 Q1–Q4."""
    return pd.DataFrame({
        "period": pd.to_datetime(["2022-01-01", "2022-04-01", "2022-07-01", "2022-10-01"]),
        "year": [2022, 2022, 2022, 2022],
        "quarter": [1, 2, 3, 4],
        "personnel": [100, 150, 200, 180],
        "uav": [5, 8, 10, 12],
        "air_defense_systems": [1, 2, 2, 3],
    })


@pytest.fixture
def consistent_economics_df():
    """Economics data same quarters as losses."""
    return pd.DataFrame({
        "period": pd.to_datetime(["2022-01-01", "2022-04-01", "2022-07-01", "2022-10-01"]),
        "year": [2022, 2022, 2022, 2022],
        "gdp_growth": [-2.1, -2.1, -2.0, -1.9],
        "inflation": [20.0, 18.0, 16.0, 14.0],
        "debt_pct_gdp": [18.5, 18.5, 19.0, 19.0],
        "trade_pct_gdp": [35.2, 35.2, 35.0, 34.8],
        "balance_of_trade": [2.0e11, 1.8e11, 1.9e11, 2.0e11],
        "budget_balance_pct_gdp": [-2.5, -2.5, -2.0, -1.5],
        "urals_oil_price": [85.0, 95.0, 90.0, 85.0],
    })


@pytest.fixture
def consistent_recruiting_df():
    """Recruiting data same quarters as losses/economics."""
    return pd.DataFrame({
        "period": pd.to_datetime(["2022-01-01", "2022-04-01", "2022-07-01", "2022-10-01"]),
        "year": [2022, 2022, 2022, 2022],
        "quarter": [1, 2, 3, 4],
        "contracts_signed_avg_per_quarter": [96750.0, 96750.0, 96750.0, 96750.0],
        "contracts_min_avg_per_quarter": [83750.0, 83750.0, 83750.0, 83750.0],
        "contracts_max_avg_per_quarter": [122500.0, 122500.0, 122500.0, 122500.0],
        "source": ["Estimate", "Estimate", "Estimate", "Estimate"],
    })


def test_periods_in_chronological_order_losses(client, consistent_losses_df):
    """Losses periods are in chronological order."""
    with patch.object(app_module, "get_losses_grouped_quarterly", return_value=consistent_losses_df):
        response = client.get("/losses")
    assert response.status_code == 200
    data = response.json()
    periods = [r["period"] for r in data]
    assert periods == sorted(periods)


def test_periods_in_chronological_order_economics(client, consistent_economics_df):
    """Economics periods are in chronological order."""
    with patch.object(app_module, "get_economics_grouped_quarterly", return_value=consistent_economics_df):
        response = client.get("/economics")
    assert response.status_code == 200
    data = response.json()
    periods = [r["period"] for r in data]
    assert periods == sorted(periods)


def test_periods_in_chronological_order_recruiting(client, consistent_recruiting_df):
    """Recruiting periods are in chronological order."""
    with patch.object(app_module, "get_recruiting", return_value=consistent_recruiting_df):
        response = client.get("/recruiting")
    assert response.status_code == 200
    data = response.json()
    periods = [r["period"] for r in data]
    assert periods == sorted(periods)


def test_period_format_yyyy_mm_dd_all_endpoints(
    client, consistent_losses_df, consistent_economics_df, consistent_recruiting_df
):
    """All endpoints return period as YYYY-MM-DD."""
    with patch.object(app_module, "get_losses_grouped_quarterly", return_value=consistent_losses_df):
        losses = client.get("/losses").json()
    with patch.object(app_module, "get_economics_grouped_quarterly", return_value=consistent_economics_df):
        economics = client.get("/economics").json()
    with patch.object(app_module, "get_recruiting", return_value=consistent_recruiting_df):
        recruiting = client.get("/recruiting").json()

    for records in (losses, economics, recruiting):
        for r in records:
            p = r["period"]
            assert len(p) == 10 and p[4] == "-" and p[7] == "-"
            parts = p.split("-")
            assert len(parts[0]) == 4 and len(parts[1]) == 2 and len(parts[2]) == 2


def test_prediction_merge_succeeds_with_consistent_data(
    client, consistent_losses_df, consistent_economics_df, consistent_recruiting_df
):
    """Prediction runs successfully when losses and recruiting have overlapping periods."""
    pred_results = [
        {"model": "Exponential smoothing", "predicted_end_quarter": "2028Q3"},
        {"model": "SARIMAX (losses + recruiting)", "predicted_end_quarter": "— (not below threshold in 20q)"},
        {"model": "Ridge recursive (losses + recruiting)", "predicted_end_quarter": "2029Q1"},
    ]

    with (
        patch.object(app_module, "get_losses_grouped_quarterly", return_value=consistent_losses_df),
        patch.object(app_module, "get_economics_grouped_quarterly", return_value=consistent_economics_df),
        patch.object(app_module, "get_recruiting", return_value=consistent_recruiting_df),
        patch.object(app_module, "get_prediction_results", return_value=pred_results),
    ):
        response = client.get("/prediction")
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 3
