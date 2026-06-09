"""Unit tests for the lab AnalysisSeries read path in
api.v1.repositories.value_repository.

No database — pyodbc connection/cursor are MagicMocks. We assert that lab reads
(a) join through LabAnalysis and filter on AnalysisSeries_ID, (b) reuse the same
payload joins / return shape as the sensor reads, and (c) the sensor reads are
unchanged (still key on Channel_ID, no LabAnalysis join).
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

from api.v1.repositories import value_repository as vr


def _conn_returning(rows: list):
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchall.return_value = rows
    conn.cursor.return_value = cursor
    return conn, cursor


def _sql(cursor) -> str:
    return "\n".join(c.args[0] for c in cursor.execute.call_args_list)


FROM = datetime(2026, 1, 1, tzinfo=timezone.utc)
TO = datetime(2026, 2, 1, tzinfo=timezone.utc)


class TestScalarLabRead:
    def test_joins_labanalysis_and_filters_on_series(self):
        conn, cursor = _conn_returning([(FROM, 12.5, 1)])
        out = vr.get_analysis_series_scalar_values(conn, 7, FROM, TO)

        sql = _sql(cursor)
        assert "[dbo].[LabAnalysis]" in sql
        assert "la.[AnalysisSeries_ID] = ?" in sql
        assert "o.[Channel_ID]" not in sql
        # AnalysisSeries_ID is the first bound param
        assert cursor.execute.call_args_list[0].args[1] == 7
        # Same return shape as the sensor scalar read
        assert out == [{"timestamp": FROM, "value": 12.5, "quality_code": 1}]

    def test_replicates_returned_as_individual_rows(self):
        # Two replicates at the same collection time → two points
        rows = [(FROM, 10.0, 1), (FROM, 10.4, 1)]
        conn, cursor = _conn_returning(rows)
        out = vr.get_analysis_series_scalar_values(conn, 7, None, None)
        assert len(out) == 2
        assert {r["value"] for r in out} == {10.0, 10.4}


class TestSensorReadUnchanged:
    def test_scalar_still_keys_on_channel_id_only(self):
        conn, cursor = _conn_returning([])
        vr.get_scalar_values(conn, 99, None, None)
        sql = _sql(cursor)
        assert "o.[Channel_ID] = ?" in sql
        assert "[dbo].[LabAnalysis]" not in sql
        assert cursor.execute.call_args_list[0].args[1] == 99


class TestVectorMatrixImageLabRead:
    def test_vector_joins_labanalysis(self):
        conn, cursor = _conn_returning([])
        vr.get_analysis_series_vector_values(conn, 3, None, None)
        sql = _sql(cursor)
        assert "[dbo].[ValueVector]" in sql
        assert "la.[AnalysisSeries_ID] = ?" in sql

    def test_matrix_joins_labanalysis(self):
        conn, cursor = _conn_returning([])
        vr.get_analysis_series_matrix_values(conn, 3, None, None)
        sql = _sql(cursor)
        assert "[dbo].[ValueMatrix]" in sql
        assert "la.[AnalysisSeries_ID] = ?" in sql

    def test_image_joins_labanalysis(self):
        conn, cursor = _conn_returning([])
        vr.get_analysis_series_image_values(conn, 3, None, None)
        sql = _sql(cursor)
        assert "[dbo].[ValueImage]" in sql
        assert "la.[AnalysisSeries_ID] = ?" in sql


class TestDispatcher:
    def test_dispatches_by_value_kind(self):
        conn, cursor = _conn_returning([])
        vr.get_analysis_series_values_for_metadata(conn, 5, 2, None, None)
        assert "[dbo].[ValueVector]" in _sql(cursor)

    def test_defaults_to_scalar(self):
        conn, cursor = _conn_returning([])
        vr.get_analysis_series_values_for_metadata(conn, 5, None, None, None)
        assert "[dbo].[Value]" in _sql(cursor)


class TestStats:
    def test_lab_stats_join_and_shape(self):
        conn, cursor = _conn_returning([])
        cursor.fetchone.return_value = (FROM, TO, 4)
        out = vr.get_analysis_series_stats(conn, 8, 1)
        sql = _sql(cursor)
        assert "la.[AnalysisSeries_ID] = ?" in sql
        assert out == {
            "analysis_series_id": 8,
            "min_timestamp": FROM,
            "max_timestamp": TO,
            "row_count": 4,
        }

    def test_lab_stats_empty(self):
        conn, cursor = _conn_returning([])
        cursor.fetchone.return_value = (None, None, 0)
        out = vr.get_analysis_series_stats(conn, 8, 1)
        assert out["row_count"] == 0
        assert out["min_timestamp"] is None
