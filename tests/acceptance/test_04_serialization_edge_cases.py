"""
Acceptance test 4: Serialization edge cases with real-like data.
Large numbers, NaN→null, Unicode, date formats.
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


def test_large_balance_of_trade_serializes_correctly(client):
    """Balance of trade in billions (1e11+) serializes without overflow."""
    df = pd.DataFrame({
        "period": pd.to_datetime(["2022-01-01"]),
        "year": [2022],
        "gdp_growth": [-2.0],
        "inflation": [20.0],
        "debt_pct_gdp": [18.5],
        "trade_pct_gdp": [35.0],
        "balance_of_trade": [2.5e11],
        "budget_balance_pct_gdp": [-2.5],
        "urals_oil_price": [85.0],
    })
    with patch.object(app_module, "get_economics_grouped_quarterly", return_value=df):
        response = client.get("/economics")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["balance_of_trade"] == 250000000000.0


def test_nan_becomes_null_losses(client):
    """NaN in losses serializes as null."""
    df = pd.DataFrame({
        "period": pd.to_datetime(["2022-01-01"]),
        "year": [2022],
        "quarter": [1],
        "personnel": [100],
        "uav": [float("nan")],
        "air_defense_systems": [1],
    })
    with patch.object(app_module, "get_losses_grouped_quarterly", return_value=df):
        response = client.get("/losses")
    assert response.status_code == 200
    data = response.json()
    assert data[0]["uav"] is None


def test_nan_becomes_null_economics(client):
    """NaN in economics (e.g. missing trade_pct_gdp) serializes as null."""
    df = pd.DataFrame({
        "period": pd.to_datetime(["2022-01-01"]),
        "year": [2022],
        "gdp_growth": [1.0],
        "inflation": [5.0],
        "debt_pct_gdp": [20.0],
        "trade_pct_gdp": [float("nan")],
        "balance_of_trade": [1.0e11],
        "budget_balance_pct_gdp": [-1.5],
        "urals_oil_price": [80.0],
    })
    with patch.object(app_module, "get_economics_grouped_quarterly", return_value=df):
        response = client.get("/economics")
    assert response.status_code == 200
    data = response.json()
    assert data[0]["trade_pct_gdp"] is None


def test_unicode_in_source_serializes(client):
    """Unicode in recruiting source string serializes correctly."""
    df = pd.DataFrame({
        "period": pd.to_datetime(["2022-01-01"]),
        "year": [2022],
        "quarter": [1],
        "contracts_signed_avg_per_quarter": [96750.0],
        "contracts_min_avg_per_quarter": [83750.0],
        "contracts_max_avg_per_quarter": [122500.0],
        "source": ["Незалежна оцінка ~387k · Історії"],
    })
    with patch.object(app_module, "get_recruiting", return_value=df):
        response = client.get("/recruiting")
    assert response.status_code == 200
    data = response.json()
    assert "Незалежна" in data[0]["source"]
    assert "Історії" in data[0]["source"]


def test_date_format_iso_yyyy_mm_dd(client):
    """Period dates are ISO YYYY-MM-DD format."""
    df = pd.DataFrame({
        "period": pd.to_datetime(["2022-01-01", "2025-10-01"]),
        "year": [2022, 2025],
        "quarter": [1, 4],
        "personnel": [100, 200],
        "uav": [5, 10],
        "air_defense_systems": [1, 2],
    })
    with patch.object(app_module, "get_losses_grouped_quarterly", return_value=df):
        response = client.get("/losses")
    assert response.status_code == 200
    data = response.json()
    assert data[0]["period"] == "2022-01-01"
    assert data[1]["period"] == "2025-10-01"
