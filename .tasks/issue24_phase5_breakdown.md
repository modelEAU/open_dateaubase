# Plan — Phase 5 (tests) breakdown for Issue #24

## Context

Parent plan: [ok-ok-no-worries-composed-canyon.md](/Users/jeandavidt/.claude/plans/ok-ok-no-worries-composed-canyon.md)
Branch: `issue-24-signal-interface` (v4.0.0)
Phase 5 goal (from parent plan): **"tests: integration + contract + unit; full green on `uv run pytest`"**.

Phase 3/4 work landed `SignalInterface*`, `EquipmentWiringHistory`, `EquipmentLocationHistory`, `ChannelPortHistory`, `ChannelRole`, new endpoints, and a rewritten ingest pipeline. Contract tests under [tests/api/contract/](tests/api/contract/) were partially updated in the same commits and are currently green (246 unit+contract pass). What still needs rewriting:

- **Integration tests** — 5 files are currently `pytest.skip(..., allow_module_level=True)` with a "Rewrite required for v4.0.0 schema" message:
  - [tests/integration/test_temporal_lifecycle.py](tests/integration/test_temporal_lifecycle.py) (507 lines, 9 tests)
  - [tests/integration/test_signal_port_ingest.py](tests/integration/test_signal_port_ingest.py) (447 lines, 22 tests)
  - [tests/integration/test_tagless_ingest.py](tests/integration/test_tagless_ingest.py) (328 lines, 14 tests)
  - [tests/integration/test_sub_signal_grouping.py](tests/integration/test_sub_signal_grouping.py) (288 lines, 9 tests)
  - [tests/integration/test_control_loop.py](tests/integration/test_control_loop.py) (522 lines, 20 tests) — not skipped but references `SignalPort`
- **Schema tests** — [tests/schema/test_sensor_status_yaml.py](tests/schema/test_sensor_status_yaml.py) has 7 failures (`TestSignalPortTypeSchema`, `TestSignalPortSubSignalColumns`) that must be rewritten around `SignalInterfaceType` + `ChannelRole`.
- **Unit tests** — [tests/unit/test_schema_ci.py::test_version_yaml_matches_latest_migration_target](tests/unit/test_schema_ci.py) currently fails because `version.yaml` = 4.0.0 and `sql/init.sql` hasn't been updated to match in this test; verify + unblock.
- **New:** `tests/integration/test_signal_interface_lifecycle.py` covering the five scenarios listed in the parent plan (unknown-port, port+equipment, TresCON mux, backfill, equipment swap).
- **Out of scope for Phase 5** (per parent plan): app tests (campaign wizard etc.) → Phase 7; L5X loader tests and importer e2e → Phase 6.

Each sub-phase below is sized to land in one focused Claude session: ~300–700 lines of test churn, one `/sc` commit, and each ends with a concrete green-test verification target.

## Sub-phase breakdown

### 5A — Schema + unit fixes + control-loop contract cleanup

**Scope:** smallest, front-loaded sweep so the whole non-db suite is green before touching integration tests.

**Files:**
- [tests/schema/test_sensor_status_yaml.py](tests/schema/test_sensor_status_yaml.py) — rename `TestSignalPortTypeSchema` → `TestSignalInterfacePortKindSchema` and `TestSignalPortSubSignalColumns` → `TestChannelSubSignalColumns` (parent via `Channel.ParentChannel_ID`, role via `ChannelRole`). Point schema assertions at new YAMLs in [schema_dictionary/tables/](schema_dictionary/tables/).
- [tests/unit/test_schema_ci.py](tests/unit/test_schema_ci.py) — `test_version_yaml_matches_latest_migration_target` — verify resolution path: either `sql/init.sql` now references `v4.0.0_signal_interface.sql` (it does per git status) or update the check to look for the v4 migration.
- [tests/api/contract/test_control_loop_endpoints.py](tests/api/contract/test_control_loop_endpoints.py) — 5 remaining `SignalPort` refs. `ControlLoopPort` now FKs `Channel_ID` (per 3E). Update mocks/fixtures/assertions to pass `channel_id` instead of `signal_port_id`; reuse the pattern already applied in [tests/api/contract/test_sub_signal_endpoints.py](tests/api/contract/test_sub_signal_endpoints.py).

