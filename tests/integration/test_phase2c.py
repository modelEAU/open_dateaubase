"""Integration tests for Phase 2c: Sensor Lifecycle Tracking (schema v1.4.0).

Tests cover:
  - Task 2c.1: EquipmentEventType and EquipmentEvent tables
  - Task 2c.2: EquipmentEventMetaData junction table (with WindowStart/WindowEnd)
  - Task 2c.3: EquipmentInstallation table and SamplingPoints temporal columns
  - Schema version 1.4.0 registered
  - Rollback from v1.4.0 → v1.3.0

Requires a running MSSQL container. Skipped automatically if unavailable.
"""

import pytest

from .conftest import (
    SQL_FILES,
    column_exists,
    get_column_type,
    get_table_names,
    run_sql_file,
)


# ===========================================================================
# TestEquipmentEventType
# ===========================================================================


class TestEquipmentEventType:
    """EquipmentEventType lookup table created with correct seed data."""

    def test_table_exists(self, db_at_v140):
        conn, _ = db_at_v140
        assert "EquipmentEventType" in get_table_names(conn)

    def test_seed_data_count(self, db_at_v140):
        conn, _ = db_at_v140
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM [dbo].[EquipmentEventType]")
        assert cursor.fetchone()[0] == 8

    def test_calibration_is_id_1(self, db_at_v140):
        conn, _ = db_at_v140
        cursor = conn.cursor()
        cursor.execute(
            "SELECT [EquipmentEventType_Name] FROM [dbo].[EquipmentEventType] "
            "WHERE [EquipmentEventType_ID] = 1"
        )
        row = cursor.fetchone()
        assert row[0] == "Calibration"

    def test_all_event_type_names_present(self, db_at_v140):
        conn, _ = db_at_v140
        cursor = conn.cursor()
        cursor.execute(
            "SELECT [EquipmentEventType_Name] FROM [dbo].[EquipmentEventType] ORDER BY [EquipmentEventType_ID]"
        )
        names = [r[0] for r in cursor.fetchall()]
        assert names == [
            "Calibration",
            "Validation",
            "Maintenance",
            "Installation",
            "Removal",
            "Firmware Update",
            "Failure",
            "Repair",
        ]


# ===========================================================================
# TestEquipmentEvent
# ===========================================================================


class TestEquipmentEvent:
    """EquipmentEvent table structure and FK constraints."""

    def test_table_exists(self, db_at_v140):
        conn, _ = db_at_v140
        assert "EquipmentEvent" in get_table_names(conn)

    def test_required_columns_exist(self, db_at_v140):
        conn, _ = db_at_v140
        for col in [
            "EquipmentEvent_ID",
            "Equipment_ID",
            "EquipmentEventType_ID",
            "EventDateTimeStart",
            "EventDateTimeEnd",
            "PerformedByPerson_ID",
            "Campaign_ID",
            "Notes",
        ]:
            assert column_exists(conn, "EquipmentEvent", col), f"Missing column: {col}"

    def test_event_datetime_type(self, db_at_v140):
        conn, _ = db_at_v140
        assert get_column_type(conn, "EquipmentEvent", "EventDateTimeStart") == "datetime2"

    def test_insert_basic_event(self, db_at_v140):
        conn, _ = db_at_v140
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO [dbo].[EquipmentEvent] "
            "([Equipment_ID], [EquipmentEventType_ID], [EventDateTimeStart], [Notes]) "
            "VALUES (1, 3, '2025-04-01T06:00:00', 'Cleaning the sensor probe')"
        )
        cursor.execute(
            "SELECT COUNT(*) FROM [dbo].[EquipmentEvent] WHERE [EquipmentEventType_ID] = 3"
        )
        assert cursor.fetchone()[0] == 1

    def test_fk_to_invalid_equipment_rejected(self, db_at_v140):
        conn, _ = db_at_v140
        cursor = conn.cursor()
        with pytest.raises(Exception):
            cursor.execute(
                "INSERT INTO [dbo].[EquipmentEvent] "
                "([Equipment_ID], [EquipmentEventType_ID], [EventDateTimeStart]) "
                "VALUES (99999, 1, '2025-04-01T06:00:00')"
            )
            conn.commit()

    def test_fk_to_invalid_event_type_rejected(self, db_at_v140):
        conn, _ = db_at_v140
        cursor = conn.cursor()
        with pytest.raises(Exception):
            cursor.execute(
                "INSERT INTO [dbo].[EquipmentEvent] "
                "([Equipment_ID], [EquipmentEventType_ID], [EventDateTimeStart]) "
                "VALUES (1, 99, '2025-04-01T06:00:00')"
            )
            conn.commit()

    def test_seed_calibration_event_present(self, db_at_v140):
        """seed_v1.4.0.sql inserts one calibration event (EquipmentEventType_ID=1)."""
        conn, _ = db_at_v140
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM [dbo].[EquipmentEvent] WHERE [EquipmentEventType_ID] = 1"
        )
        assert cursor.fetchone()[0] >= 1


