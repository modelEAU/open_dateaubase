## Phase 0: Foundation — Migration Infrastructure

**Goal:** Establish the tooling that makes all subsequent phases safe and repeatable.

**Business justification:** Without this, every subsequent change is a manual, error-prone, unrepeatable process. This phase pays for itself immediately.

### Task 0.1: Audit the Current State

```markdown
Task: Understand the current schema generation approach

1. Find and read all files that define the current database schema 
   dictionary (likely Python dicts, JSON, or YAML files that generate 
   SQL DDL)
2. List every table currently defined, with columns and relationships
3. Identify how DDL is currently generated (what script, what template 
   engine, what output)
4. Document findings in a new file: docs/architecture/current_schema_generation.md
5. Identify all places in the codebase that reference table or column 
   names directly (these are coupling points)

Acceptance criteria:
- [ ] Document exists and accurately describes the current process
- [ ] Every existing table is listed with its columns
- [ ] The DDL generation entry point is identified
- [ ] All hardcoded table/column name references are catalogued
```

### Task 0.2: Design the YAML Dictionary Format

```markdown
Task: Define the canonical YAML schema format

Create a schema dictionary format that:
- Is database-platform-agnostic (no MSSQL-specific types at this layer)
- Supports tables, columns, types, nullability, defaults, PKs, FKs, 
  indexes, check constraints
- Is version-tagged
- Can represent the ENTIRE current schema faithfully

Deliverables:
1. docs/architecture/schema_dictionary_format.md — specification of the 
   YAML format with examples
2. schema_dictionary/format_version.yaml — meta file declaring the 
   dictionary format version
3. One example table definition to validate the format against the team

Example structure:
```
```yaml
# schema_dictionary/tables/Value.yaml
_format_version: "1.0"
table:
  name: Value
  schema: dbo
  description: "High-frequency scalar time series data"
  columns:
    - name: MetaDataID
      logical_type: integer
      nullable: false
      foreign_key:
        table: MetaData
        column: MetaDataID
    - name: tstamp
      logical_type: timestamp
      precision: 7  # platform maps this to DATETIME2(7) on MSSQL
      nullable: false
    - name: Value
      logical_type: float64
      nullable: true
    - name: QualityCode
      logical_type: integer
      nullable: true
  primary_key: [MetaDataID, tstamp]
  indexes:
    - name: IX_Value_tstamp
      columns: [tstamp]
```
```markdown

Acceptance criteria:
- [ ] Format spec document is clear and complete
- [ ] At least one complex table (MetaData with FKs) is defined in the format
- [ ] Format can represent every feature used in the current schema
- [ ] Team has reviewed and approved the format (placeholder: create a 
      PR for review)
```

### Task 0.3: Convert Existing Schema to YAML Dictionary

```markdown
Task: Migrate all current table definitions to YAML

1. For every table in the current schema, create a YAML file under 
   schema_dictionary/tables/{TableName}.yaml
2. Validate completeness: the YAML files must be able to regenerate 
   the current DDL identically
3. Create schema_dictionary/version.yaml:
   ```yaml
   schema_version: "1.0.0"
   description: "Baseline schema — pre-migration"
   date: "2025-XX-XX"
   ```

Acceptance criteria:
- [ ] Every existing table has a YAML definition
- [ ] A script can read all YAML files and produce the same DDL as 
      the current generator (diff should be zero or cosmetic only)
- [ ] YAML files are committed and version-controlled
- [ ] Old dictionary format is still present (not deleted yet — 
      we're in the "expand" phase)
```

### Task 0.4: Build the Migration Script Generator

```markdown
Task: Create a Python tool that diffs two schema versions and produces 
migration SQL

Location: tools/schema_migrate/

Components:
1. tools/schema_migrate/diff.py
   - Loads two sets of YAML table definitions
   - Computes: new tables, dropped tables, new columns, altered columns,
     new/dropped indexes, new/dropped FKs
   - Returns a structured diff object

2. tools/schema_migrate/render.py
   - Takes a diff object and a platform ('mssql', 'postgres')
   - Produces a migration SQL script using Jinja2 templates
   - Produces a rollback SQL script (reverse operations)

3. tools/schema_migrate/templates/
   - mssql/create_table.sql.j2
   - mssql/add_column.sql.j2
   - mssql/add_foreign_key.sql.j2
   - mssql/drop_column.sql.j2
   - postgres/create_table.sql.j2
   - (etc.)

4. tools/schema_migrate/cli.py
   - CLI entry point:
     python -m tools.schema_migrate --from 1.0.0 --to 1.1.0 --platform mssql
   - Outputs: migrations/v1.0.0_to_v1.1.0_mssql.sql
              migrations/v1.0.0_to_v1.1.0_mssql_rollback.sql

5. tools/schema_migrate/validate.py
   - Loads a YAML schema version
   - Validates referential integrity (all FK targets exist)
   - Validates naming conventions
   - Reports warnings (e.g., "column added without default — will this 
     break existing rows?")

Testing:
- Unit tests for the differ (test_diff.py)
- Unit tests for the renderer (test_render.py) 
- Integration test: generate DDL from v1.0.0 YAML, compare to current 
  DDL output

Acceptance criteria:
- [ ] Can generate a CREATE script for the full v1.0.0 schema
- [ ] Can generate a diff migration between two test versions
- [ ] Rollback scripts are generated for every migration
- [ ] Validation catches missing FK targets
- [ ] CLI works end-to-end
```

### Task 0.5: Add Schema Version Tracking

```markdown
Task: Add the SchemaVersion table to the database

Add to schema_dictionary/tables/SchemaVersion.yaml:
```
```yaml
table:
  name: SchemaVersion
  schema: dbo
  description: "Tracks which schema version is deployed"
  columns:
    - name: VersionID
      logical_type: integer
      nullable: false
      identity: true
    - name: Version
      logical_type: string
      max_length: 20
      nullable: false
    - name: AppliedAt
      logical_type: timestamp
      precision: 7
      nullable: false
      default: CURRENT_TIMESTAMP
    - name: Description
      logical_type: string
      max_length: 500
      nullable: true
    - name: MigrationScript
      logical_type: string
      max_length: 200
      nullable: true
  primary_key: [VersionID]
```
```markdown

This is schema version 1.0.1 (first migration ever).

Generate the migration script using the tool from Task 0.4.
Insert the baseline version record.

Acceptance criteria:
- [ ] SchemaVersion table YAML exists
- [ ] Migration script v1.0.0_to_v1.0.1 is generated and reviewed
- [ ] Rollback script exists
- [ ] After applying, SELECT * FROM dbo.SchemaVersion returns one row
```