**Verify:**
```
uv run pytest tests/unit/ tests/schema/ tests/api/contract/ -q
```
All green. Zero `SignalPort` refs in `tests/schema/`, `tests/unit/`, `tests/api/contract/`.

**Commit:** `test(schema,contract): realign sensor-status + control-loop on SignalInterface/ChannelRole`

---

### 5B — Integration conftest v4 fixture + rewrite tag-mode ingest

**Scope:** unblock all db-mode integration tests by adding a v4.0.0 fixture and shared helpers, then rewrite the first skipped integration test as the template the others will follow.

**Files:**
- [tests/integration/conftest.py](tests/integration/conftest.py) — add `db_at_v400` fixture (mirrors existing `db_at_v300` pattern in [tests/integration/test_signal_port_ingest.py](tests/integration/test_signal_port_ingest.py:42-61)): apply `v1.0.0_create_mssql.sql` + `v1.0.0_to_v3.0.0_mssql.sql` + v3 patches + [migrations/v4.0.0_signal_interface.sql](migrations/v4.0.0_signal_interface.sql). Seed minimal lookup data (`Parameter`, `Unit`, one `DataAcquisitionSystem`, one `SignalInterfaceType`).
- **Shared helpers in conftest** (or new `tests/integration/_factories.py`): `make_signal_interface(conn, das_id, name, type_id) -> int`, `make_signal_interface_port(conn, si_id, name, kind_id) -> int`, `make_channel(conn, si_id, tag_name, parameter_id, ...) -> int`, `open_wiring(conn, equipment_id, si_id, port_id, valid_from) -> None`, `open_location(conn, equipment_id, sp_id, valid_from) -> None`. These absorb the boilerplate so 5C–5G stay readable.
- Rewrite [tests/integration/test_signal_port_ingest.py](tests/integration/test_signal_port_ingest.py) → rename to `test_tag_ingest.py` (keeps git blame via `git mv`). Remove the `pytest.skip`. Re-point AC1–AC8:
  - AC1 `resolve_tag` → resolves `(das_name, signal_interface_name, tag_name)` via [api/v1/endpoints/channels.py::POST /channels/resolve](api/v1/endpoints/channels.py).
  - AC2 first ingest creates `SignalInterface` + `Channel` (with `TagName`); repeat is idempotent against the new unique key `(SignalInterface_ID, TagName, Parameter_ID, DataProvenance_ID, ProcessingDegree_ID)`.
  - AC3/4 unknown DAS / tag auto-create warning paths stay, pointed at new resolver.
  - AC5/6 unknown parameter/unit → 422 (unchanged logic).
  - AC7 case-insensitive lookups against `SignalInterface.Name` + `Channel.TagName`.
  - AC8 `SignalInterface.IsActive = 0` via deactivate (rename from `SignalPort.IsActive`). Data unaffected.

**Verify:**
```
uv run pytest tests/integration/test_tag_ingest.py -m db -q
```
22 tests green. `docker compose up` required.

**Commit:** `test(integration): v4 conftest fixtures + rewrite tag-mode ingest`

---

### 5C — Integration: tagless ingest + sub-signal grouping

**Scope:** two files that share the new `EquipmentWiringHistory` resolution path. Doing them together keeps the resolver assertions consistent.

