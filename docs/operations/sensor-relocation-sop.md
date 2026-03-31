# Sensor Relocation SOP

When a sensor is physically moved to a different process location (sampling point), follow this three-step procedure. The procedure preserves data continuity: the `Channel_ID` and all historical observations remain unchanged.

> **Warning — partial-update risk:** If you complete only steps 1 or 2 without the other, point-in-time queries will return incorrect results. Always complete all three steps as a unit.

---

## Background

Each `SignalPort` has a `LocationHistory` (`SignalPortLocationHistory` table): a time-ordered record of where the sensor was measuring. At most one row per port has `EndTime IS NULL` (the current location).

A relocation closes the current active location row and opens a new one pointing to the new `SamplingPoint`. The schema ensures that `start_time` is always explicit — defaulting to *now* is forbidden because the physical move and the database update rarely happen simultaneously.

---

## Step-by-step

### Step 1 — Determine the exact move time

Record the UTC datetime when the sensor was physically moved. This is not the time you are making this database update — it is when the sensor left its old location.

If the sensor was moved at 14:30 UTC on 2024-09-10, `start_time` must be `"2024-09-10T14:30:00Z"`.

Data between the last known-good measurement at the old location and `start_time` may need to be reviewed for quality.

### Step 2 — Resolve IDs

You need:
- `signal_port_id` — the port that was moved
- `sampling_point_id` — the **new** location (must exist in `SamplingPoint`)

### Step 3 — Submit the relocation

```http
POST /api/v1/ports/{signal_port_id}/relocate
Content-Type: application/json

{
  "sampling_point_id": 15,
  "start_time": "2024-09-10T14:30:00Z",
  "notes": "Sensor moved from Inlet to Aeration Tank 2 during maintenance window"
}
```

`start_time` is **required**. The endpoint returns `422` if it is omitted.

**Response:**

```json
{
  "signal_port_id": 7,
  "new_location_history_id": 18,
  "closed_location_history_id": 12,
  "annotation_ids": [304],
  "channel_ids_affected": [55]
}
```

The API automatically creates an **"Equipment Relocation"** annotation (type ID 11) on every `Channel` associated with the port. This flags the relocation for data quality review in downstream time series analysis.

---

## Auto-annotation behaviour

The annotation has:
- `AnnotationType` = *Equipment Relocation* (ID 11, orange `#FF8C00`)
- `StartTime` = the provided `start_time`
- `EndTime` = null (open-ended — the reviewer closes it when the review is complete)
- `Title` = "Equipment Relocation"
- `Comment` = machine-generated description including new SamplingPoint ID, move time, and any notes

The annotation is visible in any time series query that covers the relocation timestamp.

---

## Verify the relocation

Query the location at times before and after the move:

```http
GET /api/v1/ports/7/location-at?at=2024-09-10T14:29:59Z
# Returns: sampling_point_id = 8 (old location)

GET /api/v1/ports/7/location-at?at=2024-09-10T14:30:01Z
# Returns: sampling_point_id = 15 (new location)
```

---

## Callout: why `start_time` must equal the physical move time

Point-in-time queries use `start_time` and `end_time` to determine which `SamplingPoint` a measurement should be attributed to. If `start_time` is set to *now* (the database update time) rather than the actual move time, all measurements between the physical move and the database update will be attributed to the **wrong** location — silently corrupting spatial context for those observations.

This is especially critical for:
- Calibration calculations that depend on sample location
- Mass balance models that aggregate measurements per zone
- Regulatory reporting tied to a specific sampling point

Always use the physical move time, even if that means back-dating the record by hours or days.

---

## What NOT to do

- Do **not** modify or delete the old `SignalPortLocationHistory` row. Historical location context must be preserved.
- Do **not** create a new `Channel` for the sensor at its new location. The channel belongs to the `SignalPort`, not the physical position.
- Do **not** omit `start_time` or set it to the current time unless the sensor was moved right now.
