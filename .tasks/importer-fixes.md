# Importer Fix Plan

## Fix 0 — Structural: support --config-dir (eliminate docker/import-test-data.yaml)

**Why:** The importer CLI only accepts a single `--config` file. `docker/import-test-data.yaml` is a
hand-maintained duplicate of the per-instrument configs in `importer/configs/`. It has already drifted
badly (wrong tags, missing variables, old felinoscope config). The fix is to make all bugs below
self-healing by eliminating the duplicate.

**Files:**
- `importer/src/table_import/import_script.py` — add `read_configs_from_dir(path)` that globs
  `*.yaml`, parses each as `Config`, and merges the list fields (`file_configs`, `tsdb_configs`,
  `scada_sql_configs`, `vector_file_configs`, `image_folder_configs`, `matrix_file_configs`).
  `api_config` is taken from the first file (or a dedicated `api_config.yaml`).
- `importer/src/table_import/__main__.py` — add `--config-dir` flag; if supplied, call
  `read_configs_from_dir` instead of `read_config_from_file`.
- `docker-compose.yml` — mount `./importer/configs` as `/configs` and change command to
  `["--config-dir", "/configs"]`. Remove the `./docker/import-test-data.yaml` volume mount.
- `docker/import-test-data.yaml` — delete (or keep as legacy reference, clearly marked deprecated).

**Acceptance:** `docker compose up importer` runs cleanly using the per-instrument configs directly.
All channels below appear with correct names and types after a fresh DB init.

---

## Fix 1 — Rodtox / AnaproFile: timestamps land in 1970 (pandas 2.x precision bug)

**Root cause:** `RodtoxFile.values()` and `AnaproFile.values()` use
`.astype(np.int64) // 1e9` on a tz-aware `datetime64[us]` series.
Pandas 2.x stores microseconds; dividing by 1e9 instead of 1e6 gives a value 1000× too small
(e.g. 2023-06-07 → ~1970-01-21).

**Files:**
- `importer/src/table_import/data_file.py`
  - `RodtoxFile.values()` line 141: replace `astype(np.int64) // 1e9`
  - `AnaproFile.values()` lines 188-190: same replacement
  - Use `.map(lambda ts: ts.timestamp() if pd.notna(ts) else float("nan"))` (same pattern as
    `PilEAUteSCADASource.get_values_since()`).

---

## Fix 2 — Vector channel created as Scalar (missing value_type_id)

**Root cause:** `_ingest_vector_source()` calls `client.resolve_channel()` without `value_type_id`.
API default is 1 (Scalar). Channel is created as Scalar; vector data is accepted silently.
Vocabulary confirms: scalar=1, vector=2, image=4. Image path already passes `value_type_id=4`.

**Files:**
- `importer/src/table_import/import_script.py`
  - `_ingest_vector_source()` ~line 419: add `value_type_id=2` to the `resolve_channel()` call.

**Secondary (API-side):** The `/ingest/sensor-vector` endpoint should reject vector payloads pushed
to a scalar channel. That's a separate API bug to address.

---

## Fix 3 — Add `file_reader_type` to config (decouple config name from reader dispatch)

**Root cause:** `get_file_reader(file_cfg.name)` dispatches on the config `name` field. Only
`"rodtox"`, `"anapro"`, `"tsdb"` are recognised. Any descriptive name raises `MissingFileTypeError`.
This blocks scan `.par` configs (Fix 4) and makes config naming brittle.

**Files:**
- `importer/src/table_import/config.py`
  - Add `file_reader_type: str | None = None` to `TaggedFileConfig` and `TaglessFileConfig`.
- `importer/src/table_import/import_script.py`
  - Change `get_file_reader(file_cfg.name)` to
    `get_file_reader(file_cfg.file_reader_type or file_cfg.name)`.

---

## Fix 4 — Missing scan scalar parameters (TSS, COD, NH4-N, Temperature from .par files)

**Root cause:** No `.par` file_configs exist in any docker-loadable config.
`RodtoxFile` can read `.par` files as-is (uses `file_structure.value_column`, handles European
decimals, supports `header_row_idx=1` to skip the device-identifier row 0).

**Files:**
- `importer/configs/wwtp_scan_anaprolyser.yaml`
  - The existing `file_configs` entries (scan_par_tss, scan_par_cod, scan_par_nh4n, scan_par_temp)
    need `file_reader_type: rodtox` added to each (unlocked by Fix 3).
  - Verify `status_map` uses `column: Status` / `OK: null` / `Warning: 2` — already correct.
  - Verify `directory_path` resolves correctly when mounted as `/test-data/scan`.

**Note:** `.par` file values use `.` decimal separator (not `,`), so the comma→dot replacement in
`RodtoxFile` is harmless but not needed.

---

## Fix 5 — spectro::lyser tagged with device identifier

**Root cause:** `importer/configs/wwtp_scan_anaprolyser.yaml` vector config uses
`tag: TEST_spectro::lyzer_V160` (correct), but `docker/import-test-data.yaml` accidentally used the
device identifier string from the `.fp` file row 0:
`13230077_10_0x0100_spectro::lyser_INFLUENTV160`.
This is fixed automatically by Fix 0 (docker config is replaced by the per-instrument configs).

**If Fix 0 is deferred:** change the `tag` in `docker/import-test-data.yaml` to
`TEST_spectro::lyzer_V160`.

---

## Fix 6 — Felinoscope not replaced by microscope config

**Root cause:** `docker/import-test-data.yaml` still has `equipment_name: felinoscope_2000`.
`wwtp_microscope.yaml` has the correct replacement (`equipment_name: TEST_microscope_001`).
Fixed automatically by Fix 0.

**If Fix 0 is deferred:** replace the `image_folder_configs` entry in the docker config with the
contents of `wwtp_microscope.yaml`.

---

## Fix 7 — SCADA docker config imports only HMI_DO (6 tags missing)

**Root cause:** `docker/import-test-data.yaml` has only one SCADA variable. The SQLite
`TagTable` confirms all 7 tags exist: `HMI_pH`, `HMI_Cond`, `HMI_Temp`, `HMI_Flow`,
`HMI_Level`, `HMI_Turb`, `HMI_DO`. All corresponding parameters and units are in the
vocabulary seed. Fixed automatically by Fix 0 (wwtp_plc_scada.yaml has all 7).

**If Fix 0 is deferred:** add the 6 missing variables to the docker config's `scada_sql_configs`.

---

## Fix 8 — Basestation turbidity test data is all zeros

**Root cause:** `100924-135506_TurbR300_2025.tsdb` has 99 records all with `value = 0.0`.
The tsdb reader is correct (timestamps parse to valid 2025 dates). The sensor was likely not
submerged or in calibration mode when the file was captured. This is a test data quality issue,
not a code bug.

**Secondary:** `metadata_byte = 136 (0x88)` on all data records is currently ignored.
WTW documentation should confirm whether this byte signals an invalid measurement; if so,
`TsdbFile.values()` should set `QualityCode` or skip the record accordingly.

**Files:**
- `importer/test_data/basestation/` — replace `100924-135506_TurbR300_2025.tsdb` with a file
  containing real non-zero turbidity readings.
- `importer/src/table_import/tsdb_file.py` (optional) — map `metadata_byte` to `QualityCode`.
