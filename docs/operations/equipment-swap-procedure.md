# Equipment Swap Procedure

When a sensor probe at a SCADA tag is physically replaced, follow this procedure to record the swap in the database.

**What stays unchanged:** `Channel_ID`, all historical observations, annotations, and processing lineage all remain intact. The `SignalPort` is the stable identity of the measurement stream — it persists across equipment changes.

---

## Background

Each `SignalPort` has a `PortEquipmentHistory` (`SignalPortEquipmentHistory` table): a time-ordered list of which physical instrument was behind the port. At most one row per port has `EndTime IS NULL` (the currently active instrument).

An equipment swap closes the current active row and opens a new one. The `Channel` row is not touched.

---

## Step-by-step

### 1. Confirm the port ID

If you know the SCADA tag and DAS name, look up the port:

```
GET /api/v1/ingest/lookup/equipment  (or query the SignalPort table directly)
```

Or, if you know the tag and DAS name, the port can be resolved from the ingest API.

### 2. Record the swap

```http
POST /api/v1/ports/{signal_port_id}/swap-equipment
Content-Type: application/json

{
  "equipment_id": 42,
  "swap_time": "2024-06-15T14:30:00Z",
  "notes": "Probe-A replaced after fouling. New probe: Probe-B (S/N 20240601)"
}
```

- `equipment_id` — the ID of the **new** instrument (must exist in the `Equipment` table)
- `swap_time` — the UTC datetime of the physical replacement
- `notes` — optional free-text for the audit trail

**Response:**

```json
{
  "signal_port_id": 7,
  "new_history_id": 23,
  "closed_history_id": 11
}
```

`closed_history_id` is `null` if there was no previously registered instrument (first registration case).

### 3. Verify the swap

Query which instrument was active at a time before and after the swap:

```http
GET /api/v1/ports/7/equipment-at?at=2024-06-15T14:29:59Z
# Returns Probe-A (equipment_id=41)

GET /api/v1/ports/7/equipment-at?at=2024-06-15T14:30:01Z
# Returns Probe-B (equipment_id=42)
```

---

## First-time registration (no prior instrument)

If a port was created automatically at ingest time but no equipment was linked, use the register endpoint:

```http
POST /api/v1/ports/{signal_port_id}/register-equipment
Content-Type: application/json

{
  "equipment_id": 42,
  "start_time": "2024-01-01T08:00:00Z",
  "notes": "Initial registration for Probe-A"
}
```

This returns `409 Conflict` if an active history row already exists — use `swap-equipment` in that case.

---

## Commission / decommission equipment

To mark a piece of equipment as active or inactive (independent of port assignment):

**Commission:**
```http
POST /api/v1/equipment/{equipment_id}/commission
Content-Type: application/json

{"notes": "Probe-B passed pre-deployment calibration check"}
```

**Decommission:**
```http
POST /api/v1/equipment/{equipment_id}/decommission
Content-Type: application/json

{"notes": "Probe-A returned to manufacturer for repair"}
```

Both endpoints set `Equipment.IsActive` and record an `EquipmentEvent` (type: *Commissioning* / *Decommissioning*). `SignalPort` and `Channel` rows are unaffected.

---

## What NOT to do

- Do **not** create a new `Channel` for the new probe. The channel belongs to the `SignalPort`, not the instrument.
- Do **not** edit or delete the old `SignalPortEquipmentHistory` row. Historical provenance must be preserved.
- Do **not** use the general-purpose `POST /api/v1/equipment/events` endpoint for swaps — it does not update the equipment history tables.
