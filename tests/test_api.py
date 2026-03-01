"""
Tests for WarDashboard API endpoints.
Uses dependency overrides for mocked data (no external APIs).
"""

import pandas as pd
import pytest

from api import app
from api.app import (
    get_economics_data,
    get_losses_data,
    get_prediction_data,
    get_recruiting_data,
)

# --- Mock data ---


@pytest.fixture
def sample_losses_df():
    """Minimal quarterly losses DataFrame as returned by get_losses_grouped_quarterly()."""
    return pd.DataFrame(
        {
            "period": pd.to_datetime(["2022-01-01", "2022-04-01"]),
            "year": [2022, 2022],
            "quarter": [1, 2],
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
            "balance_of_trade": [2.0e11, 2.0e11],
            "budget_balance_pct_gdp": [-2.5, -2.5],
            "urals_oil_price": [85.0, 95.0],
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
    assert "recruiting" in data["endpoints"]
    assert "prediction" in data["endpoints"]
    assert "/losses" in data["endpoints"]["losses"]
    assert "/economics" in data["endpoints"]["economics"]
    assert "/recruiting" in data["endpoints"]["recruiting"]
    assert "/prediction" in data["endpoints"]["prediction"]


# --- /losses ---


def test_losses_returns_200(client, sample_losses_df):
    app.dependency_overrides[get_losses_data] = lambda refresh=False: sample_losses_df
    response = client.get("/losses")
    assert response.status_code == 200


def test_losses_returns_json_list(client, sample_losses_df):
    app.dependency_overrides[get_losses_data] = lambda refresh=False: sample_losses_df
    response = client.get("/losses")
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2


def test_losses_records_have_expected_keys(client, sample_losses_df):
    app.dependency_overrides[get_losses_data] = lambda refresh=False: sample_losses_df
    response = client.get("/losses")
    data = response.json()
    expected_keys = {"period", "year", "quarter", "personnel", "uav", "air_defense_systems"}
    for record in data:
        assert set(record.keys()) == expected_keys


def test_losses_dates_are_iso_format(client, sample_losses_df):
    app.dependency_overrides[get_losses_data] = lambda refresh=False: sample_losses_df
    response = client.get("/losses")
    data = response.json()
    assert data[0]["period"] == "2022-01-01"
    assert data[1]["period"] == "2022-04-01"


def test_losses_values_match_mock(client, sample_losses_df):
    app.dependency_overrides[get_losses_data] = lambda refresh=False: sample_losses_df
    response = client.get("/losses")
    data = response.json()
    assert data[0]["personnel"] == 100 and data[0]["uav"] == 5 and data[0]["air_defense_systems"] == 1
    assert data[1]["personnel"] == 200 and data[1]["uav"] == 10 and data[1]["air_defense_systems"] == 2


# --- /economics ---


def test_economics_returns_200(client, sample_economics_df):
    app.dependency_overrides[get_economics_data] = lambda refresh=False: sample_economics_df
    response = client.get("/economics")
    assert response.status_code == 200


def test_economics_returns_json_list(client, sample_economics_df):
    app.dependency_overrides[get_economics_data] = lambda refresh=False: sample_economics_df
    response = client.get("/economics")
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2


def test_economics_records_have_expected_keys(client, sample_economics_df):
    app.dependency_overrides[get_economics_data] = lambda refresh=False: sample_economics_df
    response = client.get("/economics")
    data = response.json()
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
    for record in data:
        assert set(record.keys()) == expected_keys


def test_economics_dates_are_iso_format(client, sample_economics_df):
    app.dependency_overrides[get_economics_data] = lambda refresh=False: sample_economics_df
    response = client.get("/economics")
    data = response.json()
    assert data[0]["period"] == "2022-01-01"
    assert data[1]["period"] == "2022-04-01"


# --- /recruiting ---


@pytest.fixture
def sample_recruiting_df():
    """Minimal quarterly recruiting DataFrame as returned by get_recruiting()."""
    return pd.DataFrame(
        {
            "period": pd.to_datetime(["2023-01-01", "2023-04-01"]),
            "year": [2023, 2023],
            "quarter": [1, 2],
            "contracts_signed_avg_per_quarter": [96750.0, 96750.0],
            "contracts_min_avg_per_quarter": [83750.0, 83750.0],
            "contracts_max_avg_per_quarter": [122500.0, 122500.0],
            "source": ["Independent estimate ~387k", "Independent estimate ~387k"],
        }
    )


def test_recruiting_returns_200(client, sample_recruiting_df):
    app.dependency_overrides[get_recruiting_data] = lambda refresh=False: sample_recruiting_df
    response = client.get("/recruiting")
    assert response.status_code == 200


def test_recruiting_returns_json_list(client, sample_recruiting_df):
    app.dependency_overrides[get_recruiting_data] = lambda refresh=False: sample_recruiting_df
    response = client.get("/recruiting")
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2


def test_recruiting_records_have_expected_keys(client, sample_recruiting_df):
    app.dependency_overrides[get_recruiting_data] = lambda refresh=False: sample_recruiting_df
    response = client.get("/recruiting")
    data = response.json()
    expected_keys = {
        "period",
        "year",
        "quarter",
        "contracts_signed_avg_per_quarter",
        "contracts_min_avg_per_quarter",
        "contracts_max_avg_per_quarter",
        "source",
    }
    for record in data:
        assert set(record.keys()) == expected_keys


# --- /prediction ---


@pytest.fixture
def sample_prediction_results():
    """Minimal prediction results as returned by get_prediction_results()."""
    return [
        {"model": "Exponential smoothing", "predicted_end_quarter": "2028Q3"},
        {"model": "SARIMAX (losses + recruiting)", "predicted_end_quarter": "— (not below threshold in 20q)"},
        {"model": "Ridge recursive (losses + recruiting)", "predicted_end_quarter": "— (not below threshold in 20q)"},
    ]


def test_prediction_returns_200(client, sample_prediction_results):
    app.dependency_overrides[get_prediction_data] = lambda refresh=False: sample_prediction_results
    response = client.get("/prediction")
    assert response.status_code == 200


def test_prediction_returns_results_key(client, sample_prediction_results):
    app.dependency_overrides[get_prediction_data] = lambda refresh=False: sample_prediction_results
    response = client.get("/prediction")
    data = response.json()
    assert "results" in data
    assert isinstance(data["results"], list)


def test_prediction_results_have_model_and_predicted_end_quarter(client, sample_prediction_results):
    app.dependency_overrides[get_prediction_data] = lambda refresh=False: sample_prediction_results
    response = client.get("/prediction")
    data = response.json()
    assert len(data["results"]) == 3
    for record in data["results"]:
        assert set(record.keys()) == {"model", "predicted_end_quarter"}
        assert isinstance(record["model"], str)
        assert isinstance(record["predicted_end_quarter"], str)


def test_prediction_values_match_mock(client, sample_prediction_results):
    app.dependency_overrides[get_prediction_data] = lambda refresh=False: sample_prediction_results
    response = client.get("/prediction")
    data = response.json()
    assert data["results"] == sample_prediction_results


def test_prediction_empty_results_when_get_prediction_returns_empty(client):
    app.dependency_overrides[get_prediction_data] = lambda refresh=False: []
    response = client.get("/prediction")
    assert response.status_code == 200
    data = response.json()
    assert data["results"] == []


def test_recruiting_nan_becomes_null(client):
    """Recruiting data may have NaN; API must serialize as null."""
    df = pd.DataFrame(
        {
            "period": pd.to_datetime(["2022-01-01"]),
            "year": [2022],
            "quarter": [1],
            "contracts_signed_avg_per_quarter": [float("nan")],
            "contracts_min_avg_per_quarter": [float("nan")],
            "contracts_max_avg_per_quarter": [float("nan")],
            "source": ["No data for 2022"],
        }
    )
    app.dependency_overrides[get_recruiting_data] = lambda refresh=False: df
    response = client.get("/recruiting")
    assert response.status_code == 200
    data = response.json()
    assert data[0]["contracts_signed_avg_per_quarter"] is None
    assert data[0]["contracts_min_avg_per_quarter"] is None
    assert data[0]["contracts_max_avg_per_quarter"] is None


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
            "balance_of_trade": [1.0e11],
            "budget_balance_pct_gdp": [-1.5],
            "urals_oil_price": [80.0],
        }
    )
    app.dependency_overrides[get_economics_data] = lambda refresh=False: df
    response = client.get("/economics")
    assert response.status_code == 200
    data = response.json()
    assert data[0]["trade_pct_gdp"] is None


