# Issue #24 — SignalInterface + Channel→SignalTag rename

**Source PRD:** `.tasks/prd_controller_signaltag_draft.md` (mirrors GH #24)
**Target schema version:** `v3.1.0` (minor bump per user directive, not v4.0.0)
**Branch base:** `dev-v2.1.0` → new branch `issue-24-signal-interface`
**Strategy:** clean redesign, no legacy compat shims (synthetic test data → rebuild).

---

## Open PRD questions — proposed resolutions

These must be confirmed by the user before Phase 1 ships. Proposals:

| # | Question | Proposal |
|---|----------|----------|
| 1 | Middle-entity name | **`SignalInterface`** (current working name) |
| 2 | `SignalTag.Equipment_ID` — direct FK or history-only | **Remove direct FK**; equipment linkage via `EquipmentSignalInterfacePortHistory` only (cleaner; matches "no legacy compat" spirit) |
| 3 | Version bump | **v3.1.0** (user-directed) |
| 4 | L5X loader location | **`importer/` command** (`importer/src/table_import/l5x_loader.py`) — productionizes `scripts/parse_l5x.py` |
| 5 | DAS required on SignalInterface at create? | **Yes, required** — matches current "DAS is the entry point" UX; parent later not needed |
| 6 | Lazy vs. eager `SignalInterfacePort` rows | **Lazy** — only create when known; unknown port = NULL FK on history/tag rows |
| 7 | Supporting table renames | `ChannelAxis` → **`SignalTagAxis`**; `DatasetChannel` → **`DatasetSignalTag`** |

Nothing proceeds past Phase 0 until these are locked.

---

## Phase 0 — Alignment & baseline (no code)

- [ ] Confirm open questions above with user
- [ ] Run full test suite on `dev-v2.1.0` to capture green baseline: `uv run pytest`
- [ ] Capture row counts from a fresh `docker compose up --build` volume (post-seed) for `Channel`, `ChannelAxis`, `DatasetChannel`, `SignalPort`, `SignalPortEquipmentHistory`, `Observation`, `Value*`
- [ ] Inventory all `Channel_ID` / `StatusChannel_ID` / `ChannelAxis` / `DatasetChannel` references across: `schema_dictionary/`, `migrations/`, `sql/`, `src/`, `api/`, `app/`, `importer/`, `tests/`, `docs/`
- [ ] Create tracking checklist from inventory (one-time reference count per directory)

**Exit:** green baseline + inventory committed under `.tasks/issue24_inventory.md`.

---

## Phase 1 — Dictionary-first schema authoring

Dictionary is source of truth (user story 21). No SQL hand-written.

### 1.1 New vocab / entity YAMLs

- [ ] `schema_dictionary/tables/SignalInterfaceType.yaml` — vocab (id, name, description)
- [ ] `schema_dictionary/tables/SignalInterface.yaml` — fields: `SignalInterface_ID`, `Name` (unique within DAS), `SignalInterfaceType_ID` (FK), `Make`, `Model`, `SerialNumber`, `DataAcquisitionSystem_ID` (required FK), `Description`
- [ ] `schema_dictionary/tables/SignalInterfacePort.yaml` — fields: `SignalInterfacePort_ID`, `SignalInterface_ID` (FK), `PortIdentifier` (e.g. `6/Ch0`, unique within interface), `SignalPortType_ID` (reuse existing vocab; if it doesn't fit, mint `SignalInterfacePortKind`), `Description`
- [ ] `schema_dictionary/tables/EquipmentSignalInterfacePortHistory.yaml` — fields: `ID`, `Equipment_ID`, `SignalInterface_ID` (required), `SignalInterfacePort_ID` (nullable), `ValidFrom`, `ValidTo` (nullable), `Note`
- [ ] `schema_dictionary/tables/SignalTagSignalInterfacePortHistory.yaml` — fields: `ID`, `SignalTag_ID`, `SignalInterfacePort_ID` (nullable), `ValidFrom`, `ValidTo` (nullable), `GatingNote` (free text for mux)

### 1.2 Rename YAMLs

- [ ] `Channel.yaml` → `SignalTag.yaml` — `Channel_ID` → `SignalTag_ID`; drop `SignalPort_ID`; drop direct `Equipment_ID` (per Q2); add `SignalInterface_ID` (required FK), `SignalInterfacePort_ID` (nullable FK), `TagName` (nvarchar, unique within SignalInterface)
- [ ] `ChannelAxis.yaml` → `SignalTagAxis.yaml`; rename FK col
- [ ] `DatasetChannel.yaml` → `DatasetSignalTag.yaml`; rename FK col
- [ ] `Observation.yaml` — rename `Channel_ID` → `SignalTag_ID`
- [ ] Any YAML with `StatusChannel_ID` → `StatusSignalTag_ID` (from inventory)
- [ ] `ProcessingLineage.yaml` — rename `Channel_ID` FKs
- [ ] Views: `vw_ChannelStatus.yaml` → `vw_SignalTagStatus.yaml`; `vw_DeviceStatus.yaml` updated

### 1.3 Drops

- [ ] `SignalPort.yaml`, `SignalPortEquipmentHistory.yaml`, `SignalPortLocationHistory.yaml`, `SignalPortType.yaml` → moved to `schema_dictionary/deprecated/` (follow precedent of `deprecated/EquipmentStatusChannel.yaml`)
- [ ] **Decide:** does `SignalPortLocationHistory` have a successor? The PRD doesn't replace "where a signal is *located*." Either (a) add equivalent fields to `EquipmentSignalInterfacePortHistory`, or (b) defer location-history. Flag for user.

### 1.4 Version bump

- [ ] Update `schema_dictionary/version.yaml` → `3.1.0` with changelog entry
- [ ] Update `schema_dictionary/erd_groups.yaml`

**Exit:** dictionary lints clean; ERD regen produces new groups.

---

## Phase 2 — Migration SQL (generated from dictionary)

- [ ] `migrations/v3.1.0_signal_interface.sql` — creates new tables; renames `Channel*` → `SignalTag*`; adds new FKs on `SignalTag`; drops `SignalPort*` tables; renames FK columns on `Observation`, `ValueVector`, `ValueMatrix`, `ValueImage`, `ProcessingLineage`, `Annotation`, `DatasetSignalTag`, `SignalTagAxis`, status views
- [ ] `migrations/v3.1.0_signal_interface_rollback.sql` — inverse
- [ ] Update `sql/init.sql` to include the new migration last (after existing v3.0.0 patches)
- [ ] Update `sql/seed_importer_fixtures.sql` + `sql/seed_v2.2.0.sql` to target new chain (remove `SignalPort*` inserts; add `SignalInterface` + `SignalInterfacePort` + `SignalTag` rows)
- [ ] `sql_generation_scripts/` — regenerate from YAMLs (or add `v3.1.0_create_mssql.sql`)
- [ ] `docker compose down -v && docker compose up --build` — confirm fresh volume boots cleanly

**Exit:** fresh container initializes; all existing integration tests adapted to new names still pass (or are updated in Phase 5).

---

## Phase 3 — Data layer (src/open_dateaubase + api repositories)

- [ ] `src/open_dateaubase/data_model/table_models.py` — rename Channel model → SignalTag; add SignalInterface, SignalInterfacePort, SignalInterfaceType, history models; drop SignalPort models
- [ ] Rename `api/v1/repositories/channel_repository.py` → `signal_tag_repository.py`; update queries
- [ ] New `signal_interface_repository.py`, `signal_interface_port_repository.py`
- [ ] Update `ingestion_repository.py`, `value_repository.py`, `annotation_repository.py`, `campaign_repository.py`, `value_binning_repository.py`, `sensor_status_repository.py`, `temporal_history_repository.py` for column renames
- [ ] Drop `api/v1/repositories/*signal_port*` and `api/v1/endpoints/signal_ports.py`, `signal_port_types.py`, `ports.py`
- [ ] `src/open_dateaubase/meteaudata_bridge.py`, `lineage.py` — rename Channel references

---

## Phase 4 — API surface

- [ ] New endpoints: `api/v1/endpoints/signal_interfaces.py`, `signal_interface_ports.py`, `signal_interface_types.py` (generic CRUD pattern)
- [ ] Rename `api/v1/endpoints/channels.py` → `signal_tags.py`; paths `/channels` → `/signal-tags`
- [ ] Add traversal: `/signal-interfaces/{id}/ports`, `/signal-interfaces/{id}/signal-tags`, `/signal-tags/{id}/current-equipment`, `/signal-tags/{id}/current-port`
- [ ] Resolver: `POST /signal-tags/resolve` — body `{signal_interface_name, tag_name, create_missing?}` → canonical ID
- [ ] Update `sensor_ingest.py` / `ingest.py` to accept **only** `signal_tag_id` or `(signal_interface_name, tag_name)` — drop `signal_port_id` / equipment shortcut
- [ ] Update `timeseries.py` endpoint — observations keyed by `signal_tag_id`
- [ ] Update Pydantic schemas in `api/v1/schemas/` — rename Channel* → SignalTag*, add SignalInterface*, drop SignalPort*
- [ ] `api/v1/router.py` — wire new routers, drop old

---

## Phase 5 — Tests

- [ ] **Contract tests** (`tests/api/contract/`) — rename `channel_*` → `signal_tag_*`; add contract tests for `SignalInterface`, `SignalInterfacePort`, resolver
- [ ] **Integration tests** (`tests/integration/`, `-m db`):
  - [ ] `test_signal_interface_lifecycle.py` — create interface + tag, ingest observation with NO port, NO equipment
  - [ ] Same + port + equipment; verify traversal
  - [ ] TresCON mux: two tags on same port, distinct gating notes, ingest routes each
  - [ ] Backfill blank port; existing observations still resolve
  - [ ] Rename impact: port → nullable flow works; unknown state is supported
- [ ] **Unit tests** for L5X parser (Phase 7)
- [ ] Update `tests/integration/test_temporal_lifecycle.py`, `test_phase_d.py`, `test_ingest.py` for renames
- [ ] Update `tests/schema/test_sensor_status_yaml.py` — new view name
- [ ] `importer/tests/test_e2e_import.py` — update fixtures

**Exit:** `uv run pytest` green end-to-end.

---

## Phase 6 — Importer

- [ ] `importer/src/table_import/config.py` — `FileStructure` gains `signal_interface_name` (per-file or per-row) + `tag_name_column` or `default_tag_name`; drop `signal_port`/`equipment` as provenance fields
- [ ] `importer/src/table_import/api_client.py` — call new `/signal-tags/resolve` endpoint instead of port resolver
- [ ] `importer/src/table_import/import_script.py` — route via SignalTag
- [ ] Rewrite `importer/configs/spectrolyser_basestation.yaml`, `felinoscope.yaml`, `docker/import-test-data.yaml` — no compat shim
- [ ] Add three example configs under `importer/configs/examples/`: `monEAU_iqsensor.yaml`, `sc1000_via_plc.yaml`, `logix5000_direct.yaml`
- [ ] `importer/pyproject.toml` — no new deps expected

---

## Phase 7 — L5X loader productionization

- [ ] Move `scripts/parse_l5x.py` → `importer/src/table_import/l5x_loader.py`
- [ ] CLI entrypoint: `uv run table-import l5x <file.l5x> --signal-interface <name> --dry-run`
- [ ] Outputs: creates `SignalInterface`, `SignalInterfacePort`, `SignalTag`, `SignalTagSignalInterfacePortHistory` rows via API
- [ ] Unit tests against `modelEAU_Hedi_Latest260323.L5X` fixture — assert TresCON mux and unknown-port rows are representable
- [ ] Document in `docs/operations/l5x_import.md`

---

## Phase 8 — App UI (Streamlit)

- [ ] New nav group **Signal Sources** in `app/Home.py` containing:
  - `app/pages/signal_interfaces.py`
  - `app/pages/signal_interface_ports.py`
  - `app/pages/signal_interface_types.py`
- [ ] Rename `app/pages/channels.py` → `signal_tags.py` — new fields: `SignalInterface`, optional port, `TagName`; port UI labeled "optional; fill when wire traced"
- [ ] Drop `app/pages/signal_ports.py`, `signal_port_types.py`
- [ ] Update campaign builder page — pick SignalTag; show interface/DAS/port (or "(unknown)") read-only
- [ ] All user-facing strings "Channel" → "Signal tag"
- [ ] Smoke test: admin creates interface + tag with no port → student builds campaign → screenshot in PR

---

## Phase 9 — Docs

- [ ] `docs/reference/tables.md` — regenerate from dictionary
- [ ] `docs/reference/inserting_data.md` — update provenance chain diagram and examples
- [ ] `docs/architecture/ingestion_routing.md` — rewrite routing path
- [ ] `docs/architecture/sensor_status.md`, `sensor_lifecycle.md`, `campaigns_and_provenance.md` — update
- [ ] `docs/operations/sensor-relocation-sop.md`, `equipment-swap-procedure.md`, `equipment_move_checklist.md` — rewrite around new history tables
- [ ] Regenerate ERD diagrams (`docs/assets/erd_interactive.html`, relevant `.excalidraw` files — at minimum `01_signal_identity`, `01_metadata_to_channel`, `09_status_channel`, `13_observation_hub`)
- [ ] `mkdocs build` passes

---

## Phase 10 — Verification & merge

- [ ] Fresh `docker compose down -v && docker compose up --build` from clean repo
- [ ] `uv run pytest` full green
- [ ] `uv run mkdocs build` green
- [ ] Manual smoke: L5X loader → SignalTag created → ingest one observation via API → query via `/signal-tags/{id}/observations`
- [ ] PR opened targeting `main` (or appropriate integration branch); PR body includes (a) open-question resolutions, (b) screenshot evidence, (c) migration/rollback proof
- [ ] `/sc` for atomic, bisectable commits per phase

---

## Risks & mitigations

- **Blast radius of rename** (100+ files touched) → stage the rename as its own commit inside Phase 2 so `git log --follow` stays useful.
- **`SignalPortLocationHistory` has no obvious successor** → flagged in Phase 1.3; block on user decision.
- **Minor version bump for breaking change** — user has accepted this; document clearly in `version.yaml` changelog and PR body that v3.1.0 is breaking.
- **Seed regeneration** can silently diverge from fixtures used by tests → Phase 5 runs first integration test against freshly-seeded container, not a fixture snapshot.

---

## Out of scope (explicitly, per PRD)

Cascading interfaces, structured gating logic, per-interface JSON-schema addressing, continuous L5X/OPC UA sync, DAS re-model, `Channel` compat view, Value* payload shape changes.
