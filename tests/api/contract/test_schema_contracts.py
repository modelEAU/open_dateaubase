"""Contract tests for the open_datEAUbase API v1.

These tests assert that:
  - Every endpoint exists and returns the expected HTTP status on valid inputs
  - Response schemas contain the required fields (keys present)
  - Field types match expectations

Contract tests should FAIL if:
  - A required field is removed from a response
  - A field type changes
  - An endpoint is removed or its path changes

Contract tests should PASS if:
  - A new optional field is added
  - A new endpoint is added

The tests use FastAPI's dependency_overrides to mock the DB so they run
without a live database. DB integration tests live in tests/integration/.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from api.database import get_db
from api.main import app


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_mock_conn():
    conn = MagicMock()
    cursor = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor


@pytest.fixture
def mock_conn():
    """Override get_db with a MagicMock connection for the duration of a test."""
    conn, cursor = _make_mock_conn()

    def _override():
        yield conn

    app.dependency_overrides[get_db] = _override
    yield conn, cursor
    app.dependency_overrides.clear()


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def patched_client(mock_conn):
    """TestClient with the DB dependency already mocked."""
    with TestClient(app) as c:
        yield c, mock_conn[0], mock_conn[1]


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------

class TestRoot:
    def test_root_ok(self, client):
        r = client.get("/")
        assert r.status_code == 200

    def test_root_required_fields(self, client):
        body = client.get("/").json()
        for field in ("message", "docs", "health", "schema_version"):
            assert field in body

    def test_root_field_types(self, client):
        body = client.get("/").json()
        assert isinstance(body["message"], str)
        assert isinstance(body["schema_version"], str)


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class TestHealth:
    def test_health_endpoint_exists(self, patched_client):
        c, conn, cursor = patched_client
        cursor.fetchone.return_value = ("2.0.0",)
        r = c.get("/api/v1/health")
        assert r.status_code in (200, 503)

    def test_health_schema_has_status_field(self, patched_client):
        c, conn, cursor = patched_client
        cursor.fetchone.return_value = ("2.0.0",)
        r = c.get("/api/v1/health")
        assert "status" in r.json()

    def test_health_schema_has_api_version(self, patched_client):
        c, conn, cursor = patched_client
        cursor.fetchone.return_value = ("2.0.0",)
        r = c.get("/api/v1/health")
        assert "api_version" in r.json()
        assert isinstance(r.json()["api_version"], str)


# ---------------------------------------------------------------------------
# Sites
# ---------------------------------------------------------------------------

REQUIRED_SITE_FIELDS = {"id", "name", "description", "type", "lat_wgs84", "long_wgs84", "city", "province", "country"}


class TestSitesContract:
    def _mock_site(self):
        return {"id": 1, "name": "WRRF", "description": "Main plant", "type": None, "lat_wgs84": None, "long_wgs84": None, "city": None, "province": None, "country": None}

    def test_list_sites_returns_list(self, patched_client):
        c, conn, cursor = patched_client
        with patch("api.v1.repositories.site_repository.get_all_sites", return_value=[self._mock_site()]):
            r = c.get("/api/v1/sites")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_site_object_has_required_fields(self, patched_client):
        c, conn, cursor = patched_client
        with patch("api.v1.repositories.site_repository.get_all_sites", return_value=[self._mock_site()]):
            r = c.get("/api/v1/sites")
        if r.status_code == 200 and r.json():
            item = r.json()[0]
            for field in REQUIRED_SITE_FIELDS:
                assert field in item, f"Missing site field: {field}"

    def test_site_404_has_detail(self, patched_client):
        c, conn, cursor = patched_client
        with patch("api.v1.repositories.site_repository.get_site_by_id", return_value=None):
            r = c.get("/api/v1/sites/999999")
        assert r.status_code == 404
        assert "detail" in r.json()

    def test_sampling_locations_returns_list(self, patched_client):
        c, conn, cursor = patched_client
        mock_loc = {"id": 1, "name": "Primary Effluent", "description": None, "latitude": None, "longitude": None, "site_id": 1, "site_name": "WRRF"}
        with patch("api.v1.repositories.site_repository.get_site_by_id", return_value=self._mock_site()), \
             patch("api.v1.repositories.site_repository.get_sampling_locations_for_site", return_value=[mock_loc]):
            r = c.get("/api/v1/sites/1/sampling-locations")
        assert r.status_code == 200
        assert isinstance(r.json(), list)


# ---------------------------------------------------------------------------
# Channels
# ---------------------------------------------------------------------------

REQUIRED_CHANNEL_FIELDS = {
    "channel_id", "parameter_id", "parameter_name",
    "equipment_id", "equipment_identifier",
    "data_provenance_id", "data_provenance",
    "processing_degree_id", "processing_degree_name",
    "value_type_id", "value_type_name",
}

REQUIRED_PAGINATED_FIELDS = {"items", "total", "page", "page_size", "has_next"}


def _mock_channel():
    return {f: None for f in REQUIRED_CHANNEL_FIELDS} | {"channel_id": 1, "processing_degree_id": 1, "processing_degree_name": "Raw"}


class TestChannelsContract:
    def test_list_channels_returns_paginated_envelope(self, patched_client):
        c, conn, cursor = patched_client
        with patch("api.v1.repositories.channel_repository.list_channels", return_value=([_mock_channel()], 1)):
            r = c.get("/api/v1/channels")
        assert r.status_code == 200
        body = r.json()
        for field in REQUIRED_PAGINATED_FIELDS:
            assert field in body, f"Missing paginated field: {field}"

    def test_paginated_envelope_types(self, patched_client):
        c, conn, cursor = patched_client
        with patch("api.v1.repositories.channel_repository.list_channels", return_value=([_mock_channel()], 1)):
            r = c.get("/api/v1/channels")
        body = r.json()
        assert isinstance(body["items"], list)
        assert isinstance(body["total"], int)
        assert isinstance(body["page"], int)
        assert isinstance(body["page_size"], int)
        assert isinstance(body["has_next"], bool)

    def test_channel_item_has_all_required_fields(self, patched_client):
        c, conn, cursor = patched_client
        with patch("api.v1.repositories.channel_repository.list_channels", return_value=([_mock_channel()], 1)):
            r = c.get("/api/v1/channels")
        item = r.json()["items"][0]
        for field in REQUIRED_CHANNEL_FIELDS:
            assert field in item, f"Missing channel field: {field}"

    def test_channel_by_id_404_has_detail(self, patched_client):
        c, conn, cursor = patched_client
        with patch("api.v1.repositories.channel_repository.get_channel_by_id", return_value=None):
            r = c.get("/api/v1/channels/999999")
        assert r.status_code == 404
        assert "detail" in r.json()

    def test_pagination_query_params_accepted(self, patched_client):
        c, conn, cursor = patched_client
        with patch("api.v1.repositories.channel_repository.list_channels", return_value=([], 0)):
            r = c.get("/api/v1/channels?page=2&page_size=10&processing_degree_id=1")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Timeseries
# ---------------------------------------------------------------------------

REQUIRED_TIMESERIES_FIELDS = {
    "channel_id", "location", "site", "parameter", "unit",
    "data_shape", "provenance", "processing_degree", "campaign",
    "from_timestamp", "to_timestamp", "row_count", "data",
}


def _mock_timeseries():
    return {
        "channel_id": 1,
        "location": None,
        "site": None,
        "parameter": "TSS",
        "unit": "mg/L",
        "data_shape": "Scalar",
        "provenance": "Sensor",
        "processing_degree": "Raw",
        "campaign": None,
        "from_timestamp": "2025-01-01T00:00:00",
        "to_timestamp": "2025-01-31T00:00:00",
        "row_count": 2,
        "data": [
            {"timestamp": "2025-01-01T00:00:00", "value": 24.5, "quality_code": 1},
        ],
    }


class TestTimeseriesContract:
    def test_timeseries_returns_ok(self, patched_client):
        c, conn, cursor = patched_client
        with patch("api.v1.services.timeseries_service.get_timeseries", return_value=_mock_timeseries()):
            r = c.get("/api/v1/timeseries/1")
        assert r.status_code == 200

    def test_timeseries_has_required_fields(self, patched_client):
        c, conn, cursor = patched_client
        with patch("api.v1.services.timeseries_service.get_timeseries", return_value=_mock_timeseries()):
            r = c.get("/api/v1/timeseries/1")
        body = r.json()
        for field in REQUIRED_TIMESERIES_FIELDS:
            assert field in body, f"Missing timeseries field: {field}"

    def test_timeseries_data_is_list(self, patched_client):
        c, conn, cursor = patched_client
        with patch("api.v1.services.timeseries_service.get_timeseries", return_value=_mock_timeseries()):
            r = c.get("/api/v1/timeseries/1")
        assert isinstance(r.json()["data"], list)

    def test_timeseries_row_count_is_int(self, patched_client):
        c, conn, cursor = patched_client
        with patch("api.v1.services.timeseries_service.get_timeseries", return_value=_mock_timeseries()):
            r = c.get("/api/v1/timeseries/1")
        assert isinstance(r.json()["row_count"], int)

    def test_by_context_returns_list(self, patched_client):
        c, conn, cursor = patched_client
        with patch("api.v1.services.timeseries_service.get_timeseries_by_context", return_value=[]):
            r = c.get("/api/v1/timeseries/by-context/search?equipment_id=1&parameter_id=1")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_full_context_endpoint_exists(self, patched_client):
        c, conn, cursor = patched_client
        with patch("api.v1.services.timeseries_service.get_full_context", return_value={}):
            r = c.get("/api/v1/timeseries/1/full-context")
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# Campaigns
# ---------------------------------------------------------------------------

REQUIRED_CAMPAIGN_FIELDS = {
    "campaign_id", "campaign_type_id", "campaign_type_name",
    "site_id", "site_name", "name", "description",
    "start_date", "end_date",
}


def _mock_campaign():
    return {f: None for f in REQUIRED_CAMPAIGN_FIELDS} | {
        "campaign_id": 1, "campaign_type_id": 1, "site_id": 1, "name": "Ops 2025",
    }


class TestCampaignsContract:
    def test_list_campaigns_returns_list(self, patched_client):
        c, conn, cursor = patched_client
        with patch("api.v1.repositories.campaign_repository.list_campaigns", return_value=[_mock_campaign()]):
            r = c.get("/api/v1/campaigns")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_campaign_has_required_fields(self, patched_client):
        c, conn, cursor = patched_client
        with patch("api.v1.repositories.campaign_repository.list_campaigns", return_value=[_mock_campaign()]):
            r = c.get("/api/v1/campaigns")
        item = r.json()[0]
        for field in REQUIRED_CAMPAIGN_FIELDS:
            assert field in item, f"Missing campaign field: {field}"

    def test_campaign_by_id_404(self, patched_client):
        c, conn, cursor = patched_client
        with patch("api.v1.repositories.campaign_repository.get_campaign_by_id", return_value=None):
            r = c.get("/api/v1/campaigns/999999")
        assert r.status_code == 404

    def test_campaign_context_has_required_fields(self, patched_client):
        c, conn, cursor = patched_client
        context = {
            "sampling_locations": [],
            "equipment": [],
            "parameters": [],
            "metadata_count": 0,
            "time_range_start": None,
            "time_range_end": None,
        }
        with patch("api.v1.repositories.campaign_repository.get_campaign_by_id", return_value=_mock_campaign()), \
             patch("api.v1.repositories.campaign_repository.get_campaign_context", return_value=context):
            r = c.get("/api/v1/campaigns/1/context")
        assert r.status_code == 200
        body = r.json()
        for field in ("campaign", "sampling_locations", "equipment", "parameters", "metadata_count"):
            assert field in body, f"Missing context field: {field}"


# ---------------------------------------------------------------------------
# Equipment
# ---------------------------------------------------------------------------

REQUIRED_EQUIPMENT_FIELDS = {
    "equipment_id", "identifier", "serial_number",
    "model_id", "model_name", "manufacturer", "owner", "purchase_date",
}


def _mock_equipment():
    return {f: None for f in REQUIRED_EQUIPMENT_FIELDS} | {"equipment_id": 1}


class TestEquipmentContract:
    def test_list_equipment_returns_list(self, patched_client):
        c, conn, cursor = patched_client
        with patch("api.v1.repositories.equipment_repository.list_equipment", return_value=[_mock_equipment()]):
            r = c.get("/api/v1/equipment")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_equipment_has_required_fields(self, patched_client):
        c, conn, cursor = patched_client
        with patch("api.v1.repositories.equipment_repository.list_equipment", return_value=[_mock_equipment()]):
            r = c.get("/api/v1/equipment")
        item = r.json()[0]
        for field in REQUIRED_EQUIPMENT_FIELDS:
            assert field in item, f"Missing equipment field: {field}"

    def test_equipment_404_has_detail(self, patched_client):
        c, conn, cursor = patched_client
        with patch("api.v1.repositories.equipment_repository.get_equipment_by_id", return_value=None):
            r = c.get("/api/v1/equipment/999999")
        assert r.status_code == 404
        assert "detail" in r.json()

    def test_lifecycle_has_required_fields(self, patched_client):
        c, conn, cursor = patched_client
        with patch("api.v1.repositories.equipment_repository.get_equipment_by_id", return_value=_mock_equipment()), \
             patch("api.v1.repositories.equipment_repository.get_equipment_installations", return_value=[]), \
             patch("api.v1.repositories.equipment_repository.get_equipment_events", return_value=[]):
            r = c.get("/api/v1/equipment/1/lifecycle")
        assert r.status_code == 200
        body = r.json()
        for field in ("equipment", "installations", "events"):
            assert field in body, f"Missing lifecycle field: {field}"

    def test_lifecycle_collections_are_lists(self, patched_client):
        c, conn, cursor = patched_client
        with patch("api.v1.repositories.equipment_repository.get_equipment_by_id", return_value=_mock_equipment()), \
             patch("api.v1.repositories.equipment_repository.get_equipment_installations", return_value=[]), \
             patch("api.v1.repositories.equipment_repository.get_equipment_events", return_value=[]):
            r = c.get("/api/v1/equipment/1/lifecycle")
        body = r.json()
        assert isinstance(body["installations"], list)
        assert isinstance(body["events"], list)


# ---------------------------------------------------------------------------
# Lineage
# ---------------------------------------------------------------------------

class TestLineageContract:
    def test_forward_lineage_returns_list(self, patched_client):
        c, conn, cursor = patched_client
        with patch("api.v1.services.lineage_service.forward_lineage", return_value=[]):
            r = c.get("/api/v1/lineage/1/forward")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_backward_lineage_returns_list(self, patched_client):
        c, conn, cursor = patched_client
        with patch("api.v1.services.lineage_service.backward_lineage", return_value=[]):
            r = c.get("/api/v1/lineage/1/backward")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_lineage_tree_has_required_fields(self, patched_client):
        c, conn, cursor = patched_client
        mock_tree = {"channel_id": 1, "parents": [], "children": []}
        with patch("api.v1.services.lineage_service.full_lineage_tree", return_value=mock_tree):
            r = c.get("/api/v1/lineage/1/tree")
        assert r.status_code == 200
        body = r.json()
        for field in ("channel_id", "parents", "children"):
            assert field in body, f"Missing tree field: {field}"

    def test_lineage_tree_channel_id_is_int(self, patched_client):
        c, conn, cursor = patched_client
        mock_tree = {"channel_id": 1, "parents": [], "children": []}
        with patch("api.v1.services.lineage_service.full_lineage_tree", return_value=mock_tree):
            r = c.get("/api/v1/lineage/1/tree")
        assert isinstance(r.json()["channel_id"], int)


# ---------------------------------------------------------------------------
# Ingestion — request validation (422 checks)
# ---------------------------------------------------------------------------

class TestIngestionRequestValidation:
    """These test Pydantic validation before any business logic runs."""

    def test_sensor_ingest_rejects_empty_values(self, patched_client):
        c, conn, cursor = patched_client
        payload = {
            "das_name": "TestDAS", "tag": "TIT-1", "parameter_name": "temperature",
            "unit_name": "degC", "values": [],
        }
        r = c.post("/api/v1/ingest/sensor", json=payload)
        assert r.status_code == 422

    def test_sensor_ingest_requires_das_name(self, patched_client):
        c, conn, cursor = patched_client
        payload = {
            "tag": "TIT-1",
            "parameter_name": "temperature",
            "unit_name": "degC",
            "values": [{"timestamp": "2025-01-01T00:00:00", "value": 24.5}],
        }
        r = c.post("/api/v1/ingest/sensor", json=payload)
        assert r.status_code == 422

    def test_lab_ingest_rejects_empty_values(self, patched_client):
        c, conn, cursor = patched_client
        payload = {"values": []}
        r = c.post("/api/v1/ingest/lab", json=payload)
        assert r.status_code == 422

    def test_processed_ingest_rejects_empty_sources(self, patched_client):
        c, conn, cursor = patched_client
        payload = {
            "source_channel_ids": [],
            "processing": {"method_name": "outlier_removal", "processing_type": "Cleaning"},
            "output": {
                "processing_degree_id": 2,
                "values": [{"timestamp": "2025-01-01T00:00:00", "value": 24.5}],
            },
        }
        r = c.post("/api/v1/ingest/processed", json=payload)
        assert r.status_code == 422

    def test_ingest_response_schema_has_required_fields(self):
        """Pydantic model test — no HTTP call needed."""
        from api.v1.schemas.ingestion import IngestResponse

        resp = IngestResponse(channel_id=1, rows_written=5)
        data = resp.model_dump()
        assert "channel_id" in data
        assert "rows_written" in data
        assert "processing_step_id" in data
        assert isinstance(data["channel_id"], int)
        assert isinstance(data["rows_written"], int)


# ---------------------------------------------------------------------------
# OpenAPI spec completeness
# ---------------------------------------------------------------------------

class TestOpenAPISpec:
    REQUIRED_PATHS = [
        "/api/v1/health",
        "/api/v1/sites",
        "/api/v1/sites/{site_id}",
        "/api/v1/sites/{site_id}/sampling-locations",
        "/api/v1/channels",
        "/api/v1/channels/{channel_id}",
        "/api/v1/timeseries/{channel_id}",
        "/api/v1/timeseries/{channel_id}/full-context",
        "/api/v1/timeseries/by-context/search",
        "/api/v1/campaigns",
        "/api/v1/campaigns/{campaign_id}",
        "/api/v1/campaigns/{campaign_id}/context",
        "/api/v1/equipment",
        "/api/v1/equipment/{equipment_id}",
        "/api/v1/equipment/{equipment_id}/lifecycle",
        "/api/v1/lineage/{channel_id}/forward",
        "/api/v1/lineage/{channel_id}/backward",
        "/api/v1/lineage/{channel_id}/tree",
        "/api/v1/lineage/by-equipment/degrees",
        "/api/v1/ingest/sensor",
        "/api/v1/ingest/lab",
        "/api/v1/ingest/processed",
    ]

    def test_all_required_paths_documented(self, client):
        r = client.get("/openapi.json")
        assert r.status_code == 200
        spec_paths = set(r.json()["paths"].keys())
        for path in self.REQUIRED_PATHS:
            assert path in spec_paths, f"Path not in OpenAPI spec: {path}"

    def test_openapi_has_info_section(self, client):
        r = client.get("/openapi.json")
        spec = r.json()
        assert "info" in spec
        assert "title" in spec["info"]
        assert "version" in spec["info"]

    def test_all_ingest_endpoints_accept_post(self, client):
        r = client.get("/openapi.json")
        paths = r.json()["paths"]
        for path in ("/api/v1/ingest/sensor", "/api/v1/ingest/lab", "/api/v1/ingest/processed"):
            assert "post" in paths[path], f"{path} must accept POST"

    def test_read_endpoints_accept_get(self, client):
        r = client.get("/openapi.json")
        paths = r.json()["paths"]
        for path in ("/api/v1/sites", "/api/v1/channels", "/api/v1/campaigns", "/api/v1/equipment"):
            assert "get" in paths[path], f"{path} must accept GET"


# ---------------------------------------------------------------------------
# Last-timestamp endpoint
# ---------------------------------------------------------------------------


class TestLastTimestampEndpoint:
    def test_returns_null_when_no_data(self, patched_client):
        client, conn, cursor = patched_client
        cursor.fetchone.return_value = None
        r = client.get(
            "/api/v1/ingest/last-timestamp",
            params={"channel_id": 1},
        )
        assert r.status_code == 200
        assert r.json()["last_timestamp"] is None

    def test_returns_iso_string_when_data_exists(self, patched_client):
        from datetime import datetime
        client, conn, cursor = patched_client
        cursor.fetchone.return_value = (datetime(2024, 6, 1, 12, 0, 0),)
        r = client.get(
            "/api/v1/ingest/last-timestamp",
            params={"channel_id": 1},
        )
        assert r.status_code == 200
        assert r.json()["last_timestamp"] is not None
        assert "2024-06-01" in r.json()["last_timestamp"]

    def test_missing_required_params_returns_422(self, patched_client):
        client, conn, cursor = patched_client
        r = client.get("/api/v1/ingest/last-timestamp")
        assert r.status_code == 422

    def test_in_openapi_spec(self, client):
        r = client.get("/openapi.json")
        paths = r.json()["paths"]
        assert "/api/v1/ingest/last-timestamp" in paths
        assert "get" in paths["/api/v1/ingest/last-timestamp"]


# ---------------------------------------------------------------------------
# Observation-aware ingest contract tests
# ---------------------------------------------------------------------------


class TestObservationAwareIngest:
    """Contract tests verifying ingest endpoints work after Observation refactor.

    These tests mock the repository layer to confirm:
    1. insert_scalar_values is called (via the endpoint's internal flow)
    2. The endpoint returns expected response shape
    3. No KeyError or AttributeError from stale column references
    """

    def test_post_ingest_sensor_scalar_contract(self, client):
        """POST /ingest/sensor returns {"rows_written": N, "channel_id": N} with valid input."""
        from unittest.mock import patch

        _REPO = "api.v1.endpoints.ingest.signal_port_repository"
        with (
            patch(f"{_REPO}.find_signal_port_type_by_name", return_value=1),
            patch(f"{_REPO}.find_parameter_by_name", return_value=1),
            patch(f"{_REPO}.find_unit_by_name", return_value=1),
            patch(f"{_REPO}.find_or_create_das", return_value=(5, False)),
            patch(f"{_REPO}.find_or_create_signal_port", return_value=(10, False)),
            patch("api.v1.endpoints.ingest.ingestion_repository.find_or_create_sensor_metadata",
                  return_value=42),
            patch("api.v1.endpoints.ingest.value_repository.insert_scalar_values",
                  return_value=2),
        ):
            resp = client.post("/api/v1/ingest/sensor", json={
                "das_name": "PlantSCADA",
                "tag": "TIT-101",
                "signal_port_type": "value",
                "parameter_name": "temperature",
                "unit_name": "degC",
                "data_provenance_id": 1,
                "processing_degree_id": 1,
                "values": [
                    {"timestamp": "2024-01-01T10:00:00", "value": 7.2},
                    {"timestamp": "2024-01-01T10:05:00", "value": 7.3},
                ],
            })
        assert resp.status_code in (200, 201)
        body = resp.json()
        assert "rows_written" in body
        assert body["rows_written"] == 2

    def test_get_last_timestamp_contract(self, client):
        """GET /ingest/last-timestamp returns {"last_timestamp": ...} or null."""
        from datetime import datetime
        from unittest.mock import patch

        with patch("api.v1.endpoints.ingest.ingestion_repository.get_last_timestamp_for_channel",
                   return_value=datetime(2024, 1, 1, 10, 5, 0)):
            resp = client.get("/api/v1/ingest/last-timestamp", params={"channel_id": 1})
        assert resp.status_code == 200
        body = resp.json()
        assert "last_timestamp" in body
