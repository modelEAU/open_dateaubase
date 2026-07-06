"""Unit tests for tools.schema_migrate.diff."""

import pytest

from tools.schema_migrate.diff import diff_schemas, diff_seed_data, SchemaDiff


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _table(
    name: str,
    columns: list[dict],
    indexes: list | None = None,
    seed_data: list[dict] | None = None,
    unique_constraints: list[dict] | None = None,
    check_constraints: list[dict] | None = None,
) -> dict:
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
            "seed_data": seed_data or [],
            "unique_constraints": unique_constraints or [],
            "check_constraints": check_constraints or [],
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


class TestForeignKeys:
    def test_new_fk_detected(self):
        old = {
            "Parent": _table("Parent", [_col("Parent_ID")]),
            "Child": _table("Child", [_col("Child_ID")]),
        }
        new = {
            "Parent": _table("Parent", [_col("Parent_ID")]),
            "Child": _table("Child", [
                _col("Child_ID"),
                _col("Parent_ID", foreign_key={"table": "Parent", "column": "Parent_ID"}),
            ]),
        }
        diff = diff_schemas(old, new)
        assert "Child" in diff.new_fks
        assert diff.dropped_fks == {}

    def test_repointed_fk_same_column_name_is_drop_and_add(self):
        """A re-pointed FK (same child column, different target) must not be
        silently missed just because the column name didn't change — this is
        exactly the Channel_ID -> Channel.Stream_ID supertype repoint case."""
        old = {
            "Channel": _table("Channel", [_col("Channel_ID")]),
            "Stream": _table("Stream", [_col("Stream_ID")]),
            "Obs": _table("Obs", [
                _col("Obs_ID"),
                _col("Channel_ID", foreign_key={"table": "Channel", "column": "Channel_ID"}),
            ]),
        }
        new = {
            "Channel": _table("Channel", [_col("Stream_ID")]),
            "Stream": _table("Stream", [_col("Stream_ID")]),
            "Obs": _table("Obs", [
                _col("Obs_ID"),
                _col("Channel_ID", foreign_key={"table": "Channel", "column": "Stream_ID"}),
            ]),
        }
        diff = diff_schemas(old, new)
        assert diff.dropped_fks["Obs"][0]["ref_column"] == "Channel_ID"
        assert diff.new_fks["Obs"][0]["ref_column"] == "Stream_ID"

    def test_unchanged_fk_not_in_diff(self):
        fk = {"table": "Parent", "column": "Parent_ID"}
        old = {
            "Parent": _table("Parent", [_col("Parent_ID")]),
            "Child": _table("Child", [_col("Child_ID"), _col("Parent_ID", foreign_key=fk)]),
        }
        new = {
            "Parent": _table("Parent", [_col("Parent_ID")]),
            "Child": _table("Child", [_col("Child_ID"), _col("Parent_ID", foreign_key=dict(fk))]),
        }
        diff = diff_schemas(old, new)
        assert diff.new_fks == {}
        assert diff.dropped_fks == {}


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


class TestUniqueConstraints:
    def test_new_unique_constraint_detected(self):
        old = {"T": _table("T", [_col("ID"), _col("A")])}
        new = {
            "T": _table(
                "T", [_col("ID"), _col("A")],
                unique_constraints=[{"name": "UQ_T_A", "columns": ["A"]}],
            )
        }
        diff = diff_schemas(old, new)
        assert "T" in diff.new_unique_constraints
        assert diff.dropped_unique_constraints == {}

    def test_changed_column_list_is_drop_and_add(self):
        old = {
            "T": _table(
                "T", [_col("ID"), _col("A"), _col("B")],
                unique_constraints=[{"name": "UQ_T", "columns": ["A", "B"]}],
            )
        }
        new = {
            "T": _table(
                "T", [_col("ID"), _col("A"), _col("B")],
                unique_constraints=[{"name": "UQ_T", "columns": ["A"]}],
            )
        }
        diff = diff_schemas(old, new)
        assert diff.new_unique_constraints["T"][0]["columns"] == ["A"]
        assert diff.dropped_unique_constraints["T"][0]["columns"] == ["A", "B"]

    def test_unchanged_constraint_not_in_diff(self):
        uq = [{"name": "UQ_T", "columns": ["A"]}]
        old = {"T": _table("T", [_col("ID"), _col("A")], unique_constraints=uq)}
        new = {"T": _table("T", [_col("ID"), _col("A")], unique_constraints=uq)}
        diff = diff_schemas(old, new)
        assert diff.new_unique_constraints == {}
        assert diff.dropped_unique_constraints == {}


