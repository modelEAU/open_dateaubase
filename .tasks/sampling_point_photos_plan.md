# Plan: Sampling Point Photo Upload Feature

## Goal
Replace the dead `Pictures VARBINARY(MAX)` column with a filesystem-based photo that harmonizes with the existing sensor-image infrastructure. Store photos on disk, keep a relative path in the DB, serve via FileResponse, and expose upload/view/delete in the Streamlit app.

---

## System Context: Existing Image Infrastructure

The project already has a working image-on-disk system for sensor data. The new feature must align with it:

| Concern | Existing (sensor images) | New (sampling point photos) |
|---|---|---|
| Upload dir config | `settings.upload_dir = "./uploads/images"` | Reuse same base dir |
| Base dir (implicit) | `Path(settings.upload_dir).parent` = `./uploads/` | Same base: `./uploads/` |
| On-disk path | `./uploads/images/{channel_id}/{ts}.{ext}` | `./uploads/sampling_points/{sp_id}_{uuid}.{ext}` |
| DB column | `ValueImage.StoragePath` (`images/{channel_id}/...`) | `SamplingPoint.PicturePath` (`sampling_points/{...}`) |
| Serving | `GET /timeseries/{ch_id}/image/{ts}` → `FileResponse` | `GET /sites/{site_id}/sampling-locations/{sp_id}/picture` → `FileResponse` |
| Thumbnail | BLOB in DB (Pillow, 100×100) | None needed — reference photo, not time-series |
| App fetch | `get_channel_image()` → `bytes` → `st.image()` | Same pattern |
| App upload | `ingest_sensor_image()` → multipart POST | `upload_sampling_point_picture()` → multipart POST |

**Config note**: `upload_dir` is misleadingly named — it's the sensor-image-specific folder, not the base.
The plan adds an explicit `upload_base_dir` property to `Settings` to make this intent legible
and avoid the `Path(...).parent` hack being repeated in two places.

---

## Phases

### Phase 1 — DB Migration
- [ ] Write `migrations/v3.0.0_sampling_point_picture_path.sql`
  - `ALTER TABLE [dbo].[SamplingPoint] DROP COLUMN [Pictures]`
  - `ALTER TABLE [dbo].[SamplingPoint] ADD [PicturePath] NVARCHAR(500) NULL`
- [ ] Write `migrations/v3.0.0_sampling_point_picture_path_rollback.sql`
  - `DROP COLUMN [PicturePath]`
  - `ADD [Pictures] VARBINARY(MAX) NULL`
- [ ] Append migration to `sql/init.sql` (after existing v3.0.0 patches, before seed)
- [ ] Update `schema_dictionary/tables/SamplingPoint.yaml`
  - Remove `Pictures` entry (was `logical_type: # TODO: unmapped SQL type: BLOB`)
  - Add `PicturePath` entry: `logical_type: string`, `max_length: 500`, `nullable: true`

### Phase 2 — Config & Startup Cleanup
- [ ] `api/config.py`: add `upload_base_dir` property
  ```python
  @property
  def upload_base_dir(self) -> str:
      return str(Path(self.upload_dir).parent)
  ```
  This makes the base dir explicit and removes the `.parent` magic from call sites.
- [ ] `api/main.py`: also `mkdir` `uploads/sampling_points/` on startup (alongside existing `upload_dir`)
- [ ] Update `api/v1/endpoints/timeseries.py`: replace `Path(settings.upload_dir).parent` with `Path(settings.upload_base_dir)` in `get_image_file()`

