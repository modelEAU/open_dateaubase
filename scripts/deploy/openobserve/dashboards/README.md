# OpenObserve dashboards

The dashboard JSON in this folder is **finicky and machine-generated** — don't
hand-author it. Build panels in the OpenObserve UI, **Export**, drop the file
here, and let the deploy publish it idempotently via
`Publish-OpenObserveDashboard` (matches by title, so re-running updates in place).

## What fields are available

Every log line the app emits is single-line JSON. Vector's `parse_json` hoists
these to queryable columns (see `Write-VectorConfig` in `DeployHelpers.psm1` and
`api/logging_config.py` / `api/observability.py`):

| field          | source                            | use for                          |
|----------------|-----------------------------------|----------------------------------|
| `service`      | Vector (from container/log dir)   | which service                    |
| `level`        | every record (`info` / `error`)   | **filter errors cleanly**        |
| `status`       | request timing record             | HTTP status, 5xx error rate      |
| `duration_ms`  | request timing record             | latency percentiles, slow reqs   |
| `db_connect_ms`| request timing record             | DB-pool pressure                 |
| `uri`/`method` | request timing record             | per-route breakdown              |
| `request_id`   | request timing + error record     | tie an error to its request      |
| `traceback`    | error records only                | the actual failure stack         |

> The old dashboard matched errors with `message LIKE '%ERROR%'` — brittle.
> With `level` now hoisted, prefer `WHERE level = 'error'` (plus `status >= 500`).

## Build these panels (UI → custom SQL per panel)

Stream: `open_dateaubase`, type `logs`. Set the dashboard time range to ~6h.

1. **Service health — log volume per service** (bar)
   `SELECT histogram(_timestamp) AS x, count(*) AS y, service AS s FROM "open_dateaubase" GROUP BY x, s ORDER BY x`
   A service that stops producing lines = likely down.

2. **Errors per service** (bar)
   `SELECT histogram(_timestamp) AS x, count(*) AS y, service AS s FROM "open_dateaubase" WHERE level = 'error' OR status >= 500 GROUP BY x, s ORDER BY x`

3. **Latency p50/p95 by route** (line) — degradation signal
   `SELECT histogram(_timestamp) AS x, approx_percentile_cont(duration_ms, 0.95) AS p95, approx_percentile_cont(duration_ms, 0.5) AS p50, uri AS s FROM "open_dateaubase" WHERE duration_ms IS NOT NULL GROUP BY x, s ORDER BY x`

4. **DB connect time** (line) — pool pressure
   `SELECT histogram(_timestamp) AS x, avg(db_connect_ms) AS y FROM "open_dateaubase" WHERE db_connect_ms IS NOT NULL GROUP BY x ORDER BY x`

5. **Slow requests** (table)
   `SELECT _timestamp, uri, status, duration_ms, request_id FROM "open_dateaubase" WHERE duration_ms > 1000 ORDER BY _timestamp DESC LIMIT 50`

6. **Failures — dig into actual errors** (table) — the view OpenObserve was bad at
   `SELECT _timestamp, service, request_id, uri, status, message, traceback FROM "open_dateaubase" WHERE level = 'error' OR status >= 500 ORDER BY _timestamp DESC LIMIT 50`
   Grab a `request_id` from here and search `request_id='xxxx'` to see that
   request's whole story.

## Publish

```powershell
Import-Module ./scripts/deploy/DeployHelpers.psm1
Publish-OpenObserveDashboard -ViewerPort 5080 -User <admin> -Password <pw> `
  -TemplatePath ./scripts/deploy/openobserve/dashboards/service-health.dashboard.json
```

Export from the UI overwrites the JSON here; keep the same `title` so publish
updates the existing dashboard rather than creating a duplicate.

> User DB actions (who created/updated/deleted what) are **not** in OpenObserve —
> they live in `dbo.AuditLog` and are browsable in the app's **Audit Log** page
> (`app/pages/Audit_Log.py`). Kept out of the log store on purpose.
