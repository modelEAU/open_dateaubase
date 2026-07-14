# No Kind→level association; enforce cause/effect in the vocabulary

## Status

accepted (extends [ADR-0006](0006-unified-event-polymorphic-target.md))

## Context

[ADR-0006](0006-unified-event-polymorphic-target.md) gave `Event` an
eight-way exclusive-arc target. The Recording gesture (see `Recording` in
[CONTEXT.md](../../CONTEXT.md)) asks the user for a **Kind** and never for a
table, so *something* has to decide which of the eight targets — the **level** —
a recording lands on.

The obvious move is to teach the schema: associate each `EventKind` with the
level(s) it may legitimately apply to, then have the UI pre-fill and the DB
enforce. A second payoff was claimed for it: a future logbook-ingest mapper
could use the association to route free-text entries onto the right target.

Checking that idea against the actual `EventKind` seed data kills it:

- `Cleaning` is legitimately **Equipment** *or* **SamplingPoint**.
- `PowerOutage` is **Site** *or* **DataAcquisitionSystem** *or* **SignalInterface**.
- `Commissioning` / `Decommissioning` / `OutOfService` apply to nearly every arm
  of the arc.
- `OperationalChange` is **ProcessUnit** *or* **Site** *or* **Campaign**.

So the association is not Kind→one level but Kind→a *wide set* of levels — often
six of eight. A structure that permits almost everything disambiguates almost
nothing: it would not meaningfully drive the pre-fill, it would not meaningfully
constrain the write, and it would still be wrong on the first weird real-world
logbook entry. It is a maintenance burden dressed as rigour.

Meanwhile the *real* confusion in the model was elsewhere. `AnnotationKind`'s
seed data had drifted into naming **causes** — `Equipment Relocation` (a plant
fact, already owned by `EquipmentLocationHistory`), `Process Event`
("storm, dosing"), `Maintenance`, `Calibration Period`, `Fault` — while
`Annotation` is supposed to be a claim about *data*. That overlap, not the
missing level table, is what makes the two vocabularies feel muddy and makes
"Event or Annotation?" a question anyone has to ask.

## Decision

**No Kind→level association in the data model.** No column on `EventKind`, no
`KindAllowedTarget` link table, no unified `Kind` table with a target
discriminator, and no CHECK constraint tying a kind to an arc arm. A Kind
carries no level. The level is pre-filled from the **context the user is
standing in** — the plotted series' pedigree — and the DB stays permissive.

**Instead, enforce the cause/effect distinction in the vocabulary**, by curating
seed data and descriptions:

> A kind is an **EventKind** if it names something that *happened in the plant* —
> true whether or not anyone was measuring. It is an **AnnotationKind** if it
> names something *about the data* — meaningless without a series to say it about.

Applied to `AnnotationKind`, this collapses eleven kinds to five **verdicts**:
`Data Quality`, `Exclusion`, `Confirmed`, `Anomaly`, `Note`. An annotation says
*what is wrong with the data*, never *why*; the why lives on the `Event` it
optionally cites via `Event_ID`. The cause-named kinds are retired:
`Equipment Relocation` and `Process Event` are deleted outright, and `Fault`,
`Maintenance` and `Calibration Period` collapse into `Data Quality` + an Event
link. `Experiment` is provenance, not quality, and is retired too. `Anomaly`
absorbs the "something happened here that I can't explain" case, which is the
deliberate escape hatch for occurrences with no operational unit to hang on.

**One recording writes one row.** The dual-write path (record a `Calibration`
Event *and* mark the window suspect in one gesture) is deferred until a user
asks for it; today such a recording is simply an Event.

## Consequences

- The Recording dropdown becomes coherent: 15 causes and 5 verdicts, disjoint,
  answering two questions users genuinely hold apart — *what happened in the
  plant* vs *what's wrong with this data*. No level question is asked up front.
- The level pre-fill must come entirely from context, which pushes real work onto
  the Recording dialog: a plotted series' pedigree makes six of the eight arc
  arms simultaneously plausible, and the dialog must let the user pick a rung
  without the Kind narrowing it. This is a UI problem now, not a schema one.
- The logbook mapper loses its claimed schema-level enabler. It gains something
  better: a vocabulary where a kind's *table* is predictable from its meaning.
- Retiring six `AnnotationKind` rows is migration-worthy against the frozen v2.1
  baseline, and it breaks `api/v1/endpoints/equipment_move.py`, which hardcodes
  `AnnotationKind` 11 ("Equipment Relocation") and writes an annotation on every
  equipment move. Under this ADR that write was miscategorised — a move is an
  Event. Tracked separately.
- Losing the constraint means the DB will accept a `Calibration` on a `Site`.
  Accepted: permissiveness is cheap to tighten later, and a wrong constraint is
  expensive to unwind.

## Alternatives considered

- **`KindAllowedTarget` link table.** Rejected: the sets are wide enough that the
  table permits almost everything, so it buys no disambiguation and no real
  constraint, while adding a vocabulary to maintain in lockstep with two others.
- **One unified `Kind` table with a `target` discriminator** (`operational` /
  `data` / `both`), collapsing `Calibration` and `Calibration Period` into one
  kind that writes both rows. Rejected for now: it only pays off if the
  dual-write gesture exists, and that is deferred. The cause/effect test gets the
  same coherence in the dropdown without merging the tables.
- **A nullable `DefaultLevel` column on `EventKind`** as a soft pre-fill hint.
  Rejected: for the kinds where it would be unambiguous the context already
  supplies the answer, and for the kinds where the context is ambiguous the
  default would be wrong as often as right.