### Task 0.6: CI Integration

```markdown
Task: Add schema validation to the CI/test pipeline

1. Add a test that loads all YAML definitions and runs the validator
2. Add a test that ensures every migration has a corresponding rollback
3. Add a test that verifies the YAML version number matches the latest 
   migration target
4. If there's an existing test database setup, add a step that applies 
   all migrations from v1.0.0 to HEAD and verifies the result matches 
   the YAML-generated DDL

Acceptance criteria:
- [ ] CI fails if YAML has broken FK references
- [ ] CI fails if a migration exists without a rollback
- [ ] CI passes on the current codebase
```

---

## Phase 1: Data Shape — Polymorphic Value Storage

**Goal:** Enable storage of spectra, images, and arbitrary arrays without touching `dbo.Value`.

**Business use cases:**
- *"Store UV-Vis spectra from our spectrophotometer alongside scalar sensor data"*
- *"Store microscopy images with timestamps and link them to the same metadata system"*
- *"Query all data for a sampling location regardless of whether it's scalar or spectral"*

### Task 1.1: ValueType Lookup Table

```markdown
Task: Create the ValueType lookup table and add ValueTypeID to MetaData

New YAML files:
- schema_dictionary/tables/ValueType.yaml
- Modified: schema_dictionary/tables/MetaData.yaml (add ValueTypeID column)

Schema version: 1.1.0

ValueType seed data:
  1: Scalar    → dbo.Value
  2: Spectrum  → dbo.ValueSpectrum
  3: Image     → dbo.ValueImage
  4: Array     → dbo.ValueArray

MetaData change:
  - New column: ValueTypeID INT NOT NULL DEFAULT 1
  - New FK: → ValueType(ValueTypeID)

Generate migration v1.0.1_to_v1.1.0:
  - CREATE TABLE dbo.ValueType ...
  - INSERT seed data
  - ALTER TABLE dbo.MetaData ADD ValueTypeID ...
  - ADD CONSTRAINT FK ...

CRITICAL CHECK before generating:
  - The ALTER TABLE on MetaData uses DEFAULT 1, so all existing rows 
    get ValueTypeID=1 (Scalar) automatically
  - This is a non-breaking, expand-only change
  - Verify: no existing queries reference ValueTypeID (they can't — 
    it doesn't exist yet)

Acceptance criteria:
- [ ] YAML files updated
- [ ] Migration script generated and reviewed
- [ ] Rollback script drops the FK, drops the column, drops the table
- [ ] Existing tests still pass after migration
- [ ] SELECT COUNT(*) FROM MetaData WHERE ValueTypeID != 1 returns 0
```

### Task 1.2: Wavelength Infrastructure

```markdown
Task: Create WavelengthAxis and WavelengthBin tables

New YAML files:
- schema_dictionary/tables/WavelengthAxis.yaml
- schema_dictionary/tables/WavelengthBin.yaml
- Modified: schema_dictionary/tables/MetaData.yaml (add nullable 
  WavelengthAxisID FK)

WavelengthAxis columns:
  - WavelengthAxisID (PK, identity)
  - Name (string, not null)
  - Description (string, nullable)
  - NumberOfChannels (integer, not null)
  - MinWavelength_nm (float64, not null)
  - MaxWavelength_nm (float64, not null)

WavelengthBin columns:
  - WavelengthBinID (PK, identity)
  - WavelengthAxisID (FK → WavelengthAxis, not null)
  - BinIndex (integer, not null) — 0-based ordinal
  - Wavelength_nm (float64, not null) — center wavelength
  - Unique constraint: (WavelengthAxisID, BinIndex)

MetaData change:
  - New column: WavelengthAxisID INT NULL (nullable — only relevant 
    for spectral data)
  - New FK: → WavelengthAxis(WavelengthAxisID)

Generate migration and rollback.

Acceptance criteria:
- [ ] Tables created
- [ ] Can insert a test wavelength axis with 5 bins
- [ ] MetaData rows with ValueTypeID=1 have WavelengthAxisID=NULL
- [ ] Existing tests pass
```

### Task 1.3: ValueSpectrum Table

```markdown
Task: Create the ValueSpectrum table

New YAML file:
- schema_dictionary/tables/ValueSpectrum.yaml

Columns:
  - MetaDataID (FK → MetaData, not null)
  - tstamp (timestamp precision 7, not null)
  - WavelengthBinID (FK → WavelengthBin, not null)
  - Value (float64, nullable)
  - QualityCode (integer, nullable)

Primary key: CLUSTERED (MetaDataID, tstamp, WavelengthBinID)

Note on why this PK order:
  - Most queries are "get the full spectrum at time T for sensor X"
  - That's a seek on (MetaDataID, tstamp) followed by a range scan 
    on WavelengthBinID
  - Physically contiguous on disk = fast

Generate migration and rollback.

Write a test:
  1. Create a test WavelengthAxis with 10 bins
  2. Create a test MetaData entry with ValueTypeID=2
  3. Insert one spectrum (10 rows in ValueSpectrum for one timestamp)
  4. Query it back and verify all 10 values are returned in order

Acceptance criteria:
- [ ] Table created with correct PK
- [ ] Test data can be inserted and queried
- [ ] FK constraints enforced (cannot insert with nonexistent BinID)
- [ ] Rollback drops the table cleanly
```

### Task 1.4: ValueImage Table

```markdown
Task: Create the ValueImage table

New YAML file:
- schema_dictionary/tables/ValueImage.yaml

Columns:
  - ValueImageID (PK, bigint identity)
  - MetaDataID (FK → MetaData, not null)
  - tstamp (timestamp precision 7, not null)
  - ImageWidth (integer, not null)
  - ImageHeight (integer, not null)
  - NumberOfChannels (integer, not null, default 3)
  - ImageFormat (string max 20, not null) — 'PNG', 'TIFF', etc.
  - FileSizeBytes (bigint, nullable)
  - StorageBackend (string max 50, not null, default 'FileSystem')
  - StoragePath (string max 1000, not null)
  - Thumbnail (binary_large, nullable)
  - QualityCode (integer, nullable)
  
Constraints:
  - Unique: (MetaDataID, tstamp)
  - Index: (MetaDataID, tstamp)

Generate migration and rollback.

Write a test:
  1. Create a MetaData entry with ValueTypeID=3
  2. Insert an image reference (no actual file needed — just the path)
  3. Query it back

Acceptance criteria:
- [ ] Table created
- [ ] Unique constraint prevents duplicate timestamps for same MetaDataID
- [ ] StoragePath correctly stores long paths
```