**Files:**
- [tests/integration/test_tagless_ingest.py](tests/integration/test_tagless_ingest.py) — remove `pytest.skip`. Re-point the tagless resolver to look up `(equipment_identifier, timestamp)` → `EquipmentWiringHistory` → `(SignalInterface_ID, SignalInterfacePort_ID)` → `Channel` (per [api/v1/endpoints/ingest.py `_resolve_tagless_inputs`](api/v1/endpoints/ingest.py)). Use the `open_wiring()` helper from 5B. Keep the existing 14 test cases; rename variables (`sp_id` → `si_id`, `port_id` stays but maps to `SignalInterfacePort_ID`).
- [tests/integration/test_sub_signal_grouping.py](tests/integration/test_sub_signal_grouping.py) — remove `pytest.skip`. Sub-signals now live on `Channel.ParentChannel_ID` + `ChannelRole` (Value/Status/Alarm/Uncertainty) per the phase 1 dictionary change. Rewrite the 9 tests: parent/child grouping, role constraints, status-channel auto-selection (`Channel.ParentChannel_ID` + `ChannelRole.Name = 'Status'`). Reference the rewritten [api/v1/repositories/sensor_status_repository.py `_STATUS_CHANNEL_FOR_MEASUREMENT`](api/v1/repositories/sensor_status_repository.py).

**Verify:**
```
uv run pytest tests/integration/test_tagless_ingest.py tests/integration/test_sub_signal_grouping.py -m db -q
```
23 tests green.

**Commit:** `test(integration): tagless ingest + sub-signal grouping on v4 model`

---

### 5D — Integration: temporal lifecycle rewrite

**Scope:** the largest rewrite. Re-anchors all AC-EQ* and AC-LO* on `EquipmentWiringHistory` + `EquipmentLocationHistory`. Must also cover the **annotation-symmetry fix** called out in the parent plan's Risks section (both wiring swap and relocation now annotate).

**Files:**
- [tests/integration/test_temporal_lifecycle.py](tests/integration/test_temporal_lifecycle.py) — remove `pytest.skip`. Rewrite 9 tests:
  - AC-EQ1 Equipment rewire leaves `Channel_ID` and observations unchanged (via `rewire_equipment` in [api/v1/repositories/temporal_history_repository.py](api/v1/repositories/temporal_history_repository.py)).
  - AC-EQ2 Point-in-time `vw_ChannelEquipmentAtTime` at `T_before` vs `T_after` returns correct equipment.
  - AC-EQ3 Opening a second active `EquipmentWiringHistory` row for the same equipment raises — invariant lives on equipment now, not port.
  - AC-EQ4/5 Commission/Decommission unchanged semantically; `SignalInterface` + `Channel` unaffected.
  - AC-LO1 Relocation leaves `Channel_ID` unchanged.
  - AC-LO2 `vw_ChannelLocationAtTime` resolves Channel → Equipment → SamplingPoint at a given time.
  - AC-LO3 Second active `EquipmentLocationHistory` row raises.
  - AC-LO4 Relocation auto-annotates affected Channels (join via `vw_ChannelEquipmentAtTime` → Equipment).
  - AC-LO5 `valid_from` must be explicit.
  - **NEW** AC-ANN (symmetry): equipment wire-swap also auto-annotates affected Channels (was only on relocate in v3).
- Use the `open_wiring` / `open_location` helpers from 5B.

**Verify:**
```
uv run pytest tests/integration/test_temporal_lifecycle.py -m db -q
```
10 tests green (9 rewritten + 1 new symmetry).

**Commit:** `test(integration): temporal lifecycle on EquipmentWiring/EquipmentLocation`

---

### 5E — Integration: control loop

**Scope:** [tests/integration/test_control_loop.py](tests/integration/test_control_loop.py) (522 lines, 20 tests) — `ControlLoopPort` now FKs `Channel_ID` instead of `SignalPort_ID`. Not currently skipped but 12 `SignalPort` refs in assertions and fixtures need updating. Keep the acceptance-criteria coverage; just swap the join target.

