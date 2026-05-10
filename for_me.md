Reusable Preamble (paste at the start of every prompt)

Read prerelease_fix_plan.md in the project root before doing anything.
Key rule: this is pre-release (targeting 2.0 DDL, not a live DB). 
Changes mean: fix the YAML in schema_dictionary/tables/, update the API 
(api/v1/schemas/, api/v1/endpoints/, api/v1/repositories/), and update 
the UI (app/). Do NOT write migration SQL. When done, run 
`uv run pytest tests/unit/` and confirm it passes.
Per-wave instructions
Wave 1 (one agent, pure code — fastest)


[preamble]
Implement Wave 1 from the plan: remove the `role` and `notes` fields from 
CampaignEquipment and CampaignSamplingLocation in the API stack and UI. 
No YAML change needed — just find every place these fields appear in 
api/v1/schemas/campaigns.py, api/v1/endpoints/campaigns.py, 
api/v1/repositories/campaign_repository.py, and app/components/campaign_wizard.py, 
and strip them out.
Wave 2 (one agent — four renames, low blast radius)


[preamble]
Implement Wave 2 from the plan: four YAML column renames 
(SignalInterface.Make→Manufacturer, Person.Function→AssignedFunctions, 
ProcessingStep.Parameters→MethodParameters, drop SamplingPoint.SamplingLocation). 
For each: update the YAML, find every reference in the API and UI, rename it. 
Check schema CI after each rename before moving to the next.
Wave 3a + 3b (one agent — vocab + new table, medium complexity)


[preamble]
Implement Wave 3a and 3b from the plan: replace ProcessingKind seed values 
with the correct set, and convert Procedures.ProcedureType (free text) to 
a new ProcedureKind controlled vocabulary table with a FK. Create the new 
ProcedureKind.yaml using the existing Kind table pattern (look at 
schema_dictionary/tables/CampaignKind.yaml as the template).
Wave 3c + 3d + 4 (one agent after 3a/3b is merged — removals)


[preamble]
Implement Waves 3c, 3d, and 4 from the plan in order:
1. Remove "Validation" from EquipmentEventKind seed data
2. Remove any manuel_units entries from Parameter seed data  
3. Remove SignalInterfaceKind entirely (YAML + SignalInterface.yaml FK column + API + UI)
4. Remove SignalInterfacePortKind entirely (same pattern)
Do Wave 4 after verifying 3c/3d didn't break tests.
Wave 5 (one agent, after Wave 4 — riskiest, keep isolated)


[preamble]
Implement Wave 5 from the plan: the Channel identity restructure. 
Specifically: (1) remove ProcessingKind_ID from Channel's unique constraint 
in Channel.yaml, and (2) replace ProcessingStep.ProcessingType (free text) 
with ProcessingKind_ID (FK to ProcessingKind). Read Channel.yaml and 
ProcessingStep.yaml fully before touching anything. Run tests after each 
of the two sub-changes separately.
Waves 6–9 (can be four parallel agents after Wave 5)
Each one is self-contained:

Implement Wave 6 from the plan (Watershed enhancements: ParentWatershed_ID + GeometryGeoJSON + map UI).
Implement Wave 7 from the plan (EquipmentEvent: RecordedByPerson_ID, drop Campaign_ID, add IsInstantaneous).
Implement Wave 8 from the plan (free-text → FK for Observation.DataType, DASKind, ControllerKind).
Implement Wave 9 from the plan (UrbanCharacteristics → LandUse rename).
Dependency order

Wave 1  ──── (immediate, no deps)
Wave 2  ──── (immediate, no deps)
Wave 3a/3b ─ (after Wave 2 merged, so renames are stable)
Wave 3c/3d + Wave 4 ── (after 3a/3b — ProcessingKind values must be final before removing kind tables)
Wave 5  ──── (after Wave 4 — unique constraint change needs clean Kind table state)
Wave 6, 7, 8, 9 ── (after Wave 5, run in parallel)
DS stubs ─── (after core schema stable)
The main thing agents will miss without explicit instruction: they'll try to write migration scripts out of habit because CLAUDE.md says so. Overriding that in the preamble is the most important line in every prompt.