# ===========================================================================
# TestEquipmentEventMetaData
# ===========================================================================


class TestEquipmentEventMetaData:
    """EquipmentEventMetaData junction table with optional time windows."""

    def test_table_exists(self, db_at_v140):
        conn, _ = db_at_v140
        assert "EquipmentEventMetaData" in get_table_names(conn)

    def test_required_columns_exist(self, db_at_v140):
        conn, _ = db_at_v140
        for col in ["EquipmentEvent_ID", "Metadata_ID", "WindowStart", "WindowEnd"]:
            assert column_exists(conn, "EquipmentEventMetaData", col), f"Missing column: {col}"

    def test_window_columns_are_nullable(self, db_at_v140):
        conn, _ = db_at_v140
        cursor = conn.cursor()
        cursor.execute(
            "SELECT IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA='dbo' AND TABLE_NAME='EquipmentEventMetaData' "
            "AND COLUMN_NAME='WindowStart'"
        )
        assert cursor.fetchone()[0] == "YES"

    def test_insert_link_without_window(self, db_at_v140):
        """Link an event to a MetaData series with no time window (NULLs)."""
        conn, _ = db_at_v140
        cursor = conn.cursor()

        # Get an existing EquipmentEvent_ID from seed
        cursor.execute("SELECT TOP 1 [EquipmentEvent_ID] FROM [dbo].[EquipmentEvent]")
        event_id = cursor.fetchone()[0]

        # Get a MetaData_ID to link
        cursor.execute("SELECT TOP 1 [Metadata_ID] FROM [dbo].[MetaData]")
        md_id = cursor.fetchone()[0]

        cursor.execute(
            "INSERT INTO [dbo].[EquipmentEventMetaData] "
            "([EquipmentEvent_ID], [Metadata_ID], [WindowStart], [WindowEnd]) "
            "VALUES (?, ?, NULL, NULL)",
            event_id,
            md_id,
        )
        cursor.execute(
            "SELECT COUNT(*) FROM [dbo].[EquipmentEventMetaData] "
            "WHERE [EquipmentEvent_ID] = ? AND [Metadata_ID] = ?",
            event_id,
            md_id,
        )
        assert cursor.fetchone()[0] == 1

    def test_insert_link_with_window(self, db_at_v140):
        """Link an event to a MetaData series with explicit time window."""
        conn, _ = db_at_v140
        cursor = conn.cursor()

        cursor.execute("SELECT TOP 1 [EquipmentEvent_ID] FROM [dbo].[EquipmentEvent]")
        event_id = cursor.fetchone()[0]

        # Use a second MetaData row if available, else same one
        cursor.execute("SELECT TOP 2 [Metadata_ID] FROM [dbo].[MetaData] ORDER BY [Metadata_ID]")
        rows = cursor.fetchall()
        md_id = rows[-1][0]  # last one to avoid PK collision with previous test

        cursor.execute(
            "INSERT INTO [dbo].[EquipmentEventMetaData] "
            "([EquipmentEvent_ID], [Metadata_ID], [WindowStart], [WindowEnd]) "
            "VALUES (?, ?, '2025-03-15T09:59:00', '2025-03-15T10:01:00')",
            event_id,
            md_id,
        )
        cursor.execute(
            "SELECT [WindowStart] FROM [dbo].[EquipmentEventMetaData] "
            "WHERE [EquipmentEvent_ID] = ? AND [Metadata_ID] = ?",
            event_id,
            md_id,
        )
        row = cursor.fetchone()
        assert row is not None  # window was stored

    def test_composite_pk_prevents_duplicate_link(self, db_at_v140):
        """Same (EquipmentEvent_ID, Metadata_ID) pair cannot be inserted twice."""
        conn, _ = db_at_v140
        cursor = conn.cursor()

        cursor.execute("SELECT TOP 1 [EquipmentEvent_ID] FROM [dbo].[EquipmentEvent]")
        event_id = cursor.fetchone()[0]
        cursor.execute("SELECT TOP 1 [Metadata_ID] FROM [dbo].[MetaData]")
        md_id = cursor.fetchone()[0]

        # First insert
        cursor.execute(
            "INSERT INTO [dbo].[EquipmentEventMetaData] ([EquipmentEvent_ID], [Metadata_ID]) "
            "VALUES (?, ?)",
            event_id,
            md_id,
        )

        # Second insert of same PK must fail
        with pytest.raises(Exception):
            cursor.execute(
                "INSERT INTO [dbo].[EquipmentEventMetaData] ([EquipmentEvent_ID], [Metadata_ID]) "
                "VALUES (?, ?)",
                event_id,
                md_id,
            )
            conn.commit()


