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
| model_ID | INT | - |  | <span id="model_ID"></span>Link to the Equipment model table | FK → [Equipment_model_ID](#Equipment_model_ID) |
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
| Equipment_model_ID | INT **(PK)** | - | ✓ | <span id="Equipment_model_ID"></span>Link to the Equipment model table | FK → [Equipment_model_ID](#Equipment_model_ID) |
| Parameter_ID | INT **(PK)** | - | ✓ | <span id="Parameter_ID"></span>Link to the Parameter table | FK → [Parameter_ID](#Parameter_ID) |

<span id="EquipmentModelHasProcedures"></span>

### EquipmentModelHasProcedures

Links equipment models to the relevant maintenance procedures


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Equipment_model_ID | INT **(PK)** | - | ✓ | <span id="Equipment_model_ID"></span>Link to the Equipment model table | FK → [Equipment_model_ID](#Equipment_model_ID) |
| Procedure_ID | INT **(PK)** | - | ✓ | <span id="Procedure_ID"></span>Link to the Procedures table | FK → [Procedure_ID](#Procedure_ID) |

<span id="HydrologicalCharacteristics"></span>

### HydrologicalCharacteristics

Stores the hydrological land use percentages (e.g., forest, wetlands, cropland, grassland) within the watershed


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Watershed_ID | INT **(PK)** | - | ✓ | <span id="Watershed_ID"></span>Linked to the Watershed table | - |
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
| Project_ID | INT | - |  | <span id="Project_ID"></span>Links to the research or monitoring project | FK → [Project_ID](#Project_ID) |
| Contact_ID | INT | - |  | <span id="Contact_ID"></span>Links to the person responsible for this measurement series | FK → [Contact_ID](#Contact_ID) |
| Equipment_ID | INT | - |  | <span id="Equipment_ID"></span>Links to the physical instrument that produced the measurements | FK → [Equipment_ID](#Equipment_ID) |
| Parameter_ID | INT | - |  | <span id="Parameter_ID"></span>Links to the measured analyte or parameter (e.g. TSS, pH) | FK → [Parameter_ID](#Parameter_ID) |
| Procedure_ID | INT | - |  | <span id="Procedure_ID"></span>Links to the standard operating procedure used | FK → [Procedure_ID](#Procedure_ID) |
| Unit_ID | INT | - |  | <span id="Unit_ID"></span>Links to the measurement unit (e.g. mg/L) | FK → [Unit_ID](#Unit_ID) |
| Purpose_ID | INT | - |  | <span id="Purpose_ID"></span>Links to the measurement purpose (online, lab, calibration, validation) | FK → [Purpose_ID](#Purpose_ID) |
| Sampling_point_ID | INT | - |  | <span id="Sampling_point_ID"></span>Links to the physical sampling location | FK → [Sampling_point_ID](#Sampling_point_ID) |
| Condition_ID | INT | - |  | <span id="Condition_ID"></span>Links to the prevailing weather condition at time of measurement | FK → [Condition_ID](#Condition_ID) |

<span id="Parameter"></span>

### Parameter

Stores the different water quality or quantity parameters that are measured (e.g., pH, TSS, N-components)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Unit_ID | INT | - |  | <span id="Unit_ID"></span>A unique ID is generated automatically by MySQL | FK → [Unit_ID](#Unit_ID) |
| Parameter | NVARCHAR(100) | - |  | <span id="Parameter"></span>Name of the parameter | - |
| Parameter_ID | INT **(PK)** | - | ✓ | <span id="Parameter_ID"></span>Link to the Parameter table | - |
| Description | NVARCHAR(MAX) | - |  | <span id="Description"></span>Description of the parameter | - |

<span id="ParameterHasProcedures"></span>

### ParameterHasProcedures

Links parameters to the relevant measurement procedures


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Procedure_ID | INT **(PK)** | - | ✓ | <span id="Procedure_ID"></span>Link to the Procedures table | FK → [Procedure_ID](#Procedure_ID) |
| Parameter_ID | INT **(PK)** | - | ✓ | <span id="Parameter_ID"></span>Link to the Parameter table | FK → [Parameter_ID](#Parameter_ID) |

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
| Contact_ID | INT **(PK)** | - | ✓ | <span id="Contact_ID"></span>Link to the Contact table | FK → [Contact_ID](#Contact_ID) |
| Project_ID | INT **(PK)** | - | ✓ | <span id="Project_ID"></span>Link to the Project table | FK → [Project_ID](#Project_ID) |

<span id="ProjectHasEquipment"></span>

### ProjectHasEquipment

Links projects to the specific equipment used within them


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Equipment_ID | INT **(PK)** | - | ✓ | <span id="Equipment_ID"></span>Link to the Equipment table | FK → [Equipment_ID](#Equipment_ID) |
| Project_ID | INT **(PK)** | - | ✓ | <span id="Project_ID"></span>Link to the Project table | FK → [Project_ID](#Project_ID) |

<span id="ProjectHasSamplingPoints"></span>

### ProjectHasSamplingPoints

Links projects to the sampling points used within them


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Project_ID | INT **(PK)** | - | ✓ | <span id="Project_ID"></span>Link to the Project table | FK → [Project_ID](#Project_ID) |
| Sampling_point_ID | INT **(PK)** | - | ✓ | <span id="Sampling_point_ID"></span>Link to the Sampling_point table | FK → [Sampling_point_ID](#Sampling_point_ID) |

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
| Site_ID | INT | - |  | <span id="Site_ID"></span>A unique ID is generated automatically by MySQL | FK → [Site_ID](#Site_ID) |
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
| AppliedAt | DATETIME2(7) | - | ✓ | <span id="AppliedAt"></span>Datetime when this migration was applied | Default: `CURRENT_TIMESTAMP` |
| Description | NVARCHAR(500) | - |  | <span id="Description"></span>Human-readable description of what this migration does | - |
| MigrationScript | NVARCHAR(200) | - |  | <span id="MigrationScript"></span>Filename of the migration script that was applied | - |

<span id="Site"></span>

### Site

Stores general site information, including address, site type, and a link to the associated watershed


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Site_ID | INT **(PK)** | - | ✓ | <span id="Site_ID"></span>A unique ID is generated automatically by MySQL | - |
| Watershed_ID | INT | - |  | <span id="Watershed_ID"></span>Linked to the Watershed table | FK → [Watershed_ID](#Watershed_ID) |
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
| Watershed_ID | INT **(PK)** | - | ✓ | <span id="Watershed_ID"></span>Linked to the Watershed table | - |
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
| Comment_ID | INT | - |  | <span id="Comment_ID"></span>A unique ID is generated automatically by MySQL | FK → [Comment_ID](#Comment_ID) |
| Metadata_ID | INT | - |  | <span id="Metadata_ID"></span>A unique ID is generated automatically by MySQL | FK → [Metadata_ID](#Metadata_ID) |
| Value_ID | INT **(PK)** | - | ✓ | <span id="Value_ID"></span>A unique ID is generated automatically by MySQL | - |
| Value | FLOAT | - |  | <span id="Value"></span>Value of collected data | - |
| Number_of_experiment | INT | - |  | <span id="Number_of_experiment"></span>Number of replica of an experiment | - |
| Timestamp | INT | - |  | <span id="Timestamp"></span>Unix timestamp combining date and time of collected data | - |

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