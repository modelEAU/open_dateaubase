# Plan — Issue #24: SignalInterface + history redesign (Channel keeps its name)

## Context

GitHub issue [#24](https://github.com/modelEAU/open_dateaubase/issues/24) proposes making the "signal interface" device (PLC, SC1000, IQSensor, monEAU box) a first-class entity between `Equipment` and `DataAcquisitionSystem`. The current model collapses that middle hop into either Equipment or DAS, which:

- makes tag-based addressing (PLC tags, SCADA) second-class;
- can't represent a multiplexer like TresCON where one physical port produces multiple named streams;
- forces port identity at ingest time even when wires have not been traced.

**User direction (2026-04-21) supersedes the PRD on three points:**

1. **`Channel` is NOT renamed.** Keep the name. Add `SignalInterface_ID`, `SignalInterfacePort_ID` (nullable), `TagName`, and `ParentChannel_ID` as new columns. No downstream cascade into `Observation.Channel_ID`, `ValueVector`, `ValueMatrix`, `ValueImage`, `ChannelAxis`, `DatasetChannel`, `ProcessingLineage`, views, app pages, endpoints, or the importer's schema.
2. **Version: v4.0.0** — breaking, since `SignalPort*` tables and `Channel.SignalPort_ID` are removed.
3. **Location + equipment history redesign is a first-class objective**, not a footnote. Location and wiring must be independent and both recoverable from a `Value` row.

**Decisions locked with user (via AskUserQuestion):**

- Location history: **both** — authoritative on `Equipment` (`EquipmentLocationHistory`), plus a view to resolve Channel→location-at-time.
- `ControlLoopPort` → FK to **`Channel`**.
- Sub-signal hierarchy → **`Channel.ParentChannel_ID`** (self-FK) + **`ChannelRole`** vocab (Value / Status / Alarm / Uncertainty).
- Migration style → **drop-and-recreate** (single `v4.0.0_signal_interface.sql` + rollback).

## Target model — quick diagram

```
DataAcquisitionSystem
  └── SignalInterface (name, type, make, model, serial)
        ├── SignalInterfacePort (optional; port identifier e.g. "6/Ch0")
        └── Channel (was tied to SignalPort — now ties here via SignalInterface_ID + TagName)
              └── ParentChannel_ID → self (for Status/Alarm/Uncertainty sub-tags)

Equipment (physical sensor, lifecycle)
  ├── EquipmentWiringHistory (Equipment_ID, SignalInterface_ID, SignalInterfacePort_ID?, ValidFrom, ValidTo?, Note)
  └── EquipmentLocationHistory (Equipment_ID, SamplingPoint_ID, ValidFrom, ValidTo?)

Channel
  └── ChannelPortHistory (Channel_ID, SignalInterfacePort_ID?, ValidFrom, ValidTo?, GatingNote)  -- for mux

Views:
  vw_ChannelEquipmentAtTime   -- resolves Channel → currently-wired Equipment
  vw_ChannelLocationAtTime    -- resolves Channel → Equipment → SamplingPoint
```

**Deleted:** `SignalPort`, `SignalPortEquipmentHistory`, `SignalPortLocationHistory`, `SignalPortType`, `EquipmentInstallation` (absorbed into `EquipmentLocationHistory`).

## Files to modify

### Dictionary (source of truth)

- **New:** `schema_dictionary/tables/SignalInterface.yaml`, `SignalInterfaceType.yaml`, `SignalInterfacePort.yaml`, `SignalInterfacePortKind.yaml` (vocab for port physical kind — analog-in/out, digital-in/out, serial, network; reuse existing `SignalPortType` values), `EquipmentWiringHistory.yaml`, `EquipmentLocationHistory.yaml`, `ChannelPortHistory.yaml`, `ChannelRole.yaml`.
- **Modify:** `schema_dictionary/tables/Channel.yaml` — drop `SignalPort_ID`; add `SignalInterface_ID` (required FK), `SignalInterfacePort_ID` (nullable FK), `TagName` (nvarchar, NOT NULL), `ParentChannel_ID` (nullable self-FK), `ChannelRole_ID` (FK, default = Value); replace `UQ_Channel_SignalStream` with `(SignalInterface_ID, TagName, Parameter_ID, DataProvenance_ID, ProcessingDegree_ID)`.
- **Modify:** `schema_dictionary/tables/ControlLoopPort.yaml` — swap `SignalPort_ID` FK for `Channel_ID` FK.
- **Modify:** `schema_dictionary/views/vw_ChannelStatus.yaml`, `vw_DeviceStatus.yaml` — rebuild joins through new history tables; add `vw_ChannelEquipmentAtTime`, `vw_ChannelLocationAtTime`.
- **Deprecate (move to `schema_dictionary/deprecated/`):** `SignalPort.yaml`, `SignalPortEquipmentHistory.yaml`, `SignalPortLocationHistory.yaml`, `SignalPortType.yaml`, `EquipmentInstallation.yaml`.
- `schema_dictionary/version.yaml` → `4.0.0` with changelog; `erd_groups.yaml` updated.

### Migration SQL (generated from dictionary)

- **New:** `migrations/v4.0.0_signal_interface.sql` — single file: drops `SignalPort*` and `EquipmentInstallation`; creates new vocab+entity tables; alters `Channel` (drop `SignalPort_ID`, add new cols, replace unique index); alters `ControlLoopPort`; creates new views.
- **New:** `migrations/v4.0.0_signal_interface_rollback.sql`.
- `sql/init.sql` — append `v4.0.0_signal_interface.sql` after existing v3.0.0 patches.
- `sql/seed_v2.2.0.sql` and `sql/seed_importer_fixtures.sql` — regenerate to seed `SignalInterface` + `SignalInterfacePort` + `Channel` (with `TagName`). Drop all `SignalPort*` and `EquipmentInstallation` inserts.
- Fresh-volume verification: `docker compose down -v && docker compose up --build` (per memory rule, never patch running container).

### Data layer

- `src/open_dateaubase/data_model/table_models.py` — new Pydantic models for `SignalInterface`, `SignalInterfaceType`, `SignalInterfacePort`, `EquipmentWiringHistory`, `EquipmentLocationHistory`, `ChannelPortHistory`, `ChannelRole`. Update `Channel` model: remove `signalportID`, add `signalinterfaceID`, `signalinterfaceportID`, `tagName`, `parentchannelID`, `channelroleID`.
- `api/v1/schemas/channel.py` — `ChannelOut` drops `signal_port_id` and `signal_port_tag`; adds `signal_interface_id`, `signal_interface_name`, `tag_name`, `parent_channel_id`, `channel_role`. Keep `equipment_id` / `equipment_identifier` but resolve via the new view `vw_ChannelEquipmentAtTime`.
- **Rewrite:** `api/v1/repositories/channel_repository.py` — queries currently LEFT JOIN `SignalPort` → `SignalPortEquipmentHistory` (lines 25–28, 55–58, 124–126 today); rebuild joins through `EquipmentWiringHistory` via `(SignalInterface_ID, SignalInterfacePort_ID)` match-at-timestamp, or use the new view.
- **Rewrite:** `api/v1/repositories/ingestion_repository.py::find_or_create_sensor_metadata()` (lines 13–83) — lookup key changes from `(SignalPort_ID, Parameter_ID, DataProvenance_ID, ProcessingDegree_ID)` to `(SignalInterface_ID, TagName, Parameter_ID, DataProvenance_ID, ProcessingDegree_ID)`. Insert path mirrors the new unique index.
- **Rewrite:** `api/v1/repositories/temporal_history_repository.py` — `swap_equipment()` / `register_equipment_at_port()` / `relocate_sensor()` / `get_equipment_at_time()` / `get_location_at_time()` all move to operate on the new `EquipmentWiringHistory` and `EquipmentLocationHistory`. Make `swap` and `relocate` atomic on `Equipment`, not on a port. The auto-annotation behaviour currently in `ports.py` (lines 379–390) migrates to the equipment-move endpoint; make it symmetric — swap also annotates affected Channels.
- `api/v1/repositories/control_loop_repository.py` — `ControlLoopPort` now resolves via `Channel_ID`, not `SignalPort_ID`.
- **Delete:** `api/v1/repositories/signal_port_repository.py`, `sensor_status_repository.py` SignalPort joins reworked.

### API surface

- **New endpoints:** `api/v1/endpoints/signal_interfaces.py`, `signal_interface_ports.py`, `signal_interface_types.py` (CRUD + traversal: `/signal-interfaces/{id}/ports`, `/signal-interfaces/{id}/channels`).
- `api/v1/endpoints/channels.py` — add fields to request/response; add `POST /channels/resolve` (body `{signal_interface_name, tag_name, parameter_name?, create_missing?}` → `channel_id`). Keep `/channels` path.
- **Rewrite ingest:** `api/v1/endpoints/sensor_ingest.py` and `ingest.py` — `_resolve_tag_inputs()` (lines 68–126) resolves `(das_name, tag_name)` via `SignalInterface` instead of `SignalPort`; `_resolve_tagless_inputs()` (lines 128–150) resolves equipment → `(SignalInterface, TagName)` via the wiring-history-at-time. Backwards-incompatible — importer updates in lockstep.
- **Rewrite equipment-move endpoint:** `api/v1/endpoints/equipment_move.py` — anchors on `Equipment_ID`, mutates `EquipmentWiringHistory` and/or `EquipmentLocationHistory` atomically in one transaction. Auto-annotation applies to both swap and relocate (removes the current asymmetry).
- **Delete endpoints:** `signal_ports.py`, `signal_port_types.py`, `ports.py`. `api/v1/router.py` updated.

### Importer

- `importer/src/table_import/api_client.py::resolve_channel()` (lines 70–96) — contract stays `(das_name, tag, …) → channel_id`; backend now resolves via `SignalInterface`. Add optional `signal_interface_name` if DAS has multiple interfaces.
- `importer/src/table_import/config.py` — `FileStructure` gains optional `signal_interface_name`; `tag_name` already supported.
- `docker/import-test-data.yaml`, `importer/configs/spectrolyser_basestation.yaml`, `felinoscope.yaml` — add `signal_interface_name` where DAS→interface is 1:N.
- **New:** `importer/configs/examples/monEAU_iqsensor.yaml`, `sc1000_via_plc.yaml`, `logix5000_direct.yaml` — one per forcing case.

### L5X loader

- Move `scripts/parse_l5x.py` → `importer/src/table_import/l5x_loader.py` with CLI `uv run table-import l5x <file.l5x> --signal-interface <name> [--dry-run]`. Creates `SignalInterface`, `SignalInterfacePort`, `Channel` (with `TagName`), and `ChannelPortHistory` rows. Unit tests against `modelEAU_Hedi_Latest260323.L5X` — must round-trip the TresCON mux and an unknown-port row.

### App (Streamlit)

- New **Signal Sources** nav group in `app/Home.py`: `signal_interfaces.py`, `signal_interface_ports.py`, `signal_interface_types.py`.
- Update `app/pages/channels.py` — add columns for `SignalInterface`, `TagName`, optional port (labeled "optional; fill when wire traced"), `ParentChannel`, `Role`.
- Update `app/pages/equipment_move.py` — wizard now operates on `Equipment` as the subject, with separate tabs for "change wiring" and "change location."
- **Delete:** `app/pages/signal_ports.py`, `signal_port_types.py`.

### Tests

- **Update:** `tests/integration/test_temporal_lifecycle.py` — all AC tests re-point at `EquipmentWiringHistory` / `EquipmentLocationHistory`. Invariants stay (one active row per equipment+dimension; `ValidFrom <= ValidTo`).
- **Update:** `tests/integration/test_ingest.py`, `test_signal_port_ingest.py`, `test_tagless_ingest.py`, `test_control_loop.py`, `test_sub_signal_grouping.py` — renamed/rewritten around new model.
- **New:** `tests/integration/test_signal_interface_lifecycle.py` — covers (a) create interface + channel, ingest with NO port, NO equipment linked; (b) same + port + equipment, traversal returns them; (c) TresCON mux: two Channels on same `SignalInterfacePort` with distinct `GatingNote`, ingest routes each; (d) backfill previously-blank port, existing observations still resolve; (e) swap equipment → prior observations still resolve to old equipment via wiring-history-at-time.
- **New:** `tests/unit/test_l5x_loader.py`.
- **Update:** `tests/api/contract/` — schemas for `SignalInterface*`, updated `Channel`.
- **Update:** `tests/schema/test_sensor_status_yaml.py` for view rename/rewrite.
- `importer/tests/test_e2e_import.py` — fixtures updated.

### Docs

- Regenerate `docs/reference/tables.md`.
- Update `docs/reference/inserting_data.md`, `docs/reference/views.md`.
- Rewrite `docs/architecture/ingestion_routing.md`, `sensor_lifecycle.md`, `sensor_status.md`, `campaigns_and_provenance.md`.
- Rewrite `docs/operations/sensor-relocation-sop.md`, `equipment-swap-procedure.md`, `equipment_move_checklist.md` — unify "move sensor" around `Equipment` as subject.
- Regenerate `docs/assets/erd_interactive.html` and key excalidraw diagrams: `01_signal_identity`, `01_metadata_to_channel`, `02_equipment_port_lifecycle` (proposed_v3), `09_status_channel`, `13_observation_hub`.
- `uv run mkdocs build` must pass.

## Reuse (no new code where existing helpers suffice)

- Temporal history CRUD pattern in `api/v1/repositories/temporal_history_repository.py` — copy the `ValidFrom`/`ValidTo` gap-detection and active-row uniqueness logic; don't reinvent.
- Annotation auto-creation in `api/v1/endpoints/ports.py` lines 379–390 — lift into a shared helper and reuse for both wiring swap and location relocation.
- Generic CRUD pattern in `app/components/generic_crud.py` — all three new admin pages use it.
- Vocab-table pattern already used for `BinMode`, `SiteType` — mirror for `SignalInterfaceType`, `ChannelRole`.

## Phased execution (for when plan is approved)

1. [x] **Phase 0 — baseline:** branch `issue-24-signal-interface` created from `dev-v2.1.0`. Baseline: 276 non-db tests pass (`--ignore=tests/legacy -m "not db"`); legacy tests + `tests/integration/test_phase2c.py` have pre-existing breakage unrelated to this work. 4 pre-existing WIP commits landed before branching (UI fixes, planning docs, L5X prep script, gitignore).
2. [x] **Phase 1 — dictionary:** all YAMLs authored — `SignalInterface`, `SignalInterfaceType`, `SignalInterfacePort`, `SignalInterfacePortKind`, `ChannelRole`, `EquipmentWiringHistory`, `EquipmentLocationHistory`, `ChannelPortHistory`; `Channel` + `ControlLoopPort` rewritten; views `vw_ChannelStatus` / `vw_DeviceStatus` rewritten and `vw_ChannelEquipmentAtTime` / `vw_ChannelLocationAtTime` added; `SignalPort*` YAMLs moved to `schema_dictionary/deprecated/`; `version.yaml` → 4.0.0; `erd_groups.yaml` updated. Generator (`scripts/generate_from_yaml.py`) runs clean and emits `/tmp/sql_test/v4.0.0_create_mssql.sql` as reference steady-state.
3. [x] **Phase 2 — migration + seeds:** write `v4.0.0_signal_interface.sql` + rollback; update `sql/init.sql` + seeds; `docker compose down -v && up --build` passes.
4. [ ] **Phase 3 — data layer:** Pydantic models, repositories, schemas.
5. [ ] **Phase 4 — API:** new endpoints, rewritten ingest + equipment-move, deleted signal_port routes.
6. [ ] **Phase 5 — tests:** integration + contract + unit; full green on `uv run pytest`.
7. [ ] **Phase 6 — importer + L5X loader:** configs and loader command; e2e import test green.
8. [ ] **Phase 7 — app pages:** Signal Sources nav + updated Channel/Equipment pages.
9. [ ] **Phase 8 — docs:** regenerate + rewrite ops SOPs; `mkdocs build` green.
10. [ ] **Phase 9 — verify & PR:** fresh container boot, full test suite, manual L5X smoke, PR to `main` with screenshots and migration proof. `/sc` atomic commits per phase.

## Verification

End-to-end check (after Phase 9):

1. **Clean boot:** `docker compose down -v && docker compose up --build` — fresh volume initializes with `sql/init.sql`; no errors in log.
2. **Schema:** query `SchemaVersion` → `4.0.0`; `SELECT * FROM SignalInterface, SignalInterfacePort, EquipmentWiringHistory, EquipmentLocationHistory, ChannelPortHistory, ChannelRole` all return seed rows; `SignalPort*` and `EquipmentInstallation` no longer exist.
3. **Unit/contract/integration:** `uv run pytest` — 100% green. Specifically confirm `tests/integration/test_signal_interface_lifecycle.py` covers unknown-port, mux, and backfill paths.
4. **API smoke:**
   - `POST /api/v1/signal-interfaces` → 201; `GET /signal-interfaces/{id}/ports` → empty list; `POST /signal-interfaces/{id}/ports` → 201.
   - `POST /channels/resolve` with `(signal_interface_name, tag_name)` → returns `channel_id`; repeat call returns same id (idempotence).
   - `POST /api/v1/ingest/sensor-values` tagged and tagless paths both succeed end-to-end.
   - `GET /channels/{id}` returns `equipment_id`/`equipment_identifier` resolved via `vw_ChannelEquipmentAtTime` (not the old SignalPort join).
5. **L5X loader:** `uv run table-import l5x modelEAU_Hedi_Latest260323.L5X --signal-interface hedi_plc --dry-run` lists expected SignalInterfacePorts + Channels including TresCON mux tags. Re-run without `--dry-run` → rows created in DB.
6. **Equipment-move flow:** via the app, relocate a piece of equipment → `EquipmentLocationHistory` has a closed row + open row; affected Channels auto-annotated; swap equipment → `EquipmentWiringHistory` updated, same annotation behaviour.
7. **Docs build:** `uv run mkdocs build` clean; ERD interactive HTML opens and shows new entities.
8. **Rollback drill:** apply `v4.0.0_signal_interface_rollback.sql` against a test DB; verify v3.0.0 shape restored (empty `SignalPort*` tables recreated).

## Risks & mitigations

- **Equipment-at-time via nullable port:** when a Channel's `SignalInterfacePort_ID` is NULL and multiple equipment are wired to the same interface, `vw_ChannelEquipmentAtTime` can't uniquely resolve. Mitigation: the view returns NULL for that case and the API response surfaces `equipment_id: null` with a `resolution: "ambiguous"` flag — not an error. Documented in `docs/architecture/ingestion_routing.md`.
- **ControlLoopPort → Channel** swap: existing control-loop tests may assume port-level wiring. Mitigation: rewrite assertions around Channel identity; ControlLoopPort becomes a thin join.
- **Rename-free Channel change still has big blast radius on ingest/channel_repository**: the joins are non-trivial. Mitigation: Phase 3 rewrites `channel_repository.py` first and runs its contract tests before moving on.
- **Annotation symmetry regression:** today swap does not annotate, relocate does. The redesign makes both annotate — verify existing dashboards/queries don't count annotations in a way that silently double-counts.

## Out of scope (per PRD)

Cascading interfaces, structured gating logic, per-interface JSON-schema addressing, continuous L5X/OPC UA sync, DAS re-model, Value* payload changes, any Channel rename or alias.
