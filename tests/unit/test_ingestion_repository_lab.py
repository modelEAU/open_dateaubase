"""Unit tests for the lab observation model helpers in
api.v1.repositories.ingestion_repository.

These tests run without a database — they patch pyodbc.Connection with
MagicMock and assert against the SQL strings, call sequence and the IDs
returned. Wave D regression coverage for the LabValue → Observation
restructuring.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

from api.v1.repositories import ingestion_repository


def _conn_with_fetchone(returns: list):
    """Build a mock connection whose cursor.fetchone() returns items in order."""
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchone.side_effect = returns
    conn.cursor.return_value = cursor
    return conn, cursor


def _executed_sql(cursor: MagicMock) -> str:
    """Concatenate all SQL strings passed to cursor.execute for substring search."""
    return "\n".join(call.args[0] for call in cursor.execute.call_args_list)


class TestFindOrCreateAnalysisSeries:
    def test_returns_existing_id_when_series_found(self):
        conn, cursor = _conn_with_fetchone([(42,)])

        series_id = ingestion_repository.find_or_create_analysis_series(
            conn,
            parameter_id=7,
            sampling_point_id=3,
            value_kind_id=1,
            processing_kind_id=1,
            unit_id=5,
            name="TSS at Effluent",
        )

        assert series_id == 42
        # Only the SELECT should have run; no INSERT
        assert cursor.execute.call_count == 1
        sql = _executed_sql(cursor)
        assert "SELECT" in sql and "AnalysisSeries" in sql
        assert "INSERT" not in sql
        # No commit when row already exists
        conn.commit.assert_not_called()

    def test_inserts_when_series_not_found_and_returns_new_id(self):
        # First fetchone is the SELECT (no row); second is the INSERT OUTPUT
        conn, cursor = _conn_with_fetchone([None, (99,)])

        series_id = ingestion_repository.find_or_create_analysis_series(
            conn,
            parameter_id=7,
            sampling_point_id=3,
            value_kind_id=2,
            processing_kind_id=1,
            unit_id=5,
            name="PSVD at Effluent",
        )

        assert series_id == 99
        sql = _executed_sql(cursor)
        assert "INSERT INTO [dbo].[AnalysisSeries]" in sql
        # Identity columns appear in INSERT
        for col in ("[Name]", "[Parameter_ID]", "[SamplingPoint_ID]", "[ValueKind_ID]", "[Unit_ID]", "[ProcessingKind_ID]"):
            assert col in sql
        conn.commit.assert_called_once()


class TestInsertLabExperiment:
    def test_inserts_and_returns_id(self):
        conn, cursor = _conn_with_fetchone([(11,)])
        ts = datetime(2026, 5, 20, 9, 30, tzinfo=timezone.utc)

        exp_id = ingestion_repository.insert_lab_experiment(
            conn,
            name="PSVD-Settling-2026-05-20",
            experiment_datetime=ts,
            campaign_id=4,
            description="weekly settling",
            created_by_person_id=2,
        )

        assert exp_id == 11
        sql = _executed_sql(cursor)
        assert "INSERT INTO [dbo].[LabExperiment]" in sql
        for col in ("[Name]", "[Campaign_ID]", "[ExperimentDateTime]", "[Description]", "[CreatedByPerson_ID]", "[LabPanel_ID]"):
            assert col in sql
        conn.commit.assert_called_once()

    def test_inserts_with_lab_panel_id(self):
        conn, cursor = _conn_with_fetchone([(22,)])
        ts = datetime(2026, 5, 20, 9, 30, tzinfo=timezone.utc)

        exp_id = ingestion_repository.insert_lab_experiment(
            conn,
            name="PSVD Weekly Panel — 2026-05-20",
            experiment_datetime=ts,
            lab_panel_id=5,
        )

        assert exp_id == 22
        sql = _executed_sql(cursor)
        assert "[LabPanel_ID]" in sql
        conn.commit.assert_called_once()


class TestInsertLabAnalysis:
    def test_new_required_fks_in_insert(self):
        conn, cursor = _conn_with_fetchone([(55,)])
        ts = datetime(2026, 5, 20, 10, 0, tzinfo=timezone.utc)

        la_id = ingestion_repository.insert_lab_analysis(
            conn,
            lab_experiment_id=11,
            analysis_series_id=42,
            sample_id=7,
            laboratory_id=1,
            analyst_person_id=2,
            procedure_id=3,
            analysis_datetime=ts,
            replicate=2,
            quality_code_id=4,
            notes="duplicate",
        )

        assert la_id == 55
        sql = _executed_sql(cursor)
        # LabAnalysis insert references the two new FKs and the moved columns
        for col in ("[LabExperiment_ID]", "[AnalysisSeries_ID]", "[Replicate]", "[QualityCode_ID]"):
            assert col in sql
        # Campaign_ID was removed from LabAnalysis — must NOT appear
        assert "[Campaign_ID]" not in sql
        conn.commit.assert_called_once()

    def test_omits_datetime_when_none_to_use_default(self):
        conn, cursor = _conn_with_fetchone([(56,)])

        ingestion_repository.insert_lab_analysis(
            conn,
            lab_experiment_id=11,
            analysis_series_id=42,
            sample_id=7,
            analysis_datetime=None,
        )

        sql = _executed_sql(cursor)
        # When caller omits AnalysisDateTime, the column is not in the INSERT
        # so the DB DEFAULT (SYSUTCDATETIME()) is used.
        assert "[AnalysisDateTime]" not in sql


class TestInsertLabObservation:
    def test_scalar_routes_to_value_table_with_xor_columns(self):
        # fetchone calls: (1) Observation INSERT OUTPUT -> obs_id=300
        conn, cursor = _conn_with_fetchone([(300,)])
        ts = datetime(2026, 5, 20, 10, 0, tzinfo=timezone.utc)

        obs_id = ingestion_repository.insert_lab_observation(
            conn,
            lab_analysis_id=55,
            analysis_series_id=42,
            timestamp=ts,
            value_kind_id=1,
            value=12.4,
            quality_code=1,
        )

        assert obs_id == 300
        sql = _executed_sql(cursor)
        # Observation row inserts BOTH Channel_ID (NULL) and LabAnalysis_ID
        assert "INSERT INTO [dbo].[Observation]" in sql
        assert "[Channel_ID]" in sql and "[LabAnalysis_ID]" in sql
        # Scalar payload goes to Value
        assert "INSERT INTO [dbo].[Value]" in sql
        # Not vector/matrix
        assert "ValueVector" not in sql and "ValueMatrix" not in sql
        conn.commit.assert_called_once()

    def test_unsupported_value_kind_raises(self):
        conn, cursor = _conn_with_fetchone([(301,)])
        ts = datetime(2026, 5, 20, 10, 0, tzinfo=timezone.utc)

        try:
            ingestion_repository.insert_lab_observation(
                conn,
                lab_analysis_id=55,
                analysis_series_id=42,
                timestamp=ts,
                value_kind_id=4,  # Image — not yet routed
                value=None,
            )
        except ValueError as exc:
            assert "value_kind_id=4" in str(exc)
        else:
            raise AssertionError("expected ValueError for unsupported value_kind_id")