### Task 1.5: ValueArray Table

```markdown
Task: Create the ValueArray table

New YAML file:
- schema_dictionary/tables/ValueArray.yaml

Columns:
  - MetaDataID (FK → MetaData, not null)
  - tstamp (timestamp precision 7, not null)
  - ArrayIndex (integer, not null) — 0-based
  - Value (float64, nullable)
  - QualityCode (integer, nullable)

Primary key: CLUSTERED (MetaDataID, tstamp, ArrayIndex)

Generate migration and rollback.

Acceptance criteria:
- [ ] Table created
- [ ] Can store and retrieve a 100-element array at a single timestamp
```

### Task 1.6: Phase 1 Integration Test

```markdown
Task: End-to-end test for the data shape system

Write a test that:
1. Creates MetaData entries for each ValueType (Scalar, Spectrum, 
   Image, Array)
2. Inserts sample data into each corresponding value table
3. Queries MetaData and dispatches to the correct value table based 
   on ValueTypeID
4. Verifies that the dispatch logic works correctly

This test validates the PATTERN, not just individual tables.

Also write a helper function:
  get_values(metadata_id) → dispatches to the right table
  
This becomes the seed of the repository layer.

Acceptance criteria:
- [ ] Test creates all four types of data
- [ ] Dispatcher correctly routes to Value, ValueSpectrum, ValueImage, 
      or ValueArray
- [ ] Test is documented with comments explaining the pattern
```

### Task 1.7: Phase 1 Documentation

```markdown
Task: Document the data shape extension

1. Update docs/ with:
   - docs/architecture/data_shapes.md — explains the pattern, when to 
     use each shape, how to add new ones
   - Updated ER diagram showing new tables
   
2. Update the README or contributing guide with:
   - "How to add a new data shape" checklist
   
3. Ensure the schema_dictionary version is 1.1.0

4. Generate the complete v1.0.1 → 1.1.0 migration script (combined 
   from tasks 1.1–1.5) and its rollback

Acceptance criteria:
- [ ] Documentation is clear enough that a new contributor can understand 
      the pattern
- [ ] Migration script applies cleanly to a fresh v1.0.1 database
- [ ] Rollback script returns the database to v1.0.1 state
```

---

## Phase 2a: Core Context — Campaign and Provenance

**Goal:** Introduce the foundational context concepts that all subsequent phases depend on.

**Business use cases:**
- *"Distinguish between operational data and experimental data"*
- *"Know who collected what data, and as part of which campaign"*
- *"Filter data by campaign: show me only Experiment A's measurements"*

### Task 2a.1: Person Table

```markdown
Task: Create the Person table

New YAML: schema_dictionary/tables/Person.yaml

Columns:
  - PersonID (PK, identity)
  - FullName (string max 200, not null)
  - Email (string max 200, nullable)
  - Affiliation (string max 200, nullable)

Generate migration. This is a standalone table with no dependencies.

Acceptance criteria:
- [ ] Table created
- [ ] Can insert and query persons
```

### Task 2a.2: Campaign Infrastructure

```markdown
Task: Create CampaignType and Campaign tables

New YAMLs:
- schema_dictionary/tables/CampaignType.yaml
- schema_dictionary/tables/Campaign.yaml

CampaignType columns:
  - CampaignTypeID (PK)
  - CampaignTypeName (string max 100, not null)

CampaignType seed data:
  1: Experiment
  2: Operations
  3: Commissioning
  4: Audit

Campaign columns:
  - CampaignID (PK, identity)
  - CampaignTypeID (FK → CampaignType, not null)
  - SiteID (FK → Site, not null)
  - Name (string max 200, not null)
  - Description (string max 2000, nullable)
  - StartDate (timestamp, nullable)
  - EndDate (timestamp, nullable)
  - ProjectID (FK → Project, nullable) — backward compat link

IMPORTANT: The existing Project table/concept is NOT removed or altered.
Campaign wraps it. Some campaigns map to existing projects; others don't.

Acceptance criteria:
- [ ] Both tables created with seed data
- [ ] Campaign references Site (existing table) correctly
- [ ] ProjectID FK works for campaigns that map to existing projects
- [ ] ProjectID can be NULL for new campaigns with no legacy project
```

### Task 2a.3: DataProvenance Lookup and MetaData Columns

```markdown
Task: Add provenance tracking to MetaData

New YAML: schema_dictionary/tables/DataProvenance.yaml

DataProvenance columns:
  - DataProvenanceID (PK)
  - DataProvenanceName (string max 50, not null)

Seed data:
  1: Sensor
  2: Laboratory
  3: Manual Entry
  4: Model Output
  5: External Source

Modified: schema_dictionary/tables/MetaData.yaml — add:
  - DataProvenanceID INT NULL (nullable for backward compat — existing 
    rows don't have this yet)
  - CampaignID INT NULL (FK → Campaign, nullable)

MIGRATION NOTE: 
  - Do NOT set a default for DataProvenanceID yet — we don't know 
    which existing MetaData rows are sensor vs lab
  - A future data migration (Task 2a.4) will backfill this

Generate migration and rollback.

Acceptance criteria:
- [ ] DataProvenance table created with seed data
- [ ] MetaData has new nullable columns
- [ ] Existing MetaData rows are unchanged (NULL for new columns)
- [ ] All existing tests pass (nothing depends on these columns yet)
```

### Task 2a.4: Backfill Existing MetaData Provenance

```markdown
Task: Write a data migration to classify existing MetaData rows

This is a DATA migration, not a schema migration. It should be a 
separate script that:

1. Examines existing MetaData rows
2. Classifies them as Sensor (DataProvenanceID=1) based on available 
   context (e.g., presence of EquipmentID, or naming conventions)
3. Updates the rows
4. Reports how many rows were classified and how many remain NULL

This script should be:
- Idempotent (safe to run multiple times)
- Logged (writes to a migration log what it did)
- Reviewed by someone who knows the existing data

Location: migrations/data/backfill_provenance.sql (or .py)

Acceptance criteria:
- [ ] Script exists and is documented
- [ ] Running it twice produces the same result
- [ ] It does NOT set DataProvenanceID to NOT NULL — that's a future 
      contract step after we're confident all rows are classified
```

