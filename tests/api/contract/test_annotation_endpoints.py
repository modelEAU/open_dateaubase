"""Contract tests for the annotation API endpoints.

Tests assert that:
  - Every annotation endpoint exists and returns the expected HTTP status
  - Response schemas contain the required fields
  - Field types match expectations
  - Adding new optional fields does not break existing contract

No live database required — DB dependency is mocked via dependency_overrides.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.database import get_db
from api.main import app


# ---------------------------------------------------------------------------
# Fixtures (mirrors existing contract test pattern)
# ---------------------------------------------------------------------------

def _make_mock_conn():
    from unittest.mock import MagicMock
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor


@pytest.fixture
def mock_conn():
    conn, cursor = _make_mock_conn()

    def _override():
        yield conn

    app.dependency_overrides[get_db] = _override
    yield conn, cursor
    app.dependency_overrides.clear()


@pytest.fixture
def patched_client(mock_conn):
    with TestClient(app) as c:
        yield c, mock_conn[0], mock_conn[1]


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Shared mock data helpers
# ---------------------------------------------------------------------------

def _mock_annotation_type():
    return {
        "id": 1,
        "name": "Fault",
        "description": "Sensor or process fault",
        "color": "#FF4444",
    }


def _mock_annotation():
    return {
        "annotation_id": 1,
        "anchor": {"kind": "channel", "id": 42},
        "type": {"id": 1, "name": "Fault", "color": "#FF4444"},
        "start_time": "2025-02-15T10:00:00",
        "end_time": "2025-02-15T14:00:00",
        "title": "Sensor fouled",
        "comment": "Biofilm buildup.",
        "author": {"person_id": 5, "name": "Marie Dupont"},
        "campaign_id": None,
        "campaign_name": None,
        "event_id": None,
        "created_at": "2025-06-14T11:22:33",
        "modified_at": None,
    }


def _mock_annotation_list():
    return {
        # Top-level channel_id is the query echo (the queried channel), distinct
        # from the per-annotation anchor.
        "channel_id": 42,
        "query_range": {"from": "2025-02-01T00:00:00", "to": "2025-02-28T23:59:59"},
        "annotations": [_mock_annotation()],
        "count": 1,
    }


def _mock_annotation_types_response():
    return {"annotation_types": [_mock_annotation_type()]}


def _mock_recent_response():
    a = _mock_annotation()
    a["location"] = "Primary Effluent"
    a["variable"] = "TSS"
    return {"annotations": [a], "count": 1}


# ---------------------------------------------------------------------------
# GET /api/v1/annotation-kinds
# ---------------------------------------------------------------------------

REQUIRED_ANNOTATION_TYPE_FIELDS = {"id", "name"}


class TestAnnotationTypesContract:
    def test_list_types_returns_ok(self, patched_client):
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.annotation_service.get_annotation_kinds",
            return_value=_mock_annotation_types_response(),
        ):
            r = c.get("/api/v1/annotation-kinds")
        assert r.status_code == 200

    def test_list_types_has_annotation_types_key(self, patched_client):
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.annotation_service.get_annotation_kinds",
            return_value=_mock_annotation_types_response(),
        ):
            r = c.get("/api/v1/annotation-kinds")
        assert "annotation_types" in r.json()
        assert isinstance(r.json()["annotation_types"], list)

    def test_annotation_type_has_required_fields(self, patched_client):
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.annotation_service.get_annotation_kinds",
            return_value=_mock_annotation_types_response(),
        ):
            r = c.get("/api/v1/annotation-kinds")
        item = r.json()["annotation_types"][0]
        for field in REQUIRED_ANNOTATION_TYPE_FIELDS:
            assert field in item, f"Missing annotation type field: {field}"

    def test_annotation_type_id_is_int(self, patched_client):
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.annotation_service.get_annotation_kinds",
            return_value=_mock_annotation_types_response(),
        ):
            r = c.get("/api/v1/annotation-kinds")
        assert isinstance(r.json()["annotation_types"][0]["id"], int)


# ---------------------------------------------------------------------------
# GET /api/v1/timeseries/{id}/annotations
# ---------------------------------------------------------------------------

REQUIRED_ANNOTATION_LIST_FIELDS = {"annotations", "count"}
REQUIRED_ANNOTATION_FIELDS = {"annotation_id", "anchor", "type", "start_time", "created_at"}
REQUIRED_ANNOTATION_TYPE_IN_ANNOTATION = {"id", "name"}


class TestGetAnnotationsForTimeseries:
    def test_returns_ok(self, patched_client):
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.annotation_service.get_annotations_for_timeseries",
            return_value=_mock_annotation_list(),
        ):
            r = c.get("/api/v1/timeseries/42/annotations?from=2025-02-01T00:00:00&to=2025-02-28T23:59:59")
        assert r.status_code == 200

    def test_missing_from_param_returns_422(self, patched_client):
        c, conn, cursor = patched_client
        r = c.get("/api/v1/timeseries/42/annotations?to=2025-02-28T23:59:59")
        assert r.status_code == 422

    def test_missing_to_param_returns_422(self, patched_client):
        c, conn, cursor = patched_client
        r = c.get("/api/v1/timeseries/42/annotations?from=2025-02-01T00:00:00")
        assert r.status_code == 422

    def test_response_has_required_envelope_fields(self, patched_client):
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.annotation_service.get_annotations_for_timeseries",
            return_value=_mock_annotation_list(),
        ):
            r = c.get("/api/v1/timeseries/42/annotations?from=2025-02-01T00:00:00&to=2025-02-28T23:59:59")
        body = r.json()
        for field in REQUIRED_ANNOTATION_LIST_FIELDS:
            assert field in body, f"Missing field: {field}"

    def test_annotations_is_list(self, patched_client):
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.annotation_service.get_annotations_for_timeseries",
            return_value=_mock_annotation_list(),
        ):
            r = c.get("/api/v1/timeseries/42/annotations?from=2025-02-01T00:00:00&to=2025-02-28T23:59:59")
        assert isinstance(r.json()["annotations"], list)

    def test_annotation_item_has_required_fields(self, patched_client):
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.annotation_service.get_annotations_for_timeseries",
            return_value=_mock_annotation_list(),
        ):
            r = c.get("/api/v1/timeseries/42/annotations?from=2025-02-01T00:00:00&to=2025-02-28T23:59:59")
        item = r.json()["annotations"][0]
        for field in REQUIRED_ANNOTATION_FIELDS:
            assert field in item, f"Missing annotation field: {field}"

    def test_annotation_type_is_nested_object(self, patched_client):
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.annotation_service.get_annotations_for_timeseries",
            return_value=_mock_annotation_list(),
        ):
            r = c.get("/api/v1/timeseries/42/annotations?from=2025-02-01T00:00:00&to=2025-02-28T23:59:59")
        type_obj = r.json()["annotations"][0]["type"]
        assert isinstance(type_obj, dict)
        for field in REQUIRED_ANNOTATION_TYPE_IN_ANNOTATION:
            assert field in type_obj, f"Missing type field: {field}"

    def test_annotation_carries_discriminated_channel_anchor(self, patched_client):
        """Per-annotation anchor is a discriminated {kind, id} object, and the
        flat per-annotation `channel_id` field is gone (Slice 1 rename)."""
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.annotation_service.get_annotations_for_timeseries",
            return_value=_mock_annotation_list(),
        ):
            r = c.get("/api/v1/timeseries/42/annotations?from=2025-02-01T00:00:00&to=2025-02-28T23:59:59")
        ann = r.json()["annotations"][0]
        assert ann["anchor"] == {"kind": "channel", "id": 42}
        assert "channel_id" not in ann, "per-annotation channel_id must be replaced by anchor"

    def test_count_is_int(self, patched_client):
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.annotation_service.get_annotations_for_timeseries",
            return_value=_mock_annotation_list(),
        ):
            r = c.get("/api/v1/timeseries/42/annotations?from=2025-02-01T00:00:00&to=2025-02-28T23:59:59")
        assert isinstance(r.json()["count"], int)

    def test_channel_404_propagates(self, patched_client):
        c, conn, cursor = patched_client
        from fastapi import HTTPException

        with patch(
            "api.v1.services.annotation_service.get_annotations_for_timeseries",
            side_effect=HTTPException(status_code=404, detail="Channel 999 not found."),
        ):
            r = c.get("/api/v1/timeseries/999/annotations?from=2025-02-01T00:00:00&to=2025-02-28T23:59:59")
        assert r.status_code == 404
        assert "detail" in r.json()


# ---------------------------------------------------------------------------
# POST /api/v1/timeseries/{id}/annotations
# ---------------------------------------------------------------------------

REQUIRED_CREATE_RESPONSE_FIELDS = {"annotation_id", "anchor", "type", "start_time", "created_at"}


class TestCreateAnnotation:
    def _valid_payload(self):
        return {
            "annotation_type": "Fault",
            "start_time": "2025-02-15T10:00:00",
            "end_time": "2025-02-15T14:00:00",
            "title": "Sensor fouled",
            "comment": "Biofilm buildup.",
        }

    def test_returns_201(self, patched_client):
        c, conn, cursor = patched_client
        mock_response = {
            "annotation_id": 17,
            "anchor": {"kind": "channel", "id": 42},
            "type": {"id": 1, "name": "Fault", "color": "#FF4444"},
            "start_time": "2025-02-15T10:00:00",
            "end_time": "2025-02-15T14:00:00",
            "title": "Sensor fouled",
            "created_at": "2025-06-14T11:22:33",
        }
        with patch(
            "api.v1.services.annotation_service.create_annotation",
            return_value=mock_response,
        ):
            r = c.post("/api/v1/timeseries/42/annotations", json=self._valid_payload())
        assert r.status_code == 201

    def test_response_has_required_fields(self, patched_client):
        c, conn, cursor = patched_client
        mock_response = {
            "annotation_id": 17,
            "anchor": {"kind": "channel", "id": 42},
            "type": {"id": 1, "name": "Fault", "color": "#FF4444"},
            "start_time": "2025-02-15T10:00:00",
            "end_time": "2025-02-15T14:00:00",
            "title": "Sensor fouled",
            "created_at": "2025-06-14T11:22:33",
        }
        with patch(
            "api.v1.services.annotation_service.create_annotation",
            return_value=mock_response,
        ):
            r = c.post("/api/v1/timeseries/42/annotations", json=self._valid_payload())
        body = r.json()
        for field in REQUIRED_CREATE_RESPONSE_FIELDS:
            assert field in body, f"Missing field: {field}"

    def test_end_before_start_returns_422(self, patched_client):
        c, conn, cursor = patched_client
        payload = self._valid_payload()
        payload["end_time"] = "2025-02-14T00:00:00"  # before start_time
        r = c.post("/api/v1/timeseries/42/annotations", json=payload)
        assert r.status_code == 422

    def test_missing_annotation_type_returns_422(self, patched_client):
        c, conn, cursor = patched_client
        payload = {"start_time": "2025-02-15T10:00:00"}
        r = c.post("/api/v1/timeseries/42/annotations", json=payload)
        assert r.status_code == 422

    def test_missing_start_time_returns_422(self, patched_client):
        c, conn, cursor = patched_client
        payload = {"annotation_type": "Fault"}
        r = c.post("/api/v1/timeseries/42/annotations", json=payload)
        assert r.status_code == 422

    def test_annotation_type_as_int_accepted(self, patched_client):
        c, conn, cursor = patched_client
        mock_response = {
            "annotation_id": 18,
            "anchor": {"kind": "channel", "id": 42},
            "type": {"id": 1, "name": "Fault", "color": "#FF4444"},
            "start_time": "2025-02-15T10:00:00",
            "end_time": None,
            "title": None,
            "created_at": "2025-06-14T11:22:33",
        }
        payload = {"annotation_type": 1, "start_time": "2025-02-15T10:00:00"}
        with patch(
            "api.v1.services.annotation_service.create_annotation",
            return_value=mock_response,
        ):
            r = c.post("/api/v1/timeseries/42/annotations", json=payload)
        assert r.status_code == 201


# ---------------------------------------------------------------------------
# GET / POST /api/v1/analysis-series/{series_id}/annotations (lab arm, Slice 2)
# ---------------------------------------------------------------------------


def _mock_series_annotation():
    a = _mock_annotation()
    a["anchor"] = {"kind": "series", "id": 7}
    return a


def _mock_series_annotation_list():
    return {
        "analysis_series_id": 7,
        "query_range": {"from": "2026-01-01T00:00:00", "to": "2026-02-28T23:59:59"},
        "annotations": [_mock_series_annotation()],
        "count": 1,
    }


class TestGetAnnotationsForSeries:
    def test_returns_ok(self, patched_client):
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.annotation_service.get_annotations_for_series",
            return_value=_mock_series_annotation_list(),
        ):
            r = c.get("/api/v1/analysis-series/7/annotations?from=2026-01-01T00:00:00&to=2026-02-28T23:59:59")
        assert r.status_code == 200

    def test_annotation_carries_series_anchor(self, patched_client):
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.annotation_service.get_annotations_for_series",
            return_value=_mock_series_annotation_list(),
        ):
            r = c.get("/api/v1/analysis-series/7/annotations?from=2026-01-01T00:00:00&to=2026-02-28T23:59:59")
        ann = r.json()["annotations"][0]
        assert ann["anchor"] == {"kind": "series", "id": 7}
        assert "channel_id" not in ann

    def test_missing_from_param_returns_422(self, patched_client):
        c, conn, cursor = patched_client
        r = c.get("/api/v1/analysis-series/7/annotations?to=2026-02-28T23:59:59")
        assert r.status_code == 422

    def test_series_404_propagates(self, patched_client):
        c, conn, cursor = patched_client
        from fastapi import HTTPException

        with patch(
            "api.v1.services.annotation_service.get_annotations_for_series",
            side_effect=HTTPException(status_code=404, detail="AnalysisSeries 999 not found."),
        ):
            r = c.get("/api/v1/analysis-series/999/annotations?from=2026-01-01T00:00:00&to=2026-02-28T23:59:59")
        assert r.status_code == 404


class TestCreateAnnotationForSeries:
    def _valid_payload(self):
        return {
            "annotation_type": "Fault",
            "start_time": "2026-01-15T10:00:00",
            "end_time": "2026-01-15T14:00:00",
            "title": "Out-of-range lab result",
            "comment": "Re-run requested.",
        }

    def _mock_create_response(self):
        return {
            "annotation_id": 31,
            "anchor": {"kind": "series", "id": 7},
            "type": {"id": 1, "name": "Fault", "color": "#FF4444"},
            "start_time": "2026-01-15T10:00:00",
            "end_time": "2026-01-15T14:00:00",
            "title": "Out-of-range lab result",
            "created_at": "2026-06-10T11:22:33",
        }

    def test_returns_201(self, patched_client):
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.annotation_service.create_annotation_for_series",
            return_value=self._mock_create_response(),
        ):
            r = c.post("/api/v1/analysis-series/7/annotations", json=self._valid_payload())
        assert r.status_code == 201

    def test_response_carries_series_anchor(self, patched_client):
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.annotation_service.create_annotation_for_series",
            return_value=self._mock_create_response(),
        ):
            r = c.post("/api/v1/analysis-series/7/annotations", json=self._valid_payload())
        body = r.json()
        for field in REQUIRED_CREATE_RESPONSE_FIELDS:
            assert field in body, f"Missing field: {field}"
        assert body["anchor"] == {"kind": "series", "id": 7}

    def test_series_404_propagates(self, patched_client):
        c, conn, cursor = patched_client
        from fastapi import HTTPException

        with patch(
            "api.v1.services.annotation_service.create_annotation_for_series",
            side_effect=HTTPException(status_code=404, detail="AnalysisSeries 999 not found."),
        ):
            r = c.post("/api/v1/analysis-series/999/annotations", json=self._valid_payload())
        assert r.status_code == 404

    def test_end_before_start_returns_422(self, patched_client):
        c, conn, cursor = patched_client
        payload = self._valid_payload()
        payload["end_time"] = "2026-01-14T00:00:00"
        r = c.post("/api/v1/analysis-series/7/annotations", json=payload)
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# Point-pin integrity guard (Slice 3) — exercises the REAL service guard
# (only the repository layer is patched, so _assert_pin_in_anchor actually runs).
# ---------------------------------------------------------------------------

_KIND_ROW = {"annotation_kind_id": 1, "annotation_type_name": "Fault", "color": "#FF4444"}


class TestPinIntegrityGuardEndpoint:
    """Both arms: a cross-stream pin → 422; a matching pin → 201 with Observation_ID."""

    def _pin_payload(self, observation_id: int):
        return {
            "annotation_type": "Fault",
            "start_time": "2026-01-15T10:00:00",
            "observation_id": observation_id,
        }

    # --- sensor arm (backfilled guard) ------------------------------------
    def test_sensor_pin_wrong_channel_returns_422(self, patched_client):
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.annotation_service.channel_repository.get_channel_by_id",
            return_value={"channel_id": 42},
        ), patch(
            "api.v1.repositories.annotation_repository.get_annotation_kind_by_name",
            return_value=_KIND_ROW,
        ), patch(
            # Observation 70 belongs to channel 99 (stream_id=99), not the anchored channel 42.
            "api.v1.repositories.annotation_repository.get_observation_anchor",
            return_value=99,
        ), patch(
            "api.v1.repositories.annotation_repository.create_annotation",
        ) as mock_create:
            r = c.post("/api/v1/timeseries/42/annotations", json=self._pin_payload(70))
        assert r.status_code == 422
        mock_create.assert_not_called()  # guard ran before the INSERT

    def test_sensor_pin_matching_channel_returns_201(self, patched_client):
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.annotation_service.channel_repository.get_channel_by_id",
            return_value={"channel_id": 42},
        ), patch(
            "api.v1.repositories.annotation_repository.get_annotation_kind_by_name",
            return_value=_KIND_ROW,
        ), patch(
            "api.v1.repositories.annotation_repository.get_observation_anchor",
            return_value=42,
        ), patch(
            "api.v1.repositories.annotation_repository.create_annotation",
            return_value={"annotation_id": 17, "created_datetime": "2026-06-10T11:22:33"},
        ):
            r = c.post("/api/v1/timeseries/42/annotations", json=self._pin_payload(70))
        assert r.status_code == 201
        assert r.json()["observation_id"] == 70

    # --- lab arm ----------------------------------------------------------
    def test_lab_pin_wrong_series_returns_422(self, patched_client):
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.annotation_service.ingestion_repository.get_analysis_series_by_id",
            return_value={"analysis_series_id": 7},
        ), patch(
            "api.v1.repositories.annotation_repository.get_annotation_kind_by_name",
            return_value=_KIND_ROW,
        ), patch(
            # Observation 50 belongs to series 8 (stream_id=8), not the anchored series 7.
            "api.v1.repositories.annotation_repository.get_observation_anchor",
            return_value=8,
        ), patch(
            "api.v1.repositories.annotation_repository.create_annotation",
        ) as mock_create:
            r = c.post("/api/v1/analysis-series/7/annotations", json=self._pin_payload(50))
        assert r.status_code == 422
        mock_create.assert_not_called()

    def test_lab_pin_matching_series_returns_201(self, patched_client):
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.annotation_service.ingestion_repository.get_analysis_series_by_id",
            return_value={"analysis_series_id": 7},
        ), patch(
            "api.v1.repositories.annotation_repository.get_annotation_kind_by_name",
            return_value=_KIND_ROW,
        ), patch(
            "api.v1.repositories.annotation_repository.get_observation_anchor",
            return_value=7,
        ), patch(
            "api.v1.repositories.annotation_repository.create_annotation",
            return_value={"annotation_id": 31, "created_datetime": "2026-06-10T11:22:33"},
        ):
            r = c.post("/api/v1/analysis-series/7/annotations", json=self._pin_payload(50))
        assert r.status_code == 201
        assert r.json()["observation_id"] == 50

    def test_lab_pin_replicate2_of_correct_series_returns_201(self, patched_client):
        """Exact-replicate case: replicate-2's Observation still resolves to series 7."""
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.annotation_service.ingestion_repository.get_analysis_series_by_id",
            return_value={"analysis_series_id": 7},
        ), patch(
            "api.v1.repositories.annotation_repository.get_annotation_kind_by_name",
            return_value=_KIND_ROW,
        ), patch(
            "api.v1.repositories.annotation_repository.get_observation_anchor",
            return_value=7,
        ), patch(
            "api.v1.repositories.annotation_repository.create_annotation",
            return_value={"annotation_id": 32, "created_datetime": "2026-06-10T11:22:33"},
        ):
            r = c.post("/api/v1/analysis-series/7/annotations", json=self._pin_payload(61))
        assert r.status_code == 201
        assert r.json()["observation_id"] == 61


