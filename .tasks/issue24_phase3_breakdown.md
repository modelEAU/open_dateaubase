# Issue #24 — Phase 3 Breakdown (Data Layer)

Parent plan: `/Users/jeandavidt/.claude/plans/ok-ok-no-worries-composed-canyon.md`
Branch: `issue-24-signal-interface` (v4.0.0)
Scope: **Phase 3 only** — Pydantic models, schemas, repositories. No endpoint/router/UI changes.

Phase 3 touches ~477 `SignalPort*` references across `api/` and `src/`. Broken into 5 sub-phases, each independently testable, committable via `/sc`, and small enough to land in one focused session.

---

## 3A — Pydantic table models (foundation)

**File:** `src/open_dateaubase/data_model/table_models.py`

- Remove: `SignalPort`, `SignalPortType`, `SignalPortEquipmentHistory`, `SignalPortLocationHistory`.
- Add: `SignalInterface`, `SignalInterfaceType`, `SignalInterfacePort`, `SignalInterfacePortKind`, `ChannelRole`, `EquipmentWiringHistory`, `EquipmentLocationHistory`, `ChannelPortHistory`.
- Rewrite `Channel`: replace `signalportID` with `signalinterfaceID`, `signalinterfaceportID` (nullable), `tagName`, `parentchannelID` (nullable), `channelroleID`.
- Rewrite `ControlLoopPort`: `signalportID` → `channelID`.
- Keep aliases (`Field(alias="...")`) matching exact column names from `migrations/v4.0.0_signal_interface.sql`.

**Verify:** `uv run pytest tests/unit/ -k models` green. Nothing else depends on Phase 3A alone.

**Commit:** `refactor(models): swap SignalPort for SignalInterface in table_models`

---

## 3B — API schemas (Pydantic request/response)

**Files:**
- `api/v1/schemas/channel.py` — rewrite `ChannelOut`/`ChannelIn`: drop `signal_port_id`/`signal_port_tag`; add `signal_interface_id`, `signal_interface_name`, `tag_name`, `parent_channel_id`, `channel_role`, `signal_interface_port_id`.
- `api/v1/schemas/signal_interface.py` (NEW) — `SignalInterfaceOut`, `SignalInterfaceIn`, `SignalInterfacePortOut`, `SignalInterfacePortIn`, lookup schemas.
- Remove or stub `api/v1/schemas/signal_port.py` if it exists.

**Verify:** `uv run pytest tests/api/contract/ -k "channel or signal"` — expect some failures until repos are rewritten; flag them but don't fix yet.

**Commit:** `refactor(api-schemas): signal interface + channel schema swap`

---

## 3C — signal_interface_repository (new) + delete signal_port_repository

**Files:**
- `api/v1/repositories/signal_interface_repository.py` (NEW) — port over DAS CRUD (`list_das`, `insert_das`, `update_das`, `delete_das`) untouched; add `list_signal_interfaces`, `get_signal_interface_by_id`, `create_signal_interface`, `patch_signal_interface`, `list_signal_interface_ports`, `create_signal_interface_port`, `find_or_create_signal_interface`, `find_or_create_signal_interface_port`, `generate_tagless_tagname` (adapts `generate_tagless_tag` pattern).
- `api/v1/repositories/signal_port_repository.py` — **delete**.

**Callers broken by deletion:** audit via grep and list them in the commit body; do NOT rewrite them in 3C (that's 3E).

**Verify:** new repo functions individually — quick integration test or `python -c` smoke against Docker DB.

**Commit:** `feat(repos): signal_interface_repository; remove signal_port_repository`

---

## 3D — ingestion_repository + channel_repository

**Files:**
- `api/v1/repositories/channel_repository.py` — rewrite `_CHANNEL_SELECT` joins through `vw_ChannelEquipmentAtTime` + `SignalInterface` + `ChannelRole`; update `_row_to_dict`; rewrite INSERT/UPDATE SQL for new columns (`SignalInterface_ID`, `TagName`, `SignalInterfacePort_ID`, `ParentChannel_ID`, `ChannelRole_ID`).
- `api/v1/repositories/ingestion_repository.py`:
  - `find_or_create_sensor_metadata`: new signature `(signal_interface_id, tag_name, parameter_id, unit_id, data_provenance_id, processing_degree_id, value_type_id)`; unique key `(SignalInterface_ID, TagName, Parameter_ID, DataProvenance_ID, ProcessingDegree_ID)`.
  - `find_or_create_derived_metadata`: remove `SignalPort_ID` select; channels inherit parent's interface/tag.

**Verify:** `uv run pytest tests/api/contract/ -k "channel or ingest"` — contract tests should start passing.

**Commit:** `refactor(repos): channel + ingestion joins on SignalInterface`

---

## 3E — temporal_history + sensor_status + control_loop

**Files:**
- `api/v1/repositories/temporal_history_repository.py` — re-anchor everything on `Equipment_ID`:
  - Rename: `get_active_equipment_history(signal_port_id)` → `get_active_wiring_for_equipment(equipment_id)`.
  - `swap_equipment` → `rewire_equipment(equipment_id, new_signal_interface_id, new_port_id?, swap_time, note)`.
  - Split location into `get_active_location_for_equipment` / `relocate_equipment` operating on `EquipmentLocationHistory`.
  - Column renames: `StartTime`→`ValidFrom`, `EndTime`→`ValidTo`, `Notes`→`Note` (wiring) / `Notes` (location).
- `api/v1/repositories/sensor_status_repository.py` — rewrite `_STATUS_CHANNEL_FOR_MEASUREMENT` via `Channel.ParentChannel_ID` + `ChannelRole.Name = 'Status'`; rewrite device-status joins through `EquipmentWiringHistory` matching `(SignalInterface_ID, SignalInterfacePort_ID)` at timestamp.
- `api/v1/repositories/control_loop_repository.py` — `add_loop_port(loop_id, channel_id, role_id)`; INSERT `Channel_ID` not `SignalPort_ID`; update `get_loop_ports` SELECT.

**Verify:** `uv run pytest tests/api/contract/ tests/unit/` — all Phase 3 contract tests green. Integration (`-m db`) and endpoints will fail (Phase 4 fixes those) — that's expected.

**Commit:** `refactor(repos): temporal + status + control-loop on EquipmentWiring/ChannelRole`

---

## Phase 3 done criteria

- [ ] 3A–3E all committed.
- [ ] `uv run pytest tests/unit/ tests/api/contract/` green.
- [ ] Zero `SignalPort` references in `src/open_dateaubase/` and `api/v1/repositories/`.
- [ ] `api/v1/endpoints/` still imports old names (expected — Phase 4).

## Out of scope for Phase 3

- `api/v1/endpoints/*.py` — Phase 4.
- `api/v1/router.py` wiring of new `signal_interface_repository` — Phase 4.
- `importer/` — Phase 6.
- `app/` pages — Phase 7.
