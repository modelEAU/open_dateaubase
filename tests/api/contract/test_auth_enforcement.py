"""Contract tests for API authentication enforcement.

After the secure-by-default router split, every route except /auth and /health
requires a valid bearer token (a user JWT or the configured service token).
These tests run with the global auth bypass disabled (``no_auth_override``).
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from api.config import settings
from api.database import get_db
from api.main import app

pytestmark = pytest.mark.no_auth_override


@pytest.fixture
def client():
    # A dummy DB so dependency resolution (get_auth_service -> get_db) succeeds
    # without a real database; auth fails/succeeds before any query runs.
    app.dependency_overrides[get_db] = lambda: MagicMock()
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_protected_route_rejects_missing_token(client):
    resp = client.get("/api/v1/sites")
    assert resp.status_code == 401


def test_protected_route_rejects_non_bearer(client):
    resp = client.get("/api/v1/sites", headers={"Authorization": "Basic abc"})
    assert resp.status_code == 401


def test_service_token_grants_access(client, monkeypatch):
    monkeypatch.setattr(settings, "service_token", "s3cret-service-token")
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer s3cret-service-token"},
    )
    assert resp.status_code == 200
    assert resp.json()["email"] == "service@open-dateaubase"


def test_wrong_token_is_rejected(client, monkeypatch):
    monkeypatch.setattr(settings, "service_token", "s3cret-service-token")
    resp = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-the-token"},
    )
    assert resp.status_code == 401


def test_login_is_public(client):
    # Login must be reachable without a token (returns 401/422 for bad creds,
    # never 401 for "missing Authorization header").
    resp = client.post("/api/v1/auth/login", json={"email": "x@y.z", "password": "nope"})
    assert resp.status_code != 403
    assert "Authorization header" not in resp.text
