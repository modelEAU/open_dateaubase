"""Integration tests for Phase 2b: Lab Data Support.

Schema version: v1.3.0

Covers:
  Task 2b.1 — Laboratory and Sample tables
  Task 2b.2 — Lab context columns on MetaData (Sample_ID, Laboratory_ID, AnalystPerson_ID)
  Task 2b.3 — CampaignSamplingLocation, CampaignEquipment, CampaignParameter junction tables
  Task 2b.4 — End-to-end lab data scenario; lab vs sensor coexistence
  Rollback    — v1.3.0 → v1.2.0 reverts all changes cleanly
"""

import pytest

from .conftest import (
    SQL_FILES,
    column_exists,
    get_table_names,
    get_table_row_count,
    run_sql_file,
)

pytestmark = pytest.mark.db

# New tables introduced in v1.3.0
V130_NEW_TABLES = {
    "Laboratory",
    "Sample",
    "CampaignSamplingLocation",
    "CampaignEquipment",
    "CampaignParameter",
}


# ============================================================================
# Task 2b.1 — Laboratory table
# ============================================================================


class TestLaboratory:
    def test_laboratory_table_exists(self, db_at_v130):
        conn, _ = db_at_v130
        assert "Laboratory" in get_table_names(conn)

    def test_seed_laboratory_exists(self, db_at_v130):
        conn, _ = db_at_v130
        assert get_table_row_count(conn, "Laboratory") == 1

    def test_insert_external_laboratory(self, db_at_v130):
        """External lab has no Site_ID."""
        conn, _ = db_at_v130
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO [dbo].[Laboratory] ([Name], [Site_ID], [Description]) VALUES (?, ?, ?)",
            "External Accredited Lab", None, "City municipality analytical services"
        )
        conn.commit()
        cursor.execute(
            "SELECT [Site_ID] FROM [dbo].[Laboratory] WHERE [Name] = ?",
            "External Accredited Lab"
        )
        assert cursor.fetchone()[0] is None

    def test_laboratory_fk_site_enforced(self, db_at_v130):
        """FK violation: Site_ID=9999 does not exist."""
        conn, _ = db_at_v130
        cursor = conn.cursor()
        with pytest.raises(Exception):
            cursor.execute(
                "INSERT INTO [dbo].[Laboratory] ([Name], [Site_ID]) VALUES (?, ?)",
                "Bad Lab", 9999
            )


# ============================================================================
# Task 2b.1 — Sample table
# ============================================================================


