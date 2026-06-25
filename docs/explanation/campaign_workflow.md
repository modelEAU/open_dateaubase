# Campaign Workflow

This page explains how the main objects in open_datEAUbase fit together when you run a measurement campaign.

## The chain

```
Site
 └── Sampling Location(s)
      └── Campaign (time-bounded context)
           ├── Equipment (via CampaignEquipment)
           ├── Sampling Locations (via CampaignSamplingLocation)
           ├── Parameters (via CampaignParameter)
           ├── Sensor data (Channel → Observation → Value)
           ├── Lab data (Sample → LabAnalysis → LabValue)
           └── Annotations (intervals of interest)
```

## Why this shape?

- **Site** and **Sampling Location** describe *where*.
- **Campaign** describes *why and when*.
- **Equipment** and **Channel** describe *what produced the data*.
- **Lab Panel** is a reusable template that simplifies repeated analytical runs.

## Querying by campaign

Because campaign membership is stored in junction tables, you can ask questions like:

- Which channels were active during this campaign?
- Which lab analyses belong to this campaign?
- Which campaigns shared this sampling location?

See [Campaigns and Provenance](../architecture/campaigns_and_provenance.md) for the SQL recipes.

## See also

- [Your First Campaign](../tutorials/first_campaign.md)
- [Lab Data](../architecture/lab_data.md)
- [Ingestion Routing](../architecture/ingestion_routing.md)
