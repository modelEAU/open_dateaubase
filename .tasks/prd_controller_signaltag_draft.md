# [DRAFT PRD] `SignalInterface` as first-class entity + rename `Channel` → `SignalTag`

> **Status: DRAFT — open for comment.** Revised after feedback:
> (1) no legacy compatibility path — redesign as if this had been correct
> from the start; (2) `Controller` renamed to `SignalInterface` to avoid
> collision with control-loop concepts (PID, etc.); (3) physical port is
> *optional* — tracing wires in the plant is not a prerequisite for
> using the system; (4) the existing `Channel` table plays the role of
> "named logical data stream," but `SignalTag` is a clearer name and the
> PRD now includes that rename as part of the redesign.
> Sections marked with `❓` are the most uncertain.

## Problem Statement

As a data admin (and as a student user) of open_datEAUbase, I can't
currently express where my data actually comes from without distorting
the physical reality. The schema treats
`(Equipment, SignalPort, DataAcquisitionSystem)` as the source triple
behind `Channel`, but in every real deployment there is a
**signal-interface device** sitting between the sensing equipment and
the DAS:

- monEAU box: `Sensor → IQSensor interface → monEAU DAS`
- Hach/Rockwell: `DO sensor → SC1000 → PLC → DAS`, with the PLC
  introducing a tag naming scheme the sensor doesn't own
- Logix5000 (modelEAU): a `1769-IF8` analog-input card demuxes one
  physical channel (e.g. `Local:7:I.Ch2Data`) into *multiple* named
  instrument streams (`AIT_271`, `AIT_371`) based on a valve (TresCON
  multi-reactor sampler)

The current model forces these middle hops to disappear into either
Equipment or DAS, which:

1. Confuses users about what entity to change when the physical plant
   changes.
2. Makes tag-based addressing (PLC tags, SCADA TagIndex, Modbus
   registers) feel like a second-class concept even though it's how
   most real systems identify signals.
3. Has no way to model one physical port sourcing multiple logical
   streams over time (the TresCON mux case).
4. Leaves students without a natural "all sensors on my interface"
   grouping, which is how they actually reason about their experiments.
5. Forces users to know the physical port at entry time, even when
   the port mapping is not traceable without a physical site visit.

Separately, the current table name **`Channel`** overloads a word that
has other meanings (analog-input channel on a PLC card, RF/audio
channel, etc.). "SignalTag" more directly names what the row actually
is: a named logical data stream carrying a tag that matches what the
PLC/SCADA/interface calls it.

## Solution

Redesign the provenance chain from scratch — **no legacy fallback**.

- Introduce **`SignalInterface`** as a first-class entity between
  `Equipment` and `DataAcquisitionSystem`. Every signal flows through
  one; what used to look like a "direct monEAU sensor" is now
  explicitly modeled as
  `Sensor → IQSensor_SignalInterface → monEAU_DAS`.
- **Rename `Channel` → `SignalTag`.** The existing `Channel` table is
  the named logical data stream — it already carries `Parameter_ID`,
  `DataProvenance_ID`, `ValueType_ID`, and today links to `Equipment`.
  The rename makes this role explicit in the vocabulary of the
  project and eliminates the "channel" overload.
- On the renamed `SignalTag`: anchor identity to a `SignalInterface`
  (and an optional `SignalInterfacePort`) instead of to an
  `Equipment` + `SignalPort` pair. Add a `TagName` column so the
  controller-assigned tag name is first-class on the row.
- Make **`SignalInterfacePort`** optional on both `Equipment` and
  `SignalTag`. If the admin doesn't know which slot/channel a sensor
  is wired to, they record the equipment and the tag and leave the
  port blank; they can backfill later by tracing the wire.
- **`Observation`** and **`Value`/`ValueVector`/`ValueMatrix`/image**
  tables are **unchanged in shape**. They continue to reference the
  renamed hub (`SignalTag_ID` replacing `Channel_ID`); payload
  columns are untouched.

### Naming

`Controller` is rejected because the codebase already uses "controller"
for control loops (PID, SCADA control strategies). Shortlist for the
replacement `❓` — pick one before implementation:

- **`SignalInterface`** *(current working name)* — descriptive, neutral,
  doesn't collide with existing terms.
- **`DataConcentrator`** — industry-standard term for this function
  (ISA/IEC); very accurate but slightly jargon-heavy.
- **`IOStation`** — automation-native, concise; slightly narrower
  (implies rack-style I/O).
- **`AcquisitionInterface`** — long but crystal clear.

This PRD uses `SignalInterface` throughout; it's a find-and-replace
away from any alternative.

