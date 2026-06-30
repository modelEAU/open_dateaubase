# Unified Event with exclusive-arc polymorphic target

## Status

accepted (extends [ADR-0003](0003-exclusive-arc-for-sensor-lab-polymorphism.md))

## Context

The plant logbook records operational occurrences at every level of the
physical hierarchy: a single sensor channel, a piece of equipment, a sampling
location, a process unit, the whole site, or a campaign. The schema only had
`EquipmentEvent` (target = Equipment) and `Annotation` (target = a measurement
Stream). Site-wide and process-unit-wide entries — power outages, ventilation
failures, PLC crashes — had nowhere to land without being forced, lossily, onto
a single equipment or a single stream.

## Decision

Generalize `EquipmentEvent` into a single `Event` table whose target is an
**exclusive arc**: nullable FKs to every node of the two operational hierarchies
plus the Campaign cross-cut — spatial `Site → ProcessUnit → SamplingPoint` and
acquisition `DataAcquisitionSystem → SignalInterface → Equipment → Channel` —
**eight FKs**, with a CHECK enforcing exactly one non-NULL. DataAcquisitionSystem
and SignalInterface are included because logbook entries like *"Plantage du PLC"*
are DAS/interface-scope and otherwise have nowhere to land. (The anchor entity is
`SamplingPoint`; "SamplingLocation" is not a table.) `EquipmentEventKind` becomes
`EventKind`. `Annotation`'s `EquipmentEvent_ID` FK is repointed to `Event_ID`.
This mirrors the exclusive-arc pattern already chosen in ADR-0003 for the
sensor/lab Stream polymorphism.

Done now, during pre-release v2.0: per the project's migration policy no data
migration script is required — the change is a YAML dictionary edit plus DDL
regeneration. Post-release the same refactor would be expensive.

## Consequences

- Logbook entries map to their *smallest logical unit* instead of being dumped
  into one bucket. This is the data model the logbook mapper targets.
- **Event and Annotation stay separate tables, by design.** IWA *Metadata
  Collection* Ch3 §3.4.3.2 names the field's central unsolved problem: people
  conflate *causes* (deliberate actions, causal occurrences) with *effects*
  (observed symptoms in the signal). `Event` is the cause side (a cleaning, a
  calibration, a power outage); `Annotation` is the effect side (an outlier, a
  drift, a noise burst anchored to a Stream). The repointed `Annotation.Event_ID`
  FK **is** the "causal annotation" the book prescribes (Ch3 Fig 3.9: *"OUR drops
  **because** influent pump P100 is down"*) — a symptom optionally linked to the
  event that explains it, without merging the two tables.
- **A cross-stream symptom is carried by the shared Event, not by a
  many-to-many Annotation↔Stream join.** Ch3 D3.36 wants one symptom to span
  several signals (e.g. a control failure across reactors). Rather than fan an
  Annotation out to N streams, we anchor one `Event` (cause) at the **lowest
  common ancestor** in the arc (ProcessUnit/Site) and let the per-stream
  `Annotation`s (effects) — each still single-Stream — share that `Event_ID`.
  The cause is the unifier. This preserves the cause/effect separation above and
  keeps `Annotation.Stream_ID` a simple non-null FK; the obvious alternative (a
  join table) was rejected because it re-smears one symptom across many targets,
  the very conflation §3.4.3.2 warns against.
- Maintenance before/after readings are **not stored** as columns. The drift
  series is instead a **derived `Channel`** produced by a `ProcessingStep` (the
  schema already distinguishes raw channels from `ProducedByStep_ID` derived
  ones): one `%diff` point per maintenance Event, between the last source sample
  before `EventDateTimeStart` and the first after `EventDateTimeEnd`. This makes
  drift a first-class Stream — selectable, plottable, downloadable, and
  annotatable — and its points carry `QualityCode`s like any Channel, so a delta
  taken across a transient is simply quality-flagged (no bespoke "confidence"
  field). Manual reference readings with no backing stream (zero-checks) go to
  `Notes`.
- **The drift Channel measures the sensor's *own signal change* at the event, not
  trueness.** Ch5 §5.4.2 endorses deriving before/after from the stream for
  **cleaning under steady conditions** (sensor-vs-itself, same medium). But Ch5
  §5.5.2 is emphatic that any *accuracy/trueness* claim needs a **controlled
  reference** (the bucket procedure, A) absent from the live stream — the process
  variable itself drifts on the order of minutes, so a reading "20 min after" can
  straddle a real process change. Therefore the drift Channel's quality meaning is
  scoped to `Cleaning` (and the at-calibration signal jump), and is **never** a
  calibration accuracy result.
- **Calibration proper** — slope/intercept, single- vs multi-point, the
  Channel↔reference relationship and operator metadata — is a distinct model
  deferred to its own PRD and ADR (see `.tasks/prd_6_calibration_NOTES.md`). Ch3
  §3.2.3.4 is clear that, unlike maintenance readings, calibration *curves* must
  be **stored as append-only history**, not derived. Maintenance drift (above)
  is not calibration.
