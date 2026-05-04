# Task Plan: Importer Fixes (Fix 0–4)

## Goal
Fix 5 importer bugs so `docker compose up importer` runs cleanly with correct channel types, correct timestamps, and all configured channels.

## Fixes to Apply

- [ ] Fix 1 — Timestamps land in 1970 (pandas 2.x precision)
  - `data_file.py` line 141: RodtoxFile — replace `.astype(np.int64) // 1e9` with `.map(lambda ts: ts.timestamp() if pd.notna(ts) else float("nan"))`
  - `data_file.py` line 187-190: AnaproFile — same replacement (inline chain)

- [ ] Fix 2 — Vector channel created as Scalar (missing value_type_id=2)
  - `import_script.py` _ingest_vector_source() ~line 419: add `value_type_id=2` to resolve_channel call

- [ ] Fix 3 — Add `file_reader_type` to config (decouple config name from reader dispatch)
  - `config.py`: add `file_reader_type: str | None = None` to TaggedFileConfig and TaglessFileConfig
  - `import_script.py` line 157: change `get_file_reader(file_cfg.name)` → `get_file_reader(file_cfg.file_reader_type or file_cfg.name)`

- [ ] Fix 4 — Add `file_reader_type: rodtox` to .par configs in wwtp_scan_anaprolyser.yaml
  - All 4 file_configs entries (scan_par_tss, scan_par_cod, scan_par_nh4n, scan_par_temp)

- [ ] Fix 0 — Add `--config-dir` support (eliminate docker/import-test-data.yaml)
  - `import_script.py`: add `read_configs_from_dir(path)` function
  - `__main__.py`: add `--config-dir` flag to import subcommand
  - `docker-compose.yml`: mount `./importer/configs` as `/configs`, use `--config-dir /configs`

## Status
**Starting Fix 1**