# ===========================================================================
# TestEquipmentInstallation
# ===========================================================================


class TestEquipmentInstallation:
    """EquipmentInstallation table for deployment history."""

    def test_table_exists(self, db_at_v140):
        conn, _ = db_at_v140
        assert "EquipmentInstallation" in get_table_names(conn)

    def test_required_columns_exist(self, db_at_v140):
        conn, _ = db_at_v140
        for col in [
            "Installation_ID",
            "Equipment_ID",
            "Sampling_point_ID",
            "InstalledDate",
            "RemovedDate",
            "Campaign_ID",
            "Notes",
        ]:
            assert column_exists(conn, "EquipmentInstallation", col), f"Missing column: {col}"

    def test_removed_date_is_nullable(self, db_at_v140):
        conn, _ = db_at_v140
        cursor = conn.cursor()
        cursor.execute(
            "SELECT IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA='dbo' AND TABLE_NAME='EquipmentInstallation' "
            "AND COLUMN_NAME='RemovedDate'"
        )
        assert cursor.fetchone()[0] == "YES"

    def test_insert_installation(self, db_at_v140):
        conn, _ = db_at_v140
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO [dbo].[EquipmentInstallation] "
            "([Equipment_ID], [Sampling_point_ID], [InstalledDate], [Notes]) "
            "VALUES (1, 1, '2025-06-01T07:00:00', 'Second deployment')"
        )
        cursor.execute(
            "SELECT COUNT(*) FROM [dbo].[EquipmentInstallation] WHERE [Equipment_ID] = 1"
        )
        assert cursor.fetchone()[0] >= 1

    def test_fk_to_invalid_sampling_point_rejected(self, db_at_v140):
        conn, _ = db_at_v140
        cursor = conn.cursor()
        with pytest.raises(Exception):
            cursor.execute(
                "INSERT INTO [dbo].[EquipmentInstallation] "
                "([Equipment_ID], [Sampling_point_ID], [InstalledDate]) "
                "VALUES (1, 99999, '2025-06-01T07:00:00')"
            )
            conn.commit()

    def test_seed_installation_present(self, db_at_v140):
        """seed_v1.4.0.sql inserts one installation record."""
        conn, _ = db_at_v140
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM [dbo].[EquipmentInstallation]")
        assert cursor.fetchone()[0] >= 1


# ===========================================================================
# TestSamplingPointsTemporalColumns
# ===========================================================================


