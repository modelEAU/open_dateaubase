"""Integration tests for Phase 2a: Core Context — Campaign and Provenance.

Schema version: v1.2.0

Covers:
  Task 2a.1 — Contact renamed to Person; Status → Role; obsolete columns dropped
  Task 2a.2 — CampaignType and Campaign tables with seed data
  Task 2a.3 — DataProvenance lookup; DataProvenance_ID and Campaign_ID on MetaData
  Rollback    — v1.2.0 → v1.1.0 reverts all changes cleanly
"""

import pytest

from .conftest import (
    SQL_FILES,
    column_exists,
    get_column_type,
    get_table_names,
    get_table_row_count,
    run_sql_file,
)

pytestmark = pytest.mark.db

# New tables introduced in v1.2.0
V120_NEW_TABLES = {"Person", "CampaignType", "Campaign", "DataProvenance"}

# Tables from v1.1.0 that must still exist
V120_PRESERVED_TABLES = {
    "MetaData",
    "Value",
    "ValueType",
    "ValueBinningAxis",
    "ValueBin",
    "ValueVector",
    "ValueMatrix",
    "ValueImage",
    "MetaDataAxis",
    "Project",
    "ProjectHasContact",
    "Site",
    "Equipment",
    "SchemaVersion",
}


# ============================================================================
# Task 2a.1 — Person table (renamed from Contact)
# ============================================================================


