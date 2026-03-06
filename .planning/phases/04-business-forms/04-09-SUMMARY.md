---
phase: 04-business-forms
plan: 09
subsystem: api+ui
tags: [fastapi, streamlit, ingest, image, file-upload, pillow]
requires:
  - phase: 04-business-forms
    provides: scalar sensor ingest page with tabs (04-08)
provides:
  - POST /ingest/sensor-image multipart endpoint
  - Server-side file storage for images
  - Image ingest UI (Image tab in 9_Sensor_Ingest.py)
  - Phase 04 complete
affects: []
tech-stack:
  added: [Pillow (optional)]
  patterns:
    - Multipart form upload with FastAPI UploadFile
    - Server-side file storage with relative path DB records
    - Thumbnail generation for image previews
    - Four-tab sensor ingest interface (Scalar/Vector/Matrix/Image)
key-files:
  created: []
  modified:
    - api/config.py
    - api/main.py
    - api/v1/repositories/value_repository.py
    - api/v1/schemas/ingestion.py
    - api/v1/endpoints/ingest.py
    - app/pages/9_Sensor_Ingest.py
    - app/api_client.py
key-decisions:
  - File content stored on disk, not in DB — only metadata and path stored in ValueImage
  - Thumbnail stored as VARBINARY JPEG bytes for quick preview without file access
  - Pillow made optional with graceful fallback (no metadata/thumbnail if unavailable)
  - Upload directory configurable via settings, auto-created on startup
  - File naming uses ISO timestamp with colons replaced by hyphens for filesystem safety
  - Image channel uses value_type_id=4 (per existing schema design)
requirements-completed: []
duration: 0min
completed: 2026-03-05
---

# Phase 04 Plan 09: Image Ingest Infrastructure Summary

**Multipart image upload endpoint with server-side file storage, Pillow thumbnail generation, and Streamlit Image tab — completes Phase 04 Business Forms**

## Performance

- **Duration:** Pre-executed (commits exist)
- **Started:** 2026-03-05
- **Completed:** 2026-03-05
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Configurable upload directory (`./uploads/images` default) with auto-creation on API startup
- `POST /ingest/sensor-image` multipart endpoint accepting image file + metadata
- Server-side file storage at `uploads/images/{channel_id}/{timestamp}.{ext}`
- Pillow integration for image metadata extraction (width, height, channels, format)
- Thumbnail generation (100x100 JPEG) stored in ValueImage.Thumbnail column
- `insert_image_value` repository function for ValueImage table inserts
- `ImageIngestResponse` schema for API responses
- `ingest_sensor_image` client function in api_client.py
- Fourth "Image" tab in 9_Sensor_Ingest.py with file uploader, preview, and submit
- Full integration with existing channel identity dropdowns and timestamp inputs

## Task Commits

Each task was committed atomically:

1. **Task 1: Image ingest infrastructure** - `4b54d46` (feat)
   - Upload directory config in api/config.py
   - Startup directory creation in api/main.py
   - insert_image_value repository function
   - ImageIngestResponse schema
   - POST /ingest/sensor-image endpoint with Pillow metadata extraction
   - ingest_sensor_image client function

2. **Task 2: Image tab in Sensor Ingest** - `acf91e1` (feat)
   - Four-tab layout (Scalar, Vector, Matrix, Image)
   - Image tab with equipment/parameter/unit dropdowns
   - Date/time timestamp selection
   - st.file_uploader for image files (jpg, png, tif, bmp)
   - st.image preview with file info
   - Quality code input
   - Upload button with API integration

**Plan metadata:** `[to be committed]` (docs: complete plan)

## Files Created/Modified

- `api/config.py` - Added `upload_dir: str = "./uploads/images"` setting
- `api/main.py` - Added startup logic to create upload directory
- `api/v1/repositories/value_repository.py` - Added `insert_image_value()` function for ValueImage inserts
- `api/v1/schemas/ingestion.py` - Added `ImageIngestResponse` model
- `api/v1/endpoints/ingest.py` - Added `/sensor-image` endpoint with multipart handling, Pillow metadata extraction, thumbnail generation
- `app/api_client.py` - Added `ingest_sensor_image()` function with multipart form upload
- `app/pages/9_Sensor_Ingest.py` - Added fourth "Image" tab with file uploader, preview, and submit flow

## Decisions Made

1. **File storage, not DB BLOB**: Original schema has ValueImage store file path only; keeping file content on disk allows large images without DB bloat
2. **Thumbnail in DB**: Small 100x100 JPEG thumbnail stored as VARBINARY for quick preview without file system access
3. **Pillow optional**: Import wrapped in try/except; if Pillow unavailable, metadata fields stored as zeros/nulls but file still saved
4. **Relative paths in DB**: StoragePath stores relative path (`uploads/images/{channel_id}/{ts}.{ext}`) allowing upload directory to move
5. **Timestamp in filename**: ISO format with colons→hyphens for cross-platform filesystem compatibility
6. **Four tabs**: Image added as fourth tab alongside Scalar/Vector/Matrix, sharing channel identity UI pattern

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None - implementation proceeded smoothly with existing patterns.

## Verification Results

- ✅ POST /ingest/sensor-image endpoint registered at `/sensor-image`
- ✅ insert_image_value importable from value_repository
- ✅ Contract tests pass (89 tests)
- ✅ 9_Sensor_Ingest.py syntax valid
- ✅ Four tabs present (Scalar, Vector, Matrix, Image)
- ✅ st.file_uploader present for image files
- ✅ st.image preview present
- ✅ ingest_sensor_image call present in frontend

## Next Phase Readiness

Phase 04 Business Forms is complete. Ready for Phase 05: Timeseries Viewer.

Phase 04 delivered:
- ✅ Lookup API foundation (units, labs, procedures, samples, sampling points, equipment events, data provenance)
- ✅ EquipmentModel CRUD page
- ✅ Parameter CRUD page
- ✅ Campaign enhancement with equipment deployment
- ✅ Binning Axes page for spectral/distribution definitions
- ✅ Sensor ingest page with Scalar/Vector/Matrix/Image modes
- ✅ Lab ingest page with inline sample creation
- ✅ POST /ingest/samples endpoint
- ✅ Vector/Matrix ingest API
- ✅ Image ingest infrastructure

## Self-Check: PASSED

✅ All key files exist:
- api/config.py
- api/main.py
- api/v1/repositories/value_repository.py
- api/v1/schemas/ingestion.py
- api/v1/endpoints/ingest.py
- app/pages/9_Sensor_Ingest.py
- app/api_client.py

✅ All 04-09 commits verified:
- 4b54d46 feat(04-09): add image ingest infrastructure
- acf91e1 feat(04-09): add Image tab to Sensor Ingest page
- 9d70a9c docs(04-09): complete image ingest infrastructure plan

✅ Verification commands pass:
- POST /ingest/sensor-image endpoint registered
- insert_image_value importable
- Contract tests pass (89 tests)
- Streamlit page syntax valid
- Four tabs present with Image tab functional

---
*Phase: 04-business-forms*
*Completed: 2026-03-05*
