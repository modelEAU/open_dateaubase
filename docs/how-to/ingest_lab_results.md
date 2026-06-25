# Ingest Lab Results

Lab results are linked to a physical sample and an analytical run. You can enter them through the web app or post them in bulk via the API.

## API endpoint

```bash
POST /api/v1/ingest/lab
```

## Example payload

```json
{
  "sample_id": 5,
  "laboratory_id": 1,
  "analyst_person_id": 3,
  "procedure_id": null,
  "campaign_id": 2,
  "notes": null,
  "values": [
    {"parameter_id": 1, "unit_id": 2, "value": 24.5, "replicate": 1},
    {"parameter_id": 1, "unit_id": 2, "value": 24.8, "replicate": 2},
    {"parameter_id": 4, "unit_id": 2, "value": 312.0, "replicate": 1}
  ]
}
```

## Workflow

1. Create the sample (or reuse an existing one).
2. Create the lab analysis via the API.
3. Insert one `LabValue` row per analyte/replicate.
4. Verify in **Operations → Visualize Data** by filtering for the campaign and parameter.

## See also

- [Lab Data](../architecture/lab_data.md)
- [Lab Panels and Results](../tutorials/lab_panel_and_results.md)