# ---------------------------------------------------------------------------
# PUT /api/v1/annotations/{annotation_id}
# ---------------------------------------------------------------------------

class TestUpdateAnnotation:
    def test_returns_200(self, patched_client):
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.annotation_service.update_annotation",
            return_value=_mock_annotation(),
        ):
            r = c.put("/api/v1/annotations/1", json={"title": "Updated title"})
        assert r.status_code == 200

    def test_response_has_required_fields(self, patched_client):
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.annotation_service.update_annotation",
            return_value=_mock_annotation(),
        ):
            r = c.put("/api/v1/annotations/1", json={"title": "Updated title"})
        body = r.json()
        for field in REQUIRED_ANNOTATION_FIELDS:
            assert field in body, f"Missing field: {field}"

    def test_not_found_returns_404(self, patched_client):
        c, conn, cursor = patched_client
        from fastapi import HTTPException

        with patch(
            "api.v1.services.annotation_service.update_annotation",
            side_effect=HTTPException(status_code=404, detail="Annotation 999 not found."),
        ):
            r = c.put("/api/v1/annotations/999", json={"title": "X"})
        assert r.status_code == 404

    def test_empty_body_accepted(self, patched_client):
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.annotation_service.update_annotation",
            return_value=_mock_annotation(),
        ):
            r = c.put("/api/v1/annotations/1", json={})
        assert r.status_code == 200

    def test_update_preserves_series_anchor(self, patched_client):
        """Slice 4: editing a series-anchored annotation keeps anchor.kind=='series'
        (not silently coerced to channel). The endpoint is keyed by annotation_id,
        so a lab row round-trips through PUT unchanged."""
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.annotation_service.update_annotation",
            return_value=_mock_series_annotation(),
        ):
            r = c.put("/api/v1/annotations/31", json={"comment": "Re-checked"})
        assert r.status_code == 200
        assert r.json()["anchor"] == {"kind": "series", "id": 7}
        assert "channel_id" not in r.json()


