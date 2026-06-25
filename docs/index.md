# dat*EAU*base Documentation

Welcome to the open dat*EAU*base project documentation.

## Overview

open_dat*EAU*base is an MSSQL-backed water quality database for continuous sensor data,
discrete lab measurements, and data processing lineage. The current schema is **v2.1.0**.

## Start here

| I want to... | Go to |
| --- | --- |
| Get the stack running locally | [Getting Started](getting-started.md) |
| Set up a campaign, lab panel, and report results | [Tutorials](tutorials/first_campaign.md) |
| Find a recipe for a specific task | [How-to guides](how-to/add_a_site_and_field_system.md) |
| Look up endpoints or schema tables | [Reference](reference/api/index.md) |
| Understand why the model works this way | [Explanation](explanation/campaign_workflow.md) |

## Reference

- **[API Reference](reference/api/index.md)** — Interactive OpenAPI endpoint reference
- **[Schema Reference](reference/tables.md)** — All tables with columns and relationships
- **[Views](reference/views.md)** — Convenience views for status and timeseries queries
- **[Value Sets](reference/valuesets.md)** — Controlled vocabularies and enumerations
- **[ERD](reference/erd.md)** — Entity-relationship diagram

## Explanation

| Guide | What it covers |
| --- | --- |
| [Self-Configuring Ingestion](architecture/ingestion_routing.md) | Channel model, find-or-create, no pre-config needed |
| [Lab Data](architecture/lab_data.md) | LabAnalysis + LabValue tables for discrete samples |
| [Sensor Status](architecture/sensor_status.md) | Per-channel and device-level status tracking |
| [Campaigns and Provenance](architecture/campaigns_and_provenance.md) | Campaign model, DataProvenance, context at query time |
| [Processing Lineage](architecture/processing_lineage.md) | ProcessingStep + DataLineage DAG |
| [Annotations](architecture/annotations.md) | Human-authored interval annotations |
| [Sensor Lifecycle](architecture/sensor_lifecycle.md) | Calibration, installation history, equipment events |
| [Campaign Workflow](explanation/campaign_workflow.md) | How site, campaign, panel, and results connect |

## How-To Guides

| Guide | What it covers |
| --- | --- |
| [Add a Site and Field System](how-to/add_a_site_and_field_system.md) | Prerequisite setup for any campaign |
| [Authenticate with the API](how-to/authenticate_with_the_api.md) | Get and use bearer tokens |
| [Ingest Sensor CSV](how-to/ingest_sensor_csv.md) | Post scalar data via the API |
| [Ingest Lab Results](how-to/ingest_lab_results.md) | Bulk lab result ingestion |
| [Move or Swap a Sensor](operations/equipment_move_checklist.md) | Keep history intact during equipment changes |
| [Share a Campaign Story](how-to/share_a_campaign_story.md) | Generate and export campaign summaries |

## About

Documentation is generated from:

- the schema dictionary YAML files in `schema_dictionary/tables/` and `schema_dictionary/views/`,
- the FastAPI OpenAPI spec exported from `api/main.py`,
- and the handwritten guides in this `docs/` folder.

The site is built with MkDocs and the Material theme.
