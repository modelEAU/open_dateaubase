# Time Series Annotations

## What annotations are and why they exist

Annotations are human-authored interval records attached to a measurement stream.
They capture expert knowledge that cannot be inferred from raw values alone — a
sensor was being cleaned, an anomaly was investigated, a storm event affected a
reading, etc.

An annotation anchors to **exactly one** stream — either a sensor `Channel`
(`Channel_ID` set) **or** a lab `AnalysisSeries` (`AnalysisSeries_ID` set). The two
anchors are mutually exclusive: a database `CK_Annotation_Source` XOR check enforces
that precisely one is non-NULL per row. Lab AnalysisSeries annotations have **full
parity** with sensor Channel annotations — range and point, create/read/update/delete,
and inclusion in the cross-stream `/recent` and `/by-type` feeds.

Each annotation spans a `[StartTime, EndTime]` window on its anchored stream.
`EndTime = NULL` means either a point-in-time note or an **ongoing** situation (no
resolved end yet). Multiple annotations may overlap on the same stream and time range.

Annotations are distinct from:

| Concept | Table | Purpose |
| --- | --- | --- |
| `EquipmentEvent` | `dbo.EquipmentEvent` | Structured lifecycle events (calibration, maintenance, deployment) |
| `DataLineage` / `ProcessingStep` | `dbo.DataLineage` / `dbo.ProcessingStep` | Automated audit trail of algorithmic transformations |
| `Annotation` | `dbo.Annotation` | Free-form human commentary on any interval |

An annotation may optionally reference the `EquipmentEvent` that triggered it
(via the nullable `EquipmentEvent_ID` FK), linking the human note to the structured
event record.

---

## Schema

### `AnnotationType` — lookup table

Seeded at migration time. Never changes in normal operation.

| ID | Name | Color | Meaning |
| --- | --- | --- | --- |
| 1 | Fault | `#FF4444` | Sensor or process fault |
| 2 | Maintenance | `#FFA500` | Sensor under maintenance |
| 3 | Calibration Period | `#FFD700` | Data during calibration — may be invalid |
| 4 | Anomaly | `#FF69B4` | Unexpected behavior, needs investigation |
| 5 | Experiment | `#4488FF` | Data collected during a specific experiment |
| 6 | Process Event | `#44BB44` | Known process event (storm, dosing, etc.) |
| 7 | Data Quality | `#AA44FF` | Suspect data quality (drift, fouling) |
| 8 | Note | `#888888` | General commentary |
| 9 | Exclusion | `#CC0000` | Data should be excluded from analysis |
| 10 | Validated | `#00AA00` | Data has been reviewed and accepted |

### `Annotation` — fact table

```text
Annotation_ID     — surrogate PK (IDENTITY)
Channel_ID        — the sensor channel being annotated (FK → Channel, NULL for lab)
AnalysisSeries_ID — the lab analysis series being annotated (FK → AnalysisSeries, NULL for sensor)
AnnotationType_ID — what kind of annotation (FK → AnnotationType)
StartTime         — start of annotated range (DATETIME2, NOT NULL)
EndTime           — end of annotated range (DATETIME2, NULL = point or ongoing)
Observation_ID    — optional point pin to one exact Observation (FK → Observation, optional);
                    for sensor pins one Channel Observation, for lab pins one Replicate
AuthorPerson_ID   — who wrote it (FK → Person, optional)
Campaign_ID       — associated campaign (FK → Campaign, optional)
EquipmentEvent_ID — triggering event (FK → EquipmentEvent, optional)
Title             — short label (NVARCHAR(200), optional)
Comment           — free-text body (NVARCHAR(MAX), optional)
CreatedAt         — server-set UTC creation time
ModifiedAt        — server-set UTC last-edit time (NULL until first edit)
```

Exactly one of `Channel_ID` / `AnalysisSeries_ID` is non-NULL per row, enforced by the
`CK_Annotation_Source` XOR check constraint (the exclusive-arc pattern — see
[ADR 0003](../adr/0003-exclusive-arc-for-sensor-lab-polymorphism.md)).

Indexes:

- `IX_Annotation_Channel_Time` on `(Channel_ID, StartTime, EndTime)` — optimises interval overlap queries for sensor-anchored annotations
- `IX_Annotation_Series_Time` on `(AnalysisSeries_ID, StartTime, EndTime)` — optimises interval overlap queries for lab-anchored annotations
- `IX_Annotation_Author` on `(AuthorPerson_ID, CreatedAt)` — optimises "my annotations" and dashboard feeds

---

## Interval overlap semantics

An annotation `[A.StartTime, A.EndTime]` overlaps a query window `[from, to]` when:

```text
A.StartTime <= to  AND  (A.EndTime IS NULL  OR  A.EndTime >= from)
```

This is the standard Allen's interval overlap test. Point annotations (`EndTime = NULL`)
are treated as ongoing from `StartTime` forward, so they match any query window that
starts at or after `StartTime`.

```text
Query window:       [────────────────]
                    from            to

Overlapping:
  Full overlap      [────────────────────]
  Left overlap  [──────────]
  Right overlap              [───────────]
  Contained     [─────]
  Point (null)  *               ← overlaps if StartTime <= to

Non-overlapping:
  Before        [────]
  After                              [────]
```

---

## API endpoints