class TestSample:
    def test_sample_table_exists(self, db_at_v130):
        conn, _ = db_at_v130
        assert "Sample" in get_table_names(conn)

    def test_seed_sample_exists(self, db_at_v130):
        conn, _ = db_at_v130
        assert get_table_row_count(conn, "Sample") == 1

    def test_insert_grab_sample(self, db_at_v130):
        conn, _ = db_at_v130
        cursor = conn.cursor()
        cursor.execute("SELECT TOP 1 [Sampling_point_ID] FROM [dbo].[SamplingPoints]")
        sp_id = cursor.fetchone()[0]
        cursor.execute("SELECT TOP 1 [Person_ID] FROM [dbo].[Person]")
        person_id = cursor.fetchone()[0]
        cursor.execute("SELECT TOP 1 [Campaign_ID] FROM [dbo].[Campaign]")
        campaign_id = cursor.fetchone()[0]

        cursor.execute(
            "INSERT INTO [dbo].[Sample] "
            "([Sampling_point_ID], [SampledByPerson_ID], [Campaign_ID], "
            "[SampleDateTimeStart], [SampleType], [Description]) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            sp_id, person_id, campaign_id,
            "2025-06-01T09:00:00", "Grab", "Morning sample"
        )
        conn.commit()
        cursor.execute(
            "SELECT [SampleType] FROM [dbo].[Sample] WHERE [Description] = ?",
            "Morning sample"
        )
        assert cursor.fetchone()[0] == "Grab"

    def test_insert_composite_sample_with_end_time(self, db_at_v130):
        """24h composite sample has both start and end datetime."""
        conn, _ = db_at_v130
        cursor = conn.cursor()
        cursor.execute("SELECT TOP 1 [Sampling_point_ID] FROM [dbo].[SamplingPoints]")
        sp_id = cursor.fetchone()[0]

        cursor.execute(
            "INSERT INTO [dbo].[Sample] "
            "([Sampling_point_ID], [SampleDateTimeStart], [SampleDateTimeEnd], [SampleType]) "
            "VALUES (?, ?, ?, ?)",
            sp_id, "2025-09-01T09:00:00", "2025-09-02T09:00:00", "Composite24h"
        )
        conn.commit()
        cursor.execute(
            "SELECT [SampleDateTimeEnd] FROM [dbo].[Sample] WHERE [SampleType] = 'Composite24h'"
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] is not None

    def test_sample_requires_sampling_point(self, db_at_v130):
        """Sampling_point_ID is NOT NULL."""
        conn, _ = db_at_v130
        cursor = conn.cursor()
        with pytest.raises(Exception):
            cursor.execute(
                "INSERT INTO [dbo].[Sample] ([SampleDateTimeStart]) VALUES (?)",
                "2025-01-01T00:00:00"
            )

    def test_sample_category_field(self, db_at_v130):
        """SampleCategory stores controlled vocabulary values."""
        conn, _ = db_at_v130
        cursor = conn.cursor()
        cursor.execute("SELECT TOP 1 [Sampling_point_ID] FROM [dbo].[SamplingPoints]")
        sp_id = cursor.fetchone()[0]
        for cat in ("Field", "Synthetic", "Master Standard", "Derived Standard", "Blank"):
            cursor.execute(
                "INSERT INTO [dbo].[Sample] ([Sampling_point_ID], [SampleDateTimeStart], [SampleCategory]) "
                "VALUES (?, ?, ?)",
                sp_id, "2025-01-01T00:00:00", cat
            )
        conn.commit()
        cursor.execute(
            "SELECT COUNT(DISTINCT [SampleCategory]) FROM [dbo].[Sample] "
            "WHERE [SampleCategory] IN ('Field','Synthetic','Master Standard','Derived Standard','Blank')"
        )
        assert cursor.fetchone()[0] == 5

    def test_parent_sample_self_fk(self, db_at_v130):
        """A Derived Standard can reference a Master Standard as its parent."""
        conn, _ = db_at_v130
        cursor = conn.cursor()
        cursor.execute("SELECT TOP 1 [Sampling_point_ID] FROM [dbo].[SamplingPoints]")
        sp_id = cursor.fetchone()[0]

        # Insert master standard
        cursor.execute(
            "INSERT INTO [dbo].[Sample] "
            "([Sampling_point_ID], [SampleDateTimeStart], [SampleCategory]) "
            "VALUES (?, ?, ?)",
            sp_id, "2025-01-01T08:00:00", "Master Standard"
        )
        cursor.execute("SELECT @@IDENTITY")
        master_id = int(cursor.fetchone()[0])

        # Insert derived standard referencing the master
        cursor.execute(
            "INSERT INTO [dbo].[Sample] "
            "([ParentSample_ID], [Sampling_point_ID], [SampleDateTimeStart], [SampleCategory]) "
            "VALUES (?, ?, ?, ?)",
            master_id, sp_id, "2025-01-01T08:30:00", "Derived Standard"
        )
        cursor.execute("SELECT @@IDENTITY")
        derived_id = int(cursor.fetchone()[0])
        conn.commit()

        cursor.execute(
            "SELECT [ParentSample_ID] FROM [dbo].[Sample] WHERE [Sample_ID] = ?",
            derived_id
        )
        assert cursor.fetchone()[0] == master_id

    def test_parent_sample_fk_enforced(self, db_at_v130):
        """FK violation: ParentSample_ID=9999 does not exist."""
        conn, _ = db_at_v130
        cursor = conn.cursor()
        cursor.execute("SELECT TOP 1 [Sampling_point_ID] FROM [dbo].[SamplingPoints]")
        sp_id = cursor.fetchone()[0]
        with pytest.raises(Exception):
            cursor.execute(
                "INSERT INTO [dbo].[Sample] "
                "([ParentSample_ID], [Sampling_point_ID], [SampleDateTimeStart]) "
                "VALUES (?, ?, ?)",
                9999, sp_id, "2025-01-01T00:00:00"
            )

    def test_sample_fk_to_person(self, db_at_v130):
        """FK violation: SampledByPerson_ID=9999 does not exist."""
        conn, _ = db_at_v130
        cursor = conn.cursor()
        cursor.execute("SELECT TOP 1 [Sampling_point_ID] FROM [dbo].[SamplingPoints]")
        sp_id = cursor.fetchone()[0]
        with pytest.raises(Exception):
            cursor.execute(
                "INSERT INTO [dbo].[Sample] "
                "([Sampling_point_ID], [SampledByPerson_ID], [SampleDateTimeStart]) "
                "VALUES (?, ?, ?)",
                sp_id, 9999, "2025-01-01T00:00:00"
            )


