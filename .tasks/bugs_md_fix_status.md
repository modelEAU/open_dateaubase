# bugs/bugs.md fix — status (PAUSED, nothing committed)

Branch: `issue-24-signal-interface`. Per user: **do not commit**; everything left uncommitted.

## Baseline trajectory (real measurements this session)

| Checkpoint                | Failed | Collection errors | Notes                                                |
|---------------------------|--------|-------------------|------------------------------------------------------|
| Original baseline         | 45     | 9                 | Pre-existing mid-refactor WIP                        |
| After Wave A              | 45     | 9                 | Zero new regressions; foundational fixes in place    |
| After Wave 0              | 38 (+23 errors revealed) | 1 (only `test_sub_signal_grouping`, deferred to F2) | 7 stale failures flipped; 23 wizard tests previously hidden by collection error now visible |
| After Wave B              | 38     | 0 (excl. F2)      | 23 wizard tests flipped GREEN + 2 new BUG-3/4 regression tests; 0 new regressions |
| After Wave C              | 38     | 0                 | +3 new unit tests for `open_location_for_campaign`; 0 new regressions |
| After Wave D              | 38     | 0                 | +7 new unit tests for lab observation helpers (345 → 352 passed); 0 new regressions. Remaining 38 still cluster in Wave F2 surface. |
| After Wave E1             | 38     | 0                 | New `kind_select` component + description plumbed through 3 lookups (`data_provenance_kind`×2, `equipment_event_kinds`) and `_normalize_options` → `render_form_field`; 0 new regressions. |
| After Wave E2             | 38     | 0                 | New `render_wizard_result` helper + terminal "Summary" step added to 5 wizards (site, field_system, campaign_wizard_page, components/campaign_wizard, equipment_move ×2 flows); `nav()` gained `next_label`; `_execute_creates` returns `(created, errors)`. All 25 campaign-wizard tests still pass. |
| After Wave E3             | 38     | 0                 | Extracted scalar/vector/matrix/image tab bodies (~1500 lines) into `app/components/ingest_shapes.py` as 4 parameterized blocks (`key_prefix`/`lookups`/`submit_fn`/`context`). `sensor_ingest.py` shrunk to 130 lines as a thin caller. F3 will reuse these with `context="lab"`. **Caveat:** no automated UI test coverage exists; behavior parity verified only by import + ast-parse. Manual streamlit verification still recommended before relying on this in production. |
| After Wave F1             | 38     | 0                 | New `app/components/geo_utils.py` (`ALLOWED_GEOM_TYPES`, `validate_geojson`, `geojson_area_ha`, `maybe_prefill_area`). Consolidated duplicated validation from `site_wizard.py` + `watersheds.py`. Surface-area widget in both pages prefills from uploaded GeoJSON (geodesic via `pyproj.Geod`); sentinel-keyed so manual edits aren't clobbered. Added `shapely>=2.0` + `pyproj>=3.6` to `[project.optional-dependencies].app`. |
| After Wave F2a            | 0      | 0                 | **Verification gate met (38 → 0).** Pure test-side fix: aligned 5 contract test files with the now-merged WIP refactor in production code. `test_signal_interface_endpoints.py` — dropped 4 obsolete `TestListSignalInterfaceTypes`/`TestCreate*`/`TestUpdate*`/`TestDelete*` classes (7 tests, the underlying `signal_interface_kinds` module + `SignalInterfaceKind`/`SignalInterfacePortKind` tables were removed); fixed `_INTERFACE_ROW` (`Make` → `Manufacturer`, dropped `SignalInterfaceKind_ID` + `signal_interface_kind_name`); fixed `_PORT_ROW` (dropped `SignalInterfacePortKind_ID` + `signal_interface_port_kind_name`); fixed `_CHANNEL_ROW` (dropped `processing_kind_*`, added `produced_by_step_id`); dropped `signal_interface_kind_id` + `signal_interface_port_kind_id` from POST bodies. Other 4 files — dropped stale `patch(... .find_signal_interface_type_by_name ...)` mocks (the production endpoint never references that function; the WIP rename was actually a REMOVAL, not a rename to `_kind_`). |
| After Wave F3 (ENH-2)     | 0      | 0                 | **All 12 bugs/bugs.md items complete.** New `POST /ingest/lab-image` multipart endpoint (accepts 1..N image files = replicates); `value_repository.insert_lab_image_value()` creates Observation (Channel_ID=NULL, LabAnalysis_ID set) + ValueImage; `app/api_client.py::ingest_lab_image()`; `app/pages/lab_ingest.py` rewritten with Scalar/Vector/Matrix/Image tabs using new LabIngestRequest schema. ENH-1 + BUG-6 confirmed done in Wave E3 (status file was stale). 389 passed, 0 failed. |

