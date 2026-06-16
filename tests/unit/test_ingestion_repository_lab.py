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

import pytest
from api.v1.errors import EntityNotFoundError
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
    def test_returns_existing_stream_id_when_series_found(self):
        # find SELECT returns the existing Stream_ID (AnalysisSeries PK).
        conn, cursor = _conn_with_fetchone([(42,)])

        series_id = ingestion_repository.find_or_create_analysis_series(
            conn,
            parameter_id=7,
            sampling_point_id=3,
            value_kind_id=1,
            unit_id=5,
            name="TSS at Effluent",
        )

        assert series_id == 42
        # Only the SELECT should have run; no INSERT
        assert cursor.execute.call_count == 1
        sql = _executed_sql(cursor)
        assert "SELECT" in sql and "AnalysisSeries" in sql
        # Identity find keys on Stream_ID now, and ProcessingKind is gone.
        assert "[Stream_ID]" in sql
        assert "ProcessingKind" not in sql
        assert "INSERT" not in sql
        # No commit when row already exists
        conn.commit.assert_not_called()

    def test_inserts_stream_then_analysis_series_and_returns_stream_id(self):
        # fetchone sequence:
        #   (1) find SELECT -> None (does not exist)
        #   (2) _insert_stream OUTPUT -> Stream_ID = 99
        conn, cursor = _conn_with_fetchone([None, (99,)])

        series_id = ingestion_repository.find_or_create_analysis_series(
            conn,
            parameter_id=7,
            sampling_point_id=3,
            value_kind_id=2,
            unit_id=5,
            name="PSVD at Effluent",
        )

        # Returns the minted Stream_ID, not a separate AnalysisSeries_ID identity.
        assert series_id == 99

        sql_calls = [c.args[0] for c in cursor.execute.call_args_list]
        # Ordering: find SELECT -> Stream INSERT -> AnalysisSeries INSERT.
        stream_idx = next(
            i for i, s in enumerate(sql_calls) if "INSERT INTO [dbo].[Stream]" in s
        )
        series_idx = next(
            i for i, s in enumerate(sql_calls)
            if "INSERT INTO [dbo].[AnalysisSeries]" in s
        )
        assert stream_idx < series_idx

        # Stream insert carries the Lab StreamKind discriminator (=2).
        stream_params = cursor.execute.call_args_list[stream_idx].args[1:]
        assert stream_params == (2,)

        # AnalysisSeries insert uses Stream_ID as PK (no AnalysisSeries_ID identity,
        # no ProcessingKind_ID).
        series_sql = sql_calls[series_idx]
        assert "[Stream_ID]" in series_sql
        assert "OUTPUT INSERTED.[AnalysisSeries_ID]" not in series_sql
        assert "ProcessingKind" not in series_sql
        for col in ("[Name]", "[Parameter_ID]", "[SamplingPoint_ID]", "[ValueKind_ID]", "[Unit_ID]"):
            assert col in series_sql
        # Stream_ID leads the AnalysisSeries insert as its PK.
        series_params = cursor.execute.call_args_list[series_idx].args[1:]
        assert series_params[0] == 99
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


class TestGetSampleCollectionTime:
    def test_returns_sample_datetime_start(self):
        ts = datetime(2026, 5, 18, 8, 15, tzinfo=timezone.utc)
        conn, cursor = _conn_with_fetchone([(ts,)])

        result = ingestion_repository.get_sample_collection_time(conn, sample_id=7)

        assert result == ts
        sql = _executed_sql(cursor)
        assert "SampleDateTimeStart" in sql
        assert "[dbo].[Sample]" in sql

    def test_raises_not_found_when_sample_missing(self):
        conn, _ = _conn_with_fetchone([None])

        with pytest.raises(EntityNotFoundError) as exc_info:
            ingestion_repository.get_sample_collection_time(conn, sample_id=999)

        assert "999" in str(exc_info.value)


