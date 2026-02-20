# Database Tables

This documentation is auto-generated from dictionary.json.


## Tables


<span id="Annotation"></span>

### Annotation

Human-authored annotations on time series data. Each annotation applies to a single MetaData entry (one measurement channel) over a time range. Multiple annotations can overlap on the same range. EndTime=NULL means either a point annotation or an ongoing situation.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Annotation_ID | INT **(PK)** | - | ✓ | <span id="Annotation_ID"></span>Primary key, auto-incremented | - |
| Metadata_ID | INT | - | ✓ | <span id="Metadata_ID"></span>The time series this annotation applies to | FK → [MetaData.Metadata_ID](#MetaData) |
| AnnotationType_ID | INT | - | ✓ | <span id="AnnotationType_ID"></span>What kind of annotation this is | FK → [AnnotationType.AnnotationType_ID](#AnnotationType) |
| StartTime | DATETIME2(7) | - | ✓ | <span id="StartTime"></span>Start of the annotated time range | - |
| EndTime | DATETIME2(7) | - |  | <span id="EndTime"></span>End of the annotated range. NULL = point annotation or ongoing | - |
| AuthorPerson_ID | INT | - |  | <span id="AuthorPerson_ID"></span>Person who created this annotation | FK → [Person.Person_ID](#Person) |
| Campaign_ID | INT | - |  | <span id="Campaign_ID"></span>Campaign this annotation is associated with, if any | FK → [Campaign.Campaign_ID](#Campaign) |
| EquipmentEvent_ID | INT | - |  | <span id="EquipmentEvent_ID"></span>Equipment event that caused this annotation, if any | FK → [EquipmentEvent.EquipmentEvent_ID](#EquipmentEvent) |
| Title | NVARCHAR(200) | - |  | <span id="Title"></span>Short title for the annotation | - |
| Comment | NVARCHAR(MAX) | - |  | <span id="Comment"></span>Detailed free-text comment | - |
| CreatedAt | DATETIME2(7) | - | ✓ | <span id="CreatedAt"></span>When this annotation was created | Default: `CURRENT_TIMESTAMP` |
| ModifiedAt | DATETIME2(7) | - |  | <span id="ModifiedAt"></span>When this annotation was last modified | - |

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

A named collection of measurement activities at a site, classified by type (Experiment, Operations, Commissioning). Replaces direct use of Project for new data.


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Campaign_ID | INT **(PK)** | - | ✓ | <span id="Campaign_ID"></span>Surrogate primary key | - |
| CampaignType_ID | INT | - | ✓ | <span id="CampaignType_ID"></span>Type of campaign (Experiment, Operations, Commissioning) | FK → [CampaignType.CampaignType_ID](#CampaignType) |
| Site_ID | INT | - | ✓ | <span id="Site_ID"></span>Site where the campaign is conducted | FK → [Site.Site_ID](#Site) |
| Name | NVARCHAR(200) | - | ✓ | <span id="Name"></span>Human-readable name for the campaign | - |
| Description | NVARCHAR(2000) | - |  | <span id="Description"></span>Detailed description of the campaign objectives and scope | - |
| StartDate | DATETIME2(7) | - |  | <span id="StartDate"></span>Date and time the campaign began (UTC) | - |
| EndDate | DATETIME2(7) | - |  | <span id="EndDate"></span>Date and time the campaign ended (UTC); NULL if ongoing | - |
| Project_ID | INT | - |  | <span id="Project_ID"></span>Optional backward-compatibility link to the legacy Project table | FK → [Project.Project_ID](#Project) |

<span id="CampaignEquipment"></span>

### CampaignEquipment

Junction table: equipment deployed during a campaign.


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Campaign_ID | INT **(PK)** | - | ✓ | <span id="Campaign_ID"></span>Campaign using this equipment | FK → [Campaign.Campaign_ID](#Campaign) |
| Equipment_ID | INT **(PK)** | - | ✓ | <span id="Equipment_ID"></span>Equipment deployed during the campaign | FK → [Equipment.Equipment_ID](#Equipment) |
| Role | NVARCHAR(100) | - |  | <span id="Role"></span>Role of this equipment in the campaign (e.g., 'Primary sensor', 'Auto-sampler') | - |

<span id="CampaignParameter"></span>

### CampaignParameter

Junction table: parameters (variables) measured during a campaign.


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Campaign_ID | INT **(PK)** | - | ✓ | <span id="Campaign_ID"></span>Campaign measuring this parameter | FK → [Campaign.Campaign_ID](#Campaign) |
| Parameter_ID | INT **(PK)** | - | ✓ | <span id="Parameter_ID"></span>Parameter measured during the campaign | FK → [Parameter.Parameter_ID](#Parameter) |

<span id="CampaignSamplingLocation"></span>

### CampaignSamplingLocation

Junction table: sampling locations actively monitored during a campaign.


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Campaign_ID | INT **(PK)** | - | ✓ | <span id="Campaign_ID"></span>Campaign using this sampling location | FK → [Campaign.Campaign_ID](#Campaign) |
| Sampling_point_ID | INT **(PK)** | - | ✓ | <span id="Sampling_point_ID"></span>Sampling location used by the campaign | FK → [SamplingPoints.Sampling_point_ID](#SamplingPoints) |
| Role | NVARCHAR(100) | - |  | <span id="Role"></span>Role of this location in the campaign (e.g., 'Inlet', 'Reference') | - |

<span id="CampaignType"></span>

### CampaignType

Lookup table classifying the nature of a Campaign (Experiment, Operations, Commissioning)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| CampaignType_ID | INT **(PK)** | - | ✓ | <span id="CampaignType_ID"></span>Surrogate primary key | - |
| CampaignType_Name | NVARCHAR(100) | - | ✓ | <span id="CampaignType_Name"></span>Name of the campaign type. Controlled vocabulary: Experiment, Operations, Commissioning | - |

<span id="Comments"></span>

### Comments

Stores any additional textual comments, notes, or observations related to a specific measured value


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Comment_ID | INT **(PK)** | - | ✓ | <span id="Comment_ID"></span>A unique ID is generated automatically by MySQL | - |
| Comment | NVARCHAR(MAX) | - |  | <span id="Comment"></span>Comment on the data in the Value table | - |

<span id="DataLineage"></span>

### DataLineage

Junction table that records the input/output relationships between ProcessingStep rows and MetaData rows. Each row asserts that a given MetaData entry was either an Input to, or an Output of, a given ProcessingStep. Together these rows form a directed acyclic graph (DAG) of data transformations.
Example: outlier-removal step takes MetaData 10 (raw TSS) as Input and produces MetaData 11 (cleaned TSS) as Output.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| DataLineage_ID | INT **(PK)** | - | ✓ | <span id="DataLineage_ID"></span>Surrogate primary key | - |
| ProcessingStep_ID | INT | - | ✓ | <span id="ProcessingStep_ID"></span>The processing step that consumed or produced the MetaData entry | FK → [ProcessingStep.ProcessingStep_ID](#ProcessingStep) |
| Metadata_ID | INT | - | ✓ | <span id="Metadata_ID"></span>The MetaData entry (time series) that participates in this lineage edge | FK → [MetaData.Metadata_ID](#MetaData) |
| Role | NVARCHAR(10) | - | ✓ | <span id="Role"></span>Whether this MetaData entry was an Input (consumed by the step) or an Output (produced by the step). CHECK constraint enforces 'Input' or 'Output'.
 | - |

<span id="DataProvenance"></span>

### DataProvenance

Lookup table describing how a measurement was produced (Sensor, Laboratory, Manual Entry, Model Output, External Source)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| DataProvenance_ID | INT **(PK)** | - | ✓ | <span id="DataProvenance_ID"></span>Surrogate primary key | - |
| DataProvenance_Name | NVARCHAR(50) | - | ✓ | <span id="DataProvenance_Name"></span>Name of the provenance. Controlled vocabulary: Sensor, Laboratory, Manual Entry, Model Output, External Source | - |

<span id="Equipment"></span>

### Equipment

Stores information about a specific, physical piece of equipment (e.g., serial number, owner, purchase date, storage location)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Equipment_ID | INT **(PK)** | - | ✓ | <span id="Equipment_ID"></span>Link to the Equipment table | - |
| model_ID | INT | - |  | <span id="model_ID"></span>Link to the Equipment model table | FK → [EquipmentModel.Equipment_model_ID](#EquipmentModel) |
| identifier | NVARCHAR(100) | - |  | <span id="identifier"></span>Identification name of the equipments | - |
| Serial_number | NVARCHAR(100) | - |  | <span id="Serial_number"></span>Serial number of the equipment | - |
| Owner | NVARCHAR(MAX) | - |  | <span id="Owner"></span>Name of the owner of the equipment | - |
| Storage_location | NVARCHAR(100) | - |  | <span id="Storage_location"></span>Where is the procedure stored | - |
| Purchase_date | DATE | - |  | <span id="Purchase_date"></span>Date when the equipment was bought: 'YYYY-MM-DD | - |

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
| Notes | NVARCHAR(1000) | - |  | <span id="Notes"></span>Free-text notes about the event | - |

<span id="EquipmentEventMetaData"></span>

### EquipmentEventMetaData

Junction table linking an equipment lifecycle event to the MetaData series it involves. WindowStart/WindowEnd optionally narrow sensor readings to the relevant time window (e.g., the 2-minute immersion window during a calibration).


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| EquipmentEvent_ID | INT **(PK)** | - | ✓ | <span id="EquipmentEvent_ID"></span>Equipment event this link belongs to | FK → [EquipmentEvent.EquipmentEvent_ID](#EquipmentEvent) |
| Metadata_ID | INT **(PK)** | - | ✓ | <span id="Metadata_ID"></span>MetaData series associated with this event (sensor series or lab result series) | FK → [MetaData.Metadata_ID](#MetaData) |
| WindowStart | DATETIME2(7) | - |  | <span id="WindowStart"></span>Start of the relevant time window within the MetaData series (e.g., when sensor was immersed in solution). NULL means use all values in the series. | - |
| WindowEnd | DATETIME2(7) | - |  | <span id="WindowEnd"></span>End of the relevant time window. NULL means use all values in the series. | - |

<span id="EquipmentEventType"></span>

### EquipmentEventType

Lookup table classifying the type of lifecycle event that occurred on a piece of equipment (Calibration, Maintenance, etc.)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| EquipmentEventType_ID | INT **(PK)** | - | ✓ | <span id="EquipmentEventType_ID"></span>Surrogate primary key | - |
| EquipmentEventType_Name | NVARCHAR(100) | - | ✓ | <span id="EquipmentEventType_Name"></span>Name of the event type. Controlled vocabulary: Calibration, Validation, Maintenance, Installation, Removal, Firmware Update, Failure, Repair | - |

<span id="EquipmentInstallation"></span>

### EquipmentInstallation

Records the physical deployment history of a piece of equipment at a sampling location. Enables reconstructing which sensor was active at which location during any past interval.


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Installation_ID | INT **(PK)** | - | ✓ | <span id="Installation_ID"></span>Surrogate primary key | - |
| Equipment_ID | INT | - | ✓ | <span id="Equipment_ID"></span>Equipment that was installed | FK → [Equipment.Equipment_ID](#Equipment) |
| Sampling_point_ID | INT | - | ✓ | <span id="Sampling_point_ID"></span>Sampling location where the equipment was installed | FK → [SamplingPoints.Sampling_point_ID](#SamplingPoints) |
| InstalledDate | DATETIME2(7) | - | ✓ | <span id="InstalledDate"></span>Date and time the equipment was installed at this location (UTC) | - |
| RemovedDate | DATETIME2(7) | - |  | <span id="RemovedDate"></span>Date and time the equipment was removed (UTC). NULL means currently installed. | - |
| Campaign_ID | INT | - |  | <span id="Campaign_ID"></span>Campaign during which this installation occurred (if applicable) | FK → [Campaign.Campaign_ID](#Campaign) |
| Notes | NVARCHAR(500) | - |  | <span id="Notes"></span>Free-text notes about the installation or removal | - |

<span id="EquipmentModel"></span>

### EquipmentModel

Stores detailed, non-redundant specifications for a specific sensor or instrument model (e.g., manufacturer, functions, method)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Equipment_model_ID | INT **(PK)** | - | ✓ | <span id="Equipment_model_ID"></span>Link to the Equipment model table | - |
| Equipment_model | NVARCHAR(100) | - |  | <span id="Equipment_model"></span>Name of the equipment model. For example: ammo::lyser | - |
| Method | NVARCHAR(100) | - |  | <span id="Method"></span>Method behind the equipment | - |
| Functions | NVARCHAR(MAX) | - |  | <span id="Functions"></span>Description of the functions of the equipment | - |
| Manufacturer | NVARCHAR(100) | - |  | <span id="Manufacturer"></span>Name of the manufacturer | - |
| Manual_location | NVARCHAR(100) | - |  | <span id="Manual_location"></span>Location where the manual is stored | - |

<span id="EquipmentModelHasParameter"></span>

### EquipmentModelHasParameter

Links equipment models to the parameters they can measure


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Equipment_model_ID | INT **(PK)** | - | ✓ | <span id="Equipment_model_ID"></span>Link to the Equipment model table | FK → [EquipmentModel.Equipment_model_ID](#EquipmentModel) |
| Parameter_ID | INT **(PK)** | - | ✓ | <span id="Parameter_ID"></span>Link to the Parameter table | FK → [Parameter.Parameter_ID](#Parameter) |

<span id="EquipmentModelHasProcedures"></span>

### EquipmentModelHasProcedures

Links equipment models to the relevant maintenance procedures


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Equipment_model_ID | INT **(PK)** | - | ✓ | <span id="Equipment_model_ID"></span>Link to the Equipment model table | FK → [EquipmentModel.Equipment_model_ID](#EquipmentModel) |
| Procedure_ID | INT **(PK)** | - | ✓ | <span id="Procedure_ID"></span>Link to the Procedures table | FK → [Procedures.Procedure_ID](#Procedures) |

<span id="HydrologicalCharacteristics"></span>

### HydrologicalCharacteristics

Stores the hydrological land use percentages (e.g., forest, wetlands, cropland, grassland) within the watershed


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Watershed_ID | INT **(PK)** | - | ✓ | <span id="Watershed_ID"></span>Linked to the Watershed table | FK → [Watershed.Watershed_ID](#Watershed) |
| Urban_area | REAL | - |  | <span id="Urban_area"></span>Percentage [%] of urban areas | - |
| Forest | REAL | - |  | <span id="Forest"></span>Percentage [%] of forest areas | - |
| Wetlands | REAL | - |  | <span id="Wetlands"></span>Percentage [%] of wetlands | - |
| Cropland | REAL | - |  | <span id="Cropland"></span>Percentage [%] of croplands | - |
| Meadow | REAL | - |  | <span id="Meadow"></span>Percentage [%] of meadow areas | - |
| Grassland | REAL | - |  | <span id="Grassland"></span>Percentage [%] of grasslands | - |

<span id="IngestionRoute"></span>

### IngestionRoute

Routing table that maps an (Equipment, Parameter, DataProvenance, ProcessingDegree) key to the target MetaData entry. Ingestion scripts look up this table instead of hardcoding MetaDataIDs, so that when a sensor moves or a campaign changes, only a single row needs to be updated. ValidFrom/ValidTo define the temporal validity of each route; at most one route may be active for a given key at any point in time.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| IngestionRoute_ID | INT **(PK)** | - | ✓ | <span id="IngestionRoute_ID"></span>Surrogate primary key | - |
| Equipment_ID | INT | - |  | <span id="Equipment_ID"></span>Equipment that produces the data. NULL for non-sensor provenance (e.g. lab, manual). | FK → [Equipment.Equipment_ID](#Equipment) |
| Parameter_ID | INT | - | ✓ | <span id="Parameter_ID"></span>Measured parameter (e.g. TSS, pH, DO) | FK → [Parameter.Parameter_ID](#Parameter) |
| DataProvenance_ID | INT | - | ✓ | <span id="DataProvenance_ID"></span>How this data is produced (Sensor=1, Laboratory=2, Manual Entry=3, …) | FK → [DataProvenance.DataProvenance_ID](#DataProvenance) |
| ProcessingDegree | NVARCHAR(50) | - | ✓ | <span id="ProcessingDegree"></span>Level of processing applied before storage. Controlled vocabulary: Raw, Cleaned, Validated, Interpolated, Aggregated.
 | Default: `Raw` |
| ValidFrom | DATETIME2(7) | - | ✓ | <span id="ValidFrom"></span>Start of the interval during which this route is active (inclusive) | - |
| ValidTo | DATETIME2(7) | - |  | <span id="ValidTo"></span>End of the interval. NULL means the route is still active. | - |
| CreatedAt | DATETIME2(7) | - | ✓ | <span id="CreatedAt"></span>Timestamp when this routing rule was created | Default: `CURRENT_TIMESTAMP` |
| Metadata_ID | INT | - | ✓ | <span id="Metadata_ID"></span>Target MetaData entry where data will be stored | FK → [MetaData.Metadata_ID](#MetaData) |
| Notes | NVARCHAR(500) | - |  | <span id="Notes"></span>Free-text notes about why this route was created or changed | - |

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

<span id="MetaData"></span>

### MetaData

Central context aggregator linking every measurement to its full provenance (project, contact, equipment, parameter, procedure, unit, purpose, sampling point, and condition)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Metadata_ID | INT **(PK)** | - | ✓ | <span id="Metadata_ID"></span>Surrogate primary key | - |
| Project_ID | INT | - |  | <span id="Project_ID"></span>Links to the research or monitoring project | FK → [Project.Project_ID](#Project) |
| Contact_ID | INT | - |  | <span id="Contact_ID"></span>Links to the person responsible for this measurement series | FK → [Person.Person_ID](#Person) |
| Equipment_ID | INT | - |  | <span id="Equipment_ID"></span>Links to the physical instrument that produced the measurements | FK → [Equipment.Equipment_ID](#Equipment) |
| Parameter_ID | INT | - |  | <span id="Parameter_ID"></span>Links to the measured analyte or parameter (e.g. TSS, pH) | FK → [Parameter.Parameter_ID](#Parameter) |
| Procedure_ID | INT | - |  | <span id="Procedure_ID"></span>Links to the standard operating procedure used | FK → [Procedures.Procedure_ID](#Procedures) |
| Unit_ID | INT | - |  | <span id="Unit_ID"></span>Links to the measurement unit (e.g. mg/L) | FK → [Unit.Unit_ID](#Unit) |
| Purpose_ID | INT | - |  | <span id="Purpose_ID"></span>Links to the measurement purpose (online, lab, calibration, validation) | FK → [Purpose.Purpose_ID](#Purpose) |
| Sampling_point_ID | INT | - |  | <span id="Sampling_point_ID"></span>Links to the physical sampling location | FK → [SamplingPoints.Sampling_point_ID](#SamplingPoints) |
| Condition_ID | INT | - |  | <span id="Condition_ID"></span>Links to the prevailing weather condition at time of measurement | FK → [WeatherCondition.Condition_ID](#WeatherCondition) |
| ValueType_ID | INT | - | ✓ | <span id="ValueType_ID"></span>Identifies the shape of stored values (1=Scalar, 2=Vector, 3=Matrix, 4=Image) | FK → [ValueType.ValueType_ID](#ValueType)<br>Default: `1` |
| DataProvenance_ID | INT | - |  | <span id="DataProvenance_ID"></span>How this data was produced (Sensor, Laboratory, Manual Entry, Model Output, External Source). NULL for legacy rows; backfilled by migration. | FK → [DataProvenance.DataProvenance_ID](#DataProvenance) |
| Campaign_ID | INT | - |  | <span id="Campaign_ID"></span>Campaign this measurement series belongs to. NULL for legacy rows. | FK → [Campaign.Campaign_ID](#Campaign) |
| Sample_ID | INT | - |  | <span id="Sample_ID"></span>Discrete sample analysed to produce this measurement series. Only populated for lab data (DataProvenance_ID=2). | FK → [Sample.Sample_ID](#Sample) |
| Laboratory_ID | INT | - |  | <span id="Laboratory_ID"></span>Laboratory where analysis was performed. Only populated for lab data (DataProvenance_ID=2). | FK → [Laboratory.Laboratory_ID](#Laboratory) |
| AnalystPerson_ID | INT | - |  | <span id="AnalystPerson_ID"></span>Person who performed the analysis. Only populated for lab data (DataProvenance_ID=2). | FK → [Person.Person_ID](#Person) |
| ProcessingDegree | NVARCHAR(50) | - |  | <span id="ProcessingDegree"></span>Denormalized field indicating the level of processing applied to this time series. Ground truth is the DataLineage graph; this field exists for fast filtering. Set once at row creation and never changed — if the processing degree changes, a new MetaData row is created. Controlled vocabulary: Raw, Cleaned, Validated, Interpolated, Aggregated. Backfilled to 'Raw' for all rows existing before v1.6.0.
 | Default: `Raw` |
| StatusOfMetaDataID | INT | - |  | <span id="StatusOfMetaDataID"></span>If this MetaData entry is a status time series, this points  to the measurement MetaData entry it describes. NULL for  measurement entries and non-status entries.
 | FK → [MetaData.Metadata_ID](#MetaData) |
| StatusOfEquipmentID | INT | - |  | <span id="StatusOfEquipmentID"></span>If this MetaData entry is a device-level status time series,  this points to the Equipment it describes. NULL for channel- level status and non-status entries.
 | FK → [Equipment.Equipment_ID](#Equipment) |

<span id="MetaDataAxis"></span>

### MetaDataAxis

Junction table linking a MetaData measurement series to its binning axis or axes. AxisRole=0 is the single axis for a Vector, or the row axis for a Matrix; AxisRole=1 is the column axis for a Matrix


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Metadata_ID | INT **(PK)** | - | ✓ | <span id="Metadata_ID"></span>References the measurement series | FK → [MetaData.Metadata_ID](#MetaData) |
| AxisRole | INT **(PK)** | - | ✓ | <span id="AxisRole"></span>Dimension role: 0 = primary/row axis, 1 = secondary/column axis (Matrix only) | - |
| ValueBinningAxis_ID | INT | - | ✓ | <span id="ValueBinningAxis_ID"></span>References the binning axis for this role | FK → [ValueBinningAxis.ValueBinningAxis_ID](#ValueBinningAxis) |

<span id="Parameter"></span>

### Parameter

Stores the different water quality or quantity parameters that are measured (e.g., pH, TSS, N-components)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Unit_ID | INT | - |  | <span id="Unit_ID"></span>A unique ID is generated automatically by MySQL | FK → [Unit.Unit_ID](#Unit) |
| Parameter | NVARCHAR(100) | - |  | <span id="Parameter"></span>Name of the parameter | - |
| Parameter_ID | INT **(PK)** | - | ✓ | <span id="Parameter_ID"></span>Link to the Parameter table | - |
| Description | NVARCHAR(MAX) | - |  | <span id="Description"></span>Description of the parameter | - |

<span id="ParameterHasProcedures"></span>

### ParameterHasProcedures

Links parameters to the relevant measurement procedures


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Procedure_ID | INT **(PK)** | - | ✓ | <span id="Procedure_ID"></span>Link to the Procedures table | FK → [Procedures.Procedure_ID](#Procedures) |
| Parameter_ID | INT **(PK)** | - | ✓ | <span id="Parameter_ID"></span>Link to the Parameter table | FK → [Parameter.Parameter_ID](#Parameter) |

<span id="Person"></span>

### Person

Personal and professional information for people involved in projects (e.g., name, affiliation, role, e-mail, phone). Renamed from Contact in v1.2.0.


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Person_ID | INT **(PK)** | - | ✓ | <span id="Person_ID"></span>Surrogate primary key | - |
| Last_name | NVARCHAR(100) | - |  | <span id="Last_name"></span>Last name of the person | - |
| First_name | NVARCHAR(255) | - |  | <span id="First_name"></span>First name of the person | - |
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
| Procedure_name | NVARCHAR(100) | - |  | <span id="Procedure_name"></span>Title name of the procedure | - |
| Procedure_type | NVARCHAR(255) | - |  | <span id="Procedure_type"></span>Type of the procedure. For example, SOP | - |
| Description | NVARCHAR(MAX) | - |  | <span id="Description"></span>Description of the procedure | - |
| Procedure_location | NVARCHAR(100) | - |  | <span id="Procedure_location"></span>Where is the procedure stored | - |

<span id="ProcessingStep"></span>

### ProcessingStep

Records a single data-transformation step (outlier removal, interpolation, smoothing, aggregation, etc.) applied to one or more time series. Each row captures what was done, when, by whom, and with what parameters. The DataLineage table links ProcessingStep rows to their input and output MetaData entries, forming the full processing provenance graph.



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| ProcessingStep_ID | INT **(PK)** | - | ✓ | <span id="ProcessingStep_ID"></span>Surrogate primary key | - |
| Name | NVARCHAR(200) | - | ✓ | <span id="Name"></span>Human-readable name for this processing step (e.g. 'Outlier removal — Hampel filter') | - |
| Description | NVARCHAR(2000) | - |  | <span id="Description"></span>Free-text description of what this step does and why it was applied | - |
| MethodName | NVARCHAR(200) | - |  | <span id="MethodName"></span>Machine-readable method identifier (e.g. 'outlier_removal', 'linear_interpolation'). Maps to a metEAUdata processing function name. | - |
| MethodVersion | NVARCHAR(100) | - |  | <span id="MethodVersion"></span>Version of the method or library used (e.g. 'meteaudata 0.5.1') | - |
| ProcessingType | NVARCHAR(100) | - |  | <span id="ProcessingType"></span>Category of processing applied. Stored as a string mirroring metEAUdata's ProcessingType enum values (e.g. 'Smoothing', 'Filtering', 'Resampling', 'GapFilling'). No lookup table — metEAUdata's enum is the source of truth. Controlled vocabulary: see ProcessingType_set.
 | - |
| Parameters | NVARCHAR(MAX) | - |  | <span id="Parameters"></span>JSON blob of method parameters (e.g. '{"window": 5, "threshold": 3.0}') | - |
| ExecutedAt | DATETIME2(7) | - |  | <span id="ExecutedAt"></span>UTC timestamp when this processing step was executed | - |
| ExecutedByPerson_ID | INT | - |  | <span id="ExecutedByPerson_ID"></span>Person who ran or triggered this processing step. NULL for automated/unattended runs. | FK → [Person.Person_ID](#Person) |

<span id="Project"></span>

### Project

Stores descriptive information about the research or monitoring project for which the data was collected


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Project_ID | INT **(PK)** | - | ✓ | <span id="Project_ID"></span>Link to the Project table | - |
| name | NVARCHAR(100) | - |  | <span id="name"></span>Name of the project | - |
| Description | NVARCHAR(MAX) | - |  | <span id="Description"></span>Description of the project | - |

<span id="ProjectHasContact"></span>

### ProjectHasContact

Links projects to the personnel involved in them


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Contact_ID | INT **(PK)** | - | ✓ | <span id="Contact_ID"></span>Link to the Contact table | FK → [Person.Person_ID](#Person) |
| Project_ID | INT **(PK)** | - | ✓ | <span id="Project_ID"></span>Link to the Project table | FK → [Project.Project_ID](#Project) |

<span id="ProjectHasEquipment"></span>

### ProjectHasEquipment

Links projects to the specific equipment used within them


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Equipment_ID | INT **(PK)** | - | ✓ | <span id="Equipment_ID"></span>Link to the Equipment table | FK → [Equipment.Equipment_ID](#Equipment) |
| Project_ID | INT **(PK)** | - | ✓ | <span id="Project_ID"></span>Link to the Project table | FK → [Project.Project_ID](#Project) |

<span id="ProjectHasSamplingPoints"></span>

### ProjectHasSamplingPoints

Links projects to the sampling points used within them


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Project_ID | INT **(PK)** | - | ✓ | <span id="Project_ID"></span>Link to the Project table | FK → [Project.Project_ID](#Project) |
| Sampling_point_ID | INT **(PK)** | - | ✓ | <span id="Sampling_point_ID"></span>Link to the Sampling_point table | FK → [SamplingPoints.Sampling_point_ID](#SamplingPoints) |

<span id="Purpose"></span>

### Purpose

Stores information about the aim of the measurement (e.g., on-line measurement, laboratory analysis, calibration, validation, cleaning)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Purpose_ID | INT **(PK)** | - | ✓ | <span id="Purpose_ID"></span>A unique ID is generated automatically by MySQL | - |
| Purpose | NVARCHAR(100) | - |  | <span id="Purpose"></span>Purpose of the data collection. For example, "Measurement", "Lab_analysis", "Calibration" and "Cleaning" | - |
| Description | NVARCHAR(MAX) | - |  | <span id="Description"></span>Description of the purpose | - |

<span id="Sample"></span>

### Sample

A discrete physical sample collected at a sampling location or prepared in a laboratory. Supports field samples, calibration standards, blanks, and derived sub-samples via ParentSample_ID.


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Sample_ID | INT **(PK)** | - | ✓ | <span id="Sample_ID"></span>Surrogate primary key | - |
| ParentSample_ID | INT | - |  | <span id="ParentSample_ID"></span>Parent sample this was derived from (e.g., an aliquot of a master standard). NULL for primary samples. | FK → [Sample.Sample_ID](#Sample) |
| SampleCategory | NVARCHAR(50) | - |  | <span id="SampleCategory"></span>Nature of the sample. Controlled vocabulary: Field, Synthetic, Master Standard, Derived Standard, Blank | - |
| Sampling_point_ID | INT | - | ✓ | <span id="Sampling_point_ID"></span>Sampling location where the sample was collected or prepared | FK → [SamplingPoints.Sampling_point_ID](#SamplingPoints) |
| SampledByPerson_ID | INT | - |  | <span id="SampledByPerson_ID"></span>Person who collected the sample | FK → [Person.Person_ID](#Person) |
| Campaign_ID | INT | - |  | <span id="Campaign_ID"></span>Campaign this sample belongs to | FK → [Campaign.Campaign_ID](#Campaign) |
| SampleDateTimeStart | DATETIME2(7) | - | ✓ | <span id="SampleDateTimeStart"></span>Date and time sampling began (UTC) | - |
| SampleDateTimeEnd | DATETIME2(7) | - |  | <span id="SampleDateTimeEnd"></span>Date and time sampling ended (UTC). NULL for instantaneous grab samples. | - |
| SampleType | NVARCHAR(50) | - |  | <span id="SampleType"></span>Method of sample collection. Controlled vocabulary: Grab, Composite24h, Composite8h, Passive, Other | - |
| SampleEquipment_ID | INT | - |  | <span id="SampleEquipment_ID"></span>Equipment used to collect the sample (e.g., auto-sampler) | FK → [Equipment.Equipment_ID](#Equipment) |
| Description | NVARCHAR(500) | - |  | <span id="Description"></span>Additional notes about the sample | - |

<span id="SamplingPoints"></span>

### SamplingPoints

Stores the identification, specific geographical coordinates (Latitude/Longitude/GPS), and description of a particular spot where a sample or measurement is taken


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Sampling_point_ID | INT **(PK)** | - | ✓ | <span id="Sampling_point_ID"></span>Link to the Sampling_point table | - |
| Site_ID | INT | - |  | <span id="Site_ID"></span>A unique ID is generated automatically by MySQL | FK → [Site.Site_ID](#Site) |
| Sampling_point | NVARCHAR(100) | - |  | <span id="Sampling_point"></span>Where the sample was taken. For example: "Inlet", "Outlet" or "Upstream" | - |
| Sampling_location | NVARCHAR(100) | - |  | <span id="Sampling_location"></span>Where the sample was taken. For example: "Biofiltration", "Sewer 01" or "Retention Tank" | - |
| Latitude_GPS | NVARCHAR(100) | - |  | <span id="Latitude_GPS"></span>GPS coordinates. For example: 47°54′25.103"  | - |
| Longitude_GPS | NVARCHAR(100) | - |  | <span id="Longitude_GPS"></span>GPS coordinates. For example: $73^{\circ}47^{\prime}00.024^{\prime\prime}$ | - |
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
| AppliedAt | DATETIME2(7) | - | ✓ | <span id="AppliedAt"></span>UTC datetime when this migration was applied (stored in UTC by convention) | Default: `CURRENT_TIMESTAMP` |
| Description | NVARCHAR(500) | - |  | <span id="Description"></span>Human-readable description of what this migration does | - |
| MigrationScript | NVARCHAR(200) | - |  | <span id="MigrationScript"></span>Filename of the migration script that was applied | - |

<span id="SensorStatusCode"></span>

### SensorStatusCode

Lookup table defining sensor status codes. Each code represents  a state a sensor channel or device can be in. IsOperational  indicates whether data collected in this state should be considered  trustworthy. Severity indicates the urgency (0=normal, 1=warning,  2=fault, 3=critical).



#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| StatusCodeID | INT **(PK)** | - | ✓ | <span id="StatusCodeID"></span>Primary key, manually assigned. This is the value stored in dbo.Value. | - |
| StatusName | NVARCHAR(50) | - | ✓ | <span id="StatusName"></span>Human-readable status name | - |
| Description | NVARCHAR(200) | - |  | <span id="Description"></span>Detailed description of what this status means | - |
| IsOperational | BIT | - | ✓ | <span id="IsOperational"></span>Whether data collected during this status should be considered  trustworthy. true = data is valid, false = data may be invalid.
 | Default: `True` |
| Severity | INT | - | ✓ | <span id="Severity"></span>0=normal, 1=warning, 2=fault, 3=critical | Default: `0` |

<span id="Site"></span>

### Site

Stores general site information, including address, site type, and a link to the associated watershed


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Site_ID | INT **(PK)** | - | ✓ | <span id="Site_ID"></span>A unique ID is generated automatically by MySQL | - |
| Watershed_ID | INT | - |  | <span id="Watershed_ID"></span>Linked to the Watershed table | FK → [Watershed.Watershed_ID](#Watershed) |
| name | NVARCHAR(100) | - |  | <span id="name"></span>Name of the site | - |
| type | NVARCHAR(255) | - |  | <span id="type"></span>For example: "WWTP", "River" or "Sewer_system" | - |
| Description | NVARCHAR(MAX) | - |  | <span id="Description"></span>Description of the site | - |
| Picture | /* UNMAPPED TYPE */ | - |  | <span id="Picture"></span>Picture of the site | - |
| Street_number | NVARCHAR(100) | - |  | <span id="Street_number"></span>Address: number of the street | - |
| Street_name | NVARCHAR(100) | - |  | <span id="Street_name"></span>Address: name of the street | - |
| City | NVARCHAR(255) | - |  | <span id="City"></span>Address: name of the city | - |
| Zip_code | NVARCHAR(100) | - |  | <span id="Zip_code"></span>Address: zip code | - |
| Province | NVARCHAR(255) | - |  | <span id="Province"></span>Address: name of the province | - |
| Country | NVARCHAR(255) | - |  | <span id="Country"></span>Address: name of the country | - |

<span id="Unit"></span>

### Unit

Stores the SI units of measurement (or other relevant units) corresponding to the parameters (e.g., mg/L, g/L, s)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Unit_ID | INT **(PK)** | - | ✓ | <span id="Unit_ID"></span>A unique ID is generated automatically by MySQL | - |
| Unit | NVARCHAR(100) | - |  | <span id="Unit"></span>SI-units only | - |

<span id="UrbanCharacteristics"></span>

### UrbanCharacteristics

Stores the urban land use percentages (e.g., commercial, residential, green spaces) within the watershed


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Watershed_ID | INT **(PK)** | - | ✓ | <span id="Watershed_ID"></span>Linked to the Watershed table | FK → [Watershed.Watershed_ID](#Watershed) |
| Commercial | REAL | - |  | <span id="Commercial"></span>Percentage [%] of commercial areas. For example stores or bank areas | - |
| Green_spaces | REAL | - |  | <span id="Green_spaces"></span>Percentage [%] of green spaces | - |
| Industrial | REAL | - |  | <span id="Industrial"></span>Percentage [%] of industrial areas. For example factories | - |
| Institutional | REAL | - |  | <span id="Institutional"></span>Percentage [%] of institutional areas. For example schools, police stations or city hall | - |
| Residential | REAL | - |  | <span id="Residential"></span>Percentage [%] of residential areas. For example houses or apartment buildings | - |
| Agricultural | REAL | - |  | <span id="Agricultural"></span>Percentage [%] of agricultural land use. For example farm land | - |
| Recreational | REAL | - |  | <span id="Recreational"></span>Percentage [%] of recreational areas. For example parks or sport fields | - |

<span id="Value"></span>

### Value

Stores each measured water quality or quantity value, its time stamp, replicate identification, and the link to its specific metadata set


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Comment_ID | INT | - |  | <span id="Comment_ID"></span>A unique ID is generated automatically by MySQL | FK → [Comments.Comment_ID](#Comments) |
| Metadata_ID | INT | - |  | <span id="Metadata_ID"></span>A unique ID is generated automatically by MySQL | FK → [MetaData.Metadata_ID](#MetaData) |
| Value_ID | INT **(PK)** | - | ✓ | <span id="Value_ID"></span>A unique ID is generated automatically by MySQL | - |
| Value | FLOAT | - |  | <span id="Value"></span>Value of collected data | - |
| Number_of_experiment | INT | - |  | <span id="Number_of_experiment"></span>Number of replica of an experiment | - |
| Timestamp | DATETIME2(7) | - |  | <span id="Timestamp"></span>UTC timestamp for date and time of collected data (stored in UTC by convention) | - |

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

Stores image measurement references with metadata about the image dimensions, format, and storage location


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| ValueImage_ID | BIGINT **(PK)** | - | ✓ | <span id="ValueImage_ID"></span>Surrogate primary key | - |
| Metadata_ID | INT | - | ✓ | <span id="Metadata_ID"></span>References the metadata context for this image | FK → [MetaData.Metadata_ID](#MetaData) |
| Timestamp | DATETIME2(7) | - | ✓ | <span id="Timestamp"></span>UTC timestamp when the image was captured (stored in UTC by convention) | - |
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

Stores 2D binned measurement data as one row per (row-bin, col-bin) cell per timestamp, supporting joint distributions such as particle size-velocity


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Metadata_ID | INT **(PK)** | - | ✓ | <span id="Metadata_ID"></span>References the metadata context for this measurement | FK → [MetaData.Metadata_ID](#MetaData) |
| Timestamp | DATETIME2(7) **(PK)** | - | ✓ | <span id="Timestamp"></span>UTC timestamp of the measurement (stored in UTC by convention) | - |
| RowValueBin_ID | INT **(PK)** | - | ✓ | <span id="RowValueBin_ID"></span>References the bin on the row axis (AxisRole=0 in MetaDataAxis) | FK → [ValueBin.ValueBin_ID](#ValueBin) |
| ColValueBin_ID | INT **(PK)** | - | ✓ | <span id="ColValueBin_ID"></span>References the bin on the column axis (AxisRole=1 in MetaDataAxis) | FK → [ValueBin.ValueBin_ID](#ValueBin) |
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

Stores 1D binned measurement data as one row per bin per timestamp, unifying spectra, particle size distributions, and any other 1D distribution over a physical axis


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Metadata_ID | INT **(PK)** | - | ✓ | <span id="Metadata_ID"></span>References the metadata context for this measurement | FK → [MetaData.Metadata_ID](#MetaData) |
| Timestamp | DATETIME2(7) **(PK)** | - | ✓ | <span id="Timestamp"></span>UTC timestamp of the measurement (stored in UTC by convention) | - |
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
| name | NVARCHAR(100) | - |  | <span id="name"></span>Name of the watershed | - |
| Description | NVARCHAR(MAX) | - |  | <span id="Description"></span>Description of the watershed | - |
| Surface_area | REAL | - |  | <span id="Surface_area"></span>Surface area of the watershed [ha] | - |
| Concentration_time | INT | - |  | <span id="Concentration_time"></span>Concentration time in minutes [min] | - |
| Impervious_surface | REAL | - |  | <span id="Impervious_surface"></span>Percentage of the impervious surface of the watershed in percentage [%] | - |

<span id="WeatherCondition"></span>

### WeatherCondition

Stores descriptive information about the prevailing weather conditions when the measurement was taken (e.g., dry weather, wet weather, snow melt)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Condition_ID | INT **(PK)** | - | ✓ | <span id="Condition_ID"></span>A unique ID is generated automatically by MySQL | - |
| Weather_condition | NVARCHAR(100) | - |  | <span id="Weather_condition"></span>Type of weather condition | - |
| Description | NVARCHAR(MAX) | - |  | <span id="Description"></span>Description of the condition | - |