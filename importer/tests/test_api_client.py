"""Unit tests for DateaubaseClient using respx to mock httpx."""

from datetime import datetime, timezone

import pytest
import respx
from httpx import Response

from table_import.api_client import ApiError, DateaubaseClient

BASE = "http://testserver"

EQUIPMENT_LIST = [
    {"equipment_id": 1, "identifier": "Rodtox-A"},
    {"equipment_id": 2, "identifier": "Basestation-1"},
]

PARAMETER_LIST = [
    {"parameter_id": 10, "parameter_name": "Dissolved oxygen"},
    {"parameter_id": 11, "parameter_name": "Turbidity"},
]

UNIT_LIST = [
    {"unit_id": 5, "unit": "mg/L"},
    {"unit_id": 6, "unit": "NTU"},
]


@pytest.fixture
def client():
    c = DateaubaseClient(BASE)
    yield c
    c.close()


# ---------------------------------------------------------------------------
# Equipment resolution
# ---------------------------------------------------------------------------


@respx.mock
def test_resolve_equipment_id_found(client):
    respx.get(f"{BASE}/api/v1/channels/lookup/equipment").mock(
        return_value=Response(200, json=EQUIPMENT_LIST)
    )
    assert client.resolve_equipment_id("Rodtox-A") == 1


@respx.mock
def test_resolve_equipment_id_not_found(client):
    respx.get(f"{BASE}/api/v1/channels/lookup/equipment").mock(
        return_value=Response(200, json=EQUIPMENT_LIST)
    )
    with pytest.raises(ValueError, match="Rodtox-X"):
        client.resolve_equipment_id("Rodtox-X")


@respx.mock
def test_resolve_equipment_id_cached(client):
    route = respx.get(f"{BASE}/api/v1/channels/lookup/equipment").mock(
        return_value=Response(200, json=EQUIPMENT_LIST)
    )
    client.resolve_equipment_id("Rodtox-A")
    client.resolve_equipment_id("Basestation-1")
    assert route.call_count == 1  # fetched only once


# ---------------------------------------------------------------------------
# Parameter resolution
# ---------------------------------------------------------------------------


@respx.mock
def test_resolve_parameter_id_found(client):
    respx.get(f"{BASE}/api/v1/channels/lookup/parameters").mock(
        return_value=Response(200, json=PARAMETER_LIST)
    )
    assert client.resolve_parameter_id("Dissolved oxygen") == 10


@respx.mock
def test_resolve_parameter_id_not_found(client):
    respx.get(f"{BASE}/api/v1/channels/lookup/parameters").mock(
        return_value=Response(200, json=PARAMETER_LIST)
    )
    with pytest.raises(ValueError, match="pH"):
        client.resolve_parameter_id("pH")


# ---------------------------------------------------------------------------
# Unit resolution
# ---------------------------------------------------------------------------


@respx.mock
def test_resolve_unit_id_found(client):
    respx.get(f"{BASE}/api/v1/ingest/lookup/units").mock(
        return_value=Response(200, json=UNIT_LIST)
    )
    assert client.resolve_unit_id("mg/L") == 5


@respx.mock
def test_resolve_unit_id_not_found(client):
    respx.get(f"{BASE}/api/v1/ingest/lookup/units").mock(
        return_value=Response(200, json=UNIT_LIST)
    )
    with pytest.raises(ValueError, match="g/L"):
        client.resolve_unit_id("g/L")


# ---------------------------------------------------------------------------
# Last timestamp
# ---------------------------------------------------------------------------


@respx.mock
def test_get_last_timestamp_returns_datetime(client):
    respx.get(f"{BASE}/api/v1/ingest/last-timestamp").mock(
        return_value=Response(200, json={"last_timestamp": "2024-06-01T10:30:00"})
    )
    ts = client.get_last_timestamp(
        equipment_id=1, parameter_id=10, data_provenance_id=1, processing_degree_id=1
    )
    assert ts is not None
    assert ts.tzinfo == timezone.utc
    assert ts == datetime(2024, 6, 1, 10, 30, 0, tzinfo=timezone.utc)


@respx.mock
def test_get_last_timestamp_returns_none(client):
    respx.get(f"{BASE}/api/v1/ingest/last-timestamp").mock(
        return_value=Response(200, json={"last_timestamp": None})
    )
    ts = client.get_last_timestamp(
        equipment_id=1, parameter_id=10, data_provenance_id=1, processing_degree_id=1
    )
    assert ts is None


# ---------------------------------------------------------------------------
# Sensor ingest
# ---------------------------------------------------------------------------


@respx.mock
def test_ingest_sensor_values(client):
    respx.post(f"{BASE}/api/v1/ingest/sensor").mock(
        return_value=Response(201, json={"channel_id": 42, "rows_written": 3})
    )
    values = [
        {"timestamp": "2024-01-01T00:00:00+00:00", "value": 7.5},
        {"timestamp": "2024-01-01T00:01:00+00:00", "value": 7.6},
        {"timestamp": "2024-01-01T00:02:00+00:00", "value": 7.7},
    ]
    result = client.ingest_sensor_values(
        equipment_id=1,
        parameter_id=10,
        unit_id=5,
        data_provenance_id=1,
        processing_degree_id=1,
        values=values,
    )
    assert result["channel_id"] == 42
    assert result["rows_written"] == 3


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


@respx.mock
def test_api_error_raised_on_500(client):
    respx.get(f"{BASE}/api/v1/channels/lookup/equipment").mock(
        return_value=Response(500, text="Internal Server Error")
    )
    with pytest.raises(ApiError) as exc_info:
        client.resolve_equipment_id("anything")
    assert exc_info.value.status_code == 500
