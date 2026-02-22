"""
Tests for WarDashboard API endpoints.
Uses mocked data so tests do not depend on external APIs.
"""

import importlib
from unittest.mock import patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api import app

# Module where get_losses_grouped_monthly / get_economics_grouped_quarterly live (for patching)
app_module = importlib.import_module("api.app")


@pytest.fixture
def client():
    return TestClient(app)


# --- Mock data ---


@pytest.fixture
def sample_losses_df():
    """Minimal monthly losses DataFrame as returned by get_losses_grouped_monthly()."""
    return pd.DataFrame(
        {
            "month": pd.to_datetime(["2022-03-01", "2022-04-01"]),
            "personnel": [100, 200],
            "uav": [5, 10],
            "air_defense_systems": [1, 2],
        }
    )


@pytest.fixture
def sample_economics_df():
    """Minimal quarterly economics DataFrame as returned by get_economics_grouped_quarterly()."""
    return pd.DataFrame(
        {
            "period": pd.to_datetime(["2022-01-01", "2022-04-01"]),
            "year": [2022, 2022],
            "gdp_growth": [-2.1, -2.1],
            "inflation": [20.0, 20.0],
            "debt_pct_gdp": [18.5, 18.5],
            "trade_pct_gdp": [35.2, 35.2],
        }
    )


# --- Root ---


def test_root_returns_200(client):
    response = client.get("/")
    assert response.status_code == 200


def test_root_returns_api_info(client):
    response = client.get("/")
    data = response.json()
    assert data["name"] == "WarDashboard API"
    assert "endpoints" in data
    assert "losses" in data["endpoints"]
    assert "economics" in data["endpoints"]
    assert "/losses" in data["endpoints"]["losses"]
    assert "/economics" in data["endpoints"]["economics"]


# --- /losses ---


def test_losses_returns_200(client, sample_losses_df):
    with patch.object(app_module, "get_losses_grouped_monthly", return_value=sample_losses_df):
        response = client.get("/losses")
    assert response.status_code == 200


def test_losses_returns_json_list(client, sample_losses_df):
    with patch.object(app_module, "get_losses_grouped_monthly", return_value=sample_losses_df):
        response = client.get("/losses")
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2


def test_losses_records_have_expected_keys(client, sample_losses_df):
    with patch.object(app_module, "get_losses_grouped_monthly", return_value=sample_losses_df):
        response = client.get("/losses")
    data = response.json()
    expected_keys = {"month", "personnel", "uav", "air_defense_systems"}
    for record in data:
        assert set(record.keys()) == expected_keys


def test_losses_dates_are_iso_format(client, sample_losses_df):
    with patch.object(app_module, "get_losses_grouped_monthly", return_value=sample_losses_df):
        response = client.get("/losses")
    data = response.json()
    assert data[0]["month"] == "2022-03-01"
    assert data[1]["month"] == "2022-04-01"


def test_losses_values_match_mock(client, sample_losses_df):
    with patch.object(app_module, "get_losses_grouped_monthly", return_value=sample_losses_df):
        response = client.get("/losses")
    data = response.json()
    assert data[0]["personnel"] == 100 and data[0]["uav"] == 5 and data[0]["air_defense_systems"] == 1
    assert data[1]["personnel"] == 200 and data[1]["uav"] == 10 and data[1]["air_defense_systems"] == 2


# --- /economics ---


def test_economics_returns_200(client, sample_economics_df):
    with patch.object(app_module, "get_economics_grouped_quarterly", return_value=sample_economics_df):
        response = client.get("/economics")
    assert response.status_code == 200


def test_economics_returns_json_list(client, sample_economics_df):
    with patch.object(app_module, "get_economics_grouped_quarterly", return_value=sample_economics_df):
        response = client.get("/economics")
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2


def test_economics_records_have_expected_keys(client, sample_economics_df):
    with patch.object(app_module, "get_economics_grouped_quarterly", return_value=sample_economics_df):
        response = client.get("/economics")
    data = response.json()
    expected_keys = {"period", "year", "gdp_growth", "inflation", "debt_pct_gdp", "trade_pct_gdp"}
    for record in data:
        assert set(record.keys()) == expected_keys


def test_economics_dates_are_iso_format(client, sample_economics_df):
    with patch.object(app_module, "get_economics_grouped_quarterly", return_value=sample_economics_df):
        response = client.get("/economics")
    data = response.json()
    assert data[0]["period"] == "2022-01-01"
    assert data[1]["period"] == "2022-04-01"


def test_economics_nan_becomes_null(client):
    """Economics data may contain NaN (e.g. missing trade_pct_gdp); API must serialize as null."""
    df = pd.DataFrame(
        {
            "period": pd.to_datetime(["2022-01-01"]),
            "year": [2022],
            "gdp_growth": [1.0],
            "inflation": [5.0],
            "debt_pct_gdp": [20.0],
            "trade_pct_gdp": [float("nan")],
        }
    )
    with patch.object(app_module, "get_economics_grouped_quarterly", return_value=df):
        response = client.get("/economics")
    assert response.status_code == 200
    data = response.json()
    assert data[0]["trade_pct_gdp"] is None


# --- Edge cases ---


def test_losses_empty_list_when_no_data(client):
    empty_df = pd.DataFrame(columns=["month", "personnel", "uav", "air_defense_systems"])
    with patch.object(app_module, "get_losses_grouped_monthly", return_value=empty_df):
        response = client.get("/losses")
    assert response.status_code == 200
    assert response.json() == []


def test_economics_empty_list_when_no_data(client):
    empty_df = pd.DataFrame(
        columns=["period", "year", "gdp_growth", "inflation", "debt_pct_gdp", "trade_pct_gdp"]
    )
    with patch.object(app_module, "get_economics_grouped_quarterly", return_value=empty_df):
        response = client.get("/economics")
    assert response.status_code == 200
    assert response.json() == []


def test_404_for_unknown_path(client):
    response = client.get("/unknown")
    assert response.status_code == 404