### Task 2a.5: Phase 2a Integration Test

```markdown
Task: Test the campaign and provenance system

Write tests that:
1. Create a Site (or use existing)
2. Create two Campaigns at that site (one Experiment, one Operations)
3. Create MetaData entries associated with each campaign
4. Query "all MetaData for Campaign X" and verify correctness
5. Query "all MetaData for Site Y across all campaigns"

Acceptance criteria:
- [ ] Campaign-based filtering works
- [ ] Cross-campaign site queries work
- [ ] Provenance filtering works
```

### Task 2a.6: Phase 2a Documentation

```markdown
Task: Document campaigns and provenance

1. docs/architecture/campaigns_and_provenance.md
   - What is a Campaign vs a Project
   - Migration path from Project to Campaign
   - When to use each DataProvenance value
   
2. Update ER diagram

3. Schema version: 1.2.0

Acceptance criteria:
- [ ] Documentation explains the Campaign concept clearly
- [ ] Migration v1.1.0 → v1.2.0 is clean
```

---

## Phase 2b: Lab Data Support

**Goal:** Enable laboratory measurement data with proper context (sample, lab, analyst).

**Business use cases:**
- *"Record that analyst Marie measured TSS=24.5 mg/L on sample #123 taken from the primary effluent at 08:00"*
- *"Compare lab TSS measurements with sensor TSS measurements at the same location"*
- *"Find all lab results for Campaign X"*

### Task 2b.1: Laboratory and Sample Tables

```markdown
Task: Create Laboratory and Sample tables

New YAMLs:
- schema_dictionary/tables/Laboratory.yaml
- schema_dictionary/tables/Sample.yaml

Laboratory columns:
  - LaboratoryID (PK, identity)
  - Name (string max 200, not null)
  - SiteID (FK → Site, nullable) — some labs are on-site, some aren't
  - Description (string max 500, nullable)

Sample columns:
  - SampleID (PK, identity)
  - SamplingLocationID (FK → SamplingLocation, not null)
  - SampledByPersonID (FK → Person, nullable)
  - CampaignID (FK → Campaign, nullable)
  - SampleDateTime (timestamp, not null)
  - SampleType (string max 50, nullable) — 'Grab', 'Composite24h', etc.
  - Description (string max 500, nullable)

Depends on: Phase 2a (Person, Campaign tables must exist)

Generate migration and rollback.

Acceptance criteria:
- [ ] Both tables created
- [ ] Sample correctly references SamplingLocation, Person, Campaign
- [ ] Can model: "Marie took a grab sample from Primary Effluent at 
      08:00 as part of Experiment A"
```

### Task 2b.2: MetaData Lab Context Columns

```markdown
Task: Add lab-specific context to MetaData

Modified: schema_dictionary/tables/MetaData.yaml — add:
  - SampleID INT NULL (FK → Sample)
  - LaboratoryID INT NULL (FK → Laboratory)
  - AnalystPersonID INT NULL (FK → Person)

All nullable — only populated for lab data (DataProvenanceID=2).

Optional CHECK constraint (add to YAML and migration):
  If DataProvenanceID = 2 (Laboratory), then SampleID must not be NULL
  and LaboratoryID must not be NULL.

  NOTE: Only add this CHECK if the team agrees. It enforces data 
  quality but makes ingestion stricter. Discuss before implementing.

Generate migration and rollback.

Acceptance criteria:
- [ ] New columns exist on MetaData
- [ ] Existing rows unaffected (all NULL)
- [ ] Can create a MetaData entry for lab data with all context filled
```

### Task 2b.3: Campaign Resource Junction Tables

```markdown
Task: Create tables that define what resources a campaign uses

New YAMLs:
- schema_dictionary/tables/CampaignSamplingLocation.yaml
- schema_dictionary/tables/CampaignEquipment.yaml
- schema_dictionary/tables/CampaignVariable.yaml

CampaignSamplingLocation:
  - CampaignID (FK, not null)
  - SamplingLocationID (FK, not null)
  - Role (string max 100, nullable)
  - PK: (CampaignID, SamplingLocationID)

CampaignEquipment:
  - CampaignID (FK, not null)
  - EquipmentID (FK, not null)
  - Role (string max 100, nullable)
  - PK: (CampaignID, EquipmentID)

CampaignVariable:
  - CampaignID (FK, not null)
  - VariableID (FK, not null)
  - PK: (CampaignID, VariableID)

Generate migration and rollback.

Write a test:
  Set up the scenario from the conversation:
  - Operations campaign uses: Primary Influent, Basin A, Basin B
  - Experiment A uses: Primary Influent, Basin A
  - Experiment B uses: Primary Influent, Basin B
  - Query: "What locations does Experiment A use?" → Primary Influent, Basin A
  - Query: "What campaigns use Primary Influent?" → all three
  - Query: "What campaigns overlap with Experiment A?" → Operations 
    (shared locations)

Acceptance criteria:
- [ ] Junction tables created
- [ ] Composability scenario works as described
- [ ] Overlap queries return correct results
```

### Task 2b.4: Phase 2b Integration Test and Documentation

```markdown
Task: End-to-end lab data test

Scenario:
1. Create a Laboratory ("ModelEAU Water Quality Lab")
2. Create a Person ("Marie Dupont")
3. Create a Campaign ("TSS Validation Study", type=Experiment)
4. Create a Sample (Primary Effluent, grabbed by Marie, for the campaign)
5. Create a MetaData entry (DataProvenance=Laboratory, linked to sample, 
   lab, analyst, campaign)
6. Insert a scalar value (TSS = 24.5 mg/L)
7. Also create a sensor MetaData entry for the same location and variable
8. Insert sensor values
9. Query: "All TSS data at Primary Effluent" → returns both lab and sensor
10. Query: "Only lab TSS" → filters by DataProvenance
11. Query: "All data for the TSS Validation campaign" → returns campaign-
    specific data

Documentation: docs/architecture/lab_data.md

Schema version: 1.3.0

Acceptance criteria:
- [ ] Full scenario executes correctly
- [ ] Lab and sensor data coexist cleanly
- [ ] Filtering by provenance works
- [ ] Documentation complete
```

