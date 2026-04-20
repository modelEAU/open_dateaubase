"""Integration tests for ProcessUnit hierarchy (Issue #23).

Tests run against a live MSSQL container at the v3.0.0 schema + process unit migration.
Skipped automatically when the container is unavailable.

Covers:
  - ProcessUnitType: CRUD operations
  - ProcessUnit: CRUD operations, 3-level hierarchy tree
  - Deletion guard: blocks delete when child units exist
  - Deletion guard: blocks delete when SamplingPoint linked
  - SamplingPoint: ProcessUnit_ID FK stored and returned
"""

from __future__ import annotations

from pathlib import Path

import pytest

from .conftest import fresh_db, mssql_engine, run_sql_file  # noqa: F401
from api.v1.repositories import process_unit_repository, site_repository

PROJECT_ROOT = Path(__file__).parent.parent.parent
MIGRATIONS_DIR = PROJECT_ROOT / "migrations"

pytestmark = pytest.mark.db


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def db(fresh_db):
    """Database at v3.0.0 + process unit migration with a seed Site."""
    conn, db_name = fresh_db
    run_sql_file(conn, MIGRATIONS_DIR / "v1.0.0_create_mssql.sql")
    run_sql_file(conn, MIGRATIONS_DIR / "v1.0.0_to_v3.0.0_mssql.sql")
    run_sql_file(conn, MIGRATIONS_DIR / "v3.0.0_add_site_type_mssql.sql")
    run_sql_file(conn, MIGRATIONS_DIR / "v3.0.0_add_process_unit.sql")

    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO [dbo].[Site] ([Name]) OUTPUT INSERTED.[Site_ID] VALUES (?)",
        "Test WWTP",
    )
    site_id = cursor.fetchone()[0]
    conn.commit()

    yield conn, db_name, site_id


# ---------------------------------------------------------------------------
# ProcessUnitType
# ---------------------------------------------------------------------------


class TestProcessUnitTypeCRUD:
    def test_insert_and_retrieve(self, db):
        conn, _, _ = db
        result = process_unit_repository.insert_process_unit_type(conn, "Fermenter", None)
        assert result["name"] == "Fermenter"
        assert result["id"] > 0

    def test_list_includes_seeded_types(self, db):
        conn, _, _ = db
        types = process_unit_repository.get_all_process_unit_types(conn)
        names = {t["name"] for t in types}
        assert {"Reactor", "Pipe", "Clarifier"}.issubset(names)

    def test_update_type(self, db):
        conn, _, _ = db
        created = process_unit_repository.insert_process_unit_type(conn, "OldName", None)
        updated = process_unit_repository.update_process_unit_type(
            conn, created["id"], "NewName", "A description"
        )
        assert updated is not None
        assert updated["name"] == "NewName"
        assert updated["description"] == "A description"

    def test_update_missing_returns_none(self, db):
        conn, _, _ = db
        result = process_unit_repository.update_process_unit_type(conn, 99999, "X", None)
        assert result is None

    def test_delete_type(self, db):
        conn, _, _ = db
        created = process_unit_repository.insert_process_unit_type(conn, "ToDelete", None)
        assert process_unit_repository.delete_process_unit_type(conn, created["id"]) is True
        assert process_unit_repository.delete_process_unit_type(conn, created["id"]) is False


# ---------------------------------------------------------------------------
# ProcessUnit CRUD
# ---------------------------------------------------------------------------


class TestProcessUnitCRUD:
    def test_insert_and_retrieve(self, db):
        conn, _, site_id = db
        unit = process_unit_repository.insert_process_unit(
            conn, {"site_id": site_id, "tag": "R-210", "name": "Réacteur R-210"}
        )
        assert unit["tag"] == "R-210"
        assert unit["site_id"] == site_id
        assert unit["parent_id"] is None

    def test_list_by_site(self, db):
        conn, _, site_id = db
        process_unit_repository.insert_process_unit(
            conn, {"site_id": site_id, "tag": "R-220", "name": "Réacteur R-220"}
        )
        units = process_unit_repository.get_all_process_units(conn, site_id=site_id)
        tags = {u["tag"] for u in units}
        assert "R-220" in tags

    def test_get_by_id_missing_returns_none(self, db):
        conn, _, _ = db
        assert process_unit_repository.get_process_unit_by_id(conn, 99999) is None

    def test_update_unit(self, db):
        conn, _, site_id = db
        unit = process_unit_repository.insert_process_unit(
            conn, {"site_id": site_id, "tag": "U-001", "name": "Original"}
        )
        updated = process_unit_repository.update_process_unit(
            conn,
            unit["id"],
            {"site_id": site_id, "tag": "U-001", "name": "Updated", "description": "Desc"},
        )
        assert updated is not None
        assert updated["name"] == "Updated"
        assert updated["description"] == "Desc"

    def test_patch_unit(self, db):
        conn, _, site_id = db
        unit = process_unit_repository.insert_process_unit(
            conn, {"site_id": site_id, "tag": "P-001", "name": "Before"}
        )
        patched = process_unit_repository.patch_process_unit(
            conn, unit["id"], {"name": "After"}
        )
        assert patched is not None
        assert patched["name"] == "After"
        assert patched["tag"] == "P-001"

    def test_delete_unit(self, db):
        conn, _, site_id = db
        unit = process_unit_repository.insert_process_unit(
            conn, {"site_id": site_id, "tag": "DEL-001", "name": "To Delete"}
        )
        assert process_unit_repository.delete_process_unit(conn, unit["id"]) is True
        assert process_unit_repository.get_process_unit_by_id(conn, unit["id"]) is None

    def test_unique_tag_per_site_enforced(self, db):
        conn, _, site_id = db
        process_unit_repository.insert_process_unit(
            conn, {"site_id": site_id, "tag": "DUP-001", "name": "First"}
        )
        with pytest.raises(Exception):
            process_unit_repository.insert_process_unit(
                conn, {"site_id": site_id, "tag": "DUP-001", "name": "Duplicate"}
            )


