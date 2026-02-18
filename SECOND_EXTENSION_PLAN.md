PR 1: Time Series Annotations

Prompt for Claude Code

markdown

# PR: Time Series Annotations

## Context

You are working in the open_datEAUbase repository. The schema is defined 
as YAML files in `schema_dictionary/tables/` and migrations are generated 
using the tooling in `tools/schema_migrate/`. Before starting, read:

1. `schema_dictionary/tables/MetaData.yaml` — understand the current MetaData structure
2. `schema_dictionary/tables/Person.yaml` — exists from Phase 2a
3. `schema_dictionary/tables/Campaign.yaml` — exists from Phase 2a
4. `schema_dictionary/tables/EquipmentEvent.yaml` — may or may not exist yet (Phase 2c)
5. `schema_dictionary/version.yaml` — current schema version
6. `tools/schema_migrate/` — understand how migrations are generated
7. Any existing API code in `api/` — understand current endpoint patterns

Read all of these files before making any changes.

## What This PR Does

Adds the ability to annotate time series data with human-authored 
comments on time ranges. Annotations are interval-based (start time + 
optional end time), typed (fault, anomaly, experiment, etc.), additive 
(multiple annotations can overlap on the same time range), and linked 
to the MetaData backbone.

## Schema Changes

### Table 1: dbo.AnnotationType

Create `schema_dictionary/tables/AnnotationType.yaml`:

