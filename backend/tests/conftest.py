"""Shared test fixtures for DocuIntel AI backend tests."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture()
def client() -> TestClient:
    """Provide a TestClient instance for each test."""
    return TestClient(app)
