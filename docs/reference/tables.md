# Database Tables

This documentation is auto-generated from dictionary.json.


## Tables


<span id="comments"></span>

### Comments

Stores any additional textual comments, notes, or observations related to a specific measured value


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Comment | ntext(1073741823) | - |  | <span id="Comment"></span>Comment on the data in the Value table | - |
| Comment ID | int **(PK)** | - |  | <span id="Comment_ID"></span>A unique ID is generated automatically by MySQL | - |

<span id="contact"></span>

### Contact

Stores detailed personal and professional information for people involved in projects (e.g., name, affiliation, function, e-mail, phone)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Company | ntext(1073741823) | - |  | <span id="Company"></span>Company name | - |
| Contact ID | int **(PK)** | - |  | <span id="Contact_ID"></span>Link to the Contact table | - |
| Email | nvarchar(100) | - |  | <span id="Email"></span>E-mail address | - |
| First Name | nvarchar(255) | - |  | <span id="First_name"></span>First name of the contact | - |
| Function | ntext(1073741823) | - |  | <span id="Function"></span>More detailed description about the functions | - |
| Last Name | nvarchar(100) | - |  | <span id="Last_name"></span>Last name of the contact | - |
| Linkedin | nvarchar(100) | - |  | <span id="Linkedin"></span>LinkedIn account | - |
| Office Number | nvarchar(100) | - |  | <span id="Office_number"></span>Number of the office | - |
| Phone | nvarchar(100) | - |  | <span id="Phone"></span>Phone number | - |
| Skype Name | nvarchar(100) | - |  | <span id="Skype_name"></span>Skype name | - |
| Status | nvarchar(255) | - |  | <span id="Status"></span>Status of the person. For example: "Master student", "Postdoc" or "Intern" | - |
| Website | nvarchar(60) | - |  | <span id="Website"></span>Website URL of the contact or organization | - |
| Contact City | nvarchar(255) | - |  | <span id="contact_City"></span>Address: name of the city | - |
| Contact Country | nvarchar(255) | - |  | <span id="contact_Country"></span>Address: name of the country | - |
| Contact Street Name | nvarchar(100) | - |  | <span id="contact_Street_name"></span>Address: name of the street | - |
| Contact Street Number | nvarchar(100) | - |  | <span id="contact_Street_number"></span>Address: number of the street | - |
| Contact Zip Code | nvarchar(45) | - |  | <span id="contact_Zip_code"></span>Address: zip code | - |

<span id="equipment"></span>

### Equipment