# ---------------------------------------------------------------------------
# DELETE /api/v1/annotations/{annotation_id}
# ---------------------------------------------------------------------------

class TestDeleteAnnotation:
    def test_returns_204(self, patched_client):
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.annotation_service.delete_annotation",
            return_value=None,
        ):
            r = c.delete("/api/v1/annotations/1")
        assert r.status_code == 204

    def test_no_body_on_204(self, patched_client):
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.annotation_service.delete_annotation",
            return_value=None,
        ):
            r = c.delete("/api/v1/annotations/1")
        assert r.content == b""

    def test_not_found_returns_404(self, patched_client):
        c, conn, cursor = patched_client
        from fastapi import HTTPException

        with patch(
            "api.v1.services.annotation_service.delete_annotation",
            side_effect=HTTPException(status_code=404, detail="Annotation 999 not found."),
        ):
            r = c.delete("/api/v1/annotations/999")
        assert r.status_code == 404

    def test_delete_series_anchored_returns_204(self, patched_client):
        """Slice 4: DELETE works on a series-anchored annotation (keyed by id)."""
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.annotation_service.delete_annotation",
            return_value=None,
        ):
            r = c.delete("/api/v1/annotations/31")
        assert r.status_code == 204
        assert r.content == b""


# ---------------------------------------------------------------------------
# GET /api/v1/annotations/recent
# ---------------------------------------------------------------------------

