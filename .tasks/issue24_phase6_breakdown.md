# Plan — Phase 6 (importer + L5X loader) breakdown for Issue #24

## Context

Parent plan: [ok-ok-no-worries-composed-canyon.md](/Users/jeandavidt/.claude/plans/ok-ok-no-worries-composed-canyon.md)
Branch: `issue-24-signal-interface` (v4.0.0)
Phase 6 goal (from parent plan): **"importer + L5X loader: configs and loader command; e2e import test green."**

Phases 3–5 rewrote the backend on `SignalInterface` + `EquipmentWiringHistory` + `EquipmentLocationHistory` + `ChannelPortHistory` + `ChannelRole`. [api/v1/endpoints/channels.py:132-187](api/v1/endpoints/channels.py#L132-L187) now exposes `POST /channels/resolve` with body `{signal_interface_name, tag_name, parameter_name?, data_provenance_id?, processing_degree_id?}`. Ingest endpoints resolve via `signal_interface_repository.find_signal_interface_by_das_and_name()` at [api/v1/endpoints/ingest.py:118-153](api/v1/endpoints/ingest.py#L118-L153) (tagged) and via `find_active_equipment_wiring` at [api/v1/endpoints/ingest.py:217-258](api/v1/endpoints/ingest.py#L217-L258) (tagless). The wire-level field name **`signal_port_type`** is preserved as the server-side name for `ChannelRole` (Value/Status/Alarm/Uncertainty), so the importer does not need to rename it.

The importer is still on the v3 contract:
- [importer/src/table_import/api_client.py:70-96](importer/src/table_import/api_client.py#L70-L96) `resolve_channel()` posts `{das_name, tag, signal_port_type, parent_tag, parameter_name, ...}` — needs an optional `signal_interface_name` field (the server already accepts it on `/channels/resolve`; for `/ingest/resolve-channel` it's inferred from DAS when DAS→SI is 1:1, so the importer just passes it through to the server when present).
- [importer/src/table_import/config.py:262-341](importer/src/table_import/config.py#L262-L341) source-level configs (`TaggedFileConfig`, `TaglessFileConfig`, `TaggedTsdbConfig`, `TaglessTsdbConfig`, `PilEAUteSCADAConfig`, `TaggedVectorFileConfig`, `TaggedImageFolderConfig`, `TaglessImageFolderConfig`, `TaggedMatrixFileConfig`) have `das_name` but no `signal_interface_name`. Per user direction, **config files are written per signal interface** so the field goes on the **root of each source config** (alongside `das_name`), not per-variable.
- [importer/src/table_import/import_script.py](importer/src/table_import/import_script.py) needs to thread `signal_interface_name` from the source config into each `resolve_channel()` call and ingest call.
- [importer/tests/test_e2e_import.py:133-146](importer/tests/test_e2e_import.py#L133-L146) still references `SignalPort*` in teardown SQL — must be rewritten for v4.
- [scripts/parse_l5x.py](scripts/parse_l5x.py) (229 lines) is a pure CSV-writing parser with no HTTP/DB writes. Plan wants it moved to `importer/src/table_import/l5x_loader.py` and extended with a `load_l5x_to_api()` function that creates `SignalInterface` + `SignalInterfacePort` + `Channel` (with `TagName`) + `ChannelPortHistory` rows via the API, with `--dry-run` support. The test fixture `modelEAU_Hedi_Latest260323.L5X` already exists at repo root but is `.gitignore`d — unit tests must use a **synthetic minimal L5X XML** built inline.
- [importer/pyproject.toml:21-22](importer/pyproject.toml#L21-L22) exposes `table-import` entrypoint → [importer/src/table_import/__main__.py:cli()](importer/src/table_import/__main__.py). Today it only accepts `--config <yaml>`. Plan wants two subcommands: `table-import import --config ...` (current behaviour) and `table-import l5x <file> --signal-interface <name> [--dry-run]`.
- No `importer/configs/examples/` directory yet — plan wants three new configs there illustrating the forcing cases (monEAU IQSensor, SC1000-via-PLC, Logix5000-direct).

User direction settled by AskUserQuestion: **config field lives at the root of each source config** (mirrors `das_name`), and **Phase 6 is split into 6A/6B/6C** matching the Phase 5 breakdown house style. Each sub-phase is sized for one focused context window, ends with a `/sc` commit, and has a concrete green-verify command.

**Prereq:** Phase 5 must be green before Phase 6 starts. Remaining Phase 5 items (per [.tasks/issue24_phase5_breakdown.md](.tasks/issue24_phase5_breakdown.md)) are `SignalPort` refs in [tests/schema/test_sensor_status_yaml.py](tests/schema/test_sensor_status_yaml.py) (3 refs), [tests/api/contract/test_ingest_resolve_channel.py](tests/api/contract/test_ingest_resolve_channel.py) (5), [tests/api/contract/test_ingest_tag_mode.py](tests/api/contract/test_ingest_tag_mode.py) (6), [tests/api/contract/test_schema_contracts.py](tests/api/contract/test_schema_contracts.py) (1), [tests/api/contract/test_sub_signal_endpoints.py](tests/api/contract/test_sub_signal_endpoints.py) (1). `tests/app/test_campaign_wizard.py` (5) is Phase 7. Phase 6 assumes the first set is cleaned up.

## Files to modify

### Backend — touched only for verification (no rewrites)
- [api/v1/endpoints/signal_interfaces.py](api/v1/endpoints/signal_interfaces.py), [signal_interface_ports.py](api/v1/endpoints/signal_interface_ports.py), [signal_interface_types.py](api/v1/endpoints/signal_interface_types.py) — confirm `POST` endpoints return the created ID so the L5X loader can chain creates. If missing, minimal add (but expected to exist from Phase 4).

### Importer core
- [importer/src/table_import/api_client.py](importer/src/table_import/api_client.py) — `resolve_channel()` / `ingest_sensor_values()` / `ingest_vector_observations()` / `ingest_image()` all gain an optional `signal_interface_name: str | None = None` kwarg that's included in the POST body only when set. Add four new client methods used by the L5X loader:
  - `create_signal_interface(das_name, name, type_name) -> int`
  - `create_signal_interface_port(signal_interface_id, name, kind_name) -> int`
  - `create_channel(signal_interface_id, tag_name, parameter_name, unit_name, port_id=None, parent_channel_id=None, channel_role="value", ...) -> int`
  - `open_channel_port_history(channel_id, port_id, valid_from, gating_note=None) -> int`
- [importer/src/table_import/config.py](importer/src/table_import/config.py) — add `signal_interface_name: str | None = None` to **every source config class** at the root level: `TaggedFileConfig`, `TaglessFileConfig`, `TaggedTsdbConfig`, `TaglessTsdbConfig`, `PilEAUteSCADAConfig`, `TaggedVectorFileConfig`, `TaggedImageFolderConfig`, `TaglessImageFolderConfig`, `TaggedMatrixFileConfig`. Variables still refer to `tag` / `equipment_name`; SI scope is file-level.
- [importer/src/table_import/import_script.py](importer/src/table_import/import_script.py) — thread `source_config.signal_interface_name` through each `resolve_channel` / ingest call site. No semantic change when the field is absent.

### Importer L5X loader (new)
- **New:** [importer/src/table_import/l5x_loader.py](importer/src/table_import/l5x_loader.py) — moves `parse_modules` / `parse_tags` / `parse_io_mapping` verbatim from `scripts/parse_l5x.py`; adds `plan_l5x_load(root, signal_interface_name) -> LoadPlan` (pure) and `apply_l5x_load(plan, api_client) -> LoadResult` (HTTP writes via the four new client methods). Handles the TresCON mux case: when `io_mapping` has multiple instrument tags on the same `Local:slot:I.ChN`, each becomes a distinct `Channel` with a `ChannelPortHistory` row whose `GatingNote` records the routine/rung that disambiguates them. Unknown-port rows (controller-scope tags with no I/O reference) become channels with `SignalInterfacePort_ID = NULL`.
- **Delete (or thin-wrapper):** [scripts/parse_l5x.py](scripts/parse_l5x.py) — replace its body with `from table_import.l5x_loader import main; main()` so the legacy CLI keeps working, or delete entirely once nothing references it.
- [importer/src/table_import/__main__.py](importer/src/table_import/__main__.py) — restructure `cli()` to use argparse subparsers: `import` (current `--config` flow) and `l5x` (`<file.l5x> --signal-interface <name> [--dry-run] [--api-url <url>]`). Maintain backward compatibility for `table-import --config ...` by defaulting to the `import` subcommand when no subcommand is given (optional).

### Config files
- [importer/configs/spectrolyser_basestation.yaml](importer/configs/spectrolyser_basestation.yaml) — add `signal_interface_name: basestation_spectrolyser` (or appropriate) to the single `vector_file_configs` entry.
- [importer/configs/felinoscope.yaml](importer/configs/felinoscope.yaml) — add `signal_interface_name: felinoscope_camera` to each config entry.
- [docker/import-test-data.yaml](docker/import-test-data.yaml) — add `signal_interface_name` to every source config (rodtox, basestation, felinoscope, scada) so the docker-driven e2e import exercises the new field.
- **New:** [importer/configs/examples/monEAU_iqsensor.yaml](importer/configs/examples/monEAU_iqsensor.yaml) — DAS = `monEAU_box`, SI = `iqsensor_net_bus`; two or three probe channels with tags matching the IQSensor Net naming convention.
- **New:** [importer/configs/examples/sc1000_via_plc.yaml](importer/configs/examples/sc1000_via_plc.yaml) — DAS = `hedi_plc`, SI = `sc1000_ammonium`; channels addressed by the PLC tag name that mirrors the SC1000 port.
- **New:** [importer/configs/examples/logix5000_direct.yaml](importer/configs/examples/logix5000_direct.yaml) — DAS = `hedi_plc`, SI = `hedi_plc` (self, since the PLC IS the interface); tags match Logix5000 controller-scope tag names.

### Tests
- [importer/tests/test_api_client.py](importer/tests/test_api_client.py) — add respx-mocked tests for the four new create methods and for `signal_interface_name` passthrough.
- [importer/tests/test_e2e_import.py](importer/tests/test_e2e_import.py) — rewrite teardown SQL at [lines 133-146](importer/tests/test_e2e_import.py#L133-L146): `SignalPort` → `Channel` + `SignalInterface`. Update fixtures to seed a `SignalInterface` row (or rely on auto-create). Verify `signal_interface_name` is passed through when set.
- **New:** [tests/unit/test_l5x_loader.py](tests/unit/test_l5x_loader.py) — use a synthetic L5X XML string (built inline as a Python constant, ~80 lines covering: 1 chassis module, 2 I/O modules, 3 program-scope tags, 2 controller-scope tags, 2 rungs with MOV instructions including one TresCON-style mux where two tags point at the same port). Test: (a) `parse_modules` / `parse_tags` / `parse_io_mapping` return expected dicts, (b) `plan_l5x_load` produces the right ordered list of creates for the synthetic input (including mux + unknown-port cases), (c) `apply_l5x_load` against a mocked `DateaubaseClient` (respx or pytest-mock) emits the right HTTP calls in order, (d) `--dry-run` prints the plan without issuing HTTP.

### Docs (thin touch)
- [importer/README.md](importer/README.md) — add a **Signal Interface** section explaining `signal_interface_name` config field + short **L5X loader** section showing `uv run table-import l5x modelEAU_Hedi_Latest260323.L5X --signal-interface hedi_plc --dry-run`.

## Reuse (existing helpers)

- Respx mock patterns already used in [importer/tests/test_api_client.py](importer/tests/test_api_client.py) — extend for the 4 new methods, don't reinvent.
- Seed data helpers in [importer/tests/test_e2e_import.py](importer/tests/test_e2e_import.py) teardown block — update to v4 schema, don't write a new fixture file.
- Argparse subparser pattern — straight argparse stdlib, no new deps.
- The existing `ApiError` class and `_post()` / `_get()` helpers in `api_client.py` — the four new create methods reuse them verbatim.

## Sub-phase breakdown

### 6A — Importer plumbing for SignalInterface

**Scope:** thread `signal_interface_name` through config → client → import flow; update existing configs + docker-import; keep `import` flow green.

**Files:**
- [importer/src/table_import/api_client.py](importer/src/table_import/api_client.py) — add optional `signal_interface_name: str | None = None` to `resolve_channel`, `resolve_channel_tagless`, `ingest_sensor_values`, `ingest_sensor_values_tagless`, `ingest_vector_observations`, `ingest_image`. Include in POST body only when set.
- [importer/src/table_import/api_client.py](importer/src/table_import/api_client.py) — add four new HTTP client methods for later use by L5X loader (ship now so 6B doesn't bundle client + loader churn): `create_signal_interface`, `create_signal_interface_port`, `create_channel`, `open_channel_port_history`.
- [importer/src/table_import/config.py](importer/src/table_import/config.py) — add `signal_interface_name: str | None = None` to the 9 source-level config classes enumerated above.
- [importer/src/table_import/import_script.py](importer/src/table_import/import_script.py) — each call to `client.resolve_channel(...)` / `client.ingest_...(...)` gains `signal_interface_name=source_config.signal_interface_name`.
- [importer/configs/spectrolyser_basestation.yaml](importer/configs/spectrolyser_basestation.yaml) + [importer/configs/felinoscope.yaml](importer/configs/felinoscope.yaml) + [docker/import-test-data.yaml](docker/import-test-data.yaml) — add the new field at each source config root.
- [importer/tests/test_api_client.py](importer/tests/test_api_client.py) — add passthrough tests + tests for the 4 new create methods.
- [importer/tests/test_import_script.py](importer/tests/test_import_script.py) — if it asserts POST bodies, update to accept the new field.
- [importer/tests/test_e2e_import.py](importer/tests/test_e2e_import.py) — rewrite teardown SQL [lines 133-146](importer/tests/test_e2e_import.py#L133-L146); no `SignalPort` refs remain after this file.

**Verify:**
```
cd importer && uv run pytest tests/test_api_client.py tests/test_import_script.py -q
uv run pytest importer/tests/test_e2e_import.py -m db -q   # requires docker up
grep -rn "SignalPort\|signal_port\b" importer/            # zero hits outside comments
```
All green; zero `SignalPort` refs in importer.

**Commit:** `feat(importer): thread signal_interface_name through client, config, and ingest flow`

---

### 6B — L5X loader + unit tests + CLI subcommand

**Scope:** move + extend the L5X parser into the importer package, wire a `l5x` subcommand, and prove the happy path + TresCON mux + unknown-port cases with a synthetic XML fixture.

**Files:**
- **New:** [importer/src/table_import/l5x_loader.py](importer/src/table_import/l5x_loader.py) — `parse_modules` / `parse_tags` / `parse_io_mapping` moved verbatim from [scripts/parse_l5x.py](scripts/parse_l5x.py); new `plan_l5x_load(xml_root, signal_interface_name, *, das_name=None) -> LoadPlan` (pure, returns a dataclass of `ports_to_create`, `channels_to_create`, `port_history_to_open`); new `apply_l5x_load(plan, client: DateaubaseClient, *, dry_run: bool) -> LoadResult`. Mux detection: group `io_mapping` rows by `(slot, io_direction, channel)` → if N>1 tags, each tag becomes a Channel and each gets a `ChannelPortHistory` row with `GatingNote = f"{program}/{routine} rung {rung}"`. Unknown-port tags (controller-scope with no I/O ref) become channels with `port_id=None` and no `ChannelPortHistory`.
- [importer/src/table_import/__main__.py](importer/src/table_import/__main__.py) — replace the single-parser `cli()` with an argparse subparser dispatch: `import` (current behaviour, preserving `--config` / `--dry-run` / `--min-timestamp`) and `l5x` (new: positional `<file.l5x>`, `--signal-interface <name>` required, `--das-name <name>` optional, `--api-url <url>` optional, `--dry-run`).
- **Delete:** [scripts/parse_l5x.py](scripts/parse_l5x.py) (or replace body with a 3-line re-export calling `l5x_loader.cli()` for backward compat).
- **New:** [tests/unit/test_l5x_loader.py](tests/unit/test_l5x_loader.py) — synthetic L5X XML fixture as a module-level string constant; tests cover parse functions, `plan_l5x_load` correctness, `apply_l5x_load` mocked with respx, `--dry-run` no-write behaviour, mux and unknown-port scenarios.

**Verify:**
```
uv run pytest tests/unit/test_l5x_loader.py -q
uv run table-import --help                         # shows `import` + `l5x` subcommands
uv run table-import l5x --help                     # shows --signal-interface, --dry-run
uv run table-import l5x ./modelEAU_Hedi_Latest260323.L5X --signal-interface hedi_plc --dry-run
# (last line: local-only sanity check — L5X is gitignored; prints plan, no HTTP)
```
Unit tests green; CLI dispatches correctly; dry-run against the real L5X file prints a non-empty plan including TresCON mux tags.

**Commit:** `feat(importer): L5X loader subcommand with TresCON mux support`

---

### 6C — Example configs + end-to-end import green

**Scope:** author the three example configs the parent plan calls for, prove the full e2e import flow is green against a fresh v4 database, and document both the SignalInterface config field and L5X subcommand.

**Files:**
- **New:** [importer/configs/examples/monEAU_iqsensor.yaml](importer/configs/examples/monEAU_iqsensor.yaml), [sc1000_via_plc.yaml](importer/configs/examples/sc1000_via_plc.yaml), [logix5000_direct.yaml](importer/configs/examples/logix5000_direct.yaml) — each is a minimal but realistic `file_configs` (or `scada_sql_configs`) entry that would load into the seeded DB. All three exercise `signal_interface_name` at the source-config root.
- [importer/README.md](importer/README.md) — add **Signal Interface** and **L5X loader** sections; show `uv run table-import import --config ...` vs `uv run table-import l5x ...` invocations.
- Any seed-data additions needed to make the example configs loadable (parameters, units, equipment) go into [sql/seed_importer_fixtures.sql](sql/seed_importer_fixtures.sql). Keep additions minimal and idempotent.

**Verify (exits Phase 6):**
```
docker compose down -v && docker compose up --build    # fresh boot clean
uv run pytest importer/tests/test_e2e_import.py -m db -q   # all green
uv run pytest tests/unit/test_l5x_loader.py -q            # still green
uv run pytest                                             # full suite green (non-db + db where applicable)
uv run table-import import --config importer/configs/examples/monEAU_iqsensor.yaml --dry-run   # exits 0, prints expected plan
```
All green; three example configs validate against `Config` Pydantic model; docker-driven e2e import populates `SignalInterface`, `Channel`, `Value` rows correctly.

**Commit:** `feat(importer): example configs + e2e green on v4 signal interface`

---

## Phase 6 done criteria

- [ ] 6A–6C all committed via `/sc`.
- [ ] `uv run pytest` 100% green (including `-m db` when Docker is up).
- [ ] Zero `SignalPort` references in `importer/` or `scripts/`.
- [ ] `uv run table-import l5x --help` works; loader round-trips the TresCON mux and unknown-port rows in `tests/unit/test_l5x_loader.py`.
- [ ] Three example configs under `importer/configs/examples/` validate + dry-run cleanly.
- [ ] `importer/tests/test_e2e_import.py` passes against a fresh v4 docker boot.
- [ ] [importer/README.md](importer/README.md) documents `signal_interface_name` and the `l5x` subcommand.

## Execution order

6A → 6B → 6C. 6B depends on the 4 new HTTP client methods shipped in 6A. 6C depends on 6A's config-field plumbing and 6B's loader.

## Risks & mitigations

- **SignalInterface endpoint contracts** (`POST /signal-interfaces`, `/signal-interface-ports`, etc.) were added in Phase 4 but not exercised by the importer yet. If the response payload differs from what 6A's new client methods assume, first integration run will fail. Mitigation: 6A starts by reading the endpoints + schemas in [api/v1/endpoints/signal_interfaces.py](api/v1/endpoints/signal_interfaces.py), [signal_interface_ports.py](api/v1/endpoints/signal_interface_ports.py), [api/v1/schemas/signal_interface.py](api/v1/schemas/signal_interface.py) before writing the client methods — no guessing.
- **TresCON mux semantics** — `GatingNote` field is the disambiguator; exact content is a judgment call. Mitigation: use `f"{program}/{routine} rung {rung}"` as the loader's default and document it. Tests assert the format so future changes are caught.
- **L5X gitignore** — `modelEAU_Hedi_Latest260323.L5X` is gitignored so CI cannot run end-to-end against it. Mitigation: unit tests use a synthetic XML fixture inline; real-L5X dry-run is a local manual verification step only.
- **Config field placement change vs parent plan text** — parent plan said `FileStructure gains optional signal_interface_name`, but user direction placed it at the source-config root. Mitigation: the change is captured explicitly in this plan's Context + 6A files; no ambiguity for the executor.
- **Phase 5 not fully closed when 6A starts** — remaining `SignalPort` refs in schema/contract tests (5A) are pre-Phase 6 work. 6A should not merge until `uv run pytest tests/unit tests/schema tests/api/contract` is green.

## Out of scope for Phase 6

- App (Streamlit) changes → Phase 7.
- Docs regeneration (ERD, architecture, ops SOPs) → Phase 8.
- Final `mkdocs build` / PR assembly → Phase 9.
- Any `Value*` payload changes or tagless-ingest semantic shifts.
