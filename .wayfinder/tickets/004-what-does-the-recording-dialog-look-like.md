# What does the Recording dialog look like?

- **Parent:** [Map: Recording](../map.md)
- **Label:** `wayfinder:prototype`
- **Blocked by:** [001 — Which levels can each Kind apply to?](./001-which-levels-can-each-kind-apply-to.md), [002 — When does one gesture write two rows?](./002-when-does-one-gesture-write-two-rows.md)
- **Assignee:** claude (session 2026-07-14)
- **Status:** closed — see [Resolution](#resolution)

## Question

Make the gesture concrete enough to react to. Build a **throwaway** Streamlit prototype (via
`/prototype`) of the Recording dialog and put it in front of the user.

It must answer, by being looked at:

1. **The kind picker.** One grouped list spanning both vocabularies — "What happened" (Calibration,
   Cleaning, Repair, PowerOutage…) vs "About the data" (Fault, Anomaly, Data Quality, Exclusion,
   Confirmed, Note). Is grouping enough, or does the user need search? Does the group header leak
   the Event/Annotation split back into their face — and does that matter?
2. **The target.** Pre-filled from context and *named*, never an integer PK. Standing on a pH
   series, the plausible targets are its channel, its probe, its sampling point, its process unit,
   its site, its campaign. How are they offered — a lineage breadcrumb the user clicks a rung of?
   A selectbox ordered by what the kind allows (per ticket 001)?
3. **Time.** Brushed range pre-fills start/end. Instantaneous vs interval vs ongoing
   (`IsInstantaneous`, null `EventDateTimeEnd`) — how is that expressed without a jargon checkbox?
4. **The optional second half** (per ticket 002) — how it appears without making the dialog feel long.
5. Does the whole thing fit in one `st.dialog`, or does it want two steps?

Compare against the three dialogs it would subsume:
`_annotation_dialog` and `_equipment_event_dialog` in [explore.py](../app/pages/explore.py), and the
raw `selectbox + number_input` form on [events.py](../app/pages/events.py).

**Output:** a prototype linked from this ticket + the user's reactions, distilled into decisions.
Throwaway code — it does not get merged.

## Resolution

**Target first, then kind. One dialog, four fields, no Event/Annotation split anywhere on screen.**

Prototype: `app/prototype_recording_dialog.py` on branch **`prototype/recording-dialog`**
(commit `ced53ed`) — not on `stage`, never merged. To look at it again:
`git checkout prototype/recording-dialog && uv run streamlit run app/prototype_recording_dialog.py`. Three variants were put in
front of the user (A kind-first, B two-step, C sentence-shaped); a fourth (D, a scope-ladder
slider) was built on request mid-session and rejected. **C wins.**

### The dialog

```text
What did this happen to?   [ Hach SC1000 pH · #A21 — the probe        ▾ ]   ← pedigree rungs, named
What happened to it?       [ Cleaning — physically cleaned or flushed ▾ ]   ← vocabulary follows the target
When                       ( Moment | ●Range | Still going )
                           Started [2026-03-04 08:12]  Ended [09:40]        ← prefilled from the brush
Details                    [                                          ]
                           > Cleaning happened to Hach SC1000 pH · #A21, from … to ….
                                                                    [ Record ]
```

### What the prototype settled

1. **The kind picker is not one list.** Ticket Q1 assumed a single grouped list spanning both
   vocabularies and asked whether grouping suffices or search is needed. Neither: **20 kinds in one
   dropdown is too long to use** (the user's words, killing variant A). Picking the **target first**
   filters the vocabulary to *one* of the two — so the user only ever sees 15 causes or 5 verdicts,
   never both, and never a group header. The Event/Annotation split **never reaches their face**.
   No search box needed at 15 items.
2. **The vocabulary follows the target, and the routing is free.** The series takes verdicts (it *is*
   data); every other rung takes causes (it *is* a thing in the plant). This is the cause/effect test
   of [ADR-0007](../../docs/adr/0007-kind-level-association.md) rendered as a UI affordance rather
   than a question — and it means the target selection alone decides the table. Confirms ADR-0007
   from the other end: a Kind still carries no level, but the *level* implies the vocabulary.
3. **A verdict has exactly one possible target — the stream.** So the 8-way level question only
   exists for causes. Half the gesture's apparent complexity was never there.
4. **Target = a flat selectbox of *named* pedigree rungs**, defaulting to the equipment (the probe —
   the common case). Never an integer PK. Ordered narrow → wide.
5. **Time needs no jargon.** `Moment / Range / Still going` (a `segmented_control`) covers
   `IsInstantaneous` and the null `EventDateTimeEnd`; the brushed range prefills start/end.
6. **One `st.dialog`, not two steps.** Variant B (kind-picker step, then a form) was rejected outright
   — "the buttons, the vagueness, blech".
7. **The observation pin** is a single checkbox — "Only the point I clicked (#…)" — shown only when a
   point was clicked *and* the target is the stream.
8. **Copy is load-bearing.** The first C draft used sentence glue ("On …", "there was …",
   placeholder "pick…") and was rejected as too loose even though the flow was right. Every field
   asks a whole, concrete question.

### Rejected, and why

- **A — kind first, 20-item dropdown, then a rung radio.** The dropdown is too long to use. Emoji
  grouping (🔧 plant / 📉 data) also leaks the storage split back at the user for no gain.
- **B — two steps.** Vague, button-grid step 1. Rejected without qualification.
- **D — scope ladder** (a `select_slider` climbing narrow → wide, shading everything the selected
  rung contains). Built mid-session at the user's suggestion, rejected on sight. Worth recording
  *why* it can't be rescued later: **the eight levels are not one chain.** They fork at the stream —
  acquisition (channel → signal interface → DAS) and spatial (equipment → sampling point →
  process unit → site) — and only converge at campaign. Any single linear "climb" claims the logger
  contains the probe, which is false. A containment visual would need two ladders; not worth it.

### Ticket Q4 (the optional second half) — n/a

Moot: [002](./002-when-does-one-gesture-write-two-rows.md) ruled one gesture = one row.
The dialog has no second half, which is exactly why it fits on one screen.
