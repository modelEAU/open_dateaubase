# Plan: Standardize Vocabulary Table Names to "Kind" Suffix

## Context
- SQL DDL is **auto-generated from YAML** via `uv run mkdocs build` — never edit the generation script directly
- All v2/v3/v4 migrations were dev-branch-only artefacts; they will be **deleted**
- The YAML-defined schema becomes v2.0 on main; no incremental migration from 1.0→2.0

## Decision: Standardize all vocabulary tables to "Kind" suffix

Every vocab table must also have exactly: `<Table>_ID`, `Name`, `Description`.

---

## Tables: final rename map

| Old name | New name | Old PK col | New PK col | Name col fix | Description |
|---|---|---|---|---|---|
| AnnotationType | AnnotationKind | AnnotationType_ID | AnnotationKind_ID | `AnnotationTypeName`→`Name` | exists |
| BinMode | BinKind | BinMode_ID | BinKind_ID | `Name` ✓ | exists |
| CampaignType | CampaignKind | CampaignType_ID | CampaignKind_ID | `CampaignType_Name`→`Name` | ADD |
| ChannelRole | ChannelKind | ChannelRole_ID | ChannelKind_ID | `Name` ✓ | exists |
| ControlLoopPortRole | ControlLoopPortKind | ControlLoopPortRole_ID | ControlLoopPortKind_ID | `Name` ✓ | exists |
| DataProvenance | DataProvenanceKind | DataProvenance_ID | DataProvenanceKind_ID | `DataProvenance_Name`→`Name` | ADD |
| EquipmentEventType | EquipmentEventKind | EquipmentEventType_ID | EquipmentEventKind_ID | `EquipmentEventType_Name`→`Name` | ADD |
| ProcessUnitType | ProcessUnitKind | ProcessUnitType_ID | ProcessUnitKind_ID | `Name` ✓ | exists |
| ProcessingDegree | ProcessingKind | ProcessingDegree_ID | ProcessingKind_ID | `Name` ✓ | exists |
| SampleMethod | SampleCollectionKind | SampleMethod_ID | SampleCollectionKind_ID | `Name` ✓ | exists |
| SampleType | SampleKind | SampleType_ID | SampleKind_ID | `Name` ✓ | exists |
| SignalInterfaceType | SignalInterfaceKind | SignalInterfaceType_ID | SignalInterfaceKind_ID | `Name` ✓ | exists |
| SiteType | SiteKind | SiteType_ID | SiteKind_ID | `Name` ✓ | exists |
| ValueType | ValueKind | ValueType_ID | ValueKind_ID | `ValueType_Name`→`Name` | ADD |

**Keep as-is:** `SignalInterfacePortKind` (already correct), `QualityCode` (domain term, already has Name+Description+IsUsable), `SampleMethod`→renamed above.

---

## Child tables that need FK column renames (in their YAML + Python)

| Child table YAML | Old FK col | New FK col |
|---|---|---|
| Annotation.yaml | AnnotationType_ID | AnnotationKind_ID |
| ValueBinningAxis.yaml | BinMode_ID | BinKind_ID |
| Campaign.yaml | CampaignType_ID | CampaignKind_ID |
| Channel.yaml | ChannelRole_ID | ChannelKind_ID |
| Channel.yaml | ProcessingDegree_ID | ProcessingKind_ID |
| Channel.yaml | DataProvenance_ID | DataProvenanceKind_ID |
| Channel.yaml | ValueType_ID | ValueKind_ID |
| ControlLoopPort.yaml | ControlLoopPortRole_ID | ControlLoopPortKind_ID |
| EquipmentEvent.yaml | EquipmentEventType_ID | EquipmentEventKind_ID |
| ProcessUnit.yaml | ProcessUnitType_ID | ProcessUnitKind_ID |
| Sample.yaml | SampleType_ID | SampleKind_ID |
| Sample.yaml | SampleMethod_ID | SampleCollectionKind_ID |
| SignalInterface.yaml | SignalInterfaceType_ID | SignalInterfaceKind_ID |
| Site.yaml | SiteType_ID | SiteKind_ID |

