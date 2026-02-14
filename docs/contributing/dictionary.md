# Contributing to the Schema Dictionary

## Overview

The project uses two schema sources that serve different purposes. Make changes in the right place to keep everything in sync.

| Source              | Location                                                              | Drives                                                               |
|---------------------|-----------------------------------------------------------------------|----------------------------------------------------------------------|
| YAML files          | `schema_dictionary/tables/*.yaml`, `schema_dictionary/views/*.yaml`   | SQL DDL, interactive ERD, `tables.md`, `views.md`                    |
| `dictionary.json`   | `src/open_dateaubase/dictionary.json`                                 | Value sets (controlled vocabularies), validated by Pydantic models   |

YAML is the source of truth for table and view structure. `dictionary.json` is only for application-level metadata (allowed values, not schema).

---

## Add a column to an existing table

1. Open the table's YAML file in `schema_dictionary/tables/`.

2. Add the column entry under `columns:` with all required fields:

    ```yaml
    - name: NewColumn
      logical_type: string
      max_length: 100
      nullable: true
      description: "What this column stores."
    ```

3. If the column is a foreign key, add the `foreign_key:` block and a corresponding index:

    ```yaml
    - name: OtherTable_ID
      logical_type: integer
      nullable: true
      description: "FK to OtherTable."
      foreign_key:
        table: OtherTable
        column: OtherTable_ID
    ```

    Under `indexes:`:

    ```yaml
    indexes:
      - name: IX_ThisTable_OtherTable
        columns: [OtherTable_ID]
    ```

4. Validate:

    ```bash
    uv run pytest
    ```

5. Generate a migration script:

    ```bash
    uv run python tools/schema_migrate/generate_migration.py --table TableName
    ```

!!! warning
    Every schema change requires a migration script AND a rollback script before merging.

---

## Add a new table

1. Create `schema_dictionary/tables/NewTable.yaml`. The filename must match the `table.name` value exactly (case-sensitive).

    ```yaml
    _format_version: "1.0"
    table:
      name: NewTable
      schema: dbo
      description: "What this table stores."
      columns:
        - name: NewTable_ID
          logical_type: integer
          nullable: false
          identity: true
          description: "Auto-generated primary key."
        - name: Label
          logical_type: string
          max_length: 255
          nullable: false
          description: "A short label."
      primary_key: [NewTable_ID]
    ```

2. Validate:

    ```bash
    uv run pytest
    ```

3. Generate the migration script:

    ```bash
    uv run python tools/schema_migrate/generate_migration.py --table NewTable
    ```

!!! tip
    Supported logical types: `integer`, `biginteger`, `smallinteger`, `float64`, `float32`, `boolean`, `timestamp`, `date`, `string` (requires `max_length`), `text`, `decimal` (requires `precision` + `scale`), `binary`, `binary_large`.

---

## Add a view

1. Create `schema_dictionary/views/ViewName.yaml`. The filename must match `view.name` exactly.

    ```yaml
    _format_version: "1.0"
    view:
      name: ViewName
      schema: dbo
      description: "What this view shows."
      view_definition: |
        SELECT t.Col1, t.Col2
        FROM [dbo].[SomeTable] t
        WHERE t.Active = 1
      columns:
        - name: Col1
          sql_data_type: INT
          source_table: SomeTable
          source_column: Col1
          description: "The first column."
        - name: Col2
          sql_data_type: NVARCHAR(255)
          source_table: SomeTable
          source_column: Col2
          description: "The second column."
    ```

2. Validate:

    ```bash
    uv run pytest
    ```

!!! note
    Views do not need migration scripts. `CREATE OR ALTER VIEW` is idempotent and is included in the generated DDL automatically.

---

## Add a value set

Value sets are controlled vocabularies (lists of allowed values for a field). They live in `dictionary.json`, not in YAML.

1. Open `src/open_dateaubase/dictionary.json`.

2. Add a `valueSet` part and its `valueSetMember` children following the existing pattern in the file:

    ```json
    {
      "Part_type": "valueSet",
      "Part_name": "MyValueSet",
      "description": "Allowed values for MyField."
    },
    {
      "Part_type": "valueSetMember",
      "Part_name": "Option1",
      "valueSet": "MyValueSet",
      "description": "First allowed value."
    }
    ```

3. Validate that the Pydantic model accepts the new entries:

    ```bash
    uv run pytest
    ```

!!! note
    Value sets are not table structure. Do not add them to YAML files. The Pydantic models in `src/open_dateaubase/data_model/models.py` validate `dictionary.json` at import time.

---

## Regenerate documentation artifacts

After any YAML or `dictionary.json` change, rebuild the docs site to update the ERD, tables reference, and views reference:

```bash
uv run mkdocs build
```

To preview locally:

```bash
uv run mkdocs serve
```
