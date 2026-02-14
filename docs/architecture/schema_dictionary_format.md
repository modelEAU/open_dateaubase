# Schema Dictionary Format Specification

*Version 1.0 — Phase 0 deliverable*

---

## Purpose

This document specifies the YAML format used to define all database tables in the
`schema_dictionary/tables/` directory. Each table is defined in its own file.
The files are the **single source of truth** for schema generation, migration
diffing, and documentation generation.

---

## Design Goals

| Goal | Decision |
|---|---|
| Platform-agnostic | No MSSQL/PostgreSQL-specific types at this layer; a *type renderer* maps logical types to platform DDL |
| Human-readable | YAML, one file per table, reviewed in PRs like code |
| Self-documenting | Every table and column has a `description` field |
| Version-controlled | The file set as a whole is tagged with a schema version |
| Diff-friendly | Flat structure; adding a column = adding a few lines, easy to review |
| Complete | Covers tables, columns, PKs, FKs, unique constraints, indexes, check constraints |

---

## Logical Types

The `logical_type` field abstracts over SQL dialects. The type renderer (in
`tools/schema_migrate/render.py`) maps logical types to platform SQL types.

| Logical type | MSSQL | PostgreSQL | Notes |
|---|---|---|---|
| `integer` | `INT` | `INTEGER` | |
| `biginteger` | `BIGINT` | `BIGINT` | |
| `smallinteger` | `SMALLINT` | `SMALLINT` | |
| `float64` | `FLOAT` | `DOUBLE PRECISION` | |
| `float32` | `REAL` | `REAL` | |
| `decimal` | `NUMERIC(p,s)` | `NUMERIC(p,s)` | requires `precision` and `scale` |
| `string` | `NVARCHAR(n)` | `VARCHAR(n)` | `max_length` required; use `max` for unlimited |
| `text` | `NVARCHAR(MAX)` | `TEXT` | unlimited text |
| `boolean` | `BIT` | `BOOLEAN` | |
| `timestamp` | `DATETIME2(p)` | `TIMESTAMP(p)` | `precision` defaults to 7 |
| `date` | `DATE` | `DATE` | |
| `binary` | `VARBINARY(n)` | `BYTEA` | |
| `binary_large` | `VARBINARY(MAX)` | `BYTEA` | |

---

## File Layout

```
schema_dictionary/
  format_version.yaml          # declares the dictionary format version
  version.yaml                 # declares the schema version (data model version)
  tables/
    {TableName}.yaml           # one file per table, PascalCase
```

---

## Table File Format

```yaml
_format_version: "1.0"        # always present; validated by tooling
table:
  name: <TableName>            # PascalCase; must match the filename (minus .yaml)
  schema: dbo                  # database schema (dbo for MSSQL, public for PostgreSQL)
  description: "<one sentence>"

  columns:
    - name: <ColumnName>       # PascalCase
      logical_type: <type>     # see Logical Types table above
      # type modifiers (as needed):
      max_length: <int|"max">  # for string type
      precision: <int>         # for decimal or timestamp
      scale: <int>             # for decimal
      nullable: <true|false>
      identity: <true|false>   # auto-increment / serial; default false
      default: <value|"CURRENT_TIMESTAMP">   # optional
      description: "<one sentence>"          # optional but encouraged

      # foreign key (optional)
      foreign_key:
        table: <TableName>
        column: <ColumnName>

  primary_key: [<col>, ...]    # list of column names

  indexes:                     # optional
    - name: IX_<Table>_<Cols>
      columns: [<col>, ...]
      unique: <true|false>     # default false

  unique_constraints:          # optional; shorthand for unique single-column indexes
    - name: UQ_<Table>_<Cols>
      columns: [<col>, ...]

  check_constraints:           # optional
    - name: CK_<Table>_<Description>
      expression: "<SQL expression using column names>"
```

---

## Naming Conventions

| Element | Convention | Example |
|---|---|---|
| Tables | PascalCase | `EquipmentEvent` |
| Columns | PascalCase | `MetaDataID` |
| Files | Match table name | `EquipmentEvent.yaml` |
| PKs | `PK_{Table}` | `PK_EquipmentEvent` |
| FKs | `FK_{Child}_{Parent}` | `FK_Value_MetaData` |
| Indexes | `IX_{Table}_{Cols}` | `IX_Value_tstamp` |
| Unique | `UQ_{Table}_{Cols}` | `UQ_WavelengthBin_AxisIndex` |
| Checks | `CK_{Table}_{Desc}` | `CK_DataLineage_Role` |
| Defaults | `DF_{Table}_{Col}` | `DF_MetaData_ProcessingDegree` |

---

## Example — Simple Lookup Table

```yaml
# schema_dictionary/tables/Unit.yaml
_format_version: "1.0"
table:
  name: Unit
  schema: dbo
  description: "SI and measurement units used for reported values"
  columns:
    - name: UnitID
      logical_type: integer
      nullable: false
      identity: true
      description: "Surrogate primary key"
    - name: Unit
      logical_type: string
      max_length: 100
      nullable: false
      description: "Unit symbol or abbreviation (e.g. mg/L, °C)"
  primary_key: [UnitID]
```

---

## Example — Complex Table with Composite PK and FKs

```yaml
# schema_dictionary/tables/MetaData.yaml
_format_version: "1.0"
table:
  name: MetaData
  schema: dbo
  description: "Central context aggregator linking every measurement to its full provenance"
  columns:
    - name: MetaDataID
      logical_type: integer
      nullable: false
      identity: true
    - name: ProjectID
      logical_type: integer
      nullable: true
      foreign_key:
        table: Project
        column: ProjectID
    - name: ContactID
      logical_type: integer
      nullable: true
      foreign_key:
        table: Contact
        column: ContactID
    - name: EquipmentID
      logical_type: integer
      nullable: true
      foreign_key:
        table: Equipment
        column: EquipmentID
    - name: ParameterID
      logical_type: integer
      nullable: true
      foreign_key:
        table: Parameter
        column: ParameterID
    - name: ProcedureID
      logical_type: integer
      nullable: true
      foreign_key:
        table: Procedures
        column: ProcedureID
    - name: UnitID
      logical_type: integer
      nullable: true
      foreign_key:
        table: Unit
        column: UnitID
    - name: PurposeID
      logical_type: integer
      nullable: true
      foreign_key:
        table: Purpose
        column: PurposeID
    - name: SamplingPointID
      logical_type: integer
      nullable: true
      foreign_key:
        table: SamplingPoints
        column: SamplingPointID
    - name: ConditionID
      logical_type: integer
      nullable: true
      foreign_key:
        table: WeatherCondition
        column: ConditionID
  primary_key: [MetaDataID]
```

---

## Validation Rules (enforced by tooling)

1. `_format_version` must be present and match a known version.
2. `table.name` must match the filename (case-sensitive, minus `.yaml`).
3. All columns in `primary_key` must exist in `columns`.
4. All FK `table` references must correspond to an existing YAML file.
5. All FK `column` references must exist in the referenced table's YAML.
6. Index/constraint column references must exist in the table.
7. No duplicate column names within a table.
8. `identity: true` is only valid on `integer` and `biginteger` columns.
9. `max_length` is required when `logical_type: string`.
10. `precision` and `scale` are required when `logical_type: decimal`.
