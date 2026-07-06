"""Unit tests for tools.schema_migrate.render."""

import pytest

from tools.schema_migrate.diff import SchemaDiff, diff_schemas, diff_views
from tools.schema_migrate.render import (
    LOGICAL_TYPE_MAP,
    _render_create_index,
    render_column_def,
    render_column_type,
    render_migration,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _table(
    name: str,
    columns: list[dict],
    schema: str = "dbo",
    check_constraints: list[dict] | None = None,
    indexes: list[dict] | None = None,
) -> dict:
    return {
        "_format_version": "1.0",
        "table": {
            "name": name,
            "schema": schema,
            "description": f"Test {name}",
            "columns": columns,
            "primary_key": [columns[0]["name"]] if columns else [],
            "indexes": indexes or [],
            "check_constraints": check_constraints or [],
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


class TestRenderCreateIndexFilter:
    """Filtered/partial unique indexes (BUG-2: temporal active-row indexes)."""

    _tbl = _table("EquipmentLocationHistory", [_col("Equipment_ID"), _col("ValidTo")])

    def test_no_filter_has_no_where_clause(self):
        idx = {"name": "IX_X", "columns": ["Equipment_ID"], "unique": True}
        sql = _render_create_index("EquipmentLocationHistory", idx, self._tbl, "mssql")
        assert "WHERE" not in sql
        assert sql.endswith("([Equipment_ID]);")

    def test_filter_renders_where_clause_mssql(self):
        idx = {
            "name": "UQ_ELH_Active",
            "columns": ["Equipment_ID"],
            "unique": True,
            "filter": "[ValidTo] IS NULL",
        }
        sql = _render_create_index("EquipmentLocationHistory", idx, self._tbl, "mssql")
        assert sql == (
            "CREATE UNIQUE INDEX [UQ_ELH_Active] "
            "ON [dbo].[EquipmentLocationHistory] ([Equipment_ID]) "
            "WHERE [ValidTo] IS NULL;"
        )

    def test_filter_renders_where_clause_postgres(self):
        idx = {
            "name": "UQ_ELH_Active",
            "columns": ["Equipment_ID"],
            "unique": True,
            "filter": "ValidTo IS NULL",
        }
        sql = _render_create_index(
            "EquipmentLocationHistory", idx, self._tbl, "postgres"
        )
        assert sql.endswith('("Equipment_ID") WHERE ValidTo IS NULL;')


# ---------------------------------------------------------------------------
# Dropped-table + FK-before-drop ordering tests
# ---------------------------------------------------------------------------

class TestDropColumnWithCheckConstraint:
    """A CHECK constraint referencing a dropped column must be dropped first —
    real failure hit against a live server: 'CK_Annotation_Source is
    dependent on column Channel_ID'."""

    old = {
        "T": _table(
            "T", [_col("ID"), _col("A"), _col("B")],
            check_constraints=[{"name": "CK_T", "expression": "[A] IS NOT NULL OR [B] IS NOT NULL"}],
        )
    }
    new = {"T": _table("T", [_col("ID"), _col("B")])}

    def test_check_constraint_dropped_before_column(self):
        diff = diff_schemas(self.old, self.new)
        fwd, _ = render_migration(diff, self.new, "1.0.0", "1.1.0", "mssql")
        assert fwd.index("DROP CONSTRAINT [CK_T]") < fwd.index("DROP COLUMN [A]")

    def test_rollback_restores_column_before_readding_check_constraint(self):
        """Mirror bug caught against a live server: rollback re-added
        CK_Annotation_Source before Annotation.Channel_ID existed again."""
        diff = diff_schemas(self.old, self.new)
        _, rbk = render_migration(diff, self.new, "1.0.0", "1.1.0", "mssql", old_schema=self.old)
        assert rbk.index("ADD [A]") < rbk.index("ADD CONSTRAINT [CK_T]")


class TestDropColumnWithDefault:
    """Dropping a column with a DEFAULT requires dropping the (MSSQL
    auto-named) default constraint first — real failure hit against a live
    server: 'DF__AnalysisS__Proce__6B24EA82 is dependent on column'."""

    old = {"T": _table("T", [_col("ID"), _col("WithDefault", default=1)])}
    new = {"T": _table("T", [_col("ID")])}

    def test_forward_drops_default_constraint_before_column(self):
        diff = diff_schemas(self.old, self.new)
        fwd, _ = render_migration(diff, self.new, "1.0.0", "1.1.0", "mssql", old_schema=self.old)
        assert "sys.default_constraints" in fwd
        assert fwd.index("sys.default_constraints") < fwd.index("DROP COLUMN [WithDefault]")

    def test_rollback_of_added_defaulted_column_also_guards(self):
        diff = diff_schemas(self.new, self.old)  # WithDefault is now the "new" column
        # forward ADD needs no guard; but its own rollback (drop-added-column) does
        _, rbk = render_migration(diff, self.old, "1.0.0", "1.1.0", "mssql")
        assert "sys.default_constraints" in rbk


class TestDroppedTableMigration:
    """A table that's referenced by another dropped column/FK must actually
    drop (and restore), and the FK must go before the column/table it's on."""

    old = {
        "Parent": _table("Parent", [_col("Parent_ID", nullable=False)]),
        "Child": _table("Child", [
            _col("Child_ID", nullable=False),
            _col("Parent_ID", foreign_key={"table": "Parent", "column": "Parent_ID"}),
        ]),
    }
    new = {"Child": _table("Child", [_col("Child_ID", nullable=False)])}

    def test_drop_fk_precedes_drop_column_and_drop_table(self):
        diff = diff_schemas(self.old, self.new)
        fwd, _ = render_migration(diff, self.new, "1.0.0", "1.1.0", "mssql", old_schema=self.old)
        fk_pos = fwd.index("DROP CONSTRAINT")
        col_pos = fwd.index("DROP COLUMN")
        table_pos = fwd.index("DROP TABLE")
        assert fk_pos < col_pos < table_pos

    def test_table_is_actually_dropped(self):
        diff = diff_schemas(self.old, self.new)
        fwd, _ = render_migration(diff, self.new, "1.0.0", "1.1.0", "mssql", old_schema=self.old)
        assert "DROP TABLE [dbo].[Parent];" in fwd
        assert "-- DROP TABLE" not in fwd

    def test_rollback_restores_dropped_table(self):
        diff = diff_schemas(self.old, self.new)
        _, rbk = render_migration(diff, self.new, "1.0.0", "1.1.0", "mssql", old_schema=self.old)
        assert "CREATE TABLE" in rbk
        assert "[Parent]" in rbk
        assert "TODO: restore dropped table" not in rbk

    def test_without_old_schema_falls_back_to_comment(self):
        diff = diff_schemas(self.old, self.new)
        fwd, rbk = render_migration(diff, self.new, "1.0.0", "1.1.0", "mssql")
        assert "-- DROP TABLE Parent" in fwd
        assert "TODO: restore dropped table" in rbk


class TestDroppedColumnWithFkRollback:
    """Real failure hit against a live server: rollback re-added
    FK_AnalysisSeries_ProcessingKind_ID before ProcessingKind_ID existed
    again on AnalysisSeries — the FK-referencing column must be restored
    first."""

    old = {
        "Ref": _table("Ref", [_col("Ref_ID", nullable=False)]),
        "T": _table("T", [
            _col("ID", nullable=False),
            _col("Ref_ID", foreign_key={"table": "Ref", "column": "Ref_ID"}),
        ]),
    }
    new = {
        "Ref": _table("Ref", [_col("Ref_ID", nullable=False)]),
        "T": _table("T", [_col("ID", nullable=False)]),
    }

    def test_rollback_restores_column_before_readding_fk(self):
        diff = diff_schemas(self.old, self.new)
        _, rbk = render_migration(diff, self.new, "1.0.0", "1.1.0", "mssql", old_schema=self.old)
        assert rbk.index("ADD [Ref_ID]") < rbk.index("ADD CONSTRAINT")


class TestDroppedColumnWithIndexRollback:
    """Real failure hit against a live server: rollback re-created
    IX_Annotation_Channel_Time before Channel_ID existed again — an index
    covering a dropped column must wait for the column to be restored."""

    old = {
        "T": _table(
            "T", [_col("ID", nullable=False), _col("A")],
            indexes=[{"name": "IX_T_A", "columns": ["A"], "unique": False}],
        )
    }
    new = {"T": _table("T", [_col("ID", nullable=False)])}

    def test_rollback_restores_column_before_readding_index(self):
        diff = diff_schemas(self.old, self.new)
        _, rbk = render_migration(diff, self.new, "1.0.0", "1.1.0", "mssql", old_schema=self.old)
        assert rbk.index("ADD [A]") < rbk.index("CREATE INDEX [IX_T_A]")


class TestDroppedTableWithFkRollback:
    """Real failure hit against a live server: rollback re-added
    FK_AnalysisSeries_ProcessingKind_ID before the fully-dropped ProcessingKind
    table itself had been recreated — an FK to a dropped table must wait for
    the table restore, not just for column restoration."""

    old = {
        "Ref": _table("Ref", [_col("Ref_ID", nullable=False)]),
        "T": _table("T", [
            _col("ID", nullable=False),
            _col("Ref_ID", foreign_key={"table": "Ref", "column": "Ref_ID"}),
        ]),
    }
    new = {"T": _table("T", [_col("ID", nullable=False), _col("Ref_ID")])}

    def test_rollback_restores_table_before_readding_fk(self):
        diff = diff_schemas(self.old, self.new)
        _, rbk = render_migration(diff, self.new, "1.0.0", "1.1.0", "mssql", old_schema=self.old)
        assert rbk.index("CREATE TABLE") < rbk.index("ADD CONSTRAINT [FK_T_Ref_ID]")


# ---------------------------------------------------------------------------
# View migration tests
# ---------------------------------------------------------------------------

def _view(name: str, definition: str) -> dict:
    return {
        "_format_version": "1.0",
        "view": {"name": name, "schema": "dbo", "view_definition": definition},
    }


class TestViewMigration:
    old_views = {"vw_Old": _view("vw_Old", "SELECT 1 AS X")}
    new_views = {
        "vw_Old": _view("vw_Old", "SELECT 2 AS X"),
        "vw_New": _view("vw_New", "SELECT 1 AS Y"),
    }

    def _diff(self):
        diff = SchemaDiff()
        diff.new_views, diff.dropped_views, diff.altered_views = diff_views(
            self.old_views, self.new_views
        )
        return diff

    def test_forward_creates_new_and_altered_views(self):
        diff = self._diff()
        fwd, _ = render_migration(
            diff, {}, "1.0.0", "1.1.0", "mssql",
            old_views=self.old_views, new_views=self.new_views,
        )
        assert "CREATE OR ALTER VIEW [dbo].[vw_New]" in fwd
        assert "SELECT 2 AS X" in fwd  # altered definition, not the old one

    def test_rollback_restores_old_view_definition_and_drops_new(self):
        diff = self._diff()
        _, rbk = render_migration(
            diff, {}, "1.0.0", "1.1.0", "mssql",
            old_views=self.old_views, new_views=self.new_views,
        )
        assert "DROP VIEW [dbo].[vw_New];" in rbk
        assert "SELECT 1 AS X" in rbk  # restored old vw_Old definition


# ---------------------------------------------------------------------------
# Seed data + SchemaVersion footer tests
# ---------------------------------------------------------------------------

class TestSeedDataMigration:
    schema = {
        "Kind": _table("Kind", [_col("Kind_ID", nullable=False), _col("Name", "string")])
    }

    def test_forward_inserts_new_rows(self):
        diff = SchemaDiff(new_seed_rows={"Kind": [{"Kind_ID": 3, "Name": "New"}]})
        fwd, _ = render_migration(diff, self.schema, "1.0.0", "1.1.0", "mssql")
        assert "INSERT INTO [dbo].[Kind]" in fwd
        assert "N'New'" in fwd

    def test_rollback_deletes_inserted_rows(self):
        diff = SchemaDiff(new_seed_rows={"Kind": [{"Kind_ID": 3, "Name": "New"}]})
        _, rbk = render_migration(diff, self.schema, "1.0.0", "1.1.0", "mssql")
        assert "DELETE FROM [dbo].[Kind]" in rbk
        assert "[Kind_ID] IN (3)" in rbk


class TestSchemaVersionFooter:
    def test_forward_stamps_new_version(self):
        diff = SchemaDiff(new_tables=["T"])
        schema = {"T": _table("T", [_col("ID")])}
        fwd, _ = render_migration(diff, schema, "1.0.0", "1.1.0", "mssql", description="test bump")
        assert "INSERT INTO [dbo].[SchemaVersion]" in fwd
        assert "N'1.1.0'" in fwd
        assert "test bump" in fwd

    def test_rollback_removes_version_row(self):
        diff = SchemaDiff(new_tables=["T"])
        schema = {"T": _table("T", [_col("ID")])}
        _, rbk = render_migration(diff, schema, "1.0.0", "1.1.0", "mssql")
        assert "DELETE FROM [dbo].[SchemaVersion] WHERE [Version] = N'1.1.0';" in rbk
