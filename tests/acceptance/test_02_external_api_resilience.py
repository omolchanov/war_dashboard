"""
Acceptance test 2: External API failure and resilience.
Simulates timeouts, 4xx/5xx, malformed responses; verifies API fails (does not return 200).
Uses dependency_overrides to inject failing data providers.
"""

import pytest
import requests

from api import app
from api.app import get_economics_data, get_losses_data, get_prediction_data

pytestmark = pytest.mark.acceptance


def test_losses_timeout_does_not_return_200(client):
    """When losses pipeline times out, API returns 503 (handled by global exception handler)."""

    def raise_timeout(refresh=False):
        raise requests.Timeout("Connection timed out")

    app.dependency_overrides[get_losses_data] = raise_timeout
    response = client.get("/losses")
    assert response.status_code == 503


def test_losses_upstream_4xx_does_not_return_200(client):
    """When upstream returns 4xx, API returns 503."""

    def raise_404(refresh=False):
        resp = requests.Response()
        resp.status_code = 404
        raise requests.HTTPError("404 Not Found", response=resp)

    app.dependency_overrides[get_losses_data] = raise_404
    response = client.get("/losses")
    assert response.status_code == 503


def test_losses_upstream_5xx_does_not_return_200(client):
    """When upstream returns 5xx, API returns 503."""

    def raise_502(refresh=False):
        resp = requests.Response()
        resp.status_code = 502
        raise requests.HTTPError("502 Bad Gateway", response=resp)

    app.dependency_overrides[get_losses_data] = raise_502
    response = client.get("/losses")
    assert response.status_code == 503


def test_losses_malformed_json_does_not_return_200(client):
    """When pipeline raises due to malformed upstream response, API returns 503."""

    def raise_value_error(refresh=False):
        raise ValueError("Invalid JSON from upstream")

    app.dependency_overrides[get_losses_data] = raise_value_error
    response = client.get("/losses")
    assert response.status_code == 503


def test_economics_empty_payload_does_not_return_200(client):
    """When economics pipeline raises due to empty upstream data, API returns 503."""

    def raise_runtime(refresh=False):
        raise RuntimeError("No IMF WEO data returned for Russia.")

    app.dependency_overrides[get_economics_data] = raise_runtime
    response = client.get("/economics")
    assert response.status_code == 503


def test_prediction_upstream_failure_does_not_return_200(client):
    """When prediction fails (e.g. merge error), API returns 503."""

    def raise_value_error(refresh=False):
        raise ValueError("No personnel column in merged data")

    app.dependency_overrides[get_prediction_data] = raise_value_error
    response = client.get("/prediction")
    assert response.status_code == 503