class TestRecentAnnotations:
    def test_returns_ok(self, patched_client):
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.annotation_service.get_recent_annotations",
            return_value=_mock_recent_response(),
        ):
            r = c.get("/api/v1/annotations/recent")
        assert r.status_code == 200

    def test_has_annotations_and_count(self, patched_client):
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.annotation_service.get_recent_annotations",
            return_value=_mock_recent_response(),
        ):
            r = c.get("/api/v1/annotations/recent")
        body = r.json()
        assert "annotations" in body
        assert "count" in body
        assert isinstance(body["annotations"], list)
        assert isinstance(body["count"], int)

    def test_limit_param_accepted(self, patched_client):
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.annotation_service.get_recent_annotations",
            return_value={"annotations": [], "count": 0},
        ):
            r = c.get("/api/v1/annotations/recent?limit=5")
        assert r.status_code == 200

    def test_limit_above_max_returns_422(self, patched_client):
        c, conn, cursor = patched_client
        r = c.get("/api/v1/annotations/recent?limit=200")
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/annotations/by-type/{type_name}
# ---------------------------------------------------------------------------

class TestAnnotationsByType:
    def test_returns_ok(self, patched_client):
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.annotation_service.get_annotations_by_kind",
            return_value=_mock_recent_response(),
        ):
            r = c.get("/api/v1/annotations/by-type/Fault?from=2025-01-01T00:00:00&to=2025-12-31T23:59:59")
        assert r.status_code == 200

    def test_missing_from_returns_422(self, patched_client):
        c, conn, cursor = patched_client
        r = c.get("/api/v1/annotations/by-type/Fault?to=2025-12-31T23:59:59")
        assert r.status_code == 422

    def test_missing_to_returns_422(self, patched_client):
        c, conn, cursor = patched_client
        r = c.get("/api/v1/annotations/by-type/Fault?from=2025-01-01T00:00:00")
        assert r.status_code == 422

    def test_response_has_annotations_and_count(self, patched_client):
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.annotation_service.get_annotations_by_kind",
            return_value=_mock_recent_response(),
        ):
            r = c.get("/api/v1/annotations/by-type/Fault?from=2025-01-01T00:00:00&to=2025-12-31T23:59:59")
        body = r.json()
        assert "annotations" in body
        assert "count" in body

    def test_not_found_type_returns_404(self, patched_client):
        c, conn, cursor = patched_client
        from fastapi import HTTPException

        with patch(
            "api.v1.services.annotation_service.get_annotations_by_kind",
            side_effect=HTTPException(status_code=404, detail="AnnotationType 'DoesNotExist' not found."),
        ):
            r = c.get("/api/v1/annotations/by-type/DoesNotExist?from=2025-01-01T00:00:00&to=2025-12-31T23:59:59")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# Cross-stream feeds include lab annotations (Slice 5) — exercises the REAL
