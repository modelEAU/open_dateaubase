# When does one gesture write two rows?

- **Parent:** [Map: Recording](../map.md)
- **Label:** `wayfinder:grilling`
- **Blocked by:** —
- **Assignee:** _unclaimed_
- **Status:** closed — **out of scope**

## Question

`Annotation.Event_ID` exists precisely to say *"this data is suspect **because** that happened"* —
the causal join. Neither of today's UIs can write both halves. The Recording gesture should
be able to.

Settle the rules:

1. After a user records an `Event` (say `Cleaning` on an Equipment), when is the data-quality
   follow-up **offered**? Always? Only for kinds that plausibly taint data? Only when the user
   is standing on a chart with a brushed range?
2. The user said such a question would not be annoying, but that *what* they want to record
   "changes with context." So the follow-up is **offered, never forced**. What is the default —
   pre-checked or unchecked? Skipping it must be one click.
3. If accepted, what does the second row inherit — time range, author, a derived
   `AnnotationKind`? Is the range the same as the Event's, or does the user re-brush?
4. Which `Stream`(s) does the annotation land on? An Equipment can feed several Channels. All of
   them, the one plotted, or the user picks?
5. Does the reverse direction exist — recording an `Anomaly` on data, then saying "and here's the
   Event that caused it," creating the `Event` from the annotation side?
6. Failure semantics: the two writes hit two endpoints. If the annotation POST fails after the
   event POST succeeded, what does the user see? (Not a transaction today.)

**Output:** the decision rules, written down. No code.

## Ruled out of scope

Deferred by decision in
[Which levels can each Kind apply to?](001-which-levels-can-each-kind-apply-to.md): **one
recording writes one row.** A "we were calibrating, so this window is dodgy" recording is simply
an `Event` today. If users raise the need, the two-step is wired up then — as a fresh effort.

`Annotation.Event_ID` is unaffected and still carries the causal join; what's deferred is only
the *gesture* that writes both halves at once. All six questions above (offer rules, defaults,
inheritance, which Stream, reverse direction, failure semantics) go with it — none of them is
answerable cheaply, and none of them blocks the destination.
