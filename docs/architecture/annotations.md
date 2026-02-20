# Time Series Annotations (v1.7.0)

## What annotations are and why they exist

Annotations are human-authored interval records attached to a measurement channel
(`MetaData` entry). They capture expert knowledge that cannot be inferred from raw
values alone — a sensor was being cleaned, an anomaly was investigated, a storm event
affected a reading, etc.

Each annotation spans a `[StartTime, EndTime]` window on a single time series.
`EndTime = NULL` means either a point-in-time note or an **ongoing** situation (no
resolved end yet). Multiple annotations may overlap on the same channel and time range.

Annotations are distinct from:

| Concept | Table | Purpose |
|---|---|---|
| `EquipmentEvent` | `dbo.EquipmentEvent` | Structured lifecycle events (calibration, maintenance, deployment) |
| `DataLineage` / `ProcessingStep` | Phase 3 tables | Automated audit trail of algorithmic transformations |
| `Annotation` | `dbo.Annotation` | Free-form human commentary on any interval |

An annotation may optionally reference the `EquipmentEvent` that triggered it
(via the nullable `EquipmentEvent_ID` FK), linking the human note to the structured
event record.

---

## Schema

### `AnnotationType` — lookup table

Seeded at migration time. Never changes in normal operation.

| ID | Name | Color | Meaning |
|---|---|---|---|
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

```
Annotation_ID     — surrogate PK (IDENTITY)
Metadata_ID       — the time series being annotated (FK → MetaData)
AnnotationType_ID — what kind of annotation (FK → AnnotationType)
StartTime         — start of annotated range (DATETIME2, NOT NULL)
EndTime           — end of annotated range (DATETIME2, NULL = point or ongoing)
AuthorPerson_ID   — who wrote it (FK → Person, optional)
Campaign_ID       — associated campaign (FK → Campaign, optional)
EquipmentEvent_ID — triggering event (FK → EquipmentEvent, optional)
Title             — short label (NVARCHAR(200), optional)
Comment           — free-text body (NVARCHAR(MAX), optional)
CreatedAt         — server-set UTC creation time
ModifiedAt        — server-set UTC last-edit time (NULL until first edit)
```

Indexes:
- `IX_Annotation_MetaData_Time` on `(Metadata_ID, StartTime, EndTime)` — optimises interval overlap queries
- `IX_Annotation_Author` on `(AuthorPerson_ID, CreatedAt)` — optimises "my annotations" and dashboard feeds

---

## Interval overlap semantics

An annotation `[A.StartTime, A.EndTime]` overlaps a query window `[from, to]` when:

```
A.StartTime <= to  AND  (A.EndTime IS NULL  OR  A.EndTime >= from)
```

This is the standard Allen's interval overlap test. Point annotations (`EndTime = NULL`)
are treated as ongoing from `StartTime` forward, so they match any query window that
starts at or after `StartTime`.

```
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

### List annotations for a time series

```
GET /timeseries/{metadata_id}/annotations?from=<ISO8601>&to=<ISO8601>[&type=<name|id>]
```

Returns all annotations overlapping `[from, to]` for the given channel.

**Example response:**
```json
{
  "metadata_id": 42,
  "query_range": {"from": "2025-02-01T00:00:00", "to": "2025-02-28T23:59:59"},
  "annotations": [
    {
      "annotation_id": 7,
      "metadata_id": 42,
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

### Create annotation on a time series

```
POST /timeseries/{metadata_id}/annotations
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

### Get recent annotations (dashboard feed)

```
GET /annotations/recent?limit=20[&type=<name|id>]
```

Returns the most recently created annotations across all channels.

### Get annotations by type across all series

```
GET /annotations/by-type/{type_name}?from=<ISO8601>&to=<ISO8601>
```

### Update an annotation

```
PUT /annotations/{annotation_id}
```

Partial update — only fields provided in the body are changed.

### Delete an annotation

```
DELETE /annotations/{annotation_id}
```

Hard delete. Returns `204 No Content`.

### List annotation types

```
GET /annotation-types
```

Returns the full `AnnotationType` lookup table (for UI dropdowns).

---

## Adding a new annotation type

Annotation types are controlled-vocabulary rows in `AnnotationType`. To add one:

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
- **Multi-series annotations**: A junction table `AnnotationCoversMetaData(Annotation_ID,
  Metadata_ID)` would allow one annotation to span multiple channels simultaneously (e.g.,
  a storm event affecting an entire site). Currently, one annotation per channel is required.
- **Authentication**: `AuthorPerson_ID` is supplied by the client today. In a future
  authenticated API, this would be set from the JWT claim automatically.
