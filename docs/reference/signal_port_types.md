# SignalPortType vs ControlVariableType

Two orthogonal enumerations classify every `SignalPort`:

| Attribute | Table | Question answered |
| --- | --- | --- |
| `SignalPortType_ID` | `SignalPortType` | *What kind of data flows here?* |
| `ControlVariableType_ID` | `ControlVariableType` | *What engineering role does this port play?* |

They are independent: a blower speed command has `SignalPortType=Value` and
`ControlVariableType=ManipulatedVariable`.  A raw DO sensor reading has
`SignalPortType=Value` and `ControlVariableType=MeasuredVariable`.  A device
health indicator has `SignalPortType=Status` and `ControlVariableType=NULL`.

---

## SignalPortType

Discriminates primary value ports from the sub-signals that annotate them.

| ID | Name | Description |
| --- | --- | --- |
| 1 | Value | Primary measurement or output value |
| 2 | Status | Device or measurement status flag |
| 3 | Alarm | Alarm or alert indicator |
| 4 | Uncertainty | Measurement uncertainty estimate |

### Sub-signal constraint

Ports with `SignalPortType` of **Status**, **Alarm**, or **Uncertainty** are
sub-signal ports.  They are linked to their parent value port via
`ParentPort_ID` and **cannot be relocated independently** — they inherit their
physical location from the parent.  Attempting to call
`POST /ports/{id}/relocate` on a sub-signal port returns `422`.

See [Sub-Signal Grouping](../architecture/sub_signals.md) for the full
data model, ingest API, and query endpoint.

---

## ControlVariableType

Describes the engineering role of a port within a process-control scheme.
`NULL` means the port is not part of a control loop (most sensor channels).

| ID | Name | Description |
| --- | --- | --- |
| 1 | MeasuredVariable | The variable being controlled or monitored |
| 2 | ManipulatedVariable | The variable adjusted by the controller to affect the process |
| 3 | SetPoint | Target value the controller tries to achieve |
| 4 | Disturbance | Measured input that affects the process but is not manipulated |
| 5 | Computed | Derived or calculated signal within the control scheme |

### Relationship to ControlLoop

When a port is part of a `ControlLoop`, it is registered in `ControlLoopPort`
with the corresponding `ControlLoopPortRole_ID`.  `ControlVariableType_ID` on
the `SignalPort` row itself is the per-port label that persists even when the
port is not actively participating in a loop.

---

## Quick-reference matrix

| Example signal | SignalPortType | ControlVariableType |
| --- | --- | --- |
| TSS concentration (sensor) | Value | MeasuredVariable |
| DO setpoint | Value | SetPoint |
| Blower speed command | Value | ManipulatedVariable |
| Influent flow (disturbance feed-forward) | Value | Disturbance |
| Estimated SRT (model output) | Value | Computed |
| Probe health status code | Status | *(NULL)* |
| High-DO alarm flag | Alarm | *(NULL)* |
| DO measurement uncertainty | Uncertainty | *(NULL)* |
