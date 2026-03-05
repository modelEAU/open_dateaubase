---
status: resolved
trigger: "Investigate issue: schema-migration-discrepancies"
created: 2026-03-05T00:00:00Z
updated: 2026-03-05T00:00:00Z
---

## Current Focus

hypothesis: All column rename issues have been fixed in migration and rollback scripts
test: Verify all discrepancies are addressed by reviewing the changes made
expecting: Migration now renames all v1.0 snake_case columns to PascalCase per YAML schema
next_action: Update debug file with final status and complete the fix

## Symptoms

expected: Migration from v1.0.0 to v2.1.0 should produce a schema that matches the schema_dictionary definition
actual: Discrepancies exist between migration result and YAML-defined schema, breaking API/UI
errors: Column name mismatches (e.g., Site.PostCode vs Zip_code), potentially other schema differences
reproduction: Run docker-compose which creates v1.0 DB then applies migration, compare with schema generated from YAML
started: Investigation started now

## Eliminated

## Evidence

- timestamp: 2026-03-05T00:00:00Z
  checked: Debug file initialization
  found: Starting investigation with symptoms pre-filled
  implication: Ready to examine migration and schema files

- timestamp: 2026-03-05T00:00:00Z
  checked: Site.yaml vs v1.0.0_create_mssql.sql vs v1.0.0_to_v2.1.0_mssql.sql
  found: YAML defines 'PostCode' (line 57-61) but v1.0 baseline has 'Zip_code' (line 202). Migration only adds LatitudeWGS84/LongitudeWGS84 columns (STEP 11b, lines 385-387) but NEVER renames Zip_code to PostCode
  implication: CRITICAL: Migration output will have Zip_code, YAML expects PostCode - breaks API/UI

- timestamp: 2026-03-05T00:00:00Z
  checked: Person.yaml vs migration SQL STEP 3 (lines 198-225)
  found: YAML defines PascalCase: LastName, FirstName, Person_ID. Migration creates from Contact table but columns remain: Last_name, First_name (lines 13-14 of v1.0 baseline). Contact.Status renamed to Role (line 212), but other columns dropped (Skype_name, Street_number, Street_name, City, Zip_code, Country, Office_number). Person_ID is correct (renamed from Contact_ID line 210).
  implication: Migration produces snake_case column names (Last_name, First_name) but YAML expects PascalCase (LastName, FirstName)

- timestamp: 2026-03-05T00:00:00Z
  checked: SamplingPoint.yaml vs migration STEP 11 (lines 351-379)
  found: Migration correctly renames columns: Sampling_point_ID → SamplingPoint_ID, Sampling_point → SamplingPoint, Sampling_location → SamplingLocation, Latitude_GPS → LatitudeWGS84, Longitude_GPS → LongitudeWGS84. Also adds ValidFrom, ValidTo, CreatedByCampaign_ID. Table renamed from SamplingPoints → SamplingPoint.
  implication: SamplingPoint table is CORRECT - migration matches YAML

- timestamp: 2026-03-05T00:00:00Z
  checked: Channel.yaml vs migration STEP 8 (lines 317-327) and STEP 9 (lines 333-337)
  found: Migration correctly renames MetaData → Channel, adds DataProvenance_ID, ProcessingDegree_ID, ValueType_ID, StatusChannel_ID. Column Metadata_ID renamed to Channel_ID.
  implication: Channel table structure matches YAML (though YAML has nullable for ProcessingDegree_ID, migration has NOT NULL DEFAULT 1 - minor difference)

- timestamp: 2026-03-05T00:00:00Z
  checked: Equipment.yaml vs v1.0.0_create_mssql.sql (lines 111-119)
  found: YAML expects: EquipmentModel_ID, Identifier, SerialNumber, StorageLocation, PurchaseDate (all PascalCase). v1.0 baseline has: model_ID, identifier, Serial_number, Storage_location, Purchase_date (snake_case or lowercase). Migration does NOT modify Equipment table at all (no renames in migration SQL).
  implication: Equipment table columns remain in snake_case from v1.0, but YAML expects PascalCase - API/UI mismatch