class TestSamplingPointsTemporalColumns:
    """ValidFrom, ValidTo, CreatedByCampaign_ID added to SamplingPoints."""

    def test_valid_from_exists(self, db_at_v140):
        conn, _ = db_at_v140
        assert column_exists(conn, "SamplingPoints", "ValidFrom")

    def test_valid_to_exists(self, db_at_v140):
        conn, _ = db_at_v140
        assert column_exists(conn, "SamplingPoints", "ValidTo")

    def test_created_by_campaign_id_exists(self, db_at_v140):
        conn, _ = db_at_v140
        assert column_exists(conn, "SamplingPoints", "CreatedByCampaign_ID")

    def test_all_three_are_nullable(self, db_at_v140):
        conn, _ = db_at_v140
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COLUMN_NAME, IS_NULLABLE "
            "FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_SCHEMA='dbo' AND TABLE_NAME='SamplingPoints' "
            "AND COLUMN_NAME IN ('ValidFrom', 'ValidTo', 'CreatedByCampaign_ID')"
        )
        for col_name, nullable in cursor.fetchall():
            assert nullable == "YES", f"Expected {col_name} to be nullable"

    def test_existing_rows_unaffected(self, db_at_v140):
        """Rows inserted before v1.4.0 have NULL in new columns — non-breaking."""
        conn, _ = db_at_v140
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM [dbo].[SamplingPoints] "
            "WHERE [ValidFrom] IS NULL AND [ValidTo] IS NULL AND [CreatedByCampaign_ID] IS NULL"
        )
        assert cursor.fetchone()[0] >= 1

    def test_fk_to_campaign_accepted(self, db_at_v140):
        """CreatedByCampaign_ID FK works when pointing to a valid Campaign_ID."""
        conn, _ = db_at_v140
        cursor = conn.cursor()
        cursor.execute("SELECT TOP 1 [Campaign_ID] FROM [dbo].[Campaign]")
        campaign_id = cursor.fetchone()[0]

        cursor.execute("SELECT TOP 1 [Site_ID] FROM [dbo].[Site]")
        site_id = cursor.fetchone()[0]

        cursor.execute(
            "INSERT INTO [dbo].[SamplingPoints] "
            "([Site_ID], [Sampling_point], [Sampling_location], [CreatedByCampaign_ID]) "
            "VALUES (?, 'Test Point', 'Test Location', ?)",
            site_id,
            campaign_id,
        )
        cursor.execute(
            "SELECT COUNT(*) FROM [dbo].[SamplingPoints] WHERE [CreatedByCampaign_ID] = ?",
            campaign_id,
        )
        assert cursor.fetchone()[0] >= 1

    def test_fk_to_invalid_campaign_rejected(self, db_at_v140):
        conn, _ = db_at_v140
        cursor = conn.cursor()
        with pytest.raises(Exception):
            cursor.execute(
                "INSERT INTO [dbo].[SamplingPoints] "
                "([Sampling_point], [CreatedByCampaign_ID]) "
                "VALUES ('Bad Point', 99999)"
            )
            conn.commit()


# ===========================================================================
# TestCalibrationCrossReferenceQuery
# ===========================================================================


