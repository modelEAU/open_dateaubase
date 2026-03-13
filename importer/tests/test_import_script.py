"""Unit tests for import_script helper functions."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pandas as pd
import pytest

from table_import.import_script import (
    build_api_payload,
    ingest_via_api,
    unix_seconds_to_iso,
)
from table_import.tables import ValueTable


# ---------------------------------------------------------------------------
# unix_seconds_to_iso
# ---------------------------------------------------------------------------


def test_unix_seconds_to_iso_known_value():
    # 2024-01-15 10:30:00 UTC
    unix_ts = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc).timestamp()
    iso = unix_seconds_to_iso(unix_ts)
    assert "2024-01-15" in iso
    assert "10:30:00" in iso
    assert "+00:00" in iso or "Z" in iso.upper()


def test_unix_seconds_to_iso_epoch():
    iso = unix_seconds_to_iso(0.0)
    assert "1970-01-01" in iso


# ---------------------------------------------------------------------------
# build_api_payload
# ---------------------------------------------------------------------------


def _make_df(timestamps: list[float], values: list[float]) -> ValueTable:
    """Create a minimal ValueTable with Timestamp and Value columns."""
    df = pd.DataFrame({
        "Timestamp": timestamps,
        "Value": values,
        "Value_ID": [0] * len(timestamps),
        "Number_of_experiment": [1] * len(timestamps),
        "Metadata_ID": [0] * len(timestamps),
        "Comment_ID": [None] * len(timestamps),
    })
    return ValueTable(df)


def test_build_api_payload_filters_by_watermark():
    df = _make_df([100.0, 200.0, 300.0], [1.0, 2.0, 3.0])
    payload = build_api_payload(df, last_unix_ts=150.0, min_unix_ts=None, conversion_factor=1.0)
    assert len(payload) == 2
    assert payload[0]["value"] == 2.0
    assert payload[1]["value"] == 3.0


def test_build_api_payload_filters_by_min_timestamp():
    df = _make_df([100.0, 200.0, 300.0], [1.0, 2.0, 3.0])
    # min_unix_ts removes the first row, watermark removes nothing additional
    payload = build_api_payload(df, last_unix_ts=0.0, min_unix_ts=150.0, conversion_factor=1.0)
    assert len(payload) == 2
    assert payload[0]["value"] == 2.0


def test_build_api_payload_applies_conversion_factor():
    df = _make_df([100.0, 200.0], [1.0, 2.0])
    payload = build_api_payload(df, last_unix_ts=0.0, min_unix_ts=None, conversion_factor=0.001)
    assert abs(payload[0]["value"] - 0.001) < 1e-9
    assert abs(payload[1]["value"] - 0.002) < 1e-9


def test_build_api_payload_empty_when_all_filtered():
    df = _make_df([100.0, 200.0], [1.0, 2.0])
    payload = build_api_payload(df, last_unix_ts=500.0, min_unix_ts=None, conversion_factor=1.0)
    assert payload == []


def test_build_api_payload_timestamp_is_iso_string():
    df = _make_df([0.0], [5.0])
    payload = build_api_payload(df, last_unix_ts=-1.0, min_unix_ts=None, conversion_factor=1.0)
    assert isinstance(payload[0]["timestamp"], str)
    # Should be parseable as ISO datetime
    datetime.fromisoformat(payload[0]["timestamp"])


# ---------------------------------------------------------------------------
# ingest_via_api
# ---------------------------------------------------------------------------


def test_ingest_via_api_dry_run_does_not_call_client():
    client = MagicMock()
    payload = [{"timestamp": "2024-01-01T00:00:00+00:00", "value": 1.0}]
    ingest_via_api(
        client,
        equipment_id=1,
        parameter_id=10,
        unit_id=5,
        data_provenance_id=1,
        processing_degree_id=1,
        payload=payload,
        label="test/var",
        dry_run=True,
    )
    client.ingest_sensor_values.assert_not_called()


def test_ingest_via_api_calls_client_with_correct_args():
    client = MagicMock()
    client.ingest_sensor_values.return_value = {"channel_id": 7, "rows_written": 1}
    payload = [{"timestamp": "2024-01-01T00:00:00+00:00", "value": 1.0}]
    ingest_via_api(
        client,
        equipment_id=1,
        parameter_id=10,
        unit_id=5,
        data_provenance_id=1,
        processing_degree_id=1,
        payload=payload,
        label="test/var",
        dry_run=False,
    )
    client.ingest_sensor_values.assert_called_once_with(
        equipment_id=1,
        parameter_id=10,
        unit_id=5,
        data_provenance_id=1,
        processing_degree_id=1,
        values=payload,
    )
