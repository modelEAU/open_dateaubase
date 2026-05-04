# Phase 7 — App Pages (Signal Sources nav + Channel/Equipment updates)

## Goal
Ship all Streamlit UI changes for v4.0.0: new "Signal Sources" nav group, updated Channel
and Equipment Move pages, and removal of the old Signal Ports pages.

## Prerequisites
- Phase 3 (data layer), Phase 4 (API endpoints) green.
- API must expose: `/signal-interfaces`, `/signal-interfaces/{id}/ports`,
  `/signal-interfaces/{id}/channels`, `/signal-interface-types`, 
  `/signal-interface-port-kinds`, `/channels/lookup/channel-roles`,
  `/equipment/{id}/register-interface`, `/equipment/{id}/rewire`.

## Context-window tasks (in order; each is self-contained)

---

### Task 7.1 — `app/api_client.py`: add SignalInterface* functions, update Channel filter

**Files touched:** `app/api_client.py` only.

**What to do:**

1. Add a `# SignalInterface CRUD` section:
   - `list_signal_interfaces(das_id=None, page=1, page_size=100) -> dict` — GET `/signal-interfaces`
   - `create_signal_interface(data: dict) -> dict` — POST `/signal-interfaces`
   - `update_signal_interface(si_id: int, data: dict) -> dict` — PUT `/signal-interfaces/{si_id}`
   - `delete_signal_interface(si_id: int) -> None` — DELETE `/signal-interfaces/{si_id}`
   - `list_signal_interfaces_lookup() -> list[dict]` — GET `/signal-interfaces/lookup`

2. Add a `# SignalInterfacePort CRUD` section:
   - `list_signal_interface_ports(si_id: int) -> list[dict]` — GET `/signal-interfaces/{si_id}/ports`
   - `create_signal_interface_port(si_id: int, data: dict) -> dict` — POST `/signal-interfaces/{si_id}/ports`
   - `delete_signal_interface_port(si_id: int, port_id: int) -> None` — DELETE `/signal-interfaces/{si_id}/ports/{port_id}`

3. Add a `# SignalInterfaceType CRUD` section:
   - `list_signal_interface_types() -> list[dict]` — GET `/signal-interface-types`
   - `create_signal_interface_type(data: dict) -> dict` — POST `/signal-interface-types`
   - `update_signal_interface_type(si_type_id: int, data: dict) -> dict` — PUT `/signal-interface-types/{si_type_id}`
   - `delete_signal_interface_type(si_type_id: int) -> None` — DELETE `/signal-interface-types/{si_type_id}`

4. Add a `# SignalInterfacePortKind` section:
   - `list_signal_interface_port_kinds() -> list[dict]` — GET `/signal-interface-port-kinds`

5. Add a `# ChannelRole` section:
   - `list_channel_roles() -> list[dict]` — GET `/channels/lookup/channel-roles`

6. Update `list_channels()`:
   - Drop `signal_port_id` parameter (breaking; old callers will be updated in Task 7.4)
   - Add `signal_interface_id: int | None = None` parameter

7. Add to `# SignalInterface traversal`:
   - `list_channels_for_interface(si_id: int) -> list[dict]` — GET `/signal-interfaces/{si_id}/channels`

**Verification:** `uv run python -c "from app.api_client import list_signal_interfaces"` imports cleanly.

---

### Task 7.2 — New vocab pages: `signal_interface_types.py` and `signal_interface_port_kinds.py`

**Files touched:**
- `app/pages/signal_interface_types.py` (new)
- `app/pages/signal_interface_port_kinds.py` (new)

**What to do:**

Both pages use `render_crud_page` from `app/components/generic_crud.py`, exactly like
`site_types.py`, `bin_modes.py`, etc. Mirror that pattern.

`signal_interface_types.py`:
```python
render_crud_page(
    title="Signal Interface Types",
    pk_field="signal_interface_type_id",
    form_fields=[
        {"name": "name", "type": "text", "required": True},
        {"name": "description", "type": "text", "required": False},
    ],
    list_fn=list_signal_interface_types,
    create_fn=lambda data: create_signal_interface_type(data),
    update_fn=lambda pk, data: update_signal_interface_type(pk, data),
    delete_fn=delete_signal_interface_type,
    label_field="name",
)
```