---

## Phase 2c: Sensor Lifecycle

**Goal:** Track equipment events (calibration, validation, maintenance) and temporal installations.

**Business use cases:**
- *"When was this sensor last calibrated before the anomalous reading on March 3rd?"*
- *"Show the full lifecycle of sensor TSS_01: installations, calibrations, maintenance"*
- *"Which sensors were at the primary effluent during Q1 2025?"*

### Task 2c.1: Equipment Event Tables

```markdown
Task: Create EquipmentEventType and EquipmentEvent tables

New YAMLs:
- schema_dictionary/tables/EquipmentEventType.yaml
- schema_dictionary/tables/EquipmentEvent.yaml

EquipmentEventType seed data:
  1: Calibration
  2: Validation
  3: Maintenance
  4: Installation
  5: Removal
  6: Firmware Update
  7: Failure
  8: Repair

EquipmentEvent columns:
  - EquipmentEventID (PK, identity)
  - EquipmentID (FK → Equipment, not null)
  - EquipmentEventTypeID (FK → EquipmentEventType, not null)
  - EventDateTime (timestamp, not null)
  - PerformedByPersonID (FK → Person, nullable)
  - CampaignID (FK → Campaign, nullable)
  - Notes (string max 2000, nullable)
  - Index: (EquipmentID, EventDateTime)

Depends on: Phase 2a (Person, Campaign)

Acceptance criteria:
- [ ] Tables created with seed data
- [ ] Can record: "TSS_01 was calibrated by Jean on 2025-03-01 as part 
      of Operations"
- [ ] Index exists for efficient "events for equipment X in time range" 
      queries
```

### Task 2c.2: Equipment Event ↔ MetaData Junction

```markdown
Task: Create EquipmentEventMetaData junction table

New YAML: schema_dictionary/tables/EquipmentEventMetaData.yaml

Columns:
  - EquipmentEventID (FK → EquipmentEvent, not null)
  - MetaDataID (FK → MetaData, not null)
  - Role (string max 50, nullable) — 'Reference Standard', 
    'Sensor Under Test', etc.
  - PK: (EquipmentEventID, MetaDataID)

This links calibration events to the measurements taken during 
calibration (both the reference measurement and the sensor reading).

Write a test:
  1. Create a calibration event for sensor TSS_01
  2. Create two MetaData entries: one for the reference standard, 
     one for the sensor
  3. Link both to the calibration event with appropriate roles
  4. Query: "What measurements are associated with calibration event X?"
  5. Query: "What calibration events involved sensor Y's MetaData?"

Acceptance criteria:
- [ ] Junction table created
- [ ] Many-to-many relationship works
- [ ] Role field correctly distinguishes reference vs sensor-under-test
```

### Task 2c.3: Equipment Installation and Temporal Sampling Locations

```markdown
Task: Create EquipmentInstallation table and add temporal fields to 
SamplingLocation

New YAML: schema_dictionary/tables/EquipmentInstallation.yaml

EquipmentInstallation columns:
  - InstallationID (PK, identity)
  - EquipmentID (FK → Equipment, not null)
  - SamplingLocationID (FK → SamplingLocation, not null)
  - InstalledDate (timestamp, not null)
  - RemovedDate (timestamp, nullable) — NULL = currently installed
  - CampaignID (FK → Campaign, nullable)
  - Notes (string max 500, nullable)
  - Index: (EquipmentID, InstalledDate)
  - Index: (SamplingLocationID, InstalledDate)

Modified: schema_dictionary/tables/SamplingLocation.yaml — add:
  - ValidFrom (timestamp, nullable) — NULL = "always existed"
  - ValidTo (timestamp, nullable) — NULL = "still active"
  - CreatedByCampaignID (FK → Campaign, nullable)

IMPORTANT: Existing Equipment ↔ SamplingLocation relationships in 
MetaData are NOT changed. EquipmentInstallation is an ADDITIONAL 
source of truth for "where was this equipment?" The existing static 
link captures "what was the context when this MetaData was created." 
The installation table captures the full history.

Write a test:
  1. Install sensor TSS_01 at Primary Effluent on Jan 1
  2. Remove it on March 15
  3. Install it at Secondary Effluent on March 16
  4. Query: "Where was TSS_01 on Feb 1?" → Primary Effluent
  5. Query: "Where was TSS_01 on April 1?" → Secondary Effluent
  6. Query: "What sensors were at Primary Effluent on Feb 1?" → TSS_01

Acceptance criteria:
- [ ] Installation history is correctly queryable by time
- [ ] SamplingLocation temporal fields work
- [ ] Existing SamplingLocation rows have NULL ValidFrom/ValidTo 
      (= always active)
```

### Task 2c.4: Phase 2c Documentation

```markdown
Task: Document sensor lifecycle

1. docs/architecture/sensor_lifecycle.md
   - Equipment events model
   - Installation history model
   - Example queries for common use cases
   - "How to record a calibration" step-by-step

2. Update ER diagram

Schema version: 1.4.0

Acceptance criteria:
- [ ] Documentation covers all use cases from business requirements
- [ ] ER diagram is current
```

---

## Phase 2d: Ingestion Routing

**Goal:** Decouple ingestion scripts from hardcoded MetaDataIDs. Scripts identify themselves by equipment+variable; the system resolves the target.

**Business use cases:**
- *"When we move a sensor, we change one row in a routing table — not every script"*
- *"New campaign starts → new routing rules are added → data automatically flows to the right MetaData entries"*
- *"We can audit: this data was routed to MetaDataID X because of routing rule Y"*

### Task 2d.1: IngestionRoute Table

```markdown
Task: Create the IngestionRoute table

New YAML: schema_dictionary/tables/IngestionRoute.yaml

Columns:
  - IngestionRouteID (PK, identity)
  - EquipmentID (FK → Equipment, not null)
  - VariableID (FK → Variable, not null)
  - CampaignID (FK → Campaign, nullable)
  - DataProvenanceID (FK → DataProvenance, not null, default 1)
  - ProcessingDegree (string max 50, not null, default 'Raw')
  - MetaDataID (FK → MetaData, not null) — the resolved target
  - ValidFrom (timestamp, not null)
  - ValidTo (timestamp, nullable) — NULL = currently active
  - CreatedAt (timestamp, not null, default CURRENT_TIMESTAMP)
  - CreatedByPersonID (FK → Person, nullable)
  - Notes (string max 500, nullable)
  - Index: (EquipmentID, VariableID, DataProvenanceID, ProcessingDegree, 
            ValidFrom)

Depends on: Phase 2a (Campaign, DataProvenance, Person)

Acceptance criteria:
- [ ] Table created
- [ ] Can insert routing rules
- [ ] Can query active route for a given equipment+variable+timestamp
```

