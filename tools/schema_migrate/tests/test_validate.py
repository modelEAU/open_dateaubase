"""Unit tests for tools.schema_migrate.validate."""

import pytest

from tools.schema_migrate.validate import validate_schema


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _table(name: str, columns: list[dict], primary_key: list[str] | None = None, indexes: list | None = None) -> dict:
    return {
        "_format_version": "1.0",
        "table": {
            "name": name,
            "schema": "dbo",
            "description": f"Test {name}",
            "columns": columns,
            "primary_key": primary_key if primary_key is not None else ([columns[0]["name"]] if columns else []),
            "indexes": indexes or [],
        },
    }


def _col(name: str, logical_type: str = "integer", **kwargs) -> dict:
    base = {"name": name, "logical_type": logical_type, "nullable": True}
    base.update(kwargs)
    return base


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestValidSchema:
    def test_empty_schema_is_valid(self):
        errors = validate_schema({})
        assert errors == []

    def test_simple_schema_no_fk(self):
        schema = {
            "Unit": _table("Unit", [
                _col("UnitID", "integer", nullable=False, identity=True),
                _col("Name", "string", max_length=100, nullable=False),
            ], primary_key=["UnitID"]),
        }
        errors = validate_schema(schema)
        assert errors == []

    def test_schema_with_valid_fk(self):
        schema = {
            "Parent": _table("Parent", [_col("ParentID")], primary_key=["ParentID"]),
            "Child": _table("Child", [
                _col("ChildID"),
                {
                    "name": "ParentID",
                    "logical_type": "integer",
                    "nullable": True,
                    "foreign_key": {"table": "Parent", "column": "ParentID"},
                },
            ], primary_key=["ChildID"]),
        }
        errors = validate_schema(schema)
        assert errors == []


class TestMissingFKTable:
    def test_fk_to_nonexistent_table(self):
        schema = {
            "Child": _table("Child", [
                _col("ChildID"),
                {
                    "name": "ParentID",
                    "logical_type": "integer",
                    "nullable": True,
                    "foreign_key": {"table": "Ghost", "column": "GhostID"},
                },
            ], primary_key=["ChildID"]),
        }
        errors = validate_schema(schema)
        assert any("Ghost" in e and "does not exist" in e for e in errors)


class TestMissingFKColumn:
    def test_fk_to_nonexistent_column(self):
        schema = {
            "Parent": _table("Parent", [_col("ParentID")], primary_key=["ParentID"]),
            "Child": _table("Child", [
                _col("ChildID"),
                {
                    "name": "ForeignCol",
                    "logical_type": "integer",
                    "nullable": True,
                    "foreign_key": {"table": "Parent", "column": "NoSuchColumn"},
                },
            ], primary_key=["ChildID"]),
        }
        errors = validate_schema(schema)
        assert any("NoSuchColumn" in e for e in errors)


class TestPrimaryKeyColumnNotInColumns:
    def test_pk_column_missing(self):
        schema = {
            "T": _table("T", [_col("ID")], primary_key=["NonExistentCol"]),
        }
        errors = validate_schema(schema)
        assert any("NonExistentCol" in e for e in errors)


class TestIdentityOnNonInteger:
    def test_identity_on_text_is_invalid(self):
        schema = {
            "T": _table("T", [_col("ID", "text", identity=True)]),
        }
        errors = validate_schema(schema)
        assert any("identity" in e.lower() for e in errors)

    def test_identity_on_integer_is_valid(self):
        schema = {
            "T": _table("T", [_col("ID", "integer", identity=True)]),
        }
        errors = validate_schema(schema)
        # Only check that there's no identity error
        assert not any("identity" in e.lower() for e in errors)

    def test_identity_on_biginteger_is_valid(self):
        schema = {
            "T": _table("T", [_col("ID", "biginteger", identity=True)]),
        }
        errors = validate_schema(schema)
        assert not any("identity" in e.lower() for e in errors)


class TestStringRequiresMaxLength:
    def test_string_without_max_length(self):
        schema = {
            "T": _table("T", [_col("Name", "string")]),  # no max_length
        }
        errors = validate_schema(schema)
        assert any("max_length" in e for e in errors)

    def test_string_with_max_length_is_valid(self):
        schema = {
            "T": _table("T", [_col("Name", "string", max_length=100)]),
        }
        errors = validate_schema(schema)
        assert not any("max_length" in e for e in errors)
