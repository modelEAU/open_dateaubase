# Control Loop Modelling

## Overview

A **control loop** is a feedback mechanism that reads a measured process variable and
adjusts a manipulated variable to track a setpoint.  The schema separates two concerns:

| Concept | Table | What it captures |
|---|---|---|
| Loop topology | `ControlLoop` + `ControlLoopPort` | Which signal ports play which roles, which controller type is used, and how loops fall back to one another |
| Tuning history | `ControlLoopApplication` | The parameter snapshots in effect over each time window |

---

## ControlLoop vs ControlLoopApplication

### ControlLoop — sparse topology record

`ControlLoop` is created once and rarely updated.  It records:

- **Name** — human-readable identifier.
- **ControllerType** — one of `PID`, `PI`, `P`, `BangBang`, `Custom`, or `Manual`.
- **AlgorithmReference** — file path or repository URL for `Custom` controllers.
- **FallbackControlLoop_ID** — self-referencing FK that builds fallback chains.
- Ports via `ControlLoopPort` (see below).

### ControlLoopApplication — dense tuning history

Every time a loop is tuned, a new `ControlLoopApplication` row is inserted.  The schema
enforces **at most one active row per loop** using a filtered unique index on
`(ControlLoop_ID) WHERE EndTime IS NULL`.

A single `ControlLoopApplication` row captures:

- **StartTime / EndTime** — the time window during which these parameters were in effect.
- **Parameters** — a free-form JSON blob.  Examples:

  ```json
  // PID
  { "Kp": 1.2, "Ki": 0.05, "Kd": 0.0 }

  // MPC
  { "prediction_horizon": 10, "control_horizon": 3, "weights": { "Q": 1.0, "R": 0.1 } }

  // Bang-bang
  { "hysteresis_band": 0.5 }
  ```

- **AppliedByPerson_ID** — optional reference to the operator who performed the tuning.
- **Notes** — free-text context for the tuning event.

> **Dynamic, per-interval setpoints** (e.g. a time-varying reference trajectory) belong
> in Channel observations — not in `ControlLoopApplication`.  Application rows capture
> the *controller configuration*, not the instantaneous reference value.

### Recording a tuning event

Use the `/retune` endpoint (or `control_loop_repository.retune()`):

1. The active Application's `EndTime` is set to `start_time` of the new tuning.
2. A new Application row is inserted with `EndTime = NULL`.

Old tuning rows are **never deleted** — the full history is preserved and queryable.

---

## ControlLoopPort and roles

`ControlLoopPort` links a `SignalPort` to a `ControlLoop` with an explicit role from
`ControlLoopPortRole`.  A unique constraint prevents the same `SignalPort` from appearing
twice on the same loop.

| Role | Meaning |
|---|---|
| MeasuredVariable | The controlled or observed process variable |
| ManipulatedVariable | The actuator or output adjusted by the controller |
| SetPoint | Target value supplied to the controller |
| Disturbance | Measured input that affects the process; not manipulated |
| PredictedOutput | Model-predicted value of the controlled variable |
| Other | Escape hatch for novel roles |

---

## Cascade architecture

A `ManipulatedVariable` port on an **outer** loop can be the `SetPoint` port on an
**inner** loop by referencing the same `SignalPort_ID` with different roles in each loop.

```
Outer loop (DO controller)
  MeasuredVariable  → DO_sensor port
  ManipulatedVariable → aeration_setpoint port  ◄──┐
                                                     │ same SignalPort_ID
Inner loop (aeration controller)                     │
  SetPoint          → aeration_setpoint port  ───────┘
  MeasuredVariable  → aeration_flow_sensor port
  ManipulatedVariable → blower_command port
```

The topology is fully represented by the `ControlLoopPort` rows.  No special "cascade"
flag is needed — cascade emerges from the shared `SignalPort_ID`.

---

## Fallback chain

`ControlLoop.FallbackControlLoop_ID` is a self-referencing FK.  Chains can be traversed
end-to-end with `GET /control-loops/{loop_id}/fallback-chain`:

```
PID loop  →  PI loop  →  Manual loop  →  NULL
```

Fallback semantics are application-defined — the database records the chain topology but
does not automatically activate the fallback.

---

## Deactivating a cascade loop

Closing (setting `EndTime` on) a loop's active Application affects **only that loop**.
The inner loop's Application remains open and unaffected.  This is by design: each loop's
tuning history is independent.

---

## API endpoints

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/api/v1/control-loops` | Create a loop |
| `GET` | `/api/v1/control-loops/{loop_id}` | Get loop details |
| `GET` | `/api/v1/control-loops/{loop_id}/ports` | List ports on a loop |
| `POST` | `/api/v1/control-loops/{loop_id}/ports` | Add a port to a loop |
| `POST` | `/api/v1/control-loops/{loop_id}/applications` | Open first Application |
| `POST` | `/api/v1/control-loops/{loop_id}/retune` | Record a tuning event |
| `GET` | `/api/v1/control-loops/{loop_id}/active-application` | Current active Application |
| `GET` | `/api/v1/control-loops/{loop_id}/application-at?at=<datetime>` | Point-in-time Application |
| `GET` | `/api/v1/control-loops/{loop_id}/fallback-chain` | Full fallback chain |