Stores information about a specific, physical piece of equipment (e.g., serial number, owner, purchase date, storage location)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Equipment ID | int **(PK)** | - |  | <span id="Equipment_ID"></span>Link to the Equipment table | - |
| Equipment IDentifier | nvarchar(100) | - |  | <span id="Equipment_identifier"></span>Identification name of the equipments | - |
| Equipment Model ID | int | - |  | <span id="Equipment_model_ID"></span>Link to the Equipment model table | FK → [Equipment_model_ID](#Equipment_model_ID) |
| Owner | ntext(1073741823) | - |  | <span id="Owner"></span>Name of the owner of the equipment | - |
| Purchase Date | date | - |  | <span id="Purchase_date"></span>Date when the equipment was bought: 'YYYY-MM-DD | - |
| Serial Number | nvarchar(100) | - |  | <span id="Serial_number"></span>Serial number of the equipment | - |
| Storage Location | nvarchar(100) | - |  | <span id="Storage_location"></span>Where is the procedure stored | - |

<span id="equipment_model"></span>

### Equipment Model

Stores detailed, non-redundant specifications for a specific sensor or instrument model (e.g., manufacturer, functions, method)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Equipment Model | nvarchar(100) | - |  | <span id="Equipment_model"></span>Name of the equipment model. For example: ammo::lyser | - |
| Equipment Model ID | int **(PK)** | - |  | <span id="Equipment_model_ID"></span>Link to the Equipment model table | - |
| Functions | ntext(1073741823) | - |  | <span id="Functions"></span>Description of the functions of the equipment | - |
| Manual Location | nvarchar(100) | - |  | <span id="Manual_location"></span>Location where the manual is stored | - |
| Manufacturer | nvarchar(100) | - |  | <span id="Manufacturer"></span>Name of the manufacturer | - |
| Method | nvarchar(100) | - |  | <span id="Method"></span>Method behind the equipment | - |

<span id="equipment_model_has_Parameter"></span>

### Equipment Model Has Parameter

Links equipment models to the parameters they can measure


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Equipment Model ID | int **(CK-1)** | - |  | <span id="Equipment_model_ID"></span>Link to the Equipment model table | FK → [Equipment_model_ID](#Equipment_model_ID) |
| Parameter ID | int **(CK-2)** | - |  | <span id="Parameter_ID"></span>Link to the Parameter table | - |

<span id="equipment_model_has_procedures"></span>

### Equipment Model Has Procedures

Links equipment models to the relevant maintenance procedures


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Equipment Model ID | int **(CK-1)** | - |  | <span id="Equipment_model_ID"></span>Link to the Equipment model table | FK → [Equipment_model_ID](#Equipment_model_ID) |
| Procedure ID | int **(CK-2)** | - |  | <span id="Procedure_ID"></span>Link to the Procedures table | FK → [Procedure_ID](#Procedure_ID) |

<span id="hydrological_characteristics"></span>

### Hydrological Characteristics

Stores the hydrological land use percentages (e.g., forest, wetlands, cropland, grassland) within the watershed


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Cropland | real | - |  | <span id="Cropland"></span>Percentage [%] of croplands | - |
| Forest | real | - |  | <span id="Forest"></span>Percentage [%] of forest areas | - |
| Grassland | real | - |  | <span id="Grassland"></span>Percentage [%] of grasslands | - |
| Meadow | real | - |  | <span id="Meadow"></span>Percentage [%] of meadow areas | - |
| Urban Area | real | - |  | <span id="Urban_area"></span>Percentage [%] of urban areas | - |
| Watershed ID | int **(PK)** | - |  | <span id="Watershed_ID"></span>Linked to the Watershed table | FK → [Watershed_ID](#Watershed_ID) |
| Wetlands | real | - |  | <span id="Wetlands"></span>Percentage [%] of wetlands | - |

<span id="metadata"></span>

### Metadata

Contains a list of all existing unique metadata combinations (represented by a series of foreign keys/IDs) that describe a single measurement


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Condition ID | int | - |  | <span id="Condition_ID"></span>A unique ID is generated automatically by MySQL | FK → [Condition_ID](#Condition_ID) |
| Contact ID | int | - |  | <span id="Contact_ID"></span>Link to the Contact table | FK → [Contact_ID](#Contact_ID) |
| Equipment ID | int | - |  | <span id="Equipment_ID"></span>Link to the Equipment table | FK → [Equipment_ID](#Equipment_ID) |
| Metadata ID | int **(PK)** | - |  | <span id="Metadata_ID"></span>A unique ID is generated automatically by MySQL | - |
| Parameter ID | int | - |  | <span id="Parameter_ID"></span>Link to the Parameter table | FK → [Parameter_ID](#Parameter_ID) |
| Procedure ID | int | - |  | <span id="Procedure_ID"></span>Link to the Procedures table | FK → [Procedure_ID](#Procedure_ID) |
| Project ID | int | - |  | <span id="Project_ID"></span>Link to the Project table | FK → [Project_ID](#Project_ID) |
| Purpose ID | int | - |  | <span id="Purpose_ID"></span>A unique ID is generated automatically by MySQL | FK → [Purpose_ID](#Purpose_ID) |
| Sampling Point ID | int | - |  | <span id="Sampling_point_ID"></span>Link to the Sampling_point table | FK → [Sampling_point_ID](#Sampling_point_ID) |
| Unit ID | int | - |  | <span id="Unit_ID"></span>A unique ID is generated automatically by MySQL | FK → [Unit_ID](#Unit_ID) |

<span id="parameter"></span>

### Parameter

Stores the different water quality or quantity parameters that are measured (e.g., pH, TSS, N-components)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Parameter | nvarchar(100) | - |  | <span id="Parameter"></span>Name of the parameter | - |
| Parameter ID | int **(PK)** | - |  | <span id="Parameter_ID"></span>Link to the Parameter table | - |
| Unit ID | int | - |  | <span id="Unit_ID"></span>A unique ID is generated automatically by MySQL | FK → [Unit_ID](#Unit_ID) |
| Parameter Description | ntext(1073741823) | - |  | <span id="parameter_Description"></span>Description of the parameter | - |

<span id="parameter_has_procedures"></span>

### Parameter Has Procedures

Links parameters to the relevant measurement procedures


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Parameter ID | int **(CK-1)** | - |  | <span id="Parameter_ID"></span>Link to the Parameter table | - |
| Procedure ID | int **(CK-2)** | - |  | <span id="Procedure_ID"></span>Link to the Procedures table | FK → [Procedure_ID](#Procedure_ID) |

<span id="procedures"></span>

### Procedures

Stores details for different measurement procedures (e.g., calibration, validation, standard operating procedures, ISO methods)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Procedure ID | int **(PK)** | - |  | <span id="Procedure_ID"></span>Link to the Procedures table | - |
| Procedure Location | nvarchar(100) | - |  | <span id="Procedure_location"></span>Where is the procedure stored | - |
| Procedure Name | nvarchar(100) | - |  | <span id="Procedure_name"></span>Title name of the procedure | - |
| Procedure Type | nvarchar(255) | - |  | <span id="Procedure_type"></span>Type of the procedure. For example, SOP | - |
| Procedures Description | ntext(1073741823) | - |  | <span id="procedures_Description"></span>Description of the procedure | - |

<span id="project"></span>

### Project

Stores descriptive information about the research or monitoring project for which the data was collected


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Project ID | int **(PK)** | - |  | <span id="Project_ID"></span>Link to the Project table | - |
| Project Name | nvarchar(100) | - |  | <span id="Project_name"></span>Name of the project | - |
| Project Description | ntext(1073741823) | - |  | <span id="project_Description"></span>Description of the project | - |

<span id="project_has_contact"></span>

### Project Has Contact

Links projects to the personnel involved in them


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Contact ID | int **(CK-2)** | - |  | <span id="Contact_ID"></span>Link to the Contact table | FK → [Contact_ID](#Contact_ID) |
| Project ID | int **(CK-1)** | - |  | <span id="Project_ID"></span>Link to the Project table | FK → [Project_ID](#Project_ID) |

<span id="project_has_equipment"></span>

### Project Has Equipment

Links projects to the specific equipment used within them


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Equipment ID | int **(CK-2)** | - |  | <span id="Equipment_ID"></span>Link to the Equipment table | FK → [Equipment_ID](#Equipment_ID) |
| Project ID | int **(CK-1)** | - |  | <span id="Project_ID"></span>Link to the Project table | FK → [Project_ID](#Project_ID) |

<span id="project_has_sampling_points"></span>

### Project Has Sampling Points

Links projects to the sampling points used within them


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Project ID | int **(CK-1)** | - |  | <span id="Project_ID"></span>Link to the Project table | FK → [Project_ID](#Project_ID) |
| Sampling Point ID | int **(CK-2)** | - |  | <span id="Sampling_point_ID"></span>Link to the Sampling_point table | FK → [Sampling_point_ID](#Sampling_point_ID) |

<span id="purpose"></span>

### Purpose

Stores information about the aim of the measurement (e.g., on-line measurement, laboratory analysis, calibration, validation, cleaning)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Purpose | nvarchar(100) | - |  | <span id="Purpose"></span>Purpose of the data collection. For example, "Measurement", "Lab_analysis", "Calibration" and "Cleaning" | - |
| Purpose ID | int **(PK)** | - |  | <span id="Purpose_ID"></span>A unique ID is generated automatically by MySQL | - |
| Purpose Description | ntext(1073741823) | - |  | <span id="purpose_Description"></span>Description of the purpose | - |

<span id="sampling_points"></span>

### Sampling Points

Stores the identification, specific geographical coordinates (Latitude/Longitude/GPS), and description of a particular spot where a sample or measurement is taken


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Latitude GPS | nvarchar(100) | - |  | <span id="Latitude_GPS"></span>GPS coordinates. For example: 47°54′25.103"  | - |
| Longitude GPS | nvarchar(100) | - |  | <span id="Longitude_GPS"></span>GPS coordinates. For example: $73^{\circ}47^{\prime}00.024^{\prime\prime}$ | - |
| Pictures | BLOB | - |  | <span id="Pictures"></span>Picture of the site | - |
| Sampling Location | nvarchar(100) | - |  | <span id="Sampling_location"></span>Where the sample was taken. For example: "Biofiltration", "Sewer 01" or "Retention Tank" | - |
| Sampling Point | nvarchar(100) | - |  | <span id="Sampling_point"></span>Where the sample was taken. For example: "Inlet", "Outlet" or "Upstream" | - |
| Sampling Point ID | int **(PK)** | - |  | <span id="Sampling_point_ID"></span>Link to the Sampling_point table | - |
| Site ID | int | - |  | <span id="Site_ID"></span>A unique ID is generated automatically by MySQL | FK → [Site_ID](#Site_ID) |
| Sampling Points Description | ntext(1073741823) | - |  | <span id="sampling_points_Description"></span>Description of the sampling point | - |

<span id="site"></span>

### Site

Stores general site information, including address, site type, and a link to the associated watershed


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Picture | image(2147483647) | - |  | <span id="Picture"></span>Picture of the site | - |
| Province | nvarchar(255) | - |  | <span id="Province"></span>Address: name of the province | - |
| Site ID | int **(PK)** | - |  | <span id="Site_ID"></span>A unique ID is generated automatically by MySQL | - |
| Site Name | nvarchar(100) | - |  | <span id="Site_name"></span>Name of the site | - |
| Site Type | nvarchar(255) | - |  | <span id="Site_type"></span>For example: "WWTP", "River" or "Sewer_system" | - |
| Watershed ID | int | - |  | <span id="Watershed_ID"></span>Linked to the Watershed table | FK → [Watershed_ID](#Watershed_ID) |
| Site City | nvarchar(255) | - |  | <span id="site_City"></span>Address: name of the city | - |
| Site Country | nvarchar(255) | - |  | <span id="site_Country"></span>Address: name of the country | - |
| Site Description | ntext(1073741823) | - |  | <span id="site_Description"></span>Description of the site | - |
| Site Street Name | nvarchar(100) | - |  | <span id="site_Street_name"></span>Address: name of the street | - |
| Site Street Number | nvarchar(100) | - |  | <span id="site_Street_number"></span>Address: number of the street | - |
| Site Zip Code | nvarchar(100) | - |  | <span id="site_Zip_code"></span>Address: zip code | - |

<span id="unit"></span>

### Unit

Stores the SI units of measurement (or other relevant units) corresponding to the parameters (e.g., mg/L, g/L, s)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Unit | nvarchar(100) | - |  | <span id="Unit"></span>SI-units only | - |
| Unit ID | int **(PK)** | - |  | <span id="Unit_ID"></span>A unique ID is generated automatically by MySQL | - |

<span id="urban_characteristics"></span>

### Urban Characteristics

Stores the urban land use percentages (e.g., commercial, residential, green spaces) within the watershed


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Agricultural | real | - |  | <span id="Agricultural"></span>Percentage [%] of agricultural land use. For example farm land | - |
| Commercial | real | - |  | <span id="Commercial"></span>Percentage [%] of commercial areas. For example stores or bank areas | - |
| Green Spaces | real | - |  | <span id="Green_spaces"></span>Percentage [%] of green spaces | - |
| Industrial | real | - |  | <span id="Industrial"></span>Percentage [%] of industrial areas. For example factories | - |
| Institutional | real | - |  | <span id="Institutional"></span>Percentage [%] of institutional areas. For example schools, police stations or city hall | - |
| Recreational | real | - |  | <span id="Recreational"></span>Percentage [%] of recreational areas. For example parks or sport fields | - |
| Residential | real | - |  | <span id="Residential"></span>Percentage [%] of residential areas. For example houses or apartment buildings | - |
| Watershed ID | int **(PK)** | - |  | <span id="Watershed_ID"></span>Linked to the Watershed table | FK → [Watershed_ID](#Watershed_ID) |

<span id="value"></span>

### Value

Stores each measured water quality or quantity value, its time stamp, replicate identification, and the link to its specific metadata set


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Comment ID | int | - |  | <span id="Comment_ID"></span>A unique ID is generated automatically by MySQL | FK → [Comment_ID](#Comment_ID) |
| Metadata ID | int | - |  | <span id="Metadata_ID"></span>A unique ID is generated automatically by MySQL | FK → [Metadata_ID](#Metadata_ID) |
| Number Of Experiment | numeric | - |  | <span id="Number_of_experiment"></span>Number of replica of an experiment | - |
| Timestamp | int | - |  | <span id="Timestamp"></span>Unix timestamp combining date and time of collected data | - |
| Value | float | - |  | <span id="Value"></span>Value of collected data | - |
| Value ID | int **(PK)** | - |  | <span id="Value_ID"></span>A unique ID is generated automatically by MySQL | - |

<span id="watershed"></span>

### Watershed

Stores general information about the watershed area, including surface area, concentration time, and impervious surface percentage


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Concentration Time | int | - |  | <span id="Concentration_time"></span>Concentration time in minutes [min] | - |
| Impervious Surface | real | - |  | <span id="Impervious_surface"></span>Percentage of the impervious surface of the watershed in percentage [%] | - |
| Surface Area | real | - |  | <span id="Surface_area"></span>Surface area of the watershed [ha] | - |
| Watershed ID | int **(PK)** | - |  | <span id="Watershed_ID"></span>Linked to the Watershed table | - |
| Watershed Name | nvarchar(100) | - |  | <span id="Watershed_name"></span>Name of the watershed | - |
| Watershed Description | ntext(1073741823) | - |  | <span id="watershed_Description"></span>Description of the watershed | - |

<span id="weather_condition"></span>

### Weather Condition

Stores descriptive information about the prevailing weather conditions when the measurement was taken (e.g., dry weather, wet weather, snow melt)


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Condition ID | int **(PK)** | - |  | <span id="Condition_ID"></span>A unique ID is generated automatically by MySQL | - |
| Weather Condition | nvarchar(100) | - |  | <span id="Weather_condition"></span>Type of weather condition | - |
| Weather Condition Description | ntext(1073741823) | - |  | <span id="weather_condition_Description"></span>Description of the condition | - |