# Context: open_datEAUbase

A glossary of the core domain language. Definitions only — no implementation
details. When a term here conflicts with how code or conversation uses a word,
this file wins until deliberately changed.

## Glossary

### Trace

A single plottable stream added to the Data Explorer chart. A Trace is *either*
a sensor **Channel** or a lab **AnalysisSeries** — it is the umbrella concept
the explorer treats uniformly (one entry in the active list, one chip, one
Plotly trace). "Trace" is a UI/exploration concept, not a stored table.

### Channel

The stable identity of a **sensor** measurement stream. Excludes sampling
location from its identity (location is inferred at query time via equipment
location history). The sensor half of a Trace.

### AnalysisSeries

The stable identity of a **lab** measurement stream — the lab analogue of
Channel: "Parameter X measured at SamplingPoint Y by ProcessingKind Z producing
ValueKind W in Unit U." Unlike Channel, it includes **SamplingPoint** as
explicit identity, because lab samples always have a known origin. The lab half
of a Trace.

### Observation

The unified, time-anchored fact. Each Observation points to *exactly one* source
— a Channel (sensor) or a LabAnalysis (lab) — carries a Timestamp, and routes
its payload to the value tables (scalar/vector/matrix/image). Sensor and lab
data are siblings sharing one fact table and one set of value tables. The
`Timestamp` is the real-world measurement moment for **both** sources: the
channel read time for sensors, and the **sample collection time**
(`Sample.SampleDateTimeStart`) for lab observations.

### Sample

A discrete physical sample collected at a sampling point. Its **collection
time** (`SampleDateTimeStart`) is the real-world moment the water was sampled.

### LabAnalysis

One analytical run on one Sample for one AnalysisSeries. Carries the Replicate
number and an optional quality code. Its `AnalysisDateTime` is when the *test
was run* — which may be days after the Sample was collected.

### Replicate

A repeated measurement of the same AnalysisSeries on the same Sample
(Replicate 1 = primary, 2+ = duplicates). Multiple replicates share one sample
collection time.

### Annotation

A human-authored note attached to a **Trace** — applying *either* over a time
range *or* pinned to a single measurement point. Because it attaches to a Trace,
an Annotation can target *either* half: a sensor **Channel** or a lab
**AnalysisSeries**. A **point** Annotation pins to one exact **Observation**
(for lab, that is a single **Replicate**, since replicates share a collection
time and stack at the same instant). Every Annotation carries an
**AnnotationKind** (a controlled vocabulary term: Fault, Maintenance, Anomaly,
Note, …).

## Resolved conventions (Data Explorer)

- **Lab x-axis = Sample collection time** (`Sample.SampleDateTimeStart`), *not*
  analysis time. This lets a lab AnalysisSeries align on the time axis with a
  sensor Channel for the same parameter. This is enforced at ingest —
  `Observation.Timestamp` *is* the collection time — so the lab read path needs
  no special join and reuses the sensor read functions. See
  [ADR 0002](docs/adr/0002-lab-observation-timestamp-sample-time.md).
- **Replicates plot as individual points** at the same x, not aggregated.
- **Annotations apply to both Trace halves.** A Channel and an AnalysisSeries can
  each be annotated with full parity (range and point). A point Annotation on a
  lab Trace pins one specific Replicate. See
  [ADR 0003](docs/adr/0003-exclusive-arc-for-sensor-lab-polymorphism.md) for why
  the two halves are kept as an exclusive arc rather than a shared supertype.
