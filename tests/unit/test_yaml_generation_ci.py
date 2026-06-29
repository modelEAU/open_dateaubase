"""CI tests for YAML-based documentation, ERD, and SQL generation.

These tests run without a database and validate:
1. generate_from_yaml produces tables.md, views.md, erd.md, erd_interactive.html, and a SQL file.
2. The generated SQL contains CREATE TABLE for every table in the YAML schema.
3. The generated tables.md references every table by name.
4. View YAML files (if any) pass validate_views with no errors.
5. load_views returns an empty dict when views_dir is empty (graceful).
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
TABLES_DIR = REPO_ROOT / "schema_dictionary" / "tables"
VIEWS_DIR = REPO_ROOT / "schema_dictionary" / "views"
VERSION_YAML = REPO_ROOT / "schema_dictionary" / "version.yaml"


def _schema_version() -> str:
    import yaml

    with VERSION_YAML.open(encoding="utf-8") as fh:
        return str(yaml.safe_load(fh).get("schema_version", "0.1.0"))


# ---------------------------------------------------------------------------
# Test 1: generate_from_yaml produces all expected output files
# ---------------------------------------------------------------------------


def test_generate_all_from_yaml_produces_expected_files(tmp_path: Path) -> None:
    """generate_all_from_yaml must write tables.md, views.md, erd.md, erd_interactive.html, SQL."""
    import sys

    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from generate_from_yaml import generate_all_from_yaml

    docs_dir = tmp_path / "docs"
    assets_dir = tmp_path / "assets"
    sql_dir = tmp_path / "sql"
    version = _schema_version()

    generate_all_from_yaml(
        tables_dir=TABLES_DIR,
        views_dir=VIEWS_DIR,
        docs_dir=docs_dir,
        assets_dir=assets_dir,
        sql_dir=sql_dir,
        platform="mssql",
        version=version,
    )

    assert (docs_dir / "tables.md").exists(), "tables.md was not generated"
    assert (docs_dir / "views.md").exists(), "views.md was not generated"
    assert (docs_dir / "erd.md").exists(), "erd.md was not generated"
    assert (assets_dir / "erd_interactive.html").exists(), "erd_interactive.html was not generated"
    assert (sql_dir / f"v{version}_create_mssql.sql").exists(), "SQL CREATE script was not generated"
    assert (sql_dir / f"v{version}_seed_mssql.sql").exists(), "SQL seed script was not generated"


# ---------------------------------------------------------------------------
# Test 2: Generated seed SQL contains INSERT INTO for every table with seed_data
# ---------------------------------------------------------------------------


def test_generated_seed_sql_contains_all_vocabulary_inserts(tmp_path: Path) -> None:
    """Every table with at least one seed_data row must have an INSERT in the seed SQL."""
    import sys

    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from generate_from_yaml import generate_all_from_yaml
    from tools.schema_migrate.loader import load_schema

    version = _schema_version()
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

    seed_content = (sql_dir / f"v{version}_seed_mssql.sql").read_text(encoding="utf-8")
    schema = load_schema(TABLES_DIR)

    tables_with_seed = [
        t for t, d in schema.items()
        if d.get("table", {}).get("seed_data")
    ]
    missing = [t for t in tables_with_seed if f"INSERT INTO [dbo].[{t}]" not in seed_content]
    assert missing == [], f"Tables with seed_data missing from generated seed SQL: {missing}"


# ---------------------------------------------------------------------------
# Test 3: Generated SQL contains CREATE TABLE for every YAML table
# ---------------------------------------------------------------------------


def test_generated_sql_contains_all_tables(tmp_path: Path) -> None:
    """Every table defined in the YAML schema must appear in the generated SQL."""
    import sys

    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from generate_from_yaml import generate_all_from_yaml
    from tools.schema_migrate.loader import load_schema

    version = _schema_version()
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

    sql_content = (sql_dir / f"v{version}_create_mssql.sql").read_text(encoding="utf-8")
    schema = load_schema(TABLES_DIR)

    missing = [t for t in schema if f"CREATE TABLE [dbo].[{t}]" not in sql_content]
    assert missing == [], f"Tables missing from generated SQL: {missing}"


# ---------------------------------------------------------------------------
# Test 3: Generated tables.md mentions every table
# ---------------------------------------------------------------------------


def test_generated_tables_md_mentions_all_tables(tmp_path: Path) -> None:
    """Every table name must appear as a heading in tables.md."""
    import sys

    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from generate_from_yaml import generate_all_from_yaml
    from tools.schema_migrate.loader import load_schema

    version = _schema_version()
    docs_dir = tmp_path / "docs"

    generate_all_from_yaml(
        tables_dir=TABLES_DIR,
        views_dir=VIEWS_DIR,
        docs_dir=docs_dir,
        assets_dir=tmp_path / "assets",
        sql_dir=tmp_path / "sql",
        platform="mssql",
        version=version,
    )

    content = (docs_dir / "tables.md").read_text(encoding="utf-8")
    schema = load_schema(TABLES_DIR)

    missing = [t for t in schema if t not in content]
    assert missing == [], f"Tables missing from tables.md: {missing}"


# ---------------------------------------------------------------------------
# Test 4: View YAML files pass validate_views
# ---------------------------------------------------------------------------


def test_view_yaml_files_validate_cleanly() -> None:
    """Every .yaml file in schema_dictionary/views/ must pass validate_views."""
    from tools.schema_migrate.loader import load_views
    from tools.schema_migrate.validate import validate_views

    views = load_views(VIEWS_DIR)
    errors = validate_views(views)
    assert errors == [], "\n".join(errors)


def test_channel_location_view_exposes_resolution_discriminators() -> None:
    """F6: vw_ChannelLocationAtTime must carry Resolution + LocationResolution so a
    NULL SamplingPoint from a broken chain is distinguishable from a genuine absence."""
    import yaml as _yaml

    doc = _yaml.safe_load(
        (VIEWS_DIR / "vw_ChannelLocationAtTime.yaml").read_text(encoding="utf-8")
    )["view"]
    col_names = {c["name"] for c in doc["columns"]}
    assert {"Resolution", "LocationResolution"} <= col_names, col_names
    definition = doc["view_definition"]
    # the location leg discriminates the three broken/absent/resolved cases
    for token in ("no-equipment", "no-location", "LocationResolution"):
        assert token in definition, f"missing {token!r} in view definition"


def test_views_emitted_after_views_they_reference() -> None:
    """A view that selects from another must be CREATEd after it.

    SQL Server resolves view references at CREATE time, so an alphabetical emit
    order broke db-init once vw_ChannelEquipmentAtTime started selecting from
    vw_ChannelResolved. Guard the dependency-ordered emit.
    """
    from tools.schema_migrate.loader import load_schema, load_views
    from tools.schema_migrate.render import render_create_script_with_views

    views = load_views(VIEWS_DIR)
    schema = load_schema(TABLES_DIR)
    sql = render_create_script_with_views(schema, views, "test", "mssql")

    # Position of each "CREATE ... VIEW [dbo].[name]" in the script.
    pos = {name: sql.index(f"[dbo].[{name}]") for name in views}
    for name, vdoc in views.items():
        definition = vdoc.get("view", {}).get("view_definition") or ""
        for other in views:
            if other != name and re.search(rf"\b{re.escape(other)}\b", definition):
                assert pos[other] < pos[name], (
                    f"{name} references {other} but is created before it"
                )


# ---------------------------------------------------------------------------
# Test 5: load_views is graceful when views_dir is empty or missing
# ---------------------------------------------------------------------------


def test_load_views_returns_empty_for_missing_dir(tmp_path: Path) -> None:
    """load_views must return {} when the directory does not exist."""
    from tools.schema_migrate.loader import load_views

    result = load_views(tmp_path / "nonexistent")
    assert result == {}


def test_load_views_returns_empty_for_empty_dir(tmp_path: Path) -> None:
    """load_views must return {} when the directory exists but has no .yaml files."""
    from tools.schema_migrate.loader import load_views

    empty_dir = tmp_path / "empty_views"
    empty_dir.mkdir()
    result = load_views(empty_dir)
    assert result == {}


# ---------------------------------------------------------------------------
# Test 6: ERD HTML contains expected markers
# ---------------------------------------------------------------------------


def test_erd_html_contains_table_names(tmp_path: Path) -> None:
    """The generated ERD HTML must reference at least a few table names."""
    import sys

    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from generate_from_yaml import generate_all_from_yaml
    from tools.schema_migrate.loader import load_schema

    version = _schema_version()
    assets_dir = tmp_path / "assets"

    generate_all_from_yaml(
        tables_dir=TABLES_DIR,
        views_dir=VIEWS_DIR,
        docs_dir=tmp_path / "docs",
        assets_dir=assets_dir,
        sql_dir=tmp_path / "sql",
        platform="mssql",
        version=version,
    )

    html_content = (assets_dir / "erd_interactive.html").read_text(encoding="utf-8")
    schema = load_schema(TABLES_DIR)

    # At least half the tables should appear in the HTML
    found = sum(1 for t in schema if t in html_content)
    assert found >= len(schema) // 2, (
        f"Only {found}/{len(schema)} table names found in ERD HTML"
    )