# ============================================================================
# Task 2b.2 — Lab context columns on MetaData
# ============================================================================


class TestMetaDataLabColumns:
    def test_sample_id_column_exists(self, db_at_v130):
        conn, _ = db_at_v130
        assert column_exists(conn, "MetaData", "Sample_ID")

    def test_laboratory_id_column_exists(self, db_at_v130):
        conn, _ = db_at_v130
        assert column_exists(conn, "MetaData", "Laboratory_ID")

    def test_analyst_person_id_column_exists(self, db_at_v130):
        conn, _ = db_at_v130
        assert column_exists(conn, "MetaData", "AnalystPerson_ID")

    def test_legacy_rows_unaffected(self, db_at_v130):
        """All existing MetaData rows have NULL for the new columns."""
        conn, _ = db_at_v130
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM [dbo].[MetaData] "
            "WHERE [Sample_ID] IS NULL AND [Laboratory_ID] IS NULL AND [AnalystPerson_ID] IS NULL"
        )
        assert cursor.fetchone()[0] > 0

    def test_invalid_sample_fk_rejected(self, db_at_v130):
        """FK violation: Sample_ID=9999 does not exist."""
        conn, _ = db_at_v130
        cursor = conn.cursor()
        cursor.execute("SELECT TOP 1 [Metadata_ID] FROM [dbo].[MetaData]")
        md_id = cursor.fetchone()[0]
        with pytest.raises(Exception):
            cursor.execute(
                "UPDATE [dbo].[MetaData] SET [Sample_ID] = 9999 WHERE [Metadata_ID] = ?",
                md_id
            )


# ============================================================================
# Task 2b.3 — Campaign junction tables
# ============================================================================