```yaml
_format_version: "1.0"
table:
  name: AnnotationType
  schema: dbo
  description: >
    Lookup table defining the kinds of annotations that can be applied 
    to time series data. Each type has a display color for UI rendering.
  columns:
    - name: AnnotationTypeID
      logical_type: integer
      nullable: false
      description: "Primary key, manually assigned"
    - name: AnnotationTypeName
      logical_type: string
      max_length: 100
      nullable: false
      description: "Human-readable name of the annotation type"
    - name: Description
      logical_type: string
      max_length: 500
      nullable: true
      description: "Explanation of when to use this annotation type"
    - name: Color
      logical_type: string
      max_length: 7
      nullable: true
      description: "Hex color code for UI rendering, e.g. '#FF6B6B'"
  primary_key: [AnnotationTypeID]
  seed_data:
    - { AnnotationTypeID: 1,  AnnotationTypeName: "Fault",              Description: "Sensor or process fault",                  Color: "#FF4444" }
    - { AnnotationTypeID: 2,  AnnotationTypeName: "Maintenance",        Description: "Sensor under maintenance",                 Color: "#FFA500" }
    - { AnnotationTypeID: 3,  AnnotationTypeName: "Calibration Period", Description: "Data during calibration — may be invalid",  Color: "#FFD700" }
    - { AnnotationTypeID: 4,  AnnotationTypeName: "Anomaly",            Description: "Unexpected behavior, needs investigation",  Color: "#FF69B4" }
    - { AnnotationTypeID: 5,  AnnotationTypeName: "Experiment",         Description: "Data collected during a specific experiment", Color: "#4488FF" }
    - { AnnotationTypeID: 6,  AnnotationTypeName: "Process Event",      Description: "Known process event (storm, dosing, etc.)", Color: "#44BB44" }
    - { AnnotationTypeID: 7,  AnnotationTypeName: "Data Quality",       Description: "Suspect data quality (drift, fouling)",     Color: "#AA44FF" }
    - { AnnotationTypeID: 8,  AnnotationTypeName: "Note",               Description: "General commentary",                       Color: "#888888" }
    - { AnnotationTypeID: 9,  AnnotationTypeName: "Exclusion",          Description: "Data should be excluded from analysis",     Color: "#CC0000" }
    - { AnnotationTypeID: 10, AnnotationTypeName: "Validated",          Description: "Data has been reviewed and accepted",       Color: "#00AA00" }
Table 2: dbo.Annotation

Create schema_dictionary/tables/Annotation.yaml:

yaml

_format_version: "1.0"
table:
  name: Annotation
  schema: dbo
  description: >
    Human-authored annotations on time series data. Each annotation 
    applies to a single MetaData entry (one measurement channel) over 
    a time range. Multiple annotations can overlap on the same range. 
    EndTime=NULL means either a point annotation or an ongoing situation.
  columns:
    - name: AnnotationID
      logical_type: integer
      nullable: false
      identity: true
      description: "Primary key, auto-incremented"
    - name: MetaDataID
      logical_type: integer
      nullable: false
      description: "The time series this annotation applies to"
      foreign_key:
        table: MetaData
        column: MetaDataID
    - name: AnnotationTypeID
      logical_type: integer
      nullable: false
      description: "What kind of annotation this is"
      foreign_key:
        table: AnnotationType
        column: AnnotationTypeID
    - name: StartTime
      logical_type: timestamp
      precision: 7
      nullable: false
      description: "Start of the annotated time range"
    - name: EndTime
      logical_type: timestamp
      precision: 7
      nullable: true
      description: "End of the annotated range. NULL = point annotation or ongoing"
    - name: AuthorPersonID
      logical_type: integer
      nullable: true
      description: "Person who created this annotation"
      foreign_key:
        table: Person
        column: PersonID
    - name: CampaignID
      logical_type: integer
      nullable: true
      description: "Campaign this annotation is associated with, if any"
      foreign_key:
        table: Campaign
        column: CampaignID
    - name: EquipmentEventID
      logical_type: integer
      nullable: true
      description: >
        Equipment event that caused this annotation, if any.
        Only add this FK if dbo.EquipmentEvent exists. If Phase 2c 
        has not been implemented yet, create this column WITHOUT the 
        FK constraint and add a TODO comment in the YAML.
      foreign_key:
        table: EquipmentEvent
        column: EquipmentEventID
    - name: Title
      logical_type: string
      max_length: 200
      nullable: true
      description: "Short title for the annotation"
    - name: Comment
      logical_type: string
      max_length: max
      nullable: true
      description: "Detailed free-text comment"
    - name: CreatedAt
      logical_type: timestamp
      precision: 7
      nullable: false
      default: CURRENT_TIMESTAMP
      description: "When this annotation was created"
    - name: ModifiedAt
      logical_type: timestamp
      precision: 7
      nullable: true
      description: "When this annotation was last modified"
  primary_key: [AnnotationID]
  indexes:
    - name: IX_Annotation_MetaData_Time
      columns: [MetaDataID, StartTime, EndTime]
      description: "Optimizes interval overlap queries"
    - name: IX_Annotation_Author
      columns: [AuthorPersonID, CreatedAt]
      description: "Optimizes 'my annotations' and 'recent annotations' queries"
Migration Script

Generate the migration from the current schema version to the next.
The migration must:

CREATE TABLE dbo.AnnotationType with all columns and PK
INSERT all 10 seed data rows
CREATE TABLE dbo.Annotation with all columns, PK, FKs, and indexes
If dbo.EquipmentEvent does NOT exist in the current schema,
create the EquipmentEventID column WITHOUT the FK constraint
and add a comment: -- TODO: Add FK to EquipmentEvent when Phase 2c is implemented
UPDATE dbo.SchemaVersion with the new version
The rollback script must:

DROP TABLE dbo.Annotation
DROP TABLE dbo.AnnotationType
DELETE the SchemaVersion row
SQL Queries to Implement

Query 1: Get Annotations Overlapping a Time Range

This is the most critical query. An annotation overlaps [T1, T2] if
it starts before T2 AND (it has no end, or it ends after T1).

sql

-- Parameters: @MetaDataID INT, @T1 DATETIME2(7), @T2 DATETIME2(7)
SELECT 
    a.AnnotationID,
    a.MetaDataID,
    at.AnnotationTypeName,
    at.Color,
    a.StartTime,
    a.EndTime,
    a.Title,
    a.Comment,
    p.FullName AS AuthorName,
    c.Name AS CampaignName,
    a.CreatedAt,
    a.ModifiedAt
FROM dbo.Annotation a
JOIN dbo.AnnotationType at 
    ON at.AnnotationTypeID = a.AnnotationTypeID
LEFT JOIN dbo.Person p 
    ON p.PersonID = a.AuthorPersonID
LEFT JOIN dbo.Campaign c 
    ON c.CampaignID = a.CampaignID
WHERE a.MetaDataID = @MetaDataID
  AND a.StartTime <= @T2
  AND (a.EndTime IS NULL OR a.EndTime >= @T1)
ORDER BY a.StartTime, a.AnnotationTypeID;
Query 2: Get Annotations by Type Across All Series

sql

-- Parameters: @AnnotationTypeID INT, @T1 DATETIME2(7), @T2 DATETIME2(7)
SELECT 
    a.AnnotationID,
    a.MetaDataID,
    sl.Name AS LocationName,
    var.Name AS VariableName,
    at.AnnotationTypeName,
    at.Color,
    a.StartTime,
    a.EndTime,
    a.Title,
    a.Comment,
    p.FullName AS AuthorName
FROM dbo.Annotation a
JOIN dbo.AnnotationType at 
    ON at.AnnotationTypeID = a.AnnotationTypeID
JOIN dbo.MetaData md 
    ON md.MetaDataID = a.MetaDataID
JOIN dbo.SamplingLocation sl 
    ON sl.SamplingLocationID = md.SamplingLocationID
JOIN dbo.Variable var 
    ON var.VariableID = md.VariableID
LEFT JOIN dbo.Person p 
    ON p.PersonID = a.AuthorPersonID
WHERE a.AnnotationTypeID = @AnnotationTypeID
  AND a.StartTime <= @T2
  AND (a.EndTime IS NULL OR a.EndTime >= @T1)
ORDER BY a.StartTime;
Query 3: Recent Annotations (Dashboard Feed)

sql

-- Parameters: @Limit INT = 20
SELECT TOP (@Limit)
    a.AnnotationID,
    a.MetaDataID,
    sl.Name AS LocationName,
    var.Name AS VariableName,
    at.AnnotationTypeName,
    at.Color,
    a.StartTime,
    a.EndTime,
    a.Title,
    a.Comment,
    p.FullName AS AuthorName,
    a.CreatedAt
FROM dbo.Annotation a
JOIN dbo.AnnotationType at 
    ON at.AnnotationTypeID = a.AnnotationTypeID
JOIN dbo.MetaData md 
    ON md.MetaDataID = a.MetaDataID
JOIN dbo.SamplingLocation sl 
    ON sl.SamplingLocationID = md.SamplingLocationID
JOIN dbo.Variable var 
    ON var.VariableID = md.VariableID
LEFT JOIN dbo.Person p 
    ON p.PersonID = a.AuthorPersonID
ORDER BY a.CreatedAt DESC;
Query 4: Insert Annotation

sql

-- Parameters: @MetaDataID, @AnnotationTypeID, @StartTime, @EndTime (nullable),
--             @AuthorPersonID (nullable), @CampaignID (nullable),
--             @EquipmentEventID (nullable), @Title (nullable), @Comment (nullable)
INSERT INTO dbo.Annotation (
    MetaDataID, AnnotationTypeID, StartTime, EndTime,
    AuthorPersonID, CampaignID, EquipmentEventID,
    Title, Comment
)
OUTPUT INSERTED.AnnotationID, INSERTED.CreatedAt
VALUES (
    @MetaDataID, @AnnotationTypeID, @StartTime, @EndTime,
    @AuthorPersonID, @CampaignID, @EquipmentEventID,
    @Title, @Comment
);
Query 5: Update Annotation

sql

-- Parameters: @AnnotationID, @AnnotationTypeID, @StartTime, @EndTime,
--             @Title, @Comment
UPDATE dbo.Annotation
SET AnnotationTypeID = @AnnotationTypeID,
    StartTime = @StartTime,
    EndTime = @EndTime,
    Title = @Title,
    Comment = @Comment,
    ModifiedAt = SYSUTCDATETIME()
WHERE AnnotationID = @AnnotationID;
Query 6: Delete Annotation

sql

-- Parameters: @AnnotationID
DELETE FROM dbo.Annotation
WHERE AnnotationID = @AnnotationID;
API Endpoints

Endpoint 1: GET /api/v1/timeseries/{metadata_id}/annotations

Purpose: Get all annotations overlapping a time range for a specific
time series.

Query parameters:

Parameter	Type	Required	Description
from	ISO 8601 datetime	Yes	Start of query range
to	ISO 8601 datetime	Yes	End of query range
type	string or int	No	Filter by AnnotationTypeName or AnnotationTypeID
Response schema (200):

json

{
  "metadata_id": 42,
  "query_range": {
    "from": "2025-01-01T00:00:00Z",
    "to": "2025-03-31T23:59:59Z"
  },
  "annotations": [
    {
      "annotation_id": 1,
      "type": {
        "id": 6,
        "name": "Process Event",
        "color": "#44BB44"
      },
      "start_time": "2025-01-20T00:00:00Z",
      "end_time": "2025-01-22T00:00:00Z",
      "title": "Storm event",
      "comment": "Major rainfall event, influent flow 3x normal.",
      "author": {
        "person_id": 5,
        "name": "Marie Dupont"
      },
      "campaign": null,
      "equipment_event_id": null,
      "created_at": "2025-01-22T09:30:00Z",
      "modified_at": null
    }
  ],
  "count": 1
}
Error responses:

404: MetaData ID not found
422: Missing or invalid query parameters
Implementation: Use Query 1 from above. Wrap in the repository layer.

Endpoint 2: POST /api/v1/timeseries/{metadata_id}/annotations

Purpose: Create a new annotation on a time series.

Request body:

json

{
  "annotation_type": "Fault",
  "start_time": "2025-02-15T10:00:00Z",
  "end_time": "2025-02-15T14:00:00Z",
  "title": "Sensor fouled",
  "comment": "Biofilm buildup visible on probe. Values likely biased high.",
  "campaign_id": null,
  "equipment_event_id": null
}
Field validation rules:

annotation_type: Required. Accept either AnnotationTypeName (string)
or AnnotationTypeID (int). If string, resolve to ID via lookup.
start_time: Required. Must be valid ISO 8601.
end_time: Optional. If provided, must be >= start_time.
title: Optional. Max 200 characters.
comment: Optional. No length limit in API (DB allows MAX).
campaign_id: Optional. If provided, must exist in dbo.Campaign.
equipment_event_id: Optional. If provided, must exist in dbo.EquipmentEvent.
author_person_id is NOT in the request body. It is set from the
authenticated user context. If no auth yet, accept it as an optional
field for now with a TODO comment.
Response schema (201):

json

{
  "annotation_id": 17,
  "metadata_id": 42,
  "type": {
    "id": 1,
    "name": "Fault",
    "color": "#FF4444"
  },
  "start_time": "2025-02-15T10:00:00Z",
  "end_time": "2025-02-15T14:00:00Z",
  "title": "Sensor fouled",
  "created_at": "2025-06-14T11:22:33Z"
}
Error responses:

404: MetaData ID not found
404: annotation_type name not found in AnnotationType
404: campaign_id not found in Campaign
422: end_time before start_time
422: Missing required fields
Implementation: Validate all FK references exist before INSERT.
Use Query 4.

Endpoint 3: PUT /api/v1/annotations/{annotation_id}

Purpose: Update an existing annotation.

Request body (all fields optional — only provided fields are updated):

json

{
  "annotation_type": "Data Quality",
  "start_time": "2025-02-14T10:00:00Z",
  "end_time": "2025-02-15T14:00:00Z",
  "title": "Sensor fouled — confirmed",
  "comment": "Updated: fouling started a day earlier based on lab comparison."
}
Response schema (200): Full annotation object (same shape as POST 201
response but with all fields including modified_at).

Error responses:

404: Annotation ID not found
422: Invalid fields (same rules as POST)
Implementation: Use Query 5. Return the updated row.

Endpoint 4: DELETE /api/v1/annotations/{annotation_id}

Purpose: Delete an annotation.

Response: 204 No Content

Error responses:

404: Annotation ID not found
Implementation: Use Query 6. Hard delete. If the team prefers soft
delete, add an IsDeleted BIT column to the schema and filter it in all
queries instead. Start with hard delete and add soft delete later if needed.

Endpoint 5: GET /api/v1/annotations/recent

Purpose: Dashboard feed of most recent annotations across all series.

Query parameters:

Parameter	Type	Required	Default	Description
limit	int	No	20	Number of annotations to return (max 100)
type	string or int	No	-	Filter by annotation type
site_id	int	No	-	Filter by site
Response schema (200):

json

{
  "annotations": [
    {
      "annotation_id": 17,
      "metadata_id": 42,
      "location": "Primary Effluent",
      "variable": "TSS",
      "type": {
        "id": 1,
        "name": "Fault",
        "color": "#FF4444"
      },
      "start_time": "2025-02-15T10:00:00Z",
      "end_time": "2025-02-15T14:00:00Z",
      "title": "Sensor fouled",
      "comment": "Biofilm buildup visible on probe.",
      "author": {
        "person_id": 5,
        "name": "Marie Dupont"
      },
      "created_at": "2025-06-14T11:22:33Z"
    }
  ],
  "count": 1
}
Implementation: Use Query 3.

Endpoint 6: GET /api/v1/annotations/by-type/{type_name}

Purpose: All annotations of a given type across all series in a
time range.

Query parameters:

Parameter	Type	Required	Description
from	ISO 8601 datetime	Yes	Start of query range
to	ISO 8601 datetime	Yes	End of query range
site_id	int	No	Filter by site
Response schema (200): Same shape as Endpoint 5 response.

Implementation: Use Query 2.

Endpoint 7: GET /api/v1/annotation-types

Purpose: List all available annotation types (for populating UI
dropdowns).

Response schema (200):

json

{
  "annotation_types": [
    {
      "id": 1,
      "name": "Fault",
      "description": "Sensor or process fault",
      "color": "#FF4444"
    }
  ]
}
Implementation: Simple SELECT * FROM dbo.AnnotationType ORDER BY AnnotationTypeID.

API Implementation Structure

Create or modify these files:


api/v1/
  schemas/
    annotations.py          # Pydantic models for all request/response shapes
  endpoints/
    annotations.py          # All 7 endpoint handlers
  services/
    annotation_service.py   # Business logic (validation, FK checks)
  repositories/
    annotation_repository.py  # SQL execution (Queries 1-6)
In annotations.py (schemas), define these Pydantic models:

python

from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional

class AnnotationTypeResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    color: Optional[str] = None

class AnnotationAuthor(BaseModel):
    person_id: int
    name: str

class AnnotationResponse(BaseModel):
    annotation_id: int
    metadata_id: int
    type: AnnotationTypeResponse
    start_time: datetime
    end_time: Optional[datetime] = None
    title: Optional[str] = None
    comment: Optional[str] = None
    author: Optional[AnnotationAuthor] = None
    campaign: Optional[str] = None
    equipment_event_id: Optional[int] = None
    created_at: datetime
    modified_at: Optional[datetime] = None

class AnnotationListResponse(BaseModel):
    metadata_id: Optional[int] = None
    query_range: Optional[dict] = None
    annotations: list[AnnotationResponse]
    count: int

class AnnotationCreate(BaseModel):
    annotation_type: str | int  # Name or ID
    start_time: datetime
    end_time: Optional[datetime] = None
    title: Optional[str] = Field(None, max_length=200)
    comment: Optional[str] = None
    campaign_id: Optional[int] = None
    equipment_event_id: Optional[int] = None
    author_person_id: Optional[int] = None  # TODO: replace with auth context

    @field_validator('end_time')
    @classmethod
    def end_after_start(cls, v, info):
        if v is not None and 'start_time' in info.data and v < info.data['start_time']:
            raise ValueError('end_time must be >= start_time')
        return v

class AnnotationUpdate(BaseModel):
    annotation_type: Optional[str | int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    title: Optional[str] = Field(None, max_length=200)
    comment: Optional[str] = None
Tests

Create test files:

Test 1: Schema Validation


tests/schema/test_annotation_yaml.py
Verify AnnotationType.yaml is valid and has all required fields
Verify Annotation.yaml is valid, all FK targets exist in the schema
Verify indexes are defined
Test 2: Migration


tests/migration/test_annotation_migration.py
Apply the migration to a test database
Verify both tables exist
Verify seed data is present (10 annotation types)
Apply rollback
Verify both tables are gone
Apply migration again (idempotency of apply-rollback-apply)
Test 3: Interval Overlap Logic


tests/integration/test_annotation_overlap.py
Set up: Create a MetaData entry and several annotations:

A: [Jan 10, Jan 20] — fully inside any Feb query range → NOT returned
B: [Jan 25, Feb 5] — overlaps start of [Feb 1, Feb 28] → returned
C: [Feb 10, Feb 15] — fully inside [Feb 1, Feb 28] → returned
D: [Feb 25, Mar 5] — overlaps end of [Feb 1, Feb 28] → returned
E: [Jan 1, Mar 31] — spans entire [Feb 1, Feb 28] → returned
F: StartTime=Feb 12, EndTime=NULL (point/ongoing) → returned
G: StartTime=Mar 15, EndTime=NULL → NOT returned
H: Same time range as C but different MetaDataID → NOT returned
Query [Feb 1, Feb 28] for the test MetaDataID.
Assert exactly {B, C, D, E, F} are returned.

Test 4: CRUD Operations


tests/integration/test_annotation_crud.py
Create an annotation → verify it gets an ID and CreatedAt
Read it back → verify all fields match
Update the title and end_time → verify ModifiedAt is set
Delete it → verify it's gone
Try to read deleted annotation → 404
Test 5: API Contract


tests/api/contract/test_annotation_endpoints.py
GET /api/v1/timeseries/{id}/annotations returns the documented schema
POST creates and returns the documented schema
PUT updates and returns the documented schema
DELETE returns 204
GET /api/v1/annotation-types returns all 10 types
Verify that adding a new optional field to the response doesn't break
the contract test (future-proofing)
Test 6: Edge Cases


tests/integration/test_annotation_edge_cases.py
Create annotation with end_time before start_time → 422
Create annotation for nonexistent MetaDataID → 404
Create annotation with invalid type name → 404
Create annotation with all optional fields NULL → succeeds
Create 100 overlapping annotations on same range → all returned
Create annotation with very long comment (10,000 chars) → succeeds
Documentation

Create docs/architecture/annotations.md with:

What annotations are and why they exist
The AnnotationType taxonomy (table of all 10 types with colors)
Interval overlap semantics (with diagram)
API endpoint summary with example requests/responses
How to add new annotation types (INSERT into AnnotationType)
Relationship to EquipmentEvents (optional link)
Future: threading (ParentAnnotationID), multi-series annotations
(junction table) — mentioned as possibilities, not implemented
Checklist Before Merging

 YAML files pass schema validation
 Migration applies cleanly to a database at the previous version
 Rollback script returns database to previous version
 All 10 seed data rows are inserted
 Overlap query uses IX_Annotation_MetaData_Time index (check
execution plan if possible)
 All 6 test files pass
 API endpoints match documented request/response shapes
 No existing tests are broken
 SchemaVersion is updated
 docs/architecture/annotations.md exists and is complete
 ER diagram is updated (if one exists in the repo)
 If EquipmentEvent table does not exist yet, EquipmentEventID
column exists WITHOUT FK constraint and has a TODO comment


---

## PR 2: Sensor Status

### Prompt for Claude Code

```markdown
# PR: Per-Channel Sensor Status