class TestCheckConstraints:
    """Real failure hit against a live server: dropping Annotation.Channel_ID
    while CK_Annotation_Source still referenced it ('is dependent on column')."""

    def test_dropped_check_constraint_detected(self):
        ck = [{"name": "CK_T", "expression": "[A] IS NOT NULL"}]
        old = {"T": _table("T", [_col("ID"), _col("A")], check_constraints=ck)}
        new = {"T": _table("T", [_col("ID"), _col("A")])}
        diff = diff_schemas(old, new)
        assert diff.dropped_check_constraints["T"][0]["name"] == "CK_T"
        assert diff.new_check_constraints == {}

    def test_changed_expression_is_drop_and_add(self):
        old = {
            "T": _table(
                "T", [_col("ID"), _col("A")],
                check_constraints=[{"name": "CK_T", "expression": "[A] > 0"}],
            )
        }
        new = {
            "T": _table(
                "T", [_col("ID"), _col("A")],
                check_constraints=[{"name": "CK_T", "expression": "[A] >= 0"}],
            )
        }
        diff = diff_schemas(old, new)
        assert diff.new_check_constraints["T"][0]["expression"] == "[A] >= 0"
        assert diff.dropped_check_constraints["T"][0]["expression"] == "[A] > 0"

    def test_unchanged_constraint_not_in_diff(self):
        ck = [{"name": "CK_T", "expression": "[A] > 0"}]
        old = {"T": _table("T", [_col("ID"), _col("A")], check_constraints=ck)}
        new = {"T": _table("T", [_col("ID"), _col("A")], check_constraints=ck)}
        diff = diff_schemas(old, new)
        assert diff.new_check_constraints == {}
        assert diff.dropped_check_constraints == {}


class TestDiffSeedData:
    def test_new_table_seed_rows_are_all_new(self):
        old: dict[str, dict] = {}
        new = {
            "Kind": _table(
                "Kind", [_col("Kind_ID")],
                seed_data=[{"Kind_ID": 1, "Name": "A"}, {"Kind_ID": 2, "Name": "B"}],
            )
        }
        new_rows, dropped_rows = diff_seed_data(old, new)
        assert len(new_rows["Kind"]) == 2
        assert dropped_rows == {}

    def test_added_row_on_existing_table(self):
        old = {"Kind": _table("Kind", [_col("Kind_ID")], seed_data=[{"Kind_ID": 1, "Name": "A"}])}
        new = {
            "Kind": _table(
                "Kind", [_col("Kind_ID")],
                seed_data=[{"Kind_ID": 1, "Name": "A"}, {"Kind_ID": 2, "Name": "B"}],
            )
        }
        new_rows, dropped_rows = diff_seed_data(old, new)
        assert new_rows["Kind"] == [{"Kind_ID": 2, "Name": "B"}]
        assert dropped_rows == {}

    def test_removed_row_on_existing_table(self):
        old = {
            "Kind": _table(
                "Kind", [_col("Kind_ID")],
                seed_data=[{"Kind_ID": 1, "Name": "A"}, {"Kind_ID": 2, "Name": "B"}],
            )
        }
        new = {"Kind": _table("Kind", [_col("Kind_ID")], seed_data=[{"Kind_ID": 1, "Name": "A"}])}
        new_rows, dropped_rows = diff_seed_data(old, new)
        assert dropped_rows["Kind"] == [{"Kind_ID": 2, "Name": "B"}]
        assert new_rows == {}

    def test_dropped_table_seed_rows_are_all_dropped(self):
        old = {"Gone": _table("Gone", [_col("Gone_ID")], seed_data=[{"Gone_ID": 1, "Name": "X"}])}
        new: dict[str, dict] = {}
        new_rows, dropped_rows = diff_seed_data(old, new)
        assert dropped_rows["Gone"] == [{"Gone_ID": 1, "Name": "X"}]
        assert new_rows == {}

    def test_no_seed_data_produces_empty_diff(self):
        old = {"T": _table("T", [_col("ID")])}
        new = {"T": _table("T", [_col("ID")])}
        new_rows, dropped_rows = diff_seed_data(old, new)
        assert new_rows == {}
        assert dropped_rows == {}
