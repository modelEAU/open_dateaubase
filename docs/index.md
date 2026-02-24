# dat*EAU*base Documentation

Welcome to the open dat*EAU*base project documentation.

## Overview

open_dat*EAU*base is an MSSQL-backed water quality database for continuous sensor data,
discrete lab measurements, and data processing lineage. The current schema is **v2.1.0**.

## Navigation

- **[Schema Reference](reference/tables.md)** — All tables with columns and relationships
- **[Views](reference/views.md)** — Convenience views for status and timeseries queries
- **[Value Sets](reference/valuesets.md)** — Controlled vocabularies and enumerations
- **[ERD](reference/erd.md)** — Entity-relationship diagram

## Architecture Guides

| Guide | What it covers |
| --- | --- |
| [Self-Configuring Ingestion](architecture/ingestion_routing.md) | Channel model, find-or-create, no pre-config needed |
| [Lab Data](architecture/lab_data.md) | LabAnalysis + LabValue tables for discrete samples |
| [Sensor Status](architecture/sensor_status.md) | Per-channel and device-level status tracking |
| [Campaigns and Provenance](architecture/campaigns_and_provenance.md) | Campaign model, DataProvenance, context at query time |
| [Processing Lineage](architecture/processing_lineage.md) | ProcessingStep + DataLineage DAG |
| [Annotations](architecture/annotations.md) | Human-authored interval annotations |
| [Sensor Lifecycle](architecture/sensor_lifecycle.md) | Calibration, installation history, equipment events |

## How-To References

| Guide | What it covers |
| --- | --- |
| [Inserting Data](reference/inserting_data.md) | Step-by-step for Scalar, Vector, Matrix, Image values |
| [Equipment Move Checklist](operations/equipment_move_checklist.md) | Relocating a sensor without breaking data continuity |

## About

Documentation is generated from the schema dictionary YAML files in
`schema_dictionary/tables/` and `schema_dictionary/views/` using MkDocs with the
Material theme.