---

## Execution checklist

### Layer 0 — Clean up
- [ ] Delete all migration files except `v1.0.0_create_mssql.sql`
- [ ] Update `sql/init.sql` to remove references to deleted migrations

### Layer 1 — YAML schema dictionary (14 vocab tables renamed/fixed + child tables)
- [ ] AnnotationType.yaml → AnnotationKind.yaml
- [ ] BinMode.yaml → BinKind.yaml
- [ ] CampaignType.yaml → CampaignKind.yaml
- [ ] ChannelRole.yaml → ChannelKind.yaml
- [ ] ControlLoopPortRole.yaml → ControlLoopPortKind.yaml
- [ ] DataProvenance.yaml → DataProvenanceKind.yaml
- [ ] EquipmentEventType.yaml → EquipmentEventKind.yaml
- [ ] ProcessUnitType.yaml → ProcessUnitKind.yaml
- [ ] ProcessingDegree.yaml → ProcessingKind.yaml
- [ ] SampleMethod.yaml → SampleCollectionKind.yaml
- [ ] SampleType.yaml → SampleKind.yaml
- [ ] SignalInterfaceType.yaml → SignalInterfaceKind.yaml
- [ ] SiteType.yaml → SiteKind.yaml
- [ ] ValueType.yaml → ValueKind.yaml
- [ ] Annotation.yaml — update FK col name
- [ ] ValueBinningAxis.yaml — update FK col name
- [ ] Campaign.yaml — update FK col name
- [ ] Channel.yaml — update 4 FK col names
- [ ] ControlLoopPort.yaml — update FK col name
- [ ] EquipmentEvent.yaml — update FK col name
- [ ] ProcessUnit.yaml — update FK col name
- [ ] Sample.yaml — update 2 FK col names
- [ ] SignalInterface.yaml — update FK col name
- [ ] Site.yaml — update FK col name

### Layer 2 — Python API schemas (`api/v1/schemas/`)
- [ ] metadata.py — rename all Pydantic models + FK field names

### Layer 3 — Python repositories
- [ ] lookup_repository.py — SQL strings: table names + column names
- [ ] channel_repository.py
- [ ] campaign_repository.py
- [ ] equipment_repository.py
- [ ] site_repository.py
- [ ] control_loop_repository.py
- [ ] signal_interface_repository.py
- [ ] value_binning_repository.py
- [ ] ingestion_repository.py
- [ ] process_unit_repository.py
- [ ] metadata_repository.py (check for refs)

### Layer 4 — Python endpoints + router
- [ ] annotations.py — AnnotationType → AnnotationKind
- [ ] signal_interface_types.py → rename file + update
- [ ] quality_codes.py — route tag update only (table name unchanged)
- [ ] lab_lookup.py — SampleType/SampleMethod refs
- [ ] process_units.py — ProcessUnitType refs
- [ ] vocab.py — ProcessingDegree route
- [ ] channels.py — ChannelRole lookup route
- [ ] control_loops.py — ControlLoopPortRole refs
- [ ] router.py — all imports + prefixes

### Layer 5 — Streamlit pages (rename + update)
- [ ] annotation_types.py → annotation_kinds.py
- [ ] bin_modes.py → bin_kinds.py
- [ ] campaign_types.py → campaign_kinds.py
- [ ] equipment_event_types.py → equipment_event_kinds.py
- [ ] process_unit_types.py → process_unit_kinds.py
- [ ] processing_degrees.py → processing_kinds.py
- [ ] quality_codes.py — route/label updates only
- [ ] sample_methods.py → sample_collection_kinds.py
- [ ] sample_types.py → sample_kinds.py
- [ ] signal_interface_types.py → signal_interface_kinds.py
- [ ] site_types.py → site_kinds.py
- [ ] app/components/ — check campaign_wizard.py, schema_registry.py

### Verify
- [ ] `uv run mkdocs build` — confirm DDL generates cleanly
- [ ] `uv run pytest` — confirm tests pass