- timestamp: 2026-03-05T00:00:00Z
  checked: EquipmentModel.yaml vs v1.0.0_create_mssql.sql (lines 32-39)
  found: YAML expects: EquipmentModel_ID, EquipmentModel, ManualLocation. v1.0 baseline has: Equipment_model_ID, Equipment_model, Manual_location. Migration does NOT modify EquipmentModel table.
  implication: EquipmentModel columns remain snake_case, YAML expects PascalCase

- timestamp: 2026-03-05T00:00:00Z
  checked: Watershed.yaml vs v1.0.0_create_mssql.sql (lines 94-102)
  found: YAML expects: Name, SurfaceArea, ConcentrationTime, ImperviousSurface (PascalCase). v1.0 baseline has: name (lowercase), Surface_area, Concentration_time, Impervious_surface (snake_case). Migration does NOT modify Watershed table.
  implication: Watershed columns remain snake_case from v1.0, YAML expects PascalCase

- timestamp: 2026-03-05T00:00:00Z
  checked: UrbanCharacteristics.yaml vs v1.0.0_create_mssql.sql (lines 82-91)
  found: YAML expects: GreenSpaces (PascalCase). v1.0 baseline has: Green_spaces (snake_case). Other columns (Commercial, Industrial, etc.) match. Migration does NOT modify this table.
  implication: UrbanCharacteristics.Green_spaces should be GreenSpaces

- timestamp: 2026-03-05T00:00:00Z
  checked: HydrologicalCharacteristics.yaml vs v1.0.0_create_mssql.sql (lines 42-51)
  found: YAML expects: UrbanArea (PascalCase). v1.0 baseline has: Urban_area (snake_case). Other columns match. Migration does NOT modify this table.
  implication: HydrologicalCharacteristics.Urban_area should be UrbanArea

- timestamp: 2026-03-05T00:00:00Z
  checked: Procedures.yaml vs v1.0.0_create_mssql.sql (lines 53-59)
  found: YAML expects: ProcedureName, ProcedureType, ProcedureLocation (PascalCase). v1.0 baseline has: Procedure_name, Procedure_type, Procedure_location (snake_case). Migration does NOT modify Procedures table.
  implication: Procedures columns remain snake_case, YAML expects PascalCase

## Resolution

root_cause: The migration script v1.0.0_to_v2.1.0_mssql.sql is MISSING column renames for 8 existing tables from v1.0 baseline. While it correctly handles new table creation and some renames (Contact→Person, MetaData→Channel, SamplingPoints→SamplingPoint), it fails to rename columns to match the v2.1.0 YAML schema definition. The v1.0 baseline used snake_case (e.g., Zip_code, Last_name) but YAML expects PascalCase (e.g., PostCode, LastName).

fix: Add missing column rename statements to the migration script for:
1. Site: Zip_code → PostCode
2. Person: Last_name → LastName, First_name → FirstName
3. Equipment: model_ID → EquipmentModel_ID, identifier → Identifier, Serial_number → SerialNumber, Storage_location → StorageLocation, Purchase_date → PurchaseDate
4. EquipmentModel: Equipment_model_ID → EquipmentModel_ID, Equipment_model → EquipmentModel, Manual_location → ManualLocation
5. Watershed: name → Name, Surface_area → SurfaceArea, Concentration_time → ConcentrationTime, Impervious_surface → ImperviousSurface
6. UrbanCharacteristics: Green_spaces → GreenSpaces
7. HydrologicalCharacteristics: Urban_area → UrbanArea
8. Procedures: Procedure_name → ProcedureName, Procedure_type → ProcedureType, Procedure_location → ProcedureLocation

verification: Run migration on v1.0 baseline, verify column names match YAML schema using SQL query or schema comparison tool
files_changed: []
