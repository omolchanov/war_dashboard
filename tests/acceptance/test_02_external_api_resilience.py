"""
Acceptance test 2: External API failure and resilience.
Simulates timeouts, 4xx/5xx, malformed responses; verifies API fails (does not return 200).
"""

import importlib
from unittest.mock import patch

import pytest
import requests

from fastapi.testclient import TestClient

from api import app

app_module = importlib.import_module("api.app")
pytestmark = pytest.mark.acceptance


@pytest.fixture
def client():
    return TestClient(app)


def test_losses_timeout_does_not_return_200(client: TestClient):
    """When losses pipeline times out, request fails (exception propagates)."""
    def raise_timeout(*args, **kwargs):
        raise requests.Timeout("Connection timed out")

    with patch.object(app_module, "get_losses_grouped_quarterly", side_effect=raise_timeout):
        with pytest.raises(requests.Timeout):
            client.get("/losses")


def test_losses_upstream_4xx_does_not_return_200(client: TestClient):
    """When upstream returns 4xx, request fails (exception or 5xx)."""
    def raise_404(*args, **kwargs):
        resp = requests.Response()
        resp.status_code = 404
        raise requests.HTTPError("404 Not Found", response=resp)

    with patch.object(app_module, "get_losses_grouped_quarterly", side_effect=raise_404):
        with pytest.raises(requests.HTTPError):
            client.get("/losses")


def test_losses_upstream_5xx_does_not_return_200(client: TestClient):
    """When upstream returns 5xx, request fails (exception or 5xx)."""
    def raise_502(*args, **kwargs):
        resp = requests.Response()
        resp.status_code = 502
        raise requests.HTTPError("502 Bad Gateway", response=resp)

    with patch.object(app_module, "get_losses_grouped_quarterly", side_effect=raise_502):
        with pytest.raises(requests.HTTPError):
            client.get("/losses")


def test_losses_malformed_json_does_not_return_200(client: TestClient):
    """When pipeline raises due to malformed upstream response, request fails."""
    def raise_value_error(*args, **kwargs):
        raise ValueError("Invalid JSON from upstream")

    with patch.object(app_module, "get_losses_grouped_quarterly", side_effect=raise_value_error):
        with pytest.raises(ValueError):
            client.get("/losses")


def test_economics_empty_payload_does_not_return_200(client: TestClient):
    """When economics pipeline raises due to empty upstream data, request fails."""
    def raise_runtime(*args, **kwargs):
        raise RuntimeError("No IMF WEO data returned for Russia.")

    with patch.object(app_module, "get_economics_grouped_quarterly", side_effect=raise_runtime):
        with pytest.raises(RuntimeError):
            client.get("/economics")


def test_prediction_upstream_failure_does_not_return_200(client: TestClient):
    """When prediction fails (e.g. merge error), request fails."""
    def raise_value_error(*args, **kwargs):
        raise ValueError("No personnel column in merged data")

    with patch.object(app_module, "get_prediction_results", side_effect=raise_value_error):
        with pytest.raises(ValueError):
            client.get("/prediction")