### Core chain

`DataAcquisitionSystem → SignalInterface → SignalTag → Observation → Value`

with **optional** annotations on the source side:

- `Equipment ↔ SignalInterfacePort` (history) — which sensor is wired
  to which port over time. Port can be unknown.
- `SignalTag ↔ SignalInterfacePort` (history) — which port a tag is
  sourced from, with a free-text gating note for mux documentation.
  Port can be unknown.

### Required vs. optional at ingest time

- **Required on `SignalTag`**: `SignalInterface_ID`, `TagName`,
  `Parameter_ID`.
- **Strongly recommended on `SignalTag`**: linkage to `Equipment`
  (via the history join, possibly with a "current equipment"
  convenience view).
- **Optional**: `SignalInterfacePort_ID` — only populated when the
  admin has traced the wire. Blank is a valid, supported state.

This directly answers "is wire-tracing required?" — **no**. You can
run the whole system with every port left blank.

## User Stories

1. As a data admin, I want to register a `SignalInterface` (PLC,
   SC1000, IQSensor) with its make/model/serial, so I can represent
   my physical topology accurately.
2. As a data admin, I want to attach a `SignalInterface` to a
   `DataAcquisitionSystem`, so the DAS knows which interfaces feed it.
3. As a data admin, I want to define the ports on a SignalInterface
   *when I know them*, so I can record slot/channel for traced wires.
4. As a data admin, I want to leave `SignalInterfacePort` blank on
   equipment and tags I haven't traced yet, so I don't have to block
   data entry on a site visit.
5. As a data admin, I want to later backfill port assignments as I
   trace wires, without invalidating any existing observations.
6. As a data admin, I want to record which `Equipment` is associated
   with which `SignalInterfacePort` over time, so re-wiring does not
   erase history.
7. As a data admin, I want each `SignalTag` to carry the tag name
   used by its owning interface (e.g. `AIT_271`, `DO_AerationTank1`),
   so the names used by the PLC/SCADA are first-class in the
   database.
8. As a data admin, I want to optionally link each `SignalTag` to the
   `SignalInterfacePort` it is sourced from (with a free-text gating
   note for mux cases), so I can document physical origin when known.
9. As a data admin, I want to bulk-import `SignalTag` entries from a
   Logix5000 L5X export or a CSV from SCADA/OPC UA, so I don't
   hand-enter hundreds of tags.
10. As a data admin, I want to associate one `Equipment` with multiple
    `SignalTag`s (e.g. TresCON → `AIT_271` and `AIT_371`), so I can
    model analyzers that produce several logical streams.
11. As a student, I want to browse all sensors on one SignalInterface
    in one place, so I can set up a campaign without listing each
    sensor individually.
12. As a student, I want to select a `SignalTag` as the source of a
    measurement in my campaign, so the resulting observations have
    clear provenance.
13. As a student, I want the SignalInterface / DAS chain to be shown
    from the `SignalTag` I pick, so I don't fill in every level.
14. As a student, I want to be told if the `SignalTag` I picked has
    changed physical port or parent equipment since my campaign
    started, so I can verify the data is still the signal I expect.
15. As an importer author (YAML config), I want to reference a
    `SignalTag` by its `(signal_interface_name, tag_name)` pair, so
    I don't have to type the DAS and equipment IDs explicitly — they
    are implied by the interface.
16. As an API consumer, I want `/signal-interfaces`,
    `/signal-interfaces/{id}/ports`,
    `/signal-interfaces/{id}/signal-tags` endpoints.
