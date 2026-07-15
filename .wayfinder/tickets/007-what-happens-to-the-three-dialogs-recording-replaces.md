# What happens to the three dialogs Recording replaces?

- **Parent:** [Map: Recording](../map.md)
- **Label:** `wayfinder:grilling`
- **Blocked by:** [004 — What does the Recording dialog look like?](./004-what-does-the-recording-dialog-look-like.md)
- **Assignee:** claude (session 2026-07-14)
- **Status:** closed — see [Resolution](#resolution)

## Question

[004](./004-what-does-the-recording-dialog-look-like.md) fixed the Recording dialog's shape:
target first (a named pedigree rung), then a kind drawn from the vocabulary that target implies,
then Moment/Range/Still-going, then details. One `st.dialog`. The three existing dialogs can now be
judged against it:

1. **`_annotation_dialog`** ([explore.py:313](../../app/pages/explore.py#L313)) — Annotation +
   Quality Flag *tabs*, stream-anchored, multi-stream fan-out (`channel_ids` / `series_ids`),
   optional `observation_id` pin, ISO text inputs.
2. **`_equipment_event_dialog`** ([explore.py:503](../../app/pages/explore.py#L503)) — equipment PK
   selectbox + event-type selectbox + ISO text inputs. Subsumed by Recording standing on the
   `equipment` rung.
3. The lab-point **annotate** button and the raw `selectbox + number_input` form on
   [events.py](../../app/pages/events.py) (the admin escape hatch — explicitly out of scope for
   replacement, but it must not *contradict* Recording).

Decide, per dialog: **replaced, wrapped, or kept as a fast path?** Specifically:

- **Multi-stream.** `_annotation_dialog` writes one annotation per selected stream in one Save.
  Recording's target picker names *one* rung. Does Recording keep the fan-out (N verdicts, one
  gesture — which is still "one row per stream", not a dual-write), or does it write one and force
  repetition? This is the one place the 004 shape is genuinely silent.
- **The Quality Flag tab.** It is not an Annotation at all — it writes quality codes on
  observations. Does it survive as a second tab (reintroducing the tabs 004 deliberately dropped),
  become its own gesture, or move out of the dialog entirely?
- **Lab series.** `_annotation_dialog` already special-cases them (no Quality Flag tab). Under
  Recording a lab series' pedigree has no equipment / interface / DAS rungs — the target list is
  simply shorter. Confirm that's all it takes.
- **Removal order.** Is Recording shipped alongside the old dialogs and they're deleted after, or
  does it land as a replacement in one change?

**Output:** a decision per dialog, sharp enough that the implementation PR has nothing left to
argue about.

## Resolution

**Both Explorer dialogs are replaced outright, in one change. The Quality Flag tab is not a
Recording at all and leaves the dialog. `events.py` stays as the admin escape hatch.**

### 1. `_annotation_dialog` — replaced

Deleted. All six call sites (scalar sensor points, scalar lab points, the vector view's
"Create Annotation", the image gallery's "Annotate selected images", the image lightbox, and the
`_show_annotation_dialog` state hop) call `_recording_dialog(streams, start, end, observation_id)`
instead. The dialog it opens is exactly the 004 shape — no tabs.

**Multi-stream: the fan-out survives, and it is the *stream rung itself*.** This is the one place
004 was silent, and the answer falls out of taking 004 literally. The first rung of the target
selectbox is not "a stream" but **the selection the user already made on the chart** — it reads
`Hach SC1000 pH · CH-12 — the series` for one, and `The 3 selected series` for several. Recording
does not re-ask what the brush already said. Choosing it writes **one verdict per selected stream**
— which is not the dual-write [002](./002-when-does-one-gesture-write-two-rows.md) forbade (that
was one gesture writing into *two tables*); it is N rows of one kind in one table, the same shape
the current dialog already ships and users already rely on.

**The rungs above the stream are the pedigree *intersection*.** A cause is one row on one
operational unit, so when the selection spans several streams a rung is offered only if **every**
selected stream shares it. Brush two channels on the same probe → all rungs. Brush a pH and a
turbidity probe in the same tank → the equipment rung disappears, sampling point / process unit /
site / campaign remain. Brush across two sites → only the campaign survives. With one stream
selected (the overwhelmingly common case) the list is exactly 004's. The rule is one line to state
and a set-intersection to implement, and it makes the "one cause, one target" constraint visible
instead of enforced by a validator.

### 2. The Quality Flag tab — moved out, kept as its own gesture

It is **not a Recording**: a recording *appends a claim* and is freely retractable; a quality flag
**overwrites the stored `QualityCode` on every observation in the range**. Same button, same
selection, but one is a note and the other is an edit to the data. Putting them behind tabs in one
dialog was the muddle — it is what made "annotate" and "flag" feel like variants of each other.

It becomes a **separate button beside Record** on the same selection ("Set quality code…"),
opening its own small dialog: quality code + range + Apply, sensor-only, worded so the rewrite is
obvious. **The tabs 004 dropped do not come back.**

### 3. Lab series — confirmed, and it gets simpler than the ticket assumed

A lab series' pedigree simply has no equipment / signal-interface / DAS rungs, so its target list
is shorter (series → sampling point → process unit → site → campaign). That is all it takes.

The bonus the ticket didn't anticipate: `_annotation_dialog`'s `is_lab` special case existed
**only** to hide the Quality Flag tab from lab series. Once the flag leaves the dialog (decision 2)
the special case has nothing left to do and dies with it. Lab and sensor become the same code path
with a different rung list.

### 4. `_equipment_event_dialog` — replaced, with one deliberate capability loss

Deleted; the equipment-PK selectbox becomes the "— the probe" rung, and the write moves from the
legacy `create_equipment_event` to the unified `create_event` (ADR-0006, exactly one arc FK).

**The loss:** the old dialog let you pick *any* equipment, including equipment not on the chart.
Recording's rungs come from the plotted streams' pedigree, so that reach is gone. Accepted — it is
the map's already-out-of-scope "standalone Recording entry point", and `events.py` remains the
escape hatch for it today. If someone misses it, that's the signal to build the standalone entry
point, not to keep this dialog.

### 5. `events.py` / `annotation_kinds.py` admin pages — kept, and they don't contradict

Out of scope for replacement per the charter, and nothing here makes them wrong: both are
data-driven off the API vocabularies, so ADR-0007's pruning reaches them for free. They stay the
raw, integer-PK audit surface.

### 6. Removal order — one change, no overlap

Recording lands *as* the replacement; the two dialogs are deleted in the same PR. Shipping them
side by side would mean two write paths for the same fact, two sets of tests, and a period where
the Explorer answers "how do I write this down?" in two contradictory ways — for the same users,
who are the ones we're trying to un-confuse. The swap is mechanical (six call sites, one new
dialog), so the usual reason to stage a migration doesn't apply.

### Surfaced: the pedigree endpoint can't name the arc targets yet

Blocking gap for implementation. `GET /lineage/streams/{id}/pedigree`
(`StreamPedigreeOut` / `DeploymentSegmentOut`) returns `sampling_point_id`, `process_unit_id`,
`site_id` and `campaign_id` — but **`equipment_identifier` only as a display string, with no
`equipment_id`**, and **no `signal_interface_id` / `data_acquisition_system_id` at all**. Recording
needs an ID per rung to write the arc FK. Per
[finding 003](../findings/003-stream-lineage-query.md) the interface/DAS are time-invariant columns
on the Channel, so this is an additive widening of the response, not new resolution logic. Handed
to the implementation ticket as its first task.
