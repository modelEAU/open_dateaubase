"""Unit tests for PRD-2 S1: Event + EventKind YAML schema.

Red→green: these tests fail on the old EquipmentEvent/EquipmentEventKind schema
and pass only after the rename + 8-FK exclusive-arc change.

Validates:
- Event table exists (EquipmentEvent is gone)
- EventKind table exists (EquipmentEventKind is gone)
- Event has all 8 exclusive-arc FK columns (all nullable)
- Event carries a CHECK constraint CK_Event_ExclusiveArc
- EventKind seed vocab contains all PRD-required kinds
- Schema validator reports no errors (FK refs resolved)
- Generated DDL contains the Event CREATE TABLE and CHECK constraint
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
TABLES_DIR = REPO_ROOT / "schema_dictionary" / "tables"
VIEWS_DIR = REPO_ROOT / "schema_dictionary" / "views"
VERSION_YAML = REPO_ROOT / "schema_dictionary" / "version.yaml"

# 8 FK columns in the exclusive arc (per ADR-0006 and PRD-2)
ARC_COLUMNS = [
    "Channel_ID",
    "Equipment_ID",
    "SignalInterface_ID",
    "DataAcquisitionSystem_ID",
    "SamplingPoint_ID",
    "ProcessUnit_ID",
    "Site_ID",
    "Campaign_ID",
]

# EventKind vocab required by the PRD (subset assertion — users can add more)
REQUIRED_EVENT_KINDS = {
    "Calibration",
    "Cleaning",
    "Repair",
    "Validation",
    "PowerOutage",
    "ControllerCrash",
    "OperationalChange",
}


def _load_schema() -> dict:
    from tools.schema_migrate.loader import load_schema

    return load_schema(TABLES_DIR)


# ---------------------------------------------------------------------------
# Test 1: EquipmentEvent is gone; Event exists
# ---------------------------------------------------------------------------


def test_event_table_exists_equipment_event_gone() -> None:
    """Event table must exist; EquipmentEvent must NOT exist after the rename."""
    schema = _load_schema()
    assert "Event" in schema, "Event table not found in schema — rename not applied"
    assert "EquipmentEvent" not in schema, (
        "EquipmentEvent still exists — old table was not removed"
    )


# ---------------------------------------------------------------------------
# Test 2: EventKind is gone → EventKind exists
# ---------------------------------------------------------------------------


def test_event_kind_table_exists_equipment_event_kind_gone() -> None:
    """EventKind must exist; EquipmentEventKind must NOT exist after the rename."""
    schema = _load_schema()
    assert "EventKind" in schema, "EventKind table not found — rename not applied"
    assert "EquipmentEventKind" not in schema, (
        "EquipmentEventKind still exists — old table was not removed"
    )


# ---------------------------------------------------------------------------
# Test 3: Event has all 8 arc FK columns, all nullable
# ---------------------------------------------------------------------------


def test_event_has_all_eight_arc_columns() -> None:
    """Event must carry all 8 exclusive-arc FK columns, all nullable."""
    schema = _load_schema()
    tbl = schema["Event"]["table"]
    col_map = {c["name"]: c for c in tbl["columns"]}

    missing = [col for col in ARC_COLUMNS if col not in col_map]
    assert missing == [], f"Arc columns missing from Event: {missing}"

    non_nullable = [col for col in ARC_COLUMNS if not col_map[col].get("nullable", True)]
    assert non_nullable == [], (
        f"Arc columns must be nullable (exactly-one enforced by CHECK, not NOT NULL): "
        f"{non_nullable}"
    )


# ---------------------------------------------------------------------------
# Test 4: Event has the CK_Event_ExclusiveArc CHECK constraint
# ---------------------------------------------------------------------------


def test_event_has_exclusive_arc_check_constraint() -> None:
    """Event must declare a check_constraint named CK_Event_ExclusiveArc."""
    schema = _load_schema()
    tbl = schema["Event"]["table"]
    check_constraints = tbl.get("check_constraints", []) or []
    names = [c.get("name") for c in check_constraints]
    assert "CK_Event_ExclusiveArc" in names, (
        f"CK_Event_ExclusiveArc not found in Event.check_constraints; got: {names}"
    )

    # The expression must reference all 8 arc columns
    expr_blob = " ".join(
        c.get("expression", "") for c in check_constraints if c.get("name") == "CK_Event_ExclusiveArc"
    )
    for col in ARC_COLUMNS:
        assert col in expr_blob, (
            f"Arc column '{col}' not referenced in CK_Event_ExclusiveArc expression"
        )


# ---------------------------------------------------------------------------
# Test 5: EventKind seed vocab contains all PRD-required kinds
# ---------------------------------------------------------------------------


def test_event_kind_seed_contains_required_vocab() -> None:
    """EventKind.seed_data must include all vocabulary entries required by PRD-2."""
    schema = _load_schema()
    tbl = schema["EventKind"]["table"]
    seed = tbl.get("seed_data", []) or []
    seeded_names = {row.get("Name") for row in seed}

    missing = REQUIRED_EVENT_KINDS - seeded_names
    assert missing == set(), (
        f"EventKind seed is missing PRD-required kinds: {missing}"
    )


# ---------------------------------------------------------------------------
# Test 6: Schema validator clears (FK refs all resolved)
# ---------------------------------------------------------------------------


def test_schema_validates_cleanly_after_rename() -> None:
    """validate_schema must return no errors — Annotation FK repoint must hold."""
    from tools.schema_migrate.loader import load_schema
    from tools.schema_migrate.validate import validate_schema

    schema = load_schema(TABLES_DIR)
    errs = validate_schema(schema)
    assert errs == [], "Schema has validation errors after PRD-2 S1 rename:\n" + "\n".join(errs)


# ---------------------------------------------------------------------------
# Test 7: Generated DDL contains Event CREATE TABLE and CHECK constraint
# ---------------------------------------------------------------------------


def test_generated_ddl_contains_event_and_check(tmp_path: Path) -> None:
    """Generated MSSQL DDL must contain CREATE TABLE [dbo].[Event] and the CHECK constraint."""
    import sys
    import yaml

    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from generate_from_yaml import generate_all_from_yaml

    with VERSION_YAML.open(encoding="utf-8") as fh:
        version = str(yaml.safe_load(fh).get("schema_version", "0.1.0"))

    sql_dir = tmp_path / "sql"
    generate_all_from_yaml(
        tables_dir=TABLES_DIR,
        views_dir=VIEWS_DIR,
        docs_dir=tmp_path / "docs",
        assets_dir=tmp_path / "assets",
        sql_dir=sql_dir,
        platform="mssql",
        version=version,
    )

    sql = (sql_dir / f"v{version}_create_mssql.sql").read_text(encoding="utf-8")

    assert "CREATE TABLE [dbo].[Event]" in sql, "Event table missing from generated DDL"
    assert "CK_Event_ExclusiveArc" in sql, "CHECK constraint missing from generated DDL"
    assert "CREATE TABLE [dbo].[EquipmentEvent]" not in sql, (
        "EquipmentEvent still present in generated DDL — rename incomplete"
    )

    seed_sql = (sql_dir / f"v{version}_seed_mssql.sql").read_text(encoding="utf-8")
    assert "INSERT INTO [dbo].[EventKind]" in seed_sql, "EventKind seed missing from generated seed SQL"
    assert "EquipmentEventKind" not in seed_sql, "EquipmentEventKind still present in seed SQL"
