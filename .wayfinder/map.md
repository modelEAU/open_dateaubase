# Map: Recording — one gesture to annotate data at any level

`wayfinder:map`

## Destination

A locked design — glossary, ADR(s), and a reacted-to UI prototype — for **[Recording]**:
a single gesture in the Data Explorer that lets a user write down what happened without
ever choosing between an `Event` and an `Annotation`, at any of the eight `Event` targets
or the two `Annotation` anchors, and that shows every recording relevant to a plotted
series back on its chart.

Done when: nothing is left to decide before someone implements it.

## Notes

**Domain.** Wastewater / water-quality monitoring (`open_datEAUbase`). The load-bearing
domain facts are already settled and must not be re-litigated:

- `Event` = a claim about the **operational unit** (8-way exclusive arc: Channel, Equipment,
  SignalInterface, DataAcquisitionSystem, SamplingPoint, ProcessUnit, Site, Campaign).
  [ADR-0006](../docs/adr/0006-unified-event-polymorphic-target.md).
- `Annotation` = a claim about the **data** (anchored to one `Stream`, optional `Observation_ID`
  pin, optional `Event_ID` back-link — the causal join).
- The user picks a **Kind**, never a table. Kind routes the write. Level is *pre-filled from
  context*, never asked as an opening question. See `Recording` and `Kind` in
  [CONTEXT.md](../CONTEXT.md).

**Skills every session should consult:** `/domain-modeling` (the model is still moving),
`/grilling`, `/prototype` for the UI tickets, `dateaubase-app-map` before touching `app/`,
`write-streamlit-tests` if a ticket produces test-shaped output.

**Standing preferences.** Plan, don't do — these tickets produce decisions, not merged code
(the prototype ticket produces a throwaway to react to, not production code). Unit tests only
(`uv run pytest tests/unit/`). Schema edits need a `version.yaml` bump to reach a deployed DB.

## Decisions so far

<!-- one line per closed ticket -->

- [Which levels can each Kind apply to?](tickets/001-which-levels-can-each-kind-apply-to.md) —
  **None: a Kind carries no level.** The sets are too wide to disambiguate anything
  (`Cleaning` = Equipment *or* SamplingPoint; `PowerOutage` = Site *or* DAS *or* SignalInterface),
  so no column, no link table, no constraint. Level is pre-filled from context; the DB stays
  permissive. The rigour moves into the **vocabulary** instead — a cause/effect test that cuts
  `AnnotationKind` from 11 kinds to 5 data-quality verdicts.
  ([ADR-0007](../docs/adr/0007-kind-level-association.md))

