# Current Schema Generation — Audit

*Produced as part of Phase 0 (Foundation — Migration Infrastructure)*

---

## Overview

The repository uses a **single-source-of-truth JSON dictionary** with **Pydantic validation** to drive all schema-related outputs. A single edit to `dictionary.json` produces SQL DDL, interactive ERD diagrams, and Markdown documentation.

---

## Source of Truth

**File:** `src/open_dateaubase/dictionary.json`

The dictionary is a flat list of "parts", each representing one schema element (table, column, foreign key, value set, etc.). Parts are linked by `Part_ID` references.

**Pydantic validation model:** `src/open_dateaubase/data_model/models.py`

Enforced constraints include:
- Part_ID uniqueness across the entire dictionary
- Primary key IDs must end with `_ID`
- Table and view names cannot contain spaces
- All cross-references point to existing parts
- FK relationship metadata consistency

---

## DDL Generation Entry Point

```bash
python scripts/orchestrate_docs.py \
    src/open_dateaubase/dictionary.json \
    docs/reference \
    sql_generation_scripts \
    docs/assets \
    mssql
```

This triggers (in order):
1. `scripts/generate_sql.py` → `sql_generation_scripts/v{version}_as-designed_{db}.sql`
2. `scripts/generate_erd.py` → `docs/assets/erd_interactive.html`
3. `scripts/generate_dictionary_reference.py` → `docs/reference/*.md`

**SQL generation logic** (`generate_sql.py`):
1. Parse and validate `dictionary.json` via Pydantic
2. Build tables dict, value sets dict, views dict
3. Validate no circular FK dependencies
4. Pass 1: `CREATE TABLE` (all tables, no FKs)
5. Pass 2: `ALTER TABLE … ADD CONSTRAINT FOREIGN KEY` (dependency-ordered)
6. Pass 3: `CREATE VIEW` (if any)

---

## Part Types

| Part_type | Count | Meaning |
|---|---|---|
| `table` | 23 | Physical database tables |
| `key` | 14 | Primary key fields (ID columns) |
| `property` | 77 | Regular columns |
| `compositeKeyFirst` | embedded | First column of a composite PK |
| `compositeKeySecond` | 1 | Second column of a composite PK |
| `valueSet` | 1 | Controlled vocabulary |
| `valueSetMember` | 10 | Enumeration values |
| `view` | 0 | Database views (structure defined, none used yet) |
| `viewColumn` | 0 | View columns (structure defined, none used yet) |
| `parentKey` | — | Hierarchical self-reference |

---

## All Tables (23)

### Measurement core

| Table | Primary Key | Notes |
|---|---|---|
| `value` | `Value_ID` | High-frequency scalar measurements; FK → metadata, comments |
| `metadata` | `Metadata_ID` | Context aggregator; all columns are FKs |
| `comments` | `Comment_ID` | Free-text notes linked to values |

### Physical infrastructure

| Table | Primary Key | Notes |
|---|---|---|
| `equipment` | `Equipment_ID` | Physical instrument instances |
| `equipment_model` | `Equipment_model_ID` | Instrument type specifications |
| `equipment_model_has_Parameter` | `(Equipment_model_ID, Parameter_ID)` | Junction |
| `equipment_model_has_procedures` | `(Equipment_model_ID, Procedure_ID)` | Junction |

### Parameters & methods

| Table | Primary Key | Notes |
|---|---|---|
| `parameter` | `Parameter_ID` | Measured analytes (pH, TSS, …) |
| `unit` | `Unit_ID` | SI and measurement units |
| `procedures` | `Procedure_ID` | SOPs, calibration, ISO methods |
| `parameter_has_procedures` | `(Parameter_ID, Procedure_ID)` | Junction |

### Purpose & conditions

| Table | Primary Key | Notes |
|---|---|---|
| `purpose` | `Purpose_ID` | Measurement aim (online, lab, calibration, …) |
| `weather_condition` | `Condition_ID` | Prevailing weather |

### Site & location