## DONE & VERIFIED — Wave A, Wave 0, Wave B, Wave C, Wave D (all uncommitted)

### Wave A (foundational + label rename)

- **BUG-2** Equipment Change Location 500 — *root cause fixed*. `tools/schema_migrate/render.py::_render_create_index` had no filtered-index support, so the 4 temporal active-row UNIQUE indexes (`EquipmentLocationHistory`, `EquipmentWiringHistory`, `DASLocationHistory`, `ChannelPortHistory`) generated WITHOUT `WHERE [ValidTo] IS NULL`. Equipment could hold one history row ever → 2nd relocate → uncaught → 500. Added `filter:` support + applied to 4 YAMLs + regenerated DDL (`uv run mkdocs build` from repo root). Verified `sql_generation_scripts/v4.1.0_create_mssql.sql` lines ~695/703/712/717 now end `WHERE [ValidTo] IS NULL;`. Broadened `api/v1/endpoints/equipment_move.py` rewire (~L103) & relocate (~L210) handlers `pyodbc.IntegrityError` → `pyodbc.Error` with SQLSTATE 23000→409 else→422. New tests in `tools/schema_migrate/tests/test_render.py::TestRenderCreateIndexFilter` (3 cases). **NOTE:** this is also Wave 1.1 / Decision #13 of `plan_lab_observation_model.md` — that prerequisite for Wave D is now satisfied.
- **BUG-1** Change Wiring `KeyError: 'label'` — `app/pages/equipment_move.py:380` mapped `s["label"]`; `list_signal_interfaces_lookup()` returns `{signal_interface_id, name, das_name}`. Fixed to `f'{s["das_name"]} › {s["name"]}'`.
- **ENH-4** Process Unit "Tag" → "P&ID Tag" — UI label change only at 5 sites (`process_units.py` L83/L165, `site_wizard.py` L206/L311, `components/campaign_wizard.py` L553). DB column `tag` unchanged.

### Wave 0 (pre-existing failure triage)

- **0.1** `pyproject.toml [tool.pytest.ini_options] norecursedirs = ["importer", ".git", ".venv", ".claude", "build", "dist", "site"]` — workspace member with own deps no longer collected by root pytest; stale `.claude/worktrees/` test files no longer collected.
- **0.2** Removed stale `sys.modules.setdefault("streamlit", ModuleType("streamlit"))` stub at top of `tests/app/test_api_client.py` (lines 11-17) that shadowed the real streamlit package for the rest of the pytest session. The one usage (`_st.session_state["access_token"] = None`) was rewritten to patch `app.api_client.st` to a localized `MagicMock`, leaving the real streamlit package untouched in `sys.modules`. This unblocked `tests/app/test_campaign_wizard.py` collection.
- **0.3** Stale `tests/api/contract/test_control_loop_endpoints.py` rewritten for the `Type → Kind` rename: `_LOOP_ROW` and `_MANUAL_ROW` now use `ControllerKind_ID` (int) + `controller_kind_name` (lowercase alias); POST bodies use `controller_kind_id`; assertions read `data["controller_kind_id"]` / `data["controller_kind_name"]`; `test_invalid_controller_type_rejected` → `test_invalid_controller_kind_id_rejected` (Pydantic int-type validation still triggers 422). 4 of 4 control-loop tests now pass (19 of 19 in the file).
- **0.4** Deleted the stale `TestSignalInterfacePortKindSchema` class from `tests/schema/test_sensor_status_yaml.py` (3 tests). User confirmed the `SignalInterfacePortKind` table was removed completely. 10 of 10 sensor-status YAML tests now pass.

### Wave B (campaign wizard state propagation)