### Task 2d.2: Route Resolution Logic

```markdown
Task: Write and test the route resolution query/function

This is the core business logic for ingestion. Write it as:
1. A SQL query (for documentation and direct use)
2. A Python function (for the API)

The resolution logic:
  Given (EquipmentID, VariableID, timestamp, provenance='Sensor', 
         processing_degree='Raw'):
  → Find the IngestionRoute where all match AND 
    ValidFrom <= timestamp AND (ValidTo IS NULL OR ValidTo > timestamp)
  → Return MetaDataID
  → Raise error if no route found
  → Raise error if multiple routes found (ambiguous)

Write tests:
1. Happy path: one active route exists → returns MetaDataID
2. No route: → error with helpful message
3. Expired route: ValidTo is in the past → not returned
4. Route transition: route A valid until March 15, route B valid from 
   March 15 → correct resolution at boundary
5. Ambiguous routes: two active routes for same key → error

Acceptance criteria:
- [ ] Resolution works for all test cases
- [ ] Error messages are actionable ("No route for Equipment 42, 
      Variable 7 at 2025-03-16. Active routes: [list]")
- [ ] Boundary conditions at ValidFrom/ValidTo are correct
```

### Task 2d.3: Backfill Existing Routing

```markdown
Task: Create initial IngestionRoute entries for existing MetaData

Write a data migration script that:
1. For each existing MetaData row that has an EquipmentID:
   - Creates an IngestionRoute entry with:
     - EquipmentID = MetaData.EquipmentID
     - VariableID = MetaData.VariableID
     - MetaDataID = the MetaData row's ID
     - DataProvenanceID = MetaData.DataProvenanceID (or 1 if NULL)
     - ProcessingDegree = 'Raw'
     - ValidFrom = earliest timestamp in dbo.Value for this MetaDataID
       (or a sensible default like '2000-01-01')
     - ValidTo = NULL (still active)

2. Report statistics: how many routes created, any MetaData rows 
   without EquipmentID (these are lab or manual data — expected)

This script should be idempotent.

Acceptance criteria:
- [ ] Script creates routes for all equipment-based MetaData
- [ ] Running twice doesn't create duplicates
- [ ] Route resolution works for existing data after backfill
```

### Task 2d.4: Phase 2d Documentation

```markdown
Task: Document the ingestion routing system

1. docs/architecture/ingestion_routing.md
   - How routing works
   - How to add a new route (e.g., new sensor installed)
   - How to handle equipment moves
   - How to handle campaign transitions
   - Troubleshooting: "my data isn't being ingested" → check routes

2. docs/operations/equipment_move_checklist.md
   - Step-by-step: moving a sensor from location A to location B
   - What to update: EquipmentInstallation, IngestionRoute
   - How to verify: check that new data flows to new MetaDataID

Schema version: 1.5.0

Acceptance criteria:
- [ ] Documentation covers all operational scenarios
- [ ] Checklist is actionable by a non-developer
```

---

## Phase 3: Processing Lineage

**Goal:** Track the history of data transformations, linking raw data to its processed derivatives.

**Business use cases:**
- *"Show me all versions of this time series: raw, cleaned, interpolated"*
- *"What processing was applied to produce the validated dataset?"*
- *"Reproduce the processing: re-run the same steps with new parameters"*
- *"metEAUdata writes its processing history to the database automatically"*

### Task 3.1: ProcessingStep and DataLineage Tables

```markdown
Task: Create the processing lineage tables

New YAMLs:
- schema_dictionary/tables/ProcessingStep.yaml
- schema_dictionary/tables/DataLineage.yaml

ProcessingStep columns:
  - ProcessingStepID (PK, identity)
  - Name (string max 200, not null)
  - Description (string max 2000, nullable)
  - MethodName (string max 200, nullable) — e.g., 'outlier_removal'
  - MethodVersion (string max 50, nullable) — e.g., 'metEAUdata v0.3.2'
  - Parameters (string max, nullable) — JSON blob of config
  - ExecutedAt (timestamp, nullable)
  - ExecutedByPersonID (FK → Person, nullable)

DataLineage columns:
  - DataLineageID (PK, identity)
  - ProcessingStepID (FK → ProcessingStep, not null)
  - MetaDataID (FK → MetaData, not null)
  - Role (string max 20, not null) — 'Input' or 'Output'
  - CHECK constraint: Role IN ('Input', 'Output')
  - Index: (MetaDataID)
  - Index: (ProcessingStepID, Role)

Acceptance criteria:
- [ ] Tables created
- [ ] Can model: Raw TSS → outlier_removal → Cleaned TSS → 
      interpolation → Interpolated TSS
- [ ] Each step has inputs and outputs
```

### Task 3.2: MetaData ProcessingDegree Column

```markdown
Task: Add ProcessingDegree to MetaData

Modified: schema_dictionary/tables/MetaData.yaml — add:
  - ProcessingDegree (string max 50, nullable, default 'Raw')

NOTE: This is a DENORMALIZED convenience field. The ground truth is 
the lineage graph. But it makes filtering ("show me only raw data") 
trivially fast without graph traversal.

Backfill: All existing MetaData rows get ProcessingDegree = 'Raw' 
(they are raw — no processing has been recorded).

Acceptance criteria:
- [ ] Column added with correct default
- [ ] Existing rows have 'Raw'
- [ ] Can filter MetaData by ProcessingDegree
```

### Task 3.3: Lineage Graph Queries

