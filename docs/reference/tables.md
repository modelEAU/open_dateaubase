# Database Tables

This documentation is auto-generated from dictionary.json.


## Tables


<span id="Comments"></span>

### Comments

Stores any additional textual comments, notes, or observations related to a specific measured value


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Comment_ID | INT **(PK)** | - | ✓ | <span id="Comment_ID"></span>A unique ID is generated automatically by MySQL | - |
| Comment | NVARCHAR(MAX) | - |  | <span id="Comment"></span>Comment on the data in the Value table | - |

<span id="Contact"></span>

### Contact

Stores detailed personal and professional information for people involved in projects (e.g., name, affiliation, function, e-mail, phone)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Contact_ID | INT **(PK)** | - | ✓ | <span id="Contact_ID"></span>Link to the Contact table | - |
| Last_name | NVARCHAR(100) | - |  | <span id="Last_name"></span>Last name of the contact | - |
| First_name | NVARCHAR(255) | - |  | <span id="First_name"></span>First name of the contact | - |
| Company | NVARCHAR(MAX) | - |  | <span id="Company"></span>Company name | - |
| Status | NVARCHAR(255) | - |  | <span id="Status"></span>Status of the person. For example: "Master student", "Postdoc" or "Intern" | - |
| Function | NVARCHAR(MAX) | - |  | <span id="Function"></span>More detailed description about the functions | - |
| Office_number | NVARCHAR(100) | - |  | <span id="Office_number"></span>Number of the office | - |
| Email | NVARCHAR(100) | - |  | <span id="Email"></span>E-mail address | - |
| Phone | NVARCHAR(100) | - |  | <span id="Phone"></span>Phone number | - |
| Skype_name | NVARCHAR(100) | - |  | <span id="Skype_name"></span>Skype name | - |
| Linkedin | NVARCHAR(100) | - |  | <span id="Linkedin"></span>LinkedIn account | - |
| Street_number | NVARCHAR(100) | - |  | <span id="Street_number"></span>Address: number of the street | - |
| Street_name | NVARCHAR(100) | - |  | <span id="Street_name"></span>Address: name of the street | - |
| City | NVARCHAR(255) | - |  | <span id="City"></span>Address: name of the city | - |
| Zip_code | NVARCHAR(45) | - |  | <span id="Zip_code"></span>Address: zip code | - |
| Country | NVARCHAR(255) | - |  | <span id="Country"></span>Address: name of the country | - |
| Website | NVARCHAR(60) | - |  | <span id="Website"></span>Website URL of the contact or organization | - |

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

<span id="MetaData"></span>

### MetaData

Central context aggregator linking every measurement to its full provenance (project, contact, equipment, parameter, procedure, unit, purpose, sampling point, and condition)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Metadata_ID | INT **(PK)** | - | ✓ | <span id="Metadata_ID"></span>Surrogate primary key | - |
| Project_ID | INT | - |  | <span id="Project_ID"></span>Links to the research or monitoring project | FK → [Project.Project_ID](#Project) |
| Contact_ID | INT | - |  | <span id="Contact_ID"></span>Links to the person responsible for this measurement series | FK → [Contact.Contact_ID](#Contact) |
| Equipment_ID | INT | - |  | <span id="Equipment_ID"></span>Links to the physical instrument that produced the measurements | FK → [Equipment.Equipment_ID](#Equipment) |
| Parameter_ID | INT | - |  | <span id="Parameter_ID"></span>Links to the measured analyte or parameter (e.g. TSS, pH) | FK → [Parameter.Parameter_ID](#Parameter) |
| Procedure_ID | INT | - |  | <span id="Procedure_ID"></span>Links to the standard operating procedure used | FK → [Procedures.Procedure_ID](#Procedures) |
| Unit_ID | INT | - |  | <span id="Unit_ID"></span>Links to the measurement unit (e.g. mg/L) | FK → [Unit.Unit_ID](#Unit) |
| Purpose_ID | INT | - |  | <span id="Purpose_ID"></span>Links to the measurement purpose (online, lab, calibration, validation) | FK → [Purpose.Purpose_ID](#Purpose) |
| Sampling_point_ID | INT | - |  | <span id="Sampling_point_ID"></span>Links to the physical sampling location | FK → [SamplingPoints.Sampling_point_ID](#SamplingPoints) |
| Condition_ID | INT | - |  | <span id="Condition_ID"></span>Links to the prevailing weather condition at time of measurement | FK → [WeatherCondition.Condition_ID](#WeatherCondition) |
| ValueType_ID | INT | - | ✓ | <span id="ValueType_ID"></span>Identifies the shape of stored values (1=Scalar, 2=Vector, 3=Matrix, 4=Image) | FK → [ValueType.ValueType_ID](#ValueType)<br>Default: `1` |

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
| Contact_ID | INT **(PK)** | - | ✓ | <span id="Contact_ID"></span>Link to the Contact table | FK → [Contact.Contact_ID](#Contact) |
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