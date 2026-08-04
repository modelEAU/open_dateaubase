# Database Tables

This documentation is auto-generated from dictionary.json.


## Tables


<span id="AnalysisSeries"></span>

### AnalysisSeries

Stable stream identity for lab measurements — the lab subtype of Stream (table-per-type inheritance): it shares Stream_ID as its own primary key, which is simultaneously a foreign key to Stream.Stream_ID. Each AnalysisSeries owns exactly one Stream row carrying this same identifier. One AnalysisSeries row represents the conceptual stream of "Parameter X measured at SamplingPoint Y producing ValueKind W in Unit U" (e.g. "TSS at Effluent in mg/L"). All LabAnalyses measuring the same parameter at the same location with the same value kind, produced by the same laboratory, share one Stream_ID, giving lab data a queryable time-series identity. Laboratory is part of that identity: results from two laboratories are not interchangeable, so they form two series.
Unlike Channel — which intentionally excludes sampling location from its identity because location is inferred at query time via EquipmentLocationHistory — AnalysisSeries includes SamplingPoint_ID as explicit identity, because lab samples always have a known origin and "TSS at Influent" must be a different series from "TSS at Effluent".
Review status is a point-level attribute on LabAnalysis (added in a later slice), not part of series identity: all measurements of the same parameter at the same location share one AnalysisSeries regardless of review state.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Stream_ID | INT **(PK)** | - | ✓ | <span id="Stream_ID"></span>Shared primary key (table-per-type inheritance): both the primary key of AnalysisSeries and a foreign key to Stream.Stream_ID. Every AnalysisSeries owns exactly one Stream row carrying this same identifier.
 | FK → [Stream.Stream_ID](#Stream) |
| Name | NVARCHAR(200) | - | ✓ | <span id="Name"></span>Human-readable label (e.g. 'TSS Gravimetric at Effluent') | - |
| Parameter_ID | INT | - | ✓ | <span id="Parameter_ID"></span>Measured analyte (e.g. TSS concentration, COD concentration) | FK → [Parameter.Parameter_ID](#Parameter) |
| SamplingPoint_ID | INT | - | ✓ | <span id="SamplingPoint_ID"></span>Sampling point where the samples for this series originate | FK → [SamplingPoint.SamplingPoint_ID](#SamplingPoint) |
| ValueKind_ID | INT | - | ✓ | <span id="ValueKind_ID"></span>Shape of stored values (1=Scalar, 2=Vector, 3=Matrix, 4=Image) | FK → [ValueKind.ValueKind_ID](#ValueKind)<br>Default: `1` |
| Unit_ID | INT | - | ✓ | <span id="Unit_ID"></span>Unit of measurement for values in this series (e.g. mg/L). Treated as immutable for the lifetime of the series — a unit change requires a new AnalysisSeries row. Excluded from the uniqueness constraint because unit choice is a property of the series rather than part of its identity; two series with the same parameter / location / value kind cannot legitimately differ only by unit.
 | FK → [Unit.Unit_ID](#Unit) |
| Laboratory_ID | INT | - |  | <span id="Laboratory_ID"></span>Laboratory that produces this series. Part of series identity: two laboratories measuring the same parameter at the same sampling point are two separate series, because their results are not interchangeable. NULL means the producing laboratory is unrecorded.
 | FK → [Laboratory.Laboratory_ID](#Laboratory) |
| Campaign_ID | INT | - |  | <span id="Campaign_ID"></span>Campaign this series belongs to; scopes the series to a specific monitoring campaign | FK → [Campaign.Campaign_ID](#Campaign) |
| Description | NVARCHAR(MAX) | - |  | <span id="Description"></span>Free-text notes about this analysis series | - |

<span id="AnalysisSeriesAxis"></span>

### AnalysisSeriesAxis

Junction table linking an AnalysisSeries to its binning axis or axes (analogous to ChannelAxis for sensor channels). AxisRole=0 is the single axis for a Vector series, or the row axis for a Matrix series; AxisRole=1 is the column axis for a Matrix series.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| AnalysisSeries_ID | INT **(PK)** | - | ✓ | <span id="AnalysisSeries_ID"></span>References the lab analysis series | FK → [AnalysisSeries.Stream_ID](#AnalysisSeries) |
| AxisRole | INT **(PK)** | - | ✓ | <span id="AxisRole"></span>Dimension role: 0 = primary/row axis, 1 = secondary/column axis (Matrix only) | - |
| ValueBinningAxis_ID | INT | - | ✓ | <span id="ValueBinningAxis_ID"></span>References the binning axis for this role | FK → [ValueBinningAxis.ValueBinningAxis_ID](#ValueBinningAxis) |

<span id="Annotation"></span>

### Annotation

Human-authored annotations on time series data. Each annotation anchors to a single measurement Stream via a non-NULL Stream_ID FK — uniformly covering a sensor Channel or a lab AnalysisSeries (both are Stream subtypes) — over a time range. Multiple annotations can overlap on the same range. EndTime=NULL means either a point annotation or an ongoing situation.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Annotation_ID | INT **(PK)** | - | ✓ | <span id="Annotation_ID"></span>Primary key, auto-incremented | - |
| Stream_ID | INT | - | ✓ | <span id="Stream_ID"></span>The measurement stream this annotation attaches to. A single anchor for both sensor and lab data: it references any Stream (a sensor Channel or a lab AnalysisSeries) with full parity, replacing the former Channel_ID / AnalysisSeries_ID XOR arc.
 | FK → [Stream.Stream_ID](#Stream) |
| AnnotationKind_ID | INT | - | ✓ | <span id="AnnotationKind_ID"></span>What kind of annotation this is | FK → [AnnotationKind.AnnotationKind_ID](#AnnotationKind) |
| StartTime | DATETIME2(7) | - | ✓ | <span id="StartTime"></span>Start of the annotated time range | - |
| EndTime | DATETIME2(7) | - |  | <span id="EndTime"></span>End of the annotated range. NULL = point annotation or ongoing | - |
| AuthorPerson_ID | INT | - |  | <span id="AuthorPerson_ID"></span>Person who created this annotation | FK → [Person.Person_ID](#Person) |
| Campaign_ID | INT | - |  | <span id="Campaign_ID"></span>Campaign this annotation is associated with, if any | FK → [Campaign.Campaign_ID](#Campaign) |
| Event_ID | INT | - |  | <span id="Event_ID"></span>Event that caused this annotation, if any (causal link: Event=cause, Annotation=effect) | FK → [Event.Event_ID](#Event) |
| Title | NVARCHAR(200) | - |  | <span id="Title"></span>Short title for the annotation | - |
| Comment | NVARCHAR(MAX) | - |  | <span id="Comment"></span>Detailed free-text comment | - |
| CreatedDateTime | DATETIME2(7) | - | ✓ | <span id="CreatedDateTime"></span>When this annotation was created | Default: `CURRENT_TIMESTAMP` |
| ModifiedDateTime | DATETIME2(7) | - |  | <span id="ModifiedDateTime"></span>When this annotation was last modified | - |
| Observation_ID | INT | - |  | <span id="Observation_ID"></span>Optional link to a specific Observation for point-level annotations (e.g., 'wrong focal length on this image'). Valid for either anchor: for a sensor annotation it pins one Channel Observation; for a lab annotation it pins one Replicate (the Observation backing a single AnalysisSeries reading). When NULL, the annotation applies to the time range [StartTime, EndTime] on the anchored stream. When set, StartTime should match Observation.Timestamp.
 | FK → [Observation.Observation_ID](#Observation) |

<span id="AnnotationKind"></span>

### AnnotationKind

Controlled vocabulary of verdicts that can be passed on time series data. An annotation says what is wrong with the data, never why — the why lives on the Event it optionally cites via Event_ID (see ADR-0007). Cause-named kinds belong in EventKind. Each kind has a display color for UI rendering.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| AnnotationKind_ID | INT **(PK)** | - | ✓ | <span id="AnnotationKind_ID"></span>Primary key, manually assigned | - |
| Name | NVARCHAR(100) | - | ✓ | <span id="Name"></span>Human-readable name of the annotation kind | - |
| Description | NVARCHAR(500) | - |  | <span id="Description"></span>Explanation of when to use this annotation kind | - |
| Color | NVARCHAR(7) | - |  | <span id="Color"></span>Hex color code for UI rendering, e.g. '#FF6B6B' | - |

<span id="AuditLog"></span>

### AuditLog

Immutable log of user-initiated actions on API resources.


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| AuditLog_ID | BIGINT **(PK)** | - | ✓ | <span id="AuditLog_ID"></span>Surrogate primary key | - |
| UserAccount_ID | INT | - |  | <span id="UserAccount_ID"></span>User who performed the action (NULL for unauthenticated events) | FK → [UserAccount.UserAccount_ID](#UserAccount) |
| Action | NVARCHAR(50) | - | ✓ | <span id="Action"></span>Action verb: CREATE | UPDATE | DELETE | LOGIN | SIGNUP | - |
| ResourceType | NVARCHAR(100) | - | ✓ | <span id="ResourceType"></span>Type of resource affected (e.g. UserAccount, Site, Campaign) | - |
| ResourceID | NVARCHAR(255) | - |  | <span id="ResourceID"></span>Primary key of the affected row, serialised as a string | - |
| Details | NVARCHAR(MAX) | - |  | <span id="Details"></span>JSON snapshot or diff of the affected record | - |
| Timestamp | DATETIME2(7) | - | ✓ | <span id="Timestamp"></span>UTC timestamp when the action occurred | Default: `SYSUTCDATETIME()` |

<span id="BinKind"></span>

### BinKind

Controlled vocabulary defining how bins on a ValueBinningAxis are specified. Each axis declares exactly one kind, and all bins on that axis must conform to it.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| BinKind_ID | INT **(PK)** | - | ✓ | <span id="BinKind_ID"></span>Surrogate primary key, manually assigned | - |
| Name | NVARCHAR(30) | - | ✓ | <span id="Name"></span>Kind name (e.g. 'interval', 'nominal', 'interval_with_nominal') | - |
| Description | NVARCHAR(300) | - |  | <span id="Description"></span>Explanation of what this bin kind means | - |

<span id="Campaign"></span>

### Campaign

A named collection of measurement activities, classified by type (Experiment, Operations, Commissioning). Campaigns are multi-site: their sites are derived from sampling-location membership (CampaignSamplingLocation to SamplingPoint.Site), not stored. Supersedes Project (defunct table) for all organisational grouping.


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Campaign_ID | INT **(PK)** | - | ✓ | <span id="Campaign_ID"></span>Surrogate primary key. | - |
| CampaignKind_ID | INT | - | ✓ | <span id="CampaignKind_ID"></span>Kind of campaign (See CampaignKind table. E.g., Experiment, Monitoring, Facility Commissioning). | FK → [CampaignKind.CampaignKind_ID](#CampaignKind) |
| Name | NVARCHAR(200) | - | ✓ | <span id="Name"></span>Human-readable name for the campaign. | - |
| Description | NVARCHAR(2000) | - |  | <span id="Description"></span>Detailed description of the campaign objectives and scope. | - |
| CampaignStartDateTime | DATETIME2(7) | - |  | <span id="CampaignStartDateTime"></span>Date and time the campaign began (UTC). | - |
| CampaignEndDateTime | DATETIME2(7) | - |  | <span id="CampaignEndDateTime"></span>Date and time the campaign ended (UTC); NULL if the campaign is ongoing. | - |
| ResponsiblePerson_ID | INT | - |  | <span id="ResponsiblePerson_ID"></span>Person responsible for running the campaign | FK → [Person.Person_ID](#Person) |

<span id="CampaignEquipment"></span>

### CampaignEquipment

Junction table: equipment deployed during a campaign.


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Campaign_ID | INT **(PK)** | - | ✓ | <span id="Campaign_ID"></span>Campaign using this equipment | FK → [Campaign.Campaign_ID](#Campaign) |
| Equipment_ID | INT **(PK)** | - | ✓ | <span id="Equipment_ID"></span>Equipment deployed during the campaign | FK → [Equipment.Equipment_ID](#Equipment) |
| Role | NVARCHAR(100) | - |  | <span id="Role"></span>Role of this equipment in the campaign (e.g., 'Primary sensor', 'Auto-sampler') | - |

<span id="CampaignKind"></span>

### CampaignKind

Controlled vocabulary classifying the nature of a Campaign (Experiment, Operations, Commissioning)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| CampaignKind_ID | INT **(PK)** | - | ✓ | <span id="CampaignKind_ID"></span>Surrogate primary key | - |
| Name | NVARCHAR(100) | - | ✓ | <span id="Name"></span>Name of the campaign kind | - |
| Description | NVARCHAR(300) | - |  | <span id="Description"></span>Explanation of this campaign kind | - |

<span id="CampaignSamplingLocation"></span>

### CampaignSamplingLocation

Junction table: sampling locations actively monitored during a campaign.


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Campaign_ID | INT **(PK)** | - | ✓ | <span id="Campaign_ID"></span>Campaign using this sampling location | FK → [Campaign.Campaign_ID](#Campaign) |
| SamplingPoint_ID | INT **(PK)** | - | ✓ | <span id="SamplingPoint_ID"></span>Sampling location used by the campaign | FK → [SamplingPoint.SamplingPoint_ID](#SamplingPoint) |
| Role | NVARCHAR(100) | - |  | <span id="Role"></span>Role of this location in the campaign (e.g., 'Inlet', 'Reference') | - |

<span id="Channel"></span>

### Channel

Invariant descriptor for a measurement stream (sensor channel). Channel is the sensor subtype of Stream (table-per-type inheritance): it shares Stream_ID as its own primary key, which is simultaneously a foreign key to Stream.Stream_ID. Each row is identified by a unique (SignalInterface, TagName, Parameter, DataProvenance, ProducedByStep) combination. A Channel is created once and never changes — equipment swaps and sensor relocations are tracked on the physical Equipment via EquipmentWiringHistory and EquipmentLocationHistory, leaving Stream_ID stable. The specific SignalInterfacePort carrying the stream is optional at ingest time and is recorded over time in ChannelPortHistory (the active row is the current port). Queries that need the current port resolve it through the vw_ChannelResolved view, so there is a single source of truth and no denormalised column to drift. Lab sample results are stored in LabAnalysis + LabValue (not in Channel).
Raw/ingested channels have SignalInterface_ID NOT NULL and ProducedByStep_ID NULL. Derived/processed channels have SignalInterface_ID NULL and ProducedByStep_ID pointing to the ProcessingStep that produced them. Accumulated processing operations applied to a Channel live in the ChannelTrait junction (to be added in a later slice).



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Stream_ID | INT **(PK)** | - | ✓ | <span id="Stream_ID"></span>Shared primary key (table-per-type inheritance): both the primary key of Channel and a foreign key to Stream.Stream_ID. Every Channel owns exactly one Stream row carrying this same identifier.
 | FK → [Stream.Stream_ID](#Stream) |
| SignalInterface_ID | INT | - |  | <span id="SignalInterface_ID"></span>The SignalInterface (PLC, SCADA, basestation, ...) that publishes this tag. The anchor for ingest: observations are routed by (SignalInterface_ID, TagName). NULL for derived/processed channels that have no physical source interface.
 | FK → [SignalInterface.SignalInterface_ID](#SignalInterface) |
| TagName | NVARCHAR(200) | - | ✓ | <span id="TagName"></span>Tag string as published by the SignalInterface (case-preserved; lookups are case-insensitive trimmed). For direct-connect interfaces a synthetic tag such as "{equipment_identifier}/{parameter_name}" is auto-generated.
 | - |
| ParentChannel_ID | INT | - |  | <span id="ParentChannel_ID"></span>For sub-signal Channels (Status, Alarm, Uncertainty), points to the parent value Channel's Stream_ID. NULL for primary value channels and unlinked channels. Self-FK.
 | FK → [Channel.Stream_ID](#Channel) |
| ChannelKind_ID | INT | - | ✓ | <span id="ChannelKind_ID"></span>Kind of information this Channel carries (1=Value, 2=Status, 3=Alarm, 4=Uncertainty).
 | FK → [ChannelKind.ChannelKind_ID](#ChannelKind)<br>Default: `1` |
| Parameter_ID | INT | - |  | <span id="Parameter_ID"></span>Measured analyte or parameter (e.g. TSS concetration, pH) | FK → [Parameter.Parameter_ID](#Parameter) |
| DataProvenanceKind_ID | INT | - |  | <span id="DataProvenanceKind_ID"></span>How this data was produced (Sensor=1, Laboratory=2, Manual Entry=3, Model Output=4, External Source=5, Forecast=6)
 | FK → [DataProvenanceKind.DataProvenanceKind_ID](#DataProvenanceKind) |
| ProducedByStep_ID | INT | - |  | <span id="ProducedByStep_ID"></span>The ProcessingStep that produced this channel. NULL for raw/ingested channels. Distinguishes independently-processed variants of the same physical signal stream: two users running the same algorithm on the same raw channel each create a separate ProcessingStep row and therefore separate Channel rows.
 | FK → [ProcessingStep.ProcessingStep_ID](#ProcessingStep) |
| ValueKind_ID | INT | - | ✓ | <span id="ValueKind_ID"></span>Shape of stored values (1=Scalar, 2=Vector, 3=Matrix, 4=Image) | FK → [ValueKind.ValueKind_ID](#ValueKind)<br>Default: `1` |
| Unit_ID | INT | - |  | <span id="Unit_ID"></span>Unit of measurement for values stored in this channel (e.g. mg/L, NTU). Set at channel creation via the ingestion pipeline and treated as immutable thereafter — a unit change requires a new Channel row.
 | FK → [Unit.Unit_ID](#Unit) |

<span id="ChannelAxis"></span>

### ChannelAxis

Junction table linking a Channel measurement series to its binning axis or axes. AxisRole=0 is the single axis for a Vector, or the row axis for a Matrix; AxisRole=1 is the column axis for a Matrix.


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Channel_ID | INT **(PK)** | - | ✓ | <span id="Channel_ID"></span>References the measurement channel | FK → [Channel.Stream_ID](#Channel) |
| AxisRole | INT **(PK)** | - | ✓ | <span id="AxisRole"></span>Dimension role: 0 = primary/row axis, 1 = secondary/column axis (Matrix only) | - |
| ValueBinningAxis_ID | INT | - | ✓ | <span id="ValueBinningAxis_ID"></span>References the binning axis for this role | FK → [ValueBinningAxis.ValueBinningAxis_ID](#ValueBinningAxis) |

<span id="ChannelKind"></span>

### ChannelKind

Controlled vocabulary describing what kind of information a Channel carries (Value / Status / Alarm / Uncertainty). Sub-signals (Status, Alarm, Uncertainty) attach to their parent value Channel via Channel.ParentChannel_ID.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| ChannelKind_ID | INT **(PK)** | - | ✓ | <span id="ChannelKind_ID"></span>Surrogate primary key, manually assigned | - |
| Name | NVARCHAR(50) | - | ✓ | <span id="Name"></span>Short name for this channel kind | - |
| Description | NVARCHAR(200) | - |  | <span id="Description"></span>Explanation of what this channel kind means | - |

<span id="ChannelPortHistory"></span>

### ChannelPortHistory

Temporal record of which SignalInterfacePort (if any) a given Channel is gated through over time. Needed to model multiplexers like TresCON, where a single physical port on the parent interface emits a sequence of distinct streams distinguished by a gating discipline (round-robin, tag mapping, etc.). Also used for backfill: when a Channel is created with no port known, a row with NULL SignalInterfacePort_ID opens; when the wire is later traced, that row is closed and a new row with the port is opened. At most one row per Channel may have ValidTo IS NULL.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| ChannelPortHistory_ID | INT **(PK)** | - | ✓ | <span id="ChannelPortHistory_ID"></span>Surrogate primary key | - |
| Channel_ID | INT | - | ✓ | <span id="Channel_ID"></span>The Channel whose port gating is recorded here | FK → [Channel.Stream_ID](#Channel) |
| SignalInterfacePort_ID | INT | - |  | <span id="SignalInterfacePort_ID"></span>Port the Channel is gated through (NULL when untraced) | FK → [SignalInterfacePort.SignalInterfacePort_ID](#SignalInterfacePort) |
| ValidFrom | DATETIME2(7) | - | ✓ | <span id="ValidFrom"></span>UTC datetime when this port gating started | - |
| ValidTo | DATETIME2(7) | - |  | <span id="ValidTo"></span>UTC datetime when this port gating ended. NULL = currently gated. | - |
| GatingNote | NVARCHAR(MAX) | - |  | <span id="GatingNote"></span>Free-text description of the gating discipline (e.g. 'TresCON round-robin slot 2', 'selected when DigitalIn3 high').
 | - |

<span id="ChannelTrait"></span>

### ChannelTrait

Junction recording the accumulated set of operations applied to a Channel across its full lineage (ADR 0005). Each row asserts one OperationKind is part of a Channel's trait set; multiple traits can be simultaneously true (AND semantics), unlike the former scalar processing-kind FK.
Population rule: computed once at Channel creation as the union of all input channels' trait sets plus the producing step's OperationKind. Raw sensor channels receive a single Unprocessed trait. The set is immutable — Channels are immutable, so their trait set never changes.
This is a denormalized fast-filter cache. The lineage DAG is authoritative; the trait set is a deterministic projection of it.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Stream_ID | INT **(PK)** | - | ✓ | <span id="Stream_ID"></span>The Channel this trait belongs to (a Channel is identified by its Stream_ID; the trait set belongs to the channel).
 | FK → [Stream.Stream_ID](#Stream) |
| OperationKind_ID | INT **(PK)** | - | ✓ | <span id="OperationKind_ID"></span>An operation that is part of this Channel's accumulated trait set | FK → [OperationKind.OperationKind_ID](#OperationKind) |

<span id="ControlLoop"></span>

### ControlLoop

Identity record for a control scheme applied to a process. Describes the controller type and its degradation strategy (FallbackControlLoop_ID chain, or NULL for manual fallback). Temporal configuration (tuning, parameters) lives in ControlLoopApplication. SignalPort membership lives in ControlLoopPort.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| ControlLoop_ID | INT **(PK)** | - | ✓ | <span id="ControlLoop_ID"></span>Surrogate primary key | - |
| Name | NVARCHAR(200) | - | ✓ | <span id="Name"></span>Human-readable name for this control loop | - |
| ControllerKind_ID | INT | - | ✓ | <span id="ControllerKind_ID"></span>Controller algorithm class (FK to ControllerKind) | FK → [ControllerKind.ControllerKind_ID](#ControllerKind) |
| FallbackControlLoop_ID | INT | - |  | <span id="FallbackControlLoop_ID"></span>The control loop that takes over if this loop is deactivated. NULL = falls back to manual operation. | FK → [ControlLoop.ControlLoop_ID](#ControlLoop) |
| AlgorithmReference | NVARCHAR(500) | - |  | <span id="AlgorithmReference"></span>Path or repository URL for custom algorithm implementations | - |
| Description | NVARCHAR(MAX) | - |  | <span id="Description"></span>Narrative description of the loop, including notes on novel roles | - |

<span id="ControlLoopApplication"></span>

### ControlLoopApplication

Temporal history of a ControlLoop's active configuration — tuning events and parameter changes, not per-interval dynamic setpoints. Application rows record human or supervisory changes (new Kp/Ki/Kd, new MPC weights) that are hours-to-weeks apart. Per-interval outputs (e.g. MPC setpoint trajectory) are Observations on a SetPoint-type Channel, not Application rows. At most one row per ControlLoop_ID may have EndTime IS NULL (the "active" application).



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| ControlLoopApplication_ID | INT **(PK)** | - | ✓ | <span id="ControlLoopApplication_ID"></span>Surrogate primary key | - |
| ControlLoop_ID | INT | - | ✓ | <span id="ControlLoop_ID"></span>The control loop this application configuration belongs to | FK → [ControlLoop.ControlLoop_ID](#ControlLoop) |
| StartTime | DATETIME2(7) | - | ✓ | <span id="StartTime"></span>UTC datetime when this configuration became active | - |
| EndTime | DATETIME2(7) | - |  | <span id="EndTime"></span>UTC datetime when this configuration was superseded. NULL = currently active. | - |
| Parameters | NVARCHAR(MAX) | - |  | <span id="Parameters"></span>JSON blob of controller parameters for this application window. Examples: {"Kp":2.5,"Ki":0.1,"Kd":0.0} for PID; {"weights":{"DO":1.0,"NH4":0.5},"horizon":12} for MPC. Schema is controller-type-specific and deliberately unstructured.
 | - |
| AppliedByPerson_ID | INT | - |  | <span id="AppliedByPerson_ID"></span>Person who activated this configuration | FK → [Person.Person_ID](#Person) |
| Notes | NVARCHAR(MAX) | - |  | <span id="Notes"></span>Free-text notes about this configuration change | - |

<span id="ControlLoopPort"></span>

### ControlLoopPort

Association between a ControlLoop and its participating Streams (any time-series identity — a sensor Channel or a lab AnalysisSeries), with an explicit role for each stream. The unique constraint ensures each stream appears at most once per loop. Cascade control is modelled by using the same Stream_ID in two different loops with different roles (ManipulatedVariable in outer, SetPoint in inner).



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| ControlLoopPort_ID | INT **(PK)** | - | ✓ | <span id="ControlLoopPort_ID"></span>Surrogate primary key | - |
| ControlLoop_ID | INT | - | ✓ | <span id="ControlLoop_ID"></span>The control loop this association belongs to | FK → [ControlLoop.ControlLoop_ID](#ControlLoop) |
| Stream_ID | INT | - | ✓ | <span id="Stream_ID"></span>The Stream (sensor Channel or lab AnalysisSeries) participating in this control loop | FK → [Stream.Stream_ID](#Stream) |
| ControlLoopPortKind_ID | INT | - | ✓ | <span id="ControlLoopPortKind_ID"></span>The functional kind of this stream within the loop | FK → [ControlLoopPortKind.ControlLoopPortKind_ID](#ControlLoopPortKind) |

<span id="ControlLoopPortKind"></span>

### ControlLoopPortKind

Controlled vocabulary for the functional kind of a Channel within a ControlLoop. 'Other' is an explicit escape hatch for novel control schemes; its use should be accompanied by a description in ControlLoop.Description.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| ControlLoopPortKind_ID | INT **(PK)** | - | ✓ | <span id="ControlLoopPortKind_ID"></span>Surrogate primary key, manually assigned | - |
| Name | NVARCHAR(50) | - | ✓ | <span id="Name"></span>Short name for this control loop port kind | - |
| Description | NVARCHAR(200) | - |  | <span id="Description"></span>Explanation of the kind within a control loop | - |

<span id="ControllerKind"></span>

### ControllerKind

Controlled vocabulary for control loop algorithm classes


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| ControllerKind_ID | INT **(PK)** | - | ✓ | <span id="ControllerKind_ID"></span>Surrogate primary key | - |
| Name | NVARCHAR(100) | - | ✓ | <span id="Name"></span>Human-readable name of the controller algorithm class | - |
| Description | NVARCHAR(500) | - |  | <span id="Description"></span>Explanation of the controller algorithm | - |

<span id="DASLocationHistory"></span>

### DASLocationHistory

Temporal record of where a Data Acquisition System (DAS) is physically deployed (which Site and Campaign). At most one row per DAS may have ValidTo IS NULL (the DAS's current deployment). Used by the campaign wizard to warn when a DAS is being reused at a different site while still marked as active elsewhere.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| DASLocationHistory_ID | INT **(PK)** | - | ✓ | <span id="DASLocationHistory_ID"></span>Surrogate primary key | - |
| DataAcquisitionSystem_ID | INT | - | ✓ | <span id="DataAcquisitionSystem_ID"></span>The DAS whose site deployment is recorded here | FK → [DataAcquisitionSystem.DataAcquisitionSystem_ID](#DataAcquisitionSystem) |
| Site_ID | INT | - | ✓ | <span id="Site_ID"></span>The site where this DAS is deployed during this period | FK → [Site.Site_ID](#Site) |
| Campaign_ID | INT | - |  | <span id="Campaign_ID"></span>Campaign during which this deployment started (if applicable) | FK → [Campaign.Campaign_ID](#Campaign) |
| ValidFrom | DATETIME2(7) | - | ✓ | <span id="ValidFrom"></span>UTC datetime when the DAS was deployed at this site | - |
| ValidTo | DATETIME2(7) | - |  | <span id="ValidTo"></span>UTC datetime when the DAS left this site. NULL = currently deployed. | - |
| Notes | NVARCHAR(MAX) | - |  | <span id="Notes"></span>Free-text notes about the deployment or move | - |

<span id="DataAcquisitionSystem"></span>

### DataAcquisitionSystem

The computer or device that collects measurements from your field equipment and stores or transmits them. This is usually a box at the site — a logger, a SCADA station, or even a laptop running your instrument software. Technically it is any upstream system that assigns tags to signals: SCADA servers, PLCs, data loggers, OPC-UA servers, CSV importers, etc. Supports hierarchy via ParentSystem_ID (e.g. plant SCADA → field PLC → sensor module).



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| DataAcquisitionSystem_ID | INT **(PK)** | - | ✓ | <span id="DataAcquisitionSystem_ID"></span>Surrogate primary key | - |
| ParentSystem_ID | INT | - |  | <span id="ParentSystem_ID"></span>Optional parent DAS in a hierarchy (e.g. plant SCADA containing a PLC sub-system) | FK → [DataAcquisitionSystem.DataAcquisitionSystem_ID](#DataAcquisitionSystem) |
| Name | NVARCHAR(200) | - | ✓ | <span id="Name"></span>Human-readable name of the system (e.g. 'Plant SCADA', 'CommCube-A') | - |
| DataAcquisitionSystemKind_ID | INT | - |  | <span id="DataAcquisitionSystemKind_ID"></span>Category of DAS (FK to DataAcquisitionSystemKind) | FK → [DataAcquisitionSystemKind.DataAcquisitionSystemKind_ID](#DataAcquisitionSystemKind) |
| Manufacturer | NVARCHAR(100) | - |  | <span id="Manufacturer"></span>Manufacturer or vendor of the system | - |
| Model | NVARCHAR(100) | - |  | <span id="Model"></span>Model name or version of the system | - |
| Description | NVARCHAR(MAX) | - |  | <span id="Description"></span>Free-text notes about this DAS | - |

<span id="DataAcquisitionSystemKind"></span>

### DataAcquisitionSystemKind

Controlled vocabulary for categories of Data Acquisition Systems


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| DataAcquisitionSystemKind_ID | INT **(PK)** | - | ✓ | <span id="DataAcquisitionSystemKind_ID"></span>Surrogate primary key | - |
| Name | NVARCHAR(100) | - | ✓ | <span id="Name"></span>Human-readable name of the Data Acquisition System category | - |
| Description | NVARCHAR(500) | - |  | <span id="Description"></span>Explanation of what this category of Data Acquisition System represents | - |

<span id="DataProvenanceKind"></span>

### DataProvenanceKind

Controlled vocabulary describing how a measurement was produced (Sensor, Laboratory, Manual Entry, Model Output, External Source, Forecast)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| DataProvenanceKind_ID | INT **(PK)** | - | ✓ | <span id="DataProvenanceKind_ID"></span>Surrogate primary key | - |
| Name | NVARCHAR(50) | - | ✓ | <span id="Name"></span>Name of the provenance kind | - |
| Description | NVARCHAR(300) | - |  | <span id="Description"></span>Explanation of how data with this provenance was produced | - |

<span id="Dataset"></span>

### Dataset

A named collection of Channels assembled for a processing or analysis purpose. Analogous to metEAUdata's Dataset concept: groups one or more Signals (Channels) that are processed together. Particularly useful for multivariate processing, where multiple input Channels produce one or more output Channels in a single ProcessingStep. Channels in a Dataset need not share a Campaign or Site.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Dataset_ID | INT **(PK)** | - | ✓ | <span id="Dataset_ID"></span>Surrogate primary key | - |
| Name | NVARCHAR(200) | - | ✓ | <span id="Name"></span>Human-readable name for the dataset (e.g. 'WWTP Influent Q1-2024 Multivariate') | - |
| Description | NVARCHAR(2000) | - |  | <span id="Description"></span>Detailed description of the dataset's contents, scope, and intended use | - |
| Purpose | NVARCHAR(500) | - |  | <span id="Purpose"></span>The analytical or processing objective this dataset was assembled for (e.g. 'Fault detection model training', 'Compliance reporting', 'Gap-filling pipeline').
 | - |
| CreatedOn | DATETIME2(7) | - | ✓ | <span id="CreatedOn"></span>UTC timestamp when this dataset was created | Default: `CURRENT_TIMESTAMP` |
| CreatedByPerson_ID | INT | - |  | <span id="CreatedByPerson_ID"></span>Person who created this dataset. NULL for automated pipelines. | FK → [Person.Person_ID](#Person) |

<span id="DatasetChannel"></span>

### DatasetChannel

Junction table linking Datasets to the Channels they contain. A Dataset groups one or more Channels that are processed together. A Channel may appear in multiple Datasets (e.g. a raw TSS channel used as input in several independent analysis pipelines).



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Dataset_ID | INT **(PK)** | - | ✓ | <span id="Dataset_ID"></span>The dataset this channel belongs to | FK → [Dataset.Dataset_ID](#Dataset) |
| Channel_ID | INT **(PK)** | - | ✓ | <span id="Channel_ID"></span>The channel (signal in metEAUdata terms) included in this dataset | FK → [Channel.Stream_ID](#Channel) |

<span id="Equipment"></span>

### Equipment

Stores information about a specific physical piece of equipment (e.g., serial number, owner, purchase date, storage location).



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Equipment_ID | INT **(PK)** | - | ✓ | <span id="Equipment_ID"></span>Surrogate primary key | - |
| EquipmentModel_ID | INT | - |  | <span id="EquipmentModel_ID"></span>Link to the Equipment model table | FK → [EquipmentModel.EquipmentModel_ID](#EquipmentModel) |
| Identifier | NVARCHAR(100) | - |  | <span id="Identifier"></span>Name used to uniquekly identify the equipment. | - |
| SerialNumber | NVARCHAR(100) | - |  | <span id="SerialNumber"></span>Serial number of the equipment | - |
| Owner | NVARCHAR(MAX) | - |  | <span id="Owner"></span>Name of the owner of the equipment | - |
| StorageLocation | NVARCHAR(100) | - |  | <span id="StorageLocation"></span>Where the equipment is stored when not deployed | - |
| PurchaseDate | DATE | - |  | <span id="PurchaseDate"></span>Date when the equipment was bought. | - |
| IsActive | BIT | - | ✓ | <span id="IsActive"></span>Whether this equipment is currently in service. Set to false when decommissioned. Decommissioning should also be recorded as an EquipmentEvent for auditability.
 | Default: `True` |

<span id="EquipmentKind"></span>

### EquipmentKind

Controlled vocabulary for categories of equipment models


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| EquipmentKind_ID | INT **(PK)** | - | ✓ | <span id="EquipmentKind_ID"></span>Surrogate primary key | - |
| Name | NVARCHAR(100) | - | ✓ | <span id="Name"></span>Human-readable name of the equipment category | - |
| Description | NVARCHAR(500) | - |  | <span id="Description"></span>Explanation of what this category of equipment represents | - |

<span id="EquipmentLocationHistory"></span>

### EquipmentLocationHistory

Temporal record of where a piece of Equipment is physically installed (which SamplingPoint). Independent from EquipmentWiringHistory: a probe can be relocated without changing its wiring, and vice versa. At most one row per Equipment may have ValidTo IS NULL (the equipment's current location).



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| EquipmentLocationHistory_ID | INT **(PK)** | - | ✓ | <span id="EquipmentLocationHistory_ID"></span>Surrogate primary key | - |
| Equipment_ID | INT | - | ✓ | <span id="Equipment_ID"></span>The physical instrument whose location is recorded here | FK → [Equipment.Equipment_ID](#Equipment) |
| SamplingPoint_ID | INT | - | ✓ | <span id="SamplingPoint_ID"></span>Sampling location where this equipment is installed during this period | FK → [SamplingPoint.SamplingPoint_ID](#SamplingPoint) |
| ValidFrom | DATETIME2(7) | - | ✓ | <span id="ValidFrom"></span>UTC datetime when the equipment started measuring at this location | - |
| ValidTo | DATETIME2(7) | - |  | <span id="ValidTo"></span>UTC datetime when the equipment left this location. NULL = currently installed. | - |
| Campaign_ID | INT | - |  | <span id="Campaign_ID"></span>Campaign under which this deployment occurred. Recommended: permanent baseline sensors reference a standing operational campaign. | FK → [Campaign.Campaign_ID](#Campaign) |
| Notes | NVARCHAR(MAX) | - |  | <span id="Notes"></span>Free-text notes about the deployment or relocation | - |

<span id="EquipmentModel"></span>

### EquipmentModel

Stores detailed, non-redundant specifications for a specific sensor or instrument model (e.g., manufacturer, functions, method)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| EquipmentModel_ID | INT **(PK)** | - | ✓ | <span id="EquipmentModel_ID"></span>Link to the Equipment model table | - |
| EquipmentModel | NVARCHAR(100) | - |  | <span id="EquipmentModel"></span>Name of the equipment model. For example: ammo::lyser | - |
| Method | NVARCHAR(100) | - |  | <span id="Method"></span>Method behind the equipment | - |
| Functions | NVARCHAR(MAX) | - |  | <span id="Functions"></span>Description of the functions of the equipment | - |
| Manufacturer | NVARCHAR(100) | - |  | <span id="Manufacturer"></span>Name of the manufacturer | - |
| ManualLocation | NVARCHAR(1000) | - |  | <span id="ManualLocation"></span>Location where the manual is stored (e.g. a SharePoint URL) | - |
| EquipmentKind_ID | INT | - |  | <span id="EquipmentKind_ID"></span>Category of equipment this model belongs to. Drives which pickers offer it — only models classified as Sampler appear in the laboratory forms. | FK → [EquipmentKind.EquipmentKind_ID](#EquipmentKind) |

<span id="EquipmentModelHasParameter"></span>

### EquipmentModelHasParameter

Links equipment models to the parameters they can measure


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| EquipmentModel_ID | INT **(PK)** | - | ✓ | <span id="EquipmentModel_ID"></span>Link to the Equipment model table | FK → [EquipmentModel.EquipmentModel_ID](#EquipmentModel) |
| Parameter_ID | INT **(PK)** | - | ✓ | <span id="Parameter_ID"></span>Link to the Parameter table | FK → [Parameter.Parameter_ID](#Parameter) |

<span id="EquipmentModelHasProcedures"></span>

### EquipmentModelHasProcedures

Links equipment models to the relevant maintenance procedures


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| EquipmentModel_ID | INT **(PK)** | - | ✓ | <span id="EquipmentModel_ID"></span>Link to the Equipment model table | FK → [EquipmentModel.EquipmentModel_ID](#EquipmentModel) |
| Procedure_ID | INT **(PK)** | - | ✓ | <span id="Procedure_ID"></span>Link to the Procedures table | FK → [Procedures.Procedure_ID](#Procedures) |

<span id="EquipmentWiringHistory"></span>

### EquipmentWiringHistory

Temporal record of how a piece of Equipment is wired to a SignalInterface (and optionally a specific SignalInterfacePort). When a sensor probe is swapped, rewired to a different input, or temporarily disconnected, a closed row is written and (usually) a new open row is opened. The port reference is nullable: at ingest time the interface + tag are always known, but the physical port may not have been traced yet. At most one row per Equipment may have ValidTo IS NULL (the equipment's current wiring).



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| EquipmentWiringHistory_ID | INT **(PK)** | - | ✓ | <span id="EquipmentWiringHistory_ID"></span>Surrogate primary key | - |
| Equipment_ID | INT | - | ✓ | <span id="Equipment_ID"></span>The physical instrument whose wiring is recorded here | FK → [Equipment.Equipment_ID](#Equipment) |
| SignalInterface_ID | INT | - | ✓ | <span id="SignalInterface_ID"></span>The interface this equipment is wired into during this period | FK → [SignalInterface.SignalInterface_ID](#SignalInterface) |
| SignalInterfacePort_ID | INT | - |  | <span id="SignalInterfacePort_ID"></span>Specific port on the interface (NULL when not yet traced) | FK → [SignalInterfacePort.SignalInterfacePort_ID](#SignalInterfacePort) |
| ValidFrom | DATETIME2(7) | - | ✓ | <span id="ValidFrom"></span>UTC datetime when this wiring started | - |
| ValidTo | DATETIME2(7) | - |  | <span id="ValidTo"></span>UTC datetime when this wiring ended. NULL = currently wired. | - |
| Note | NVARCHAR(MAX) | - |  | <span id="Note"></span>Free-text notes (reason for rewire, calibration context) | - |

<span id="Event"></span>

### Event

Records a discrete, time-stamped operational occurrence (calibration, cleaning, power outage, PLC crash, site visit, …) at any node of the physical hierarchy. Each Event attaches to exactly one target via an exclusive arc of eight nullable FKs — a CHECK constraint enforces that exactly one is non-NULL. Generalises the former EquipmentEvent (which was restricted to Equipment).



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Event_ID | INT **(PK)** | - | ✓ | <span id="Event_ID"></span>Surrogate primary key | - |
| Channel_ID | INT | - |  | <span id="Channel_ID"></span>Leaf target: the specific sensor Channel the event concerns (references Channel.Stream_ID) | FK → [Channel.Stream_ID](#Channel) |
| Equipment_ID | INT | - |  | <span id="Equipment_ID"></span>Target: the Equipment the event concerns (sensor, actuator, …) | FK → [Equipment.Equipment_ID](#Equipment) |
| SignalInterface_ID | INT | - |  | <span id="SignalInterface_ID"></span>Target: the SignalInterface (field bus, port block) the event concerns | FK → [SignalInterface.SignalInterface_ID](#SignalInterface) |
| DataAcquisitionSystem_ID | INT | - |  | <span id="DataAcquisitionSystem_ID"></span>Target: the DataAcquisitionSystem (PLC, logger) the event concerns | FK → [DataAcquisitionSystem.DataAcquisitionSystem_ID](#DataAcquisitionSystem) |
| SamplingPoint_ID | INT | - |  | <span id="SamplingPoint_ID"></span>Target: the SamplingPoint the event concerns | FK → [SamplingPoint.SamplingPoint_ID](#SamplingPoint) |
| ProcessUnit_ID | INT | - |  | <span id="ProcessUnit_ID"></span>Target: the ProcessUnit the event concerns | FK → [ProcessUnit.ProcessUnit_ID](#ProcessUnit) |
| Site_ID | INT | - |  | <span id="Site_ID"></span>Target: the Site the event concerns (site-wide power outage, etc.) | FK → [Site.Site_ID](#Site) |
| Campaign_ID | INT | - |  | <span id="Campaign_ID"></span>Target: the Campaign the event concerns | FK → [Campaign.Campaign_ID](#Campaign) |
| EventKind_ID | INT | - | ✓ | <span id="EventKind_ID"></span>Kind of event (calibration, cleaning, power outage, …) | FK → [EventKind.EventKind_ID](#EventKind) |
| EventDateTimeStart | DATETIME2(7) | - | ✓ | <span id="EventDateTimeStart"></span>Date and time the event began (UTC) | - |
| IsInstantaneous | BIT | - | ✓ | <span id="IsInstantaneous"></span>True if the event occurred at a single point in time. When true, EventDateTimeEnd must be NULL. When false and EventDateTimeEnd is NULL, the event is ongoing.
 | Default: `False` |
| EventDateTimeEnd | DATETIME2(7) | - |  | <span id="EventDateTimeEnd"></span>Date and time the event ended (UTC). NULL when IsInstantaneous=1 (point-in-time) or when the event is still ongoing (IsInstantaneous=0).
 | - |
| PerformedByPerson_ID | INT | - |  | <span id="PerformedByPerson_ID"></span>Person who physically performed the event (e.g. technician on site) | FK → [Person.Person_ID](#Person) |
| RecordedByPerson_ID | INT | - |  | <span id="RecordedByPerson_ID"></span>Person who entered this record into the system (may differ from PerformedByPerson_ID) | FK → [Person.Person_ID](#Person) |
| Notes | NVARCHAR(MAX) | - |  | <span id="Notes"></span>Free-text notes about the event | - |

<span id="EventKind"></span>

### EventKind

Controlled vocabulary classifying the kind of operational event (Calibration, Cleaning, PowerOutage, ControllerCrash, …). Generalises the former EquipmentEventKind to cover all targets in the exclusive-arc Event table.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| EventKind_ID | INT **(PK)** | - | ✓ | <span id="EventKind_ID"></span>Surrogate primary key | - |
| Name | NVARCHAR(100) | - | ✓ | <span id="Name"></span>Name of the event kind | - |
| Description | NVARCHAR(300) | - |  | <span id="Description"></span>Explanation of what this kind of event involves | - |

<span id="HydrologicalCharacteristics"></span>

### HydrologicalCharacteristics

Stores the hydrological land use percentages (e.g., forest, wetlands, cropland, grassland) within the watershed


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Watershed_ID | INT **(PK)** | - | ✓ | <span id="Watershed_ID"></span>Linked to the Watershed table | FK → [Watershed.Watershed_ID](#Watershed) |
| UrbanArea | REAL | - |  | <span id="UrbanArea"></span>Percentage [%] of urban areas | - |
| Forest | REAL | - |  | <span id="Forest"></span>Percentage [%] of forest areas | - |
| Wetlands | REAL | - |  | <span id="Wetlands"></span>Percentage [%] of wetlands | - |
| Cropland | REAL | - |  | <span id="Cropland"></span>Percentage [%] of croplands | - |
| Meadow | REAL | - |  | <span id="Meadow"></span>Percentage [%] of meadow areas | - |
| Grassland | REAL | - |  | <span id="Grassland"></span>Percentage [%] of grasslands | - |

<span id="LabAnalysis"></span>

### LabAnalysis

One analytical run on a discrete physical sample — the event-record sitting at the intersection of two orthogonal grouping axes: LabExperiment (the session: who/when) and AnalysisSeries (the stream identity: parameter / location / kind / processing / unit). The measurement itself lives in Observation (via LabAnalysis_ID) and is routed to a payload table (Value / ValueVector / ValueMatrix / ValueImage) so lab data is no longer scalar-only. Point-level review state (ReviewStatus_ID, ReviewedByPerson_ID, ReviewDateTime) records the institutional approval of each individual measurement, parallel to QualityCode_ID; AuditLog covers amendment history.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| LabAnalysis_ID | INT **(PK)** | - | ✓ | <span id="LabAnalysis_ID"></span>Surrogate primary key | - |
| LabExperiment_ID | INT | - | ✓ | <span id="LabExperiment_ID"></span>The lab session this analysis was part of | FK → [LabExperiment.LabExperiment_ID](#LabExperiment) |
| AnalysisSeries_ID | INT | - | ✓ | <span id="AnalysisSeries_ID"></span>The measurement stream (parameter / location / value kind) this analysis belongs to | FK → [AnalysisSeries.Stream_ID](#AnalysisSeries) |
| Sample_ID | INT | - | ✓ | <span id="Sample_ID"></span>The physical sample that was analysed | FK → [Sample.Sample_ID](#Sample) |
| Replicate | INT | - | ✓ | <span id="Replicate"></span>Replicate number (1 = primary measurement, 2+ = duplicates) | Default: `1` |
| QualityCode_ID | INT | - |  | <span id="QualityCode_ID"></span>Optional quality flag. NULL means no quality assessment has been recorded. | FK → [QualityCode.QualityCode_ID](#QualityCode) |
| ReviewStatus_ID | INT | - | ✓ | <span id="ReviewStatus_ID"></span>Institutional approval state of this measurement. Defaults to Pending (1) at ingest. Review is point-level (per LabAnalysis row), not series-level.
 | FK → [ReviewStatus.ReviewStatus_ID](#ReviewStatus)<br>Default: `1` |
| ReviewedByPerson_ID | INT | - |  | <span id="ReviewedByPerson_ID"></span>Person who approved/rejected this measurement. NULL = not yet reviewed. | FK → [Person.Person_ID](#Person) |
| ReviewDateTime | DATETIME2(7) | - |  | <span id="ReviewDateTime"></span>When the review decision was recorded. NULL = not yet reviewed. | - |
| Laboratory_ID | INT | - |  | <span id="Laboratory_ID"></span>Laboratory where the analysis was performed | FK → [Laboratory.Laboratory_ID](#Laboratory) |
| AnalystPerson_ID | INT | - |  | <span id="AnalystPerson_ID"></span>Person who performed the analysis | FK → [Person.Person_ID](#Person) |
| Procedure_ID | INT | - |  | <span id="Procedure_ID"></span>Standard operating procedure used for this analysis | FK → [Procedures.Procedure_ID](#Procedures) |
| AnalysisDateTime | DATETIME2(7) | - | ✓ | <span id="AnalysisDateTime"></span>UTC datetime when the analysis was performed. If it's a long analysis, record the beginning. | Default: `SYSUTCDATETIME()` |
| Notes | NVARCHAR(MAX) | - |  | <span id="Notes"></span>Free-text notes about this analysis run | - |

<span id="LabExperiment"></span>

### LabExperiment

Session container for lab work — groups heterogeneous LabAnalyses that were performed together as one named lab occasion (e.g. "PSVD-Settling- 2026-05-11"). One LabExperiment can span multiple AnalysisSeries; one AnalysisSeries can participate in many LabExperiments. The session axis answers "what was done that day" while the AnalysisSeries axis answers "all measurements of this parameter at this location over time".



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| LabExperiment_ID | INT **(PK)** | - | ✓ | <span id="LabExperiment_ID"></span>Surrogate primary key | - |
| Name | NVARCHAR(200) | - | ✓ | <span id="Name"></span>Human-readable label for the session | - |
| Campaign_ID | INT | - |  | <span id="Campaign_ID"></span>Campaign this experiment was part of, if any | FK → [Campaign.Campaign_ID](#Campaign) |
| ExperimentDateTime | DATETIME2(7) | - | ✓ | <span id="ExperimentDateTime"></span>UTC datetime when the session took place | Default: `SYSUTCDATETIME()` |
| Description | NVARCHAR(MAX) | - |  | <span id="Description"></span>Free-text notes about this experiment | - |
| CreatedByPerson_ID | INT | - |  | <span id="CreatedByPerson_ID"></span>Person who recorded this experiment session | FK → [Person.Person_ID](#Person) |
| LabPanel_ID | INT | - |  | <span id="LabPanel_ID"></span>LabPanel this experiment was derived from, if any. NULL for experiments created from scratch. | FK → [LabPanel.LabPanel_ID](#LabPanel) |

<span id="LabPanel"></span>

### LabPanel

Named, reusable bundle of AnalysisSeries to run together in a lab session. Copy-on-use: selecting a panel pre-populates the series list for a new LabExperiment; the resulting experiment is fully independent. Analogous to a clinical lab panel.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| LabPanel_ID | INT **(PK)** | - | ✓ | <span id="LabPanel_ID"></span>Surrogate primary key | - |
| Name | NVARCHAR(200) | - | ✓ | <span id="Name"></span>Human-readable panel name (e.g. 'PSVD Weekly Panel') | - |
| Description | NVARCHAR(MAX) | - |  | <span id="Description"></span>Free-text description of the panel's purpose | - |
| CreatedByPerson_ID | INT | - |  | <span id="CreatedByPerson_ID"></span>Person who created this panel | FK → [Person.Person_ID](#Person) |
| DefaultSampleCollectionKind_ID | INT | - |  | <span id="DefaultSampleCollectionKind_ID"></span>Default sample collection method pre-filled when this panel is loaded (e.g. Grab) | FK → [SampleCollectionKind.SampleCollectionKind_ID](#SampleCollectionKind) |
| DefaultSampleKind_ID | INT | - |  | <span id="DefaultSampleKind_ID"></span>Default sample analytical role pre-filled when this panel is loaded (e.g. Field) | FK → [SampleKind.SampleKind_ID](#SampleKind) |
| DefaultSampleMaterialKind_ID | INT | - |  | <span id="DefaultSampleMaterialKind_ID"></span>Default sample material/matrix pre-filled when this panel is loaded (e.g. mixed liquor) | FK → [SampleMaterialKind.SampleMaterialKind_ID](#SampleMaterialKind) |
| DefaultSampleEquipment_ID | INT | - |  | <span id="DefaultSampleEquipment_ID"></span>Default equipment pre-filled when this panel is loaded (e.g. auto-sampler ID) | FK → [Equipment.Equipment_ID](#Equipment) |
| CreatedAt | DATETIME2(7) | - | ✓ | <span id="CreatedAt"></span>When this panel was created (UTC) | Default: `GETUTCDATE()` |

<span id="LabPanelSeries"></span>

### LabPanelSeries

Junction table linking a LabPanel to the AnalysisSeries it prescribes. When a user creates an experiment "from panel", all series listed here are pre-populated into the session.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| LabPanel_ID | INT **(PK)** | - | ✓ | <span id="LabPanel_ID"></span>References the panel (FK) | FK → [LabPanel.LabPanel_ID](#LabPanel) |
| AnalysisSeries_ID | INT **(PK)** | - | ✓ | <span id="AnalysisSeries_ID"></span>References an analysis series to include in the panel | FK → [AnalysisSeries.Stream_ID](#AnalysisSeries) |

<span id="Laboratory"></span>

### Laboratory

A laboratory where discrete samples are analysed. May be on-site or external.


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Laboratory_ID | INT **(PK)** | - | ✓ | <span id="Laboratory_ID"></span>Surrogate primary key | - |
| Name | NVARCHAR(200) | - | ✓ | <span id="Name"></span>Name of the laboratory | - |
| Site_ID | INT | - |  | <span id="Site_ID"></span>Site where the laboratory is located, if on-site. NULL for external labs. | FK → [Site.Site_ID](#Site) |
| Description | NVARCHAR(500) | - |  | <span id="Description"></span>Additional information about the laboratory | - |

<span id="LandUse"></span>

### LandUse

Stores the land use percentages (e.g., commercial, residential, green spaces) within the watershed


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Watershed_ID | INT **(PK)** | - | ✓ | <span id="Watershed_ID"></span>Linked to the Watershed table | FK → [Watershed.Watershed_ID](#Watershed) |
| Commercial | REAL | - |  | <span id="Commercial"></span>Percentage [%] of commercial areas. For example stores or bank areas | - |
| GreenSpaces | REAL | - |  | <span id="GreenSpaces"></span>Percentage [%] of green spaces | - |
| Industrial | REAL | - |  | <span id="Industrial"></span>Percentage [%] of industrial areas. For example factories | - |
| Institutional | REAL | - |  | <span id="Institutional"></span>Percentage [%] of institutional areas. For example schools, police stations or city hall | - |
| Residential | REAL | - |  | <span id="Residential"></span>Percentage [%] of residential areas. For example houses or apartment buildings | - |
| Agricultural | REAL | - |  | <span id="Agricultural"></span>Percentage [%] of agricultural land use. For example farm land | - |
| Recreational | REAL | - |  | <span id="Recreational"></span>Percentage [%] of recreational areas. For example parks or sport fields | - |

<span id="Observation"></span>

### Observation

Shared hub table representing a single measurement event at a timestamp. The source is either a sensor Channel (Channel_ID NOT NULL, LabAnalysis_ID NULL) or a lab analysis (LabAnalysis_ID NOT NULL, Channel_ID NULL); an XOR CHECK constraint enforces that exactly one is set per row. The four payload tables (Value, ValueVector, ValueMatrix, ValueImage) carry only their type-specific data, keyed by Observation_ID. ValueKind_ID mirrors the upstream Channel.ValueKind_ID or AnalysisSeries.ValueKind_ID for self-description.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Observation_ID | INT **(PK)** | - | ✓ | <span id="Observation_ID"></span>Surrogate key; auto-assigned by the database | - |
| Channel_ID | INT | - |  | <span id="Channel_ID"></span>The sensor channel this observation belongs to. NULL for lab observations (which set LabAnalysis_ID instead).
 | FK → [Channel.Stream_ID](#Channel) |
| LabAnalysis_ID | INT | - |  | <span id="LabAnalysis_ID"></span>The lab analysis this observation belongs to. NULL for sensor observations (which set Channel_ID instead). Exactly one of Channel_ID / LabAnalysis_ID is non-NULL per row (XOR CHECK).
 | FK → [LabAnalysis.LabAnalysis_ID](#LabAnalysis) |
| Timestamp | DATETIME2(7) | - | ✓ | <span id="Timestamp"></span>UTC timestamp of the observation — the real-world moment it was measured. For sensor observations this is the channel read time; for lab observations it is set from Sample.SampleDateTimeStart (the sample collection time) at insert time. LabAnalysis.AnalysisDateTime is kept separately as analytical-provenance metadata.
 | - |
| ValueKind_ID | INT | - | ✓ | <span id="ValueKind_ID"></span>Payload kind (1=Scalar, 2=Vector, 3=Matrix, 4=Image). For sensor observations must match the Channel's ValueKind; for lab observations must match the AnalysisSeries's ValueKind.
 | FK → [ValueKind.ValueKind_ID](#ValueKind) |

<span id="OperationKind"></span>

### OperationKind

Controlled vocabulary of data-transformation operations. It serves two roles: (1) it classifies a ProcessingStep — each step performs exactly one OperationKind; and (2) the accumulated set of OperationKinds applied across a Channel's full lineage forms that Channel's ChannelTrait set. Replaces the retired processing-kind lookup (ADR 0005). IDs are stable and referenced by application code.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| OperationKind_ID | INT **(PK)** | - | ✓ | <span id="OperationKind_ID"></span>Surrogate primary key, manually assigned (non-identity) | - |
| Name | NVARCHAR(50) | - | ✓ | <span id="Name"></span>Operation name (e.g. 'OutlierRemoval', 'Smoothing') | - |
| Description | NVARCHAR(200) | - |  | <span id="Description"></span>Explanation of what this operation does | - |

<span id="Parameter"></span>

### Parameter

Stores the different water quality or quantity parameters that are measured (e.g., pH, TSS, N-components)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Parameter_ID | INT **(PK)** | - | ✓ | <span id="Parameter_ID"></span>Surrogate key. Manually assigned. | - |
| Parameter | NVARCHAR(100) | - |  | <span id="Parameter"></span>Name of the parameter | - |
| Description | NVARCHAR(MAX) | - |  | <span id="Description"></span>Description of the parameter | - |
| ENVO_IRI | NVARCHAR(256) | - |  | <span id="ENVO_IRI"></span>ENVO ontology IRI for the parameter (e.g. http://purl.obolibrary.org/obo/ENVO_01001502) | - |
| ValueKind_ID | INT | - | ✓ | <span id="ValueKind_ID"></span>Shape of the stored value: FK to ValueKind (1=Scalar, 2=Vector, 3=Matrix, 4=Image) | FK → [ValueKind.ValueKind_ID](#ValueKind)<br>Default: `1` |
| QUDT_QuantityKind_IRI | NVARCHAR(256) | - |  | <span id="QUDT_QuantityKind_IRI"></span>QUDT quantity kind IRI; used at build time to populate ParameterHasUnit. NULL = no physical quantity kind (status codes, images, spectra). | - |

<span id="ParameterHasUnit"></span>

### ParameterHasUnit

Records which Units are valid for the measurement values of each Parameter. Covers Scalar, Vector, and Matrix parameters. Image parameters are excluded. For Vector/Matrix parameters this is the unit of the individual scalar values at each bin — axis units live in ValueBinningAxis.Unit_ID, not here. Do not hand-edit seed_data — rows are generated by generate_from_yaml.py by merging QUDT applicableUnit results with per-parameter manual_units overrides.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Parameter_ID | INT **(PK)** | - | ✓ | <span id="Parameter_ID"></span>Link to Parameter | FK → [Parameter.Parameter_ID](#Parameter) |
| Unit_ID | INT **(PK)** | - | ✓ | <span id="Unit_ID"></span>Link to Unit | FK → [Unit.Unit_ID](#Unit) |

<span id="Person"></span>

### Person

Personal and professional information for people involved in projects (e.g., name, affiliation, role, e-mail, phone).


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Person_ID | INT **(PK)** | - | ✓ | <span id="Person_ID"></span>Surrogate primary key | - |
| LastName | NVARCHAR(100) | - |  | <span id="LastName"></span>Last name of the person | - |
| FirstName | NVARCHAR(255) | - |  | <span id="FirstName"></span>First name of the person | - |
| Company | NVARCHAR(MAX) | - |  | <span id="Company"></span>Affiliated organisation or company | - |
| Role | NVARCHAR(255) | - |  | <span id="Role"></span>Role of the person. Controlled vocabulary: MSc, Postdoc, Intern, PhD, Professor, Research Professional, Technician, Administrator, Guest | - |
| AssignedFunctions | NVARCHAR(MAX) | - |  | <span id="AssignedFunctions"></span>Detailed description of the person's assigned duties. | - |
| Email | NVARCHAR(100) | - |  | <span id="Email"></span>E-mail address | - |
| Phone | NVARCHAR(100) | - |  | <span id="Phone"></span>Phone number | - |
| Linkedin | NVARCHAR(100) | - |  | <span id="Linkedin"></span>LinkedIn profile URL | - |
| Website | NVARCHAR(60) | - |  | <span id="Website"></span>Personal or organisation website URL | - |

<span id="ProcedureKind"></span>

### ProcedureKind

Controlled vocabulary classifying the type of a Procedure (Calibration Protocol, SOP, etc.)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| ProcedureKind_ID | INT **(PK)** | - | ✓ | <span id="ProcedureKind_ID"></span>Surrogate primary key | - |
| Name | NVARCHAR(100) | - | ✓ | <span id="Name"></span>Name of the procedure kind | - |
| Description | NVARCHAR(300) | - |  | <span id="Description"></span>Explanation of this procedure kind | - |

<span id="Procedures"></span>

### Procedures

Stores details for different measurement procedures (e.g., calibration, validation, standard operating procedures, ISO methods)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Procedure_ID | INT **(PK)** | - | ✓ | <span id="Procedure_ID"></span>Link to the Procedures table | - |
| ProcedureName | NVARCHAR(100) | - |  | <span id="ProcedureName"></span>Title name of the procedure | - |
| ProcedureKind_ID | INT | - |  | <span id="ProcedureKind_ID"></span>FK to ProcedureKind — controlled vocabulary for the type of procedure | FK → [ProcedureKind.ProcedureKind_ID](#ProcedureKind) |
| Description | NVARCHAR(MAX) | - |  | <span id="Description"></span>Description of the procedure | - |
| ProcedureLocation | NVARCHAR(100) | - |  | <span id="ProcedureLocation"></span>Where is the procedure stored (URL) | - |

<span id="ProcessUnit"></span>

### ProcessUnit

Self-referential, site-scoped hierarchy of functional process locations. Each unit carries a stable P&ID-style Tag unique per site. Used to structure sampling points within process facilities (WWTPs, pilot plants) without breaking field campaigns that rely on free-text SamplingLocation fields.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| ProcessUnit_ID | INT **(PK)** | - | ✓ | <span id="ProcessUnit_ID"></span>Primary key for the ProcessUnit | - |
| Site_ID | INT | - | ✓ | <span id="Site_ID"></span>Foreign key to Site — scopes the unit to a single site | FK → [Site.Site_ID](#Site) |
| Tag | NVARCHAR(100) | - | ✓ | <span id="Tag"></span>Stable functional identifier (e.g. R-210, BioLine1, 10-PL-102). Unique per site. | - |
| Name | NVARCHAR(255) | - | ✓ | <span id="Name"></span>Human-readable name for the process unit | - |
| Description | NVARCHAR(MAX) | - |  | <span id="Description"></span>Optional description of the process unit's role or function | - |
| ProcessUnitKind_ID | INT | - |  | <span id="ProcessUnitKind_ID"></span>Foreign key to ProcessUnitKind lookup | FK → [ProcessUnitKind.ProcessUnitKind_ID](#ProcessUnitKind) |
| Parent_ID | INT | - |  | <span id="Parent_ID"></span>Self-reference to the parent ProcessUnit, enabling an unlimited-depth tree | FK → [ProcessUnit.ProcessUnit_ID](#ProcessUnit) |

<span id="ProcessUnitKind"></span>

### ProcessUnitKind

Controlled vocabulary of process unit kinds (e.g. Reactor, Pipe, Clarifier)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| ProcessUnitKind_ID | INT **(PK)** | - | ✓ | <span id="ProcessUnitKind_ID"></span>Primary key for the ProcessUnitKind lookup | - |
| Name | NVARCHAR(100) | - | ✓ | <span id="Name"></span>Name of the process unit kind (e.g. Reactor, Pipe, Clarifier) | - |
| Description | NVARCHAR(300) | - |  | <span id="Description"></span>Explanation of this process unit kind | - |

<span id="ProcessingLineage"></span>

### ProcessingLineage

Junction table that records the input relationships between ProcessingStep rows and Stream rows. Every row is an input edge — it asserts that a given Stream (a sensor Channel or a lab AnalysisSeries) was consumed as an input by a given ProcessingStep. Together these rows form a directed acyclic graph (DAG) of data transformations. Generalizing inputs to Stream is what lets a lab AnalysisSeries feed a derived Channel (ADR 0004).
Output channels are still identified by Channel.ProducedByStep_ID (not stored here). The output of a step is always a Channel (a sensor stream); only the inputs generalize to any Stream.
Example: an outlier-removal step consumes Stream 10 (raw TSS) as an input; Channel 11 (cleaned TSS) carries ProducedByStep_ID pointing to that step.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| ProcessingLineage_ID | INT **(PK)** | - | ✓ | <span id="ProcessingLineage_ID"></span>Surrogate primary key | - |
| ProcessingStep_ID | INT | - | ✓ | <span id="ProcessingStep_ID"></span>The processing step that consumed or produced the Channel entry | FK → [ProcessingStep.ProcessingStep_ID](#ProcessingStep) |
| Stream_ID | INT | - | ✓ | <span id="Stream_ID"></span>The Stream (a sensor Channel or a lab AnalysisSeries) consumed as an input by this ProcessingStep. References any measurement stream, which is what allows a lab AnalysisSeries to be an input to a derived Channel (ADR 0004).
 | FK → [Stream.Stream_ID](#Stream) |
| StartTime | DATETIME2(7) | - |  | <span id="StartTime"></span>Start of the data slice that was consumed or produced by this step (UTC). NULL means the edge applies to the entire channel from the beginning.
 | - |
| EndTime | DATETIME2(7) | - |  | <span id="EndTime"></span>End of the data slice that was consumed or produced by this step (UTC). NULL means the slice is open-ended (ongoing online processing).
 | - |

<span id="ProcessingStep"></span>

### ProcessingStep

Records a single data-transformation step (outlier removal, interpolation, smoothing, aggregation, etc.) applied to one or more time series. Each row captures what was done, when, by whom, and with what parameters. The ProcessingLineage table links ProcessingStep rows to their input and output Channel entries, forming the full processing provenance graph.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| ProcessingStep_ID | INT **(PK)** | - | ✓ | <span id="ProcessingStep_ID"></span>Surrogate primary key | - |
| Name | NVARCHAR(200) | - | ✓ | <span id="Name"></span>Human-readable name for this processing step | - |
| Description | NVARCHAR(MAX) | - |  | <span id="Description"></span>Free-text description of what this step does and why it was applied | - |
| MethodName | NVARCHAR(200) | - |  | <span id="MethodName"></span>Machine-readable method identifier (e.g. 'outlier_removal', 'linear_interpolation'). Maps to a metEAUdata processing function name. | - |
| MethodVersion | NVARCHAR(100) | - |  | <span id="MethodVersion"></span>Version of the method or library used (e.g. 'meteaudata 0.5.1') | - |
| OperationKind_ID | INT | - |  | <span id="OperationKind_ID"></span>Category of operation this step performs (FK to OperationKind lookup). One step = one OperationKind.
 | FK → [OperationKind.OperationKind_ID](#OperationKind) |
| MethodParameters | NVARCHAR(MAX) | - |  | <span id="MethodParameters"></span>JSON blob of method parameters (e.g. '{"window": 5, "threshold": 3.0}') | - |
| ExecutedDateTime | DATETIME2(7) | - |  | <span id="ExecutedDateTime"></span>UTC timestamp when this processing step was executed | - |
| ExecutedByPerson_ID | INT | - |  | <span id="ExecutedByPerson_ID"></span>Person who ran or triggered this processing step. NULL for automated/unattended runs. | FK → [Person.Person_ID](#Person) |
| Dataset_ID | INT | - |  | <span id="Dataset_ID"></span>The Dataset this processing step belongs to. NULL for steps that operate on a single channel without a named analysis context. Required for multivariate steps that consume or produce multiple channels.
 | FK → [Dataset.Dataset_ID](#Dataset) |

<span id="QualityCode"></span>

### QualityCode

Controlled dictionary of quality flags for measurements. IsUsable indicates whether the value should be included in downstream analysis.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| QualityCode_ID | INT **(PK)** | - | ✓ | <span id="QualityCode_ID"></span>Surrogate primary key, manually assigned | - |
| Name | NVARCHAR(50) | - | ✓ | <span id="Name"></span>Short code name (e.g. 'Accepted', 'BelowLoD') | - |
| Description | NVARCHAR(200) | - |  | <span id="Description"></span>Explanation of what this quality code means | - |
| IsUsable | BIT | - | ✓ | <span id="IsUsable"></span>Whether a value carrying this code should be included in analysis. true = value is fit for use; false = value must be excluded or treated specially.
 | Default: `True` |

<span id="ReviewStatus"></span>

### ReviewStatus

Controlled dictionary of the institutional review/approval state of a single lab measurement. Point-level, parallel to QualityCode: it records whether a designated reviewer has approved or rejected an individual LabAnalysis point, not a series-level property. The lab workflow is single-round, single-reviewer; corrections are recorded as a new replicate, and AuditLog captures amendment history.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| ReviewStatus_ID | INT **(PK)** | - | ✓ | <span id="ReviewStatus_ID"></span>Surrogate primary key, manually assigned | - |
| Name | NVARCHAR(50) | - | ✓ | <span id="Name"></span>Short status name (e.g. 'Pending', 'Approved', 'Rejected') | - |
| Description | NVARCHAR(200) | - |  | <span id="Description"></span>Explanation of what this review status means | - |

<span id="Sample"></span>

### Sample

A discrete physical sample collected at a sampling location or prepared in a laboratory. Supports field samples, calibration standards, blanks, and derived sub-samples via ParentSample_ID.


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Sample_ID | INT **(PK)** | - | ✓ | <span id="Sample_ID"></span>Surrogate primary key | - |
| ParentSample_ID | INT | - |  | <span id="ParentSample_ID"></span>Parent sample this was derived from (e.g., an aliquot of a master standard). NULL for primary samples. | FK → [Sample.Sample_ID](#Sample) |
| SampleKind_ID | INT | - |  | <span id="SampleKind_ID"></span>Analytical role of the sample (FK to SampleKind lookup table, e.g. Field/Blank/Standard) | FK → [SampleKind.SampleKind_ID](#SampleKind) |
| SampleMaterialKind_ID | INT | - |  | <span id="SampleMaterialKind_ID"></span>Physical matrix/material of the sample (FK to SampleMaterialKind lookup table, e.g. wastewater/mixed liquor) | FK → [SampleMaterialKind.SampleMaterialKind_ID](#SampleMaterialKind) |
| SamplingPoint_ID | INT | - | ✓ | <span id="SamplingPoint_ID"></span>Sampling location where the sample was collected or prepared | FK → [SamplingPoint.SamplingPoint_ID](#SamplingPoint) |
| SampledByPerson_ID | INT | - |  | <span id="SampledByPerson_ID"></span>Person who collected the sample | FK → [Person.Person_ID](#Person) |
| Campaign_ID | INT | - |  | <span id="Campaign_ID"></span>Campaign this sample belongs to | FK → [Campaign.Campaign_ID](#Campaign) |
| SampleDateTimeStart | DATETIME2(7) | - | ✓ | <span id="SampleDateTimeStart"></span>Date and time sampling began (UTC) | - |
| SampleDateTimeEnd | DATETIME2(7) | - |  | <span id="SampleDateTimeEnd"></span>Date and time sampling ended (UTC). NULL for instantaneous grab samples. | - |
| SampleCollectionKind_ID | INT | - |  | <span id="SampleCollectionKind_ID"></span>Method of sample collection (FK to SampleCollectionKind lookup table) | FK → [SampleCollectionKind.SampleCollectionKind_ID](#SampleCollectionKind) |
| SampleEquipment_ID | INT | - |  | <span id="SampleEquipment_ID"></span>Equipment used to collect the sample (e.g., auto-sampler) | FK → [Equipment.Equipment_ID](#Equipment) |
| Replicate | INT | - | ✓ | <span id="Replicate"></span>Field replicate number (1 = the primary sample, 2+ = further samples taken at the same point and time). Distinct from LabAnalysis.Replicate, which counts repeat analyses of one physical sample.
 | Default: `1` |
| Description | NVARCHAR(500) | - |  | <span id="Description"></span>Additional notes about the sample | - |

<span id="SampleCollectionKind"></span>

### SampleCollectionKind

Controlled vocabulary describing how a sample was collected. Referenced by Sample.SampleCollectionKind_ID.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| SampleCollectionKind_ID | INT **(PK)** | - | ✓ | <span id="SampleCollectionKind_ID"></span>Surrogate primary key | - |
| Name | NVARCHAR(50) | - | ✓ | <span id="Name"></span>Collection kind name (e.g. 'Grab', 'Composite24h') | - |
| Description | NVARCHAR(200) | - |  | <span id="Description"></span>Explanation of the collection kind | - |

<span id="SampleKind"></span>

### SampleKind

Controlled vocabulary describing the nature of a physical sample. Referenced by Sample.SampleKind_ID.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| SampleKind_ID | INT **(PK)** | - | ✓ | <span id="SampleKind_ID"></span>Surrogate primary key | - |
| Name | NVARCHAR(50) | - | ✓ | <span id="Name"></span>Sample kind name (e.g. 'Field', 'Blank') | - |
| Description | NVARCHAR(200) | - |  | <span id="Description"></span>Explanation of what this sample kind represents | - |

<span id="SampleMaterialKind"></span>

### SampleMaterialKind

Controlled vocabulary describing the physical matrix (material) of a sample, independent of its analytical role (see SampleKind). Referenced by Sample.SampleMaterialKind_ID. Seeded with common wastewater-treatment-plant matrices; extend via the CRUD UI as needed.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| SampleMaterialKind_ID | INT **(PK)** | - | ✓ | <span id="SampleMaterialKind_ID"></span>Surrogate primary key | - |
| Name | NVARCHAR(50) | - | ✓ | <span id="Name"></span>Sample material name (e.g. 'mixed liquor', 'tap water') | - |
| Description | NVARCHAR(200) | - |  | <span id="Description"></span>Explanation of what this sample material represents | - |

<span id="SamplingPoint"></span>

### SamplingPoint

Stores the identification, specific geographical coordinates (Latitude/Longitude/GPS), and description of a particular spot where a sample or measurement is taken


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| SamplingPoint_ID | INT **(PK)** | - | ✓ | <span id="SamplingPoint_ID"></span>Surrogate primary key | - |
| Site_ID | INT | - | ✓ | <span id="Site_ID"></span>Site this sampling point belongs to | FK → [Site.Site_ID](#Site) |
| SamplingPoint | NVARCHAR(100) | - | ✓ | <span id="SamplingPoint"></span>Name of the sampling location. For example: 'Inlet of R100', 'Clarifier outflow mixing tank' or 'upstream of primary settler' | - |
| LatitudeWGS84 | FLOAT | - |  | <span id="LatitudeWGS84"></span>WGS84 latitude in decimal degrees. For example: 45.9070 | - |
| LongitudeWGS84 | FLOAT | - |  | <span id="LongitudeWGS84"></span>WGS84 longitude in decimal degrees. For example: -73.7833 | - |
| Description | NVARCHAR(MAX) | - |  | <span id="Description"></span>Description of the sampling point | - |
| PicturePath | NVARCHAR(500) | - |  | <span id="PicturePath"></span>Relative path to the sampling point reference photo on disk (e.g. sampling_points/42_abc123.jpg) | - |
| ValidFrom | DATETIME2(7) | - |  | <span id="ValidFrom"></span>Date from which this sampling point record is considered valid (UTC). NULL means valid from the beginning of records. | - |
| ValidTo | DATETIME2(7) | - |  | <span id="ValidTo"></span>Date until which this sampling point record is valid (UTC). NULL means currently active. | - |
| ProcessUnit_ID | INT | - |  | <span id="ProcessUnit_ID"></span>Optional process unit this sampling point is located within (e.g. a tank or zone) | FK → [ProcessUnit.ProcessUnit_ID](#ProcessUnit) |
| CreatedByCampaign_ID | INT | - |  | <span id="CreatedByCampaign_ID"></span>Campaign during which this sampling point was first established (if applicable) | FK → [Campaign.Campaign_ID](#Campaign) |

<span id="SchemaVersion"></span>

### SchemaVersion

Tracks which schema versions have been applied to this database instance


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| VersionID | INT **(PK)** | - | ✓ | <span id="VersionID"></span>Surrogate primary key | - |
| Version | NVARCHAR(20) | - | ✓ | <span id="Version"></span>Schema version string (e.g. 1.0.1) | - |
| AppliedDateTime | DATETIME2(7) | - | ✓ | <span id="AppliedDateTime"></span>UTC datetime when this migration was applied (stored in UTC by convention) | Default: `CURRENT_TIMESTAMP` |
| Description | NVARCHAR(500) | - |  | <span id="Description"></span>Human-readable description of what this migration does | - |
| MigrationScript | NVARCHAR(200) | - |  | <span id="MigrationScript"></span>Filename of the migration script that was applied | - |

<span id="SignalInterface"></span>

### SignalInterface

A software or physical interface connected to the Data Acquisition System where data from one or more instruments is displayed or logged. Typically, each equipment vendor maintains their own interface. Examples: a Hach SC1000 controller, a WTW IQ Sensor Net bus, a monEAU/TresCON basestation, a Logix5000 PLC. A SignalInterface owns one or more SignalInterfacePorts and is the stable anchor that Channels reference via tag name — so tags keep working when the wiring to individual Equipment changes.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| SignalInterface_ID | INT **(PK)** | - | ✓ | <span id="SignalInterface_ID"></span>Surrogate primary key | - |
| DataAcquisitionSystem_ID | INT | - | ✓ | <span id="DataAcquisitionSystem_ID"></span>The data acquisition system that reads data from this interface | FK → [DataAcquisitionSystem.DataAcquisitionSystem_ID](#DataAcquisitionSystem) |
| Name | NVARCHAR(200) | - | ✓ | <span id="Name"></span>Human-readable unique name of this interface (e.g. 'pileaute_plc', 'monEAU01_sc1000') | - |
| Manufacturer | NVARCHAR(100) | - |  | <span id="Manufacturer"></span>Manufacturer (e.g. 'Rockwell', 'Hach', 'WTW') | - |
| Model | NVARCHAR(100) | - |  | <span id="Model"></span>Model designation (e.g. 'Logix5000', 'SC1000', 'TresCON') | - |
| SerialNumber | NVARCHAR(100) | - |  | <span id="SerialNumber"></span>Serial number if known | - |
| Description | NVARCHAR(MAX) | - |  | <span id="Description"></span>Free-text notes about this interface | - |
| IsActive | BIT | - | ✓ | <span id="IsActive"></span>Whether this interface is currently in service | Default: `True` |

<span id="SignalInterfacePort"></span>

### SignalInterfacePort

A specific physical or logical connection point on a Signal Interface — for example, an analog input slot on a controller, a serial port on a basestation, or a probe socket on a sensor hub. This represents exactly where an instrument is wired in. Ports are optional: if you have not yet traced the wiring, a Channel can exist with no port assigned and is still addressable by its tag name alone. Multiple sensors can share one port (multiplexer case), distinguished by a gating note.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| SignalInterfacePort_ID | INT **(PK)** | - | ✓ | <span id="SignalInterfacePort_ID"></span>Surrogate primary key | - |
| SignalInterface_ID | INT | - | ✓ | <span id="SignalInterface_ID"></span>The interface this port belongs to | FK → [SignalInterface.SignalInterface_ID](#SignalInterface) |
| PortIdentifier | NVARCHAR(100) | - | ✓ | <span id="PortIdentifier"></span>Identifier used by the interface (e.g. 'slot6/Ch0', 'COM2', 'ProbeA') | - |
| Description | NVARCHAR(MAX) | - |  | <span id="Description"></span>Free-text notes about this port | - |
| IsActive | BIT | - | ✓ | <span id="IsActive"></span>Whether this port is currently in use | Default: `True` |

<span id="Site"></span>

### Site

Stores general site information, including address, site type, and a link to the associated watershed


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Site_ID | INT **(PK)** | - | ✓ | <span id="Site_ID"></span>A unique ID is generated automatically by the database | - |
| Watershed_ID | INT | - |  | <span id="Watershed_ID"></span>Linked to the Watershed table | FK → [Watershed.Watershed_ID](#Watershed) |
| Name | NVARCHAR(100) | - |  | <span id="Name"></span>Name of the site | - |
| SiteKind_ID | INT | - |  | <span id="SiteKind_ID"></span>Kind of the site via SiteKind lookup | FK → [SiteKind.SiteKind_ID](#SiteKind) |
| Description | NVARCHAR(MAX) | - |  | <span id="Description"></span>Description of the site | - |
| LatitudeWGS84 | FLOAT | - |  | <span id="LatitudeWGS84"></span>Latitude of the site in WGS84 decimal degrees | - |
| LongitudeWGS84 | FLOAT | - |  | <span id="LongitudeWGS84"></span>Longitude of the site in WGS84 decimal degrees | - |
| StreetNumber | NVARCHAR(100) | - |  | <span id="StreetNumber"></span>Address: number of the street | - |
| StreetName | NVARCHAR(100) | - |  | <span id="StreetName"></span>Address: name of the street | - |
| City | NVARCHAR(255) | - |  | <span id="City"></span>Address: name of the city | - |
| PostCode | NVARCHAR(100) | - |  | <span id="PostCode"></span>Address: postal code | - |
| Province | NVARCHAR(255) | - |  | <span id="Province"></span>Address: name of the province | - |
| Country | NVARCHAR(255) | - |  | <span id="Country"></span>Address: name of the country | - |

<span id="SiteKind"></span>

### SiteKind

Controlled vocabulary of site kinds (e.g. Wastewater Treatment Plant, River, Pilot Plant)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| SiteKind_ID | INT **(PK)** | - | ✓ | <span id="SiteKind_ID"></span>Primary key for the SiteKind lookup | - |
| Name | NVARCHAR(100) | - | ✓ | <span id="Name"></span>Name of the site kind (e.g. Wastewater Treatment Plant) | - |
| Description | NVARCHAR(300) | - |  | <span id="Description"></span>Detailed description of the site kind | - |

<span id="Stream"></span>

### Stream

The stored supertype for any time-series identity — either a sensor Channel or a lab AnalysisSeries. Every Channel and every AnalysisSeries owns exactly one Stream row (via Stream_ID), and the subtypes share Stream_ID as their own primary key (table-per-type inheritance, shared PK). Tables that attach to "any stream" (Annotation, ProcessingLineage input edges) carry a single Stream_ID FK rather than a Channel/AnalysisSeries XOR pair. The StreamKind_ID discriminator enables fast "sensor vs lab" filtering without joining the subtype tables. Subtype-specific columns stay on the subtype tables; this supertype is deliberately minimal.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Stream_ID | INT **(PK)** | - | ✓ | <span id="Stream_ID"></span>Surrogate primary key — the universal identifier of any measurement stream. Shared down to the Channel and AnalysisSeries subtypes as their own primary key.
 | - |
| StreamKind_ID | INT | - | ✓ | <span id="StreamKind_ID"></span>Discriminator identifying the stream subtype (Sensor=Channel, Lab=AnalysisSeries). Enables fast "sensor vs lab" filtering without joining to the subtype tables.
 | FK → [StreamKind.StreamKind_ID](#StreamKind) |

<span id="StreamKind"></span>

### StreamKind

Controlled vocabulary discriminating the subtype of a Stream: a sensor measurement stream (Channel) or a laboratory measurement stream (AnalysisSeries). Used as the StreamKind_ID discriminator on Stream to enable fast "sensor vs lab" filtering without joining the subtype tables.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| StreamKind_ID | INT **(PK)** | - | ✓ | <span id="StreamKind_ID"></span>Surrogate primary key, manually assigned | - |
| Name | NVARCHAR(50) | - | ✓ | <span id="Name"></span>Short code name (e.g. 'Sensor', 'Lab') | - |
| Description | NVARCHAR(200) | - |  | <span id="Description"></span>Explanation of what this stream kind means | - |

<span id="Unit"></span>

### Unit

Stores the SI units of measurement (or other relevant units) corresponding to the parameters (e.g., mg/L, g/L, s)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Unit_ID | INT **(PK)** | - | ✓ | <span id="Unit_ID"></span>A unique ID is generated automatically by the database | - |
| Unit | NVARCHAR(100) | - |  | <span id="Unit"></span>SI-units only | - |
| QUDT_IRI | NVARCHAR(256) | - |  | <span id="QUDT_IRI"></span>QUDT ontology IRI for the unit (e.g. https://qudt.org/vocab/unit/MilliGM-PER-L) | - |
| UnitVector | NVARCHAR(64) | - |  | <span id="UnitVector"></span>SI unit dimension vector [m, kg, s, A, K, mol, cd] as a comma-separated string (e.g. 0,1,-3,0,0,0,0) | - |
| SI_Multiplier | FLOAT | - |  | <span id="SI_Multiplier"></span>Multiply value by this to obtain SI quantity (e.g. 0.001 for mg/L → kg/m³). NULL = no linear SI conversion. | - |
| SI_Offset | FLOAT | - |  | <span id="SI_Offset"></span>Add this after applying SI_Multiplier (e.g. 273.15 for °C → K). NULL treated as 0. | - |

<span id="UserAccount"></span>

### UserAccount

Application user accounts for API authentication.


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| UserAccount_ID | INT **(PK)** | - | ✓ | <span id="UserAccount_ID"></span>Surrogate primary key | - |
| Email | NVARCHAR(255) | - | ✓ | <span id="Email"></span>Unique e-mail address used for login | - |
| FullName | NVARCHAR(255) | - | ✓ | <span id="FullName"></span>Display name of the user | - |
| PasswordHash | NVARCHAR(255) | - | ✓ | <span id="PasswordHash"></span>PBKDF2-SHA256 password hash (pbkdf2_sha256$iters$salt$digest) | - |
| IsActive | BIT | - | ✓ | <span id="IsActive"></span>Whether the account is enabled | Default: `True` |
| IsVerified | BIT | - | ✓ | <span id="IsVerified"></span>Whether the e-mail address has been verified | Default: `True` |
| CreatedAt | DATETIME2(7) | - | ✓ | <span id="CreatedAt"></span>UTC timestamp when the account was created | Default: `SYSUTCDATETIME()` |
| UpdatedAt | DATETIME2(7) | - | ✓ | <span id="UpdatedAt"></span>UTC timestamp of the last profile update | Default: `SYSUTCDATETIME()` |

<span id="Value"></span>

### Value

Scalar payload for a single Observation. One row per Observation of DataType='Scalar'. Channel and Timestamp are resolved via the Observation table.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Observation_ID | INT **(PK)** | - | ✓ | <span id="Observation_ID"></span>Links this scalar value to its Observation (channel + timestamp) | FK → [Observation.Observation_ID](#Observation) |
| Value | FLOAT | - |  | <span id="Value"></span>Measured scalar value | - |
| QualityCode | INT | - |  | <span id="QualityCode"></span>Quality flag for this scalar measurement (references QualityCode.QualityCode_ID) | - |

<span id="ValueBin"></span>

### ValueBin

Individual bins on a ValueBinningAxis. The fields populated on each bin depend on the parent axis BinMode: 'interval' bins have LowerBound and UpperBound only; 'interval_with_nominal' bins have all three fields; 'nominal' bins have NominalValue only.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| ValueBin_ID | INT **(PK)** | - | ✓ | <span id="ValueBin_ID"></span>Surrogate primary key | - |
| ValueBinningAxis_ID | INT | - | ✓ | <span id="ValueBinningAxis_ID"></span>References the parent binning axis | FK → [ValueBinningAxis.ValueBinningAxis_ID](#ValueBinningAxis) |
| BinIndex | INT | - | ✓ | <span id="BinIndex"></span>0-based ordinal position of this bin within its axis | - |
| LowerBound | FLOAT | - |  | <span id="LowerBound"></span>Inclusive lower edge of this bin in the axis unit; NULL for 'nominal' mode bins | - |
| UpperBound | FLOAT | - |  | <span id="UpperBound"></span>Exclusive upper edge of this bin in the axis unit; must be greater than LowerBound when set; NULL for 'nominal' mode bins | - |
| NominalValue | FLOAT | - |  | <span id="NominalValue"></span>Nominal (center or exact) value of this bin in the axis unit; NULL for 'interval' mode bins | - |

<span id="ValueBinningAxis"></span>

### ValueBinningAxis

Defines a named measurement axis for binned data (e.g. wavelength, particle size, velocity), linking to the Unit table for axis units


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| ValueBinningAxis_ID | INT **(PK)** | - | ✓ | <span id="ValueBinningAxis_ID"></span>Surrogate primary key | - |
| Name | NVARCHAR(200) | - | ✓ | <span id="Name"></span>Human-readable name identifying this axis configuration (e.g. 'S::CAN spectro::lyser UV-Vis') | - |
| Description | NVARCHAR(500) | - |  | <span id="Description"></span>Optional description of this axis | - |
| NumberOfBins | INT | - | ✓ | <span id="NumberOfBins"></span>Total number of bins defined on this axis | - |
| Unit_ID | INT | - | ✓ | <span id="Unit_ID"></span>Physical unit of the axis coordinates (e.g. nm, µm, m/s) — distinct from the measured value unit stored in Channel | FK → [Unit.Unit_ID](#Unit) |
| BinKind_ID | INT | - | ✓ | <span id="BinKind_ID"></span>Declares how all bins on this axis are specified; FK to BinKind (1=interval, 2=interval_with_nominal, 3=nominal) | FK → [BinKind.BinKind_ID](#BinKind)<br>Default: `1` |

<span id="ValueImage"></span>

### ValueImage

Image measurement payload for a single Observation. One row per Observation of DataType='Image'. Stores metadata about image dimensions, format, and storage location. Channel and Timestamp are resolved via the Observation table.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Observation_ID | INT **(PK)** | - | ✓ | <span id="Observation_ID"></span>Links this image to its Observation (channel + timestamp). Acts as both PK and FK — one image per observation.
 | FK → [Observation.Observation_ID](#Observation) |
| ImageWidth | INT | - | ✓ | <span id="ImageWidth"></span>Width of the image in pixels | - |
| ImageHeight | INT | - | ✓ | <span id="ImageHeight"></span>Height of the image in pixels | - |
| NumberOfChannels | INT | - | ✓ | <span id="NumberOfChannels"></span>Number of color channels (e.g. 3 for RGB, 1 for grayscale) | Default: `3` |
| ImageFormat | NVARCHAR(20) | - | ✓ | <span id="ImageFormat"></span>Image file format (e.g. PNG, TIFF, JPEG) | - |
| FileSizeBytes | BIGINT | - |  | <span id="FileSizeBytes"></span>File size in bytes | - |
| StorageBackend | NVARCHAR(50) | - | ✓ | <span id="StorageBackend"></span>Storage backend type (e.g. FileSystem, S3, Azure Blob) | Default: `'FileSystem'` |
| StoragePath | NVARCHAR(1000) | - | ✓ | <span id="StoragePath"></span>Full path or URI to the stored image file | - |
| Thumbnail | VARBINARY(MAX) | - |  | <span id="Thumbnail"></span>Optional thumbnail image stored inline as binary | - |
| QualityCode | INT | - |  | <span id="QualityCode"></span>Quality flag for this image | - |

<span id="ValueKind"></span>

### ValueKind

Controlled vocabulary defining the shape of stored measurement values (Scalar, Vector, Matrix, Image)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| ValueKind_ID | INT **(PK)** | - | ✓ | <span id="ValueKind_ID"></span>Surrogate primary key | - |
| Name | NVARCHAR(50) | - | ✓ | <span id="Name"></span>Human-readable name of the value kind (Scalar, Vector, Matrix, or Image) | - |
| Description | NVARCHAR(200) | - |  | <span id="Description"></span>Explanation of what this value kind represents structurally | - |

<span id="ValueMatrix"></span>

### ValueMatrix

One row per (observation, row-bin, col-bin) for 2D matrix data. Supports joint distributions such as particle size-velocity. Channel and Timestamp are resolved via the Observation table.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Observation_ID | INT **(PK)** | - | ✓ | <span id="Observation_ID"></span>References the Observation (channel + timestamp) for this measurement | FK → [Observation.Observation_ID](#Observation) |
| RowValueBin_ID | INT **(PK)** | - | ✓ | <span id="RowValueBin_ID"></span>References the bin on the row axis (AxisRole=0) | FK → [ValueBin.ValueBin_ID](#ValueBin) |
| ColValueBin_ID | INT **(PK)** | - | ✓ | <span id="ColValueBin_ID"></span>References the bin on the column axis (AxisRole=1) | FK → [ValueBin.ValueBin_ID](#ValueBin) |
| Value | FLOAT | - |  | <span id="Value"></span>Measured value at this (row-bin, col-bin) cell | - |
| QualityCode | INT | - |  | <span id="QualityCode"></span>Quality flag for this measurement | - |

<span id="ValueVector"></span>

### ValueVector

One row per (observation, bin) for vector (spectral) data. Unifies spectra, particle size distributions, and any other 1D distribution over a physical axis. Channel and Timestamp are resolved via the Observation table.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Observation_ID | INT **(PK)** | - | ✓ | <span id="Observation_ID"></span>References the Observation (channel + timestamp) for this measurement | FK → [Observation.Observation_ID](#Observation) |
| ValueBin_ID | INT **(PK)** | - | ✓ | <span id="ValueBin_ID"></span>References the bin (and through it, the axis) for this value | FK → [ValueBin.ValueBin_ID](#ValueBin) |
| Value | FLOAT | - |  | <span id="Value"></span>Measured value at this bin | - |
| QualityCode | INT | - |  | <span id="QualityCode"></span>Quality flag for this measurement | - |

<span id="Watershed"></span>

### Watershed

Stores general information about the watershed area, including surface area, concentration time, and impervious surface percentage


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Watershed_ID | INT **(PK)** | - | ✓ | <span id="Watershed_ID"></span>Linked to the Watershed table | - |
| Name | NVARCHAR(100) | - |  | <span id="Name"></span>Name of the watershed | - |
| Description | NVARCHAR(MAX) | - |  | <span id="Description"></span>Description of the watershed | - |
| SurfaceArea | REAL | - |  | <span id="SurfaceArea"></span>Surface area of the watershed [ha] | - |
| ConcentrationTime | INT | - |  | <span id="ConcentrationTime"></span>Concentration time in minutes [min] | - |
| ImperviousSurface | REAL | - |  | <span id="ImperviousSurface"></span>Percentage of the impervious surface of the watershed in percentage [%] | - |
| ParentWatershed_ID | INT | - |  | <span id="ParentWatershed_ID"></span>Optional parent watershed for nested/hierarchical watershed relationships | FK → [Watershed.Watershed_ID](#Watershed) |
| GeometryGeoJSON | NVARCHAR(MAX) | - |  | <span id="GeometryGeoJSON"></span>GeoJSON string representing the watershed boundary (Polygon or MultiPolygon only) | - |