**Files:**
- [tests/integration/test_control_loop.py](tests/integration/test_control_loop.py) — for every fixture and assertion, replace `signal_port_id` → `channel_id`; update INSERT statements to match the new `ControlLoopPort` schema. Reuse `make_channel()` helper from 5B to build the loop's input/output channels. Verify `add_loop_port()` / `get_loop_ports()` from [api/v1/repositories/control_loop_repository.py](api/v1/repositories/control_loop_repository.py) return `Channel_ID`-keyed rows.

**Verify:**
```
uv run pytest tests/integration/test_control_loop.py -m db -q
```
20 tests green. Zero `SignalPort` refs in the file afterwards.

**Commit:** `test(integration): control-loop assertions on Channel_ID`

---

### 5F — New signal_interface_lifecycle integration tests + full green

**Scope:** author the new integration test file called out explicitly in the parent plan, then prove the whole `uv run pytest` is green.

**Files:**
- **New** `tests/integration/test_signal_interface_lifecycle.py` — five scenarios from parent plan §Tests:
  - **(a) Unknown-port, unknown-equipment ingest:** create `SignalInterface` + `Channel` (with `TagName`), ingest values with no `SignalInterfacePort_ID` and no `EquipmentWiringHistory`. Assert data lands, `vw_ChannelEquipmentAtTime` returns NULL with `resolution: "ambiguous"` (per Risks section).
  - **(b) Port + equipment wired:** same as (a) plus `SignalInterfacePort_ID` set on Channel and an open `EquipmentWiringHistory` row. Assert traversal `Channel → Equipment → SamplingPoint` at timestamp resolves cleanly.
  - **(c) TresCON mux:** two Channels on the same `SignalInterfacePort_ID` differentiated by `ChannelPortHistory.GatingNote`. Ingest for each `TagName` routes to the correct Channel. Cross-check via `vw_ChannelStatus`.
  - **(d) Backfill previously-blank port:** Channel exists with `SignalInterfacePort_ID = NULL` and prior observations. Set `SignalInterfacePort_ID` via PATCH. Prior observations still resolve via `Channel_ID`; new observations use the now-populated port.
  - **(e) Swap equipment, historical resolution:** close old `EquipmentWiringHistory` row, open a new one. Observations before swap resolve to old equipment via `vw_ChannelEquipmentAtTime` at `timestamp_before`; after swap resolve to new equipment.
- Use `db_at_v400` fixture + helpers from 5B.

**Final verification (exits Phase 5):**
```
uv run pytest                       # full suite, non-db + db
uv run pytest -m db                 # db subset
grep -rn "SignalPort" tests/        # should return zero (excluding tests/app/, which is Phase 7)
```
All green, zero remaining `SignalPort` refs in `tests/integration/`, `tests/api/contract/`, `tests/unit/`, `tests/schema/`.

**Commit:** `test(integration): signal interface lifecycle + full-suite green on v4`

---

## Phase 5 done criteria

- [ ] 5A–5F all committed via `/sc`.
- [ ] `uv run pytest` 100% green (including `-m db` when Docker is up).
- [ ] Zero `SignalPort` references outside `tests/app/` (Phase 7) and the `migrations/deprecated/` or archival paths.
- [ ] New `test_signal_interface_lifecycle.py` covers all five scenarios (a–e).
- [ ] Annotation symmetry regression (wiring swap annotates, matching relocate) has a dedicated assertion in 5D.

## Execution order

5A → 5B → (5C ‖ 5E can overlap if you have two windows, both depend only on 5B helpers) → 5D → 5F.
5D benefits from 5C's sub-signal work (status channels land in 5C) so serialize those two.

## Out of scope for Phase 5

- App tests ([tests/app/test_campaign_wizard.py](tests/app/test_campaign_wizard.py), 14 failures) → Phase 7.
- `tests/unit/test_l5x_loader.py` → Phase 6 (ships with the loader itself).
- `importer/tests/test_e2e_import.py` → Phase 6.