# service + repository against a mocked cursor, so the UNION SQL and the
# location/variable enrichment for the lab half are actually run. A pre-Slice-5
# Channel-only inner join would never surface the series-anchored row.
# ---------------------------------------------------------------------------

FROM = "2026-01-01T00:00:00"
TO = "2026-02-28T23:59:59"


def _feed_row(annotation_id, *, stream_id, stream_kind_id=1,
              location=None, parameter=None, created="2026-01-15T10:00:00"):
    """A 20-column feed row matching the repo's UNION SELECT shape.

    Column layout must match _row_to_annotation + _feed_row in annotation_repository:
    0=annotation_id, 1=stream_id, 2=annotation_kind_id, 3=name, 4=color,
    5=start_time, 6=end_time, 7=title, 8=comment, 9=author_person_id,
    10=author_name, 11=campaign_id, 12=campaign_name, 13=event_id,
    14=created_datetime, 15=modified_datetime, 16=stream_kind_id,
    17=observation_id, 18=location_name, 19=parameter_name.
    stream_kind_id=1 → sensor/channel, stream_kind_id=2 → lab/series.
    """
    return (
        annotation_id, stream_id, 3, "Fault", "#FF0000",
        "2026-01-10T00:00:00", "2026-01-20T00:00:00", "title", "comment",
        None, None, None, None, None, created, None,
        stream_kind_id, None, location, parameter,
    )


