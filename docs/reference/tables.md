# Database Tables

This documentation is auto-generated from dictionary.json.


## Tables


<span id="Annotation"></span>

### Annotation

Human-authored annotations on time series data. Each annotation applies to a single Channel entry (one measurement channel) over a time range. Multiple annotations can overlap on the same range. EndTime=NULL means either a point annotation or an ongoing situation.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Annotation_ID | INT **(PK)** | - | ✓ | <span id="Annotation_ID"></span>Primary key, auto-incremented | - |
| Channel_ID | INT | - | ✓ | <span id="Channel_ID"></span>The time series this annotation applies to | FK → [Channel.Channel_ID](#Channel) |
| AnnotationType_ID | INT | - | ✓ | <span id="AnnotationType_ID"></span>What kind of annotation this is | FK → [AnnotationType.AnnotationType_ID](#AnnotationType) |
| StartTime | DATETIME2(7) | - | ✓ | <span id="StartTime"></span>Start of the annotated time range | - |
| EndTime | DATETIME2(7) | - |  | <span id="EndTime"></span>End of the annotated range. NULL = point annotation or ongoing | - |
| AuthorPerson_ID | INT | - |  | <span id="AuthorPerson_ID"></span>Person who created this annotation | FK → [Person.Person_ID](#Person) |
| Campaign_ID | INT | - |  | <span id="Campaign_ID"></span>Campaign this annotation is associated with, if any | FK → [Campaign.Campaign_ID](#Campaign) |
| EquipmentEvent_ID | INT | - |  | <span id="EquipmentEvent_ID"></span>Equipment event that caused this annotation, if any | FK → [EquipmentEvent.EquipmentEvent_ID](#EquipmentEvent) |
| Title | NVARCHAR(200) | - |  | <span id="Title"></span>Short title for the annotation | - |
| Comment | NVARCHAR(MAX) | - |  | <span id="Comment"></span>Detailed free-text comment | - |
| CreatedDateTime | DATETIME2(7) | - | ✓ | <span id="CreatedDateTime"></span>When this annotation was created | Default: `CURRENT_TIMESTAMP` |
| ModifiedDateTime | DATETIME2(7) | - |  | <span id="ModifiedDateTime"></span>When this annotation was last modified | - |
| Observation_ID | INT | - |  | <span id="Observation_ID"></span>Optional link to a specific Observation for point-level annotations (e.g., 'wrong focal length on this image'). When NULL, the annotation applies to the time range [StartTime, EndTime] on the channel. When set, StartTime should match Observation.Timestamp.
 | FK → [Observation.Observation_ID](#Observation) |

<span id="AnnotationType"></span>

### AnnotationType

Lookup table defining the kinds of annotations that can be applied to time series data. Each type has a display color for UI rendering.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| AnnotationType_ID | INT **(PK)** | - | ✓ | <span id="AnnotationType_ID"></span>Primary key, manually assigned | - |
| AnnotationTypeName | NVARCHAR(100) | - | ✓ | <span id="AnnotationTypeName"></span>Human-readable name of the annotation type | - |
| Description | NVARCHAR(500) | - |  | <span id="Description"></span>Explanation of when to use this annotation type | - |
| Color | NVARCHAR(7) | - |  | <span id="Color"></span>Hex color code for UI rendering, e.g. '#FF6B6B' | - |

<span id="Campaign"></span>

### Campaign

A named collection of measurement activities at a site, classified by type (Experiment, Operations, Commissioning). Supersedes Project for all organisational grouping.


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Campaign_ID | INT **(PK)** | - | ✓ | <span id="Campaign_ID"></span>Surrogate primary key | - |
| CampaignType_ID | INT | - | ✓ | <span id="CampaignType_ID"></span>Type of campaign (Experiment, Operations, Commissioning) | FK → [CampaignType.CampaignType_ID](#CampaignType) |
| Site_ID | INT | - | ✓ | <span id="Site_ID"></span>Site where the campaign is conducted | FK → [Site.Site_ID](#Site) |
| Name | NVARCHAR(200) | - | ✓ | <span id="Name"></span>Human-readable name for the campaign | - |
| Description | NVARCHAR(2000) | - |  | <span id="Description"></span>Detailed description of the campaign objectives and scope | - |
| CampaignStartDateTime | DATETIME2(7) | - |  | <span id="CampaignStartDateTime"></span>Date and time the campaign began (UTC) | - |
| CampaignEndDateTime | DATETIME2(7) | - |  | <span id="CampaignEndDateTime"></span>Date and time the campaign ended (UTC); NULL if ongoing | - |

<span id="CampaignEquipment"></span>

### CampaignEquipment

Junction table: equipment deployed during a campaign.


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Campaign_ID | INT **(PK)** | - | ✓ | <span id="Campaign_ID"></span>Campaign using this equipment | FK → [Campaign.Campaign_ID](#Campaign) |
| Equipment_ID | INT **(PK)** | - | ✓ | <span id="Equipment_ID"></span>Equipment deployed during the campaign | FK → [Equipment.Equipment_ID](#Equipment) |
| Role | NVARCHAR(100) | - |  | <span id="Role"></span>Role of this equipment in the campaign (e.g., 'Primary sensor', 'Auto-sampler') | - |

<span id="CampaignSamplingLocation"></span>

### CampaignSamplingLocation

Junction table: sampling locations actively monitored during a campaign.


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Campaign_ID | INT **(PK)** | - | ✓ | <span id="Campaign_ID"></span>Campaign using this sampling location | FK → [Campaign.Campaign_ID](#Campaign) |
| SamplingPoint_ID | INT **(PK)** | - | ✓ | <span id="SamplingPoint_ID"></span>Sampling location used by the campaign | FK → [SamplingPoint.SamplingPoint_ID](#SamplingPoint) |
| Role | NVARCHAR(100) | - |  | <span id="Role"></span>Role of this location in the campaign (e.g., 'Inlet', 'Reference') | - |

<span id="CampaignType"></span>

### CampaignType

Lookup table classifying the nature of a Campaign (Experiment, Operations, Commissioning)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| CampaignType_ID | INT **(PK)** | - | ✓ | <span id="CampaignType_ID"></span>Surrogate primary key | - |
| CampaignType_Name | NVARCHAR(100) | - | ✓ | <span id="CampaignType_Name"></span>Name of the campaign type. Controlled vocabulary: Experiment, Operations, Commissioning | - |

<span id="Channel"></span>

### Channel

Invariant descriptor for a measurement stream (sensor channel). Each row identifies a unique (SignalPort, Parameter, DataProvenance, ProcessingDegree) combination. A Channel is created once and never changes — equipment swaps and sensor relocations are tracked on the SignalPort via SignalPortEquipmentHistory and SignalPortLocationHistory, leaving the Channel_ID stable. Lab sample results are stored in LabAnalysis + LabValue (not in Channel).



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Channel_ID | INT **(PK)** | - | ✓ | <span id="Channel_ID"></span>Surrogate primary key | - |
| SignalPort_ID | INT | - | ✓ | <span id="SignalPort_ID"></span>The SignalPort (stable signal identity) that this measurement stream belongs to. Replaces Equipment_ID — equipment that produces data is tracked via SignalPortEquipmentHistory, allowing probes to be swapped without breaking the Channel.
 | FK → [SignalPort.SignalPort_ID](#SignalPort) |
| Parameter_ID | INT | - |  | <span id="Parameter_ID"></span>Measured analyte or parameter (e.g. TSS, pH) | FK → [Parameter.Parameter_ID](#Parameter) |
| DataProvenance_ID | INT | - |  | <span id="DataProvenance_ID"></span>How this data was produced (Sensor=1, Laboratory=2, Manual Entry=3, Model Output=4, External Source=5, Forecast=6)
 | FK → [DataProvenance.DataProvenance_ID](#DataProvenance) |
| ProcessingDegree_ID | INT | - |  | <span id="ProcessingDegree_ID"></span>Level of processing applied to this time series (FK to ProcessingDegree lookup). Ground truth is the DataLineage graph; this field exists for fast filtering. Set once at row creation — if the processing degree changes, a new Channel row is created. Default 1 = Raw.
 | FK → [ProcessingDegree.ProcessingDegree_ID](#ProcessingDegree)<br>Default: `1` |
| ValueType_ID | INT | - | ✓ | <span id="ValueType_ID"></span>Shape of stored values (1=Scalar, 2=Vector, 3=Matrix, 4=Image) | FK → [ValueType.ValueType_ID](#ValueType)<br>Default: `1` |

<span id="ChannelAxis"></span>

### ChannelAxis

Junction table linking a Channel measurement series to its binning axis or axes. AxisRole=0 is the single axis for a Vector, or the row axis for a Matrix; AxisRole=1 is the column axis for a Matrix.


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Channel_ID | INT **(PK)** | - | ✓ | <span id="Channel_ID"></span>References the measurement channel | FK → [Channel.Channel_ID](#Channel) |
| AxisRole | INT **(PK)** | - | ✓ | <span id="AxisRole"></span>Dimension role: 0 = primary/row axis, 1 = secondary/column axis (Matrix only) | - |
| ValueBinningAxis_ID | INT | - | ✓ | <span id="ValueBinningAxis_ID"></span>References the binning axis for this role | FK → [ValueBinningAxis.ValueBinningAxis_ID](#ValueBinningAxis) |

<span id="ControlLoop"></span>

### ControlLoop

Identity record for a control scheme applied to a process. Describes the controller type and its degradation strategy (FallbackControlLoop_ID chain, or NULL for manual fallback). Temporal configuration (tuning, parameters) lives in ControlLoopApplication. SignalPort membership lives in ControlLoopPort.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| ControlLoop_ID | INT **(PK)** | - | ✓ | <span id="ControlLoop_ID"></span>Surrogate primary key | - |
| Name | NVARCHAR(200) | - | ✓ | <span id="Name"></span>Human-readable name for this control loop | - |
| ControllerType | NVARCHAR(50) | - | ✓ | <span id="ControllerType"></span>Controller algorithm class: PID, PI, P, BangBang, Custom, Manual, MPC, Cascade, Feedforward, etc. | - |
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

Association between a ControlLoop and its SignalPorts, with an explicit role for each port. The unique constraint ensures each port appears at most once per loop. Cascade control is modelled by using the same SignalPort_ID in two different loops with different roles (ManipulatedVariable in outer, SetPoint in inner).



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| ControlLoopPort_ID | INT **(PK)** | - | ✓ | <span id="ControlLoopPort_ID"></span>Surrogate primary key | - |
| ControlLoop_ID | INT | - | ✓ | <span id="ControlLoop_ID"></span>The control loop this association belongs to | FK → [ControlLoop.ControlLoop_ID](#ControlLoop) |
| SignalPort_ID | INT | - | ✓ | <span id="SignalPort_ID"></span>The port participating in this control loop | FK → [SignalPort.SignalPort_ID](#SignalPort) |
| ControlLoopPortRole_ID | INT | - | ✓ | <span id="ControlLoopPortRole_ID"></span>The functional role of this port within the loop | FK → [ControlLoopPortRole.ControlLoopPortRole_ID](#ControlLoopPortRole) |

<span id="ControlLoopPortRole"></span>

### ControlLoopPortRole

Controlled vocabulary for the functional role of a SignalPort within a ControlLoop. 'Other' is an explicit escape hatch for novel control schemes; its use should be accompanied by a description in ControlLoop.Description.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| ControlLoopPortRole_ID | INT **(PK)** | - | ✓ | <span id="ControlLoopPortRole_ID"></span>Surrogate primary key, manually assigned | - |
| Name | NVARCHAR(50) | - | ✓ | <span id="Name"></span>Short name for this role | - |
| Description | NVARCHAR(200) | - |  | <span id="Description"></span>Explanation of the role within a control loop | - |

<span id="DataAcquisitionSystem"></span>

### DataAcquisitionSystem

Represents any upstream system that assigns tags to signals: SCADA servers, PLCs, data loggers, OPC-UA servers, CSV importers, etc. Supports hierarchy via ParentSystem_ID (e.g. plant SCADA → field PLC → sensor module).



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| DataAcquisitionSystem_ID | INT **(PK)** | - | ✓ | <span id="DataAcquisitionSystem_ID"></span>Surrogate primary key | - |
| ParentSystem_ID | INT | - |  | <span id="ParentSystem_ID"></span>Optional parent DAS in a hierarchy (e.g. plant SCADA containing a PLC sub-system) | FK → [DataAcquisitionSystem.DataAcquisitionSystem_ID](#DataAcquisitionSystem) |
| Name | NVARCHAR(200) | - | ✓ | <span id="Name"></span>Human-readable name of the system (e.g. 'Plant SCADA', 'CommCube-A') | - |
| SystemType | NVARCHAR(50) | - |  | <span id="SystemType"></span>Category of system: SCADA, PLC, DataLogger, OPC-UA, CSV, etc. | - |
| Manufacturer | NVARCHAR(100) | - |  | <span id="Manufacturer"></span>Manufacturer or vendor of the system | - |
| Model | NVARCHAR(100) | - |  | <span id="Model"></span>Model name or version of the system | - |
| Description | NVARCHAR(MAX) | - |  | <span id="Description"></span>Free-text notes about this DAS | - |

<span id="DataProvenance"></span>

### DataProvenance

Lookup table describing how a measurement was produced (Sensor, Laboratory, Manual Entry, Model Output, External Source, Forecast)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| DataProvenance_ID | INT **(PK)** | - | ✓ | <span id="DataProvenance_ID"></span>Surrogate primary key | - |
| DataProvenance_Name | NVARCHAR(50) | - | ✓ | <span id="DataProvenance_Name"></span>Name of the provenance. Controlled vocabulary: Sensor, Laboratory, Manual Entry, Model Output, External Source, Forecast | - |

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
| Channel_ID | INT **(PK)** | - | ✓ | <span id="Channel_ID"></span>The channel (signal) included in this dataset | FK → [Channel.Channel_ID](#Channel) |

<span id="Equipment"></span>

### Equipment

Stores information about a specific physical piece of equipment (e.g., serial number, owner, purchase date, storage location). Equipment is linked to measurement streams via SignalPortEquipmentHistory (not directly via Channel), allowing instrument swaps without breaking data continuity.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Equipment_ID | INT **(PK)** | - | ✓ | <span id="Equipment_ID"></span>Surrogate primary key | - |
| EquipmentModel_ID | INT | - |  | <span id="EquipmentModel_ID"></span>Link to the Equipment model table | FK → [EquipmentModel.EquipmentModel_ID](#EquipmentModel) |
| Identifier | NVARCHAR(100) | - |  | <span id="Identifier"></span>Identification name of the equipment | - |
| SerialNumber | NVARCHAR(100) | - |  | <span id="SerialNumber"></span>Serial number of the equipment | - |
| Owner | NVARCHAR(MAX) | - |  | <span id="Owner"></span>Name of the owner of the equipment | - |
| StorageLocation | NVARCHAR(100) | - |  | <span id="StorageLocation"></span>Where the equipment is stored when not deployed | - |
| PurchaseDate | DATE | - |  | <span id="PurchaseDate"></span>Date when the equipment was bought: 'YYYY-MM-DD' | - |
| IsActive | BIT | - | ✓ | <span id="IsActive"></span>Whether this equipment is currently in service. Set to false when decommissioned. Decommissioning should also be recorded as an EquipmentEvent for auditability. Enables fast active/inactive filtering without inspecting SignalPortEquipmentHistory.
 | Default: `True` |

<span id="EquipmentEvent"></span>

### EquipmentEvent

Records a discrete lifecycle event (calibration, maintenance, failure, etc.) that occurred on a specific piece of equipment.


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| EquipmentEvent_ID | INT **(PK)** | - | ✓ | <span id="EquipmentEvent_ID"></span>Surrogate primary key | - |
| Equipment_ID | INT | - | ✓ | <span id="Equipment_ID"></span>Equipment on which the event occurred | FK → [Equipment.Equipment_ID](#Equipment) |
| EquipmentEventType_ID | INT | - | ✓ | <span id="EquipmentEventType_ID"></span>Type of lifecycle event | FK → [EquipmentEventType.EquipmentEventType_ID](#EquipmentEventType) |
| EventDateTimeStart | DATETIME2(7) | - | ✓ | <span id="EventDateTimeStart"></span>Date and time the event began (UTC) | - |
| EventDateTimeEnd | DATETIME2(7) | - |  | <span id="EventDateTimeEnd"></span>Date and time the event ended (UTC). NULL if instantaneous or ongoing. | - |
| PerformedByPerson_ID | INT | - |  | <span id="PerformedByPerson_ID"></span>Person who performed or recorded the event | FK → [Person.Person_ID](#Person) |
| Campaign_ID | INT | - |  | <span id="Campaign_ID"></span>Campaign during which this event occurred (if applicable) | FK → [Campaign.Campaign_ID](#Campaign) |
| Notes | NVARCHAR(MAX) | - |  | <span id="Notes"></span>Free-text notes about the event | - |

<span id="EquipmentEventType"></span>

### EquipmentEventType

Lookup table classifying the type of lifecycle event that occurred on a piece of equipment (Calibration, Maintenance, etc.)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| EquipmentEventType_ID | INT **(PK)** | - | ✓ | <span id="EquipmentEventType_ID"></span>Surrogate primary key | - |
| EquipmentEventType_Name | NVARCHAR(100) | - | ✓ | <span id="EquipmentEventType_Name"></span>Name of the event type. Controlled vocabulary: Calibration, Validation, Maintenance, Installation, Removal, Firmware Update, Failure, Repair | - |

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
| ManualLocation | NVARCHAR(100) | - |  | <span id="ManualLocation"></span>Location where the manual is stored | - |

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

One analytical run on a discrete physical sample. Groups together all LabValue rows from a single lab session. Lab data does not fit the continuous-stream Channel abstraction (it is tied to a physical sample, not an equipment stream), so it lives here rather than in Channel + Value.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| LabAnalysis_ID | INT **(PK)** | - | ✓ | <span id="LabAnalysis_ID"></span>Surrogate primary key | - |
| Sample_ID | INT | - | ✓ | <span id="Sample_ID"></span>The physical sample that was analysed | FK → [Sample.Sample_ID](#Sample) |
| Laboratory_ID | INT | - |  | <span id="Laboratory_ID"></span>Laboratory where the analysis was performed | FK → [Laboratory.Laboratory_ID](#Laboratory) |
| AnalystPerson_ID | INT | - |  | <span id="AnalystPerson_ID"></span>Person who performed the analysis | FK → [Person.Person_ID](#Person) |
| Procedure_ID | INT | - |  | <span id="Procedure_ID"></span>Standard operating procedure used for this analysis | FK → [Procedures.Procedure_ID](#Procedures) |
| AnalysisDateTime | DATETIME2(7) | - | ✓ | <span id="AnalysisDateTime"></span>UTC datetime when the analysis was performed. If it's a long analysis, record the beginning. | Default: `SYSUTCDATETIME()` |
| Campaign_ID | INT | - |  | <span id="Campaign_ID"></span>Campaign this analysis was part of, if any | FK → [Campaign.Campaign_ID](#Campaign) |
| Notes | NVARCHAR(MAX) | - |  | <span id="Notes"></span>Free-text notes about this analysis run | - |

<span id="LabValue"></span>

### LabValue

A single measured value from a lab analysis, for a specific parameter and unit. Multiple LabValue rows belong to one LabAnalysis (one value per parameter per replicate).



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| LabValue_ID | INT **(PK)** | - | ✓ | <span id="LabValue_ID"></span>Surrogate primary key | - |
| LabAnalysis_ID | INT | - | ✓ | <span id="LabAnalysis_ID"></span>The analysis run this value belongs to | FK → [LabAnalysis.LabAnalysis_ID](#LabAnalysis) |
| Parameter_ID | INT | - | ✓ | <span id="Parameter_ID"></span>Measured analyte (e.g. TSS, COD) | FK → [Parameter.Parameter_ID](#Parameter) |
| LabResult | FLOAT | - | ✓ | <span id="LabResult"></span>Numerical result of the measurement | - |
| Replicate | INT | - | ✓ | <span id="Replicate"></span>Replicate number (1 = primary measurement, 2+ = duplicates) | Default: `1` |
| QualityCode_ID | INT | - |  | <span id="QualityCode_ID"></span>Optional quality flag. NULL means no quality assessment has been recorded. | FK → [QualityCode.QualityCode_ID](#QualityCode) |
| Comment | NVARCHAR(MAX) | - |  | <span id="Comment"></span>Optional free-text comment reference | - |

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

<span id="Observation"></span>

### Observation

Shared hub table representing a single measurement event on a channel at a timestamp. The four payload tables (Value, ValueVector, ValueMatrix, ValueImage) carry only their type-specific data, keyed by Observation_ID. DataType mirrors Channel.ValueType_ID for self-description.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Observation_ID | INT **(PK)** | - | ✓ | <span id="Observation_ID"></span>Surrogate key; auto-assigned by the database | - |
| Channel_ID | INT | - | ✓ | <span id="Channel_ID"></span>The channel this observation belongs to | FK → [Channel.Channel_ID](#Channel) |
| Timestamp | DATETIME2(7) | - | ✓ | <span id="Timestamp"></span>UTC timestamp of the observation | - |
| DataType | NVARCHAR(10) | - | ✓ | <span id="DataType"></span>Payload type: Scalar, Vector, Matrix, or Image. Must match the Channel's ValueType. | - |

<span id="Parameter"></span>

### Parameter

Stores the different water quality or quantity parameters that are measured (e.g., pH, TSS, N-components)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Unit_ID | INT | - |  | <span id="Unit_ID"></span>A unique ID is generated automatically by the database | FK → [Unit.Unit_ID](#Unit) |
| Parameter | NVARCHAR(100) | - |  | <span id="Parameter"></span>Name of the parameter | - |
| Parameter_ID | INT **(PK)** | - | ✓ | <span id="Parameter_ID"></span>Link to the Parameter table | - |
| Description | NVARCHAR(MAX) | - |  | <span id="Description"></span>Description of the parameter | - |

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
| Function | NVARCHAR(MAX) | - |  | <span id="Function"></span>Detailed description of the person's assigned duties | - |
| Email | NVARCHAR(100) | - |  | <span id="Email"></span>E-mail address | - |
| Phone | NVARCHAR(100) | - |  | <span id="Phone"></span>Phone number | - |
| Linkedin | NVARCHAR(100) | - |  | <span id="Linkedin"></span>LinkedIn profile URL | - |
| Website | NVARCHAR(60) | - |  | <span id="Website"></span>Personal or organisation website URL | - |

<span id="Procedures"></span>

### Procedures

Stores details for different measurement procedures (e.g., calibration, validation, standard operating procedures, ISO methods)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Procedure_ID | INT **(PK)** | - | ✓ | <span id="Procedure_ID"></span>Link to the Procedures table | - |
| ProcedureName | NVARCHAR(100) | - |  | <span id="ProcedureName"></span>Title name of the procedure | - |
| ProcedureType | NVARCHAR(255) | - |  | <span id="ProcedureType"></span>Type of the procedure. For example, SOP | - |
| Description | NVARCHAR(MAX) | - |  | <span id="Description"></span>Description of the procedure | - |
| ProcedureLocation | NVARCHAR(100) | - |  | <span id="ProcedureLocation"></span>Where is the procedure stored | - |

<span id="ProcessingDegree"></span>

### ProcessingDegree

Controlled dictionary describing the level of processing applied to a Channel's time series. A new Channel row is created each time the processing degree changes — this field is set once at row creation. The DataLineage graph is the authoritative record of how each Channel was derived; this field exists for fast filtering.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| ProcessingDegree_ID | INT **(PK)** | - | ✓ | <span id="ProcessingDegree_ID"></span>Surrogate primary key, manually assigned | - |
| Name | NVARCHAR(50) | - | ✓ | <span id="Name"></span>Processing level name (e.g. 'Raw', 'Cleaned') | - |
| Description | NVARCHAR(200) | - |  | <span id="Description"></span>Explanation of what this processing level means | - |

<span id="ProcessingLineage"></span>

### ProcessingLineage

Junction table that records the input/output relationships between ProcessingStep rows and Channel rows. Each row asserts that a given Channel entry was either an Input to, or an Output of, a given ProcessingStep. Together these rows form a directed acyclic graph (DAG) of data transformations.
Example: outlier-removal step takes Channel 10 (raw TSS) as Input and produces Channel 11 (cleaned TSS) as Output.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| ProcessingLineage_ID | INT **(PK)** | - | ✓ | <span id="ProcessingLineage_ID"></span>Surrogate primary key | - |
| ProcessingStep_ID | INT | - | ✓ | <span id="ProcessingStep_ID"></span>The processing step that consumed or produced the Channel entry | FK → [ProcessingStep.ProcessingStep_ID](#ProcessingStep) |
| Channel_ID | INT | - | ✓ | <span id="Channel_ID"></span>The Channel entry (time series) that participates in this lineage edge | FK → [Channel.Channel_ID](#Channel) |
| RoleInProcessingStep | NVARCHAR(10) | - | ✓ | <span id="RoleInProcessingStep"></span>Whether this Channel entry was an Input (consumed by the step) or an Output (produced by the step). CHECK constraint enforces 'Input' or 'Output'.
 | - |
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
| Name | NVARCHAR(200) | - | ✓ | <span id="Name"></span>Human-readable name for this processing step (e.g. 'Outlier removal — Hampel filter') | - |
| Description | NVARCHAR(MAX) | - |  | <span id="Description"></span>Free-text description of what this step does and why it was applied | - |
| MethodName | NVARCHAR(200) | - |  | <span id="MethodName"></span>Machine-readable method identifier (e.g. 'outlier_removal', 'linear_interpolation'). Maps to a metEAUdata processing function name. | - |
| MethodVersion | NVARCHAR(100) | - |  | <span id="MethodVersion"></span>Version of the method or library used (e.g. 'meteaudata 0.5.1') | - |
| ProcessingType | NVARCHAR(100) | - |  | <span id="ProcessingType"></span>Category of processing applied. Stored as a string mirroring metEAUdata's ProcessingType enum values (e.g. 'Smoothing', 'Filtering', 'Resampling', 'GapFilling'). No lookup table — metEAUdata's enum is the source of truth. Controlled vocabulary: see ProcessingType_set.
 | - |
| Parameters | NVARCHAR(MAX) | - |  | <span id="Parameters"></span>JSON blob of method parameters (e.g. '{"window": 5, "threshold": 3.0}') | - |
| ExecutedDateTime | DATETIME2(7) | - |  | <span id="ExecutedDateTime"></span>UTC timestamp when this processing step was executed | - |
| ExecutedByPerson_ID | INT | - |  | <span id="ExecutedByPerson_ID"></span>Person who ran or triggered this processing step. NULL for automated/unattended runs. | FK → [Person.Person_ID](#Person) |
| Dataset_ID | INT | - |  | <span id="Dataset_ID"></span>The Dataset this processing step belongs to. NULL for steps that operate on a single channel without a named analysis context. Required for multivariate steps that consume or produce multiple channels.
 | FK → [Dataset.Dataset_ID](#Dataset) |

<span id="QualityCode"></span>

### QualityCode

Controlled dictionary of quality flags for laboratory measurement results. Each LabValue row may reference one QualityCode. IsUsable indicates whether the value should be included in downstream analysis.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| QualityCode_ID | INT **(PK)** | - | ✓ | <span id="QualityCode_ID"></span>Surrogate primary key, manually assigned | - |
| Name | NVARCHAR(50) | - | ✓ | <span id="Name"></span>Short code name (e.g. 'Accepted', 'BelowLoD') | - |
| Description | NVARCHAR(200) | - |  | <span id="Description"></span>Explanation of what this quality code means | - |
| IsUsable | BIT | - | ✓ | <span id="IsUsable"></span>Whether a value carrying this code should be included in analysis. true = value is fit for use; false = value must be excluded or treated specially.
 | Default: `True` |

<span id="Sample"></span>

### Sample

A discrete physical sample collected at a sampling location or prepared in a laboratory. Supports field samples, calibration standards, blanks, and derived sub-samples via ParentSample_ID.


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Sample_ID | INT **(PK)** | - | ✓ | <span id="Sample_ID"></span>Surrogate primary key | - |
| ParentSample_ID | INT | - |  | <span id="ParentSample_ID"></span>Parent sample this was derived from (e.g., an aliquot of a master standard). NULL for primary samples. | FK → [Sample.Sample_ID](#Sample) |
| SampleType_ID | INT | - |  | <span id="SampleType_ID"></span>Nature of the sample (FK to SampleType lookup table) | FK → [SampleType.SampleType_ID](#SampleType) |
| SamplingPoint_ID | INT | - | ✓ | <span id="SamplingPoint_ID"></span>Sampling location where the sample was collected or prepared | FK → [SamplingPoint.SamplingPoint_ID](#SamplingPoint) |
| SampledByPerson_ID | INT | - |  | <span id="SampledByPerson_ID"></span>Person who collected the sample | FK → [Person.Person_ID](#Person) |
| Campaign_ID | INT | - |  | <span id="Campaign_ID"></span>Campaign this sample belongs to | FK → [Campaign.Campaign_ID](#Campaign) |
| SampleDateTimeStart | DATETIME2(7) | - | ✓ | <span id="SampleDateTimeStart"></span>Date and time sampling began (UTC) | - |
| SampleDateTimeEnd | DATETIME2(7) | - |  | <span id="SampleDateTimeEnd"></span>Date and time sampling ended (UTC). NULL for instantaneous grab samples. | - |
| SampleMethod_ID | INT | - |  | <span id="SampleMethod_ID"></span>Method of sample collection (FK to SampleMethod lookup table) | FK → [SampleMethod.SampleMethod_ID](#SampleMethod) |
| SampleEquipment_ID | INT | - |  | <span id="SampleEquipment_ID"></span>Equipment used to collect the sample (e.g., auto-sampler) | FK → [Equipment.Equipment_ID](#Equipment) |
| Description | NVARCHAR(500) | - |  | <span id="Description"></span>Additional notes about the sample | - |

<span id="SampleMethod"></span>

### SampleMethod

Controlled dictionary describing how a sample was collected. Referenced by Sample.SampleMethod_ID.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| SampleMethod_ID | INT **(PK)** | - | ✓ | <span id="SampleMethod_ID"></span>Surrogate primary key, manually assigned | - |
| Name | NVARCHAR(50) | - | ✓ | <span id="Name"></span>Collection method name (e.g. 'Grab', 'Composite24h') | - |
| Description | NVARCHAR(200) | - |  | <span id="Description"></span>Explanation of the collection method | - |

<span id="SampleType"></span>

### SampleType

Controlled dictionary describing the nature of a physical sample. Referenced by Sample.SampleType_ID.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| SampleType_ID | INT **(PK)** | - | ✓ | <span id="SampleType_ID"></span>Surrogate primary key, manually assigned | - |
| Name | NVARCHAR(50) | - | ✓ | <span id="Name"></span>Sample type name (e.g. 'Field', 'Blank') | - |
| Description | NVARCHAR(200) | - |  | <span id="Description"></span>Explanation of what this sample type represents | - |

<span id="SamplingPoint"></span>

### SamplingPoint

Stores the identification, specific geographical coordinates (Latitude/Longitude/GPS), and description of a particular spot where a sample or measurement is taken


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| SamplingPoint_ID | INT **(PK)** | - | ✓ | <span id="SamplingPoint_ID"></span>Link to the SamplingPoint table | - |
| Site_ID | INT | - |  | <span id="Site_ID"></span>A unique ID is generated automatically by the database | FK → [Site.Site_ID](#Site) |
| SamplingPoint | NVARCHAR(100) | - |  | <span id="SamplingPoint"></span>Where the sample was taken. For example: "Inlet", "Outlet" or "Upstream" | - |
| SamplingLocation | NVARCHAR(100) | - |  | <span id="SamplingLocation"></span>Where the sample was taken. For example: "Biofiltration", "Sewer 01" or "Retention Tank" | - |
| LatitudeWGS84 | FLOAT | - |  | <span id="LatitudeWGS84"></span>WGS84 latitude in decimal degrees. For example: 45.9070 | - |
| LongitudeWGS84 | FLOAT | - |  | <span id="LongitudeWGS84"></span>WGS84 longitude in decimal degrees. For example: -73.7833 | - |
| Description | NVARCHAR(MAX) | - |  | <span id="Description"></span>Description of the sampling point | - |
| Pictures | /* UNMAPPED TYPE */ | - |  | <span id="Pictures"></span>Picture of the site | - |
| ValidFrom | DATETIME2(7) | - |  | <span id="ValidFrom"></span>Date from which this sampling point record is considered valid (UTC). NULL means valid from the beginning of records. | - |
| ValidTo | DATETIME2(7) | - |  | <span id="ValidTo"></span>Date until which this sampling point record is valid (UTC). NULL means currently active. | - |
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

<span id="SignalPort"></span>

### SignalPort

Universal connection point between a DataAcquisitionSystem and a measurement Channel. A port is the stable identity of a signal: it persists across equipment swaps and sensor relocations. One row per tag per DAS. For SCADA systems the tag is a standard tag string (e.g. "TIT-101"). For direct-connect stations a synthetic tag is auto-generated as "{equipment_identifier}/{parameter_name}". Sub-signals (status, alarm, uncertainty) reference their parent value port via ParentPort_ID.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| SignalPort_ID | INT **(PK)** | - | ✓ | <span id="SignalPort_ID"></span>Surrogate primary key | - |
| DataAcquisitionSystem_ID | INT | - | ✓ | <span id="DataAcquisitionSystem_ID"></span>The DAS that owns this tag | FK → [DataAcquisitionSystem.DataAcquisitionSystem_ID](#DataAcquisitionSystem) |
| Tag | NVARCHAR(200) | - | ✓ | <span id="Tag"></span>Tag string as published by the DAS (case-preserved; lookups are case-insensitive trimmed) | - |
| SignalPortType_ID | INT | - | ✓ | <span id="SignalPortType_ID"></span>Kind of data flowing through this port (Value, Status, Alarm, Uncertainty) | FK → [SignalPortType.SignalPortType_ID](#SignalPortType) |
| ParentPort_ID | INT | - |  | <span id="ParentPort_ID"></span>For sub-signals (Status, Alarm, Uncertainty ports), points to the parent Value-type port. NULL for primary value ports and unlinked ports.
 | FK → [SignalPort.SignalPort_ID](#SignalPort) |
| IsActive | BIT | - | ✓ | <span id="IsActive"></span>Whether this port is currently expected to receive data. Set to false when a signal is retired. | Default: `True` |
| Description | NVARCHAR(MAX) | - |  | <span id="Description"></span>Free-text notes about this port | - |

<span id="SignalPortEquipmentHistory"></span>

### SignalPortEquipmentHistory

Temporal record of which physical instrument (Equipment) is behind a SignalPort. When a sensor probe is replaced, close the current row (set EndTime) and open a new row for the replacement instrument. Equipment_ID may be NULL when the physical instrument is unknown at ingest time. At most one row per port may have EndTime IS NULL (the "currently installed" instrument).



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| SignalPortEquipmentHistory_ID | INT **(PK)** | - | ✓ | <span id="SignalPortEquipmentHistory_ID"></span>Surrogate primary key | - |
| SignalPort_ID | INT | - | ✓ | <span id="SignalPort_ID"></span>The port to which this equipment is linked | FK → [SignalPort.SignalPort_ID](#SignalPort) |
| Equipment_ID | INT | - |  | <span id="Equipment_ID"></span>The physical instrument behind this port during this period. NULL = unknown at ingest time. | FK → [Equipment.Equipment_ID](#Equipment) |
| StartTime | DATETIME2(7) | - | ✓ | <span id="StartTime"></span>UTC datetime when this equipment started serving this port | - |
| EndTime | DATETIME2(7) | - |  | <span id="EndTime"></span>UTC datetime when this equipment stopped serving this port. NULL = currently installed. | - |
| Notes | NVARCHAR(MAX) | - |  | <span id="Notes"></span>Free-text notes (e.g. reason for swap, calibration context) | - |

<span id="SignalPortLocationHistory"></span>

### SignalPortLocationHistory

Temporal record of where a SignalPort is measuring (which SamplingPoint). Enables the sensor relocation SOP: when a sensor is physically moved, close the current row (set EndTime) and open a new row for the new SamplingPoint. Point-in-time queries resolve the SamplingPoint at any historical timestamp. At most one row per port may have EndTime IS NULL (the "active" location).



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| SignalPortLocationHistory_ID | INT **(PK)** | - | ✓ | <span id="SignalPortLocationHistory_ID"></span>Surrogate primary key | - |
| SignalPort_ID | INT | - | ✓ | <span id="SignalPort_ID"></span>The port whose physical location is recorded here | FK → [SignalPort.SignalPort_ID](#SignalPort) |
| SamplingPoint_ID | INT | - | ✓ | <span id="SamplingPoint_ID"></span>The SamplingPoint where this port is measuring during this period | FK → [SamplingPoint.SamplingPoint_ID](#SamplingPoint) |
| StartTime | DATETIME2(7) | - | ✓ | <span id="StartTime"></span>UTC datetime when the port started measuring at this SamplingPoint | - |
| EndTime | DATETIME2(7) | - |  | <span id="EndTime"></span>UTC datetime when the port stopped measuring here. NULL = currently active. | - |
| Notes | NVARCHAR(MAX) | - |  | <span id="Notes"></span>Free-text notes (e.g. reason for relocation) | - |

<span id="SignalPortType"></span>

### SignalPortType

Controlled vocabulary describing the kind of data flowing through a SignalPort. Answers "what kind of signal is this?". A blower command has SignalPortType=Value. A device health indicator has SignalPortType=Status.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| SignalPortType_ID | INT **(PK)** | - | ✓ | <span id="SignalPortType_ID"></span>Surrogate primary key, manually assigned | - |
| Name | NVARCHAR(50) | - | ✓ | <span id="Name"></span>Short name for this port type | - |
| Description | NVARCHAR(200) | - |  | <span id="Description"></span>Explanation of what this port type means | - |

<span id="Site"></span>

### Site

Stores general site information, including address, site type, and a link to the associated watershed


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Site_ID | INT **(PK)** | - | ✓ | <span id="Site_ID"></span>A unique ID is generated automatically by the database | - |
| Watershed_ID | INT | - |  | <span id="Watershed_ID"></span>Linked to the Watershed table | FK → [Watershed.Watershed_ID](#Watershed) |
| Name | NVARCHAR(100) | - |  | <span id="Name"></span>Name of the site | - |
| Type | NVARCHAR(255) | - |  | <span id="Type"></span>For example: "WWTP", "River" or "Sewer_system" | - |
| Description | NVARCHAR(MAX) | - |  | <span id="Description"></span>Description of the site | - |
| LatitudeWGS84 | FLOAT | - |  | <span id="LatitudeWGS84"></span>Latitude of the site in WGS84 decimal degrees | - |
| LongitudeWGS84 | FLOAT | - |  | <span id="LongitudeWGS84"></span>Longitude of the site in WGS84 decimal degrees | - |
| StreetNumber | NVARCHAR(100) | - |  | <span id="StreetNumber"></span>Address: number of the street | - |
| StreetName | NVARCHAR(100) | - |  | <span id="StreetName"></span>Address: name of the street | - |
| City | NVARCHAR(255) | - |  | <span id="City"></span>Address: name of the city | - |
| PostCode | NVARCHAR(100) | - |  | <span id="PostCode"></span>Address: postal code | - |
| Province | NVARCHAR(255) | - |  | <span id="Province"></span>Address: name of the province | - |
| Country | NVARCHAR(255) | - |  | <span id="Country"></span>Address: name of the country | - |

<span id="Unit"></span>

### Unit

Stores the SI units of measurement (or other relevant units) corresponding to the parameters (e.g., mg/L, g/L, s)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Unit_ID | INT **(PK)** | - | ✓ | <span id="Unit_ID"></span>A unique ID is generated automatically by the database | - |
| Unit | NVARCHAR(100) | - |  | <span id="Unit"></span>SI-units only | - |

<span id="UrbanCharacteristics"></span>

### UrbanCharacteristics

Stores the urban land use percentages (e.g., commercial, residential, green spaces) within the watershed


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

<span id="Value"></span>

### Value

Scalar payload for a single Observation. One row per Observation of DataType='Scalar'. Channel and Timestamp are resolved via the Observation table.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Observation_ID | INT **(PK)** | - | ✓ | <span id="Observation_ID"></span>Links this scalar value to its Observation (channel + timestamp) | FK → [Observation.Observation_ID](#Observation) |
| Value | FLOAT | - |  | <span id="Value"></span>Measured scalar value | - |

<span id="ValueBin"></span>

### ValueBin

Individual bins on a ValueBinningAxis, each defined by a half-open interval [LowerBound, UpperBound) in the axis unit


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| ValueBin_ID | INT **(PK)** | - | ✓ | <span id="ValueBin_ID"></span>Surrogate primary key | - |
| ValueBinningAxis_ID | INT | - | ✓ | <span id="ValueBinningAxis_ID"></span>References the parent binning axis | FK → [ValueBinningAxis.ValueBinningAxis_ID](#ValueBinningAxis) |
| BinIndex | INT | - | ✓ | <span id="BinIndex"></span>0-based ordinal position of this bin within its axis | - |
| LowerBound | FLOAT | - | ✓ | <span id="LowerBound"></span>Inclusive lower edge of this bin in the axis unit | - |
| UpperBound | FLOAT | - | ✓ | <span id="UpperBound"></span>Exclusive upper edge of this bin in the axis unit; must be greater than LowerBound | - |

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
| Unit_ID | INT | - | ✓ | <span id="Unit_ID"></span>Physical unit of the axis coordinates (e.g. nm, µm, m/s) — distinct from the measured value unit stored in MetaData | FK → [Unit.Unit_ID](#Unit) |

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

<span id="ValueType"></span>

### ValueType

Lookup table defining the shape of stored measurement values (Scalar, Vector, Matrix, Image)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| ValueType_ID | INT **(PK)** | - | ✓ | <span id="ValueType_ID"></span>Surrogate primary key | - |
| ValueType_Name | NVARCHAR(50) | - | ✓ | <span id="ValueType_Name"></span>Human-readable name of the value type (Scalar, Vector, Matrix, or Image) | - |

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