```markdown
Task: Write and test lineage traversal queries

Implement as SQL queries and Python functions:

1. get_lineage_forward(metadata_id):
   "What was this data processed into?"
   → Follow DataLineage where Role='Input', get the ProcessingStep, 
     then get the outputs

2. get_lineage_backward(metadata_id):
   "Where did this processed data come from?"
   → Follow DataLineage where Role='Output', get the ProcessingStep, 
     then get the inputs

3. get_full_lineage_tree(metadata_id):
   "Show the complete processing chain from raw to final"
   → Recursive traversal (use a CTE or iterative Python)

4. get_all_processing_degrees(location, variable, time_range):
   "Show all versions of this time series"
   → Query MetaData for matching location+variable with different 
     ProcessingDegree values, return values from each

Write tests for each, including:
- Simple chain: Raw → Cleaned → Validated (linear)
- Fan-out: Raw → Cleaned AND Raw → Aggregated (branching)
- Fan-in: TSS_raw + Turbidity_raw → Derived_TSS (multiple inputs)

Acceptance criteria:
- [ ] All four query patterns work
- [ ] Linear, branching, and fan-in topologies are handled
- [ ] Recursive traversal terminates (no infinite loops on acyclic data)
- [ ] Results include step names, parameters, and execution timestamps
```

### Task 3.4: metEAUdata Integration Spec

```markdown
Task: Design the interface between metEAUdata and the lineage tables

This is a SPECIFICATION task, not implementation. The implementation 
will happen in the metEAUdata repo.

Deliverable: docs/architecture/metEAUdata_integration.md

Contents:
1. Mapping from metEAUdata concepts to database tables:
   - TimeSeries → MetaData + Value table
   - Processing step → ProcessingStep row
   - Input/output links → DataLineage rows
   
2. Workflow: When metEAUdata processes data:
   a. Create a new MetaData entry for the output (same location, 
      variable, unit; different ProcessingDegree)
   b. Determine the correct value table (same shape as input)
   c. Write processed values
   d. Create a ProcessingStep row with method name, version, parameters
   e. Create DataLineage rows linking input MetaData → step → output MetaData
   f. If using the ingestion API: POST /api/v1/ingest/processed with 
      lineage metadata in the request body

3. API endpoint specification for processed data ingestion:
   POST /api/v1/ingest/processed
   Body: {
     "source_metadata_ids": [42],
     "processing": {
       "method": "outlier_removal",
       "method_version": "metEAUdata 0.3.2",
       "parameters": {"method": "zscore", "threshold": 3.0}
     },
     "output": {
       "processing_degree": "Cleaned",
       "values": [{"tstamp": "...", "value": 24.5}, ...]
     }
   }

Acceptance criteria:
- [ ] Spec is reviewed by the metEAUdata maintainer
- [ ] API endpoint contract is defined
- [ ] Data flow diagram shows the complete write path
```

### Task 3.5: Phase 3 Documentation

```markdown
Task: Document the lineage system

1. docs/architecture/processing_lineage.md
2. Updated ER diagram (final)

Schema version: 1.6.0

Acceptance criteria:
- [ ] Documentation explains lineage concepts clearly
- [ ] Examples show how to trace data back to its raw source
- [ ] ER diagram includes all tables from all phases
```

---

## Phase 4: API Layer

**Goal:** Create a stable, versioned API that becomes the single entry point for all data operations.

**Business use cases:**
- *"All scripts use the API instead of direct SQL — so schema changes don't break them"*
- *"New team members can start ingesting data without knowing the database schema"*
- *"We can add new tables without breaking any existing client"*

### Task 4.1: API Skeleton and Versioning

```markdown
Task: Set up the API project structure

Technology choice: FastAPI (Python, async, automatic OpenAPI docs)
  — or whatever the team prefers. The plan is framework-agnostic.

Structure:
  api/
    __init__.py
    main.py                  # FastAPI app, versioned router mounting
    v1/
      __init__.py
      router.py              # Mounts all v1 sub-routers
      schemas/
        timeseries.py        # Pydantic response/request models
        metadata.py
        campaigns.py
        equipment.py
        lineage.py
        ingestion.py
      endpoints/
        timeseries.py        # GET /api/v1/timeseries
        metadata.py          # GET /api/v1/metadata
        campaigns.py         # GET /api/v1/campaigns
        equipment.py         # GET /api/v1/equipment
        lineage.py           # GET /api/v1/lineage
        ingest.py            # POST /api/v1/ingest/*
      services/
        timeseries_service.py   # Business logic
        routing_service.py      # Ingestion route resolution
        lineage_service.py      # Lineage graph traversal
      repositories/
        value_repository.py     # Dispatches to correct value table
        metadata_repository.py
        campaign_repository.py
    database.py               # DB connection/session management
    config.py                 # Environment configuration

Key design rules:
- Endpoints NEVER execute SQL directly
- Endpoints call services
- Services call repositories
- Repositories execute SQL
- Response schemas are the API contract — they change carefully

Acceptance criteria:
- [ ] API starts and serves /docs (OpenAPI UI)
- [ ] /api/v1/ prefix is mounted
- [ ] At least one endpoint works (e.g., GET /api/v1/health)
- [ ] Database connection is configured
```

### Task 4.2: Core Read Endpoints

```markdown
Task: Implement read endpoints for existing data

Endpoints:
  GET /api/v1/sites
  GET /api/v1/sites/{id}
  GET /api/v1/sites/{id}/sampling-locations
  GET /api/v1/metadata?site=...&location=...&variable=...&provenance=...
  GET /api/v1/timeseries/{metadata_id}?from=...&to=...
  GET /api/v1/timeseries/by-context?location=...&variable=...&from=...&to=...

The timeseries endpoint must:
- Look up the MetaData entry
- Check ValueTypeID
- Dispatch to the correct value table
- Return a uniform response format regardless of underlying table

Response schema for timeseries:
  {
    "metadata_id": 42,
    "location": "Primary Effluent",
    "variable": "TSS",
    "unit": "mg/L",
    "data_shape": "Scalar",
    "provenance": "Sensor",
    "processing_degree": "Raw",
    "campaign": "Operations 2025",
    "data": [
      {"timestamp": "2025-01-01T00:00:00", "value": 24.5, "quality": 1},
      ...
    ]
  }

Acceptance criteria:
- [ ] All endpoints return correct data from the current database
- [ ] Response schemas are defined as Pydantic models
- [ ] Value dispatch works for Scalar (and Spectrum/Image/Array when 
      those tables exist)
- [ ] Query parameters filter correctly
- [ ] Pagination is implemented for large result sets
```

### Task 4.3: Ingestion Endpoints