class TestFindOrCreateSensorMetadata:
    def test_raw_channel_inserts_stream_then_channel_then_unprocessed_trait(self):
        # fetchone sequence:
        #   (1) find SELECT -> None (does not exist)
        #   (2) _insert_stream OUTPUT -> Stream_ID = 500
        conn, cursor = _conn_with_fetchone([None, (500,)])

        stream_id = ingestion_repository.find_or_create_sensor_metadata(
            conn,
            signal_interface_id=3,
            tag_name="DO-effluent",
            parameter_id=7,
            unit_id=5,
            data_provenance_id=1,
        )

        # Returns the minted Stream_ID, not a separate Channel_ID.
        assert stream_id == 500

        sql_calls = [c.args[0] for c in cursor.execute.call_args_list]
        # Ordering: find SELECT -> Stream INSERT -> Channel INSERT -> ChannelTrait
        stream_idx = next(
            i for i, s in enumerate(sql_calls) if "INSERT INTO [dbo].[Stream]" in s
        )
        channel_idx = next(
            i for i, s in enumerate(sql_calls) if "INSERT INTO [dbo].[Channel]" in s
        )
        trait_idx = next(
            i for i, s in enumerate(sql_calls) if "INSERT INTO [dbo].[ChannelTrait]" in s
        )
        assert stream_idx < channel_idx < trait_idx

        # Stream insert carries the Sensor StreamKind discriminator (=1).
        stream_params = cursor.execute.call_args_list[stream_idx].args[1:]
        assert stream_params == (1,)

        # Channel insert uses Stream_ID as PK (no Channel_ID identity column).
        channel_sql = sql_calls[channel_idx]
        assert "[Stream_ID]" in channel_sql
        assert "OUTPUT INSERTED.[Channel_ID]" not in channel_sql
        channel_params = cursor.execute.call_args_list[channel_idx].args[1:]
        assert channel_params[0] == 500  # Stream_ID as PK leads the insert

        # ChannelTrait row is (Stream_ID=500, OperationKind_ID=1 Unprocessed).
        trait_params = cursor.execute.call_args_list[trait_idx].args[1:]
        assert 500 in trait_params
        assert 1 in trait_params  # Unprocessed
        conn.commit.assert_called_once()

    def test_returns_existing_stream_id_without_inserting(self):
        # find SELECT returns an existing (Stream_ID, Unit_ID) row.
        conn, cursor = _conn_with_fetchone([(777, 5)])

        stream_id = ingestion_repository.find_or_create_sensor_metadata(
            conn,
            signal_interface_id=3,
            tag_name="DO-effluent",
            parameter_id=7,
            unit_id=5,
            data_provenance_id=1,
        )

        assert stream_id == 777
        sql = _executed_sql(cursor)
        assert "INSERT INTO [dbo].[Stream]" not in sql
        assert "INSERT INTO [dbo].[Channel]" not in sql
        assert "INSERT INTO [dbo].[ChannelTrait]" not in sql
        conn.commit.assert_not_called()