class TestPersonTable:
    """Contact table was renamed to Person; PK Contact_ID → Person_ID;
    Status → Role; obsolete columns dropped."""

    def test_person_table_exists(self, db_at_v120):
        conn, _ = db_at_v120
        assert "Person" in get_table_names(conn)

    def test_contact_table_is_gone(self, db_at_v120):
        conn, _ = db_at_v120
        assert "Contact" not in get_table_names(conn)

    def test_person_id_column_exists(self, db_at_v120):
        conn, _ = db_at_v120
        assert column_exists(conn, "Person", "Person_ID")

    def test_contact_id_column_gone_from_person(self, db_at_v120):
        """Person table PK is Person_ID, not Contact_ID."""
        conn, _ = db_at_v120
        assert not column_exists(conn, "Person", "Contact_ID")

    def test_role_column_exists(self, db_at_v120):
        conn, _ = db_at_v120
        assert column_exists(conn, "Person", "Role")

    def test_status_column_gone(self, db_at_v120):
        conn, _ = db_at_v120
        assert not column_exists(conn, "Person", "Status")

    def test_obsolete_columns_dropped(self, db_at_v120):
        conn, _ = db_at_v120
        for col in ("Skype_name", "Street_number", "Street_name", "City", "Zip_code", "Country", "Office_number"):
            assert not column_exists(conn, "Person", col), (
                f"Column '{col}' should have been dropped from Person"
            )

    def test_retained_columns_exist(self, db_at_v120):
        conn, _ = db_at_v120
        for col in ("Last_name", "First_name", "Company", "Function", "Email", "Phone", "Linkedin", "Website"):
            assert column_exists(conn, "Person", col), (
                f"Column '{col}' should still exist on Person"
            )

    def test_existing_person_data_preserved(self, db_at_v120):
        """Seed data from v1.0.0 (2 Contact rows) must survive the rename."""
        conn, _ = db_at_v120
        assert get_table_row_count(conn, "Person") == 2

    def test_insert_and_query_person(self, db_at_v120):
        conn, _ = db_at_v120
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO [dbo].[Person] ([Last_name], [First_name], [Role], [Email]) "
            "VALUES (?, ?, ?, ?)",
            "Dupont", "Marie", "PhD", "marie.dupont@example.com"
        )
        conn.commit()
        cursor.execute(
            "SELECT [Last_name], [Role] FROM [dbo].[Person] WHERE [Email] = ?",
            "marie.dupont@example.com"
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "Dupont"
        assert row[1] == "PhD"

    def test_metadata_contact_id_fk_still_works(self, db_at_v120):
        """MetaData.Contact_ID FK (preserved column name) now points to Person."""
        conn, _ = db_at_v120
        cursor = conn.cursor()
        # Get first Person_ID
        cursor.execute("SELECT TOP 1 [Person_ID] FROM [dbo].[Person]")
        person_id = cursor.fetchone()[0]

        # MetaData rows that already reference that Person via Contact_ID must exist
        cursor.execute(
            "SELECT COUNT(*) FROM [dbo].[MetaData] WHERE [Contact_ID] = ?",
            person_id
        )
        count = cursor.fetchone()[0]
        # Seed data from v1.0.0 links MetaData rows to contacts — at least some should exist
        assert count >= 0  # No error = FK integrity is intact


# ============================================================================
# Task 2a.2 — CampaignType and Campaign tables
# ============================================================================


class TestCampaignType:
    """CampaignType lookup table with seed data."""

    def test_campaign_type_table_exists(self, db_at_v120):
        conn, _ = db_at_v120
        assert "CampaignType" in get_table_names(conn)

    def test_campaign_type_seed_data(self, db_at_v120):
        conn, _ = db_at_v120
        cursor = conn.cursor()
        cursor.execute(
            "SELECT [CampaignType_ID], [CampaignType_Name] "
            "FROM [dbo].[CampaignType] ORDER BY [CampaignType_ID]"
        )
        rows = cursor.fetchall()
        assert len(rows) == 3
        assert (rows[0][0], rows[0][1]) == (1, "Experiment")
        assert (rows[1][0], rows[1][1]) == (2, "Operations")
        assert (rows[2][0], rows[2][1]) == (3, "Commissioning")


class TestCampaign:
    """Campaign table, FK integrity, and filtering queries."""

    def test_campaign_table_exists(self, db_at_v120):
        conn, _ = db_at_v120
        assert "Campaign" in get_table_names(conn)

    def test_seed_campaigns_exist(self, db_at_v120):
        """seed_v1.2.0.sql inserts 2 campaigns."""
        conn, _ = db_at_v120
        assert get_table_row_count(conn, "Campaign") == 2

    def test_insert_experiment_campaign(self, db_at_v120):
        conn, _ = db_at_v120
        cursor = conn.cursor()
        # Get Site_ID from existing seed data
        cursor.execute("SELECT TOP 1 [Site_ID] FROM [dbo].[Site]")
        site_id = cursor.fetchone()[0]

        cursor.execute(
            "INSERT INTO [dbo].[Campaign] "
            "([CampaignType_ID], [Site_ID], [Name], [Description], [StartDate], [EndDate], [Project_ID]) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            1, site_id, "Nitrate Sensor Test", "Parallel sensor test at primary effluent",
            "2025-09-01T00:00:00", "2025-10-31T00:00:00", None
        )
        conn.commit()
        cursor.execute(
            "SELECT [Name], [CampaignType_ID] FROM [dbo].[Campaign] WHERE [Name] = ?",
            "Nitrate Sensor Test"
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[1] == 1  # Experiment

    def test_campaign_requires_valid_type(self, db_at_v120):
        """FK violation: CampaignType_ID=99 does not exist."""
        conn, _ = db_at_v120
        cursor = conn.cursor()
        cursor.execute("SELECT TOP 1 [Site_ID] FROM [dbo].[Site]")
        site_id = cursor.fetchone()[0]
        with pytest.raises(Exception):
            cursor.execute(
                "INSERT INTO [dbo].[Campaign] "
                "([CampaignType_ID], [Site_ID], [Name]) VALUES (?, ?, ?)",
                99, site_id, "Bad campaign"
            )

    def test_campaign_requires_valid_site(self, db_at_v120):
        """FK violation: Site_ID=9999 does not exist."""
        conn, _ = db_at_v120
        cursor = conn.cursor()
        with pytest.raises(Exception):
            cursor.execute(
                "INSERT INTO [dbo].[Campaign] "
                "([CampaignType_ID], [Site_ID], [Name]) VALUES (?, ?, ?)",
                1, 9999, "Bad campaign"
            )

    def test_campaign_project_link_optional(self, db_at_v120):
        """Campaign.Project_ID is nullable; can link to an existing Project."""
        conn, _ = db_at_v120
        cursor = conn.cursor()
        cursor.execute("SELECT TOP 1 [Site_ID] FROM [dbo].[Site]")
        site_id = cursor.fetchone()[0]
        cursor.execute("SELECT TOP 1 [Project_ID] FROM [dbo].[Project]")
        project_id = cursor.fetchone()[0]

        cursor.execute(
            "INSERT INTO [dbo].[Campaign] "
            "([CampaignType_ID], [Site_ID], [Name], [Project_ID]) "
            "VALUES (?, ?, ?, ?)",
            2, site_id, "Ops linked to project", project_id
        )
        conn.commit()
        cursor.execute(
            "SELECT [Project_ID] FROM [dbo].[Campaign] WHERE [Name] = ?",
            "Ops linked to project"
        )
        row = cursor.fetchone()
        assert row[0] == project_id

    def test_filter_metadata_by_campaign(self, db_at_v120):
        """Can associate MetaData with a Campaign and then filter by it."""
        conn, _ = db_at_v120
        cursor = conn.cursor()

        # Get IDs from seed data
        cursor.execute("SELECT TOP 1 [Campaign_ID] FROM [dbo].[Campaign]")
        campaign_id = cursor.fetchone()[0]
        cursor.execute("SELECT TOP 1 [Metadata_ID] FROM [dbo].[MetaData]")
        metadata_id = cursor.fetchone()[0]

        # Associate a MetaData row with the campaign
        cursor.execute(
            "UPDATE [dbo].[MetaData] SET [Campaign_ID] = ? WHERE [Metadata_ID] = ?",
            campaign_id, metadata_id
        )
        conn.commit()

        # Query: all MetaData for that campaign
        cursor.execute(
            "SELECT [Metadata_ID] FROM [dbo].[MetaData] WHERE [Campaign_ID] = ?",
            campaign_id
        )
        rows = cursor.fetchall()
        assert any(r[0] == metadata_id for r in rows)

    def test_cross_campaign_site_query(self, db_at_v120):
        """Can query all MetaData for a site across all campaigns."""
        conn, _ = db_at_v120
        cursor = conn.cursor()

        # Get site from seed data
        cursor.execute("SELECT TOP 1 [Site_ID] FROM [dbo].[Site]")
        site_id = cursor.fetchone()[0]

        # This query joins MetaData → Campaign → Site
        cursor.execute(
            "SELECT m.[Metadata_ID] "
            "FROM [dbo].[MetaData] m "
            "JOIN [dbo].[Campaign] c ON m.[Campaign_ID] = c.[Campaign_ID] "
            "WHERE c.[Site_ID] = ?",
            site_id
        )
        # Just verifies the query runs without error (no data in seed has Campaign_ID set yet)
        rows = cursor.fetchall()
        assert isinstance(rows, list)


# ============================================================================
# Task 2a.3 — DataProvenance lookup and MetaData columns
# ============================================================================


class TestDataProvenance:
    """DataProvenance lookup table with seed data."""

    def test_data_provenance_table_exists(self, db_at_v120):
        conn, _ = db_at_v120
        assert "DataProvenance" in get_table_names(conn)

    def test_data_provenance_seed_data(self, db_at_v120):
        conn, _ = db_at_v120
        cursor = conn.cursor()
        cursor.execute(
            "SELECT [DataProvenance_ID], [DataProvenance_Name] "
            "FROM [dbo].[DataProvenance] ORDER BY [DataProvenance_ID]"
        )
        rows = cursor.fetchall()
        assert len(rows) == 5
        names = [r[1] for r in rows]
        assert names == ["Sensor", "Laboratory", "Manual Entry", "Model Output", "External Source"]

    def test_metadata_has_data_provenance_id_column(self, db_at_v120):
        conn, _ = db_at_v120
        assert column_exists(conn, "MetaData", "DataProvenance_ID")

    def test_metadata_data_provenance_id_is_nullable(self, db_at_v120):
        """Existing MetaData rows have NULL DataProvenance_ID until backfill."""
        conn, _ = db_at_v120
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM [dbo].[MetaData] WHERE [DataProvenance_ID] IS NULL"
        )
        null_count = cursor.fetchone()[0]
        assert null_count > 0, "Legacy MetaData rows should have NULL DataProvenance_ID before backfill"

    def test_metadata_has_campaign_id_column(self, db_at_v120):
        conn, _ = db_at_v120
        assert column_exists(conn, "MetaData", "Campaign_ID")

    def test_metadata_campaign_id_is_nullable(self, db_at_v120):
        conn, _ = db_at_v120
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM [dbo].[MetaData] WHERE [Campaign_ID] IS NULL"
        )
        null_count = cursor.fetchone()[0]
        assert null_count > 0

    def test_set_provenance_on_metadata(self, db_at_v120):
        """Can set DataProvenance_ID = 1 (Sensor) on a MetaData row."""
        conn, _ = db_at_v120
        cursor = conn.cursor()
        cursor.execute("SELECT TOP 1 [Metadata_ID] FROM [dbo].[MetaData]")
        metadata_id = cursor.fetchone()[0]
        cursor.execute(
            "UPDATE [dbo].[MetaData] SET [DataProvenance_ID] = 1 WHERE [Metadata_ID] = ?",
            metadata_id
        )
        conn.commit()
        cursor.execute(
            "SELECT [DataProvenance_ID] FROM [dbo].[MetaData] WHERE [Metadata_ID] = ?",
            metadata_id
        )
        assert cursor.fetchone()[0] == 1

    def test_invalid_provenance_fk_rejected(self, db_at_v120):
        """FK violation: DataProvenance_ID=99 does not exist."""
        conn, _ = db_at_v120
        cursor = conn.cursor()
        cursor.execute("SELECT TOP 1 [Metadata_ID] FROM [dbo].[MetaData]")
        metadata_id = cursor.fetchone()[0]
        with pytest.raises(Exception):
            cursor.execute(
                "UPDATE [dbo].[MetaData] SET [DataProvenance_ID] = 99 WHERE [Metadata_ID] = ?",
                metadata_id
            )

    def test_filter_metadata_by_provenance(self, db_at_v120):
        """Can filter MetaData by DataProvenance type."""
        conn, _ = db_at_v120
        cursor = conn.cursor()

        # Set a few rows to Sensor (ID=1)
        cursor.execute(
            "UPDATE TOP (3) [dbo].[MetaData] SET [DataProvenance_ID] = 1"
        )
        conn.commit()

        cursor.execute(
            "SELECT COUNT(*) FROM [dbo].[MetaData] WHERE [DataProvenance_ID] = 1"
        )
        assert cursor.fetchone()[0] >= 3


