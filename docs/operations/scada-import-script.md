# Configuring a SCADA Import Script

This guide explains how to ingest data from a SCADA system (or any tag-based
data acquisition system) using the `POST /api/v1/ingest/sensor` endpoint.

## Overview

As of schema v3.0.0, sensor channels are identified by a **SignalPort** — the
stable identity of a signal within a given Data Acquisition System (DAS).  You
no longer need to look up equipment IDs before ingesting data.  A minimal
import script only needs to know:

- The **DAS name** (e.g. `"Plant SCADA"`)
- The **tag** (e.g. `"TIT-101"`)
- The **parameter name** (e.g. `"temperature"`)
- The **unit name** (e.g. `"degC"`)

## Minimal configuration example

```python
import requests

API_BASE = "http://localhost:8000/api/v1"

def push_readings(tag: str, readings: list[dict]) -> dict:
    payload = {
        "das_name": "Plant SCADA",
        "tag": tag,
        "signal_port_type": "value",   # default; omit if not needed
        "parameter_name": "temperature",
        "unit_name": "degC",
        "data_provenance_id": 1,       # 1 = Sensor (default)
        "processing_degree_id": 1,     # 1 = Raw (default)
        "values": readings,
    }
    resp = requests.post(f"{API_BASE}/ingest/sensor", json=payload)
    resp.raise_for_status()
    return resp.json()

# Example call
result = push_readings(
    tag="TIT-101",
    readings=[
        {"timestamp": "2024-06-01T08:00:00", "value": 18.3},
        {"timestamp": "2024-06-01T08:05:00", "value": 18.5},
    ],
)
print(result)
# {"channel_id": 7, "rows_written": 2, "warnings": [], "processing_step_id": null}
```

## Warning vs. error behaviour

The endpoint distinguishes between two categories of unrecognised inputs:

| Input | Behaviour | Effect on ingestion |
|---|---|---|
| Unknown `das_name` | **Warning** — DAS auto-created | Ingestion continues |
| Unknown `tag` | **Warning** — SignalPort auto-created | Ingestion continues |
| Unknown `parameter_name` | **Error** — HTTP 422 | Ingestion halted, no DB writes |
| Unknown `unit_name` | **Error** — HTTP 422 | Ingestion halted, no DB writes |
| Unknown `signal_port_type` | **Error** — HTTP 422 | Ingestion halted, no DB writes |

### Why this distinction?

DAS names and tags are _infrastructure identifiers_ — it is normal for a new
SCADA system or a new sensor tag to be seen for the first time during ingestion.
Auto-creating them preserves data continuity without manual pre-registration.

Parameter and unit names are _measurement semantics_.  A typo in `parameter_name`
(e.g. `"tempreature"`) would silently create a junk channel and corrupt the data
model.  A validation error forces the import script author to fix the config
before any data is written.

### Reading warnings from the response

When a DAS or SignalPort is auto-created, the response includes a `warnings` list:

```json
{
  "channel_id": 12,
  "rows_written": 100,
  "processing_step_id": null,
  "warnings": [
    "DataAcquisitionSystem 'Plant SCADA' was not found and has been auto-created (ID=3).",
    "SignalPort tag='TIT-999' (DAS='Plant SCADA') was not found and has been auto-created (ID=17)."
  ]
}
```

Warnings are also logged at `WARNING` level on the server.  On first deploy,
expect one warning per DAS and one per tag.  Subsequent runs produce no warnings.

## Name lookup rules

All name comparisons are **case-insensitive and whitespace-trimmed**.  The
following are equivalent:

```
"temperature"  ==  "Temperature"  ==  "  TEMPERATURE  "
"degC"         ==  "degc"         ==  "  DegC  "
"Plant SCADA"  ==  "plant scada"  ==  "  Plant SCADA  "
"TIT-101"      ==  "tit-101"      ==  "  TIT-101  "
```

Tags are stored case-preserved in the database (the first spelling wins) but
future lookups always normalise before comparing.

## Valid `signal_port_type` values

| String | Meaning |
|---|---|
| `"value"` | Primary measurement or output value *(default)* |
| `"status"` | Device or measurement status flag |
| `"alarm"` | Alarm or alert indicator |
| `"uncertainty"` | Measurement uncertainty estimate |

