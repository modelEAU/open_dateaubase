# 2. Lab Observation.Timestamp stores sample collection time

Date: 2026-06-09

## Status

Accepted. Supersedes [ADR 0001](0001-lab-trace-x-axis.md).

## Context

Every measurement is an `Observation` carrying a `Timestamp`. For a sensor, that
`Timestamp` is the real-world moment the value was measured. For a lab
measurement, the analogous real-world moment is when the analyte was extracted
from the observed system — the **sample collection time**
(`Sample.SampleDateTimeStart`) — *not* when the test was later run in the lab
(`LabAnalysis.AnalysisDateTime`), which can be hours or days afterward.

[ADR 0001](0001-lab-trace-x-axis.md) chose to store the **analysis time** in
`Observation.Timestamp` and recover the collection time for plotting via a
separate lab read path that joins `Observation → LabAnalysis → Sample`. In
practice that read path was **never implemented**: the Data Explorer and every
read function in `value_repository.py` are keyed on `Channel_ID` and
`Observation.Timestamp` only. So `Observation.Timestamp` for lab rows held a
value (analysis time) that nothing consumed, while the time that *is*
semantically meaningful lived one join away.

## Decision

Lab ingest sets `Observation.Timestamp = Sample.SampleDateTimeStart` (the sample
collection time) for **all** lab observations — scalar, vector, matrix, and
image. The collection time is looked up at ingest from the measurement's
`Sample_ID` (`Sample.SampleDateTimeStart` is `NOT NULL`, so it is always
available).

`LabAnalysis.AnalysisDateTime` continues to be stored as analytical-provenance
metadata — it answers "when was the test run", which remains useful — but it is
no longer the Observation's time anchor.

## Consequences

- `Observation.Timestamp` now means the same thing for both sources: the
  real-world measurement moment. A lab TSS point lands on the time axis where the
  water was actually sampled, lining up with the sensor that was in the water at
  that moment — the overlay is meaningful by construction.
- The lab read path **converges with the sensor read path**: when lab reads are
  built, they can reuse the proven sensor read functions keyed on
  `Observation.Timestamp`, with no extra `Sample` join. ADR 0001's expectation of
  *divergent* lab read functions no longer applies.
- Replicates of the same AnalysisSeries on the same Sample share one collection
  time, so they land on the same x; we plot them as individual points rather than
  aggregating (unchanged from ADR 0001).
- If a future need arises to view lab data by analysis time, it would be an
  explicit toggle reading `LabAnalysis.AnalysisDateTime`, not the default.
- Pre-release (v2.0): no data migration — the ingest logic and the schema
  dictionary description are corrected directly.