class TestCampaignJunctionTables:
    def test_all_junction_tables_exist(self, db_at_v130):
        conn, _ = db_at_v130
        tables = get_table_names(conn)
        for t in V130_NEW_TABLES:
            assert t in tables, f"Table {t} not found"

    def test_seed_campaign_sampling_location(self, db_at_v130):
        """seed_v1.3.0 inserts 2 entries (one per campaign)."""
        conn, _ = db_at_v130
        assert get_table_row_count(conn, "CampaignSamplingLocation") == 2

    def test_seed_campaign_equipment(self, db_at_v130):
        conn, _ = db_at_v130
        assert get_table_row_count(conn, "CampaignEquipment") == 2

    def test_seed_campaign_parameter(self, db_at_v130):
        conn, _ = db_at_v130
        assert get_table_row_count(conn, "CampaignParameter") == 2

    def test_composability_scenario(self, db_at_v130):
        """Three campaigns share two sampling points composably.

        Operations  → uses SP1, SP2
        Experiment A → uses SP1
        Experiment B → uses SP2
        Query: "What locations does Experiment A use?" → SP1 only
        Query: "What campaigns use SP1?" → Operations and Experiment A
        Query: "What campaigns overlap with Experiment A?" → Operations (shared SP1)
        """
        conn, _ = db_at_v130
        cursor = conn.cursor()

        # Get existing site and sampling points
        cursor.execute("SELECT TOP 1 [Site_ID] FROM [dbo].[Site]")
        site_id = cursor.fetchone()[0]
        cursor.execute(
            "SELECT TOP 2 [Sampling_point_ID] FROM [dbo].[SamplingPoints] ORDER BY [Sampling_point_ID]"
        )
        sp_rows = cursor.fetchall()
        if len(sp_rows) < 2:
            pytest.skip("Need at least 2 SamplingPoints for composability test")
        sp1, sp2 = sp_rows[0][0], sp_rows[1][0]

        # Create three campaigns
        cursor.execute(
            "INSERT INTO [dbo].[Campaign] ([CampaignType_ID], [Site_ID], [Name]) VALUES (?, ?, ?)",
            2, site_id, "Ops2b"
        )
        cursor.execute("SELECT @@IDENTITY")
        ops_id = int(cursor.fetchone()[0])

        cursor.execute(
            "INSERT INTO [dbo].[Campaign] ([CampaignType_ID], [Site_ID], [Name]) VALUES (?, ?, ?)",
            1, site_id, "ExpA2b"
        )
        cursor.execute("SELECT @@IDENTITY")
        expa_id = int(cursor.fetchone()[0])

        cursor.execute(
            "INSERT INTO [dbo].[Campaign] ([CampaignType_ID], [Site_ID], [Name]) VALUES (?, ?, ?)",
            1, site_id, "ExpB2b"
        )
        cursor.execute("SELECT @@IDENTITY")
        expb_id = int(cursor.fetchone()[0])

        # Link sampling locations
        for row in [
            (ops_id, sp1), (ops_id, sp2),
            (expa_id, sp1),
            (expb_id, sp2),
        ]:
            cursor.execute(
                "INSERT INTO [dbo].[CampaignSamplingLocation] ([Campaign_ID], [Sampling_point_ID]) VALUES (?, ?)",
                *row
            )
        conn.commit()

        # "What locations does Experiment A use?" → sp1 only
        cursor.execute(
            "SELECT [Sampling_point_ID] FROM [dbo].[CampaignSamplingLocation] WHERE [Campaign_ID] = ?",
            expa_id
        )
        expa_locs = {r[0] for r in cursor.fetchall()}
        assert expa_locs == {sp1}

        # "What campaigns use SP1?" → ops_id and expa_id
        cursor.execute(
            "SELECT [Campaign_ID] FROM [dbo].[CampaignSamplingLocation] WHERE [Sampling_point_ID] = ?",
            sp1
        )
        sp1_campaigns = {r[0] for r in cursor.fetchall()}
        assert ops_id in sp1_campaigns
        assert expa_id in sp1_campaigns
        assert expb_id not in sp1_campaigns

        # "What campaigns overlap with Experiment A?" → those sharing any of Experiment A's locations
        cursor.execute(
            "SELECT DISTINCT csl2.[Campaign_ID] "
            "FROM [dbo].[CampaignSamplingLocation] csl1 "
            "JOIN [dbo].[CampaignSamplingLocation] csl2 "
            "  ON csl1.[Sampling_point_ID] = csl2.[Sampling_point_ID] "
            "WHERE csl1.[Campaign_ID] = ? AND csl2.[Campaign_ID] != ?",
            expa_id, expa_id
        )
        overlapping = {r[0] for r in cursor.fetchall()}
        assert ops_id in overlapping
        assert expb_id not in overlapping


# ============================================================================
# Task 2b.4 — End-to-end lab data scenario
# ============================================================================


