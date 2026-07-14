# Can we query the events relevant to a Stream?

- **Parent:** [Map: Recording](../map.md)
- **Label:** `wayfinder:research`
- **Blocked by:** —
- **Assignee:** _unclaimed_
- **Status:** closed
- **Findings:** [003-stream-lineage-query.md](../findings/003-stream-lineage-query.md)

## Answer

**Yes — the lineage walk already ships.** `get_stream_pedigree`
(`GET /lineage/streams/{id}/pedigree?from=&to=`) already returns the windowed deployment timeline
that the overlay needs, and the CSV export already calls it. It covers 6 of the 8 `Event` targets;
`SignalInterface` and `DataAcquisitionSystem` are time-invariant columns on the Channel, one join
away. Campaign is _not_ a `(stream, time)` puzzle — it is stamped on the deployment row.

Three gaps: `/events` has no time filter; nothing composes pedigree × events; and **derived
channels resolve to zero segments** (no SignalInterface → empty overlay). Recommended shape:
one server-composed `GET /streams/{id}/recordings?from=&to=` returning level-tagged recordings,
cached client-side (the pedigree has an N+1 that the per-render overlay would expose).

## Question

Today the Explorer overlays **equipment events only** — it calls
`GET /equipment/{id}/lifecycle`. An event on a `SamplingPoint`, `Site`, or `Campaign` is invisible
on every chart, even when it is the thing that explains the data in front of you. The chosen
overlay design is **"whole lineage of the series, user-toggleable per level."**

That requires a query that does not exist. Establish whether it can:

1. Given a `Stream` (sensor Channel or lab AnalysisSeries), what is its **lineage** — the set of
   `Event` targets that are ancestors of it? Walk both hierarchies: acquisition
   (`Channel → Equipment → SignalInterface → DataAcquisitionSystem`) and spatial
   (`SamplingPoint → ProcessUnit → Site`), plus the `Campaign` active over the queried window.
2. Does the schema actually let you traverse that today? Which FKs / views exist, which are
   missing? **A lab `AnalysisSeries` has no Equipment** — does its lineage differ in shape?
3. `Campaign` is time-varying — a stream can sit under different campaigns over its life. Is
   "the active campaign" a function of `(stream, time)`? Is there already a view for this
   (the CSV export reportedly stamps sampling location + campaign per row — reuse it?).
4. Shape the API: one endpoint (`GET /streams/{id}/recordings?from=&to=`) returning events +
   annotations tagged with the level they came from (so the UI can toggle per level)? Or does
   the client fan out across the existing `/events?<arc_fk>=` filters?
5. Cost: is the lineage walk cheap enough to run per plotted series on every chart render?

**Output:** a markdown findings doc linked from this ticket, plus a recommended endpoint shape.
Research only — no endpoint gets built here.
