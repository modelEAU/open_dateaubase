"""SQL migration script renderer for MSSQL and PostgreSQL."""

import re
from datetime import datetime, timezone

from .diff import SchemaDiff

LOGICAL_TYPE_MAP: dict[str, dict[str, str]] = {
    "mssql": {
        "integer": "INT",
        "biginteger": "BIGINT",
        "smallinteger": "SMALLINT",
        "float64": "FLOAT",
        "float32": "REAL",
        "boolean": "BIT",
        "timestamp": "DATETIME2",
        "timestamptz": "DATETIMEOFFSET",
        "date": "DATE",
        "text": "NVARCHAR(MAX)",
        "binary": "VARBINARY",
        "binary_large": "VARBINARY(MAX)",
        "decimal": "NUMERIC",
        "string": "NVARCHAR",
    },
    "postgres": {
        "integer": "INTEGER",
        "biginteger": "BIGINT",
        "smallinteger": "SMALLINT",
        "float64": "DOUBLE PRECISION",
        "float32": "REAL",
        "boolean": "BOOLEAN",
        "timestamp": "TIMESTAMP",
        "timestamptz": "TIMESTAMPTZ",
        "date": "DATE",
        "text": "TEXT",
        "binary": "BYTEA",
        "binary_large": "BYTEA",
        "decimal": "NUMERIC",
        "string": "VARCHAR",
    },
}


def _q(identifier: str, platform: str) -> str:
    """Quote an SQL identifier for the target platform.

    Args:
        identifier: The raw identifier (table or column name).
        platform: ``'mssql'`` or ``'postgres'``.

    Returns:
        Quoted identifier string.
    """
    if platform == "mssql":
        return f"[{identifier}]"
    return f'"{identifier}"'


def render_column_type(col: dict, platform: str) -> str:
    """Convert logical type + modifiers to platform SQL type string.

    Args:
        col: Column definition dict from the schema YAML.
        platform: ``'mssql'`` or ``'postgres'``.

    Returns:
        SQL type string (e.g. ``NVARCHAR(255)``, ``NUMERIC(10,2)``).
    """
    logical = col.get("logical_type") or ""
    type_map = LOGICAL_TYPE_MAP[platform]
    base = type_map.get(logical, logical.upper() if logical else "/* UNMAPPED TYPE */")

    if logical == "string":
        max_length = col.get("max_length", "MAX")
        if str(max_length).lower() == "max":
            if platform == "mssql":
                return "NVARCHAR(MAX)"
            return "VARCHAR(MAX)"
        return f"{base}({max_length})"

    if logical == "decimal":
        precision = col.get("precision")
        scale = col.get("scale")
        if precision is not None and scale is not None:
            return f"NUMERIC({precision},{scale})"
        return "NUMERIC"

    if logical in ("timestamp", "timestamptz"):
        precision = col.get("precision")
        if precision is not None:
            return f"{base}({precision})"
        return base

    if logical == "binary":
        max_length = col.get("max_length")
        if max_length is not None:
            if platform == "mssql":
                return f"VARBINARY({max_length})"
            return "BYTEA"
        return base

    return base


def render_column_def(col: dict, platform: str) -> str:
    """Render a full column definition for CREATE TABLE or ADD COLUMN.

    Args:
        col: Column definition dict from the schema YAML.
        platform: ``'mssql'`` or ``'postgres'``.

    Returns:
        SQL fragment suitable for use inside CREATE TABLE or ALTER TABLE ADD.
    """
    parts: list[str] = [_q(col["name"], platform), render_column_type(col, platform)]

    nullable = col.get("nullable", True)
    identity = col.get("identity", False)

    if identity:
        if platform == "mssql":
            parts.append("IDENTITY(1,1)")
        else:
            # For PostgreSQL replace type with SERIAL/BIGSERIAL when identity
            logical = col.get("logical_type", "")
            if logical == "biginteger":
                parts[1] = "BIGSERIAL"
            else:
                parts[1] = "SERIAL"
            # Remove the IDENTITY marker — handled by type replacement
            identity = False  # no extra keyword needed

    if not nullable:
        parts.append("NOT NULL")

    default = col.get("default")
    if default is not None:
        if str(default).upper() == "CURRENT_TIMESTAMP":
            logical = col.get("logical_type", "")
            if logical == "timestamptz" and platform == "mssql":
                parts.append("DEFAULT SYSDATETIMEOFFSET()")
            else:
                parts.append("DEFAULT CURRENT_TIMESTAMP")
        elif isinstance(default, bool):
            parts.append(f"DEFAULT {1 if default else 0}")
        else:
            parts.append(f"DEFAULT {default}")

    return " ".join(parts)


