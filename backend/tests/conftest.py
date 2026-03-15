"""
Shared fixtures for backend tests.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="session")
def client():
    """Reusable test client backed by the real DB."""
    with TestClient(app) as c:
        yield c