## Context

You are working in the open_datEAUbase repository. The schema is defined 
as YAML files in `schema_dictionary/tables/` and migrations are generated 
using the tooling in `tools/schema_migrate/`. Before starting, read:

1. `schema_dictionary/tables/MetaData.yaml` — understand the current 
   MetaData structure, especially any columns added by previous PRs
2. `schema_dictionary/tables/Value.yaml` — the scalar value table 
   (status values will be stored here)
3. `schema_dictionary/tables/Equipment.yaml` — equipment table
4. `schema_dictionary/tables/Variable.yaml` — variable table
5. `schema_dictionary/tables/Unit.yaml` — unit table
6. `schema_dictionary/version.yaml` — current schema version
7. `tools/schema_migrate/` — understand how migrations are generated
8. Any existing API code in `api/` — understand current endpoint patterns

Read all of these files before making any changes.

## What This PR Does

Adds per-channel sensor status tracking. In a multi-parameter sensor 
(e.g., an SC1000 controller with TSS, pH, and DO probes), each 
measurement channel can have an independent status (operational, fault, 
fouled, calibrating, etc.). Status is stored as a time series in 
dbo.Value using state-change encoding (only transitions are recorded). 
The link between a status time series and its measurement channel is 
a self-referential FK on MetaData.

This PR does NOT store status in a separate table. It reuses dbo.Value 
via a convention: status MetaData entries have Variable='Sensor Status' 
and point to their measurement MetaData via StatusOfMetaDataID.

