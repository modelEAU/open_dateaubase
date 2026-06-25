# Explore Your Data

The **Explore** page (**Operations → Visualize Data**) is the main place to inspect time series, compare lab and sensor data, annotate events, and trace processing lineage.

This tutorial walks through a typical exploration session.

## 1. Pick a time range

Use the date pickers at the top of the page. The default is the last 30 days. Expand the range if you are looking at a finished campaign.

## 2. Find channels or lab series

Open the channel picker panel. You can cross-filter by:

- Campaign
- Sampling location
- Parameter
- Equipment
- Value type (Scalar, Vector, Matrix, Image)

Select one or more channels or lab series. They appear as chips below the picker.

## 3. Plot the data

Click **Plot**. Explore renders the right visualization for each value type:

- **Scalar** — overlaid line chart with annotation overlays.
- **Vector** — 2-D heatmap (time × bin).
- **Matrix** — time-slice heatmap or row/column slice line chart.
- **Image** — thumbnail gallery.

## 4. Add annotations or inspect provenance

Click and drag on a scalar plot to mark an interesting interval, then add an annotation. Open the provenance panel to see how a derived stream was computed from its ancestors.

## 5. Export

Use the download button to export the current selection as CSV for further analysis.

## See also

- [Campaigns and Provenance](../architecture/campaigns_and_provenance.md)
- [Processing Lineage](../architecture/processing_lineage.md)