- **BUG-3** Campaign payload missing `site_id` — `wiz_s1_site_label` dropped by Streamlit after step 1. Fix in `app/components/campaign_wizard.py`: added `_sync_site_label` / `_sync_site_name` on_change callbacks in `_step_site` writing `wiz_s1_site_label_store` / `wiz_s1_site_name_store`; `_execute_creates` now reads the store keys first and falls back to widget keys. Added explicit guard: if `campaign_site_id is None` for "Use existing", append a clear error and return early instead of POSTing a payload that 422s.
- **BUG-4** Step 3 "No sampling locations selected" — `wiz_sl_{id}_mode` dropped by Streamlit after step 2. Added `wiz_sl_{sl_id}_mode_store` write in the step-2 `on_next` sync loop. New helper `_sl_mode(sl_wiz_id)` reads `_mode_store` first. Updated 4 read sites: `_sl_display_label` (L262), step-4 filter (L841-846), review summary (L1219), `_execute_creates` SL loop (L1432).
- **Wave B test work**: fixed the `mocked_lookups` fixture in `tests/app/test_campaign_wizard.py` for the `Type → Kind` rename (renamed `list_signal_port_types_lookup` → `list_signal_interfaces_lookup`, removed `list_signal_ports`, added `list_process_units_lookup`; renamed `create_signal_port` → `create_signal_interface`, `register_equipment_at_port` → `register_equipment_at_interface`; added `create_process_unit`, `deploy_das`, `get_das_conflict`; replaced stale `campaign_type_id` → `campaign_kind_id` and `processing_degree_id` → `processing_kind_id` in fixture data; updated assertion strings to match current validator wording). All **23 previously-erroring wizard tests** now pass. Added `TestStatePropagationBugs` class with 2 new focused regression tests (`test_bug_3_site_id_resolved_from_store_key_only`, `test_bug_4_sl_mode_resolved_from_store_key_only`) that simulate the post-transition state by deleting widget keys while keeping only `_store` keys. **25 of 25** wizard tests now pass.

### Wave D (lab observation model restructuring)

Executes `plan_lab_observation_model.md` Waves 1.2 → 4 (Wave 1.1 was already done in Wave A — same renderer `filter:` support).

- **YAML (Wave 1.2 + 1.3):** New tables `AnalysisSeries.yaml`, `AnalysisSeriesAxis.yaml`, `LabExperiment.yaml`. Modified `LabAnalysis.yaml` (added `LabExperiment_ID`, `AnalysisSeries_ID`, `Replicate`, `QualityCode_ID`; removed `Campaign_ID`; reordered columns; added `UQ_LabAnalysis_Identity`). Modified `Observation.yaml` (`Channel_ID` now nullable, added `LabAnalysis_ID`, XOR `CK_Observation_Source` check, replaced single UQ with two filtered indexes `UQ_Obs_Channel` (WHERE `Channel_ID IS NOT NULL`) and `UQ_Obs_Lab` (WHERE `LabAnalysis_ID IS NOT NULL`)). Deleted `LabValue.yaml`.
- **DDL (Wave 1.4):** Regenerated via `uv run mkdocs build`. Verified `sql_generation_scripts/v4.1.0_create_mssql.sql` contains all three new CREATE TABLE blocks, the Observation XOR CHECK, both filtered UQ indexes, the new LabAnalysis FKs, and zero remaining `LabValue` references.
- **Python models (Wave 2):** `src/open_dateaubase/data_model/table_models.py` — `ObservationBase` now has `channelID: Optional[int]` + `labanalysisID: Optional[int]`. `LabAnalysisBase` gains `labexperimentID: int`, `analysisseriesID: int`, `replicate: int`, `qualitycodeID: Optional[int]`; drops `campaignID`. Removed `LabValueBase` / `LabValueCreate` / `LabValue`. Added `AnalysisSeries{Base,Create}`, `AnalysisSeriesAxis{Base,Create}`, `LabExperiment{Base,Create}` and their non-Base concrete classes.
- **API schemas (Wave 3.1):** `api/v1/schemas/ingestion.py` — replaced `LabValueItem` + old `LabIngestRequest` with `LabMeasurementItem` (series identity + measurement fields including `value: float | list | None` for scalar/vector/matrix) and a new `LabIngestRequest` (`name`, `experiment_datetime`, `campaign_id?`, `description?`, `created_by_person_id?`, `measurements: list[LabMeasurementItem]` with non-empty validator). `LabIngestResponse` now returns `lab_experiment_id` (was `lab_analysis_id`).
- **Repository (Wave 3.2):** `api/v1/repositories/ingestion_repository.py` — added `find_or_create_analysis_series` (find-by-identity, insert if missing, returns `AnalysisSeries_ID`), `insert_lab_experiment`, `upsert_analysis_series_axis`, `insert_lab_observation` (writes Observation with `Channel_ID=NULL` + `LabAnalysis_ID` set; routes payload to `Value` / `ValueVector` / `ValueMatrix` based on `value_kind_id`, resolving vector/matrix bin axes from `AnalysisSeriesAxis`). Updated `insert_lab_analysis` signature to require `lab_experiment_id` + `analysis_series_id`, drop `campaign_id`, add `replicate` + `quality_code_id`; supports `analysis_datetime=None` to use the DB DEFAULT. Removed `insert_lab_value`.
- **Endpoint (Wave 3.3):** `api/v1/endpoints/ingest.py::ingest_lab` — new flow: insert LabExperiment → loop measurements: find-or-create AnalysisSeries, insert LabAnalysis, re-read AnalysisDateTime if defaulted, insert lab Observation routed to payload. Returns `LabIngestResponse(lab_experiment_id, rows_written)`.
- **Tests (Wave 4):** Added `tests/unit/test_ingestion_repository_lab.py` with 7 mocked-cursor tests covering `find_or_create_analysis_series` (found + not-found paths), `insert_lab_experiment`, `insert_lab_analysis` (new FKs in SQL + `Campaign_ID` absent + datetime-default branch), `insert_lab_observation` (XOR columns set + scalar routes to `Value` + unsupported value_kind raises). Updated `tests/api/contract/test_schema_contracts.py::test_lab_ingest_rejects_empty_values` payload to the new shape (provides `name` + `experiment_datetime` + `measurements: []`). The integration test from the plan's verification gate ("insert AnalysisSeries + LabExperiment + scalar/vector → routes to Value/ValueVector") needs a live MSSQL DB and is gated by `tests/integration/conftest.py` — left as the manual smoke check from the plan (Wave 4 verification).
- **Verification:** Re-ran `uv run pytest -q tests/unit tests/api tests/schema tests/app --ignore=tests/integration -p no:cacheprovider` → **38 failed, 352 passed** (same 38 cluster as the post-Wave-C baseline; 7 new lab tests added to passing column). All 38 remaining failures live in the Wave F2 surface (5 files: `test_ingest_resolve_channel.py`, `test_ingest_tag_mode.py`, `test_ingest_tagless_mode.py`, `test_signal_interface_endpoints.py`, `test_sub_signal_endpoints.py`) — none touch the lab observation model. Zero new regressions from Wave D.

