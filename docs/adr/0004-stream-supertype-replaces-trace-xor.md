# 4. Stream supertype replaces the Trace exclusive arc

Date: 2026-06-11

## Status

Accepted. Supersedes ADR 0003 (stream-level XOR only — see Consequences).

## Context

ADR 0003 chose the exclusive-arc pattern for stream-level polymorphism
(`Channel | AnalysisSeries`) and set an explicit trip-wire: *"if a third table
needs to point at 'a Trace,' the recurring disjunction has earned its own
identity."*

That trip-wire has fired. Three tables now need to reference "any stream":

1. `Annotation` — already uses `Channel_ID xor AnalysisSeries_ID`
2. `ProcessingLineage` — input edges need to accept either a Channel or an
   AnalysisSeries as input (lab data processed into a derived Channel)
3. Future tables are predictable: `DatasetChannel`, series-level quality
   overrides, and any other construct that targets a measurement stream

Separately, the domain term **Trace** was defined in `CONTEXT.md` as
"a UI/exploration concept, not a stored table." That description turned out to be
aspirational rather than accurate — the concept kept reappearing as a structural
necessity. The name itself was borrowed from Plotly's own "trace" term, creating
a collision in the Data Explorer layer.

## Decision

Materialize **Stream** as a stored supertype table using table-per-type (TPT)
inheritance with a **shared primary key**:

```
Stream(Stream_ID PK identity, StreamKind)
Channel(Stream_ID PK FK → Stream, SignalInterface_ID, TagName, …)
AnalysisSeries(Stream_ID PK FK → Stream, SamplingPoint_ID, …)
```

`Stream_ID` is the universal identifier for any measurement stream. Channel and
AnalysisSeries each carry `Stream_ID` as their primary key (not a separate
surrogate). Every Channel and AnalysisSeries creation must first insert a Stream
row to obtain the shared `Stream_ID`.

Tables that previously used the XOR arc now carry a single non-NULL
`Stream_ID FK → Stream`:
- `Annotation.Stream_ID`
- `ProcessingLineage.InputStream_ID` (input edges)

The term **"Trace"** is retired from the domain vocabulary. The Data Explorer
uses **Stream** throughout. The Plotly series objects are an implementation
detail, not a domain concept.

## Consequences

- **ADR 0003 is partially superseded.** The stream-level XOR
  (`Channel | AnalysisSeries`) is replaced by the Stream supertype. The
  *instance-level* XOR in `Observation` (`Channel_ID | LabAnalysis_ID`) is
  unaffected — ADR 0003's rationale (read-path flatness, only two occurrences)
  still holds for that arc.
- **One ID for everything.** Code that previously held `channel_id` or
  `analysis_series_id` as external references should migrate to `stream_id`.
  The subtype-specific columns (SignalInterface, TagName, SamplingPoint…) remain
  on their respective tables.
- **Two inserts per Channel or AnalysisSeries creation.** Insert Stream first,
  get Stream_ID, then insert Channel or AnalysisSeries with that as PK.
- **`StreamKind` discriminator** on Stream enables fast "sensor vs. lab" filters
  without joining to the subtype tables.
- All existing `Annotation` queries must be updated: `Channel_ID` / `AnalysisSeries_ID`
  columns are replaced by `Stream_ID`.
- The stream-level XOR CHECK constraints in `Annotation` and any future tables
  are replaced by a non-NULL FK — simpler and enforced structurally.
