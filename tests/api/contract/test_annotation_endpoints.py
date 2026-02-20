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
        "metadata_id": 42,
        "type": {"id": 1, "name": "Fault", "color": "#FF4444"},
        "start_time": "2025-02-15T10:00:00",
        "end_time": "2025-02-15T14:00:00",
        "title": "Sensor fouled",
        "comment": "Biofilm buildup.",
        "author": {"person_id": 5, "name": "Marie Dupont"},
        "campaign_id": None,
        "campaign_name": None,
        "equipment_event_id": None,
        "created_at": "2025-06-14T11:22:33",
        "modified_at": None,
    }


def _mock_annotation_list():
    return {
        "metadata_id": 42,
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
# GET /api/v1/annotation-types
# ---------------------------------------------------------------------------

REQUIRED_ANNOTATION_TYPE_FIELDS = {"id", "name"}


class TestAnnotationTypesContract:
    def test_list_types_returns_ok(self, patched_client):
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.annotation_service.get_annotation_types",
            return_value=_mock_annotation_types_response(),
        ):
            r = c.get("/api/v1/annotation-types")
        assert r.status_code == 200

    def test_list_types_has_annotation_types_key(self, patched_client):
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.annotation_service.get_annotation_types",
            return_value=_mock_annotation_types_response(),
        ):
            r = c.get("/api/v1/annotation-types")
        assert "annotation_types" in r.json()
        assert isinstance(r.json()["annotation_types"], list)

    def test_annotation_type_has_required_fields(self, patched_client):
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.annotation_service.get_annotation_types",
            return_value=_mock_annotation_types_response(),
        ):
            r = c.get("/api/v1/annotation-types")
        item = r.json()["annotation_types"][0]
        for field in REQUIRED_ANNOTATION_TYPE_FIELDS:
            assert field in item, f"Missing annotation type field: {field}"

    def test_annotation_type_id_is_int(self, patched_client):
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.annotation_service.get_annotation_types",
            return_value=_mock_annotation_types_response(),
        ):
            r = c.get("/api/v1/annotation-types")
        assert isinstance(r.json()["annotation_types"][0]["id"], int)


# ---------------------------------------------------------------------------
# GET /api/v1/timeseries/{id}/annotations
# ---------------------------------------------------------------------------

REQUIRED_ANNOTATION_LIST_FIELDS = {"annotations", "count"}
REQUIRED_ANNOTATION_FIELDS = {"annotation_id", "metadata_id", "type", "start_time", "created_at"}
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

    def test_count_is_int(self, patched_client):
        c, conn, cursor = patched_client
        with patch(
            "api.v1.services.annotation_service.get_annotations_for_timeseries",
            return_value=_mock_annotation_list(),
        ):
            r = c.get("/api/v1/timeseries/42/annotations?from=2025-02-01T00:00:00&to=2025-02-28T23:59:59")
        assert isinstance(r.json()["count"], int)

    def test_metadata_404_propagates(self, patched_client):
        c, conn, cursor = patched_client
        from fastapi import HTTPException

        with patch(
            "api.v1.services.annotation_service.get_annotations_for_timeseries",
            side_effect=HTTPException(status_code=404, detail="MetaData 999 not found."),
        ):
            r = c.get("/api/v1/timeseries/999/annotations?from=2025-02-01T00:00:00&to=2025-02-28T23:59:59")
        assert r.status_code == 404
        assert "detail" in r.json()


# ---------------------------------------------------------------------------
# POST /api/v1/timeseries/{id}/annotations
# ---------------------------------------------------------------------------

REQUIRED_CREATE_RESPONSE_FIELDS = {"annotation_id", "metadata_id", "type", "start_time", "created_at"}


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
            "metadata_id": 42,
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
            "metadata_id": 42,
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
            "metadata_id": 42,
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
            "api.v1.services.annotation_service.get_annotations_by_type",
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
            "api.v1.services.annotation_service.get_annotations_by_type",
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
            "api.v1.services.annotation_service.get_annotations_by_type",
            side_effect=HTTPException(status_code=404, detail="AnnotationType 'DoesNotExist' not found."),
        ):
            r = c.get("/api/v1/annotations/by-type/DoesNotExist?from=2025-01-01T00:00:00&to=2025-12-31T23:59:59")
        assert r.status_code == 404


# ---------------------------------------------------------------------------
# OpenAPI spec — annotation paths are documented
# ---------------------------------------------------------------------------

class TestAnnotationOpenAPISpec:
    REQUIRED_ANNOTATION_PATHS = [
        "/api/v1/annotation-types",
        "/api/v1/timeseries/{metadata_id}/annotations",
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
        path = r.json()["paths"].get("/api/v1/timeseries/{metadata_id}/annotations", {})
        assert "get" in path, "GET not documented for timeseries annotations"
        assert "post" in path, "POST not documented for timeseries annotations"

    def test_annotation_resource_accepts_put_and_delete(self, client):
        r = client.get("/openapi.json")
        path = r.json()["paths"].get("/api/v1/annotations/{annotation_id}", {})
        assert "put" in path, "PUT not documented for annotation resource"
        assert "delete" in path, "DELETE not documented for annotation resource"


# ---------------------------------------------------------------------------
# Backwards-compatibility: existing timeseries contract is unbroken
# ---------------------------------------------------------------------------

REQUIRED_TIMESERIES_FIELDS = {
    "metadata_id", "location", "site", "parameter", "unit",
    "data_shape", "provenance", "processing_degree", "campaign",
    "from_timestamp", "to_timestamp", "row_count", "data",
}


class TestTimeseriesContractUnchanged:
    """Ensure annotation additions don't break the existing timeseries contract."""

    def _mock_timeseries(self):
        return {
            "metadata_id": 1,
            "location": "Primary Effluent",
            "site": "WRRF",
            "parameter": "TSS",
            "unit": "mg/L",
            "data_shape": "Scalar",
            "provenance": "Sensor",
            "processing_degree": "Raw",
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
