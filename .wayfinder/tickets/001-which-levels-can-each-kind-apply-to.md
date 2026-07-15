# Which levels can each Kind apply to?

- **Parent:** [Map: Recording](../map.md)
- **Label:** `wayfinder:grilling`
- **Blocked by:** —
- **Assignee:** jeandavidt (session 2026-07-14)
- **Status:** closed

## Question

The user wants each **Kind** associated with the level(s) it can legitimately apply to —
both to drive the Recording gesture's target pre-fill and (stated second payoff) to help a
future logbook mapper parse free-text entries onto the right target.

Decide the model:

1. Is it Kind → **one** level, or Kind → a **set** of levels? (`Calibration` plausibly applies
   to both `Equipment` and `Channel`; `PowerOutage` to `Site` or `DataAcquisitionSystem`.)
2. Does `AnnotationKind` participate, or is level meaningless for annotations (whose anchor is
   always a `Stream`)? If it doesn't participate, the two vocabularies stop being symmetric —
   is that acceptable, or does it argue for one unified Kind table with a `target` discriminator?
3. Where does the association live — a new column on `EventKind`, a `KindAllowedTarget` link
   table, or a unified `Kind` table replacing both?
4. Is the association a **constraint** (DB rejects a Calibration on a Site) or a **hint** (UI
   defaults and orders by it, DB stays permissive)? A constraint is harder to reverse and will
   bite on the first weird real-world logbook entry.

Cross-check against the real vocabularies before deciding — `EventKind.yaml` and
`AnnotationKind.yaml` seed data, and any logbook samples in the repo.

**Output:** a decision, a glossary update, and — since this is hard to reverse, surprising, and
a genuine trade-off — almost certainly an **ADR**. Schema shape only; no DDL, no migration.

## Resolution

**No Kind→level association at all.** The premise didn't survive contact with the seed data.

Checking `EventKind`'s 15 rows: `Cleaning` is Equipment *or* SamplingPoint; `PowerOutage` is
Site *or* DAS *or* SignalInterface; `Commissioning`/`Decommissioning`/`OutOfService` apply to
nearly every arm of the arc. The association isn't Kind→one level, it's Kind→a *wide set* —
often six of eight. A structure that permits almost everything disambiguates nothing: it can't
drive the pre-fill, can't meaningfully constrain the write, and would still be wrong on the
first weird logbook entry. Questions 1, 3 and 4 all die with it: no column, no link table, no
unified `Kind` table, no constraint. Level is pre-filled from the **context the user is standing
in**; the DB stays permissive.

The real muddiness was elsewhere, and it's what question 2 was actually poking at.
`AnnotationKind` had drifted into naming **causes** (`Equipment Relocation`, `Process Event`,
`Maintenance`, `Calibration Period`, `Fault`) even though an `Annotation` is a claim about
*data*. So the effort moves from the schema into the **vocabulary**:

> A kind is an **EventKind** if it names something that *happened in the plant* — true whether
> or not anyone was measuring. It is an **AnnotationKind** if it names something *about the
> data* — meaningless without a series to say it about.

Applied, `AnnotationKind` collapses 11 → 5 verdicts: `Data Quality`, `Exclusion`, `Confirmed`,
`Anomaly`, `Note`. An annotation says *what* is wrong with the data, never *why* — the why lives
on the cited `Event`. `Anomaly` absorbs the "something happened, I can't name the unit" case
(no new `Unexplained Disturbance` kind needed). `Process Event` and `Equipment Relocation` are
deleted; `Fault`/`Maintenance`/`Calibration Period` become `Data Quality` + an Event link;
`Experiment` is provenance, not quality, and is retired.

**One recording writes one row.** Dual-write deferred until a user asks — a "calibration tainted
this window" recording is just an Event today. This rules
[When does one gesture write two rows?](002-when-does-one-gesture-write-two-rows.md) out of scope.

Written up as **[ADR-0007](../../docs/adr/0007-kind-level-association.md)** (with the rejected
alternatives — link table, unified Kind table, `DefaultLevel` column — recorded, because they
will be re-proposed). Glossary updated in [CONTEXT.md](../../CONTEXT.md): `EventKind`,
`Annotation`, `Kind` and `Recording` rewritten, new **Cause/Effect Test** entry.

**Surfaced:** `api/v1/endpoints/equipment_move.py:41` hardcodes `AnnotationKind` 11 and writes an
"Equipment Relocation" *annotation* on every equipment move — a miscategorised write that the
retirement breaks. Graduated to
[Retire the six cause-named AnnotationKinds](006-retire-the-six-cause-named-annotationkinds.md).