class TestRecentIncludesLabAnnotations:
    def test_lab_annotation_appears_alongside_sensor(self, patched_client):
        c, conn, cursor = patched_client
        # Cursor returns one sensor + one lab row (lab is more recent).
        cursor.fetchall.return_value = [
            _feed_row(2, stream_id=7, stream_kind_id=2, location="Effluent", parameter="COD",
                      created="2026-01-16T00:00:00"),
            _feed_row(1, stream_id=42, stream_kind_id=1, parameter="TSS",
                      created="2026-01-15T00:00:00"),
        ]
        r = c.get("/api/v1/annotations/recent")
        assert r.status_code == 200
        anns = r.json()["annotations"]
        anchors = [(a["anchor"]["kind"], a["anchor"]["id"]) for a in anns]
        assert ("series", 7) in anchors  # lab row surfaced
        assert ("channel", 42) in anchors  # sensor row still there
        lab = next(a for a in anns if a["anchor"] == {"kind": "series", "id": 7})
        assert lab["location"] == "Effluent"
        assert lab["variable"] == "COD"


class TestByTypeIncludesLabAnnotations:
    def test_lab_annotation_appears_with_location_and_variable(self, patched_client):
        c, conn, cursor = patched_client
        cursor.fetchall.return_value = [
            _feed_row(1, stream_id=42, stream_kind_id=1, parameter="TSS"),
            _feed_row(2, stream_id=7, stream_kind_id=2, location="Effluent", parameter="COD"),
        ]
        with patch(
            "api.v1.repositories.annotation_repository.get_annotation_kind_by_name",
            return_value={"annotation_kind_id": 3, "annotation_type_name": "Fault",
                          "color": "#FF0000"},
        ):
            r = c.get(f"/api/v1/annotations/by-type/Fault?from={FROM}&to={TO}")
        assert r.status_code == 200
        anns = r.json()["annotations"]
        lab = next(a for a in anns if a["anchor"] == {"kind": "series", "id": 7})
        assert lab["anchor"]["kind"] == "series"
        assert lab["location"] == "Effluent"
        assert lab["variable"] == "COD"


