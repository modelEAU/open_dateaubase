"""Contract tests for strict-mode ingest and the /lookup/tags endpoint.

Tests run without a live database using dependency_overrides and patch.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.database import get_db
from api.main import app

_REPO = "api.v1.endpoints.ingest.signal_interface_repository"
_LOOKUP_REPO = "api.v1.endpoints.ingest.lookup_repository"
_ING_REPO = "api.v1.endpoints.ingest.ingestion_repository"
_VAL_REPO = "api.v1.endpoints.ingest.value_repository"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_conn():
    conn = MagicMock()

    def _override():
        yield conn

    app.dependency_overrides[get_db] = _override
    yield conn
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# GET /ingest/lookup/tags
# ---------------------------------------------------------------------------


class TestTagsLookupEndpoint:
    def test_returns_tags_for_known_das(self, client, mock_conn):
        tags = [
            {"signal_interface_id": 1, "name": "TIT-101"},
            {"signal_interface_id": 2, "name": "TIT-102"},
        ]
        with patch(f"{_LOOKUP_REPO}.get_tags_lookup", return_value=tags) as mock_fn:
            resp = client.get("/api/v1/ingest/lookup/tags", params={"das_id": 5})

        assert resp.status_code == 200
        assert resp.json() == tags
        mock_fn.assert_called_once_with(mock_conn, 5)

    def test_returns_empty_list_for_unknown_das(self, client, mock_conn):
        with patch(f"{_LOOKUP_REPO}.get_tags_lookup", return_value=[]):
            resp = client.get("/api/v1/ingest/lookup/tags", params={"das_id": 999})

        assert resp.status_code == 200
        assert resp.json() == []

    def test_missing_das_id_returns_422(self, client, mock_conn):
        resp = client.get("/api/v1/ingest/lookup/tags")
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /ingest/sensor  with strict=True
# ---------------------------------------------------------------------------

_VALID_PAYLOAD = {
    "das_name": "PlantSCADA",
    "tag": "TIT-101",
    "channel_kind": "value",
    "parameter_name": "temperature",
    "unit_name": "degC",
    "data_provenance_kind_id": 1,
    "strict": True,
    "values": [{"timestamp": "2024-01-01T00:00:00", "value": 22.5}],
}


class TestStrictModeTagged:
    def test_unknown_das_returns_422(self, client, mock_conn):
        """strict=True: DAS not in DB → 422, no write."""
        with (
            patch(f"{_REPO}.find_channel_kind_by_name", return_value=1),
            patch(f"{_REPO}.find_parameter_by_name", return_value=7),
            patch(f"{_REPO}.find_unit_by_name", return_value=3),
            patch(f"{_REPO}.find_das_by_name", return_value=None) as mock_das,
            patch(f"{_REPO}.find_or_create_das") as mock_create_das,
            patch(f"{_ING_REPO}.find_or_create_sensor_metadata") as mock_chan,
            patch(f"{_VAL_REPO}.insert_scalar_values") as mock_write,
        ):
            resp = client.post("/api/v1/ingest/sensor", json=_VALID_PAYLOAD)

        assert resp.status_code == 422
        detail = resp.json()["detail"].lower()
        assert "das" in detail
        mock_das.assert_called_once()
        mock_create_das.assert_not_called()
        mock_chan.assert_not_called()
        mock_write.assert_not_called()

    def test_unknown_tag_returns_422(self, client, mock_conn):
        """strict=True: DAS found but tag missing → 422, no write."""
        with (
            patch(f"{_REPO}.find_channel_kind_by_name", return_value=1),
            patch(f"{_REPO}.find_parameter_by_name", return_value=7),
            patch(f"{_REPO}.find_unit_by_name", return_value=3),
            patch(f"{_REPO}.find_das_by_name", return_value=10),
            patch(f"{_REPO}.find_signal_interface_by_das_and_name", return_value=None) as mock_si,
            patch(f"{_REPO}.find_or_create_signal_interface") as mock_create_si,
            patch(f"{_ING_REPO}.find_or_create_sensor_metadata") as mock_chan,
            patch(f"{_VAL_REPO}.insert_scalar_values") as mock_write,
        ):
            resp = client.post("/api/v1/ingest/sensor", json=_VALID_PAYLOAD)

        assert resp.status_code == 422
        detail = resp.json()["detail"].lower()
        assert "tag" in detail or "signal" in detail
        mock_si.assert_called_once()
        mock_create_si.assert_not_called()
        mock_chan.assert_not_called()
        mock_write.assert_not_called()

    def test_non_strict_still_creates_das(self, client, mock_conn):
        """strict=False (default): unknown DAS is auto-created, no 422."""
        payload = {**_VALID_PAYLOAD, "strict": False}
        with (
            patch(f"{_REPO}.find_channel_kind_by_name", return_value=1),
            patch(f"{_REPO}.find_parameter_by_name", return_value=7),
            patch(f"{_REPO}.find_unit_by_name", return_value=3),
            patch(f"{_REPO}.find_or_create_das", return_value=(10, True)) as mock_das,
            patch(
                f"{_REPO}.find_signal_interface_by_das_and_name", return_value=None
            ),
            patch(f"{_REPO}.find_or_create_signal_interface", return_value=(20, True)),
            patch(f"{_ING_REPO}.find_or_create_sensor_metadata", return_value=42),
            patch(f"{_VAL_REPO}.insert_scalar_values", return_value=1),
        ):
            resp = client.post("/api/v1/ingest/sensor", json=payload)

        assert resp.status_code == 201
        mock_das.assert_called_once()