`signal_interface_port_kinds.py`:
```python
render_crud_page(
    title="Signal Interface Port Kinds",
    pk_field="signal_interface_port_kind_id",
    form_fields=[
        {"name": "name", "type": "text", "required": True},
        {"name": "description", "type": "text", "required": False},
    ],
    list_fn=list_signal_interface_port_kinds,
    create_fn=None,   # vocab, no create
    update_fn=None,
    delete_fn=None,
    label_field="name",
)
```
(Adjust create/update/delete if the API supports writes for port kinds.)

**Verification:** Pages render without errors (API 404 is acceptable if API not yet running).

---

### Task 7.3 — New entity page: `app/pages/signal_interfaces.py`

**Files touched:** `app/pages/signal_interfaces.py` (new).

**What to do:**

Top section: CRUD table of SignalInterfaces (columns: id, name, type, DAS name, serial).
Fields for create/edit:
- `name` (text, required)
- `signal_interface_type_id` (select, options_fn=`list_signal_interface_types`)
- `das_id` (select, options_fn=`list_das_lookup`)
- `serial_number` (text, optional)
- `make` / `model` (text, optional)

When a row is selected, show a detail panel below the table with three tabs:

**Tab "Ports":**
- Call `list_signal_interface_ports(si_id)`.
- Show DataFrame. 
- Button "➕ Add Port" → `create_form_dialog` with fields:
  - `port_identifier` (text, required — e.g. "6/Ch0")
  - `signal_interface_port_kind_id` (select, options from `list_signal_interface_port_kinds`)
  - `description` (text, optional)
- Calls `create_signal_interface_port(si_id, data)`.

**Tab "Channels":**
- Call `list_channels_for_interface(si_id)`.
- Show DataFrame (read-only; edit via Channels page).

**Tab "Wiring History" (optional/stretch):**
- Show a read-only table of `EquipmentWiringHistory` rows tied to this interface
  (only include if the API exposes it; skip with an info message otherwise).

**Imports needed from api_client:**
`list_signal_interfaces`, `create_signal_interface`, `update_signal_interface`,
`delete_signal_interface`, `list_signal_interface_ports`, `create_signal_interface_port`,
`list_signal_interface_port_kinds`, `list_signal_interface_types`, `list_das_lookup`,
`list_channels_for_interface`, `APIError`

**Verification:** Page renders, tabs load.

---

### Task 7.4 — Update `app/pages/channels.py`

**Files touched:** `app/pages/channels.py`.

**What to do:**

1. Remove all references to `signal_port_id` / `list_signal_ports` / `signal_port_options`.

2. Add a Signal Interface filter:
   - Load `signal_interfaces_lookup = list_signal_interfaces_lookup()` in the lookup block.
   - Build `signal_interface_options`.
   - Replace the old "Signal Port" filter column with a "Signal Interface" selectbox.
   - Pass `signal_interface_id=signal_interface_id_filter` to `list_channels()`.