def _render_create_table(table_name: str, table_dict: dict, platform: str) -> str:
    """Render a CREATE TABLE statement for a table definition.

    Args:
        table_name: Name of the table.
        table_dict: Full file-level dict (including ``_format_version`` key).
        platform: ``'mssql'`` or ``'postgres'``.

    Returns:
        Complete CREATE TABLE SQL statement string (no trailing newline).
    """
    tbl = table_dict["table"]
    schema = tbl.get("schema", "dbo")
    columns: list[dict] = tbl.get("columns", [])
    primary_key: list[str] = tbl.get("primary_key", [])
    check_constraints: list[dict] = tbl.get("check_constraints", []) or []
    unique_constraints: list[dict] = tbl.get("unique_constraints", []) or []
    # Also collect unique constraints declared via the generic `constraints` list
    for c in tbl.get("constraints", []) or []:
        if c.get("type") == "unique":
            unique_constraints = [*unique_constraints, c]

    col_defs: list[str] = [f"    {render_column_def(col, platform)}" for col in columns]

    if primary_key:
        pk_cols = ", ".join(_q(c, platform) for c in primary_key)
        pk_name = f"PK_{table_name}"
        col_defs.append(f"    CONSTRAINT {_q(pk_name, platform)} PRIMARY KEY ({pk_cols})")

    for uq in unique_constraints:
        uq_name = uq.get("name", "")
        uq_cols = ", ".join(_q(c, platform) for c in uq["columns"])
        col_defs.append(f"    CONSTRAINT {_q(uq_name, platform)} UNIQUE ({uq_cols})")

    for ck in check_constraints:
        ck_name = ck.get("name", "")
        expr = ck.get("expression", "")
        col_defs.append(f"    CONSTRAINT {_q(ck_name, platform)} CHECK ({expr})")

    body = ",\n".join(col_defs)
    full_table = _q(f"{schema}.{table_name}", platform) if platform == "postgres" else f"{_q(schema, platform)}.{_q(table_name, platform)}"
    return f"CREATE TABLE {full_table} (\n{body}\n);"


def _render_drop_table(table_name: str, table_dict: dict, platform: str) -> str:
    tbl = table_dict["table"]
    schema = tbl.get("schema", "dbo")
    if platform == "postgres":
        full_table = f'"{schema}"."{table_name}"'
    else:
        full_table = f"[{schema}].[{table_name}]"
    return f"DROP TABLE {full_table};"


def _render_add_fk(table_name: str, fk: dict, table_dict: dict, platform: str) -> str:
    tbl = table_dict["table"]
    schema = tbl.get("schema", "dbo")
    child_col = fk["column"]
    ref_table = fk["ref_table"]
    ref_col = fk["ref_column"]
    fk_name = fk.get("constraint_name") or f"FK_{table_name}_{child_col}"

    if platform == "mssql":
        return (
            f"ALTER TABLE [{schema}].[{table_name}] "
            f"ADD CONSTRAINT [{fk_name}] "
            f"FOREIGN KEY ([{child_col}]) "
            f"REFERENCES [{schema}].[{ref_table}] ([{ref_col}]);"
        )
    return (
        f'ALTER TABLE "{schema}"."{table_name}" '
        f'ADD CONSTRAINT "{fk_name}" '
        f'FOREIGN KEY ("{child_col}") '
        f'REFERENCES "{schema}"."{ref_table}" ("{ref_col}");'
    )


def _render_drop_fk(table_name: str, fk: dict, table_dict: dict, platform: str) -> str:
    tbl = table_dict["table"]
    schema = tbl.get("schema", "dbo")
    child_col = fk["column"]
    fk_name = fk.get("constraint_name") or f"FK_{table_name}_{child_col}"

    if platform == "mssql":
        return (
            f"ALTER TABLE [{schema}].[{table_name}] "
            f"DROP CONSTRAINT [{fk_name}];"
        )
    return (
        f'ALTER TABLE "{schema}"."{table_name}" '
        f'DROP CONSTRAINT "{fk_name}";'
    )


def _render_add_unique(table_name: str, uq: dict, table_dict: dict, platform: str) -> str:
    tbl = table_dict["table"]
    schema = tbl.get("schema", "dbo")
    cols = ", ".join(_q(c, platform) for c in uq["columns"])
    return (
        f"ALTER TABLE {_q(schema, platform)}.{_q(table_name, platform)} "
        f"ADD CONSTRAINT {_q(uq['name'], platform)} UNIQUE ({cols});"
    )


def _render_drop_unique(table_name: str, uq: dict, table_dict: dict, platform: str) -> str:
    tbl = table_dict["table"]
    schema = tbl.get("schema", "dbo")
    keyword = "CONSTRAINT" if platform == "mssql" else "CONSTRAINT"
    return (
        f"ALTER TABLE {_q(schema, platform)}.{_q(table_name, platform)} "
        f"DROP {keyword} {_q(uq['name'], platform)};"
    )


def _render_add_check(table_name: str, ck: dict, table_dict: dict, platform: str) -> str:
    tbl = table_dict["table"]
    schema = tbl.get("schema", "dbo")
    return (
        f"ALTER TABLE {_q(schema, platform)}.{_q(table_name, platform)} "
        f"ADD CONSTRAINT {_q(ck['name'], platform)} CHECK ({ck.get('expression', '')});"
    )


def _render_drop_check(table_name: str, ck: dict, table_dict: dict, platform: str) -> str:
    tbl = table_dict["table"]
    schema = tbl.get("schema", "dbo")
    return (
        f"ALTER TABLE {_q(schema, platform)}.{_q(table_name, platform)} "
        f"DROP CONSTRAINT {_q(ck['name'], platform)};"
    )


