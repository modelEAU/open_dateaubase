# Phase 4 — API breakdown (context-window sized chunks)

## Chunk 1: Signal Interface admin endpoints + route cleanup

**What:** Scaffold the three new admin endpoint modules and remove the old signal-port routes.

**Files:**
- **New:** `api/v1/endpoints/signal_interface_types.py` (vocab CRUD — mirror `BinMode`/`SiteType` pattern)
- **New:** `api/v1/endpoints/signal_interfaces.py` (CRUD + `GET /{id}/ports`, `GET /{id}/channels`)
- **New:** `api/v1/endpoints/signal_interface_ports.py` (CRUD under a signal interface)
- **Modify:** `api/v1/router.py` — register new routes, remove old `signal_ports`, `signal_port_types`, `ports`
- **Delete:** `api/v1/endpoints/signal_ports.py`, `signal_port_types.py`, `ports.py`

**Why separate:** These are boilerplate CRUD and traversal endpoints. No dependency on ingest or equipment-move logic. Can be verified immediately with contract tests.

---

## Chunk 2: Channel endpoint enhancements

**What:** Update the channel request/response shapes and add the tag-resolution endpoint.

**Files:**
- **Modify:** `api/v1/endpoints/channels.py` — add `signal_interface_id`, `tag_name`, `parent_channel_id`, `channel_role` to request/response; keep `equipment_id`/`equipment_identifier` but resolve via new view
- **Modify:** `api/v1/schemas/channel.py` — update `ChannelOut` (drop `signal_port_id`/`signal_port_tag`, add new fields)
- **New endpoint in same file:** `POST /channels/resolve` — body `{signal_interface_name, tag_name, parameter_name?, create_missing?}` → `channel_id`

**Why separate:** Self-contained; depends only on data layer (Phase 3) already having the updated `Channel` model and `channel_repository.py`. Good checkpoint before touching ingest.

---

## Chunk 3: Ingest endpoints rewrite (tagged + tagless)

**What:** Rewrite both resolution paths in the ingest pipeline to use `SignalInterface` + `TagName` instead of `SignalPort_ID`.

**Files:**
- **Modify:** `api/v1/endpoints/sensor_ingest.py` and/or `api/v1/endpoints/ingest.py`
  - `_resolve_tag_inputs()` (lines 68–126): resolve `(das_name, tag_name)` via `SignalInterface` instead of `SignalPort`
  - `_resolve_tagless_inputs()` (lines 128–150): resolve equipment → `(SignalInterface, TagName)` via `EquipmentWiringHistory` at timestamp
- **Modify:** `api/v1/repositories/ingestion_repository.py::find_or_create_sensor_metadata()` — lookup key changes to `(SignalInterface_ID, TagName, Parameter_ID, DataProvenance_ID, ProcessingDegree_ID)`

**Why separate:** This is the highest-risk rewrite in Phase 4. Both resolution paths live in the same file(s), so doing them together keeps the ingest contract consistent. Fits in one window because the two functions are bounded (~80 lines of logic).

---

## Chunk 4: Equipment move endpoint rewrite

**What:** Rewrite equipment-move to anchor on `Equipment`, operate on the new history tables, and make auto-annotation symmetric.

**Files:**
- **Rewrite:** `api/v1/endpoints/equipment_move.py` — subject is now `Equipment_ID`; mutates `EquipmentWiringHistory` and/or `EquipmentLocationHistory` atomically in one transaction
- **Modify:** `api/v1/repositories/temporal_history_repository.py` — move `swap_equipment()` / `register_equipment_at_port()` / `relocate_sensor()` / `get_equipment_at_time()` / `get_location_at_time()` to operate on `EquipmentWiringHistory` + `EquipmentLocationHistory`
- **New shared helper (or modify existing):** lift auto-annotation logic from old `ports.py` (lines 379–390) into a reusable helper; call it from both swap and relocate so both are symmetric
- **Modify:** `api/v1/repositories/control_loop_repository.py` — `ControlLoopPort` now resolves via `Channel_ID`

**Why separate:** This chunk has the most cross-cutting coordination (two history tables, atomic transaction, annotation side effects, control-loop join update). It stands alone because it doesn't share files with Chunk 3.

---

## Execution order

1 → 2 → 3 → 4. Chunks 1 and 2 can be parallelized if you have two context windows, but 3 and 4 should wait until 1/2 are in place because they depend on the new endpoint shapes and repository patterns being stable.