| Table | Primary Key | Notes |
|---|---|---|
| `site` | `Site_ID` | Physical site with address |
| `sampling_points` | `Sampling_point_ID` | GPS-tagged sampling location; FK → site |
| `watershed` | `Watershed_ID` | Watershed area definitions |
| `hydrological_characteristics` | `Watershed_ID` (1-to-1) | Land-use percentages |
| `urban_characteristics` | `Watershed_ID` (1-to-1) | Urban land-use percentages |

### Project management

| Table | Primary Key | Notes |
|---|---|---|
| `project` | `Project_ID` | Research/monitoring projects |
| `contact` | `Contact_ID` | Personnel/organisations |
| `project_has_contact` | `(Project_ID, Contact_ID)` | Junction |
| `project_has_equipment` | `(Project_ID, Equipment_ID)` | Junction |
| `project_has_sampling_points` | `(Project_ID, Sampling_point_ID)` | Junction |

---

## Foreign Key Graph (27 relationships)

```
comments        →  value                (Comment_ID)
metadata        →  value                (Metadata_ID)
equipment_model →  equipment            (Equipment_model_ID)
equipment_model →  equipment_model_has_Parameter   (Equipment_model_ID)
equipment_model →  equipment_model_has_procedures  (Equipment_model_ID)
parameter       →  equipment_model_has_Parameter   (Parameter_ID)
parameter       →  parameter_has_procedures        (Parameter_ID)
parameter       →  metadata             (Parameter_ID)
procedures      →  equipment_model_has_procedures  (Procedure_ID)
procedures      →  parameter_has_procedures        (Procedure_ID)
procedures      →  metadata             (Procedure_ID)
project         →  metadata             (Project_ID)
project         →  project_has_contact  (Project_ID)
project         →  project_has_equipment(Project_ID)
project         →  project_has_sampling_points     (Project_ID)
contact         →  project_has_contact  (Contact_ID)
contact         →  metadata             (Contact_ID)
equipment       →  project_has_equipment(Equipment_ID)
equipment       →  metadata             (Equipment_ID)
purpose         →  metadata             (Purpose_ID)
sampling_points →  project_has_sampling_points     (Sampling_point_ID)
sampling_points →  metadata             (Sampling_point_ID)
weather_condition→  metadata            (Condition_ID)
unit            →  metadata             (Unit_ID)
unit            →  parameter            (Unit_ID)
watershed       →  site                 (Watershed_ID)
watershed       →  hydrological_characteristics    (Watershed_ID)
watershed       →  urban_characteristics           (Watershed_ID)
```

---

## Naming Conventions in Generated DDL

| Element | Convention | Example |
|---|---|---|
| Table names | lowercase, square-bracketed | `[comments]` |
| Column names | PascalCase, square-bracketed | `[Comment_ID]` |
| Primary keys | `PK_{tablename}` | `PK_comments` |
| Foreign keys | `FK_{source_table}_{source_field}` | `FK_value_Comment_ID` |

Table-prefixed fields (e.g. `site_City` → `[City]`) have the prefix stripped in DDL generation.

---

## Hardcoded Table/Column References (Coupling Points)

| File | Location | What is hardcoded |
|---|---|---|
| `scripts/generate_sql.py` | `extract_field_name()` | Field-name normalisation logic (strips table prefix, handles `_ID` suffix) |
| `scripts/generate_erd.py` | FK target inference | Converts `Contact_ID` → `contact` (strips `_ID`, lowercases) |
| `scripts/orchestrate_docs.py` | Line 36 | Output filename `erd_interactive.html` |
| `tests/fixtures/sample_dictionary.py` | Throughout | Sample table/field names used in unit tests |

No application code executes raw SQL with hardcoded table names. All SQL is generated from `dictionary.json`.

---

## Current Limitations (Motivating Phase 0)

1. **No migration tooling** — schema changes produce a full `CREATE TABLE` script, not incremental `ALTER TABLE` scripts.
2. **No version tracking** — the database has no record of which schema version is deployed.
3. **No rollback scripts** — reverting a schema change requires manual SQL.
4. **MSSQL-only** — PostgreSQL types are stubbed but not implemented.
5. **JSON is brittle at scale** — a single large JSON file becomes hard to review and merge; YAML per-table files are easier.
6. **No CI validation** — broken FK references are caught only at generation time, not automatically.
