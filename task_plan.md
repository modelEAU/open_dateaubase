# Task Plan: Issue 26 — YAML seed_data + SI conversions + ParameterHasUnit + /convert + ingestion validation

## Goal
Migrate Units and Parameters to YAML seed_data, add SI conversion metadata, create ParameterHasUnit junction table, add /convert API endpoint, validate (Parameter, Unit) pairs at ingestion time. Schema bump 4.0.0 → 4.1.0.

## Phases
- [x] Phase 0: Explore codebase (complete)
- [x] Phase 1: Unit.yaml — add SI columns + 13-row seed_data
- [x] Phase 2: Parameter.yaml — add ValueKind_ID + QUDT_QuantityKind_IRI + 18-row seed_data
- [x] Phase 3: ParameterHasUnit.yaml — new junction table YAML
- [x] Phase 4: Migration scripts (v4.0.0 → v4.1.0 forward + rollback)
- [x] Phase 5: tools/ontology_query.py — QUDT SPARQL client + manual_units resolver
- [x] Phase 6: generate_from_yaml.py — add step 8 for ParameterHasUnit INSERTs
- [x] Phase 7: /convert API endpoint + schemas + router
- [x] Phase 8: Importer config validation (parameter+unit pair check)
- [x] Phase 9: Cleanup seed_fixtures.sql + rename parameters in importer configs
- [x] Phase 10: Bump version.yaml to 4.1.0
- [x] Phase 11: Verify — uv run mkdocs build succeeded; 399 tests pass (5 ChannelRole failures are pre-existing branch issues, not caused by these changes)

## Key Decisions
- Parameter naming: "concentration" explicit (TSS → TSS concentration, etc.)
- absorbance → Absorbance spectrum (Vector, ValueKind_ID=2); new Light Absorbance (Scalar, ValueKind_ID=1)
- manual_units is a build-only YAML field, NOT a DB column
- Image (ValueKind_ID=4) parameters skip ParameterHasUnit entirely
- QUDT fallback: manual_units by name, resolved at build time; QUDT unreachable = warning, not failure

## Errors Encountered
- (none yet)

## Status
**Currently in Phase 1**