def _render_drop_default_constraint(table_name: str, col_name: str, schema: str = "dbo") -> str:
    """Render a dynamic-SQL block dropping a column's DEFAULT constraint, if any.

    MSSQL auto-names DEFAULT constraints (e.g. ``DF__Table__Col__1A2B3C4D``)
    unless one is explicitly named in the CREATE TABLE, so the exact name
    can't be predicted at generation time. A column can't be dropped while
    such a constraint references it, so this looks the name up from
    ``sys.default_constraints`` and drops it if present — a no-op otherwise.
    """
    return (
        "DECLARE @df NVARCHAR(200);\n"
        "SELECT @df = dc.name FROM sys.default_constraints dc\n"
        "JOIN sys.columns c ON c.default_object_id = dc.object_id AND c.object_id = dc.parent_object_id\n"
        f"WHERE dc.parent_object_id = OBJECT_ID('{schema}.{table_name}') AND c.name = '{col_name}';\n"
        f"IF @df IS NOT NULL EXEC('ALTER TABLE [{schema}].[{table_name}] DROP CONSTRAINT [' + @df + ']');"
    )


def _render_delete_seed_rows(
    table_name: str, table_dict: dict, rows: list[dict], platform: str
) -> str:
    """Render a DELETE statement removing seed rows by primary-key value.

    Args:
        table_name: Name of the table.
        table_dict: Full file-level dict (including ``_format_version`` key).
        rows: Seed rows to delete (each must contain the table's PK column).
        platform: ``'mssql'`` or ``'postgres'``.

    Returns:
        A single DELETE statement, or ``""`` if the table has no primary key
        or ``rows`` is empty.
    """
    tbl = table_dict["table"]
    pk = (tbl.get("primary_key") or [None])[0]
    if not pk or not rows:
        return ""
    schema = tbl.get("schema", "dbo")
    ids = ", ".join(_render_seed_value(row[pk]) for row in rows if pk in row)
    return (
        f"DELETE FROM {_q(schema, platform)}.{_q(table_name, platform)} "
        f"WHERE {_q(pk, platform)} IN ({ids});"
    )


def _render_create_index(table_name: str, idx: dict, table_dict: dict, platform: str) -> str:
    tbl = table_dict["table"]
    schema = tbl.get("schema", "dbo")
    idx_name = idx["name"]
    cols = ", ".join(_q(c, platform) for c in idx["columns"])
    unique = "UNIQUE " if idx.get("unique") else ""
    # Optional filtered/partial index: a raw SQL predicate. Identical syntax
    # for MSSQL filtered indexes and PostgreSQL partial indexes.
    where = f" WHERE {idx['filter']}" if idx.get("filter") else ""

    if platform == "mssql":
        return (
            f"CREATE {unique}INDEX [{idx_name}] "
            f"ON [{schema}].[{table_name}] ({cols}){where};"
        )
    return (
        f'CREATE {unique}INDEX "{idx_name}" '
        f'ON "{schema}"."{table_name}" ({cols}){where};'
    )


def _render_drop_index(table_name: str, idx: dict, table_dict: dict, platform: str) -> str:
    tbl = table_dict["table"]
    schema = tbl.get("schema", "dbo")
    idx_name = idx["name"]
    if platform == "mssql":
        return f"DROP INDEX [{idx_name}] ON [{schema}].[{table_name}];"
    return f'DROP INDEX "{schema}"."{idx_name}";'


def _table_fks(table_dict: dict) -> list[dict]:
    """Collect all FK dicts from a table definition."""
    fks: list[dict] = []
    for col in table_dict.get("table", {}).get("columns", []) or []:
        fk = col.get("foreign_key")
        if fk:
            entry: dict = {
                "column": col["name"],
                "ref_table": fk["table"],
                "ref_column": fk["column"],
            }
            if "constraint_name" in fk:
                entry["constraint_name"] = fk["constraint_name"]
            fks.append(entry)
    return fks


def _sort_tables_fk_safe(table_names: list[str], schema: dict[str, dict]) -> list[str]:
    """Return table_names sorted so tables with no FKs come first."""
    no_fk = [t for t in table_names if not _table_fks(schema.get(t, {}))]
    has_fk = [t for t in table_names if _table_fks(schema.get(t, {}))]
    return no_fk + has_fk


def _column_defs_by_name(table_dict: dict) -> dict[str, dict]:
    """Return {column_name: column_dict} for a table, or {} if not given."""
    return {
        col["name"]: col
        for col in table_dict.get("table", {}).get("columns", []) or []
    }


def _header(from_version: str, to_version: str, platform: str, is_rollback: bool = False) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    if is_rollback:
        rollback_ref = f"v{to_version}_to_v{from_version}_{platform}_rollback.sql"
        direction = f"v{to_version} -> v{from_version} (ROLLBACK)"
    else:
        rollback_ref = f"v{from_version}_to_v{to_version}_{platform}_rollback.sql"
        direction = f"v{from_version} -> v{to_version}"

    return (
        f"-- Migration: {direction}\n"
        f"-- Platform: {platform}\n"
        f"-- Generated: {now}\n"
        f"-- Rollback: {rollback_ref}\n"
    )