### Wave C (campaign deployment writes EquipmentLocationHistory)

- **BUG-5** `create_campaign_deployment` never recorded the physical placement. Added `temporal_history_repository.open_location_for_campaign()` mirroring `relocate_equipment` close-then-open semantics but (a) **adding `Campaign_ID`** to the INSERT column list and (b) **NOT committing** (caller owns the transaction). Threaded `valid_from: datetime | None`, `notes: str | None` through `DeploymentCreateIn` (`api/v1/schemas/campaigns.py`) → endpoint `create_campaign_deployment` (`api/v1/endpoints/campaigns.py`) → repository function. `campaign_repository.create_campaign_deployment` now (i) inserts `CampaignEquipment`, (ii) inserts `CampaignSamplingLocation` (idempotent), (iii) calls `open_location_for_campaign` to write the actual `EquipmentLocationHistory` row, all in one transaction with a single `conn.commit()` at the end. UI call site `app/components/campaign_wizard.py:1691` now passes `valid_from=campaign_start_date.isoformat()` when available. Backed by 3 new unit tests in `tests/unit/test_temporal_history_repository.py::TestOpenLocationForCampaign` using `MagicMock` (no DB needed) that verify (a) UPDATE-then-INSERT call sequence, (b) `Campaign_ID` column appears in the INSERT SQL string, (c) `conn.commit()` is NOT called by the helper, (d) bound parameters include equipment_id / sampling_point_id / start_time / campaign_id. **Requires Wave A's filtered-index fix** (BUG-2) — without it, the new INSERT would collide on the unfiltered unique index.

## Bug-list completion (11 of 12 items; ENH-2 image tab in progress)

