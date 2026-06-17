"""The app-level handler that maps repository EntityNotFoundError -> HTTP 404.

Repositories raise the plain domain error (no FastAPI dependency); api.main
registers a handler that turns it into a 404 JSON response. This pins that
contract by exercising the real handler on the real app via a throwaway route.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import app
from api.v1.errors import EntityNotFoundError


@app.get("/_test_entity_not_found")
def _raise_entity_not_found():
    raise EntityNotFoundError("widget 5 not found")


def test_entity_not_found_maps_to_404():
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/_test_entity_not_found")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "widget 5 not found"}
