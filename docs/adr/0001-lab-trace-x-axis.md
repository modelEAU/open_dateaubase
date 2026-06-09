# 1. Lab traces plot at sample collection time, not Observation.Timestamp

Date: 2026-06-06

## Status

Superseded by [ADR 0002](0002-lab-observation-timestamp-sample-time.md).

The end-user convention this ADR established (lab Traces plot at sample
collection time) still holds. What changed is the *mechanism*: rather than
storing analysis time in `Observation.Timestamp` and recovering collection time
through a read-time join, lab ingest now stores the collection time directly as
`Observation.Timestamp`. The separate lab read path described below was never
built; reversing the anchor lets lab reads reuse the sensor read functions.

## Context

The Data Explorer plots **Traces** — a Trace is either a sensor **Channel** or
a lab **AnalysisSeries** (see [CONTEXT.md](../../CONTEXT.md)). A key goal is to
overlay a lab AnalysisSeries against a sensor Channel for the same parameter
(e.g. lab TSS points on top of an online TSS sensor line) so they can be
compared on a shared time axis.

Every measurement is an `Observation`, which carries a `Timestamp`. For lab
observations, that `Timestamp` is set at ingest from
`LabAnalysis.AnalysisDateTime` — the moment the **test was run in the lab**.
That can be hours or days after the water was physically sampled
(`Sample.SampleDateTimeStart`).

The sensor read path keys its x-axis on `Observation.Timestamp`, which for
sensors *is* the real-world measurement time. Naively, the lab read path would
do the same.

## Decision

Lab Traces use **`Sample.SampleDateTimeStart`** (sample collection time) as their
x-axis, **not** `Observation.Timestamp`. The lab read query therefore joins
`Observation → LabAnalysis → Sample` and selects the sample's collection time as
the point's timestamp.

`Observation.Timestamp` (= analysis time) is still stored and remains available;
it is simply not what the explorer plots against.

## Consequences

- A lab TSS measurement lines up on the time axis with the sensor that was in
  the water when the sample was taken — the overlay is meaningful.
- The lab read functions diverge from the sensor read functions (extra join +
  different timestamp column), which reinforced the choice to keep **separate**
  lab read functions rather than parametrizing the proven sensor queries.
- Replicates of the same AnalysisSeries on the same Sample share one collection
  time, so they land on the same x; we plot them as individual points rather
  than aggregating.
- If a future need arises to view lab data by analysis time, it would be an
  explicit toggle, not the default.
