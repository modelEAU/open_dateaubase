# datEAUbase Schema Documentation.

## 1. Overview

### 1.1 Purpose

datEAUbase is a relational database designed to:

- Centralize water quality data from multiple sources (online sensors, laboratories, manual observations)
- Document measurements with comprehensive metadata (who, what, where, when, how, why)
- Ensure data traceability from physical sensor to final storage
- Keep track of data as it gets processed to improve its quality.
- Maintain historical records of equipment usage, research projects, and site evolution

## 2. Functional Domains

The database is organized into several color-coded functional domains:

| Domain | Color | Tables | Description |
|--------|-------|--------|-------------|
| **Metadata and Values** 3 | Core measurement data and context |
| **Instrumentation & Procedures**| 9 | Equipment, models, parameters, and SOPs |
| **Geospatial & Environmental** | 5 | Sites, watersheds, land use characteristics |
| **Projects & Associations** | 8 | Research projects and contacts |

---

## 3. Database Structure

### 3.1 Core Data Flow

```text
value ──▶ metadata (Central Hub linking the value with their specific context)
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


### 4. Key Publications

1. Plana, Q., et al. (2018). "Towards a water quality database for raw and validated data with emphasis on structured metadata." *Water Quality Research Journal*, 54(1), 1-9.
