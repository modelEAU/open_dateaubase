"""The process-unit vocabulary splits into categories, and a stage is a role."""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.schema_migrate.loader import load_schema

_TABLES_DIR = Path(__file__).parent.parent.parent / "schema_dictionary" / "tables"

_CATEGORIES = {"Structural", "Treatment", "Conveyance"}


@pytest.fixture
def schema():
    return load_schema(_TABLES_DIR)


def _cols(schema, table):
    return {c["name"]: c for c in schema[table]["table"]["columns"]}


def test_process_unit_kind_category_is_optional_and_constrained(schema):
    col = _cols(schema, "ProcessUnitKind")["Category"]
    assert col["logical_type"] == "string"
    assert col.get("nullable", True) is True
    checks = schema["ProcessUnitKind"]["table"]["check_constraints"]
    expr = next(c["expression"] for c in checks if "Category" in c["expression"])
    assert all(f"'{c}'" in expr for c in _CATEGORIES)


def test_seeded_kinds_use_only_known_categories(schema):
    seed = schema["ProcessUnitKind"]["table"]["seed_data"]
    used = {row.get("Category") for row in seed} - {None}
    assert used <= _CATEGORIES
    # Every category is populated — an empty one means the split lost a term.
    assert used == _CATEGORIES


def test_treatment_stage_seeds_the_train_in_order(schema):
    seed = schema["TreatmentStage"]["table"]["seed_data"]
    assert [row["Name"] for row in sorted(seed, key=lambda r: r["SortOrder"])] == [
        "Preliminary",
        "Primary",
        "Secondary",
        "Tertiary",
        "Sludge line",
    ]


def test_process_unit_carries_an_optional_stage(schema):
    col = _cols(schema, "ProcessUnit")["TreatmentStage_ID"]
    assert col.get("nullable", True) is True
    assert col["foreign_key"]["table"] == "TreatmentStage"


def test_person_is_active_defaults_to_active(schema):
    col = _cols(schema, "Person")["IsActive"]
    assert col["logical_type"] == "boolean"
    assert col.get("nullable", True) is False
    assert col["default"] is True
