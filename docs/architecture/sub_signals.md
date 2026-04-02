# Sub-Signal Grouping

## Background

Every physical measurement point typically exposes more than one data stream.
A dissolved-oxygen probe, for example, publishes a primary DO value **and** a
device health status code **and** a measurement uncertainty estimate.  In
open_datEAUbase these streams are modelled as separate `SignalPort` rows that
share the same physical location — linked by `ParentPort_ID`.

---

## Data model

```
SignalPort (TIT-101, SignalPortType=Value, ParentPort_ID=NULL)   ← parent
  └── SignalPort (TIT-101/status,      SignalPortType=Status,      ParentPort_ID=<parent>)
  └── SignalPort (TIT-101/alarm,       SignalPortType=Alarm,       ParentPort_ID=<parent>)
  └── SignalPort (TIT-101/uncertainty, SignalPortType=Uncertainty, ParentPort_ID=<parent>)
```

| Column | Notes |
| --- | --- |
| `ParentPort_ID` | `NULL` on value ports; points to the parent port on sub-signals |
| `SignalPortType_ID` | Discriminates between Value (1), Status (2), Alarm (3), Uncertainty (4) |

Sub-signal ports share equipment and location history with their parent — they
are *attributes* of a signal, not independent measurement points.

---

## Constraints

**Sub-signal ports cannot be relocated independently.**

A relocation call (`POST /ports/{id}/relocate`) against a port whose
`ParentPort_ID IS NOT NULL` returns `422 Unprocessable Entity`:

```json
{
  "detail": "SignalPort 42 is a sub-signal port (ParentPort_ID=17) and cannot
             be relocated independently. Relocate the parent port instead."
}
```

Relocating the parent port leaves all sub-signal `ParentPort_ID` links
unchanged — sub-signals continue to point to the same parent regardless of
where the parent moves.

---

## Ingest: declaring a sub-signal with `parent_tag`

Add `parent_tag` to a `SensorIngestRequest` to link the new port to an
existing parent value port at ingest time.

### Request fields

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `das_name` | string | yes | Name of the DataAcquisitionSystem |
| `tag` | string | yes | Tag for the sub-signal port (e.g. `"TIT-101/status"`) |
| `signal_port_type` | string | no | One of `"value"`, `"status"`, `"alarm"`, `"uncertainty"` (default `"value"`) |
| `parent_tag` | string | no | Tag of the parent value port in the same DAS.  Omit for primary value ports. |
| `parameter_name` | string | yes | Measured quantity |
| `unit_name` | string | yes | Measurement unit |
| `values` | list | yes | One or more `{timestamp, value}` items |

### Example — ingest a Status sub-signal

```bash
POST /api/v1/ingest/sensor
Content-Type: application/json

{
  "das_name": "SCADA-WWTP",
  "tag": "TIT-101/status",
  "signal_port_type": "status",
  "parent_tag": "TIT-101",
  "parameter_name": "Device Status Code",
  "unit_name": "dimensionless",
  "values": [
    {"timestamp": "2024-06-01T08:00:00Z", "value": 1},
    {"timestamp": "2024-06-01T08:15:00Z", "value": 1}
  ]
}
```

### Behaviour

1. `parent_tag` is resolved to a `SignalPort_ID` within the same DAS.
2. If the tag is not found → **422** is returned before any database write.
3. `set_parent_port` is called after the Channel row is created.  The call is
   idempotent: re-ingesting with the same `parent_tag` succeeds silently.
4. Attempting to reassign a port to a *different* parent → **422**.
5. If `parent_tag` is omitted, the parent-linking step is skipped entirely.

---

## API: query sub-signals

### `GET /api/v1/ports/{signal_port_id}/sub-signals`

Returns all ports whose `ParentPort_ID` equals `signal_port_id`.

#### Path parameter

| Parameter | Type | Notes |
| --- | --- | --- |
| `signal_port_id` | integer | The parent value port |

#### Response `200 OK`

```json
{
  "parent_port_id": 17,
  "sub_signals": [
    {
      "signal_port_id": 42,
      "tag": "TIT-101/status",
      "is_active": true,
      "description": null,
      "parent_port_id": 17,
      "signal_port_type_id": 2,
      "signal_port_type_name": "Status"
    },
    {
      "signal_port_id": 43,
      "tag": "TIT-101/alarm",
      "is_active": true,
      "description": null,
      "parent_port_id": 17,
      "signal_port_type_id": 3,
      "signal_port_type_name": "Alarm"
    }
  ]
}
```

Returns `{"parent_port_id": 17, "sub_signals": []}` when no sub-signals exist.

---

## See also

- [SignalPortType](../reference/signal_port_types.md)
- [Sensor Relocation SOP](../operations/sensor-relocation-sop.md)
