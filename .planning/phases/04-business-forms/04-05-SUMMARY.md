---
phase: 04-business-forms
plan: 05
type: execute
domain: streamlit
---

# Phase 04 Plan 05: Sensor Data Ingest Page Summary

## Objective
Create a Streamlit sensor ingest page for scalar time series data. The student selects equipment, parameter, and unit from dropdowns, pastes or uploads a CSV of timestamp+value rows, reviews a preview, and submits to POST /ingest/sensor.

## What Was Built

### New File Created
- `app/pages/9_Sensor_Ingest.py` - Scalar sensor data ingest page with:
  - Channel identity section (Equipment, Parameter, Unit, Data Provenance, Processing Degree dropdowns)
  - Data input section with "Paste CSV" and "Upload CSV file" modes
  - CSV parsing with header auto-detection and error handling
  - Preview table showing first 20 valid rows
  - Submit to database with success feedback showing channel_id

### API Enhancements
- Added `list_data_provenance_lookup()` to `api/v1/repositories/lookup_repository.py`
- Added GET `/ingest/lookup/data-provenance` endpoint to `api/v1/endpoints/ingest.py`
- Added `list_data_provenance_lookup()` to `app/api_client.py`

## Database-Driven Dropdowns

All dropdowns now query the database instead of using hardcoded values:

| Field | Lookup Function | Source Table |
|-------|----------------|--------------|
| Equipment | `list_equipment_lookup()` | dbo.Equipment |
| Parameter | `list_parameters_lookup()` | dbo.Parameter |
| Unit | `list_units_lookup()` | dbo.Unit |
| Data Provenance | `list_data_provenance_lookup()` | dbo.DataProvenance |
| Processing Degree | `list_processing_degrees_lookup()` | dbo.ProcessingDegree |

## CSV Input Features

- **Paste CSV mode**: Text area with example placeholder showing ISO timestamp format
- **Upload CSV mode**: File uploader supporting .csv files
- **Parsing**: Uses Python csv module with BOM stripping and header auto-detection
- **Validation**: Timestamp parsed with `datetime.fromisoformat()`, value as float, quality_code as int
- **Error handling**: Parse errors shown in expandable section, valid rows remain submittable
- **Preview**: First 20 rows displayed in dataframe

## Submit Behavior

- Submit button disabled until Equipment, Parameter, and Unit are selected AND valid rows exist
- Payload sent to `ingest_sensor()` with proper SensorIngestRequest shape
- Success message shows: "✅ Ingested {N} rows into channel **{channel_id}**"
- Session state cleared after successful submission

## Verification Results

- ✅ Page syntax-checks clean (`py_compile` passes)
- ✅ All required imports present
- ✅ Both input modes (paste + upload) implemented
- ✅ Preview section and submit button present
- ✅ All dropdowns query database (no hardcoded values)
- ✅ Data provenance locked to "Sensor" (ID=1) - other provenances use different pages

## Files Modified

| File | Change |
|------|--------|
| `app/pages/9_Sensor_Ingest.py` | Created - scalar sensor ingest page |
| `api/v1/repositories/lookup_repository.py` | Added `get_data_provenance_lookup()` and `get_data_provenance_by_id()` |
| `api/v1/endpoints/ingest.py` | Added `/lookup/data-provenance` endpoint |
| `app/api_client.py` | Added `list_data_provenance_lookup()` function |

## Deviations from Plan

None - plan executed as written with the addition of making all dropdown values database-driven (including Data Provenance display name and Processing Degree options).

## Next Steps

Ready for Phase 04 Plan 06: Vector/Matrix sensor ingest modes (to be added to same page with tabs).

---
*Completed: 2026-03-05*
