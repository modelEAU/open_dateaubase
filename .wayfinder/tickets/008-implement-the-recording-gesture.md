# Implement the Recording gesture

- **Parent:** [Map: Recording](../map.md)
- **Label:** `wayfinder:task`
- **Blocked by:** — (every decision it needs is closed: [001], [002], [004], [005], [006], [007])
- **Assignee:** claude (session 2026-07-15)
- **Status:** closed — see [Outcome](#outcome)

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

## Outcome

**Shipped. All five tasks land as one change; the two Explorer dialogs are gone.**

1. **Pedigree widened.** `DeploymentSegmentOut` gains `equipment_id`; `StreamPedigreeOut`
   gains `signal_interface` + `data_acquisition_system` (a new `PedigreeNodeOut` = `{id, name}`)
   on the root, since [finding 003] says the acquisition arms are time-invariant Channel columns.
   The repo's identity query joins `SignalInterface`/`DataAcquisitionSystem`; the segment query
   carries `Equipment_ID`. A lab series yields `None` for all three. Unit test: a sensor pedigree
   names all 8 arc arms, a lab series the 5 it can reach (`tests/unit/test_stream_pedigree.py`).

2. **`_recording_dialog(streams, start, end, observation_id)`** replaces both dialogs. Target
   selectbox = the stream rung (`… — the series` / `The N selected series`) plus the pedigree
   **intersection** ordered narrow→wide, defaulting to the equipment; kind selectbox draws
   `list_annotation_kinds()` on the stream rung, else `list_event_kinds()`;
   `segmented_control` Moment/Range/Still-going; the observation pin shows only on the stream rung
   with a clicked point. Save: stream rung → `create_annotation` once per stream; any other rung →
   `create_event` with exactly that one arc FK. Copy follows the [004] prototype. **House-style
   note:** the kind selectbox uses the `NONE_LABEL` sentinel row, not `index=None` (guarded by
   `test_no_hand_spelled_sentinel_labels`); every widget carries `help=`.

3. **Both dialogs deleted**, all six call sites repointed (scalar sensor + lab, vector, image
   gallery, image lightbox via `_show_annotation_dialog`). The `is_lab` branch and the
   `_show_event_dialog` / `_event_equipment_ids` session state died with them; `main()` no longer
   preloads equipment / kind / event-type lookups (the dialog resolves its own per gesture).

4. **`_quality_flag_dialog`** lifted out behind its own "Set quality code…" button, sensor-only,
   worded so the rewrite (not a claim) is obvious.

5. **Routing asserted directly** (`tests/app/test_recording_dialog.py`, driven via
   `AppTest.from_function` so the `@st.dialog` reopens each rerun): stream rung + verdict →
   `create_annotation` once per stream and no event; equipment rung + cause → one `create_event`
   with only `equipment_id` set; a heterogeneous 2-stream selection offers only shared rungs; the
   pin checkbox appears only on the stream rung with a clicked point. `test_explore_selection.py`
   and `test_explore_lab.py` were rewritten off the old dialogs.

**Verification:** 795 unit+app tests pass, 270 API tests pass. **Left undone:** the Playwright
`tests/e2e/test_explore_screenshot.py` still drives the removed dialogs by UI text — the broken
browser tier (unit-tests-only house rule), flagged for whoever next revives e2e. No schema
version bump: the pedigree change is a Pydantic response widening, not a `schema_dictionary` edit.

[001]: ./001-which-levels-can-each-kind-apply-to.md
[002]: ./002-when-does-one-gesture-write-two-rows.md
[004]: ./004-what-does-the-recording-dialog-look-like.md
[005]: ./005-how-do-eight-levels-of-overlay-not-drown-the-chart.md
[006]: ./006-retire-the-six-cause-named-annotationkinds.md
[007]: ./007-what-happens-to-the-three-dialogs-recording-replaces.md
[finding 003]: ../findings/003-stream-lineage-query.md
[ADR-0006]: ../../docs/adr/0006-unified-event-polymorphic-target.md