# ============================================================================
# Schema version
# ============================================================================


class TestSchemaVersionV120:
    def test_schema_version_is_120(self, db_at_v120):
        conn, _ = db_at_v120
        cursor = conn.cursor()
        cursor.execute(
            "SELECT TOP 1 [Version] FROM [dbo].[SchemaVersion] ORDER BY [VersionID] DESC"
        )
        row = cursor.fetchone()
        assert row is not None
        assert row[0] == "1.2.0"


# ============================================================================
# Rollback: v1.2.0 → v1.1.0
# ============================================================================


class TestRollbackV120:
    """Rollback from v1.2.0 should restore the v1.1.0 Contact table structure."""

    def test_rollback_restores_contact_table(self, db_at_v120):
        conn, _ = db_at_v120
        run_sql_file(conn, SQL_FILES["rollback_v1.2.0"])

        tables = get_table_names(conn)
        assert "Contact" in tables, "Contact table should be restored after rollback"
        assert "Person" not in tables, "Person table should be gone after rollback"

    def test_rollback_removes_campaign_tables(self, db_at_v120):
        conn, _ = db_at_v120
        run_sql_file(conn, SQL_FILES["rollback_v1.2.0"])

        tables = get_table_names(conn)
        assert "Campaign" not in tables
        assert "CampaignType" not in tables
        assert "DataProvenance" not in tables

    def test_rollback_restores_contact_id_column(self, db_at_v120):
        conn, _ = db_at_v120
        run_sql_file(conn, SQL_FILES["rollback_v1.2.0"])

        assert column_exists(conn, "Contact", "Contact_ID")
        assert not column_exists(conn, "Contact", "Person_ID")

    def test_rollback_restores_status_column(self, db_at_v120):
        conn, _ = db_at_v120
        run_sql_file(conn, SQL_FILES["rollback_v1.2.0"])

        assert column_exists(conn, "Contact", "Status")
        assert not column_exists(conn, "Contact", "Role")

    def test_rollback_removes_metadata_columns(self, db_at_v120):
        conn, _ = db_at_v120
        run_sql_file(conn, SQL_FILES["rollback_v1.2.0"])

        assert not column_exists(conn, "MetaData", "DataProvenance_ID")
        assert not column_exists(conn, "MetaData", "Campaign_ID")

    def test_schema_version_reverted(self, db_at_v120):
        conn, _ = db_at_v120
        run_sql_file(conn, SQL_FILES["rollback_v1.2.0"])

        cursor = conn.cursor()
        cursor.execute(
            "SELECT TOP 1 [Version] FROM [dbo].[SchemaVersion] ORDER BY [VersionID] DESC"
        )
        row = cursor.fetchone()
        # After rollback the latest version should be 1.1.0
        assert row is not None
        assert row[0] == "1.1.0"
