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


# ---------------------------------------------------------------------------
# signal_interface_name passthrough
# ---------------------------------------------------------------------------


@respx.mock
def test_resolve_channel_passes_signal_interface_name(client):
    route = respx.post(f"{BASE}/api/v1/ingest/resolve-channel").mock(
        return_value=Response(200, json={"channel_id": 1, "warnings": []})
    )
    client.resolve_channel(
        das_name="DAS-1",
        tag="TIT-101",
        parameter_name="temperature",
        unit_name="degC",
        signal_interface_name="my_plc",
    )
    assert route.called
    sent = route.calls[0].request
    import json
    body = json.loads(sent.content)
    assert body["signal_interface_name"] == "my_plc"


@respx.mock
def test_resolve_channel_omits_signal_interface_name_when_none(client):
    route = respx.post(f"{BASE}/api/v1/ingest/resolve-channel").mock(
        return_value=Response(200, json={"channel_id": 1, "warnings": []})
    )
    client.resolve_channel(
        das_name="DAS-1",
        tag="TIT-101",
        parameter_name="temperature",
        unit_name="degC",
    )
    import json
    body = json.loads(route.calls[0].request.content)
    assert "signal_interface_name" not in body


# ---------------------------------------------------------------------------
# create_signal_interface
# ---------------------------------------------------------------------------


@respx.mock
def test_create_signal_interface_returns_id(client):
    respx.post(f"{BASE}/api/v1/signal-interfaces/provision").mock(
        return_value=Response(201, json={"signal_interface_id": 10, "name": "plc_1"})
    )
    si_id = client.create_signal_interface(
        das_name="plant_das",
        name="plc_1",
        type_name="PLC",
    )
    assert si_id == 10


@respx.mock
def test_create_signal_interface_passes_optional_fields(client):
    route = respx.post(f"{BASE}/api/v1/signal-interfaces/provision").mock(
        return_value=Response(201, json={"signal_interface_id": 11, "name": "plc_2"})
    )
    client.create_signal_interface(
        das_name="plant_das",
        name="plc_2",
        type_name="PLC",
        make="Siemens",
        model="S7-1200",
        description="Main PLC",
    )
    import json
    body = json.loads(route.calls[0].request.content)
    assert body["make"] == "Siemens"
    assert body["model"] == "S7-1200"
    assert body["description"] == "Main PLC"


# ---------------------------------------------------------------------------
# create_signal_interface_port
# ---------------------------------------------------------------------------


@respx.mock
def test_create_signal_interface_port_returns_id(client):
    respx.post(f"{BASE}/api/v1/signal-interface-ports/provision").mock(
        return_value=Response(
            201,
            json={
                "signal_interface_port_id": 20,
                "port_identifier": "AIN1",
                "signal_interface_id": 10,
            },
        )
    )
    port_id = client.create_signal_interface_port(
        signal_interface_id=10,
        port_identifier="AIN1",
        kind_name="analog_input",
    )
    assert port_id == 20


# ---------------------------------------------------------------------------
# create_channel
# ---------------------------------------------------------------------------


@respx.mock
def test_create_channel_returns_id(client):
    respx.post(f"{BASE}/api/v1/channels/provision").mock(
        return_value=Response(201, json={"channel_id": 30, "tag_name": "TIT-101"})
    )
    ch_id = client.create_channel(
        signal_interface_id=10,
        tag_name="TIT-101",
    )
    assert ch_id == 30


@respx.mock
def test_create_channel_passes_optional_fields(client):
    route = respx.post(f"{BASE}/api/v1/channels/provision").mock(
        return_value=Response(201, json={"channel_id": 31, "tag_name": "TIT-102"})
    )
    client.create_channel(
        signal_interface_id=10,
        tag_name="TIT-102",
        parameter_name="temperature",
        unit_name="degC",
        channel_kind="value",
        data_provenance_id=2,
    )
    import json
    body = json.loads(route.calls[0].request.content)
    assert body["parameter_name"] == "temperature"
    assert body["unit_name"] == "degC"
    assert body["data_provenance_id"] == 2


# ---------------------------------------------------------------------------
# open_channel_port_history
# ---------------------------------------------------------------------------


@respx.mock
def test_open_channel_port_history_returns_id(client):
    respx.post(f"{BASE}/api/v1/channels/5/port-history").mock(
        return_value=Response(
            201,
            json={
                "channel_port_history_id": 99,
                "channel_id": 5,
                "signal_interface_port_id": 20,
                "valid_from": "2024-01-01T00:00:00",
                "gating_note": None,
            },
        )
    )
    cph_id = client.open_channel_port_history(
        channel_id=5,
        port_id=20,
        valid_from="2024-01-01T00:00:00",
    )
    assert cph_id == 99
