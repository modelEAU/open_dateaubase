"""Unit tests for tools.schema_migrate.diff."""

import pytest

from tools.schema_migrate.diff import diff_schemas, SchemaDiff


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _table(name: str, columns: list[dict], indexes: list | None = None) -> dict:
    """Build a minimal schema YAML dict for a single table."""
    return {
        "_format_version": "1.0",
        "table": {
            "name": name,
            "schema": "dbo",
            "description": f"Test table {name}",
            "columns": columns,
            "primary_key": [columns[0]["name"]] if columns else [],
            "indexes": indexes or [],
        },
    }


def _col(name: str, logical_type: str = "integer", **kwargs) -> dict:
    return {"name": name, "logical_type": logical_type, "nullable": True, **kwargs}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAddTable:
    def test_new_table_detected(self):
        old: dict[str, dict] = {}
        new = {"MyTable": _table("MyTable", [_col("ID")])}
        diff = diff_schemas(old, new)
        assert "MyTable" in diff.new_tables
        assert diff.dropped_tables == []

    def test_no_dropped_when_only_adding(self):
        old = {"Existing": _table("Existing", [_col("ID")])}
        new = {
            "Existing": _table("Existing", [_col("ID")]),
            "NewOne": _table("NewOne", [_col("ID")]),
        }
        diff = diff_schemas(old, new)
        assert "NewOne" in diff.new_tables
        assert diff.dropped_tables == []


class TestDropTable:
    def test_dropped_table_detected(self):
        old = {"Gone": _table("Gone", [_col("ID")])}
        new: dict[str, dict] = {}
        diff = diff_schemas(old, new)
        assert "Gone" in diff.dropped_tables
        assert diff.new_tables == []

    def test_remaining_table_not_in_dropped(self):
        old = {
            "Stays": _table("Stays", [_col("ID")]),
            "Gone": _table("Gone", [_col("ID")]),
        }
        new = {"Stays": _table("Stays", [_col("ID")])}
        diff = diff_schemas(old, new)
        assert "Gone" in diff.dropped_tables
        assert "Stays" not in diff.dropped_tables


class TestAddColumn:
    def test_new_column_detected(self):
        old = {"T": _table("T", [_col("ID")])}
        new = {"T": _table("T", [_col("ID"), _col("NewCol", "text")])}
        diff = diff_schemas(old, new)
        assert "T" in diff.new_columns
        assert any(c["name"] == "NewCol" for c in diff.new_columns["T"])

    def test_existing_column_not_in_new_columns(self):
        old = {"T": _table("T", [_col("ID"), _col("Existing")])}
        new = {"T": _table("T", [_col("ID"), _col("Existing"), _col("Brand")])}
        diff = diff_schemas(old, new)
        assert all(c["name"] != "Existing" for c in diff.new_columns.get("T", []))


class TestDropColumn:
    def test_dropped_column_detected(self):
        old = {"T": _table("T", [_col("ID"), _col("ToRemove")])}
        new = {"T": _table("T", [_col("ID")])}
        diff = diff_schemas(old, new)
        assert "T" in diff.dropped_columns
        assert "ToRemove" in diff.dropped_columns["T"]

    def test_kept_column_not_in_dropped(self):
        old = {"T": _table("T", [_col("ID"), _col("Keep"), _col("Drop")])}
        new = {"T": _table("T", [_col("ID"), _col("Keep")])}
        diff = diff_schemas(old, new)
        assert "Keep" not in diff.dropped_columns.get("T", [])


class TestAlterColumn:
    def test_type_change_detected(self):
        old = {"T": _table("T", [_col("ID"), _col("Col", "integer")])}
        new = {"T": _table("T", [_col("ID"), _col("Col", "biginteger")])}
        diff = diff_schemas(old, new)
        assert "T" in diff.altered_columns
        alts = diff.altered_columns["T"]
        assert len(alts) == 1
        assert alts[0]["column"] == "Col"
        assert alts[0]["old"]["logical_type"] == "integer"
        assert alts[0]["new"]["logical_type"] == "biginteger"

    def test_nullable_change_detected(self):
        old = {"T": _table("T", [_col("ID"), {"name": "Col", "logical_type": "integer", "nullable": True}])}
        new = {"T": _table("T", [_col("ID"), {"name": "Col", "logical_type": "integer", "nullable": False}])}
        diff = diff_schemas(old, new)
        assert "T" in diff.altered_columns


class TestNoChanges:
    def test_identical_schemas_produce_empty_diff(self):
        schema = {
            "A": _table("A", [_col("ID"), _col("Name", "text")]),
            "B": _table("B", [_col("ID")]),
        }
        diff = diff_schemas(schema, schema)
        assert diff.is_empty()

    def test_is_empty_returns_true(self):
        diff = SchemaDiff()
        assert diff.is_empty()

    def test_is_empty_returns_false_when_new_table(self):
        diff = SchemaDiff(new_tables=["X"])
        assert not diff.is_empty()