def render_migration(
    diff: SchemaDiff,
    new_schema: dict[str, dict],
    from_version: str,
    to_version: str,
    platform: str,
    old_schema: dict[str, dict] | None = None,
    old_views: dict[str, dict] | None = None,
    new_views: dict[str, dict] | None = None,
    description: str = "",
) -> tuple[str, str]:
    """Render forward migration and rollback SQL scripts.

    Args:
        diff: The :class:`~tools.schema_migrate.diff.SchemaDiff` describing changes.
        new_schema: The new (target) schema dict, needed for CREATE TABLE bodies.
        from_version: Source schema version string (e.g. ``'1.0.0'``).
        to_version: Target schema version string (e.g. ``'1.0.1'``).
        platform: ``'mssql'`` or ``'postgres'``.
        old_schema: The old (source) schema dict. Required to actually drop
            (rather than just comment) removed tables and to restore them —
            plus removed columns — on rollback. Omit only for callers that
            don't have it; the migration still renders, just with manual-TODO
            placeholders for those two cases.
        old_views: Old (source) views dict from ``load_views``, needed to
            render view drops/restores.
        new_views: New (target) views dict from ``load_views``, needed to
            render view creates/alters.
        description: Human-readable description stamped into the
            ``dbo.SchemaVersion`` row this migration inserts.

    Returns:
        A tuple ``(migration_sql, rollback_sql)`` — both as plain strings.
    """
    old_schema = old_schema or {}
    fwd: list[str] = [_header(from_version, to_version, platform, is_rollback=False)]
    rbk: list[str] = [_header(from_version, to_version, platform, is_rollback=True)]

    # ── CREATE new tables (no-FK tables first) ──────────────────────────────
    sorted_new = _sort_tables_fk_safe(diff.new_tables, new_schema)
    for table_name in sorted_new:
        fwd.append(_render_create_table(table_name, new_schema[table_name], platform))

    # ── ADD COLUMN ───────────────────────────────────────────────────────────
    for table_name, cols in diff.new_columns.items():
        tbl = new_schema[table_name]["table"]
        schema = tbl.get("schema", "dbo")
        for col in cols:
            col_def = render_column_def(col, platform)
            if platform == "mssql":
                fwd.append(f"ALTER TABLE [{schema}].[{table_name}] ADD {col_def};")
            else:
                fwd.append(f'ALTER TABLE "{schema}"."{table_name}" ADD COLUMN {col_def};')

    # ── ALTER COLUMN ─────────────────────────────────────────────────────────
    for table_name, alterations in diff.altered_columns.items():
        tbl = new_schema[table_name]["table"]
        schema = tbl.get("schema", "dbo")
        for alt in alterations:
            col_name = alt["column"]
            new_type = render_column_type(alt["new"], platform)
            old_type = render_column_type(alt["old"], platform)
            if platform == "mssql":
                fwd.append(
                    f"ALTER TABLE [{schema}].[{table_name}] "
                    f"ALTER COLUMN [{col_name}] {new_type};"
                )
            else:
                fwd.append(
                    f'ALTER TABLE "{schema}"."{table_name}" '
                    f'ALTER COLUMN "{col_name}" TYPE {new_type};'
                )

    # ── DROP FK (existing tables) — must precede DROP INDEX/COLUMN/TABLE ────
    for table_name, fks in diff.dropped_fks.items():
        for fk in fks:
            fwd.append(_render_drop_fk(table_name, fk, new_schema[table_name], platform))

    # ── DROP UNIQUE CONSTRAINT (existing tables) ─────────────────────────────
    for table_name, uqs in diff.dropped_unique_constraints.items():
        for uq in uqs:
            fwd.append(_render_drop_unique(table_name, uq, new_schema[table_name], platform))

    # ── DROP CHECK CONSTRAINT (existing tables) ──────────────────────────────
    for table_name, cks in diff.dropped_check_constraints.items():
        for ck in cks:
            fwd.append(_render_drop_check(table_name, ck, new_schema[table_name], platform))

    # ── DROP INDEX ───────────────────────────────────────────────────────────
    for table_name, indexes in diff.dropped_indexes.items():
        for idx in indexes:
            fwd.append(_render_drop_index(table_name, idx, new_schema[table_name], platform))

    # ── DROP COLUMN ──────────────────────────────────────────────────────────
    for table_name, col_names in diff.dropped_columns.items():
        tbl = new_schema.get(table_name, {}).get("table", {})
        schema = tbl.get("schema", "dbo")
        for col_name in col_names:
            if platform == "mssql":
                # MSSQL auto-names DEFAULT constraints, so the exact name
                # can't be known at generation time — look it up and drop it
                # dynamically before dropping a column that might carry one.
                # Each such block gets its own batch (GO) since the same
                # @df variable name is reused across dropped columns.
                fwd.append("GO")
                fwd.append(_render_drop_default_constraint(table_name, col_name, schema))
                fwd.append("GO")
                fwd.append(f"ALTER TABLE [{schema}].[{table_name}] DROP COLUMN [{col_name}];")
            else:
                fwd.append(f'ALTER TABLE "{schema}"."{table_name}" DROP COLUMN "{col_name}";')

    # ── DROP TABLE (FK-safe order: a table FKing another dropped table first) ─
    if diff.dropped_tables and old_schema:
        drop_order = list(reversed(_sort_tables_fk_safe(diff.dropped_tables, old_schema)))
        for table_name in drop_order:
            fwd.append(_render_drop_table(table_name, old_schema[table_name], platform))
    else:
        for table_name in diff.dropped_tables:
            fwd.append(f"-- DROP TABLE {table_name} (was removed from schema)")

    # ── CREATE INDEX (existing tables) ───────────────────────────────────────
    for table_name, indexes in diff.new_indexes.items():
        for idx in indexes:
            fwd.append(_render_create_index(table_name, idx, new_schema[table_name], platform))

    # ── CREATE INDEX (new tables) ────────────────────────────────────────────
    for table_name in sorted_new:
        tbl = new_schema[table_name]["table"]
        for idx in tbl.get("indexes", []) or []:
            fwd.append(_render_create_index(table_name, idx, new_schema[table_name], platform))

    # ── ADD UNIQUE CONSTRAINT (existing tables; new tables get theirs inline) ─
    for table_name, uqs in diff.new_unique_constraints.items():
        for uq in uqs:
            fwd.append(_render_add_unique(table_name, uq, new_schema[table_name], platform))

    # ── ADD CHECK CONSTRAINT (existing tables; new tables get theirs inline) ──
    # MSSQL binds a CHECK expression's column references against the schema
    # as of the start of the batch, not incrementally — so a column added
    # earlier in this same script isn't visible yet without a fresh batch.
    for table_name, cks in diff.new_check_constraints.items():
        for ck in cks:
            if platform == "mssql":
                fwd.append("GO")
            fwd.append(_render_add_check(table_name, ck, new_schema[table_name], platform))
            if platform == "mssql":
                fwd.append("GO")

    # ── ADD FK (existing tables) ─────────────────────────────────────────────
    for table_name, fks in diff.new_fks.items():
        for fk in fks:
            fwd.append(_render_add_fk(table_name, fk, new_schema[table_name], platform))

    # ── ADD FK (new tables) ──────────────────────────────────────────────────
    for table_name in sorted_new:
        for fk in _table_fks(new_schema[table_name]):
            fwd.append(_render_add_fk(table_name, fk, new_schema[table_name], platform))

    # ── SEED DATA: insert new vocab rows, delete rows removed from surviving
    #    tables (rows on fully-dropped tables already vanished with the table) ─
    for table_name in _sort_tables_fk_safe(list(diff.new_seed_rows), new_schema):
        fwd.append(
            _render_insert_block(
                table_name, new_schema[table_name], platform, rows=diff.new_seed_rows[table_name]
            )
        )
    for table_name, rows in diff.dropped_seed_rows.items():
        if table_name in diff.dropped_tables:
            continue
        stmt = _render_delete_seed_rows(table_name, new_schema[table_name], rows, platform)
        if stmt:
            fwd.append(stmt)

    # ── VIEWS: drop obsolete, then create/alter to their final definition ────
    # CREATE (OR ALTER) VIEW must be the sole statement in its sqlcmd batch on
    # MSSQL, so each one gets wrapped in its own GO...GO block.
    if old_views and diff.dropped_views:
        for view_name in reversed(_order_views_by_dependency(old_views)):
            if view_name in diff.dropped_views:
                if platform == "mssql":
                    fwd.append("GO")
                fwd.append(render_drop_view(view_name, old_views[view_name], platform))
                if platform == "mssql":
                    fwd.append("GO")
    if new_views:
        for view_name in _order_views_by_dependency(new_views):
            if view_name in diff.new_views or view_name in diff.altered_views:
                if platform == "mssql":
                    fwd.append("GO")
                fwd.append(render_create_view(view_name, new_views[view_name], platform))
                if platform == "mssql":
                    fwd.append("GO")

    # ── SchemaVersion bookkeeping ─────────────────────────────────────────────
    version_desc = _render_seed_value(description or f"Migration v{from_version} -> v{to_version}")
    if platform == "mssql":
        fwd.append(
            f"INSERT INTO [dbo].[SchemaVersion] ([Version], [Description]) "
            f"VALUES (N'{to_version}', {version_desc});"
        )
    else:
        fwd.append(
            f'INSERT INTO "dbo"."SchemaVersion" ("Version", "Description") '
            f"VALUES ('{to_version}', {version_desc});"
        )

    # ── ROLLBACK (built separately for correct dependency ordering) ──────────

    # 0. Remove the SchemaVersion row this migration stamped.
    if platform == "mssql":
        rbk.append(f"DELETE FROM [dbo].[SchemaVersion] WHERE [Version] = N'{to_version}';")
    else:
        rbk.append(f"DELETE FROM \"dbo\".\"SchemaVersion\" WHERE \"Version\" = '{to_version}';")

    # 1. Seed data: delete rows this migration inserted into surviving tables
    #    (rows on brand-new tables disappear when the table itself is dropped).
    for table_name, rows in diff.new_seed_rows.items():
        if table_name in diff.new_tables:
            continue
        stmt = _render_delete_seed_rows(table_name, new_schema[table_name], rows, platform)
        if stmt:
            rbk.append(stmt)

    # 2. Drop FKs first (from new tables, then from existing tables)
    for table_name in sorted_new:
        for fk in _table_fks(new_schema[table_name]):
            rbk.append(_render_drop_fk(table_name, fk, new_schema[table_name], platform))
    for table_name, fks in diff.new_fks.items():
        for fk in fks:
            rbk.append(_render_drop_fk(table_name, fk, new_schema[table_name], platform))

    # 3. Re-adding dropped FKs waits until after column restoration below —
    #    one may reference a column, like AnalysisSeries.ProcessingKind_ID,
    #    that doesn't exist again yet.

    # 4. Drop unique/check constraints this migration added. (Re-adding the
    #    ones it dropped waits until after column restoration below — they
    #    may reference a column, like Annotation.Channel_ID, that doesn't
    #    exist again yet.)
    for table_name, uqs in diff.new_unique_constraints.items():
        for uq in uqs:
            rbk.append(_render_drop_unique(table_name, uq, new_schema[table_name], platform))
    for table_name, cks in diff.new_check_constraints.items():
        for ck in cks:
            rbk.append(_render_drop_check(table_name, ck, new_schema[table_name], platform))

    # 5. Drop new indexes (on new tables and on existing tables)
    for table_name in sorted_new:
        tbl = new_schema[table_name]["table"]
        for idx in tbl.get("indexes", []) or []:
            rbk.append(_render_drop_index(table_name, idx, new_schema[table_name], platform))
    for table_name, indexes in diff.new_indexes.items():
        for idx in indexes:
            rbk.append(_render_drop_index(table_name, idx, new_schema[table_name], platform))

    # 6. Re-adding dropped indexes waits until after column restoration below
    #    — one may cover a column, like Annotation.Channel_ID, that doesn't
    #    exist again yet.

    # 7. Restore dropped columns (from old_schema when available)
    for table_name, col_names in diff.dropped_columns.items():
        old_cols = _column_defs_by_name(old_schema.get(table_name, {}))
        tbl = new_schema[table_name]["table"]
        schema = tbl.get("schema", "dbo")
        for col_name in col_names:
            old_col = old_cols.get(col_name)
            if not old_col:
                rbk.append(f"-- TODO: restore dropped column {col_name} on {table_name} manually.")
                continue
            col_def = render_column_def(old_col, platform)
            if platform == "mssql":
                rbk.append(f"ALTER TABLE [{schema}].[{table_name}] ADD {col_def};")
            else:
                rbk.append(f'ALTER TABLE "{schema}"."{table_name}" ADD COLUMN {col_def};')

    # 7a. Re-add indexes this migration dropped — now that any column they
    #     cover has been restored above. (FKs wait until after step 11: one
    #     may reference a fully-dropped table, like ProcessingKind, that
    #     doesn't exist again until then.)
    for table_name, indexes in diff.dropped_indexes.items():
        for idx in indexes:
            rbk.append(_render_create_index(table_name, idx, new_schema[table_name], platform))

    # 7b. Re-add unique/check constraints this migration dropped — now that
    #     any column they reference has been restored above.
    for table_name, uqs in diff.dropped_unique_constraints.items():
        for uq in uqs:
            rbk.append(_render_add_unique(table_name, uq, new_schema[table_name], platform))
    for table_name, cks in diff.dropped_check_constraints.items():
        for ck in cks:
            if platform == "mssql":
                rbk.append("GO")
            rbk.append(_render_add_check(table_name, ck, new_schema[table_name], platform))
            if platform == "mssql":
                rbk.append("GO")

    # 8. Reverse column type/nullability changes
    for table_name, alterations in diff.altered_columns.items():
        tbl = new_schema[table_name]["table"]
        schema = tbl.get("schema", "dbo")
        for alt in alterations:
            col_name = alt["column"]
            old_type = render_column_type(alt["old"], platform)
            if platform == "mssql":
                rbk.append(
                    f"ALTER TABLE [{schema}].[{table_name}] "
                    f"ALTER COLUMN [{col_name}] {old_type};"
                )
            else:
                rbk.append(
                    f'ALTER TABLE "{schema}"."{table_name}" '
                    f'ALTER COLUMN "{col_name}" TYPE {old_type};'
                )

    # 9. Drop columns this migration added
    for table_name, cols in diff.new_columns.items():
        tbl = new_schema[table_name]["table"]
        schema = tbl.get("schema", "dbo")
        for col in cols:
            if platform == "mssql":
                rbk.append("GO")
                rbk.append(_render_drop_default_constraint(table_name, col["name"], schema))
                rbk.append("GO")
                rbk.append(f"ALTER TABLE [{schema}].[{table_name}] DROP COLUMN [{col['name']}];")
            else:
                rbk.append(f'ALTER TABLE "{schema}"."{table_name}" DROP COLUMN "{col["name"]}";')

    # 10. Drop new tables (reverse FK-safe order so dependent tables drop first)
    for table_name in reversed(sorted_new):
        rbk.append(_render_drop_table(table_name, new_schema[table_name], platform))

    # 11. Restore dropped tables (bodies, then indexes, then FKs) — parent-first
    if diff.dropped_tables and old_schema:
        restore_order = _sort_tables_fk_safe(diff.dropped_tables, old_schema)
        for table_name in restore_order:
            rbk.append(_render_create_table(table_name, old_schema[table_name], platform))
        for table_name in restore_order:
            tbl = old_schema[table_name]["table"]
            for idx in tbl.get("indexes", []) or []:
                rbk.append(_render_create_index(table_name, idx, old_schema[table_name], platform))
        for table_name in restore_order:
            for fk in _table_fks(old_schema[table_name]):
                rbk.append(_render_add_fk(table_name, fk, old_schema[table_name], platform))
    else:
        for table_name in diff.dropped_tables:
            rbk.append(f"-- TODO: restore dropped table {table_name} manually.")

    # 11a. Re-add FKs this migration dropped — deferred until every table and
    #      column they might reference (including a fully-dropped table
    #      restored just above) exists again.
    for table_name, fks in diff.dropped_fks.items():
        for fk in fks:
            rbk.append(_render_add_fk(table_name, fk, new_schema[table_name], platform))

    # 12. Restore seed rows removed by this migration (on now-restored dropped
    #     tables and on surviving tables that lost specific rows)
    for table_name, rows in diff.dropped_seed_rows.items():
        table_dict = new_schema.get(table_name) or old_schema.get(table_name)
        if not table_dict:
            continue
        block = _render_insert_block(table_name, table_dict, platform, rows=rows)
        if block:
            rbk.append(block)

    # 13. Views: undo — drop what forward created, restore old definitions
    if new_views and diff.new_views:
        for view_name in reversed(_order_views_by_dependency(new_views)):
            if view_name in diff.new_views:
                if platform == "mssql":
                    rbk.append("GO")
                rbk.append(render_drop_view(view_name, new_views[view_name], platform))
                if platform == "mssql":
                    rbk.append("GO")
    if old_views:
        for view_name in _order_views_by_dependency(old_views):
            if view_name in diff.altered_views or view_name in diff.dropped_views:
                if platform == "mssql":
                    rbk.append("GO")
                rbk.append(render_create_view(view_name, old_views[view_name], platform))
                if platform == "mssql":
                    rbk.append("GO")

    return "\n\n".join(fwd) + "\n", "\n\n".join(rbk) + "\n"