All annotation endpoints are under `/api/v1`.

### List annotations for a channel

```http
GET /timeseries/{channel_id}/annotations?from=<ISO8601>&to=<ISO8601>[&type=<name|id>]
```

Returns all annotations overlapping `[from, to]` for the given channel.

**Example response:**

```json
{
  "channel_id": 42,
  "query_range": {"from": "2025-02-01T00:00:00", "to": "2025-02-28T23:59:59"},
  "annotations": [
    {
      "annotation_id": 7,
      "anchor": {"kind": "channel", "id": 42},
      "observation_id": null,
      "type": {"id": 2, "name": "Maintenance", "description": "...", "color": "#FFA500"},
      "start_time": "2025-02-10T08:00:00",
      "end_time": "2025-02-10T11:30:00",
      "title": "Probe cleaning",
      "comment": "Removed fouling from UV probe. Values during window unreliable.",
      "author": {"person_id": 3, "name": "Jane Smith"},
      "campaign_id": null,
      "equipment_event_id": 15,
      "created_at": "2025-02-10T12:00:00",
      "modified_at": null
    }
  ],
  "count": 1
}
```

### Create annotation on a channel

```http
POST /timeseries/{channel_id}/annotations
```

```json
{
  "annotation_type": "Maintenance",
  "start_time": "2025-02-10T08:00:00",
  "end_time": "2025-02-10T11:30:00",
  "title": "Probe cleaning",
  "comment": "Removed fouling from UV probe.",
  "equipment_event_id": 15,
  "author_person_id": 3
}
```

`annotation_type` accepts either the type name (string) or `AnnotationType_ID` (integer).

To pin an annotation to one exact reading, pass `observation_id`. The service rejects
(HTTP 422) a pin whose `Observation` does not belong to the anchored stream.

### List annotations for a lab AnalysisSeries

```http
GET /analysis-series/{series_id}/annotations?from=<ISO8601>&to=<ISO8601>[&type=<name|id>]
```

The parallel lab sub-resource. The envelope echoes `analysis_series_id` (instead of
`channel_id`) and each annotation carries `anchor: {"kind": "series", "id": <series_id>}`.

### Create annotation on a lab AnalysisSeries

```http
POST /analysis-series/{series_id}/annotations
```

Same body shape as the channel create. The created annotation is anchored to the
series (`anchor.kind == "series"`). A lab `observation_id` pin targets one Replicate of
the series.

### The per-annotation `anchor`

Every annotation in a response carries a discriminated `anchor` object identifying what
it is attached to:

```json
{"kind": "channel", "id": 42}   // sensor Channel
{"kind": "series",  "id": 7}    // lab AnalysisSeries
```

This replaced the earlier flat per-annotation `channel_id` field. (The list envelope
still echoes the queried `channel_id` / `analysis_series_id` at the top level as a
query echo — distinct from the per-row `anchor`.)

### Get recent annotations (dashboard feed)

```http
GET /annotations/recent?limit=20[&type=<name|id>]
```

Returns the most recently created annotations across all streams — both sensor
Channels and lab AnalysisSeries (UNIONed), ordered by creation time. Each item carries
its `anchor` plus a derived `location` and `variable` for the anchored stream.

### Get annotations by type across all streams

```http
GET /annotations/by-type/{type_name}?from=<ISO8601>&to=<ISO8601>
```

### Update an annotation

```http
PUT /annotations/{annotation_id}
```

Partial update — only fields provided in the body are changed.

### Delete an annotation

```http
DELETE /annotations/{annotation_id}
```

Hard delete. Returns `204 No Content`.

### List annotation types

```http
GET /annotation-types
```

Returns the full `AnnotationType` lookup table (for UI dropdowns).

---

## Adding a new annotation type

```sql
INSERT INTO [dbo].[AnnotationType] ([AnnotationType_ID], [AnnotationTypeName], [Description], [Color])
VALUES (11, N'Regulatory Sample', N'Sample collected for regulatory reporting purposes', N'#00CCDD');
```

There is no migration script required for adding vocabulary rows — they are data, not schema.
Coordinate with the team before adding types to avoid duplicates.

---

## Relationship to EquipmentEvents

`EquipmentEvent` records structured, lifecycle events (calibration runs, cleaning cycles,
deployment changes) with typed metadata. An `Annotation` can optionally reference the
event that caused it via `EquipmentEvent_ID`.

Typical pattern:

1. A technician logs a calibration event in `EquipmentEvent` (structured).
2. They also create a `Calibration Period` annotation on the affected channel covering
   the window when data is unreliable — and set `EquipmentEvent_ID` to link them.

This keeps the structured event and the human commentary independently queryable while
maintaining a traceable link.

---

## Future considerations (not implemented)

- **Annotation threading**: A `ParentAnnotation_ID` self-FK would allow replies/follow-ups
  on a single annotation, creating discussion threads.
- **Multi-stream annotations**: A junction table `AnnotationCoversChannel(Annotation_ID,
  Channel_ID)` would allow one annotation to span multiple streams simultaneously (e.g.,
  a storm event affecting an entire site). Currently, one annotation anchors to exactly
  one stream (a Channel **or** an AnalysisSeries).
- **Authentication**: `AuthorPerson_ID` is supplied by the client today. In a future
  authenticated API, this would be set from the JWT claim automatically.