3. Update the create form fields (and edit form fields) to reflect the new Channel schema:
   - Remove: `signal_port_id`
   - Add (in order):
     - `signal_interface_id` (select, required, options=`signal_interface_options`)
     - `signal_interface_port_id` (select, optional, options fetched from the selected
       interface's ports — or just a number input for now if dynamic lookup is complex)
     - `tag_name` (text, required)
     - `parent_channel_id` (number, optional — self-FK; raw int is fine for now)
     - `channel_role_id` (select, optional, options from `list_channel_roles()`)
   - Keep: `parameter_id`, `data_provenance_id`, `processing_degree_id`, `value_type_id`

4. Import changes: remove `list_signal_ports`; add `list_signal_interfaces_lookup`,
   `list_channel_roles` from `app.api_client`.

**Verification:** Page renders without errors; existing channel rows load cleanly.

---

### Task 7.5 — Update `app/pages/equipment_move.py` — add "Change Wiring" tab

**Files touched:** `app/pages/equipment_move.py`.

**What to do:**

The existing page is a 4-step relocation wizard. Restructure as follows:

At the top of the page, add two Streamlit tabs:
```python
tab_relocate, tab_rewire = st.tabs(["Change Location", "Change Wiring"])
```

**`tab_relocate`:** Move the existing 4-step wizard code (steps 1–4 as-is) inside this
tab block. Keep all session state keys prefixed `mv_` as they are.

**`tab_rewire`:** New 4-step wizard for changing equipment ↔ interface wiring.
- Session keys prefixed `mw_` (mw = move-wiring).
- Step 1: Select Equipment (same `list_equipment_lookup()` call, reuse `_render_equipment_info_panel`).
  - Show current wiring info via `get_wiring_at_time(equipment_id, now_utc)`.
- Step 2: Wiring details:
  - Destination SignalInterface (select from `list_signal_interfaces_lookup()`).
  - Optional SignalInterfacePort (select from `list_signal_interface_ports(si_id)` —
    only loaded after interface is chosen; show "No port (interface-level only)" option).
  - Timestamp (date + time, UTC).
  - Notes (optional text).
- Step 3: Optional equipment event (same `_step_equipment_event` helper, reuse it).
- Step 4: Review & Confirm — calls `rewire_equipment(equipment_id, payload)` where
  `payload = {signal_interface_id, signal_interface_port_id?, valid_from, notes?}`.

The cancel/back/next nav (`_nav`) helper is shared by both tabs.

**New api_client import needed:** `rewire_equipment` (already exists), `get_wiring_at_time`
(already exists), `list_signal_interfaces_lookup` (from Task 7.1).

**Verification:** Both tabs render; relocate tab still works end-to-end.

---

### Task 7.6 — Delete old pages, update `Home.py` nav

**Files touched:**
- `app/pages/signal_ports.py` — delete
- `app/pages/signal_port_types.py` — delete
- `app/Home.py` — update navigation

**What to do in `Home.py`:**

1. Remove from `"Entities"` group:
   - `signal_ports.py` → `"Signal Ports"`

2. Remove from `"Vocabulary"` group:
   - `signal_port_types.py` → `"Signal Port Types"`

3. Add new `"Signal Sources"` nav group (insert after `"Entities"` or before `"Vocabulary"`):
   ```python
   "Signal Sources": [
       st.Page(str(_pages / "signal_interfaces.py"), title="Signal Interfaces", icon="🔌"),
       st.Page(str(_pages / "signal_interface_types.py"), title="Interface Types"),
       st.Page(str(_pages / "signal_interface_port_kinds.py"), title="Port Kinds"),
   ],
   ```

4. Update quick-navigation blurb on the home page to mention Signal Sources.

**Verification:** `uv run streamlit run app/Home.py` starts cleanly, no import errors,
Signal Sources nav group visible, Signal Ports and Signal Port Types absent.

---

## Execution order

```
7.1 → 7.2 → 7.3 → 7.4 → 7.5 → 7.6
```
Each task is a single focused context window. 7.2 and 7.3 can be parallelized after 7.1.
7.4 and 7.5 are independent of each other and can run in parallel after 7.1.
7.6 must run last (deletes files, updates nav).

## Done criteria

- [ ] `uv run streamlit run app/Home.py` — app starts, no import errors.
- [ ] "Signal Sources" nav group present with Signal Interfaces, Interface Types, Port Kinds.
- [ ] Signal Ports and Signal Port Types pages absent from nav.
- [ ] Signal Interfaces page: table loads, ports tab shows sub-list, add port dialog works.
- [ ] Channels page: Signal Port filter replaced by Signal Interface; new fields (tag_name,
      channel_role) appear in create/edit form.
- [ ] Equipment Move page: two tabs present; "Change Location" tab unchanged; "Change Wiring"
      tab shows interface/port selects and calls `rewire_equipment` on confirm.
- [ ] No references to `list_signal_ports` or `signal_port_id` remain in any active page.