class TestCalibrationCrossReferenceQuery:
    """End-to-end: calibration event links sensor and lab MetaData via shared Sample."""

    def test_cross_reference_query_executes(self, db_at_v140):
        """Set up a minimal calibration scenario and verify the cross-reference query runs."""
        conn, _ = db_at_v140
        cursor = conn.cursor()

        # -- Person (analyst / technician)
        cursor.execute(
            "INSERT INTO [dbo].[Person] ([First_name], [Last_name]) "
            "OUTPUT INSERTED.Person_ID VALUES ('Cal', 'Tech')"
        )
        person_id = cursor.fetchone()[0]

        # -- Campaign
        cursor.execute(
            "SELECT TOP 1 [Campaign_ID] FROM [dbo].[Campaign]"
        )
        campaign_id = cursor.fetchone()[0]

        # -- Sampling point for the calibration solution
        cursor.execute("SELECT TOP 1 [Site_ID] FROM [dbo].[Site]")
        site_id = cursor.fetchone()[0]
        cursor.execute(
            "INSERT INTO [dbo].[SamplingPoints] ([Site_ID], [Sampling_point], [Sampling_location]) "
            "OUTPUT INSERTED.Sampling_point_ID VALUES (?, 'CalSol', 'Calibration Solution')",
            site_id,
        )
        sp_cal_id = cursor.fetchone()[0]

        # -- Master standard sample
        cursor.execute(
            "INSERT INTO [dbo].[Sample] "
            "([Sampling_point_ID], [SampleCategory], [SampledByPerson_ID], "
            "[Campaign_ID], [SampleDateTimeStart], [SampleType]) "
            "OUTPUT INSERTED.Sample_ID "
            "VALUES (?, 'Master Standard', ?, ?, '2025-03-14T10:00:00', 'Grab')",
            sp_cal_id, person_id, campaign_id,
        )
        master_id = cursor.fetchone()[0]

        # -- Derived standard (sub-sample of master)
        cursor.execute(
            "INSERT INTO [dbo].[Sample] "
            "([Sampling_point_ID], [SampleCategory], [ParentSample_ID], "
            "[SampledByPerson_ID], [Campaign_ID], [SampleDateTimeStart], [SampleType]) "
            "OUTPUT INSERTED.Sample_ID "
            "VALUES (?, 'Derived Standard', ?, ?, ?, '2025-03-15T08:00:00', 'Grab')",
            sp_cal_id, master_id, person_id, campaign_id,
        )
        derived_id = cursor.fetchone()[0]

        # -- Laboratory
        cursor.execute(
            "SELECT TOP 1 [Laboratory_ID] FROM [dbo].[Laboratory]"
        )
        lab_id = cursor.fetchone()[0]

        # -- Parameters and units
        cursor.execute("SELECT TOP 1 [Parameter_ID] FROM [dbo].[Parameter]")
        param_id = cursor.fetchone()[0]
        cursor.execute("SELECT TOP 1 [Unit_ID] FROM [dbo].[Unit]")
        unit_id = cursor.fetchone()[0]
        cursor.execute("SELECT TOP 1 [Sampling_point_ID] FROM [dbo].[SamplingPoints] WHERE [Sampling_point_ID] != ?", sp_cal_id)
        sp_sensor_id = cursor.fetchone()[0]

        # -- Sensor MetaData (DataProvenance_ID=1)
        cursor.execute(
            "INSERT INTO [dbo].[MetaData] "
            "([Sampling_point_ID], [Parameter_ID], [Unit_ID], [DataProvenance_ID], "
            "[Campaign_ID], [Sample_ID]) "
            "OUTPUT INSERTED.Metadata_ID "
            "VALUES (?, ?, ?, 1, ?, ?)",
            sp_sensor_id, param_id, unit_id, campaign_id, derived_id,
        )
        sensor_md_id = cursor.fetchone()[0]

        # -- Lab MetaData (DataProvenance_ID=2)
        cursor.execute(
            "INSERT INTO [dbo].[MetaData] "
            "([Sampling_point_ID], [Parameter_ID], [Unit_ID], [DataProvenance_ID], "
            "[Campaign_ID], [Sample_ID], [Laboratory_ID], [AnalystPerson_ID]) "
            "OUTPUT INSERTED.Metadata_ID "
            "VALUES (?, ?, ?, 2, ?, ?, ?, ?)",
            sp_cal_id, param_id, unit_id, campaign_id, derived_id, lab_id, person_id,
        )
        lab_md_id = cursor.fetchone()[0]

        # -- EquipmentEvent (Calibration)
        cursor.execute(
            "INSERT INTO [dbo].[EquipmentEvent] "
            "([Equipment_ID], [EquipmentEventType_ID], [EventDateTimeStart], [EventDateTimeEnd], "
            "[PerformedByPerson_ID], [Campaign_ID], [Notes]) "
            "OUTPUT INSERTED.EquipmentEvent_ID "
            "VALUES (1, 1, '2025-03-15T08:00:00', '2025-03-15T09:00:00', ?, ?, 'Calibration test')",
            person_id, campaign_id,
        )
        event_id = cursor.fetchone()[0]

        # -- Link sensor MetaData with time window
        cursor.execute(
            "INSERT INTO [dbo].[EquipmentEventMetaData] "
            "([EquipmentEvent_ID], [Metadata_ID], [WindowStart], [WindowEnd]) "
            "VALUES (?, ?, '2025-03-15T08:55:00', '2025-03-15T08:57:00')",
            event_id, sensor_md_id,
        )

        # -- Link lab MetaData (no window needed)
        cursor.execute(
            "INSERT INTO [dbo].[EquipmentEventMetaData] "
            "([EquipmentEvent_ID], [Metadata_ID]) VALUES (?, ?)",
            event_id, lab_md_id,
        )

        # -- Cross-reference query: for this calibration event, how many MetaData links exist?
        cursor.execute(
            "SELECT COUNT(*) FROM [dbo].[EquipmentEventMetaData] WHERE [EquipmentEvent_ID] = ?",
            event_id,
        )
        assert cursor.fetchone()[0] == 2

        # -- Verify sensor and lab MetaData share the same Sample_ID
        cursor.execute(
            "SELECT [Sample_ID] FROM [dbo].[MetaData] WHERE [Metadata_ID] IN (?, ?)",
            sensor_md_id, lab_md_id,
        )
        sample_ids = {r[0] for r in cursor.fetchall()}
        assert sample_ids == {derived_id}, "Both MetaData rows should reference the same calibration sample"