class TestEndToEndLabData:
    """Full scenario: Lab TSS measurement coexists with sensor TSS measurement."""

    def _setup_scenario(self, conn):
        """Insert all objects for the scenario. Returns a dict of key IDs."""
        cursor = conn.cursor()

        # Get seed IDs
        cursor.execute("SELECT TOP 1 [Site_ID] FROM [dbo].[Site]")
        site_id = cursor.fetchone()[0]
        cursor.execute("SELECT TOP 1 [Sampling_point_ID] FROM [dbo].[SamplingPoints]")
        sp_id = cursor.fetchone()[0]
        cursor.execute("SELECT TOP 1 [Parameter_ID] FROM [dbo].[Parameter]")
        param_id = cursor.fetchone()[0]
        cursor.execute("SELECT TOP 1 [Unit_ID] FROM [dbo].[Unit]")
        unit_id = cursor.fetchone()[0]
        cursor.execute("SELECT TOP 1 [Equipment_ID] FROM [dbo].[Equipment]")
        equip_id = cursor.fetchone()[0]

        # Create an analyst Person
        cursor.execute(
            "INSERT INTO [dbo].[Person] ([Last_name], [First_name], [Role]) VALUES (?, ?, ?)",
            "Dupont", "Marie", "PhD"
        )
        cursor.execute("SELECT @@IDENTITY")
        analyst_id = int(cursor.fetchone()[0])

        # Laboratory
        cursor.execute(
            "INSERT INTO [dbo].[Laboratory] ([Name], [Site_ID]) VALUES (?, ?)",
            "Test Lab", site_id
        )
        cursor.execute("SELECT @@IDENTITY")
        lab_id = int(cursor.fetchone()[0])

        # Campaign
        cursor.execute(
            "INSERT INTO [dbo].[Campaign] ([CampaignType_ID], [Site_ID], [Name]) VALUES (?, ?, ?)",
            1, site_id, "TSS Validation E2E"
        )
        cursor.execute("SELECT @@IDENTITY")
        campaign_id = int(cursor.fetchone()[0])

        # Sample
        cursor.execute(
            "INSERT INTO [dbo].[Sample] "
            "([Sampling_point_ID], [SampledByPerson_ID], [Campaign_ID], [SampleDateTimeStart], [SampleType]) "
            "VALUES (?, ?, ?, ?, ?)",
            sp_id, analyst_id, campaign_id, "2025-03-15T08:00:00", "Grab"
        )
        cursor.execute("SELECT @@IDENTITY")
        sample_id = int(cursor.fetchone()[0])

        # Lab MetaData
        cursor.execute(
            "INSERT INTO [dbo].[MetaData] "
            "([Sampling_point_ID], [Parameter_ID], [Unit_ID], [ValueType_ID], "
            "[DataProvenance_ID], [Campaign_ID], [Sample_ID], [Laboratory_ID], [AnalystPerson_ID]) "
            "VALUES (?, ?, ?, 1, 2, ?, ?, ?, ?)",
            sp_id, param_id, unit_id, campaign_id, sample_id, lab_id, analyst_id
        )
        cursor.execute("SELECT @@IDENTITY")
        lab_md_id = int(cursor.fetchone()[0])

        # Sensor MetaData (same location + parameter, provenance=Sensor)
        cursor.execute(
            "INSERT INTO [dbo].[MetaData] "
            "([Equipment_ID], [Sampling_point_ID], [Parameter_ID], [Unit_ID], [ValueType_ID], "
            "[DataProvenance_ID], [Campaign_ID]) "
            "VALUES (?, ?, ?, ?, 1, 1, ?)",
            equip_id, sp_id, param_id, unit_id, campaign_id
        )
        cursor.execute("SELECT @@IDENTITY")
        sensor_md_id = int(cursor.fetchone()[0])

        # Lab value (TSS = 24.5 mg/L)
        cursor.execute(
            "INSERT INTO [dbo].[Value] ([Metadata_ID], [Timestamp], [Value]) VALUES (?, ?, ?)",
            lab_md_id, "2025-03-15T08:30:00", 24.5
        )

        # Sensor value (TSS = 23.1)
        cursor.execute(
            "INSERT INTO [dbo].[Value] ([Metadata_ID], [Timestamp], [Value]) VALUES (?, ?, ?)",
            sensor_md_id, "2025-03-15T08:00:00", 23.1
        )

        conn.commit()

        return {
            "sp_id": sp_id,
            "param_id": param_id,
            "campaign_id": campaign_id,
            "sample_id": sample_id,
            "lab_id": lab_id,
            "analyst_id": analyst_id,
            "lab_md_id": lab_md_id,
            "sensor_md_id": sensor_md_id,
        }

    def test_lab_and_sensor_data_coexist(self, db_at_v130):
        """Both lab and sensor MetaData can exist for the same location/parameter."""
        conn, _ = db_at_v130
        ids = self._setup_scenario(conn)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM [dbo].[MetaData] "
            "WHERE [Sampling_point_ID] = ? AND [Parameter_ID] = ?",
            ids["sp_id"], ids["param_id"]
        )
        count = cursor.fetchone()[0]
        assert count >= 2  # at least lab + sensor

    def test_filter_lab_data_by_provenance(self, db_at_v130):
        """DataProvenance_ID=2 (Laboratory) returns only lab MetaData."""
        conn, _ = db_at_v130
        ids = self._setup_scenario(conn)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT [Metadata_ID] FROM [dbo].[MetaData] "
            "WHERE [Sampling_point_ID] = ? AND [DataProvenance_ID] = 2",
            ids["sp_id"]
        )
        rows = {r[0] for r in cursor.fetchall()}
        assert ids["lab_md_id"] in rows
        assert ids["sensor_md_id"] not in rows

    def test_filter_sensor_data_by_provenance(self, db_at_v130):
        """DataProvenance_ID=1 (Sensor) returns only sensor MetaData."""
        conn, _ = db_at_v130
        ids = self._setup_scenario(conn)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT [Metadata_ID] FROM [dbo].[MetaData] "
            "WHERE [Sampling_point_ID] = ? AND [DataProvenance_ID] = 1",
            ids["sp_id"]
        )
        rows = {r[0] for r in cursor.fetchall()}
        assert ids["sensor_md_id"] in rows
        assert ids["lab_md_id"] not in rows

    def test_filter_all_data_by_campaign(self, db_at_v130):
        """Campaign_ID filter returns both lab and sensor MetaData."""
        conn, _ = db_at_v130
        ids = self._setup_scenario(conn)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT [Metadata_ID] FROM [dbo].[MetaData] WHERE [Campaign_ID] = ?",
            ids["campaign_id"]
        )
        rows = {r[0] for r in cursor.fetchall()}
        assert ids["lab_md_id"] in rows
        assert ids["sensor_md_id"] in rows

    def test_lab_metadata_has_full_context(self, db_at_v130):
        """Lab MetaData row has Sample_ID, Laboratory_ID, and AnalystPerson_ID set."""
        conn, _ = db_at_v130
        ids = self._setup_scenario(conn)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT [Sample_ID], [Laboratory_ID], [AnalystPerson_ID] "
            "FROM [dbo].[MetaData] WHERE [Metadata_ID] = ?",
            ids["lab_md_id"]
        )
        row = cursor.fetchone()
        assert row[0] == ids["sample_id"]
        assert row[1] == ids["lab_id"]
        assert row[2] == ids["analyst_id"]

    def test_lab_values_retrievable(self, db_at_v130):
        """Can retrieve TSS lab value (24.5) for the lab MetaData."""
        conn, _ = db_at_v130
        ids = self._setup_scenario(conn)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT [Value] FROM [dbo].[Value] WHERE [Metadata_ID] = ?",
            ids["lab_md_id"]
        )
        values = [r[0] for r in cursor.fetchall()]
        assert len(values) == 1
        assert abs(values[0] - 24.5) < 0.001

    def test_sensor_values_retrievable(self, db_at_v130):
        """Can retrieve TSS sensor value (23.1) for the sensor MetaData."""
        conn, _ = db_at_v130
        ids = self._setup_scenario(conn)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT [Value] FROM [dbo].[Value] WHERE [Metadata_ID] = ?",
            ids["sensor_md_id"]
        )
        values = [r[0] for r in cursor.fetchall()]
        assert len(values) == 1
        assert abs(values[0] - 23.1) < 0.001


