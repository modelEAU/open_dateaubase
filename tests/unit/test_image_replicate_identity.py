"""Images are addressed by Observation_ID, not by (stream, timestamp).

Lab replicates of one sample all carry the sample-collection time (ADR 0002), so
a timestamp-keyed read collapses every replicate onto whichever row the DB
returned first: two uploaded pictures, one picture shown twice. These tests pin
the observation-keyed contract end of that fix.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

from api.v1.repositories import value_repository as vr

TS = datetime(2026, 7, 14, 16, 0, tzinfo=timezone.utc)


def _conn(rows: list, one=None):
    conn, cursor = MagicMock(), MagicMock()
    cursor.fetchall.return_value = rows
    cursor.fetchone.return_value = one
    conn.cursor.return_value = cursor
    return conn, cursor


class TestImageListing:
    def test_rows_carry_observation_id(self):
        """Both replicates come back, each addressable on its own."""
        rows = [
            (501, TS, 640, 480, 3, "PNG", 1000, "FileSystem", "lab_images/7/1.png", 1),
            (502, TS, 640, 480, 3, "PNG", 2000, "FileSystem", "lab_images/7/2.png", 1),
        ]
        conn, cursor = _conn(rows)
        out = vr.get_analysis_series_image_values(conn, 22, None, None)

        assert "o.[Observation_ID]" in cursor.execute.call_args_list[0].args[0]
        assert [r["observation_id"] for r in out] == [501, 502]
        assert [r["storage_path"] for r in out] == ["lab_images/7/1.png", "lab_images/7/2.png"]


class TestImageFetch:
    def test_thumbnail_keyed_on_observation(self):
        conn, cursor = _conn([], one=(b"thumb-of-502",))
        assert vr.get_image_thumbnail(conn, 502) == b"thumb-of-502"

        sql, *params = cursor.execute.call_args.args
        assert "vi.[Observation_ID] = ?" in sql
        assert "[Timestamp]" not in sql  # a ts filter is what fused the replicates
        assert params == [502]

    def test_metadata_keyed_on_observation(self):
        conn, cursor = _conn([], one=("lab_images/7/2.png", "PNG"))
        meta = vr.get_image_metadata(conn, 502)

        assert meta == {"storage_path": "lab_images/7/2.png", "image_format": "PNG"}
        sql, *params = cursor.execute.call_args.args
        assert "vi.[Observation_ID] = ?" in sql
        assert params == [502]

    def test_missing_image_returns_none(self):
        conn, _ = _conn([], one=None)
        assert vr.get_image_thumbnail(conn, 999) is None
        assert vr.get_image_metadata(conn, 999) is None