```markdown
Task: Implement write endpoints for data ingestion

Endpoints:
  POST /api/v1/ingest/sensor
    Body: { equipment_id, variable_id, values: [{tstamp, value, quality}] }
    → Resolves route via IngestionRoute table
    → Writes to appropriate value table
    → Returns: { metadata_id, rows_written }

  POST /api/v1/ingest/lab
    Body: { sample_id, variable_id, laboratory_id, analyst_person_id,
            values: [{tstamp, value, quality}] }
    → Finds or creates MetaData entry
    → Writes values
    → Returns: { metadata_id, rows_written }

  POST /api/v1/ingest/processed
    Body: { source_metadata_ids: [...], processing: {...}, 
            output: { processing_degree, values: [...] } }
    → Creates ProcessingStep and DataLineage
    → Creates new MetaData entry
    → Writes processed values
    → Returns: { metadata_id, processing_step_id, rows_written }

Each endpoint must:
- Validate all foreign keys exist before writing
- Return clear errors for routing failures
- Be idempotent where possible (e.g., upserting values)

Acceptance criteria:
- [ ] Sensor ingestion resolves routes correctly
- [ ] Lab ingestion creates proper context
- [ ] Processed data ingestion creates lineage graph
- [ ] Error responses are actionable
- [ ] All three endpoints have integration tests
```

### Task 4.4: Context Query Endpoints

```markdown
Task: Implement the "full context" query endpoints

These are the complex business-logic queries:

  GET /api/v1/timeseries/{metadata_id}/full-context?from=...&to=...
    Returns:
    - All processing degrees of this time series (multiple lines)
    - Equipment events in the time range (calibrations, maintenance)
    - Processing lineage graph
    - Campaign information

  GET /api/v1/equipment/{id}/lifecycle?from=...&to=...
    Returns:
    - Installation history
    - All events (calibrations, validations, maintenance)
    - Associated campaigns

  GET /api/v1/campaigns/{id}/context
    Returns:
    - Sampling locations used
    - Equipment used
    - Variables measured
    - Associated MetaData entries
    - Time range

These endpoints assemble data from many tables — this is the business 
logic layer that justifies having an API.

Acceptance criteria:
- [ ] Full-context endpoint returns all relevant information
- [ ] Equipment lifecycle is a coherent narrative
- [ ] Campaign context is complete
- [ ] Response times are acceptable (< 2s for typical queries)
```

### Task 4.5: API Stability Tests

```markdown
Task: Create contract tests that prevent accidental API breakage

For every response schema:
1. Write a test that asserts the schema has specific required fields
2. Write a test that asserts field types
3. Store example responses as JSON fixtures
4. Test that the API still produces responses matching the fixtures 
   (modulo actual data values)

These tests should FAIL if someone:
- Removes a field from a response
- Changes a field type
- Renames a field

These tests should PASS if someone:
- Adds a new optional field
- Adds a new endpoint

Location: tests/api/contract/

Acceptance criteria:
- [ ] Every endpoint has a contract test
- [ ] Tests catch field removals and type changes
- [ ] Tests pass for additive changes
- [ ] CI runs contract tests
```

---

## Cross-Cutting Concerns (Apply Throughout)

### Migration Safety Checklist

```markdown
For EVERY migration script, before merging the PR:

- [ ] Migration script applies cleanly to a fresh database at the 
      previous version
- [ ] Rollback script returns the database to the previous version
- [ ] Applying migration then rollback then migration again works 
      (idempotency of the pair)
- [ ] No existing test breaks after migration
- [ ] SchemaVersion table is updated
- [ ] YAML dictionary matches the post-migration database state
- [ ] Migration does NOT:
  - [ ] Add NOT NULL columns without defaults to tables with existing data
  - [ ] Drop columns that existing code references
  - [ ] Rename tables or columns (use expand-contract instead)
  - [ ] Modify dbo.Value in any way
- [ ] Migration script has a header comment:
  -- Migration: v1.X.0 → v1.Y.0
  -- Description: [what this does]
  -- Rollback: v1.Y.0_to_v1.X.0_rollback.sql
  -- Author: [name]
  -- Date: [date]
  -- Breaking changes: NONE (or describe)
```

### Naming Conventions

```markdown
Enforce throughout:

Tables: PascalCase (EquipmentEvent, not equipment_event)
Columns: PascalCase (MetaDataID, not metadata_id)
FKs: FK_{ChildTable}_{ParentTable} or FK_{ChildTable}_{Column}
Indexes: IX_{Table}_{Columns}
PKs: PK_{Table}
Check constraints: CK_{Table}_{Description}
Default constraints: DF_{Table}_{Column}
Unique constraints: UQ_{Table}_{Columns}

YAML files: match table name (EquipmentEvent.yaml)
Migration scripts: v{from}_to_v{to}_{platform}.sql
Rollback scripts: v{to}_to_v{from}_{platform}_rollback.sql
```

### Testing Strategy

```markdown
Three levels of tests, all must pass:

1. YAML Validation (fast, no database needed):
   - All FK targets exist
   - All naming conventions followed
   - No duplicate table/column names
   - Version number incremented if tables changed

2. Migration Tests (requires test database):
   - Fresh install from v1.0.0 to HEAD works
   - Each individual migration applies and rolls back cleanly
   - Post-migration state matches YAML dictionary

3. Integration Tests (requires test database with sample data):
   - Business scenarios from each phase work end-to-end
   - API contract tests pass
   - Route resolution works
   - Lineage queries return correct graphs
```

---

## Quick Reference: Dependency Graph

```
Phase 0 (Foundation)
   │
   ├──► Phase 1 (Data Shape) ──────────────────────────────►│
   │                                                         │
   ├──► Phase 2a (Core Context) ──► Phase 2b (Lab Data) ──►│
   │         │                                               │
   │         ├──► Phase 2c (Sensor Lifecycle) ──────────────►│
   │         │                                               │
   │         └──► Phase 2d (Ingestion Routing) ─────────────►│
   │                                                         │
   └──► Phase 3 (Processing Lineage) ──────────────────────►│
            (needs Person from 2a)                           │
                                                             ▼
                                                      Phase 4 (API)
```

**Minimum viable path:** 0 → 1 → 2a → 2d → 4 (gets you data shapes, campaigns, and API-mediated ingestion).

**Full path:** 0 → 1 → 2a → 2b → 2c → 2d → 3 → 4.

Phases 1, 2b, 2c, and 3 can run in parallel after their dependencies are met.