# ===========================================================================
# TestSchemaVersionV140
# ===========================================================================


class TestSchemaVersionV140:
    def test_schema_version_is_140(self, db_at_v140):
        conn, _ = db_at_v140
        cursor = conn.cursor()
        cursor.execute(
            "SELECT [Version] FROM [dbo].[SchemaVersion] WHERE [Version] = '1.4.0'"
        )
        assert cursor.fetchone() is not None


# ===========================================================================
# TestRollbackV140
# ===========================================================================


class TestRollbackV140:
    """Rolling back v1.4.0 removes all new objects and leaves v1.3.0 intact."""

    def test_rollback_removes_new_tables(self, db_at_v140):
        pass  # SQL_FILES and run_sql_file already imported at module level

        conn, _ = db_at_v140
        run_sql_file(conn, SQL_FILES["rollback_v1.4.0"])

        tables = get_table_names(conn)
        for t in [
            "EquipmentEventType",
            "EquipmentEvent",
            "EquipmentEventMetaData",
            "EquipmentInstallation",
        ]:
            assert t not in tables, f"Table {t} should have been removed by rollback"

    def test_rollback_removes_sampling_points_columns(self, db_at_v140):
        pass  # SQL_FILES and run_sql_file already imported at module level

        conn, _ = db_at_v140
        run_sql_file(conn, SQL_FILES["rollback_v1.4.0"])

        for col in ["ValidFrom", "ValidTo", "CreatedByCampaign_ID"]:
            assert not column_exists(conn, "SamplingPoints", col), (
                f"Column SamplingPoints.{col} should have been removed by rollback"
            )

    def test_rollback_removes_version_entry(self, db_at_v140):
        pass  # SQL_FILES and run_sql_file already imported at module level

        conn, _ = db_at_v140
        run_sql_file(conn, SQL_FILES["rollback_v1.4.0"])

        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM [dbo].[SchemaVersion] WHERE [Version] = '1.4.0'"
        )
        assert cursor.fetchone()[0] == 0

    def test_rollback_preserves_v130_tables(self, db_at_v140):
        pass  # SQL_FILES and run_sql_file already imported at module level

        conn, _ = db_at_v140
        run_sql_file(conn, SQL_FILES["rollback_v1.4.0"])

        tables = get_table_names(conn)
        for t in ["Laboratory", "Sample", "CampaignSamplingLocation", "CampaignEquipment", "CampaignParameter"]:
            assert t in tables, f"v1.3.0 table {t} should still exist after v1.4.0 rollback"