# ---------------------------------------------------------------------------
# OpenAPI spec — annotation paths are documented
# ---------------------------------------------------------------------------

class TestAnnotationOpenAPISpec:
    REQUIRED_ANNOTATION_PATHS = [
        "/api/v1/annotation-kinds",
        "/api/v1/timeseries/{channel_id}/annotations",
        "/api/v1/analysis-series/{series_id}/annotations",
        "/api/v1/annotations/recent",
        "/api/v1/annotations/by-type/{type_name}",
        "/api/v1/annotations/{annotation_id}",
    ]

    def test_annotation_paths_in_spec(self, client):
        r = client.get("/openapi.json")
        assert r.status_code == 200
        spec_paths = set(r.json()["paths"].keys())
        for path in self.REQUIRED_ANNOTATION_PATHS:
            assert path in spec_paths, f"Annotation path not in OpenAPI spec: {path}"

    def test_timeseries_annotations_accepts_get_and_post(self, client):
        r = client.get("/openapi.json")
        path = r.json()["paths"].get("/api/v1/timeseries/{channel_id}/annotations", {})
        assert "get" in path, "GET not documented for timeseries annotations"
        assert "post" in path, "POST not documented for timeseries annotations"

    def test_annotation_resource_accepts_put_and_delete(self, client):
        r = client.get("/openapi.json")
        path = r.json()["paths"].get("/api/v1/annotations/{annotation_id}", {})
        assert "put" in path, "PUT not documented for annotation resource"
        assert "delete" in path, "DELETE not documented for annotation resource"