# ============================================================================
# Schema version
# ============================================================================


class TestSchemaVersionV130:
    def test_schema_version_is_130(self, db_at_v130):
        conn, _ = db_at_v130
        cursor = conn.cursor()
        cursor.execute(
            "SELECT TOP 1 [Version] FROM [dbo].[SchemaVersion] ORDER BY [VersionID] DESC"
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "1.3.0"


# ============================================================================
# Rollback: v1.3.0 → v1.2.0
# ============================================================================


class TestRollbackV130:
    def test_rollback_removes_lab_tables(self, db_at_v130):
        conn, _ = db_at_v130
        run_sql_file(conn, SQL_FILES["rollback_v1.3.0"])

        tables = get_table_names(conn)
        for t in V130_NEW_TABLES:
            assert t not in tables, f"Table {t} should be gone after rollback"

    def test_rollback_removes_metadata_lab_columns(self, db_at_v130):
        conn, _ = db_at_v130
        run_sql_file(conn, SQL_FILES["rollback_v1.3.0"])

        for col in ("Sample_ID", "Laboratory_ID", "AnalystPerson_ID"):
            assert not column_exists(conn, "MetaData", col), (
                f"MetaData.{col} should be gone after rollback"
            )

    def test_rollback_preserves_v120_tables(self, db_at_v130):
        conn, _ = db_at_v130
        run_sql_file(conn, SQL_FILES["rollback_v1.3.0"])

        tables = get_table_names(conn)
        for t in ("Person", "Campaign", "CampaignType", "DataProvenance"):
            assert t in tables, f"v1.2.0 table {t} should survive rollback to v1.2.0"

    def test_schema_version_reverted(self, db_at_v130):
        conn, _ = db_at_v130
        run_sql_file(conn, SQL_FILES["rollback_v1.3.0"])

        cursor = conn.cursor()
        cursor.execute(
            "SELECT TOP 1 [Version] FROM [dbo].[SchemaVersion] ORDER BY [VersionID] DESC"
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "1.2.0"