# --- Edge cases ---


def test_losses_empty_list_when_no_data(client):
    empty_df = pd.DataFrame(columns=["period", "year", "quarter", "personnel", "uav", "air_defense_systems"])
    app.dependency_overrides[get_losses_data] = lambda refresh=False: empty_df
    response = client.get("/losses")
    assert response.status_code == 200
    assert response.json() == []


def test_economics_empty_list_when_no_data(client):
    empty_df = pd.DataFrame(
        columns=["period", "year", "gdp_growth", "inflation", "debt_pct_gdp", "trade_pct_gdp", "balance_of_trade", "budget_balance_pct_gdp", "urals_oil_price"]
    )
    app.dependency_overrides[get_economics_data] = lambda refresh=False: empty_df
    response = client.get("/economics")
    assert response.status_code == 200
    assert response.json() == []


def test_recruiting_empty_list_when_no_data(client):
    empty_df = pd.DataFrame(
        columns=[
            "period",
            "year",
            "quarter",
            "contracts_signed_avg_per_quarter",
            "contracts_min_avg_per_quarter",
            "contracts_max_avg_per_quarter",
            "source",
        ]
    )
    app.dependency_overrides[get_recruiting_data] = lambda refresh=False: empty_df
    response = client.get("/recruiting")
    assert response.status_code == 200
    assert response.json() == []


def test_404_for_unknown_path(client):
    response = client.get("/unknown")
    assert response.status_code == 404