| Item | Status |
|---|---|
| BUG-1 Change Wiring KeyError | ✅ done |
| BUG-2 Change Location 500 | ✅ done (root cause) |
| BUG-3 Campaign site_id | ✅ done |
| BUG-4 Campaign SL mode | ✅ done |
| BUG-5 Campaign deployment → location history | ✅ done (unit-tested; integration test needs MSSQL DB) |
| BUG-6 Image ingest contract | ✅ done (Wave E3 — api_client `ingest_sensor_image` already matches endpoint; status file was stale) |
| ENH-1 Strict DAS/Tag dropdowns | ✅ done (Wave E3 — `ingest_shapes.py` shows selectbox when DAS lookup available; passes `strict=True`; status file was stale) |
| ENH-2 Lab ingest full parity | ✅ done (Wave F3 — Scalar/Vector/Matrix/Image tabs; new `POST /ingest/lab-image` endpoint; folder upload = replicates) |
| ENH-3 Watershed area from geoJSON | ✅ done (Wave F1) |
| ENH-4 Process Unit P&ID Tag | ✅ done |
| ENH-5 Reusable kind_select | ✅ done (Wave E1) |
| ENH-6 Reusable wizard success page | ✅ done (Wave E2) |

## Handoff to a fresh agent

**Canonical plan:** `/Users/jeandavidt/.claude/plans/can-you-look-through-tidy-anchor.md`
— full per-wave breakdown, cluster table of pre-existing failures, per-wave "tests to flip GREEN" verification gates, and the resume checklist.

**Deep design notes:** `/Users/jeandavidt/.claude/plans/can-you-look-through-tidy-anchor-agent-a232308db0ea76f77.md`.

**Why a fresh agent for D + E + F:** the lab observation model restructuring (Wave D) alone touches 8+ files across YAML / DDL / Python models / API schemas / endpoints / repository / tests. A fresh agent has the headroom to do that cleanly. The current session has done enough load-bearing reads + edits that handing off is the responsible call.

**Verify Wave A–C are still in place** (the user has not committed, so the agent should run these to confirm the working tree state):

```bash
grep -c "WHERE \[ValidTo\] IS NULL" sql_generation_scripts/v4.1.0_create_mssql.sql   # expect 4
grep -c "filter:" schema_dictionary/tables/EquipmentLocationHistory.yaml             # expect 1
grep -c "DAS › " app/pages/equipment_move.py                                        # expect 1
grep -c "P&ID Tag" app/pages/process_units.py                                       # expect 2
grep -c "wiz_s1_site_label_store" app/components/campaign_wizard.py                  # expect ≥3
grep -c "wiz_sl_.*_mode_store\|_sl_mode" app/components/campaign_wizard.py          # expect ≥5
grep -c "open_location_for_campaign" api/v1/repositories/temporal_history_repository.py api/v1/repositories/campaign_repository.py  # expect 1 each
uv run pytest -q --no-header tests/unit tests/api tests/schema tests/app --ignore=tests/integration -p no:cacheprovider 2>&1 | tail -3   # expect 38 failed
```

**Sequencing for the fresh agent:**

1. ~~Wave D (lab observation model)~~ — **DONE this session.** Backend complete; UI parity (Wave F3) still pending.
2. Wave E1, E2, E3 — reusable components groundwork.
3. Wave F1 (geoJSON area), Wave F2 (strict DAS/Tag + BUG-6 image ingest + flip the remaining `_type_` → `_kind_` and ingest-contract failures), Wave F3 (lab UI parity — now unblocked by Wave D).

**Remaining 38 baseline failures** all cluster around the in-progress ingest / signal-interface refactor and flip GREEN as part of Wave F2.

**Additional Wave D verification commands for a fresh agent:**

```bash
grep -c "WHERE Channel_ID IS NOT NULL\|WHERE LabAnalysis_ID IS NOT NULL" sql_generation_scripts/v4.1.0_create_mssql.sql   # expect ≥2
grep -c "CK_Observation_Source" sql_generation_scripts/v4.1.0_create_mssql.sql                                            # expect 1
grep -c "AnalysisSeries\|LabExperiment" sql_generation_scripts/v4.1.0_create_mssql.sql                                    # expect ≥6
grep -c "LabValue" sql_generation_scripts/v4.1.0_create_mssql.sql                                                         # expect 0
ls schema_dictionary/tables/LabValue.yaml 2>&1 | grep -c "No such file"                                                   # expect 1
uv run python -c "from open_dateaubase.data_model.table_models import AnalysisSeries, LabExperiment, LabAnalysis; print('OK')"
uv run pytest -q tests/unit/test_ingestion_repository_lab.py -p no:cacheprovider 2>&1 | tail -2                          # expect 7 passed
```