# ---------------------------------------------------------------------------
# Backwards-compatibility: timeseries contract uses channel_id
# ---------------------------------------------------------------------------

REQUIRED_TIMESERIES_FIELDS = {
    "channel_id", "location", "site", "parameter", "unit",
    "data_shape", "provenance", "traits", "campaign",
    "from_timestamp", "to_timestamp", "row_count", "data",
}


class TestTimeseriesContractUnchanged:
    """Ensure annotation additions don't break the existing timeseries contract."""

    def _mock_timeseries(self):
        return {
            "channel_id": 1,
            "location": None,
            "site": None,
            "parameter": "TSS",
            "unit": "mg/L",
            "data_shape": "Scalar",
            "provenance": "Sensor",
            "traits": [],
            "campaign": None,
            "from_timestamp": "2025-01-01T00:00:00",
            "to_timestamp": "2025-01-31T00:00:00",
            "row_count": 1,
            "data": [{"timestamp": "2025-01-01T00:00:00", "value": 24.5, "quality_code": 1}],
        }

    def test_timeseries_endpoint_still_has_required_fields(self, patched_client):
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.timeseries_service.get_timeseries",
            return_value=self._mock_timeseries(),
        ):
            r = c.get("/api/v1/timeseries/1")
        assert r.status_code == 200
        body = r.json()
        for field in REQUIRED_TIMESERIES_FIELDS:
            assert field in body, f"Timeseries field broken: {field}"
