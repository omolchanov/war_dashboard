"""Shared fixtures for acceptance tests."""

import pytest

from fastapi.testclient import TestClient

from api import app


@pytest.fixture
def client():
    """FastAPI TestClient for the app."""
    return TestClient(app)