- [Can we query the events relevant to a Stream?](tickets/003-can-we-query-the-events-relevant-to-a-stream.md) —
  **Yes, and the walk already ships.** `get_stream_pedigree` returns the windowed deployment
  timeline (equipment → sampling point → process unit → site → campaign, one segment per slice of
  the stream's life); the CSV export already calls it. It covers 6 of the 8 `Event` targets;
  `SignalInterface`/`DAS` are time-invariant columns on the Channel. Campaign needs no interval
  resolution — it's stamped on the deployment row. Recommended: one server-composed
  `GET /streams/{id}/recordings?from=&to=`, plus a `from`/`to` filter on `/events` (it has none).
  ([findings](findings/003-stream-lineage-query.md))

- [How do eight levels of overlay not drown the chart?](tickets/005-how-do-eight-levels-of-overlay-not-drown-the-chart.md) —
  **Coverage decides the rendering, not level.** Anything covering >25% of the *visible* window
  drops to a gutter lane below the axis; everything else is an in-plot band — recomputed on zoom, so
  a 3-hour site-wide outage stays a band while a months-long campaign stays a strip. Toggles are the
  **4 groups** (Data / Acquisition / Spatial / Campaign), all **on by default**. **Colour = kind**
  (the 5 ADR-0007 verdicts for annotations, one neutral steel for all events — `EventKind` gets no
  `Color`); **level = position**. Overlap stacks in per-group lanes, never merges. Hover reads,
  click opens the Recording dialog. The table survives as **Recordings** + Level/Target columns.
  **Derived streams inherit** their ancestors' recordings via `ProcessingLineage`, tagged `via CH-n`.
  ([prototype](https://claude.ai/code/artifact/7fb848ff-ccab-4252-894c-cfc1d9ded838))

- [What does the Recording dialog look like?](tickets/004-what-does-the-recording-dialog-look-like.md) —
  **Target first, then kind. One dialog, four fields.** The user picks a *named* pedigree rung
  ("Hach SC1000 pH · #A21 — the probe"), and the rung decides the vocabulary: the series takes the
  5 verdicts, every other rung takes the 15 causes. So **the target selection alone routes the
  write** — the Event/Annotation split never reaches the user's face, not even as a group header,
  and a 20-item dropdown (rejected variant A) never happens. A verdict has exactly one possible
  target, so the 8-way level question only exists for causes. Time is `Moment / Range / Still going`,
  prefilled from the brush — no `IsInstantaneous` jargon. One `st.dialog`, no second half (per
  [002](tickets/002-when-does-one-gesture-write-two-rows.md)). Copy is load-bearing: sentence glue
  was rejected, every field asks a whole question.
  (prototype: `app/prototype_recording_dialog.py` on branch `prototype/recording-dialog` — throwaway, not merged)

- [Retire the six cause-named AnnotationKinds](tickets/006-retire-the-six-cause-named-annotationkinds.md) —
  **Shipped: 11 kinds → 5 verdicts, and a move now writes no recording.** Hard-delete, not
  tombstone: the migration remaps existing annotations onto a survivor first (`Fault`/`Maintenance`/
  `Calibration Period` → `Data Quality`; `Experiment`/`Process Event`/`Equipment Relocation` →
  `Note`) with the old kind name prefixed into the comment, then deletes. Survivor IDs are **not**
  renumbered — 1/2/3/5/6/11 stay burned. `equipment_move.py` stops auto-annotating every channel:
  the history rows *are* the record of a move, the pedigree walk already puts it on the chart, and
  the move wizard already offers an explicit Event. No new `Relocation` EventKind; no colour
  reassignment. Schema **v2.2.0 → v2.3.0**.

## Not yet specified

- **Test strategy** for the Recording dialog. Narrower again after
  [004](tickets/004-what-does-the-recording-dialog-look-like.md): one gesture, one row, four
  fields, and the target selection alone decides the table — so the interesting assertion is just
  "picking rung X + kind Y posts to table Z". Likely one AppTest, unremarkable; confirm when the
  implementation ticket is written.

## Out of scope

- **Replacing the Events / Annotations admin pages.** Decided at chartering: Recording is the
  humane path *in the Explorer*; the admin pages stay as the raw escape hatch and audit table.
  Their integer-PK `number_input` forms are ugly but they are not the pain.
- **A standalone Recording entry point** for events with no chart to stand on (a site visit, a
  campaign-wide note). Follows from Explorer-only scoping; revisit as a fresh effort.
- **Logbook parsing/ingest itself.** Building it is another map. (Kind↔level was supposed to
  enable it; per ADR-0007 there is no Kind↔level, so the enabler is now the pruned vocabulary.)
  **How the mapper routes free text** was held as fog pending
  [004](tickets/004-what-does-the-recording-dialog-look-like.md); 004 answers it in principle — a
  human resolves the ambiguity by picking the **target** first, and the target implies the table —
  so the mapper's hard problem is target resolution, not table choice. That's a question for the
  logbook map, not this one. Out of scope, with the answer handed forward.
- **[When does one gesture write two rows?](tickets/002-when-does-one-gesture-write-two-rows.md)** —
  **one recording writes one row.** A "we were calibrating, so this window is dodgy" recording is
  simply an `Event` today; the dual-write gesture gets wired up if and when users ask for it.
  `Annotation.Event_ID` still carries the causal join — only the gesture is deferred.

[Recording]: ../CONTEXT.md#recording