### Phase 3 — Repository & Schema
- [ ] `api/v1/schemas/metadata.py`: add `picture_path: str | None = None` to `SamplingLocationOut`
- [ ] `api/v1/repositories/site_repository.py`:
  - `get_sampling_locations_for_site()`: add `sp.[PicturePath]` to SELECT
  - `insert_sampling_location()`: confirm it does not reference `Pictures` (it doesn't currently)
  - Add `update_sampling_location_picture(conn, sp_id: int, path: str | None) -> None`

### Phase 4 — API Endpoints
Add three endpoints to `api/v1/endpoints/sites.py` under the existing `/{site_id}/sampling-locations` router:

- [ ] `POST /{site_id}/sampling-locations/{sp_id}/picture`
  - Accepts `UploadFile`, validates extension (jpg/jpeg/png only)
  - Generates filename: `{sp_id}_{uuid4().hex}.{ext}`
  - Writes to `Path(settings.upload_base_dir) / "sampling_points" / filename`
  - If a previous file exists (non-NULL `PicturePath`), delete the old file from disk first
  - Calls `update_sampling_location_picture(conn, sp_id, relative_path)`
  - Returns `{"picture_path": relative_path}`

- [ ] `GET /{site_id}/sampling-locations/{sp_id}/picture`
  - Reads `PicturePath` from DB
  - Returns 404 if NULL or file missing
  - Returns `FileResponse` with correct `media_type` (same mime map as timeseries endpoint)

- [ ] `DELETE /{site_id}/sampling-locations/{sp_id}/picture`
  - Reads current `PicturePath`; returns 404 if already NULL
  - Deletes file from disk (suppress `FileNotFoundError`)
  - Calls `update_sampling_location_picture(conn, sp_id, None)`
  - Returns 204

### Phase 5 — App API Client
Add to `app/api_client.py` (following the `get_channel_image` / `ingest_sensor_image` pattern):

- [ ] `get_sampling_point_picture(site_id: int, sp_id: int) -> bytes`
  - `GET /sites/{site_id}/sampling-locations/{sp_id}/picture`
  - Returns raw bytes (caller passes to `st.image()`)

- [ ] `upload_sampling_point_picture(site_id: int, sp_id: int, file_bytes: bytes, filename: str) -> dict`
  - `POST /sites/{site_id}/sampling-locations/{sp_id}/picture` (multipart)
  - Returns parsed JSON (contains `picture_path`)

- [ ] `delete_sampling_point_picture(site_id: int, sp_id: int) -> None`
  - `DELETE /sites/{site_id}/sampling-locations/{sp_id}/picture`

### Phase 6 — App UI (sites.py)
The sites page already has a sampling locations section. Extend it:

- [ ] When showing a sampling location row, display a photo thumbnail inline if `picture_path` is set
  - Fetch bytes via `get_sampling_point_picture()` and show with `st.image(..., width=120)`
- [ ] In the sampling location edit/detail view, add a **Photo** section:
  - If photo exists: show `st.image()` at reasonable size + a **Remove photo** button
  - `st.file_uploader("Upload photo", type=["jpg","jpeg","png"])` always visible
  - On upload: call `upload_sampling_point_picture()` → show success + refresh
  - On remove: call `delete_sampling_point_picture()` → show success + refresh

### Phase 7 — Docker & Volume
- [ ] `docker-compose.yml`: add `uploads` named volume mounted at `/app/uploads` in the `api` service
  - This makes photos persist across `docker compose restart` (not `down -v`)
- [ ] `Dockerfile.app` (or API Dockerfile): ensure `/app/uploads/sampling_points` is writable at runtime
- [ ] Add `uploads/sampling_points/.gitkeep` and ensure `uploads/images/.gitkeep` also exists so the dir structure is committed but contents are gitignored
- [ ] Verify `uploads/` is in `.gitignore` (contents, not the gitkeep files)

### Phase 8 — Rebuild & Manual Test
- [ ] `docker compose down -v && docker compose up --build`
- [ ] Upload a photo to a sampling point via the app
- [ ] Verify it appears in the list view
- [ ] Restart container (`docker compose restart api`) — confirm photo persists
- [ ] Delete the photo — confirm file is removed from disk and DB is NULL

---

## Key Decisions

| Decision | Rationale |
|---|---|
| `PicturePath` not `PictureUrl` | Consistent with `ValueImage.StoragePath` — always a relative disk path, never a URL |
| One photo per sampling point | Simpler UX; the reference-photo use case doesn't need galleries |
| No thumbnail blob in DB | Sampling point photos are rarely accessed; Streamlit can resize on the fly |
| Delete old file on re-upload | Prevents orphaned files accumulating on disk |
| FileResponse not StaticFiles | Consistent with how sensor images are served; allows auth guards later |
| Endpoint under `/sites/{site_id}/sampling-locations/{sp_id}/picture` | Follows existing nested route convention for sampling locations |
| `upload_base_dir` config property | Makes the base dir intent explicit; removes the `.parent` anti-pattern from two places |

## Constraints (per CLAUDE.md)
- Every schema change → migration + rollback + YAML dictionary entry
- Sync API only (`def`, pyodbc)
- DB volume teardown required after migration: `docker compose down -v && docker compose up --build`

## Status
**Phases 1–7 implemented** — Phase 8 (rebuild + manual test) pending docker volume teardown.