class TestFindOrCreateDerivedMetadata:
    def test_derived_channel_writes_unioned_trait_set(self):
        # fetchone sequence:
        #   (1) source-channel SELECT -> (TagName, Parameter_ID, ValueKind_ID, Unit_ID)
        #   (2) find-existing SELECT -> None
        #   (3) _insert_stream OUTPUT -> Stream_ID = 900
        #   (4) source ChannelTrait set -> rows {2, 3}
        #   (5) ProcessingStep OperationKind lookup -> (5,)  (Smoothing)
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.side_effect = [
            ("DO-effluent", 7, 1, 5),  # source channel metadata
            None,  # derived channel does not yet exist
            (900,),  # minted Stream_ID
            (5,),  # producing step OperationKind_ID = Smoothing
        ]
        # The source channel already carries OutlierRemoval(2) + DriftCorrection(3).
        cursor.fetchall.return_value = [(2,), (3,)]
        conn.cursor.return_value = cursor

        stream_id = ingestion_repository.find_or_create_derived_metadata(
            conn,
            source_channel_id=42,
            produced_by_step_id=88,
        )

        assert stream_id == 900

        sql_calls = [c.args[0] for c in cursor.execute.call_args_list]
        # Source lookup keys on Stream_ID, not Channel_ID.
        source_sql = sql_calls[0]
        assert "[Stream_ID] = ?" in source_sql

        stream_idx = next(
            i for i, s in enumerate(sql_calls) if "INSERT INTO [dbo].[Stream]" in s
        )
        channel_idx = next(
            i for i, s in enumerate(sql_calls) if "INSERT INTO [dbo].[Channel]" in s
        )
        trait_calls = [
            c
            for c in cursor.execute.call_args_list
            if "INSERT INTO [dbo].[ChannelTrait]" in c.args[0]
        ]
        assert stream_idx < channel_idx
        # Trait set = {2, 3} (source) ∪ {5} (producing step) = three distinct rows.
        written_ops = {c.args[-1] for c in trait_calls}
        assert written_ops == {2, 3, 5}
        # All traits attach to the new Stream_ID.
        assert all(900 in c.args[1:] for c in trait_calls)
        conn.commit.assert_called_once()

    def test_multi_input_trait_union_includes_non_primary_inputs(self):
        """A derived channel inherits traits from EVERY input of its step, not
        just the primary source — the union is read from ProcessingLineage.

        Primary source (source_channel_id) carries only {2} (OutlierRemoval).
        A second input contributes {5} (Smoothing) via the step's lineage edges.
        The producing step is {6} (Interpolation). The output channel must
        therefore carry {2, 5, 6}. The single-input implementation would have
        written {2, 6} — missing the Smoothing trait from the non-primary input
        — so this test is red on that implementation and green on the union one.
        """
        conn = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.side_effect = [
            ("pca-out", 7, 1, 5),  # source channel metadata
            None,  # derived channel does not yet exist
            (900,),  # minted Stream_ID
            (6,),  # producing step OperationKind_ID = Interpolation
        ]
        # fetchall #1: _get_channel_trait_set(primary source) -> {2}
        # fetchall #2: _get_step_input_trait_union(step) -> {2, 5} across all inputs
        cursor.fetchall.side_effect = [[(2,)], [(2,), (5,)]]
        conn.cursor.return_value = cursor

        stream_id = ingestion_repository.find_or_create_derived_metadata(
            conn,
            source_channel_id=42,
            produced_by_step_id=88,
        )

        assert stream_id == 900

        sql_calls = [c.args[0] for c in cursor.execute.call_args_list]
        # The union is computed from the lineage DAG, not just the source channel.
        assert any(
            "[dbo].[ProcessingLineage]" in s and "JOIN [dbo].[ChannelTrait]" in s
            for s in sql_calls
        )

        trait_calls = [
            c
            for c in cursor.execute.call_args_list
            if "INSERT INTO [dbo].[ChannelTrait]" in c.args[0]
        ]
        written_ops = {c.args[-1] for c in trait_calls}
        # Smoothing(5) from the non-primary input MUST be present.
        assert written_ops == {2, 5, 6}
        assert all(900 in c.args[1:] for c in trait_calls)
        conn.commit.assert_called_once()


class TestLabExperimentExists:
    def test_returns_true_when_row_found(self):
        conn, cursor = _conn_with_fetchone([(1,)])
        assert ingestion_repository.lab_experiment_exists(conn, 42) is True
        sql = _executed_sql(cursor)
        assert "LabExperiment" in sql
        assert "LabExperiment_ID" in sql

    def test_returns_false_when_row_not_found(self):
        conn, cursor = _conn_with_fetchone([None])
        assert ingestion_repository.lab_experiment_exists(conn, 999) is False