## Deduplication / watermark pattern

To avoid re-ingesting already-stored data, query the last timestamp for a
channel before sending new rows:

```python
def get_last_timestamp(channel_id: int) -> str | None:
    resp = requests.get(
        f"{API_BASE}/ingest/last-timestamp",
        params={"channel_id": channel_id},
    )
    resp.raise_for_status()
    return resp.json()["last_timestamp"]  # ISO 8601 string or null
```

Once you have the `channel_id` from the first successful ingest response, pass
it here to get the watermark for subsequent runs.

## Tagless (direct-connect) ingest

Some monitoring stations (e.g. bench analysers, stand-alone data loggers) connect
directly to the API and have no SCADA tag names.  For these use the
`POST /api/v1/ingest/sensor-tagless` endpoint instead.

### When to use tagless mode

| Mode | Use when |
|---|---|
| Tag mode (`/ingest/sensor`) | Signal has a SCADA tag (e.g. `TIT-101`) |
| Tagless mode (`/ingest/sensor-tagless`) | No tag — you identify signals by equipment + parameter |

### Auto-tag generation rule

The endpoint derives a stable, deterministic SignalPort tag from the two inputs:

```text
tag = "{equipment_identifier.strip().lower()}/{parameter_name.strip().lower()}"
```

Examples:

| `equipment_identifier` | `parameter_name` | Generated tag |
|---|---|---|
| `"Probe_A"` | `"DO"` | `"probe_a/do"` |
| `" Probe_A "` | `" DO "` | `"probe_a/do"` (whitespace stripped) |
| `"Station1"` | `"Dissolved Oxygen"` | `"station1/dissolved oxygen"` |

The tag is computed before any database lookup, so the same inputs always produce
the same tag across all runs.

### Tagless ingest example

```python
import requests

API_BASE = "http://localhost:8000/api/v1"

def push_direct_readings(equipment_id: str, readings: list[dict]) -> dict:
    payload = {
        "das_name": "BenchAnalyser",
        "equipment_identifier": equipment_id,
        "parameter_name": "dissolved oxygen",
        "unit_name": "mg/L",
        "data_provenance_id": 1,   # 1 = Sensor (default)
        "processing_degree_id": 1, # 1 = Raw (default)
        "values": readings,
    }
    resp = requests.post(f"{API_BASE}/ingest/sensor-tagless", json=payload)
    resp.raise_for_status()
    return resp.json()

result = push_direct_readings(
    equipment_id="Probe_A",
    readings=[{"timestamp": "2024-06-01T08:00:00", "value": 8.3}],
)
print(result)
# {"channel_id": 14, "rows_written": 1, "warnings": [...], "processing_step_id": null}
```

### How `SignalPortEquipmentHistory` is seeded automatically

When the port is **first created**, the endpoint immediately opens a
`SignalPortEquipmentHistory` row linking the Equipment to the port with
`StartTime = now (UTC)` and `EndTime = NULL` (currently active).  This means
provenance is recorded at ingest time — you do not need a separate API call to
register the equipment.

On **subsequent calls** with the same inputs the port already exists, so no
duplicate history row is created.

### Warning vs. error behaviour for tagless mode

| Input | Behaviour | Effect on ingestion |
|---|---|---|
| Unknown `das_name` | **Warning** — DAS auto-created | Ingestion continues |
| Unknown `equipment_identifier` | **Warning** — Equipment auto-created | Ingestion continues |
| Unknown `parameter_name` | **Error** — HTTP 422 | Ingestion halted, no DB writes |
| Unknown `unit_name` | **Error** — HTTP 422 | Ingestion halted, no DB writes |

Equipment identifiers follow the same "auto-create with warning" policy as DAS
names and SCADA tags — it is normal to encounter new equipment at ingest time.
Parameter and unit names still require pre-registration because a typo would
silently corrupt the data model.

---

## Retiring a signal port

When a SCADA tag is decommissioned, mark its port inactive.  Historical data and
the Channel row are untouched.

```python
requests.patch(f"{API_BASE}/ingest/signal-ports/{signal_port_id}/deactivate").raise_for_status()
```
