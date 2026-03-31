"""Unit tests for DateaubaseClient using respx to mock httpx."""

from datetime import datetime, timezone

import pytest
import respx
from httpx import Response

from table_import.api_client import ApiError, DateaubaseClient

BASE = "http://testserver"

VALUES = [{"timestamp": "2024-01-01T00:00:00+00:00", "value": 7.5}]


@pytest.fixture
def client():
    c = DateaubaseClient(BASE)
    yield c
    c.close()


# ---------------------------------------------------------------------------
# resolve_channel (tagged)
# ---------------------------------------------------------------------------


@respx.mock
def test_resolve_channel_returns_channel_id_and_warnings(client):
    respx.post(f"{BASE}/api/v1/ingest/resolve-channel").mock(
        return_value=Response(200, json={"channel_id": 42, "warnings": []})
    )
    channel_id, warnings = client.resolve_channel(
        das_name="DAS-1",
        tag="TIT-101",
        parameter_name="temperature",
        unit_name="degC",
    )
    assert channel_id == 42
    assert warnings == []


@respx.mock
def test_resolve_channel_returns_warnings(client):
    respx.post(f"{BASE}/api/v1/ingest/resolve-channel").mock(
        return_value=Response(200, json={"channel_id": 5, "warnings": ["DAS auto-created"]})
    )
    channel_id, warnings = client.resolve_channel(
        das_name="NewDAS",
        tag="TAG-1",
        parameter_name="temperature",
        unit_name="degC",
    )
    assert channel_id == 5
    assert len(warnings) == 1
    assert "DAS auto-created" in warnings[0]


# ---------------------------------------------------------------------------
# resolve_channel_tagless
# ---------------------------------------------------------------------------


@respx.mock
def test_resolve_channel_tagless_returns_channel_id(client):
    respx.post(f"{BASE}/api/v1/ingest/resolve-channel-tagless").mock(
        return_value=Response(200, json={"channel_id": 99, "warnings": []})
    )
    channel_id, warnings = client.resolve_channel_tagless(
        das_name="DirectStation",
        equipment_name="Probe_A",
        parameter_name="dissolved oxygen",
        unit_name="mg/L",
    )
    assert channel_id == 99
    assert warnings == []


# ---------------------------------------------------------------------------
# get_last_timestamp
# ---------------------------------------------------------------------------


@respx.mock
def test_get_last_timestamp_returns_datetime(client):
    respx.get(f"{BASE}/api/v1/ingest/last-timestamp").mock(
        return_value=Response(200, json={"last_timestamp": "2024-06-01T10:30:00"})
    )
    ts = client.get_last_timestamp(channel_id=42)
    assert ts is not None
    assert ts.tzinfo == timezone.utc
    assert ts == datetime(2024, 6, 1, 10, 30, 0, tzinfo=timezone.utc)


@respx.mock
def test_get_last_timestamp_returns_none(client):
    respx.get(f"{BASE}/api/v1/ingest/last-timestamp").mock(
        return_value=Response(200, json={"last_timestamp": None})
    )
    ts = client.get_last_timestamp(channel_id=42)
    assert ts is None


# ---------------------------------------------------------------------------
# ingest_sensor_values (tagged)
# ---------------------------------------------------------------------------


@respx.mock
def test_ingest_sensor_values_tagged(client):
    respx.post(f"{BASE}/api/v1/ingest/sensor").mock(
        return_value=Response(201, json={"channel_id": 42, "rows_written": 1, "warnings": []})
    )
    result = client.ingest_sensor_values(
        das_name="DAS-1",
        tag="TIT-101",
        parameter_name="temperature",
        unit_name="degC",
        values=VALUES,
    )
    assert result["channel_id"] == 42
    assert result["rows_written"] == 1


# ---------------------------------------------------------------------------
# ingest_sensor_values_tagless
# ---------------------------------------------------------------------------


@respx.mock
def test_ingest_sensor_values_tagless(client):
    respx.post(f"{BASE}/api/v1/ingest/sensor-tagless").mock(
        return_value=Response(201, json={"channel_id": 7, "rows_written": 1, "warnings": []})
    )
    result = client.ingest_sensor_values_tagless(
        das_name="DirectStation",
        equipment_name="Probe_A",
        parameter_name="dissolved oxygen",
        unit_name="mg/L",
        values=VALUES,
    )
    assert result["channel_id"] == 7
    assert result["rows_written"] == 1


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


@respx.mock
def test_api_error_raised_on_500(client):
    respx.post(f"{BASE}/api/v1/ingest/resolve-channel").mock(
        return_value=Response(500, text="Internal Server Error")
    )
    with pytest.raises(ApiError) as exc_info:
        client.resolve_channel(
            das_name="DAS-1",
            tag="TIT-101",
            parameter_name="temperature",
            unit_name="degC",
        )
    assert exc_info.value.status_code == 500


@respx.mock
def test_api_error_raised_on_422(client):
    respx.post(f"{BASE}/api/v1/ingest/resolve-channel").mock(
        return_value=Response(422, json={"detail": "Unknown parameter_name 'xyzzy'"})
    )
    with pytest.raises(ApiError) as exc_info:
        client.resolve_channel(
            das_name="DAS-1",
            tag="TIT-101",
            parameter_name="xyzzy",
            unit_name="degC",
        )
    assert exc_info.value.status_code == 422