# ---------------------------------------------------------------------------
# Hierarchy tree
# ---------------------------------------------------------------------------


class TestProcessUnitTree:
    def test_three_level_hierarchy(self, db):
        """Area → Reactor → Zone returns correct tree shape."""
        conn, _, site_id = db

        area = process_unit_repository.insert_process_unit(
            conn, {"site_id": site_id, "tag": "BR1", "name": "Ligne Bio 1"}
        )
        reactor = process_unit_repository.insert_process_unit(
            conn, {"site_id": site_id, "tag": "R-230", "name": "Réacteur R-230", "parent_id": area["id"]}
        )
        zone = process_unit_repository.insert_process_unit(
            conn, {"site_id": site_id, "tag": "Z-230A", "name": "Zone aération", "parent_id": reactor["id"]}
        )

        tree = process_unit_repository.get_process_unit_tree(conn, site_id)
        area_nodes = [n for n in tree if n["tag"] == "BR1"]
        assert len(area_nodes) == 1, "Area should be a root"

        reactors = area_nodes[0]["children"]
        assert any(n["tag"] == "R-230" for n in reactors)

        reactor_node = next(n for n in reactors if n["tag"] == "R-230")
        zones = reactor_node["children"]
        assert any(n["tag"] == "Z-230A" for n in zones)

    def test_lookup_returns_expected_fields(self, db):
        conn, _, site_id = db
        process_unit_repository.insert_process_unit(
            conn, {"site_id": site_id, "tag": "LKP-001", "name": "Lookup Test"}
        )
        lookup = process_unit_repository.get_process_units_lookup(conn, site_id=site_id)
        assert all({"id", "name", "tag", "site_id"}.issubset(u.keys()) for u in lookup)


# ---------------------------------------------------------------------------
# Deletion guard
# ---------------------------------------------------------------------------


class TestDeletionGuard:
    def test_blocks_delete_when_children_exist(self, db):
        conn, _, site_id = db
        parent = process_unit_repository.insert_process_unit(
            conn, {"site_id": site_id, "tag": "PARENT-G", "name": "Parent"}
        )
        process_unit_repository.insert_process_unit(
            conn, {"site_id": site_id, "tag": "CHILD-G", "name": "Child", "parent_id": parent["id"]}
        )
        with pytest.raises(ValueError, match="child unit"):
            process_unit_repository.delete_process_unit(conn, parent["id"])

    def test_blocks_delete_when_sampling_point_linked(self, db):
        conn, _, site_id = db
        unit = process_unit_repository.insert_process_unit(
            conn, {"site_id": site_id, "tag": "SP-GUARD", "name": "Unit with SP"}
        )
        # Create a SamplingPoint linked to this unit
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO [dbo].[SamplingPoint] ([Site_ID], [SamplingPoint], [ProcessUnit_ID])"
            " VALUES (?, ?, ?)",
            site_id,
            "SP at unit",
            unit["id"],
        )
        conn.commit()

        with pytest.raises(ValueError, match="sampling point"):
            process_unit_repository.delete_process_unit(conn, unit["id"])


# ---------------------------------------------------------------------------
# SamplingPoint ProcessUnit_ID FK
# ---------------------------------------------------------------------------


class TestSamplingPointProcessUnitFK:
    def test_process_unit_id_stored_and_returned(self, db):
        conn, _, site_id = db
        unit = process_unit_repository.insert_process_unit(
            conn, {"site_id": site_id, "tag": "SP-FK-TEST", "name": "Unit for SP"}
        )
        sp = site_repository.insert_sampling_location(
            conn,
            site_id,
            {"name": "SP linked to unit", "process_unit_id": unit["id"]},
        )
        assert sp["process_unit_id"] == unit["id"]

    def test_process_unit_id_nullable(self, db):
        conn, _, site_id = db
        sp = site_repository.insert_sampling_location(
            conn, site_id, {"name": "SP no unit"}
        )
        assert sp["process_unit_id"] is None