def render_create_script(
    schema: dict[str, dict],
    version: str,
    platform: str,
) -> str:
    """Render a full CREATE script for all tables in schema (baseline).

    Args:
        schema: Full schema dict from ``load_schema``.
        version: Schema version string.
        platform: ``'mssql'`` or ``'postgres'``.

    Returns:
        SQL string containing all CREATE TABLE and CREATE INDEX statements,
        plus ALTER TABLE ADD CONSTRAINT for all foreign keys.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines: list[str] = [
        f"-- Baseline CREATE script for schema v{version}",
        f"-- Platform: {platform}",
        f"-- Generated: {now}",
        "",
    ]

    sorted_tables = _sort_tables_fk_safe(sorted(schema.keys()), schema)

    for table_name in sorted_tables:
        lines.append(_render_create_table(table_name, schema[table_name], platform))
        lines.append("")

    # Indexes
    for table_name in sorted_tables:
        tbl = schema[table_name]["table"]
        for idx in tbl.get("indexes", []) or []:
            lines.append(_render_create_index(table_name, idx, schema[table_name], platform))
        lines.append("")

    # Foreign keys (after all tables exist)
    for table_name in sorted_tables:
        for fk in _table_fks(schema[table_name]):
            lines.append(_render_add_fk(table_name, fk, schema[table_name], platform))

    return "\n".join(lines) + "\n"


def render_create_view(view_name: str, view_dict: dict, platform: str) -> str:
    """Render a CREATE OR ALTER VIEW (MSSQL) or CREATE OR REPLACE VIEW (PostgreSQL).

    Args:
        view_name: Name of the view.
        view_dict: Full file-level dict (including ``_format_version`` key).
        platform: ``'mssql'`` or ``'postgres'``.

    Returns:
        Complete CREATE VIEW SQL statement string.
    """
    v = view_dict["view"]
    schema = v.get("schema", "dbo")
    definition = (v.get("view_definition") or "").strip()

    full_view = (
        f"[{schema}].[{view_name}]" if platform == "mssql"
        else f'"{schema}"."{view_name}"'
    )

    if platform == "mssql":
        return f"CREATE OR ALTER VIEW {full_view} AS\n{definition};"
    return f"CREATE OR REPLACE VIEW {full_view} AS\n{definition};"


def render_drop_view(view_name: str, view_dict: dict, platform: str) -> str:
    """Render a DROP VIEW statement.

    Args:
        view_name: Name of the view.
        view_dict: Full file-level dict.
        platform: ``'mssql'`` or ``'postgres'``.

    Returns:
        DROP VIEW SQL statement string.
    """
    v = view_dict["view"]
    schema = v.get("schema", "dbo")

    full_view = (
        f"[{schema}].[{view_name}]" if platform == "mssql"
        else f'"{schema}"."{view_name}"'
    )
    return f"DROP VIEW {full_view};"


def _order_views_by_dependency(views: dict[str, dict]) -> list[str]:
    """View names in creation order: a view that selects from another comes after it.

    SQL Server resolves view references at CREATE (OR ALTER) time — there is no
    deferral across views — so emitting them alphabetically breaks whenever one
    view sits on top of another (e.g. vw_ChannelEquipmentAtTime on
    vw_ChannelResolved). Dependencies are read straight from each view's SQL text
    (whole-word match on the other view names), so no manual bookkeeping is
    needed. Kahn's algorithm with an alphabetical tiebreak keeps output stable.
    """
    names = list(views)

    def _definition(name: str) -> str:
        return (views[name].get("view", {}).get("view_definition") or "")

    deps = {
        name: {
            other
            for other in names
            if other != name and re.search(rf"\b{re.escape(other)}\b", _definition(name))
        }
        for name in names
    }
    ordered: list[str] = []
    remaining = set(names)
    while remaining:
        ready = sorted(n for n in remaining if deps[n] <= set(ordered))
        if not ready:  # a dependency cycle — surface it rather than emit broken SQL
            raise ValueError(f"Cyclic view dependencies among: {sorted(remaining)}")
        ordered.extend(ready)
        remaining -= set(ready)
    return ordered


def render_create_script_with_views(
    schema: dict[str, dict],
    views: dict[str, dict],
    version: str,
    platform: str,
) -> str:
    """Render a full CREATE script for all tables and views (baseline).

    Args:
        schema: Full schema dict from ``load_schema``.
        views: Full views dict from ``load_views``.
        version: Schema version string.
        platform: ``'mssql'`` or ``'postgres'``.

    Returns:
        SQL string containing all CREATE TABLE, CREATE INDEX, ALTER TABLE FK,
        and CREATE VIEW statements.
    """
    # Reuse existing table CREATE script
    sql = render_create_script(schema, version, platform).rstrip("\n")

    if views:
        view_lines: list[str] = ["", "-- Views"]
        for view_name in _order_views_by_dependency(views):
            if platform == "mssql":
                view_lines.append("GO")
            view_lines.append(render_create_view(view_name, views[view_name], platform))
            view_lines.append("")
        sql += "\n" + "\n".join(view_lines)

    return sql + "\n"


def _render_seed_value(value: object) -> str:
    """Convert a Python YAML value to an SQL literal.

    Args:
        value: Python value from a seed_data row dict.

    Returns:
        SQL literal string:
        - ``None``  → ``NULL``
        - ``bool``  → ``1`` or ``0``  (MSSQL BIT)
        - ``int`` / ``float`` → decimal string
        - ``str``   → ``N'...'`` with single-quotes escaped as ``''``
    """
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    # str
    escaped = str(value).replace("'", "''")
    return f"N'{escaped}'"


def _render_insert_block(
    table_name: str, table_dict: dict, platform: str, rows: list[dict] | None = None
) -> str:
    """Render INSERT statements for a table's seed_data (or an explicit row subset).

    Args:
        table_name: Name of the table.
        table_dict: Full file-level dict (including ``_format_version`` key).
        platform: ``'mssql'`` or ``'postgres'``.
        rows: Explicit rows to render (e.g. only the rows added by a
            migration). Defaults to the table's full ``seed_data``.

    Returns:
        Multi-line SQL string with all INSERTs (and IDENTITY_INSERT wrappers
        where needed), or ``""`` if there are no rows to render.
    """
    tbl = table_dict["table"]
    schema = tbl.get("schema", "dbo")
    seed_rows: list[dict] = rows if rows is not None else (tbl.get("seed_data") or [])

    if not seed_rows:
        return ""

    # Detect whether any column uses IDENTITY
    has_identity = any(col.get("identity", False) for col in tbl.get("columns", []) or [])

    # Build quoted table reference
    if platform == "mssql":
        full_table = f"[{schema}].[{table_name}]"
    else:
        full_table = f'"{schema}"."{table_name}"'

    lines: list[str] = [f"-- {table_name}"]

    if has_identity:
        lines.append(f"SET IDENTITY_INSERT {full_table} ON;")

    # Collect declared column names so build-time-only keys are silently dropped.
    declared_cols: set[str] = {col["name"] for col in tbl.get("columns", []) or []}

    for row in seed_rows:
        # Filter to only declared column keys (drops e.g. manual_units)
        filtered = {k: v for k, v in row.items() if k in declared_cols}
        if platform == "mssql":
            cols = ", ".join(f"[{col}]" for col in filtered)
        else:
            cols = ", ".join(f'"{col}"' for col in filtered)
        vals = ", ".join(_render_seed_value(v) for v in filtered.values())
        lines.append(f"INSERT INTO {full_table} ({cols}) VALUES ({vals});")

    if has_identity:
        lines.append(f"SET IDENTITY_INSERT {full_table} OFF;")

    return "\n".join(lines)


def render_seed_script(
    schema: dict[str, dict],
    version: str,
    platform: str,
) -> str:
    """Render a seed INSERT script for all tables in the schema that have seed_data.

    Args:
        schema: Full schema dict from ``load_schema``.
        version: Schema version string.
        platform: ``'mssql'`` or ``'postgres'``.

    Returns:
        SQL string containing all INSERT statements for vocabulary tables,
        with IDENTITY_INSERT wrappers where needed.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    lines: list[str] = [
        f"-- Seed data for schema v{version}",
        f"-- Platform: {platform}",
        f"-- Generated: {now}",
        "",
    ]

    sorted_tables = _sort_tables_fk_safe(sorted(schema.keys()), schema)

    blocks: list[str] = []
    for table_name in sorted_tables:
        block = _render_insert_block(table_name, schema[table_name], platform)
        if block:
            blocks.append(block)

    return "\n".join(lines) + "\n".join(blocks) + "\n"
