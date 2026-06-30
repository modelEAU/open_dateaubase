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

## Event

A discrete, time-stamped occurrence in the operational life of the system —
a calibration, maintenance action, failure, power outage, site visit, etc.
The supertype generalizing the former **EquipmentEvent**. Each Event attaches
to exactly one **target** at its *smallest logical unit* via an exclusive arc —
any node of the two operational hierarchies plus Campaign: a Channel, Equipment,
SignalInterface, DataAcquisitionSystem, SamplingPoint, ProcessUnit, Site, or
Campaign (exactly one non-NULL, enforced by CHECK). Has a start (and optional end /
instantaneous flag), a performed-by and a recorded-by Person, an
[EventKind], and free-text notes. The destination for plant **logbook**
entries. Not to be confused with an [annotation], which anchors to a
measurement [Stream] over a time range rather than to an operational unit.
_Avoid_: EquipmentEvent (now a special case), SiteEvent (never existed).

## EventKind

The controlled vocabulary classifying an [Event] (calibration, maintenance,
failure, power outage, …). The supertype generalizing the former
**EquipmentEventKind**.

## Annotation

A human-authored note anchored to a measurement [Stream] (one Channel or
AnalysisSeries) over a time range. Distinct from an [Event]: an annotation
is *about the data*; an event is *about the operational unit*. An annotation
may optionally reference the Event that explains it.

## Measurement Range

The min/max a **sensor** can physically produce when configured and operated
correctly. A property of the sensor itself, independent of location or time
(IWA Ch3 D3.6). _Avoid_: confusing with the [Variable Range] (process) or a
[Control Limit] (error tolerance) — they bound different things.

## Variable Range

The expected range of the **measured value** under normal operation — the
"normal operating range" (IWA Ch3 D3.7). Describes the *process*, not the
sensor, and is context-dependent (location, time of day, season). A per-[Stream]
property. A value outside it is a candidate process anomaly / contextual outlier.

## Control Limit

A tolerance on a **derived quality metric** — maintenance drift `%diff`,
offset/slope drift, bias — used to decide whether a sensor needs action. It
bounds the *error*, not the measured value, so it is **not** a [Variable Range].
Per `(Stream × metric-type)`, and **historicized** (re-baselined over time, à la
SPC) like a calibration curve. The acceptance limits on the logbook's
per-equipment maintenance sheets are Control Limits.

[pedigree]: #pedigree
[provenance]: #provenance
[annotation]: #annotation
[Stream]: #stream
[Event]: #event
[EventKind]: #eventkind
[Variable Range]: #variable-range
[Control Limit]: #control-limit
