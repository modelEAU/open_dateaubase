# Retire the six cause-named AnnotationKinds

- **Parent:** [Map: Recording](../map.md)
- **Label:** `wayfinder:task`
- **Blocked by:** —
- **Assignee:** jeandavidt (session 2026-07-14)
- **Status:** closed

## Question

Graduated from the fog by
[Which levels can each Kind apply to?](001-which-levels-can-each-kind-apply-to.md), which decided
the cause/effect test ([ADR-0007](../../docs/adr/0007-kind-level-association.md)) and cut
`AnnotationKind` from 11 kinds to 5. Nothing left to *decide* — but the vocabulary can't be
retired without a plan, and the Recording dialog tickets assume the pruned vocabulary.

Retire `Fault` (1), `Maintenance` (2), `Calibration Period` (3), `Experiment` (5),
`Process Event` (6), `Equipment Relocation` (11). Keep `Anomaly` (4), `Data Quality` (7),
`Note` (8), `Exclusion` (9), `Confirmed` (10) — rewriting `Anomaly`'s description so it visibly
absorbs the "something happened here I can't explain" case.

Settle:

1. **Delete or tombstone?** `sql/seed_demo.sql` has no `Annotation` rows, so nothing is orphaned
   *there* — but a deployed instance may have rows citing the retired kinds. Hard-delete with a
   remap (`Fault`/`Maintenance`/`Calibration Period` → `Data Quality`), or keep the rows and mark
   them inactive so history reads back unchanged? The v2.1 baseline is frozen, so this is
   migration-worthy either way.
2. **`equipment_move.py`.** [Line 41](../../api/v1/endpoints/equipment_move.py#L41) hardcodes
   `AnnotationKind` 11 and writes an "Equipment Relocation" *annotation* on every move. Under
   ADR-0007 that write is miscategorised: a move is a **cause**, and
   `EquipmentLocationHistory` already records it. Does the endpoint write an `Event`
   (a new `EventKind`? `Relocation` is not in the 15) or stop writing a recording at all?
3. **Version bump + migration script.** Per repo rules a schema-dictionary edit only reaches a
   deployed DB via a `version.yaml` bump; DDL regenerates via `uv run mkdocs build`.
4. **Do any `AnnotationKind` colors need reassigning** once six rows leave? The five survivors
   should be visually distinguishable on a chart overlay.

**Output:** the retired vocabulary in `schema_dictionary/tables/AnnotationKind.yaml`, a decision
on `equipment_move.py`, and whatever migration the answer to (1) demands.

## Answer

**Deleted, with a remap — and the equipment-move endpoint now writes no recording at all.**

1. **Delete, don't tombstone.** There is no `IsActive` flag on `AnnotationKind` and adding one
   buys a vocabulary that reads back muddy forever: every dropdown, every colour legend, every
   mapper would have to remember which five of eleven kinds are real. The forward migration
   (`migrations/v2.2.0_to_v2.3.0_mssql.sql`) instead **remaps existing annotations onto a
   survivor before deleting the retired rows** (the `DELETE` would otherwise trip
   `FK_Annotation_AnnotationKind_ID`): `Fault` / `Maintenance` / `Calibration Period` →
   `Data Quality`; `Experiment` / `Process Event` / `Equipment Relocation` → `Note`. The retired
   kind's name is **prefixed into the `Comment`** (`[Calibration Period] …`), so no wording is
   lost and a human can still see what the row used to claim. **Surviving IDs are not
   renumbered** — 1/2/3/5/6/11 stay burned, so an old row can never silently change meaning.
   Rollback restores the six rows but leaves remapped annotations on their survivor kind; the
   comment prefix is the recovery path.

2. **`equipment_move.py` stops writing a recording.** Not an Event, not an Annotation — *nothing*.
   `EquipmentLocationHistory` / `EquipmentWiringHistory` **are** the record of a move (and per
   [003](003-can-we-query-the-events-relevant-to-a-stream.md) the pedigree walk already surfaces
   the relocation on the chart for free), the app's move wizard already offers an explicit
   `create_equipment_event` when the mover wants one, and per
   [002](002-when-does-one-gesture-write-two-rows.md) one gesture writes one row. Auto-annotating
   every channel of the equipment was exactly the miscategorised write ADR-0007 kills — and it
   would have polluted the very overlay [005](005-how-do-eight-levels-of-overlay-not-drown-the-chart.md)
   is trying to keep readable. Deleted: `_annotate_move`, `_get_channel_ids`,
   `annotation_repository.create_equipment_move_annotations`, and the `annotation_ids` field on
   both move responses (plus the dead `PortRelocate*` schemas that carried it). No new
   `Relocation` EventKind: the 15 causes stay as they are.

3. **Version bumped 2.2.0 → 2.3.0**, migration + rollback generated and hand-completed (the
   generator emits the seed `DELETE` but cannot see *modified* seed rows, so the two rewritten
   descriptions are hand-written `UPDATE`s), DDL regenerated via `uv run mkdocs build`,
   `sql/init.sql` repointed at the v2.3.0 scripts.

4. **No colour reassignment.** The five survivors are already distinct and far apart — Anomaly
   `#FF69B4` pink, Data Quality `#AA44FF` purple, Note `#888888` grey, Exclusion `#CC0000` red,
   Confirmed `#00AA00` green. Guarded by a uniqueness assertion in the new test.

`Anomaly`'s description was rewritten to visibly absorb the escape-hatch case ("Unexplained
behaviour — something happened here that no known event accounts for"); `Data Quality`'s now
points at the `Event_ID` link for the why.

**Verification:** `tests/unit/test_annotationkind_verdicts.py` (red on the eleven-kind
vocabulary), 647 unit tests pass. The two retired acceptance criteria in
`tests/integration/test_temporal_lifecycle.py` (AC-LO4, AC-ANN — "a move auto-annotates every
affected channel") were removed, and `docs/operations/sensor-relocation-sop.md` now says a move
writes no annotation.
