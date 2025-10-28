# Database Tables

This documentation is auto-generated from the Parts metadata table.


## Tables


<span id="comments"></span>

### Comments

Table for Comments


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Comment | ntext(1073741823) | - |  | <span id="Comment"></span>Comment in comments table | - |
| Comment ID | int **(PK)** | - |  | <span id="Comment_ID"></span>Identifier for comments, also used in 1 other table(s) | - |

<span id="contact"></span>

### Contact

Table for Contact


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Company | ntext(1073741823) | - |  | <span id="Company"></span>Company in contact table | - |
| Contact ID | int **(PK)** | - |  | <span id="Contact_ID"></span>Identifier for contact, also used in 2 other table(s) | - |
| Email | nvarchar(100) | - |  | <span id="Email"></span>Email in contact table | - |
| First Name | nvarchar(255) | - |  | <span id="First_name"></span>First Name in contact table | - |
| Function | ntext(1073741823) | - |  | <span id="Function"></span>Function in contact table | - |
| Last Name | nvarchar(100) | - |  | <span id="Last_name"></span>Last Name in contact table | - |
| Linkedin | nvarchar(100) | - |  | <span id="Linkedin"></span>Linkedin in contact table | - |
| Office Number | nvarchar(100) | - |  | <span id="Office_number"></span>Office Number in contact table | - |
| Phone | nvarchar(100) | - |  | <span id="Phone"></span>Phone in contact table | - |
| Skype Name | nvarchar(100) | - |  | <span id="Skype_name"></span>Skype Name in contact table | - |
| Status | nvarchar(255) | - |  | <span id="Status"></span>Status in contact table | - |
| Website | nvarchar(60) | - |  | <span id="Website"></span>Website in contact table | - |
| Contact City | nvarchar(255) | - |  | <span id="contact_City"></span>Contact City in contact table | - |
| Contact Country | nvarchar(255) | - |  | <span id="contact_Country"></span>Contact Country in contact table | - |
| Contact Street Name | nvarchar(100) | - |  | <span id="contact_Street_name"></span>Contact Street Name in contact table | - |
| Contact Street Number | nvarchar(100) | - |  | <span id="contact_Street_number"></span>Contact Street Number in contact table | - |
| Contact Zip Code | nvarchar(45) | - |  | <span id="contact_Zip_code"></span>Contact Zip Code in contact table | - |

<span id="equipment"></span>

### Equipment

