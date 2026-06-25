# Lab Panels and Results

A **lab panel** is a reusable template for an analytical run. It defines which analytes (AnalysisSeries) you normally measure together, so when you report lab results you only pick the panel and the values auto-fill.

This tutorial covers:

1. Creating a lab panel.
2. Associating it with a campaign.
3. Using the panel to enter lab results.
4. Verifying the results in Explore.

## 1. Create a lab panel

Go to **Operations → Lab Panels** and click **New**. Fill in:

- **Panel name** — something descriptive, e.g. "Inlet routine".
- **Description** — optional context.
- **Default collection kind** — how the sample is usually collected.
- **Default equipment** — the autosampler or lab instrument, if any.
- **AnalysisSeries** — the parameters and sampling points that make up the panel.

Save the panel.

## 2. Associate the panel with a campaign

Panels are used when you create a **Lab Analysis**. Pick the campaign on the **Operations → Insert Lab Data** page; the campaign context links the analysis (and its panel) to the right experiment or monitoring period.

## 3. Report results with the panel

Go to **Operations → Insert Lab Data**. Select the campaign and sample, then choose the panel. The panel pre-fills the AnalysisSeries rows. Enter the measured values, quality codes, and replicate numbers, then submit.

## 4. Verify in Explore

Go to **Operations → Visualize Data**, filter by campaign and parameter, and confirm the new lab points appear on the plot.

## See also

- [Lab Data](../architecture/lab_data.md) — how the lab tables fit together.
- [Ingest Lab Results](../how-to/ingest_lab_results.md) — bulk import via the API or YAML.
