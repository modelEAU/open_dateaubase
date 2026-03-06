---
phase: 05-timeseries-viewer
plan: 01
subsystem: frontend-ui
provides: [explore-page, lttb-component, timeseries-visualization]
affects: [06-deployment-setup]
tech-stack:
  added: [plotly, lttb-algorithm]
  patterns: [streamlit-session-state, api-client-httpx, plotly-go]
key-files:
  - app/pages/11_Explore.py
  - app/components/lttb.py
  - sql/seed_explore.sql
key-decisions:
  - LTTB downsampling implemented as pure-Python component (no external dep) at 1000-point cap
  - Multi-value-type dispatch in single page (Scalar/Vector/Matrix/Image) with per-type viz
  - Equipment events and annotations overlaid on scalar charts via Plotly shapes
---

# Phase 5 Plan 1: Timeseries Viewer Summary

**Comprehensive data explorer built with multi-series visualization, LTTB downsampling, annotation/event overlays, and all four value-type renderers.**

## Accomplishments

- `app/pages/11_Explore.py` — Data Explorer page (38.9 KB) supporting all four value types:
  - **Scalar**: overlaid Plotly line charts, quality-code colored points (6-color map), annotation overlays as vertical bands, equipment event markers, point selection for annotation creation
  - **Vector**: 2D heatmap (time × bin axis) rendered via Plotly `go.Heatmap`
  - **Matrix**: time-slice heatmap or row/col slice line chart
  - **Image**: thumbnail gallery with fullscreen dialog and multi-select bulk actions
- `app/components/lttb.py` — Pure-Python Largest-Triangle-Three-Buckets downsampling; reduces timeseries to ≤ 1000 points while preserving visual shape; no external dependencies
- `sql/seed_explore.sql` — Seed data for exploration development/testing
- API client functions added to `app/api_client.py`: `get_channel_timeseries`, `get_channel_thumbnail`, `get_channel_image`, `get_equipment_events`, `list_annotation_types`, `list_campaigns_lookup`, `list_equipment_lookup`, `list_parameters_lookup`, `list_channels`, `list_equipment_event_types`, `create_equipment_event`
- Session-state caching layer: timeseries, annotations, and equipment events cached per `(channel_id, start, end)` key to avoid redundant API calls on re-renders
- Date range picker, channel multi-selector (filterable by parameter/equipment/campaign), download CSV button

## Files Created/Modified

- `app/pages/11_Explore.py` — Created: Data Explorer page
- `app/components/lttb.py` — Created: LTTB downsampling algorithm
- `sql/seed_explore.sql` — Created: Seed data for exploration
- `app/api_client.py` — Modified: Added timeseries, image, equipment event, and lookup functions

## Decisions Made

- **LTTB as pure Python**: No numpy/scipy dependency added; algorithm hand-rolled to keep app Docker image lightweight.
- **VIZ_MAX_POINTS = 1000**: Hard cap for LTTB output to keep Plotly render time acceptable.
- **All value types in one page**: Single `11_Explore.py` with per-type render branches rather than separate pages, reducing navigation complexity for graduate students.
- **Quality colors**: Six-slot color dict (Accepted/Suspect/Rejected/BelowLoD/AboveLoQ/Outlier) hardcoded from QualityCode seed data.

## Issues Encountered

None documented — phase executed by a separate agent.

## Next Phase Readiness

- Phase 06 (Deployment Setup) can proceed immediately.
- `Dockerfile.app` does not yet exist — app service missing from docker-compose.yml.
- Existing `Dockerfile` references outdated entry point (`api_metadata.main:app`) and uses `requirements.txt` (no longer present); needs replacement with `Dockerfile.api` using uv.
- `API_BASE_URL` env var must be set correctly in Docker context (`http://api:8000/api/v1`) vs local dev (`http://localhost:8000/api/v1`).
- No `.env.example` exists yet; only `.env.docker.example` (DB vars only).