Table for Equipment


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Equipment ID | int **(PK)** | - |  | <span id="Equipment_ID"></span>Identifier for equipment, also used in 2 other table(s) | - |
| Equipment IDentifier | nvarchar(100) | - |  | <span id="Equipment_identifier"></span>Equipment IDentifier in equipment table | - |
| Equipment Model ID | int | - |  | <span id="Equipment_model_ID"></span>Identifier for equipment_model, also used in 3 other table(s) | FK → [Equipment_model_ID](#Equipment_model_ID) |
| Owner | ntext(1073741823) | - |  | <span id="Owner"></span>Owner in equipment table | - |
| Purchase Date | date | - |  | <span id="Purchase_date"></span>Purchase Date in equipment table | - |
| Serial Number | nvarchar(100) | - |  | <span id="Serial_number"></span>Serial Number in equipment table | - |
| Storage Location | nvarchar(100) | - |  | <span id="Storage_location"></span>Storage Location in equipment table | - |

<span id="equipment_model"></span>

### Equipment Model

Table for Equipment Model


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Equipment Model | nvarchar(100) | - |  | <span id="Equipment_model"></span>Equipment Model in equipment_model table | - |
| Equipment Model ID | int **(PK)** | - |  | <span id="Equipment_model_ID"></span>Identifier for equipment_model, also used in 3 other table(s) | - |
| Functions | ntext(1073741823) | - |  | <span id="Functions"></span>Functions in equipment_model table | - |
| Manual Location | nvarchar(100) | - |  | <span id="Manual_location"></span>Manual Location in equipment_model table | - |
| Manufacturer | nvarchar(100) | - |  | <span id="Manufacturer"></span>Manufacturer in equipment_model table | - |
| Method | nvarchar(100) | - |  | <span id="Method"></span>Method in equipment_model table | - |

<span id="equipment_model_has_Parameter"></span>

### Equipment Model Has Parameter

Table for Equipment Model Has Parameter


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Equipment Model ID | int **(CK-1)** | - |  | <span id="Equipment_model_ID"></span>Identifier for equipment_model, also used in 3 other table(s) | - |
| Parameter ID | int **(CK-2)** | - |  | <span id="Parameter_ID"></span>Identifier for parameter, also used in 3 other table(s) | - |

<span id="equipment_model_has_procedures"></span>

### Equipment Model Has Procedures

Table for Equipment Model Has Procedures


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Equipment Model ID | int **(CK-1)** | - |  | <span id="Equipment_model_ID"></span>Identifier for equipment_model, also used in 3 other table(s) | - |
| Procedure ID | int **(CK-2)** | - |  | <span id="Procedure_ID"></span>Identifier for procedures, also used in 3 other table(s) | - |

<span id="hydrological_characteristics"></span>

### Hydrological Characteristics

Table for Hydrological Characteristics


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Cropland | real | - |  | <span id="Cropland"></span>Cropland in hydrological_characteristics table | - |
| Forest | real | - |  | <span id="Forest"></span>Forest in hydrological_characteristics table | - |
| Grassland | real | - |  | <span id="Grassland"></span>Grassland in hydrological_characteristics table | - |
| Meadow | real | - |  | <span id="Meadow"></span>Meadow in hydrological_characteristics table | - |
| Urban Area | real | - |  | <span id="Urban_area"></span>Urban Area in hydrological_characteristics table | - |
| Watershed ID | int **(PK)** | - |  | <span id="Watershed_ID"></span>Identifier for hydrological_characteristics, also used in 3 other table(s) | - |
| Wetlands | real | - |  | <span id="Wetlands"></span>Wetlands in hydrological_characteristics table | - |

<span id="metadata"></span>

### Metadata

Table for Metadata


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Condition ID | int | - |  | <span id="Condition_ID"></span>Identifier for weather_condition, also used in 1 other table(s) | FK → [Condition_ID](#Condition_ID) |
| Contact ID | int | - |  | <span id="Contact_ID"></span>Identifier for contact, also used in 2 other table(s) | FK → [Contact_ID](#Contact_ID) |
| Equipment ID | int | - |  | <span id="Equipment_ID"></span>Identifier for equipment, also used in 2 other table(s) | FK → [Equipment_ID](#Equipment_ID) |
| Metadata ID | int **(PK)** | - |  | <span id="Metadata_ID"></span>Identifier for metadata, also used in 1 other table(s) | - |
| Parameter ID | int | - |  | <span id="Parameter_ID"></span>Identifier for parameter, also used in 3 other table(s) | FK → [Parameter_ID](#Parameter_ID) |
| Procedure ID | int | - |  | <span id="Procedure_ID"></span>Identifier for procedures, also used in 3 other table(s) | FK → [Procedure_ID](#Procedure_ID) |
| Project ID | int | - |  | <span id="Project_ID"></span>Identifier for project, also used in 4 other table(s) | FK → [Project_ID](#Project_ID) |
| Purpose ID | int | - |  | <span id="Purpose_ID"></span>Identifier for purpose, also used in 1 other table(s) | FK → [Purpose_ID](#Purpose_ID) |
| Sampling Point ID | int | - |  | <span id="Sampling_point_ID"></span>Identifier for sampling_points, also used in 2 other table(s) | FK → [Sampling_point_ID](#Sampling_point_ID) |
| Unit ID | int | - |  | <span id="Unit_ID"></span>Identifier for unit, also used in 2 other table(s) | FK → [Unit_ID](#Unit_ID) |

<span id="parameter"></span>

### Parameter

Table for Parameter


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Parameter | nvarchar(100) | - |  | <span id="Parameter"></span>Parameter in parameter table | - |
| Parameter ID | int **(PK)** | - |  | <span id="Parameter_ID"></span>Identifier for parameter, also used in 3 other table(s) | - |
| Unit ID | int | - |  | <span id="Unit_ID"></span>Identifier for unit, also used in 2 other table(s) | FK → [Unit_ID](#Unit_ID) |
| Parameter Description | ntext(1073741823) | - |  | <span id="parameter_Description"></span>Parameter Description in parameter table | - |

<span id="parameter_has_procedures"></span>

### Parameter Has Procedures

Table for Parameter Has Procedures


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Parameter ID | int **(CK-1)** | - |  | <span id="Parameter_ID"></span>Identifier for parameter, also used in 3 other table(s) | - |
| Procedure ID | int **(CK-2)** | - |  | <span id="Procedure_ID"></span>Identifier for procedures, also used in 3 other table(s) | - |

<span id="procedures"></span>

### Procedures

Table for Procedures


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Procedure ID | int **(PK)** | - |  | <span id="Procedure_ID"></span>Identifier for procedures, also used in 3 other table(s) | - |
| Procedure Location | nvarchar(100) | - |  | <span id="Procedure_location"></span>Procedure Location in procedures table | - |
| Procedure Name | nvarchar(100) | - |  | <span id="Procedure_name"></span>Procedure Name in procedures table | - |
| Procedure Type | nvarchar(255) | - |  | <span id="Procedure_type"></span>Procedure Type in procedures table | - |
| Procedures Description | ntext(1073741823) | - |  | <span id="procedures_Description"></span>Procedures Description in procedures table | - |

<span id="project"></span>

### Project

Table for Project


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Project ID | int **(PK)** | - |  | <span id="Project_ID"></span>Identifier for project, also used in 4 other table(s) | - |
| Project Name | nvarchar(100) | - |  | <span id="Project_name"></span>Project Name in project table | - |
| Project Description | ntext(1073741823) | - |  | <span id="project_Description"></span>Project Description in project table | - |

<span id="project_has_contact"></span>

### Project Has Contact

Table for Project Has Contact


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Contact ID | int **(CK-2)** | - |  | <span id="Contact_ID"></span>Identifier for contact, also used in 2 other table(s) | - |
| Project ID | int **(CK-1)** | - |  | <span id="Project_ID"></span>Identifier for project, also used in 4 other table(s) | - |

<span id="project_has_equipment"></span>

### Project Has Equipment

Table for Project Has Equipment


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Equipment ID | int **(CK-2)** | - |  | <span id="Equipment_ID"></span>Identifier for equipment, also used in 2 other table(s) | - |
| Project ID | int **(CK-1)** | - |  | <span id="Project_ID"></span>Identifier for project, also used in 4 other table(s) | - |

<span id="project_has_sampling_points"></span>

### Project Has Sampling Points

Table for Project Has Sampling Points


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Project ID | int **(CK-1)** | - |  | <span id="Project_ID"></span>Identifier for project, also used in 4 other table(s) | - |
| Sampling Point ID | int **(CK-2)** | - |  | <span id="Sampling_point_ID"></span>Identifier for sampling_points, also used in 2 other table(s) | - |

<span id="purpose"></span>

### Purpose

Table for Purpose


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Purpose | nvarchar(100) | - |  | <span id="Purpose"></span>Purpose in purpose table | - |
| Purpose ID | int **(PK)** | - |  | <span id="Purpose_ID"></span>Identifier for purpose, also used in 1 other table(s) | - |
| Purpose Description | ntext(1073741823) | - |  | <span id="purpose_Description"></span>Purpose Description in purpose table | - |

<span id="sampling_points"></span>

### Sampling Points

Table for Sampling Points


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Latitude GPS | nvarchar(100) | - |  | <span id="Latitude_GPS"></span>Latitude GPS in sampling_points table | - |
| Longitude GPS | nvarchar(100) | - |  | <span id="Longitude_GPS"></span>Longitude GPS in sampling_points table | - |
| Pictures | BLOB | - |  | <span id="Pictures"></span>Pictures in sampling_points table | - |
| Sampling Location | nvarchar(100) | - |  | <span id="Sampling_location"></span>Sampling Location in sampling_points table | - |
| Sampling Point | nvarchar(100) | - |  | <span id="Sampling_point"></span>Sampling Point in sampling_points table | - |
| Sampling Point ID | int **(PK)** | - |  | <span id="Sampling_point_ID"></span>Identifier for sampling_points, also used in 2 other table(s) | - |
| Site ID | int | - |  | <span id="Site_ID"></span>Identifier for site, also used in 1 other table(s) | FK → [Site_ID](#Site_ID) |
| Sampling Points Description | ntext(1073741823) | - |  | <span id="sampling_points_Description"></span>Sampling Points Description in sampling_points table | - |

<span id="site"></span>

### Site

Table for Site


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Picture | image(2147483647) | - |  | <span id="Picture"></span>Picture in site table | - |
| Province | nvarchar(255) | - |  | <span id="Province"></span>Province in site table | - |
| Site ID | int **(PK)** | - |  | <span id="Site_ID"></span>Identifier for site, also used in 1 other table(s) | - |
| Site Name | nvarchar(100) | - |  | <span id="Site_name"></span>Site Name in site table | - |
| Site Type | nvarchar(255) | - |  | <span id="Site_type"></span>Site Type in site table | - |
| Watershed ID | int | - |  | <span id="Watershed_ID"></span>Identifier for hydrological_characteristics, also used in 3 other table(s) | FK → [Watershed_ID](#Watershed_ID) |
| Site City | nvarchar(255) | - |  | <span id="site_City"></span>Site City in site table | - |
| Site Country | nvarchar(255) | - |  | <span id="site_Country"></span>Site Country in site table | - |
| Site Description | ntext(1073741823) | - |  | <span id="site_Description"></span>Site Description in site table | - |
| Site Street Name | nvarchar(100) | - |  | <span id="site_Street_name"></span>Site Street Name in site table | - |
| Site Street Number | nvarchar(100) | - |  | <span id="site_Street_number"></span>Site Street Number in site table | - |
| Site Zip Code | nvarchar(100) | - |  | <span id="site_Zip_code"></span>Site Zip Code in site table | - |

<span id="unit"></span>

### Unit

Table for Unit


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Unit | nvarchar(100) | - |  | <span id="Unit"></span>Unit in unit table | - |
| Unit ID | int **(PK)** | - |  | <span id="Unit_ID"></span>Identifier for unit, also used in 2 other table(s) | - |

<span id="urban_characteristics"></span>

### Urban Characteristics

Table for Urban Characteristics


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Agricultural | real | - |  | <span id="Agricultural"></span>Agricultural in urban_characteristics table | - |
| Commercial | real | - |  | <span id="Commercial"></span>Commercial in urban_characteristics table | - |
| Green Spaces | real | - |  | <span id="Green_spaces"></span>Green Spaces in urban_characteristics table | - |
| Industrial | real | - |  | <span id="Industrial"></span>Industrial in urban_characteristics table | - |
| Institutional | real | - |  | <span id="Institutional"></span>Institutional in urban_characteristics table | - |
| Recreational | real | - |  | <span id="Recreational"></span>Recreational in urban_characteristics table | - |
| Residential | real | - |  | <span id="Residential"></span>Residential in urban_characteristics table | - |
| Watershed ID | int **(PK)** | - |  | <span id="Watershed_ID"></span>Identifier for hydrological_characteristics, also used in 3 other table(s) | - |

<span id="value"></span>

### Value

Table for Value


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Comment ID | int | - |  | <span id="Comment_ID"></span>Identifier for comments, also used in 1 other table(s) | FK → [Comment_ID](#Comment_ID) |
| Metadata ID | int | - |  | <span id="Metadata_ID"></span>Identifier for metadata, also used in 1 other table(s) | FK → [Metadata_ID](#Metadata_ID) |
| Number Of Experiment | numeric | - |  | <span id="Number_of_experiment"></span>Number Of Experiment in value table | - |
| Timestamp | int | - |  | <span id="Timestamp"></span>Timestamp in value table | - |
| Value | float | - |  | <span id="Value"></span>Value in value table | - |
| Value ID | int **(PK)** | - |  | <span id="Value_ID"></span>Unique identifier for value | - |

<span id="watershed"></span>

### Watershed

Table for Watershed


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Concentration Time | int | - |  | <span id="Concentration_time"></span>Concentration Time in watershed table | - |
| Impervious Surface | real | - |  | <span id="Impervious_surface"></span>Impervious Surface in watershed table | - |
| Surface Area | real | - |  | <span id="Surface_area"></span>Surface Area in watershed table | - |
| Watershed ID | int **(PK)** | - |  | <span id="Watershed_ID"></span>Identifier for hydrological_characteristics, also used in 3 other table(s) | - |
| Watershed Name | nvarchar(100) | - |  | <span id="Watershed_name"></span>Watershed Name in watershed table | - |
| Watershed Description | ntext(1073741823) | - |  | <span id="watershed_Description"></span>Watershed Description in watershed table | - |

<span id="weather_condition"></span>

### Weather Condition

Table for Weather Condition


#### Fields

| Field | SQL Type | Value Set | Required | Description | Constraints |
|-------|----------|-----------|----------|-------------|-------------|
| Condition ID | int **(PK)** | - |  | <span id="Condition_ID"></span>Identifier for weather_condition, also used in 1 other table(s) | - |
| Weather Condition | nvarchar(100) | - |  | <span id="Weather_condition"></span>Weather Condition in weather_condition table | - |
| Weather Condition Description | ntext(1073741823) | - |  | <span id="weather_condition_Description"></span>Weather Condition Description in weather_condition table | - |