# Lab AnalysisSeries Annotation — Implementation Plan

Give lab **AnalysisSeries** annotation parity with sensor **Channels** by
mirroring the `Observation` exclusive-arc one level up onto `Annotation`.

**Design locked via grill-with-docs (2026-06-10).** See:
- [ADR 0003](../docs/adr/0003-exclusive-arc-for-sensor-lab-polymorphism.md) — exclusive arc vs. supertype + trip-wire
- [CONTEXT.md](../CONTEXT.md) — `Annotation` glossary term + resolved convention

## Decisions (recap)

| # | Branch | Decision |
|---|---|---|
| 1 | Granularity | Full parity — range **and** point |
| 2 | Anchor | `Channel_ID` nullable + new `AnalysisSeries_ID` nullable + XOR CHECK |
| 3 | Point pin | Exact `Observation` (one Replicate); `AnalysisSeries_ID` always set, `Observation_ID` optional |
| 4 | Endpoint | `GET/POST /analysis-series/{series_id}/annotations` (parallel sub-resource) |
| 5 | Scope | Full — including `/recent` + `/by-type` via UNION |
| 6 | Response | Discriminated `anchor: {kind, id}` replaces flat `channel_id` (breaking) |
| 7 | Mixed create | Per-arm, no mixing (homogeneous dialog) |
| 8 | Pin integrity | Service-layer guard, applied to **both** arms |

## Guardrails

- **Pre-release v2.0 → dictionary correction, NOT a migration.** Edit the YAML,
  regenerate DDL. No `migrations/` scripts. (CLAUDE.md rule 6, [[project-context]])
- **Never touch `dbo.Value` / existing production tables** beyond the agreed
  `Annotation` column changes. (CLAUDE.md rule 5)
- **Unit tests only** — `uv run pytest tests/unit/`. Integration suite is broken.
  ([[feedback-testing]])
- Every new column has a dictionary entry. (CLAUDE.md rule 7)
- Slices are vertical + independently committable; commit each with `/sc`.
- **Every slice ships behavior-checking tests.** A slice is NOT done because the
  existing suite passes — that only proves *no regression*. Done = a **new or
  extended** test exercises the modified behavior AND would **fail on the
  pre-change code** (red → green). Before committing a slice, confirm each new
  test actually pins the new behavior: stash the production change, run the test,
  watch it fail; restore, watch it pass. If a test passes both ways, it isn't
  testing the change. ([[feedback-tests-must-cover-modified-behavior]])

---

## Slice 0 — Schema (data layer)

Anchor columns + XOR, regenerated from the dictionary.

- [ ] `schema_dictionary/tables/Annotation.yaml`:
  - [ ] `Channel_ID`: `nullable: false` → `nullable: true`
  - [ ] Add `AnalysisSeries_ID` (nullable, FK → `AnalysisSeries.AnalysisSeries_ID`)
  - [ ] Add `check_constraints: [{name: CK_Annotation_Source, expression: "(Channel_ID IS NOT NULL AND AnalysisSeries_ID IS NULL) OR (Channel_ID IS NULL AND AnalysisSeries_ID IS NOT NULL)"}]`
  - [ ] Add index `IX_Annotation_Series_Time` on `(AnalysisSeries_ID, StartTime, EndTime)` (mirror `IX_Annotation_Channel_Time`)
  - [ ] Update table `description` to say anchor is Channel **or** AnalysisSeries
  - [ ] Tighten `Observation_ID` description: pin valid for either source; for lab it pins one Replicate
- [ ] Regenerate DDL from dictionary (`tools/schema_migrate/render.py` / `scripts/generate_sql.py`); confirm the CHECK + FK + index emit (watch the generator caveat, [[ddl-regeneration-caveat]])
- [ ] Rebuild local DB (`scripts/init_db.py`) — confirm table creates clean
- [ ] **Test (new):** extend the schema-dictionary unit test (pattern:
  `tests/unit/test_lab_ingest_schema.py`) — assert `Annotation` has
  `Channel_ID` nullable, an `AnalysisSeries_ID` FK → `AnalysisSeries`, and a
  `check_constraints` entry named `CK_Annotation_Source`. Also assert the
  generator (`render.py`) **emits** the `CHECK (...)` and FK for `Annotation`.
- **Verify (red→green):** the new test fails against the un-edited YAML (no
  `AnalysisSeries_ID` / no CHECK), passes after the edit. DDL diff shows only the
  intended `Annotation` changes; DB builds.

