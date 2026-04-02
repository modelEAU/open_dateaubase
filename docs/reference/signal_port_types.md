# SignalPortType

Discriminates primary value ports from the sub-signals that annotate them.

| ID | Name | Description |
| --- | --- | --- |
| 1 | Value | Primary measurement or output value |
| 2 | Status | Device or measurement status flag |
| 3 | Alarm | Alarm or alert indicator |
| 4 | Uncertainty | Measurement uncertainty estimate |

## Sub-signal constraint

Ports with `SignalPortType` of **Status**, **Alarm**, or **Uncertainty** are
sub-signal ports.  They are linked to their parent value port via
`ParentPort_ID` and **cannot be relocated independently** — they inherit their
physical location from the parent.  Attempting to call
`POST /ports/{id}/relocate` on a sub-signal port returns `422`.

See [Sub-Signal Grouping](../architecture/sub_signals.md) for the full
data model, ingest API, and query endpoint.

---

## Quick-reference examples

| Example signal | SignalPortType |
| --- | --- |
| TSS concentration (sensor) | Value |
| Blower speed command | Value |
| DO setpoint | Value |
| Influent flow (feed-forward input) | Value |
| Probe health status code | Status |
| High-DO alarm flag | Alarm |
| DO measurement uncertainty | Uncertainty |