## Design Principles

1. Status is per-channel (per MetaData entry), not per-equipment
2. Device-level status is also supported (per Equipment)
3. Status values go in dbo.Value — no new value table
4. State-change encoding: only write a row when status changes
5. A lookup table (SensorStatusCode) defines the meaning of each code
6. Two self-referential nullable FKs on MetaData: StatusOfMetaDataID 
   and StatusOfEquipmentID, with a CHECK that at most one is non-NULL

## Schema Changes

### Table 1: dbo.SensorStatusCode

Create `schema_dictionary/tables/SensorStatusCode.yaml`:

```yaml
_format_version: "1.0"
table:
  name: SensorStatusCode
  schema: dbo
  description: >
    Lookup table defining sensor status codes. Each code represents 
    a state a sensor channel or device can be in. IsOperational 
    indicates whether data collected in this state should be considered 
    trustworthy. Severity indicates the urgency (0=normal, 1=warning, 
    2=fault, 3=critical).
  columns:
    - name: StatusCodeID
      logical_type: integer
      nullable: false
      description: "Primary key, manually assigned. This is the value stored in dbo.Value."
    - name: StatusName
      logical_type: string
      max_length: 50
      nullable: false
      description: "Human-readable status name"
    - name: Description
      logical_type: string
      max_length: 200
      nullable: true
      description: "Detailed description of what this status means"
    - name: IsOperational
      logical_type: boolean
      nullable: false
      default: true
      description: >
        Whether data collected during this status should be considered 
        trustworthy. true = data is valid, false = data may be invalid.
    - name: Severity
      logical_type: integer
      nullable: false
      default: 0
      description: "0=normal, 1=warning, 2=fault, 3=critical"
  primary_key: [StatusCodeID]
  seed_data:
    - { StatusCodeID: 0,  StatusName: "Unknown",      Description: "Status not reported or not available",              IsOperational: false, Severity: 1 }
    - { StatusCodeID: 1,  StatusName: "Operational",   Description: "Sensor channel is functioning normally",            IsOperational: true,  Severity: 0 }
    - { StatusCodeID: 2,  StatusName: "Warning",       Description: "Sensor is operational but a warning condition exists", IsOperational: true,  Severity: 1 }
    - { StatusCodeID: 3,  StatusName: "Fault",         Description: "Sensor channel has faulted, data is unreliable",   IsOperational: false, Severity: 2 }
    - { StatusCodeID: 4,  StatusName: "Maintenance",   Description: "Sensor is undergoing maintenance",                 IsOperational: false, Severity: 1 }
    - { StatusCodeID: 5,  StatusName: "Calibrating",   Description: "Sensor channel is being calibrated",               IsOperational: false, Severity: 1 }
    - { StatusCodeID: 6,  StatusName: "Starting Up",   Description: "Sensor is in startup/warmup phase",                IsOperational: false, Severity: 1 }
    - { StatusCodeID: 7,  StatusName: "Shutting Down",  Description: "Sensor is shutting down",                          IsOperational: false, Severity: 1 }
    - { StatusCodeID: 8,  StatusName: "Offline",       Description: "Sensor is powered off or disconnected",            IsOperational: false, Severity: 0 }
    - { StatusCodeID: 9,  StatusName: "Degraded",      Description: "Sensor is operational but accuracy may be reduced", IsOperational: true,  Severity: 1 }
    - { StatusCodeID: 10, StatusName: "Fouled",        Description: "Sensor probe is fouled, readings likely biased",   IsOperational: true,  Severity: 2 }
Modification 1: dbo.MetaData — Add Status Link Columns

Modify schema_dictionary/tables/MetaData.yaml to add:

yaml

    - name: StatusOfMetaDataID
      logical_type: integer
      nullable: true
      description: >
        If this MetaData entry is a status time series, this points 
        to the measurement MetaData entry it describes. NULL for 
        measurement entries and non-status entries.
      foreign_key:
        table: MetaData
        column: MetaDataID
    - name: StatusOfEquipmentID
      logical_type: integer
      nullable: true
      description: >
        If this MetaData entry is a device-level status time series, 
        this points to the Equipment it describes. NULL for channel-
        level status and non-status entries.
      foreign_key:
        table: Equipment
        column: EquipmentID
Add a check constraint to the table definition:

yaml

  check_constraints:
    - name: CK_MetaData_StatusTarget
      expression: "NOT (StatusOfMetaDataID IS NOT NULL AND StatusOfEquipmentID IS NOT NULL)"
      description: >
        A status entry is about either a measurement channel OR a 
        device, never both. At most one of StatusOfMetaDataID and 
        StatusOfEquipmentID can be non-NULL.
Modification 2: dbo.Variable — Seed Data

Add two variable entries if they don't already exist:

sql

-- Only insert if not exists
IF NOT EXISTS (SELECT 1 FROM dbo.Variable WHERE Name = 'Sensor Status')
    INSERT INTO dbo.Variable (Name, Description) 
    VALUES ('Sensor Status', 
            'Per-channel operational status code. Values reference dbo.SensorStatusCode.');

IF NOT EXISTS (SELECT 1 FROM dbo.Variable WHERE Name = 'Device Status')
    INSERT INTO dbo.Variable (Name, Description) 
    VALUES ('Device Status', 
            'Overall equipment health status. Values reference dbo.SensorStatusCode.');
Modification 3: dbo.Unit — Seed Data

sql

IF NOT EXISTS (SELECT 1 FROM dbo.Unit WHERE Name = 'Status Code')
    INSERT INTO dbo.Unit (Name, Description) 
    VALUES ('Status Code', 'Dimensionless integer code referencing dbo.SensorStatusCode');
Migration Script

Generate the migration from the current schema version to the next.
The migration must:

CREATE TABLE dbo.SensorStatusCode with all columns and PK
INSERT all 11 seed data rows
ALTER TABLE dbo.MetaData ADD StatusOfMetaDataID INT NULL
ALTER TABLE dbo.MetaData ADD StatusOfEquipmentID INT NULL
ADD FK constraint FK_MetaData_StatusOfMD (StatusOfMetaDataID → MetaData.MetaDataID)
ADD FK constraint FK_MetaData_StatusOfEquip (StatusOfEquipmentID → Equipment.EquipmentID)
ADD CHECK constraint CK_MetaData_StatusTarget
INSERT 'Sensor Status' and 'Device Status' variables (IF NOT EXISTS)
INSERT 'Status Code' unit (IF NOT EXISTS)
UPDATE dbo.SchemaVersion
The rollback script must:

DROP CONSTRAINT CK_MetaData_StatusTarget
DROP CONSTRAINT FK_MetaData_StatusOfEquip
DROP CONSTRAINT FK_MetaData_StatusOfMD
ALTER TABLE dbo.MetaData DROP COLUMN StatusOfEquipmentID
ALTER TABLE dbo.MetaData DROP COLUMN StatusOfMetaDataID
DROP TABLE dbo.SensorStatusCode
Optionally DELETE the seeded Variable and Unit rows (only if no
data references them — add a safety check)
DELETE the SchemaVersion row
SQL Queries to Implement

Query 1: Get Current Status for a Measurement Channel

"What is the current status of the TSS channel?"

sql

-- Parameters: @MeasurementMetaDataID INT
SELECT TOP 1
    sc.StatusCodeID,
    sc.StatusName,
    sc.IsOperational,
    sc.Severity,
    v.tstamp AS StatusSince
FROM dbo.MetaData statusMD
JOIN dbo.Value v 
    ON v.MetaDataID = statusMD.MetaDataID
JOIN dbo.SensorStatusCode sc 
    ON sc.StatusCodeID = CAST(v.Value AS INT)
WHERE statusMD.StatusOfMetaDataID = @MeasurementMetaDataID
ORDER BY v.tstamp DESC;
Query 2: Get Status at a Specific Point in Time

"What was the TSS channel status on Feb 16 at noon?"

sql

-- Parameters: @MeasurementMetaDataID INT, @Timestamp DATETIME2(7)
SELECT TOP 1
    sc.StatusCodeID,
    sc.StatusName,
    sc.IsOperational,
    sc.Severity,
    v.tstamp AS StatusSince
FROM dbo.MetaData statusMD
JOIN dbo.Value v 
    ON v.MetaDataID = statusMD.MetaDataID
JOIN dbo.SensorStatusCode sc 
    ON sc.StatusCodeID = CAST(v.Value AS INT)
WHERE statusMD.StatusOfMetaDataID = @MeasurementMetaDataID
  AND v.tstamp <= @Timestamp
ORDER BY v.tstamp DESC;
Query 3: Get Status Transitions in a Time Range

"Show me all TSS channel status changes in February."

sql

-- Parameters: @MeasurementMetaDataID INT, @T1 DATETIME2(7), @T2 DATETIME2(7)
SELECT 
    v.tstamp AS TransitionTime,
    sc.StatusCodeID,
    sc.StatusName,
    sc.IsOperational,
    sc.Severity
FROM dbo.MetaData statusMD
JOIN dbo.Value v 
    ON v.MetaDataID = statusMD.MetaDataID
JOIN dbo.SensorStatusCode sc 
    ON sc.StatusCodeID = CAST(v.Value AS INT)
WHERE statusMD.StatusOfMetaDataID = @MeasurementMetaDataID
  AND v.tstamp BETWEEN @T1 AND @T2
ORDER BY v.tstamp;
Query 4: Get Status Band for Rendering (Intervals)

"Give me status intervals for the UI to render as colored bands."
This converts point transitions into intervals.

sql

-- Parameters: @MeasurementMetaDataID INT, @T1 DATETIME2(7), @T2 DATETIME2(7)
WITH StatusTransitions AS (
    -- Get the last status before the window starts
    SELECT TOP 1
        v.tstamp AS TransitionTime,
        CAST(v.Value AS INT) AS StatusCodeID
    FROM dbo.MetaData statusMD
    JOIN dbo.Value v ON v.MetaDataID = statusMD.MetaDataID
    WHERE statusMD.StatusOfMetaDataID = @MeasurementMetaDataID
      AND v.tstamp <= @T1
    ORDER BY v.tstamp DESC
    
    UNION ALL
    
    -- Get all transitions within the window
    SELECT 
        v.tstamp AS TransitionTime,
        CAST(v.Value AS INT) AS StatusCodeID
    FROM dbo.MetaData statusMD
    JOIN dbo.Value v ON v.MetaDataID = statusMD.MetaDataID
    WHERE statusMD.StatusOfMetaDataID = @MeasurementMetaDataID
      AND v.tstamp > @T1 AND v.tstamp <= @T2
),
StatusIntervals AS (
    SELECT 
        TransitionTime AS IntervalStart,
        LEAD(TransitionTime) OVER (ORDER BY TransitionTime) AS IntervalEnd,
        StatusCodeID
    FROM StatusTransitions
)
SELECT 
    -- Clamp interval start to query range
    CASE WHEN si.IntervalStart < @T1 THEN @T1 ELSE si.IntervalStart END AS IntervalStart,
    -- Clamp interval end to query range (NULL = extends to end of range)
    CASE WHEN si.IntervalEnd IS NULL THEN @T2 
         WHEN si.IntervalEnd > @T2 THEN @T2 
         ELSE si.IntervalEnd END AS IntervalEnd,
    sc.StatusCodeID,
    sc.StatusName,
    sc.IsOperational,
    sc.Severity,
    sc.Description AS StatusDescription
FROM StatusIntervals si
JOIN dbo.SensorStatusCode sc ON sc.StatusCodeID = si.StatusCodeID
WHERE si.IntervalEnd IS NULL OR si.IntervalEnd > @T1
ORDER BY si.IntervalStart;
Query 5: Get Measurement Values with Status

"Show TSS values with the sensor status at each point."

sql

-- Parameters: @MeasurementMetaDataID INT, @T1 DATETIME2(7), @T2 DATETIME2(7)
SELECT 
    v.tstamp,
    v.Value,
    v.QualityCode,
    sc.StatusCodeID,
    sc.StatusName,
    sc.IsOperational,
    sc.Severity
FROM dbo.Value v
OUTER APPLY (
    SELECT TOP 1 sv.Value AS StatusValue
    FROM dbo.MetaData statusMD
    JOIN dbo.Value sv ON sv.MetaDataID = statusMD.MetaDataID
    WHERE statusMD.StatusOfMetaDataID = @MeasurementMetaDataID
      AND sv.tstamp <= v.tstamp
    ORDER BY sv.tstamp DESC
) statusLookup
LEFT JOIN dbo.SensorStatusCode sc 
    ON sc.StatusCodeID = CAST(statusLookup.StatusValue AS INT)
WHERE v.MetaDataID = @MeasurementMetaDataID
  AND v.tstamp BETWEEN @T1 AND @T2
ORDER BY v.tstamp;
Query 6: Get Measurement Values (Operational Only)

"Show TSS values but only when the sensor was operational."

sql

-- Parameters: @MeasurementMetaDataID INT, @T1 DATETIME2(7), @T2 DATETIME2(7)
SELECT 
    v.tstamp,
    v.Value,
    v.QualityCode
FROM dbo.Value v
OUTER APPLY (
    SELECT TOP 1 sv.Value AS StatusValue
    FROM dbo.MetaData statusMD
    JOIN dbo.Value sv ON sv.MetaDataID = statusMD.MetaDataID
    WHERE statusMD.StatusOfMetaDataID = @MeasurementMetaDataID
      AND sv.tstamp <= v.tstamp
    ORDER BY sv.tstamp DESC
) statusLookup
LEFT JOIN dbo.SensorStatusCode sc 
    ON sc.StatusCodeID = CAST(statusLookup.StatusValue AS INT)
WHERE v.MetaDataID = @MeasurementMetaDataID
  AND v.tstamp BETWEEN @T1 AND @T2
  AND (sc.IsOperational = 1 OR sc.IsOperational IS NULL)
  -- NULL = no status data exists, assume operational (fail open)
ORDER BY v.tstamp;
Query 7: Get All Channel Statuses for an Equipment

"Is the SC1000 healthy? What's the status of each channel?"

sql

-- Parameters: @EquipmentID INT
SELECT 
    measMD.MetaDataID AS MeasurementMetaDataID,
    measVar.Name AS MeasurementVariable,
    sl.Name AS LocationName,
    sc.StatusCodeID,
    sc.StatusName,
    sc.IsOperational,
    sc.Severity,
    latestStatus.tstamp AS StatusSince
FROM dbo.MetaData statusMD
JOIN dbo.MetaData measMD 
    ON measMD.MetaDataID = statusMD.StatusOfMetaDataID
JOIN dbo.Variable measVar 
    ON measVar.VariableID = measMD.VariableID
JOIN dbo.SamplingLocation sl 
    ON sl.SamplingLocationID = measMD.SamplingLocationID
CROSS APPLY (
    SELECT TOP 1 v.tstamp, v.Value
    FROM dbo.Value v
    WHERE v.MetaDataID = statusMD.MetaDataID
    ORDER BY v.tstamp DESC
) latestStatus
JOIN dbo.SensorStatusCode sc 
    ON sc.StatusCodeID = CAST(latestStatus.Value AS INT)
WHERE measMD.EquipmentID = @EquipmentID
  AND statusMD.StatusOfMetaDataID IS NOT NULL
ORDER BY measVar.Name;
Query 8: Get Device-Level Status

sql

-- Parameters: @EquipmentID INT
SELECT TOP 1
    sc.StatusCodeID,
    sc.StatusName,
    sc.IsOperational,
    sc.Severity,
    v.tstamp AS StatusSince
FROM dbo.MetaData statusMD
JOIN dbo.Value v 
    ON v.MetaDataID = statusMD.MetaDataID
JOIN dbo.SensorStatusCode sc 
    ON sc.StatusCodeID = CAST(v.Value AS INT)
WHERE statusMD.StatusOfEquipmentID = @EquipmentID
ORDER BY v.tstamp DESC;
Views

Create two database views for convenience. Add these as YAML definitions
(create a schema_dictionary/views/ directory if it doesn't exist) AND
as SQL in the migration.

View 1: vw_ChannelStatus

sql

CREATE VIEW dbo.vw_ChannelStatus AS
SELECT 
    statusMD.MetaDataID AS StatusMetaDataID,
    statusMD.StatusOfMetaDataID AS MeasurementMetaDataID,
    measMD.EquipmentID,
    e.Name AS EquipmentName,
    measVar.Name AS MeasurementVariable,
    sl.Name AS LocationName,
    v.tstamp,
    CAST(v.Value AS INT) AS StatusCodeID,
    sc.StatusName,
    sc.IsOperational,
    sc.Severity
FROM dbo.Value v
JOIN dbo.MetaData statusMD 
    ON statusMD.MetaDataID = v.MetaDataID
JOIN dbo.MetaData measMD 
    ON measMD.MetaDataID = statusMD.StatusOfMetaDataID
JOIN dbo.Variable measVar 
    ON measVar.VariableID = measMD.VariableID
JOIN dbo.Equipment e 
    ON e.EquipmentID = measMD.EquipmentID
JOIN dbo.SamplingLocation sl 
    ON sl.SamplingLocationID = measMD.SamplingLocationID
LEFT JOIN dbo.SensorStatusCode sc 
    ON sc.StatusCodeID = CAST(v.Value AS INT)
WHERE statusMD.StatusOfMetaDataID IS NOT NULL;
View 2: vw_DeviceStatus

sql

CREATE VIEW dbo.vw_DeviceStatus AS
SELECT 
    statusMD.MetaDataID AS StatusMetaDataID,
    statusMD.StatusOfEquipmentID AS EquipmentID,
    e.Name AS EquipmentName,
    v.tstamp,
    CAST(v.Value AS INT) AS StatusCodeID,
    sc.StatusName,
    sc.IsOperational,
    sc.Severity
FROM dbo.Value v
JOIN dbo.MetaData statusMD 
    ON statusMD.MetaDataID = v.MetaDataID
JOIN dbo.Equipment e 
    ON e.EquipmentID = statusMD.StatusOfEquipmentID
LEFT JOIN dbo.SensorStatusCode sc 
    ON sc.StatusCodeID = CAST(v.Value AS INT)
WHERE statusMD.StatusOfEquipmentID IS NOT NULL;
API Endpoints

Endpoint 1: GET /api/v1/status-codes

Purpose: List all sensor status codes (for UI dropdowns and legends).

Response schema (200):

json

{
  "status_codes": [
    {
      "id": 0,
      "name": "Unknown",
      "description": "Status not reported or not available",
      "is_operational": false,
      "severity": 1
    },
    {
      "id": 1,
      "name": "Operational",
      "description": "Sensor channel is functioning normally",
      "is_operational": true,
      "severity": 0
    }
  ]
}
Implementation: Simple SELECT * FROM dbo.SensorStatusCode.

Endpoint 2: GET /api/v1/equipment/{equipment_id}/status

Purpose: Get the full health picture of a sensor: device-level
status plus all per-channel statuses.

Query parameters:

Parameter	Type	Required	Description
at	ISO 8601 datetime	No	Point in time to query. Default: now.
Response schema (200):

json

{
  "equipment_id": 5,
  "equipment_name": "SC1000_Controller",
  "queried_at": "2025-02-16T12:00:00Z",
  "device_status": {
    "status_code": 1,
    "status_name": "Operational",
    "is_operational": true,
    "severity": 0,
    "since": "2025-01-01T00:00:00Z"
  },
  "channel_statuses": [
    {
      "measurement_metadata_id": 42,
      "variable": "TSS",
      "location": "Primary Effluent",
      "status_code": 1,
      "status_name": "Operational",
      "is_operational": true,
      "severity": 0,
      "since": "2025-01-01T00:00:00Z"
    },
    {
      "measurement_metadata_id": 43,
      "variable": "pH",
      "location": "Primary Effluent",
      "status_code": 10,
      "status_name": "Fouled",
      "is_operational": true,
      "severity": 2,
      "since": "2025-02-15T00:00:00Z"
    },
    {
      "measurement_metadata_id": 44,
      "variable": "DO",
      "location": "Primary Effluent",
      "status_code": 1,
      "status_name": "Operational",
      "is_operational": true,
      "severity": 0,
      "since": "2025-01-01T00:00:00Z"
    }
  ],
  "overall_operational": true,
  "worst_severity": 2
}
Notes:

overall_operational: true only if device AND all channels are operational
worst_severity: max severity across device and all channels
If at parameter is provided, use Query 2 logic for each channel
and Query 8 for device level at that timestamp
If no status MetaData exists for this equipment, return device_status: null
and channel_statuses: []
Error responses:

404: Equipment not found
Implementation: Use Query 7 (channels) and Query 8 (device).
If at is provided, use Query 2 pattern for each.

Endpoint 3: GET /api/v1/equipment/{equipment_id}/status/history

Purpose: Get status transitions over a time range for the whole sensor.

Query parameters:

Parameter	Type	Required	Description
from	ISO 8601 datetime	Yes	Start of range
to	ISO 8601 datetime	Yes	End of range
channel	string	No	Filter to a specific variable name (e.g., "TSS")
Response schema (200):

json

{
  "equipment_id": 5,
  "equipment_name": "SC1000_Controller",
  "query_range": {
    "from": "2025-02-01T00:00:00Z",
    "to": "2025-02-28T23:59:59Z"
  },
  "device_transitions": [
    {
      "timestamp": "2025-01-01T00:00:00Z",
      "status_code": 1,
      "status_name": "Operational",
      "is_operational": true
    }
  ],
  "channel_transitions": {
    "TSS": {
      "measurement_metadata_id": 42,
      "transitions": [
        {
          "timestamp": "2025-01-01T00:00:00Z",
          "status_code": 1,
          "status_name": "Operational",
          "is_operational": true
        }
      ]
    },
    "pH": {
      "measurement_metadata_id": 43,
      "transitions": [
        {
          "timestamp": "2025-01-01T00:00:00Z",
          "status_code": 1,
          "status_name": "Operational",
          "is_operational": true
        },
        {
          "timestamp": "2025-02-15T00:00:00Z",
          "status_code": 10,
          "status_name": "Fouled",
          "is_operational": true
        },
        {
          "timestamp": "2025-02-20T00:00:00Z",
          "status_code": 1,
          "status_name": "Operational",
          "is_operational": true
        }
      ]
    }
  }
}
Implementation: Use Query 3 for each channel. Include the last
transition before the range start (for initial state).

Endpoint 4: GET /api/v1/timeseries/{metadata_id}/status

Purpose: Get the status band for a specific measurement channel
over a time range. Returns intervals, not point transitions.

Query parameters:

Parameter	Type	Required	Description
from	ISO 8601 datetime	Yes	Start of range
to	ISO 8601 datetime	Yes	End of range
Response schema (200):

json

{
  "metadata_id": 43,
  "variable": "pH",
  "equipment_name": "SC1000_Controller",
  "query_range": {
    "from": "2025-02-01T00:00:00Z",
    "to": "2025-02-28T23:59:59Z"
  },
  "status_intervals": [
    {
      "from": "2025-02-01T00:00:00Z",
      "to": "2025-02-15T00:00:00Z",
      "status_code": 1,
      "status_name": "Operational",
      "is_operational": true,
      "severity": 0
    },
    {
      "from": "2025-02-15T00:00:00Z",
      "to": "2025-02-20T00:00:00Z",
      "status_code": 10,
      "status_name": "Fouled",
      "is_operational": true,
      "severity": 2
    },
    {
      "from": "2025-02-20T00:00:00Z",
      "to": "2025-02-28T23:59:59Z",
      "status_code": 1,
      "status_name": "Operational",
      "is_operational": true,
      "severity": 0
    }
  ],
  "has_status_data": true
}
Notes:

If no status MetaData exists for this measurement, return
has_status_data: false and status_intervals: []
Intervals are clamped to the query range
Implementation: Use Query 4 (status band with LEAD window function).

Endpoint 5: Extend GET /api/v1/timeseries/{metadata_id}

Purpose: Add optional status inclusion to the existing timeseries
endpoint.

New query parameters (additive, non-breaking):

Parameter	Type	Required	Default	Description
include_status	bool	No	false	Include status band in response
operational_only	bool	No	false	Filter to values where sensor was operational
Extended response (only when include_status=true — additional fields):

json

{
  "metadata_id": 43,
  "location": "Primary Effluent",
  "variable": "pH",
  "unit": "pH units",
  "data": [
    {"timestamp": "2025-02-14T12:00:00Z", "value": 7.2, "quality": 1},
    {"timestamp": "2025-02-15T12:00:00Z", "value": 7.8, "quality": 1},
    {"timestamp": "2025-02-16T12:00:00Z", "value": 8.1, "quality": 1}
  ],
  "status_band": [
    {
      "from": "2025-02-01T00:00:00Z",
      "to": "2025-02-15T00:00:00Z",
      "status_name": "Operational",
      "is_operational": true
    },
    {
      "from": "2025-02-15T00:00:00Z",
      "to": "2025-02-20T00:00:00Z",
      "status_name": "Fouled",
      "is_operational": true
    }
  ],
  "has_status_data": true
}
When operational_only=true:

Use Query 6 instead of the normal value query
Values during non-operational periods are excluded from data
If include_status is also true, the status_band still shows all
intervals (so the UI can show what was filtered out)
CRITICAL: This must not break existing API contract tests.

The status_band and has_status_data fields are new optional
fields with defaults
When include_status is not provided, these fields are omitted
from the response (or set to null/empty)
Existing contract tests that don't use these parameters must pass
Implementation:

Modify the existing timeseries endpoint handler
Modify the existing timeseries service to optionally call status queries
Modify the existing timeseries Pydantic response model to add
optional fields with defaults
API Implementation Structure

Create or modify these files:


api/v1/
  schemas/
    sensor_status.py          # New: Pydantic models for status
    timeseries.py             # Modified: add status_band fields
  endpoints/
    sensor_status.py          # New: Endpoints 1-4
    timeseries.py             # Modified: Endpoint 5 (add params)
  services/
    sensor_status_service.py  # New: status business logic
    timeseries_service.py     # Modified: add status integration
  repositories/
    sensor_status_repository.py  # New: Queries 1-8
In sensor_status.py (schemas), define:

python

from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class StatusCodeResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    is_operational: bool
    severity: int

class ChannelStatus(BaseModel):
    measurement_metadata_id: int
    variable: str
    location: str
    status_code: int
    status_name: str
    is_operational: bool
    severity: int
    since: datetime

class DeviceStatus(BaseModel):
    status_code: int
    status_name: str
    is_operational: bool
    severity: int
    since: datetime

class EquipmentStatusResponse(BaseModel):
    equipment_id: int
    equipment_name: str
    queried_at: datetime
    device_status: Optional[DeviceStatus] = None
    channel_statuses: list[ChannelStatus]
    overall_operational: bool
    worst_severity: int

class StatusTransition(BaseModel):
    timestamp: datetime
    status_code: int
    status_name: str
    is_operational: bool

class StatusInterval(BaseModel):
    from_time: datetime  # 'from' is reserved in Python, use from_time
    to_time: datetime
    status_code: int
    status_name: str
    is_operational: bool
    severity: int

    class Config:
        # Serialize from_time/to_time as 'from'/'to' in JSON
        json_schema_extra = {
            "properties": {
                "from": {"type": "string", "format": "date-time"},
                "to": {"type": "string", "format": "date-time"}
            }
        }

class TimeSeriesStatusBand(BaseModel):
    status_intervals: list[StatusInterval]
    has_status_data: bool
Tests

Test 1: Schema Validation


tests/schema/test_sensor_status_yaml.py
SensorStatusCode.yaml is valid, has all columns and seed data
MetaData.yaml has StatusOfMetaDataID and StatusOfEquipmentID columns
Check constraint CK_MetaData_StatusTarget is defined
Self-referential FK on MetaData is valid
Test 2: Migration


tests/migration/test_sensor_status_migration.py
Apply migration, verify SensorStatusCode table exists with 11 rows
Verify MetaData has new columns
Verify CHECK constraint works: inserting a MetaData row with BOTH
StatusOfMetaDataID and StatusOfEquipmentID non-NULL fails
Verify inserting with only one non-NULL succeeds
Verify Variable and Unit seed rows exist
Apply rollback, verify columns and table are gone
Apply again (idempotency)
Test 3: Status Convention Setup


tests/integration/test_sensor_status_setup.py
Create an Equipment (SC1000)
Create three measurement MetaData entries (TSS, pH, DO)
Create three channel status MetaData entries pointing to each
measurement via StatusOfMetaDataID
Create one device status MetaData entry via StatusOfEquipmentID
Verify all links are correct
Verify that querying MetaData WHERE StatusOfMetaDataID = {TSS MetaDataID}
returns exactly one row
Test 4: State-Change Encoding and Queries


tests/integration/test_sensor_status_queries.py
Set up: SC1000 with TSS, pH, DO channels

Insert status transitions:

TSS channel: Operational at Jan 1 (no changes)
pH channel: Operational at Jan 1, Fouled at Feb 15, Operational at Feb 20
DO channel: Operational at Jan 1, Calibrating at Mar 1 10:00,
Operational at Mar 1 10:30
Device: Operational at Jan 1 (no changes)
Test Query 1 (current status for each channel):

TSS → Operational
pH → Operational (most recent is Feb 20 = Operational)
DO → Operational
Test Query 2 (status at point in time):

pH at Feb 16 → Fouled
pH at Feb 21 → Operational
pH at Jan 15 → Operational
Test Query 3 (transitions in range):

pH in Feb → [Fouled at Feb 15, Operational at Feb 20]
TSS in Feb → [] (no transitions in range)
Test Query 4 (status band):

pH in Feb → 3 intervals: [Feb 1→Feb 15 Operational,
Feb 15→Feb 20 Fouled, Feb 20→Feb 28 Operational]
Test Query 5 (values with status):

Insert pH values every day in February
Query with status → values Feb 15-19 have status=Fouled,
all others have status=Operational
Test Query 6 (operational only):

Same pH values → all returned (Fouled has IsOperational=true)
Change Fouled to IsOperational=false in seed data for this test
(or use Fault instead) → Feb 15-19 values excluded
Test Query 7 (all channels for equipment):

Returns TSS=Operational, pH=Operational, DO=Operational
Test Query 8 (device status):

Returns Operational
Test 5: Multi-Parameter Independence


tests/integration/test_sensor_status_isolation.py
This is the critical test that proves channel statuses don't cross-
contaminate:

Set up SC1000 with TSS, pH, DO and their status channels
Set pH to Fouled, keep TSS and DO operational
Query TSS values with status → all Operational
Query pH values with status → shows Fouled period
Query DO values with status → all Operational
VERIFY: pH's Fouled status does NOT appear in TSS or DO queries
Test 6: Missing Status Data


tests/integration/test_sensor_status_missing.py
Create a measurement MetaData with NO companion status MetaData
Query values with include_status=true → values returned,
has_status_data=false, status_band=[]
Query with operational_only=true → all values returned
(fail-open: no status = assume operational)
Test 7: API Contract


tests/api/contract/test_sensor_status_endpoints.py
GET /api/v1/status-codes returns documented schema
GET /api/v1/equipment/{id}/status returns documented schema
GET /api/v1/equipment/{id}/status/history returns documented schema
GET /api/v1/timeseries/{id}/status returns documented schema
GET /api/v1/timeseries/{id} WITHOUT include_status → response
matches the pre-existing contract (NO new fields)
GET /api/v1/timeseries/{id}?include_status=true → response has
status_band field
GET /api/v1/timeseries/{id}?operational_only=true → response has
fewer data points when non-operational periods exist
Test 8: CHECK Constraint


tests/integration/test_sensor_status_constraints.py
INSERT MetaData with StatusOfMetaDataID=42, StatusOfEquipmentID=NULL → OK
INSERT MetaData with StatusOfMetaDataID=NULL, StatusOfEquipmentID=5 → OK
INSERT MetaData with StatusOfMetaDataID=42, StatusOfEquipmentID=5 → FAILS
INSERT MetaData with StatusOfMetaDataID=NULL, StatusOfEquipmentID=NULL → OK
(this is a normal measurement entry)
Documentation

Create docs/architecture/sensor_status.md with:

Concept: Per-channel vs device-level status
Why status is per-channel: Multi-parameter sensor example,
independent failure modes
Storage convention: Status as a Variable in dbo.Value,
state-change encoding, StatusOfMetaDataID link
SensorStatusCode reference table: All 11 codes with meanings,
IsOperational, Severity
How to set up status for a new sensor:
Step-by-step: create measurement MetaData, create companion
status MetaData with StatusOfMetaDataID pointing to it
Set up IngestionRoute for status (if ingestion routing exists)
How to query status: Examples of each query pattern
API endpoint summary with example requests/responses
Integration with annotations: Status = machine-reported state,
annotations = human-authored commentary. They're complementary.
A Fault annotation might be created by a human to explain a
machine-reported Fault status.
State-change encoding: Why we store transitions not heartbeats,
how to interpret it, how ingestion scripts should deduplicate
Checklist Before Merging

 YAML files pass schema validation
 Migration applies cleanly to a database at the previous version
 Rollback script returns database to previous version
 All 11 seed data rows are in SensorStatusCode
 'Sensor Status' and 'Device Status' Variable rows exist
 'Status Code' Unit row exists
 CHECK constraint CK_MetaData_StatusTarget is enforced
 Self-referential FK on MetaData works
 Views vw_ChannelStatus and vw_DeviceStatus return correct data
 All 8 test files pass
 Channel status isolation test passes (Task 5 — most critical)
 Missing status data test passes (fail-open behavior)
 Existing timeseries API contract tests still pass WITHOUT
include_status parameter
 API endpoints match documented request/response shapes
 No existing tests are broken by this PR
 SchemaVersion is updated
 docs/architecture/sensor_status.md exists and is complete
 ER diagram is updated (if one exists in the repo)

