"""Unit tests for tools.schema_migrate.render."""

import pytest

from tools.schema_migrate.diff import SchemaDiff, diff_schemas
from tools.schema_migrate.render import (
    LOGICAL_TYPE_MAP,
    render_column_def,
    render_column_type,
    render_migration,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _table(name: str, columns: list[dict], schema: str = "dbo") -> dict:
    return {
        "_format_version": "1.0",
        "table": {
            "name": name,
            "schema": schema,
            "description": f"Test {name}",
            "columns": columns,
            "primary_key": [columns[0]["name"]] if columns else [],
            "indexes": [],
            "check_constraints": [],
        },
    }


def _col(name: str, logical_type: str = "integer", **kwargs) -> dict:
    return {"name": name, "logical_type": logical_type, "nullable": True, **kwargs}


# ---------------------------------------------------------------------------
# Type mapping tests
# ---------------------------------------------------------------------------

class TestMSSQLTypeMapping:
    def test_integer(self):
        assert render_column_type(_col("X", "integer"), "mssql") == "INT"

    def test_biginteger(self):
        assert render_column_type(_col("X", "biginteger"), "mssql") == "BIGINT"

    def test_float64(self):
        assert render_column_type(_col("X", "float64"), "mssql") == "FLOAT"

    def test_text(self):
        assert render_column_type(_col("X", "text"), "mssql") == "NVARCHAR(MAX)"

    def test_boolean(self):
        assert render_column_type(_col("X", "boolean"), "mssql") == "BIT"

    def test_string_with_length(self):
        col = _col("X", "string", max_length=255)
        assert render_column_type(col, "mssql") == "NVARCHAR(255)"

    def test_string_max(self):
        col = _col("X", "string", max_length="max")
        assert render_column_type(col, "mssql") == "NVARCHAR(MAX)"

    def test_decimal_with_precision_scale(self):
        col = _col("X", "decimal", precision=10, scale=2)
        assert render_column_type(col, "mssql") == "NUMERIC(10,2)"

    def test_timestamp_with_precision(self):
        col = _col("X", "timestamp", precision=3)
        assert render_column_type(col, "mssql") == "DATETIME2(3)"

    def test_timestamp_default(self):
        col = _col("X", "timestamp")
        assert render_column_type(col, "mssql") == "DATETIME2"

    def test_timestamptz_with_precision(self):
        col = _col("X", "timestamptz", precision=7)
        assert render_column_type(col, "mssql") == "DATETIMEOFFSET(7)"

    def test_timestamptz_default(self):
        col = _col("X", "timestamptz")
        assert render_column_type(col, "mssql") == "DATETIMEOFFSET"


class TestPostgresTypeMapping:
    def test_integer(self):
        assert render_column_type(_col("X", "integer"), "postgres") == "INTEGER"

    def test_float64(self):
        assert render_column_type(_col("X", "float64"), "postgres") == "DOUBLE PRECISION"

    def test_text(self):
        assert render_column_type(_col("X", "text"), "postgres") == "TEXT"

    def test_boolean(self):
        assert render_column_type(_col("X", "boolean"), "postgres") == "BOOLEAN"

    def test_string_with_length(self):
        col = _col("X", "string", max_length=100)
        assert render_column_type(col, "postgres") == "VARCHAR(100)"

    def test_binary_large(self):
        assert render_column_type(_col("X", "binary_large"), "postgres") == "BYTEA"

    def test_timestamptz_with_precision(self):
        col = _col("X", "timestamptz", precision=7)
        assert render_column_type(col, "postgres") == "TIMESTAMPTZ(7)"

    def test_timestamptz_default(self):
        col = _col("X", "timestamptz")
        assert render_column_type(col, "postgres") == "TIMESTAMPTZ"


# ---------------------------------------------------------------------------
# Column definition tests
# ---------------------------------------------------------------------------

class TestRenderColumnDef:
    def test_simple_not_null(self):
        col = {"name": "ID", "logical_type": "integer", "nullable": False}
        result = render_column_def(col, "mssql")
        assert result == "[ID] INT NOT NULL"

    def test_nullable(self):
        col = {"name": "Val", "logical_type": "float64", "nullable": True}
        result = render_column_def(col, "mssql")
        assert "NOT NULL" not in result

    def test_identity_mssql(self):
        col = {"name": "ID", "logical_type": "integer", "nullable": False, "identity": True}
        result = render_column_def(col, "mssql")
        assert "IDENTITY(1,1)" in result

    def test_identity_postgres_uses_serial(self):
        col = {"name": "ID", "logical_type": "integer", "nullable": False, "identity": True}
        result = render_column_def(col, "postgres")
        assert "SERIAL" in result

    def test_default_value(self):
        col = {"name": "Cnt", "logical_type": "integer", "nullable": True, "default": 0}
        result = render_column_def(col, "mssql")
        assert "DEFAULT 0" in result

    def test_default_current_timestamp(self):
        col = {"name": "CreatedAt", "logical_type": "timestamp", "nullable": False, "default": "CURRENT_TIMESTAMP"}
        result = render_column_def(col, "mssql")
        assert "DEFAULT CURRENT_TIMESTAMP" in result

    def test_default_current_timestamp_timestamptz_mssql(self):
        col = {"name": "CreatedAt", "logical_type": "timestamptz", "precision": 7, "nullable": False, "default": "CURRENT_TIMESTAMP"}
        result = render_column_def(col, "mssql")
        assert "SYSDATETIMEOFFSET()" in result
        assert "DATETIMEOFFSET(7)" in result

    def test_default_current_timestamp_timestamptz_postgres(self):
        col = {"name": "CreatedAt", "logical_type": "timestamptz", "precision": 7, "nullable": False, "default": "CURRENT_TIMESTAMP"}
        result = render_column_def(col, "postgres")
        assert "DEFAULT CURRENT_TIMESTAMP" in result
        assert "TIMESTAMPTZ(7)" in result

    def test_postgres_quoting(self):
        col = {"name": "MyCol", "logical_type": "integer", "nullable": True}
        result = render_column_def(col, "postgres")
        assert result.startswith('"MyCol"')


# ---------------------------------------------------------------------------
# CREATE TABLE test
# ---------------------------------------------------------------------------

class TestRenderCreateTable:
    def test_create_table_contains_table_name(self):
        schema = {
            "Unit": _table("Unit", [
                {"name": "UnitID", "logical_type": "integer", "nullable": False, "identity": True},
                {"name": "Unit", "logical_type": "string", "max_length": 100, "nullable": False},
            ])
        }
        diff = diff_schemas({}, schema)
        migration_sql, _ = render_migration(diff, schema, "0.0.0", "1.0.0", "mssql")
        assert "CREATE TABLE" in migration_sql
        assert "[Unit]" in migration_sql

    def test_create_table_has_primary_key(self):
        schema = {
            "T": _table("T", [_col("ID", "integer", nullable=False)])
        }
        diff = diff_schemas({}, schema)
        migration_sql, _ = render_migration(diff, schema, "0.0.0", "1.0.0", "mssql")
        assert "PRIMARY KEY" in migration_sql


# ---------------------------------------------------------------------------
# ADD COLUMN test
# ---------------------------------------------------------------------------

class TestRenderAddColumn:
    def test_add_column_statement(self):
        old = {"T": _table("T", [_col("ID")])}
        new = {"T": _table("T", [_col("ID"), _col("NewCol", "text")])}
        diff = diff_schemas(old, new)
        migration_sql, rollback_sql = render_migration(diff, new, "1.0.0", "1.0.1", "mssql")
        assert "ADD" in migration_sql
        assert "NewCol" in migration_sql

    def test_rollback_drops_added_column(self):
        old = {"T": _table("T", [_col("ID")])}
        new = {"T": _table("T", [_col("ID"), _col("NewCol", "text")])}
        diff = diff_schemas(old, new)
        _, rollback_sql = render_migration(diff, new, "1.0.0", "1.0.1", "mssql")
        assert "DROP COLUMN" in rollback_sql
        assert "NewCol" in rollback_sql


# ---------------------------------------------------------------------------
# Header comment test
# ---------------------------------------------------------------------------

class TestMigrationHeader:
    def test_header_contains_versions(self):
        schema = {"T": _table("T", [_col("ID")])}
        diff = diff_schemas({}, schema)
        migration_sql, _ = render_migration(diff, schema, "1.0.0", "1.0.1", "mssql")
        assert "1.0.0" in migration_sql
        assert "1.0.1" in migration_sql

    def test_header_contains_platform(self):
        schema = {"T": _table("T", [_col("ID")])}
        diff = diff_schemas({}, schema)
        migration_sql, _ = render_migration(diff, schema, "1.0.0", "1.0.1", "postgres")
        assert "postgres" in migration_sql

    def test_rollback_header_present(self):
        schema = {"T": _table("T", [_col("ID")])}
        diff = diff_schemas({}, schema)
        _, rollback_sql = render_migration(diff, schema, "1.0.0", "1.0.1", "mssql")
        assert "ROLLBACK" in rollback_sql.upper() or "rollback" in rollback_sql
