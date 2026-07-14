# What happens to the three dialogs Recording replaces?

- **Parent:** [Map: Recording](../map.md)
- **Label:** `wayfinder:grilling`
- **Blocked by:** [004 — What does the Recording dialog look like?](./004-what-does-the-recording-dialog-look-like.md)
- **Assignee:** _unclaimed_
- **Status:** open

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
