# Ingest Sensor CSV

For one-off or small-scale sensor imports, you can post scalar CSV data directly to the API. For production pipelines, use the [YAML importer](../getting-started.md#6-running-the-importer).

## Prerequisites

- The equipment, parameter, and unit already exist in the database.
- You have an [API access token](authenticate_with_the_api.md).

## Example: tagless scalar CSV

```bash
curl -X POST http://localhost:8000/api/v1/ingest/sensor \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" \
  -d '{
    "equipment_id": 1,
    "parameter_id": 1,
    "unit_id": 1,
    "data_provenance_id": 1,
    "processing_degree": "Raw",
    "timestamps": ["2025-09-10T10:00:00Z", "2025-09-10T10:15:00Z"],
    "values": [185.0, 192.3]
  }'
```

The API creates the `Channel` automatically on first ingest and returns the `channel_id`.

## Verify

Open **Operations → Visualize Data**, select the equipment and parameter, and confirm the points appear.

## See also

- [Self-Configuring Ingestion](../architecture/ingestion_routing.md)
- [Ingest Lab Results](ingest_lab_results.md)
