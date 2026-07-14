# Implement the Recording gesture

- **Parent:** [Map: Recording](../map.md)
- **Label:** `wayfinder:task`
- **Blocked by:** — (every decision it needs is closed: [001], [002], [004], [005], [006], [007])
- **Assignee:** _unclaimed_
- **Status:** open

## Question

None. This ticket has nothing left to decide — it exists to carry the decisions into `app/` and
`api/`. If implementing it raises a question, that question is a new ticket, not a judgement call
made in the PR.

The gesture, in one line: **standing on a plotted series, the user picks a named pedigree rung and
a kind, and one row is written to the table the rung implies — never choosing between an Event and
an Annotation.**

Binding decisions, and where each lives:

- **The dialog's shape** — target first, then kind, then `Moment / Range / Still going`, then
  details; one `st.dialog`, four fields, no tabs, no group headers, no Event/Annotation words on
  screen. Copy is load-bearing (see the transcript in [004]) — do not re-sentence it.
  Reference implementation: `app/prototype_recording_dialog.py` on branch
  `prototype/recording-dialog` (commit `ced53ed`). **Throwaway: read it, don't merge it.**
- **The routing** — the rung *is* the routing. Stream rung → `Annotation` (5 verdicts, [006]);
  every other rung → `Event` (15 causes) on the matching arc FK ([ADR-0006]).
- **Multi-stream + rung intersection + the Quality Flag split** — [007].
- **The overlay it writes into** — [005]: coverage decides band-vs-gutter, colour = kind, the 4
  group toggles. **Out of scope here** unless the write path needs it; the overlay is its own work.

## Tasks

1. **Widen the pedigree response so a rung can name its arc target.** (Blocking — see the
   "Surfaced" note in [007].) `GET /lineage/streams/{id}/pedigree` returns `equipment_identifier`
   as a display string only, and nothing at all for the signal interface / DAS.
   Add `equipment_id` to `DeploymentSegmentOut`, and `signal_interface` + `data_acquisition_system`
   (id + name) to `StreamPedigreeOut` — per [finding 003] they are time-invariant columns on the
   Channel, so they belong on the pedigree root, not on the per-deployment segments. Additive; no
   new resolution logic. Unit test: a sensor stream's pedigree yields an id for all 8 arc arms it
   can reach; a lab series yields the 5 it can.

2. **`_recording_dialog(streams, start, end, observation_id)` in `app/pages/explore.py`.**
   - Target selectbox: rung 0 is the *selection* (`… — the series`, or `The N selected series`);
     rungs above it are the **intersection** of the selected streams' pedigrees, ordered narrow →
     wide, defaulting to the equipment when present.
   - Kind selectbox: `list_annotation_kinds()` when rung 0 is selected, else `list_event_kinds()`.
   - Time: `segmented_control` — Moment / Range / Still going — prefilled from the brush.
   - Observation pin: one checkbox, shown only when a point was clicked **and** rung 0 is selected.
   - Save: rung 0 → `create_annotation` once per selected stream (fan-out, existing per-stream
     error collection); any other rung → `create_event` with exactly that one arc FK set.
     **Not** `create_equipment_event` — that legacy path goes away.

3. **Delete `_annotation_dialog` and `_equipment_event_dialog`;** repoint all six call sites
   (scalar sensor, scalar lab, vector view, image gallery, image lightbox, and the
   `_show_annotation_dialog` session-state hop). The `is_lab` branch dies with the Quality Flag tab.

4. **`_quality_flag_dialog`** — the old Tab 2, lifted out unchanged behind its own "Set quality
   code…" button next to Record. Sensor-only. Wording says plainly that it **rewrites** the stored
   flag on every point in the range (it is an edit, not a claim).

5. **Tests** (`tests/app/`, AppTest — [see the map's note]): the interesting assertion is the
   routing, so assert it directly.
   - picking rung 0 + a verdict → `create_annotation` called once per selected stream, `create_event`
     not called;
   - picking the equipment rung + a cause → `create_event` called once with `equipment_id` set and
     the other 7 arc FKs absent;
   - a heterogeneous 2-stream selection offers only the shared rungs;
   - the observation checkbox appears only for rung 0 + a clicked point.
   Patch `app.api_client.*` per the `apptest_patch_target` convention.

## Out of scope

- The chart overlay ([005]) — reading recordings back. Separate work.
- A standalone Recording entry point with no chart to stand on (map, "Out of scope").
- The `events.py` / `annotation_kinds.py` admin pages — they stay as the raw escape hatch ([007]).

[001]: ./001-which-levels-can-each-kind-apply-to.md
[002]: ./002-when-does-one-gesture-write-two-rows.md
[004]: ./004-what-does-the-recording-dialog-look-like.md
[005]: ./005-how-do-eight-levels-of-overlay-not-drown-the-chart.md
[006]: ./006-retire-the-six-cause-named-annotationkinds.md
[007]: ./007-what-happens-to-the-three-dialogs-recording-replaces.md
[finding 003]: ../findings/003-stream-lineage-query.md
[ADR-0006]: ../../docs/adr/0006-unified-event-polymorphic-target.md
