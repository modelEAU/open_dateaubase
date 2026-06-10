# 3. Exclusive arc over a Source supertype for sensor/lab polymorphism

Date: 2026-06-10

## Status

Accepted.

## Context

Several tables need to point at "a measurement stream that is *either* a sensor
or a lab stream." `Observation` already does this — it carries `Channel_ID` and
`LabAnalysis_ID` with an XOR `CHECK` (exactly one non-NULL). `Annotation` is
about to acquire the same shape (`Channel_ID` xor `AnalysisSeries_ID`) so that
lab AnalysisSeries can be annotated with parity to sensor Channels.

There are two standard ways to model "belongs to exactly one of N known kinds":

1. **Exclusive arc** — one nullable FK column per target kind, plus a `CHECK`
   enforcing exactly one is set. Real foreign keys on every arm, so the database
   enforces referential integrity. This is what `Observation` uses.
2. **Source supertype** — introduce a single stored identity (e.g. a `Trace` /
   `MeasurementSource` table) that both `Channel` and `AnalysisSeries`
   specialize. Downstream tables then carry one clean, non-NULL FK to that
   supertype, and the disjunction lives in the type hierarchy instead of being
   repeated.

A third option, a `parent_id` + `parent_type` *string* with no foreign keys
(Rails-style polymorphism), is rejected outright: it discards referential
integrity, which this schema treats as non-negotiable.

The supertype is not hypothetical — `CONTEXT.md` already names it. A **Trace**
is defined as "either a sensor Channel or a lab AnalysisSeries," but it is
explicitly a UI/exploration concept, *not a stored table*.

## Decision

Use the **exclusive arc** (mutually-exclusive nullable FKs + XOR `CHECK`) for
sensor/lab polymorphism, rather than promoting `Trace` to a stored supertype
table — for now.

Rationale:

- **Read-path flatness.** ADR 0002 deliberately converged the lab read path onto
  the sensor read functions by storing collection time directly in
  `Observation.Timestamp`, so lab reads need *no extra join*. A supertype table
  would reintroduce a join on the hot read path, undoing part of that win.
- **Integrity is preserved either way.** The exclusive arc keeps a real FK on
  each arm, so we lose nothing on integrity versus the supertype — only some SQL
  ergonomics (queries branch / COALESCE).
- **Only two occurrences.** The disjunction currently appears in `Observation`
  and (soon) `Annotation`. At this count, a supertype table is premature
  abstraction; the duplication is cheap and local.

## Consequences

- Each table in the arc must branch in application/SQL logic on which id is set;
  the `CHECK` guarantees integrity but not ergonomics.
- Adding a **third** source kind means touching every arc table (new nullable
  column + rewritten `CHECK`) — cost is O(tables). This is the accepted downside.
- **Trip-wire for revisiting:** if a *third* table needs to point at "a Trace,"
  the recurring disjunction has earned its own identity. At that point, promote
  `Trace` from a UI concept to a stored supertype table (`Trace_ID`), collapse
  the per-table XOR columns into a single non-NULL FK, and supersede this ADR.
  Two occurrences = exclusive arc; three or more of the same pair = supertype.
- Note the two arcs do not target the same pair: `Observation` disjoins
  `Channel | LabAnalysis` (one analytical run), while `Annotation` disjoins
  `Channel | AnalysisSeries` (the stream identity). A future `Trace` supertype
  would unify the *stream-identity* side (`Channel | AnalysisSeries`).