17. As an API consumer, I want `/signal-tags/{id}/observations` to
    return the time series, so the tag is the primary query axis
    (replaces today's `/channels/{id}/observations`).
18. As a domain modeler, I want the schema to allow multiple
    `SignalTag`s to reference the same `SignalInterfacePort`
    (time-multiplexing), so the TresCON case is representable.
19. As a domain modeler, I want the schema to allow a `SignalTag` to
    have *no* `SignalInterfacePort`, so unknown/un-traced wiring is
    representable without workarounds.
20. As a docs reader, I want a dictionary (YAML) entry for every new
    table / renamed table / modified column, so the schema stays
    discoverable.
21. As a project maintainer, I want the dictionary (YAML) to be the
    source of truth of my data model, from which I can generate a
    fully compliant schema and reference from scratch.
22. As a project maintainer, I want the migration to be a single
    clean redesign (no legacy compat columns, no `Channel` alias
    view), so the resulting schema looks as if it had been correct
    from v1.

## Implementation Decisions

### Schema — full redesign (no dual-write, no legacy columns)

- **New table `SignalInterface`** — identity of an interface device.
  Key fields: name (unique within DAS), SignalInterfaceType FK
  (vocab: PLC, SCADA, SC1000, IQSensor, monEAU-Interface, Other),
  make, model, serial, DAS FK (required). No cascading parent
  interface for now (see Out of Scope).
- **New vocabulary table `SignalInterfaceType`**.
- **New table `SignalInterfacePort`** — optional physical termination
  point on a SignalInterface. Key fields: SignalInterface FK, port
  identifier (e.g. `6/Ch0`), port-kind vocab (analog-in/out,
  discrete-in/out, serial, network), description.
- **Rename `Channel` → `SignalTag`**:
  - Table `Channel` → `SignalTag`.
  - Primary key `Channel_ID` → `SignalTag_ID`.
  - All FK columns named `Channel_ID` (on `Observation`,
    `ValueVector`, `ValueMatrix`, image tables, `ChannelAxis`,
    `ProcessingLineage`, `Annotation`, `DatasetChannel`, any
    self-reference like `StatusChannel_ID`) → `SignalTag_ID` /
    `StatusSignalTag_ID` / etc.
  - Supporting tables renamed: `ChannelAxis` → `SignalTagAxis`,
    `DatasetChannel` → `DatasetSignalTag`. `❓` confirm naming for
    these.
  - Add `SignalInterface_ID` (required FK) to `SignalTag`.
  - Add `SignalInterfacePort_ID` (optional FK) to `SignalTag`.
  - Add `TagName` column to `SignalTag` (unique within
    SignalInterface).
  - Re-evaluate the existing `Equipment_ID` FK on `SignalTag`: keep
    it as a direct FK (convenience), *or* remove it in favor of the
    history-table association only. `❓`
- **New history table `EquipmentSignalInterfacePortHistory`** — binds
  Equipment to a *port* with a validity window. Port FK is nullable
  (an equipment can be "plugged into the interface without a known
  port"); in that case the history row binds equipment directly to
  SignalInterface.
- **New history table `SignalTagSignalInterfacePortHistory`** —
  optional, many-to-many, time-varying. Port FK nullable. Free-text
  `gating_note` for mux documentation.
- **`Observation`, `Value`, `ValueVector`, `ValueMatrix`, image
  tables** — shape unchanged. Their FKs to the old `Channel_ID` are
  renamed to `SignalTag_ID`; payload columns are untouched.
- **Drop** `SignalPort` and `SignalPortEquipmentHistory` in their
  current form; the replacements above fully supersede them.

### Dictionary-first authoring

Per user story 21, every new / renamed / modified table or column is
authored as a YAML dictionary entry first, and the SQL is generated
from it. The migration PR must include:

- Dictionary YAML for every new and renamed table, every new column
  on `SignalTag`, and every dropped object.
- Updated `generate_yaml_tables.py` / `generate_from_yaml.py` output.
- A regeneration check in CI (or at least documented in the PR body).

### API

- CRUD endpoints for `SignalInterface`, `SignalInterfacePort`,
  `SignalInterfaceType`.
- `Channel` CRUD and all `/channels/...` paths renamed to
  `/signal-tags/...`, reflecting the table rename and the new FKs /
  `TagName` column.
- Traversal: `/signal-interfaces/{id}/ports`,
  `/signal-interfaces/{id}/signal-tags`,
  `/signal-tags/{id}/current-equipment`,
  `/signal-tags/{id}/current-port` (may return null).
- Ingest endpoints accept *only* `signal_tag_id` or
  `(signal_interface_name, tag_name)` as provenance. No equipment/port
  shortcut.
- Resolver: `POST /signal-tags/resolve` — given
  `(signal_interface_name, tag_name)` returns canonical ID, with
  optional `create_missing=true`.

### Importer (table_import)

- `FileStructure` carries `tag_name_column` or `default_tag_name`, in
  combination with a `signal_interface_name` field (per-file or
  per-row). Equipment/port fields removed from provenance; any
  remaining use is cosmetic or for downstream linking.
- Existing configs that reference `channel`, `channel_id`, or
  `channel_name` are rewritten to `signal_tag` / `tag_name`. No
  compatibility shim.
- New example config in `importer/configs/` for each forcing case:
  monEAU/IQSensor, SC1000 via PLC, Logix5000 direct.

### App pages

- New admin pages under a **Signal Sources** nav group:
  **SignalInterfaces**, **SignalInterfacePorts**,
  **SignalInterfaceTypes**.
- `Channel` admin page is renamed to **SignalTags** and gains the new
  `SignalInterface`, port, and `TagName` fields. Port is *soft* —
  clearly labeled "optional; fill when wire traced."
- Navigation, page titles, breadcrumbs, and any user-facing strings
  referring to "Channel" are updated to "Signal tag."
- Campaign builder: pick a `SignalTag`; downstream interface / DAS
  shown as read-only context; port shown as "(unknown)" when blank.

### L5X / external import tooling

- Productionize `scripts/parse_l5x.py` output → a seed loader that
  creates `SignalInterface`, `SignalInterfacePort`, `SignalTag`, and
  `SignalTagSignalInterfacePortHistory` rows.
- `❓` location: `scripts/` one-shot vs. `importer/` command.

### Migration strategy

- Test data is synthetic → clean rebuild, no dual-write phase.
- Single migration file: `migrations/v4.0.0_signal_interface.sql`
  (bumped to v4 because this is a breaking schema redesign including
  a table rename), plus rollback, plus full dictionary YAML entries.
- `sql/init.sql` updated to include it in order.
- Seed data regenerated to use the new chain and new table/column
  names.

## Testing Decisions

Good tests exercise *external behavior* — API contracts, ingest
outcomes, page renders — not internal helpers.

**Target surfaces:**

- **Contract tests** for the new / modified Pydantic schemas and
  request/response shapes. Mirror `tests/api/contract/`.
- **Integration tests (`-m db`)** for:
  - Create SignalInterface + SignalTag and ingest an observation — no
    port, no equipment — verify the value lands.
  - Same, with a port + equipment linked — verify traversal API
    returns them.
  - TresCON multiplexer: two SignalTags linked to the same
    SignalInterfacePort with distinct gating notes, ingest routes
    each correctly.
  - Backfill a previously-blank port and verify existing observations
    still resolve cleanly.
- **Unit tests** for the L5X parser — given a fixture L5X, verify
  module list and MOV-extraction output.
- **UI smoke tests (manual, documented)** — admin creates interface +
  tags, student runs a campaign, screenshot evidence in PR.

**Prior art:**

- `tests/integration/test_ingest.py`
- `tests/api/contract/`
- `importer/tests/`

## Out of Scope

- **Cascading interfaces** (Interface → Interface → DAS). Allowed by
  a nullable parent FK if we add it, but not wired into UI/API.
- **Structured gating logic.** The TresCON valve decision stays in
  the PLC. We store the valve tag name as a free-text note on the
  tag↔port history row.
- **Interface-type-specific addressing schemas** (JSON schema per
  interface type). Tag name is free-text unique-within-interface.
- **Continuous L5X/OPC UA sync.** One-shot seed loader only.
- **Re-modeling `DataAcquisitionSystem`** itself.
- **Changes to `Observation` / `Value*` / payload table shape.** This
  PRD renames their FK column from `Channel_ID` to `SignalTag_ID` but
  does not touch payload columns or indexing beyond that rename.
- **Backwards-compatibility `Channel` view or alias.** Explicitly
  rejected: clean rename, consumers update.

## Further Notes

- The modelEAU L5X export (`modelEAU_Hedi_Latest260323.L5X`) and the
  parser in `scripts/parse_l5x.py` are the forcing examples — any
  design that cannot represent the ~20-row I/O mapping *including the
  TresCON mux and unknown-port cases* is rejected.
- The "interface as a kind of Equipment (self-referential)"
  alternative is declined: interfaces don't sense, and conflating
  them with sensors re-creates the muddle this PRD eliminates.
- Naming: `TagName` column on `SignalTag` — the column holds the
  interface-assigned tag string (e.g. `AIT_271`). `❓` confirm.
- Dictionary YAML is treated as the source of truth (per user story
  21) — SQL is generated, not hand-written.

### Open questions to resolve before implementation

1. Final name for the new middle entity: `SignalInterface` /
   `DataConcentrator` / `IOStation` / `AcquisitionInterface`?
2. `SignalTag.Equipment_ID` — keep as direct FK or remove in favor of
   the history join only?
3. Version bump: v4.0.0 (breaking, matches "clean rewrite + rename"
   spirit) or v3.2.0?
4. Does the L5X seed loader live in `scripts/` or become a proper
   `importer/` command?
5. Is a SignalInterface *required* to have a DAS at creation time, or
   can it be parented later? (Affects admin UX — create-order.)
6. Do we keep `SignalInterfacePort` rows even when unknown, or create
   them lazily only when known? (Affects history-row shape.)
7. Renamed supporting tables: `ChannelAxis` → `SignalTagAxis`,
   `DatasetChannel` → `DatasetSignalTag` — confirm, or pick different
   names?