## Slice 1 — Contract refactor (sensor only, no new behavior)

De-risk the breaking response change *in isolation*, sensor stays green.

- [ ] `api/v1/schemas/annotations.py`: add `AnnotationAnchor {kind: Literal['channel','series'], id: int}`; replace `AnnotationResponse.channel_id: int` with `anchor: AnnotationAnchor`; reconcile `AnnotationListResponse.channel_id`
- [ ] `api/v1/services/annotation_service.py` `_build_annotation_response`: emit `anchor` (kind `'channel'` for now)
- [ ] `tests/api/contract/test_schema_contracts.py`: assert on `anchor` instead of `channel_id`
- [ ] Frontend: no change expected (render loop never reads `ann['channel_id']`) — grep-confirm
- [ ] **Test (modified):** update `tests/api/contract/test_schema_contracts.py`
  to assert the sensor annotation response carries `anchor == {kind:'channel', id:N}`
  **and** that `channel_id` is gone. This is the test that pins the rename.
- **Verify (red→green):** the rewritten assertion fails on the old flat-`channel_id`
  builder, passes on the `anchor` builder. Full `tests/unit/` green (no regression).

## Slice 2 — Tracer bullet: lab range annotation, end to end

Thinnest complete vertical — proves the arc DB→UI for the simplest case (range, no pin).

- [ ] `api/v1/repositories/annotation_repository.py`: branch all `WHERE Channel_ID` / `JOIN Channel` on the anchor; `create_annotation` accepts `analysis_series_id`; `_row_to_annotation` carries both ids; add `get_annotations_for_series(series_id, from, to)`
- [ ] `api/v1/services/annotation_service.py`: `get_annotations_for_series` + `create_annotation_for_series` (guard via `analysis_series` lookup → 404, mirror channel guard); `_build_annotation_response` emits `kind:'series'` when series-anchored
- [ ] `api/v1/endpoints/annotations.py`: add `analysis_series_annotations_router` with `GET/POST /{series_id}/annotations`; mount under `/analysis-series` in `router.py`
- [ ] `app/pages/explore.py`: `_load_series_annotations(series_id)` (cache `explore_series_annotations`); draw `add_vrect`/`add_vline`/`[ref]` overlays in the lab-series loop (~L528); series path in `_annotation_dialog` POSTing `/analysis-series/{id}/annotations`
- [ ] **Tests (new):**
  - [ ] Repo+service unit: `create_annotation_for_series` then
    `get_annotations_for_series` returns the row with `anchor.kind=='series'`;
    creating against a non-existent series → 404.
  - [ ] Endpoint unit: `POST /analysis-series/{id}/annotations` → 201; `GET`
    returns it. (mirror the existing `/timeseries/{ch}/annotations` endpoint tests)
  - [ ] Frontend AppTest (`tests/.../app`, per [[app-testing-protocol]] /
    write-streamlit-tests): with the series-annotations API mocked, the explore
    chart renders the overlay row for a lab Trace (assert overlay table contains
    the annotation / a vrect was added).
- **Verify (red→green):** each test fails before its layer's change (no series
  router / no series load) and passes after. Manual: range annotation on a lab
  Trace renders band+line.

## Slice 3 — Point pin + symmetric integrity guard

- [ ] Lab point pin: dialog/UI passes `Observation_ID` for a clicked replicate; repo/service persist it on the series arm
- [ ] Service guard `_assert_pin_in_anchor(conn, observation_id, anchor)`: pinned `Observation` must resolve to the anchored stream — lab via `Observation→LabAnalysis→AnalysisSeries`, sensor via `Observation.Channel_ID`; else `422`
- [ ] Wire guard into **both** `create_annotation` (sensor) and `create_annotation_for_series` (lab) — backfills the check the sensor arm never had
- [ ] **Tests (new):** parametrized over both arms —
  - [ ] pin an `Observation` from a *different* stream → `422`
  - [ ] pin an `Observation` belonging to the anchor → `201` and `Observation_ID` persisted
  - [ ] lab: pinning replicate-2 of the correct series → `201` (the exact-replicate case)
- **Verify (red→green):** the 422 tests fail before the guard exists (the
  mismatched pin would currently insert), pass after. Sensor 422 test proves the
  backfill actually runs on the sensor arm.

## Slice 4 — Edit / delete, lab-aware

