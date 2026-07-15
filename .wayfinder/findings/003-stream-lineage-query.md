# Findings: can we query the events relevant to a Stream?

- **Ticket:** [003](../tickets/003-can-we-query-the-events-relevant-to-a-stream.md)
- **Verdict:** **Yes.** The lineage walk already exists, shipped, and is already called by the
  Explorer's CSV export. Six of the eight `Event` targets fall out of it directly; the other two
  are one join away. The overlay needs **one new endpoint** and **one new filter on `/events`** —
  no new schema, no new view, no new traversal logic.

---

## 1. The lineage walk already exists: `get_stream_pedigree`

[`channel_repository.get_stream_pedigree`](../../api/v1/repositories/channel_repository.py#L713)
(behind `GET /lineage/streams/{id}/pedigree?from=&to=`) already answers question 1 of the ticket.
It returns the stream's identity plus a **deployment timeline**: one segment per slice of the
stream's life with a stable location, each carrying `equipment`, `sampling_location`,
`process_unit`, `site`, `campaign`, `responsible_person`, and its own `valid_from`/`valid_to`.
`from`/`to` already restrict it to segments overlapping a window — exactly the overlay's window.

For a **sensor Channel** it does the EWH×ELH temporal join:

```text
Channel → (vw_ChannelResolved: current port)
        → EquipmentWiringHistory   (which Equipment was on that interface/port, when)
        → EquipmentLocationHistory (where that Equipment stood, when)
        → SamplingPoint → ProcessUnit → Site
        + Campaign  (stamped on the ELH row)
```

For a **lab AnalysisSeries** the shape genuinely differs (ticket Q2): there is no Equipment and no
acquisition chain at all. `AnalysisSeries` carries `SamplingPoint_ID` and `Campaign_ID` as plain
columns, so its lineage is a **single, open, time-invariant segment** — the pedigree already
returns exactly that. So the two stream kinds unify at the *segment* level, not at the join level,
which is precisely what the overlay consumes.

**This is not theoretical.** [`explore_export.py`](../../app/components/explore_export.py) already
calls it per exported stream to build the metadata YAML. The traversal is in production.

## 2. Coverage of the eight Event targets

| Event target | Reachable from a Stream? | How |
| --- | --- | --- |
| `Channel` | yes | it *is* the stream (sensor kind) |
| `Equipment` | yes | pedigree segment → `equipment` |
| `SamplingPoint` | yes | pedigree segment → `sampling_location` |
| `ProcessUnit` | yes | pedigree segment → `process_unit` |
| `Site` | yes | pedigree segment → `site` |
| `Campaign` | yes | pedigree segment → `campaign` |
| `SignalInterface` | **not yet** | `Channel.SignalInterface_ID` — one column read |
| `DataAcquisitionSystem` | **not yet** | `SignalInterface.DataAcquisitionSystem_ID` — one further join |

The two missing rungs are the cheapest ones in the whole graph: both are **time-invariant on the
Channel** (a Channel is created once and never rewired — rewiring is modelled on the *Equipment*
side, in `EquipmentWiringHistory`). So they are a two-column `SELECT`, not a temporal walk. A lab
series has neither, and correctly shows no SignalInterface/DAS level.

**Recommendation:** add `signal_interface` + `data_acquisition_system` to the pedigree's
time-invariant identity block (not to the deployment segments — they don't vary per deployment).
That completes the arc and benefits the export YAML too.

## 3. Campaign is *not* a `(stream, time)` puzzle (ticket Q3)

Good news, and worth stating plainly because the ticket suspected otherwise. There are three
routes to "the campaign of this stream" in the schema:

1. `EquipmentLocationHistory.Campaign_ID` — stamped on the deployment row. **Already time-scoped**,
   because the ELH row itself has `ValidFrom`/`ValidTo`. This is what the pedigree returns and what
   the CSV export stamps per row.
2. `CampaignSamplingLocation` / `CampaignEquipment` — untimed membership tables.
3. `Campaign.CampaignStartDateTime` / `CampaignEndDateTime` — the campaign's own span.

Route 1 already gives us a per-time-slice answer for free, so **no interval resolution needs to be
invented**. Use it; ignore 2 and 3 for the overlay. (Route 2 is used only as a single-site fallback
inside `_pedigree_campaign`; route 3 is display metadata.) If the deployment row has a NULL
`Campaign_ID`, the honest answer is "no campaign at this level" — not "go guess from campaign
dates."

## 4. The gaps — what actually has to be built

Three, all small.

**Gap A — `/events` has no time filter.**
[`get_events`](../../api/v1/repositories/event_repository.py#L161) filters on the eight arc FKs and
nothing else. It returns *every* event ever recorded on a target. The overlay needs
"events overlapping [from, to]". Add `from`/`to` to `get_events` — a standard overlap predicate on
`(EventDateTimeStart, EventDateTimeEnd)`, with `IsInstantaneous` rows treated as a point. This is
the same predicate `get_equipment_events` already implements for the lifecycle endpoint, so there
is a working reference to copy.

**Gap B — no single "recordings for a stream" endpoint.**
Today the Explorer calls `GET /equipment/{id}/lifecycle` and gets equipment events only. Nothing
composes pedigree × events.

**Gap C — derived channels fall off the map.**
A derived Channel (`ProducedByStep_ID` set) has `SignalInterface_ID = NULL`, so the EWH join
matches nothing and the pedigree returns **zero deployment segments**. Every derived stream — and
the Explorer plots them — would show an empty overlay, which is worse than wrong: it looks like
"no events happened." The fix is to resolve lineage through `ProcessingLineage` back to the root
channel(s) and take *their* pedigree. That is a real decision, not a detail — see "Open" below.

## 5. Recommended endpoint shape (ticket Q4)

**One endpoint, server-side composed.** Not a client fan-out.

```http
GET /streams/{stream_id}/recordings?from=&to=
```

```jsonc
{
  "stream_id": 42,
  "levels": [                      // ordered narrow → wide; the UI's toggle list
    {"level": "channel",   "target_id": 42,  "label": "CH-42 · pH raw",      "recordings": [...]},
    {"level": "equipment", "target_id": 7,   "label": "Hach SC1000 #A21",    "recordings": [...]},
    {"level": "signal_interface", ...},
    {"level": "data_acquisition_system", ...},
    {"level": "sampling_point", "target_id": 3, "label": "Effluent weir",    "recordings": [...]},
    {"level": "process_unit", ...},
    {"level": "site", ...},
    {"level": "campaign", ...},
    {"level": "stream",    "target_id": 42,  "label": "this stream",         "recordings": [...]}  // Annotations
  ]
}
```

Each recording is `{kind: "event"|"annotation", id, kind_name, start, end, is_instantaneous,
title, notes, event_id?}` — one flat shape so the chart renderer doesn't branch.

Why one endpoint and not a client fan-out across `/events?<arc_fk>=`:

- The client **cannot do the fan-out without first doing the pedigree call anyway** — it doesn't
  know which equipment/sampling point/site the stream lived under. So a fan-out is 1 + 8 round
  trips minimum, per plotted series, versus 1.
- The **level label** ("which Equipment did this event happen to, and when was that relevant?")
  only exists server-side, in the pedigree segment. Making the client re-derive it duplicates the
  temporal join in Python.
- A stream with two deployments has **two** equipment ancestors, not one. The fan-out is over
  *segments × levels*, not just levels. That's the kind of loop that belongs in one SQL statement.

Annotations enter at the `stream` level and are already windowed
(`GET /timeseries/{id}/annotations?from=&to=`), so folding them in is a `UNION`, not new work.

## 6. Cost (ticket Q5)

Acceptable, with one caveat.

- The pedigree walk is `O(deployment segments)`, not `O(observations)`. A stream has a handful of
  segments over its whole life, and `from`/`to` cuts that further. Contrast with
  `vw_ChannelLocationAtTime`, which resolves lineage **per Observation** — that view is the wrong
  tool for the overlay and must not be used for it; it would do the temporal join a million times
  to answer a question about a dozen rows.
- Events per level is one indexed FK lookup each; all eight collapse into a single query with
  OR'd `IN` lists over the collected ancestor ids.
- **Caveat:** `get_stream_pedigree` currently issues 2 queries per segment (`_pedigree_segment`
  calls `_pedigree_sampling_point` and `_pedigree_campaign` per row) — a classic N+1. It's
  invisible at export time (one-shot, few streams) but the overlay runs **per plotted series on
  every chart render**. Either flatten those into the segment query, or cache the endpoint in
  `api_client` with the existing `st.cache_data(ttl=...)` pattern — the lineage of a stream over a
  fixed window is stable, so caching is the lazy correct answer. **Do the cache; flatten only if
  it measurably hurts.**

## 7. ~~Open~~ RESOLVED in [005](../tickets/005-how-do-eight-levels-of-overlay-not-drown-the-chart.md) — derived streams **do** inherit

Option (a) below was chosen. Resolve through `ProcessingLineage` to the root channel(s), union
their pedigrees, and tag the inherited levels `via CH-n` so the UI can label them and the user can
toggle them off with their group. Gap C is therefore **in scope for the recordings endpoint**, not
deferred. The original argument, kept for the record:

**Do derived streams inherit their ancestors' events?** (Gap C.) A pH channel that was
median-filtered has no equipment of its own, but the "sensor was being cleaned" event on the raw
channel's equipment explains the filtered data *just as well* — arguably it is the only thing that
does. Options:

- **(a) Inherit.** Resolve through `ProcessingLineage` to the root channel(s), union their
  pedigrees. Truthful, and matches the intuition that a derived stream is "the same measurement,
  processed." Costs one recursion and raises "whose annotation is it?" if two roots disagree.
- **(b) Don't.** A derived channel shows only its own annotations and its own `Channel`-level
  events. Cheap, and defensible: the derived stream is a *different claim about the world*.
  But it renders an empty overlay on exactly the streams users stare at hardest.

Recommend **(a)**, marked as a distinct level in the response (`"level": "equipment",
"via": "derived from CH-17"`) so the user can toggle inherited events off. But this is a modelling
call, not an implementation one — it belongs in the map, not in the endpoint's PR.

## Summary of work implied (research only — none of it built here)

1. Add `from`/`to` overlap filter to `get_events` (+ `/events` query params).
2. Add `signal_interface` / `data_acquisition_system` to the pedigree identity block.
3. New `GET /streams/{id}/recordings?from=&to=` composing pedigree × events × annotations.
4. Cache it in `api_client` (the N+1 in `_pedigree_segment` makes this non-optional).
5. Decide the derived-stream inheritance question first — it changes #3's shape.
