# datEAUbase Schema Documentation (AS-IS 2025)

**Version:** 2025-09-12  
**Source:** Lucidchart Schema "datEAUbase_AS-IS_2025.pdf"  
**Context:** Central database for the pilEAUte/datEAUbase information system, interconnected with FactoryTalk Historian, Python API, and MQTT for hydrological, environmental, and operational data management.

---

## Table of Contents

1. [Overview](#1-overview)
2. [Functional Domains](#2-functional-domains)
3. [Database Structure](#3-database-structure)
4. [Table Reference](#4-table-reference)
5. [Controlled Vocabularies](#5-controlled-vocabularies)
6. [Schema Evolution](#6-schema-evolution)
7. [References](#8-references)

---
Useful link to be capable of reading the schema: https://www.freecodecamp.org/news/crows-foot-notation-relationship-symbols-and-how-to-read-diagrams/
## 1. Overview

### 1.1 Purpose

datEAUbase is a MySQL relational database designed to:
- Centralize water quality data from multiple sources (online sensors, laboratories, manual observations)
- Document measurements with comprehensive metadata (who, what, where, when, how, why)
- Ensure data traceability from physical sensor to final storage
- Implement quality assurance through validation workflows and operational thresholds
- Maintain historical records of equipment usage, research projects, and site evolution

### 1.2 Database Statistics

| Metric | Value |
|--------|-------|
| Total tables | 35 (33 application + 2 system/archive) |
| Junction tables | 8 |
| Foreign keys in metadata | 13 (increased from 9 in 2020) |
| Daily data growth | ~150,000 records |
| Annual growth | ~55 million records |
| Annual storage requirement | ~4 GB (data + indexes) |

---

## 2. Functional Domains

The database is organized into six color-coded functional domains:

| Domain | Color | Tables | Description |
|--------|-------|--------|-------------|
| **Metadata and Values** 3 | Core measurement data and context |
| **Instrumentation & Procedures**| 9 | Equipment, models, parameters, and SOPs |
| **Geospatial & Environmental** | 5 | Sites, watersheds, land use characteristics |
| **Projects & Associations** | 8 | Research projects and team relationships |
| **Support References** | 6 | Units, statuses, types, sources, operations |
| **Systems & Control** | 4 | Control loops, synchronization, archives |

---

## 3. Database Structure

### 3.1 Core Data Flow
```text
value ──▶ metadata (Central Hub - 13 Foreign Keys)
   │             │
   │             ├──▶ parameter ──▶ unit
   │             ├──▶ equipment ──▶ equipment_model
   │             ├──▶ sampling_points ──▶ site ──▶ watershed
   │             ├──▶ contact
   │             ├──▶ project
   │             ├──▶ purpose
   │             ├──▶ procedures
   │             ├──▶ weather_condition
   │             ├──▶ type_data 
   │             ├──▶ status 
   │             ├──▶ operations 
   │             └──▶ source 
   │
   └──▶ comments
```

### 3.2 Key Relationships

<Cardinality is determined by the constraints, not the arrow drawing.>
**One-to-One (1:1)**
- watershed ↔ urban_characteristics
- watershed ↔ hydrological_characteristics

**One-to-Many (1:N)**
- equipment_model → equipment
- site → sampling_points
- project → metadata

**Many-to-Many (M:N) via junction tables**
- equipment_model ↔ parameter (via equipment_model_has_specification)
- equipment_model ↔ procedures (via equipment_model_has_procedures)
- parameter ↔ procedures (via parameter_has_procedures)
- project ↔ equipment (via project_has_equipment)
- project ↔ contact (via project_has_contact)
- project ↔ sampling_points (via project_has_sampling_points)
- equipment ↔ sampling_points (via equipment_has_sampling_points)

---

## 4. Table Reference

### 4.1 Metadata and Values

#### value
Primary data storage for all measurements and observations.

| Field | Type | Description |
|-------|------|-------------|
| Value_ID | INT (PK) | Unique identifier |
| Value | FLOAT | Measured value |
| Timestamp | INT | Unix timestamp |
| Number_of_experiment | NUMERIC | Replicate number for statistical analysis |
| Metadata_ID | INT (FK) | Context reference → metadata |
| Comment_ID | INT (FK) | Optional annotation → comments |

**Volume:** Highest growth table (~150K records/day)

---

#### metadata
Central hub containing complete measurement context with 13 foreign keys.

| Field | Type | Description |
|-------|------|-------------|
| Metadata_ID | INT (PK) | Unique identifier |
| Parameter_ID | INT (FK) | What was measured → parameter |
| Unit_ID | INT (FK) | Measurement unit → unit |
| Purpose_ID | INT (FK) | Measurement objective → purpose |
| Equipment_ID | INT (FK) | Instrument used → equipment |
| Procedure_ID | INT (FK) | Method followed → procedures |
| Condition_ID | INT (FK) | Weather context → weather_condition |
| Sampling_point_ID | INT (FK) | Location → sampling_points |
| Contact_ID | INT (FK, NOT NULL) | Responsible person → contact |
| Project_ID | INT (FK) | Associated project → project |
| Type_ID | INT (FK) | Data type → type_data |
| Status_ID | INT (FK) | Validation status → status |
| Operations_ID | INT (FK) | Operational thresholds → operations |
| Source_ID | INT (FK) | Data provenance → source  |

**Purpose:** Pre-computed context combinations to optimize query performance and ensure consistency.

---

#### comments
Free-text annotations for measurements.

| Field | Type | Description |
|-------|------|-------------|
| Comment_ID | INT (PK) | Unique identifier |
| Comment | TEXT | Descriptive note |

**Usage:** Anomalies, incidents, calibration issues, field observations.

---

### 4.2 Instrumentation & Procedures 

#### equipment_model
Catalog of equipment types and models.

| Field | Type | Description |
|-------|------|-------------|
| Equipment_model_ID | INT (PK) | Unique identifier |
| Equipment_model | VARCHAR(100) | Model name |
| Manufacturer | VARCHAR(100) | Manufacturer name |
| Method | VARCHAR(100) | Measurement principle |
| Functions | TEXT | Capabilities description |
| Manual_location | VARCHAR(100) | Manual reference |
| Equipment_type | VARCHAR(100) | Category (Sensor, Analyzer, etc.) |
| Product_number | VARCHAR(100) | Manufacturer part number |
| SOP_number | INT | Related SOP reference |
| SOP_URL | VARCHAR(255) | Online procedure link |
| Contact_ID | INT (FK) | Manufacturer contact → contact |
| Resources_URL | VARCHAR(300) | Additional resources |
| Notes | VARCHAR(150) | Miscellaneous notes |

---

#### equipment
Individual equipment inventory.

| Field | Type | Description |
|-------|------|-------------|
| Equipment_ID | INT (PK) | Unique identifier |
| Equipment_identifier | VARCHAR(100) | User-friendly name |
| Serial_number | VARCHAR(100) | Manufacturer serial number |
| Equipment_model_ID | INT (FK) | Model reference → equipment_model |
| Owner | TEXT | Owner information |
| Storage_location | VARCHAR(100) | Storage location when not deployed |
| Purchase_date | DATE | Acquisition date |
| Status | VARCHAR(10) | Current status (Active, Retired, Maintenance) |
| Commissioning_date | DATE | Initial deployment date |
| Notes | VARCHAR(300) | Special notes |

---

#### parameter
Catalog of measurable variables.

| Field | Type | Description |
|-------|------|-------------|
| Parameter_ID | INT (PK) | Unique identifier |
| Parameter | VARCHAR(100) | Parameter name (pH, TSS, Temperature, etc.) |
| Unit_ID | INT (FK) | Default unit → unit |
| Parameter_Description | TEXT | Scientific definition |

**Examples:** pH, Temperature, TSS, COD, BOD, NH4-N, NO3-N, Flow, Turbidity

---

#### unit
Measurement units reference.

| Field | Type | Description |
|-------|------|-------------|
| Unit_ID | INT (PK) | Unique identifier |
| Unit | VARCHAR(100) | Unit symbol (mg/L, °C, m³/s, pH, %) |

---

#### procedures
Standard Operating Procedures (SOPs).

| Field | Type | Description |
|-------|------|-------------|
| Procedure_ID | INT (PK) | Unique identifier |
| Procedure_name | VARCHAR(100) | SOP name |
| Procedure_type | VARCHAR(255) | Type (Calibration, Maintenance, Analysis, Sampling) |
| Procedure_location | VARCHAR(100) | Document location |
| Procedures_Description | TEXT | Detailed description |

---

#### purpose
Measurement objectives.

| Field | Type | Description |
|-------|------|-------------|
| Purpose_ID | INT (PK) | Unique identifier |
| Purpose | VARCHAR(100) | Purpose code |
| Purpose_Description | TEXT | Detailed explanation |

**Values:** Measurement, Calibration, Validation, Cleaning, Laboratory, Simulation, Manual observation

---

#### equipment_model_has_specification
Technical specifications for equipment models (replaces legacy equipment_model_has_Parameter).

| Field | Type | Description |
|-------|------|-------------|
| Equipment_model_ID | INT (CK) | Equipment model → equipment_model |
| Parameter_ID | INT (CK) | Measurable parameter → parameter |
| Range_min | FLOAT | Minimum measurement range |
| Range_max | FLOAT | Maximum measurement range |
| Resolution | VARCHAR(100) | Measurement resolution |
| Unit_ID | INT (FK) | Range unit → unit |

**Purpose:** Automatic validation against sensor physical limits.

---

#### equipment_model_has_procedures
Links equipment models to applicable procedures.

| Field | Type | Description |
|-------|------|-------------|
| Equipment_model_ID | INT (CK) | Equipment model → equipment_model |
| Procedure_ID | INT (CK) | Procedure → procedures |

---

#### parameter_has_procedures
Links parameters to analytical methods.

| Field | Type | Description |
|-------|------|-------------|
| Parameter_ID | INT (CK) | Parameter → parameter |
| Procedure_ID | INT (CK) | Procedure → procedures |

---

### 4.3 Geospatial & Environmental

#### site
Physical locations (treatment plants, monitoring stations, study sites).

| Field | Type | Description |
|-------|------|-------------|
| Site_ID | INT (PK) | Unique identifier |
| Site_name | VARCHAR(100) | Site name |
| Site_type | VARCHAR(255) | Category (WRRF, River, Lake, Sewer, Industrial) |
| Watershed_ID | INT (FK) | Associated watershed → watershed |
| Site_Description | TEXT | Detailed description |
| Picture | IMAGE | Site photograph |
| Site_Street_number | VARCHAR(100) | Street number |
| Site_Street_name | VARCHAR(100) | Street name |
| Site_City | VARCHAR(255) | City |
| Site_Zip_code | VARCHAR(100) | Postal code |
| Province | VARCHAR(255) | Province/State |
| Site_Country | VARCHAR(255) | Country |

---

#### sampling_points
Specific measurement locations within sites.

| Field | Type | Description |
|-------|------|-------------|
| Sampling_point_ID | INT (PK) | Unique identifier |
| Sampling_point | VARCHAR(100) | Point name (Inlet, Outlet, Reactor, etc.) |
| Sampling_location | VARCHAR(100) | Location description |
| Site_ID | INT (FK) | Parent site → site |
| Latitude_GPS | VARCHAR(100) | GPS latitude |
| Longitude_GPS | VARCHAR(100) | GPS longitude |
| Sampling_points_Description | TEXT | Detailed description |
| Pictures_URL | VARCHAR(500) | Photo links |

---

#### watershed
Drainage basin characteristics.

| Field | Type | Description |
|-------|------|-------------|
| Watershed_ID | INT (PK) | Unique identifier |
| Watershed_name | VARCHAR(100) | Watershed name |
| Surface_area | REAL | Area (km²) |
| Concentration_time | INT | Time of concentration (hours) |
| Impervious_surface | REAL | Impervious surface percentage |
| Watershed_Description | TEXT | Detailed description |

---

#### urban_characteristics
Urban land use distribution (1:1 with watershed).

| Field | Type | Description |
|-------|------|-------------|
| Watershed_ID | INT (PK, FK) | Watershed reference → watershed |
| Residential | REAL | Residential area percentage |
| Commercial | REAL | Commercial area percentage |
| Industrial | REAL | Industrial area percentage |
| Institutional | REAL | Institutional area percentage |
| Green_spaces | REAL | Green spaces percentage |
| Agricultural | REAL | Agricultural area percentage |
| Recreational | REAL | Recreational area percentage |

---

#### hydrological_characteristics
Natural land cover distribution (1:1 with watershed).

| Field | Type | Description |
|-------|------|-------------|
| Watershed_ID | INT (PK, FK) | Watershed reference → watershed |
| Urban_area | REAL | Urban area percentage |
| Forest | REAL | Forest percentage |
| Wetlands | REAL | Wetlands percentage |
| Cropland | REAL | Cropland percentage |
| Meadow | REAL | Meadow percentage |
| Grassland | REAL | Grassland percentage |

---

#### weather_condition
Weather conditions during measurements.

| Field | Type | Description |
|-------|------|-------------|
| Condition_ID | INT (PK) | Unique identifier |
| Weather_condition | VARCHAR(100) | Condition name |
| Weather_condition_Description | TEXT | Criteria definition |

**Values:** Dry weather, Wet weather, Storm event, Snow melt

---

### 4.4 Projects & Associations

#### project
Research projects and monitoring programs.

| Field | Type | Description |
|-------|------|-------------|
| Project_ID | INT (PK) | Unique identifier |
| Project_name | VARCHAR(100) | Project name |
| Project_Description | TEXT | Objectives, funding, duration |

---

#### contact
Personnel and organizations.

| Field | Type | Description |
|-------|------|-------------|
| Contact_ID | INT (PK) | Unique identifier |
| Last_name | VARCHAR(100) | Last name |
| First_name | VARCHAR(255) | First name |
| Company | TEXT | Organization |
| Status | VARCHAR(255) | Role (Researcher, Technician, Student) |
| Function | TEXT | Position/title |
| Office_number | VARCHAR(100) | Office number |
| Phone | VARCHAR(100) | Phone number |
| Email | VARCHAR(100) | Email address |
| Skype_name | VARCHAR(100) | Skype identifier |
| Linkedin | VARCHAR(100) | LinkedIn profile |
| Website | VARCHAR(60) | Website |
| Contact_Street_number | VARCHAR(100) | Street number |
| Contact_Street_name | VARCHAR(100) | Street name |
| Contact_City | VARCHAR(255) | City |
| Contact_Zip_code | VARCHAR(45) | Postal code |
| Contact_Country | VARCHAR(255) | Country |

---

#### project_has_equipment
Equipment allocation to projects (M:N junction).

| Field | Type | Description |
|-------|------|-------------|
| Project_ID | INT (CK) | Project → project |
| Equipment_ID | INT (CK) | Equipment → equipment |

---

#### project_has_contact
Project team members (M:N junction).

| Field | Type | Description |
|-------|------|-------------|
| Project_ID | INT (CK) | Project → project |
| Contact_ID | INT (CK) | Contact → contact |

---

#### project_has_sampling_points
Project study sites (M:N junction).

| Field | Type | Description |
|-------|------|-------------|
| Project_ID | INT (CK) | Project → project |
| Sampling_point_ID | INT (CK) | Sampling point → sampling_points |

---

#### equipment_has_sampling_points
Equipment deployment history (M:N junction).

| Field | Type | Description |
|-------|------|-------------|
| Equipment_ID | INT (CK) | Equipment → equipment |
| Sampling_point_ID | INT (CK) | Sampling point → sampling_points |

**Purpose:** Track equipment relocation over time.

---

### 4.5 Support References

#### source 
Data provenance and traceability 

| Field | Type | Description |
|-------|------|-------------|
| Source_ID | INT (PK) | Unique identifier |
| Signal_Transmission | VARCHAR(25) | Protocol (MQTT, Modbus TCP, OPC UA, CSV Import) |
| Signal_Transmission_Address | VARCHAR(50) | Connection address |
| Source_Location | VARCHAR(100) | Physical/logical location |
| Source_Software | VARCHAR(50) | Source system name |
| Raw_Database_Path | VARCHAR(100) | Raw database path |
| TAG_Name | VARCHAR(50) | Signal identifier in source system |
| TAG_Number | INT | Numeric tag identifier |
| Sampling_Time | VARCHAR(10) | Sampling frequency |
| Import_Location | VARCHAR(100) | Import script location |
| Importing_Software | VARCHAR(50) | Import tool |
| Import_Script | VARCHAR(50) | Script filename |

**Purpose:** Eliminates hardcoded metadata IDs by linking source system tags to database records.

---

#### operations 
Operational thresholds and alarms .

| Field | Type | Description |
|-------|------|-------------|
| Operations_ID | INT (PK) | Unique identifier |
| NOR_min | FLOAT | Normal Operating Range minimum |
| NOR_max | FLOAT | Normal Operating Range maximum |
| Alarm_low | FLOAT | Critical low threshold |
| Alarm_high | FLOAT | Critical high threshold |

**Purpose:** Automatic anomaly detection and quality control.

---

#### status 
Data validation states ( 2025).

| Field | Type | Description |
|-------|------|-------------|
| Status_ID | INT (PK) | Unique identifier |
| Status | VARCHAR(50) | Status name |
| Description | TEXT | Workflow description |

**Values:** raw, flagged, validated, replaced, rejected

---

#### type_data 
Data collection/generation methods ( 2025).

| Field | Type | Description |
|-------|------|-------------|
| Type_ID | INT (PK) | Unique identifier |
| Type | VARCHAR(20) | Type name |
| Description | TEXT | Type explanation |

**Values:** measurement, laboratory, control_signal, calculated, manual, calibration, simulation, validation

---

#### maxTimestamp
Import synchronization tracking.

| Field | Type | Description |
|-------|------|-------------|
| MaxTimestamp_ID | INT (PK) | Unique identifier |
| Timestamp | INT | Last imported timestamp |
| Hits1000 | INT | Counter/pagination |

**Purpose:** Incremental import tracking to prevent duplicates.

---

### 4.6 Systems & Control (⚙️ Gray)

#### control_loop
Automated control system documentation.

| Field | Type | Description |
|-------|------|-------------|
| Measurement | INT (FK) | Process variable → metadata |
| Controller | INT (FK) | Controller output → metadata |
| Actuator | INT (FK) | Actuator command → metadata |
| Notes | VARCHAR(200) | Control configuration details |

**Purpose:** Documents PID loops and automation logic for process analysis.

---

#### value_before_12_04_2025
Pre-migration archive (backup before 2025-04-12 schema changes).

**Status:** Read-only historical archive  
**Structure:** Identical to value table

---

#### value_test_hedi
Test/development environment.

**Status:** Test data - may be purged  
**Structure:** Identical to value table

---

#### sysdiagrams
SQL Server system table for database diagrams.

**Note:** Not an application table - auto-generated by SQL Server Management Studio.


## .6 Key Metrics

### 6.1 Database Size

| Metric | Value |
|--------|-------|
| Application tables | 33 |
| System/archive tables | 2 |
| Junction tables | 8 |
| Total tables | 35 |

### 6.2 Relationships

| Type | Count | Key Table |
|------|-------|-----------|
| Foreign keys in metadata | 13 | metadata (central hub) |
| 1:1 relationships | 2 | watershed ↔ characteristics |
| 1:N relationships | Multiple | Most tables |
| N:N relationships | 8 | Via junction tables |

### 6.3 Data Volume

| Metric | Value |
|--------|-------|
| Daily growth (value table) | ~150,000 records |
| Annual growth | ~55 million records |
| Storage per record | ~20 bytes |
| Annual storage (data) | ~1.1 GB |
| Annual storage (with indexes) | ~4 GB |
| 10-year projection | ~40 GB |

---

## 7. References

### 7.1 Related Documentation

| Document | Content |
|----------|---------|
| `tables.md` | Detailed field descriptions and SQL types |
| `valuesets.md` | Complete controlled vocabularies |
| `schema.md` | Entity-relationship diagrams |
| `architecture.md` | System integration and data flows |
| `queries.md` | Common SQL query examples |

### 7.2 Key Publications

1. Plana, Q., et al. (2018). "Towards a water quality database for raw and validated data with emphasis on structured metadata." *Water Quality Research Journal*, 54(1), 1-9.

2. Horsburgh, J.S., et al. (2008). "A relational model for environmental and water resources data." *Water Resources Research*, 44(5).

### 7.3 Standards

- ISO 19115:2013 - Geographic Information - Metadata
- CUAHSI ODM (Observations Data Model)
- EPA STORET (Storage and Retrieval)

---

## Appendix: Glossary

| Term | Definition |
|------|------------|
| **Metadata** | Complete context of a measurement (who, what, where, when, how, why) |
| **Primary Key (PK)** | Unique identifier for table rows |
| **Foreign Key (FK)** | Reference to another table's primary key |
| **Composite Key (CK)** | Primary key composed of multiple columns |
| **Junction Table** | Table linking two tables in many-to-many relationships |
| **NOR** | Normal Operating Range - expected values under normal conditions |
| **PV/CV/MV** | Process/Control/Manipulated Variable (control terminology) |
| **WRRF** | Water Resource Recovery Facility (wastewater treatment plant) |
| **TSS** | Total Suspended Solids |
| **COD/BOD** | Chemical/Biochemical Oxygen Demand |
| **SCADA** | Supervisory Control And Data Acquisition |
| **PLC** | Programmable Logic Controller |
| **MQTT/OPC UA** | Industrial communication protocols |
| **TAG** | Signal identifier in SCADA/source system |