PUT/DELETE are keyed on `annotation_id` (anchor-agnostic) — confirm no Channel coupling leaks.

- [ ] Audit `update_annotation` / `get_annotation_by_id` / `delete_annotation` for `JOIN Channel` assumptions; branch where needed
- [ ] Frontend edit/delete affordances work on a series-anchored annotation
- [ ] **Tests (new):** create a series-anchored annotation, `PUT` it (change
  kind/comment) → reflected; `GET` by id → `anchor.kind=='series'`; `DELETE` →
  gone. A regression test that `update`/`get_by_id` don't drop lab rows via a
  stale `JOIN Channel`.
- **Verify (red→green):** the lab get-by-id / update test fails if any read path
  still inner-joins `Channel` (lab row vanishes), passes once branched.

## Slice 5 — Cross-series feeds (`/recent`, `/by-type`)

- [ ] `annotation_repository`: rewrite `get_recent_annotations` + `get_annotations_by_kind` as `UNION ALL` of a Channel-enriched half and an AnalysisSeries-enriched half (`AnalysisSeries → SamplingPoint` ⇒ `location`, `→ Parameter` ⇒ `variable`); `ORDER BY` preserved
- [ ] Service: enrichment maps both halves onto the existing generic `location` / `variable` fields; response carries `anchor`
- [ ] **Tests (new):** seed one sensor + one lab annotation; assert **both**
  appear in `/recent` ordered by `created_at`, and a lab annotation appears in
  `/by-type/{name}` with `location` (SamplingPoint) + `variable` (Parameter)
  populated and `anchor.kind=='series'`.
- **Verify (red→green):** the "lab annotation appears in /recent" assertion fails
  on the old Channel-only `JOIN` (lab row excluded), passes after the UNION.

## Slice 6 — Coverage audit + docs close-out

Tests are authored per-slice (above); this slice proves the *net* is complete.

- [ ] **Coverage audit:** every decision (1–8) maps to at least one test that
  fails without its change. Walk the table; for any row lacking a guarding test,
  add one. Specifically confirm: XOR rejection, anchor-branch read, both-arm pin
  guard, anchor response shape, UNION feeds.
- [ ] **Red-green spot-check:** for the 2–3 highest-risk tests (XOR reject, pin
  guard, lab-in-/recent), re-confirm red on `git stash` of the production change.
- [ ] Update annotation API docs / examples referencing `channel_id` → `anchor`
- [ ] Confirm dictionary entry complete; re-run DDL regen clean
- [ ] `uv run pytest tests/unit/` fully green
- **Verify:** would a staff engineer approve? Diff sensor behavior vs. `main` —
  unchanged except the `anchor` rename, and every new path has a test that would
  catch its regression.

---

## Review (completed 2026-06-10)

Delivered via one-agent-per-slice delegation, dependency-ordered, each slice a
single semantic commit gated on a red→green test before commit.

| Slice | Commit | Result |
|---|---|---|
| 0 Schema | `ef68581` | XOR anchor in dictionary; +7 schema tests (red→green) |
| 1 Contract | `2eda421` | `anchor:{kind,id}` response, sensor-only no-behavior-change |
| 2 Tracer | `24f202b` | lab range annotation DB→UI; +8 unit/+8 contract/+1 app |
| 3 Pin+guard | `3b058a0` | Observation_ID pin + symmetric 422 guard (both arms) |
| 4 Edit/delete | `643f54d` | audit found paths already lab-safe; +regression tests (inject-the-bug proof) |
| 5 Feeds | `80e3200` | `/recent`+`/by-type` UNION; caught latent dropped-enrichment bug |
| 6 Audit | `638a113` | all 8 decisions mapped to teeth-tested coverage; docs + stale comments fixed |

**Final suites:** 188 unit · 222 contract · 42 app — all green (baseline was 147 unit).

**Residual nits (non-blocking, noted by audit):** contract feed tests mock the
cursor so they prove anchor/enrichment mapping but not the UNION SQL (carried by
separate SQL-shape unit tests); update lab-safety rests on SQL-string-absence
assertions, slightly brittle to refactors. Both acceptable under unit-tests-only.

**Not done (out of scope by decision):** `AnnotationUpdate` pin-mutation
(deferred, absence is test-pinned); DB-level XOR rejection can't be unit-tested
(no live DB) — verified at dictionary+generator level instead.
