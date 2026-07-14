# How do eight levels of overlay not drown the chart?

- **Parent:** [Map: Recording](../map.md)
- **Label:** `wayfinder:prototype`
- **Blocked by:** [003 — Can we query the events relevant to a Stream?](./003-can-we-query-the-events-relevant-to-a-stream.md)
- **Assignee:** _unclaimed_
- **Status:** closed
- **Prototype:** <https://claude.ai/code/artifact/7fb848ff-ccab-4252-894c-cfc1d9ded838>
  (throwaway; source `scratchpad/overlay-mockup.html`, not checked in)

## Answers

1. **Coverage decides the rendering, not level.** A recording covering more than **25% of the
   visible window** renders as a gutter lane below the axis; everything else renders as an in-plot
   band. Recomputed on zoom, so a wide site event becomes a band once you zoom out past it, and a
   band becomes a strip once you zoom into it. One constant, no per-level configuration. Rejected:
   "high levels go to the gutter" — a 3-hour site-wide power outage is the most explanatory mark on
   the chart and must stay a band.
2. **Four toggles, not eight.** The 8 levels collapse to the 4 groups a user thinks in: **Data**
   (this stream's annotations), **Acquisition** (channel · equipment · signal interface · DAS),
   **Spatial** (sampling point · process unit · site), **Campaign**. Each pill carries its count.
   **All four default on** — including Campaign: it is usually one quiet gutter strip, and knowing
   which campaign you are inside is worth one lane.
3. **Colour encodes kind; level is encoded by position.** Annotations use the five ADR-0007 verdict
   colours (`Data Quality`, `Exclusion`, `Confirmed`, `Anomaly`, `Note`). Events all use **one**
   neutral steel — `EventKind` has no `Color` column and must not grow one; 15 hues is noise. Level
   is legible from _where_ the mark sits (which lane, or in-plot) and is named in tooltip + table.
4. **Overlap: lanes in the gutter, alpha in the plot.** The gutter has **one lane per group** (4,
   not 8), so wide recordings at different levels stack. In-plot bands are narrow by definition;
   where they do overlap they blend at low alpha and both stay hoverable. **Never merged** — two
   recordings are two claims.
5. **Hover reads, click opens.** Hover → kind, level, target, window, author. Click → the same
   Recording dialog that wrote it, in read/edit mode.
6. **The table survives**, renamed **Recordings**, gaining **Level** and **Target** columns. The
   `#` refs keep matching the chart labels. It stays the accessible/copyable view and the only
   thing that still works when six bands stack.
7. **Derived streams inherit their ancestors' recordings.** Resolved through `ProcessingLineage` to
   the root channel's pedigree, tagged `via CH-n` in tooltip and table, toggling with their group.
   Without this, the Acquisition group is empty on exactly the streams users stare at hardest.

## Question

Chosen design: a plotted series shows recordings from its **whole lineage**, with **per-level
toggles**. Today's chart draws `markArea` / `markLine` bands for annotations + equipment events
and already gets busy ([explore_echarts.py](../app/components/explore_echarts.py), `_overlay_markers`).
Now multiply by up to eight levels plus annotations.

Answer, with a picture:

1. A `Site`-level power outage spans *everything*. A campaign spans months. These are wide bands
   that will wash out the chart. Do wide/high-level recordings render differently — a thin gutter
   strip below the axis rather than a full-height band?
2. What are the toggles, concretely? Eight checkboxes is a lot of chrome. Group them
   (acquisition / spatial / campaign / data)? Default some off?
3. Colour: `AnnotationKind` already carries a `Color`. `EventKind` does not. Does colour encode
   **kind** or **level**? It cannot legibly encode both. (Consult `dataviz` — and note bands must
   stay legible in light and dark.)
4. Overlap: two recordings on the same span, at different levels. Stacked lanes, or merged?
5. How does a user get *from* a band *to* the record — hover tooltip, click-to-open?
6. Does the existing `_render_overlay_table` under the chart survive, and does it grow a level column?

Reuse ticket 003's endpoint shape; do not design the query here.

**Output:** a prototype (or annotated mockups) linked from this ticket + the user's reactions,
distilled into decisions. Throwaway.
