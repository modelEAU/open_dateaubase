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

## Retiring a signal port

When a SCADA tag is decommissioned, mark its port inactive.  Historical data and
the Channel row are untouched.

```python
requests.patch(f"{API_BASE}/ingest/signal-ports/{signal_port_id}/deactivate").raise_for_status()
```
