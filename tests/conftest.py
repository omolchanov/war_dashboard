"""Shared fixtures for tests."""

import pytest
from fastapi.testclient import TestClient

from api import app


@pytest.fixture
def client():
    """FastAPI TestClient for the app. Used by unit and acceptance tests."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_dependency_overrides():
    """Clear FastAPI dependency overrides after each test to prevent leakage."""
    yield
    app.dependency_overrides.clear()
