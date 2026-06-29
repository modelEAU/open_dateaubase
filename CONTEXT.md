# Context Glossary

Canonical terms for the open_datEAUbase domain. Glossary only — no implementation
details. When code or conversation uses one of these words, it means *this*.

## Stream

The supertype of a sensor **Channel** and a lab **AnalysisSeries** (table-per-type
inheritance; every Channel and AnalysisSeries owns exactly one Stream row via
`Stream_ID`). The unit of selection in the Data Explorer. A "time series" the user
plots or downloads is a Stream.

## Provenance

The **processing-step lineage DAG** of a Stream: how it was derived from upstream
streams through processing steps (outlier removal, drift correction, smoothing, …),
plus accumulated traits. This is the *transformation history*. Surfaced by the
`/lineage/streams/{id}/provenance` endpoint and the Explore Provenance panel. Not to
be confused with [pedigree].

## Pedigree

The **organizational and spatial context** of a Stream — distinct from [provenance].
The pedigree splits into a time-invariant identity and a **time-bound deployment
timeline**:

- Identity (fixed): parameter, unit, value kind, label.
- Deployment timeline (one segment per slice of the stream's life):
  - Sampling location (the SamplingPoint)
  - Process unit (the ProcessUnit the sampling point sits on)
  - Site (owning the sampling point / campaign)
  - Campaign
  - Responsible person (the campaign's `ResponsiblePerson`)
  - Equipment (sensor only)

A **sensor channel's** location and campaign are *historical*: its equipment is
rewired (`EquipmentWiringHistory`) and moved between sampling points
(`EquipmentLocationHistory`) over time, so one channel's data can span several
locations and campaigns. The pedigree therefore carries a list of segments, each
with its own `valid_from`/`valid_to`, not a single snapshot. A **lab
AnalysisSeries** has a single fixed sampling point + campaign — one open segment.

Pedigree is the *who/where/why*; provenance is the *how-derived*. The data-export
metadata YAML carries pedigree, and each exported CSV row carries the sampling
location + campaign active at that row's timestamp.

[pedigree]: #pedigree
[provenance]: #provenance
