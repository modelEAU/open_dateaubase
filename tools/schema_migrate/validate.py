"""Schema validator: checks referential integrity and type constraints."""


def validate_views(views: dict[str, dict]) -> list[str]:
    """Validate a loaded views dict and return a list of error strings.

    Checks performed:
    1. Each view has a non-empty ``view_definition``.
    2. Each column entry has a ``name`` and ``sql_data_type``.

    Args:
        views: Views dict returned by :func:`~tools.schema_migrate.loader.load_views`.

    Returns:
        List of human-readable error strings; empty if all views are valid.
    """
    errors: list[str] = []

    for view_name, data in views.items():
        v = data.get("view", {})

        definition = (v.get("view_definition") or "").strip()
        if not definition:
            errors.append(f"{view_name}: view_definition is missing or empty.")

        for col in v.get("columns", []) or []:
            col_name = col.get("name", "<unnamed>")
            if not col.get("name"):
                errors.append(f"{view_name}: a column entry is missing 'name'.")
            if not col.get("sql_data_type"):
                errors.append(
                    f"{view_name}.{col_name}: sql_data_type is required for view columns."
                )

    return errors


def validate_schema(schema: dict[str, dict]) -> list[str]:
    """Validate a loaded schema dict and return a list of error strings.

    An empty list means the schema is valid.

    Checks performed:
    1. All FK table references point to a table that exists in the schema.
    2. All FK column references exist in the referenced table.
    3. All ``primary_key`` columns exist in the table's ``columns`` list.
    4. All index columns exist in the table's ``columns`` list.
    5. ``identity: true`` only on ``integer`` or ``biginteger`` columns.
    6. ``max_length`` present when ``logical_type`` is ``string``.
    7. ``precision`` and ``scale`` present when ``logical_type`` is ``decimal``.

    Args:
        schema: Schema dict returned by :func:`~tools.schema_migrate.loader.load_schema`.

    Returns:
        List of human-readable error strings; empty if the schema is fully valid.
    """
    errors: list[str] = []

    # Build a lookup: table_name -> set of column names
    table_columns: dict[str, set[str]] = {}
    for table_name, data in schema.items():
        cols = data.get("table", {}).get("columns", []) or []
        table_columns[table_name] = {col["name"] for col in cols}

    for table_name, data in schema.items():
        tbl = data.get("table", {})
        columns: list[dict] = tbl.get("columns", []) or []
        col_names = table_columns[table_name]

        # ── Per-column checks ────────────────────────────────────────────────
        for col in columns:
            col_name = col.get("name", "<unnamed>")
            logical_type = col.get("logical_type", "")

            # Check 5: identity only on integer/biginteger
            if col.get("identity") and logical_type not in ("integer", "biginteger"):
                errors.append(
                    f"{table_name}.{col_name}: identity: true is only valid "
                    f"on integer or biginteger columns (found '{logical_type}')."
                )

            # Check 6: max_length required for string
            if logical_type == "string" and col.get("max_length") is None:
                errors.append(
                    f"{table_name}.{col_name}: max_length is required when "
                    f"logical_type is 'string'."
                )

            # Check 7: precision and scale required for decimal
            if logical_type == "decimal":
                if col.get("precision") is None:
                    errors.append(
                        f"{table_name}.{col_name}: precision is required when "
                        f"logical_type is 'decimal'."
                    )
                if col.get("scale") is None:
                    errors.append(
                        f"{table_name}.{col_name}: scale is required when "
                        f"logical_type is 'decimal'."
                    )

            # Check 1 & 2: FK table and column references
            fk = col.get("foreign_key")
            if fk:
                ref_table = fk.get("table")
                ref_col = fk.get("column")

                if ref_table not in schema:
                    errors.append(
                        f"{table_name}.{col_name}: FK references table "
                        f"'{ref_table}' which does not exist in the schema."
                    )
                elif ref_col not in table_columns.get(ref_table, set()):
                    errors.append(
                        f"{table_name}.{col_name}: FK references column "
                        f"'{ref_col}' in table '{ref_table}' which does not exist."
                    )

        # ── Check 3: primary_key columns exist ───────────────────────────────
        primary_key: list[str] = tbl.get("primary_key", []) or []
        for pk_col in primary_key:
            if pk_col not in col_names:
                errors.append(
                    f"{table_name}: primary_key column '{pk_col}' does not "
                    f"exist in the table's columns list."
                )

        # ── Check 4: index columns exist ─────────────────────────────────────
        for idx in tbl.get("indexes", []) or []:
            idx_name = idx.get("name", "<unnamed>")
            for idx_col in idx.get("columns", []):
                if idx_col not in col_names:
                    errors.append(
                        f"{table_name}: index '{idx_name}' references column "
                        f"'{idx_col}' which does not exist in the table's columns list."
                    )

        # ── Check 4: unique_constraint columns exist ─────────────────────────
        for uq in tbl.get("unique_constraints", []) or []:
            uq_name = uq.get("name", "<unnamed>")
            for uq_col in uq.get("columns", []):
                if uq_col not in col_names:
                    errors.append(
                        f"{table_name}: unique_constraint '{uq_name}' references "
                        f"column '{uq_col}' which does not exist in the table's columns list."
                    )

    return errors
