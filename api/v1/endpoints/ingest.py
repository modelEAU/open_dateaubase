"""Data ingestion endpoints.

Four paths:
  POST /ingest/sensor    — raw sensor data, channel resolved/created via stream identity
  POST /ingest/sensor-vector — vector sensor data (spectral/distribution)
  POST /ingest/sensor-matrix — matrix sensor data (2D distribution)
  POST /ingest/sensor-image — image sensor data with file upload
  POST /ingest/lab       — lab analysis data (LabExperiment + AnalysisSeries + LabAnalysis + Observation)
  POST /ingest/processed — processed data with lineage tracking
"""

from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

import logging

from api.config import settings
from api.database import get_db
from ..repositories import (
    channel_repository,
    ingestion_repository,
    lookup_repository,
    signal_interface_repository,
    value_repository,
)
from ..schemas.ingestion import (
    ChannelResolveResponse,
    ImageIngestResponse,
    IngestResponse,
    LabImageIngestResponse,
    LabIngestRequest,
    LabIngestResponse,
    MatrixSensorIngestRequest,
    ProcessedIngestRequest,
    SampleCreateRequest,
    SampleCreateResponse,
    SensorChannelResolveRequest,
    SensorIngestRequest,
    TaglessSensorChannelResolveRequest,
    TaglessSensorIngestRequest,
    TaglessVectorSensorIngestRequest,
    VectorSensorIngestRequest,
)
from ..services import lineage_service

logger = logging.getLogger(__name__)

# Try to import Pillow, but make it optional
try:
    from PIL import Image as PILImage

    PILLOW_AVAILABLE = True
except ImportError:
    PILImage = None
    PILLOW_AVAILABLE = False

router = APIRouter()


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------


def _resolve_tag_inputs(
    conn,
    das_name: str,
    tag: str,
    channel_kind: str,
    parameter_name: str,
    unit_name: str,
    strict: bool = False,
) -> tuple[int, str, int, int, int, list[str]]:
    """Validate names and resolve to IDs.  Returns (signal_interface_id, tag_name, parameter_id, unit_id, channel_kind_id, warnings).

    Raises HTTP 422 for unrecognised channel_kind, parameter, or unit — *before* any DB writes.
    When strict=True, also raises 422 for unknown DAS or SignalInterface instead of auto-creating.
    """
    # --- Validation-only lookups first (no writes) ---
    channel_kind_id = signal_interface_repository.find_channel_kind_by_name(
        conn, channel_kind
    )
    if channel_kind_id is None:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown channel_kind {channel_kind!r}. "
            "Valid values: value, status, alarm, uncertainty.",
        )

    param_id = signal_interface_repository.find_parameter_by_name(conn, parameter_name)
    if param_id is None:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown parameter_name {parameter_name!r}. "
            "Add the parameter to the Parameter table before ingesting.",
        )

    unit_id = signal_interface_repository.find_unit_by_name(conn, unit_name)
    if unit_id is None:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown unit_name {unit_name!r}. "
            "Add the unit to the Unit table before ingesting.",
        )

    # --- DAS resolution ---
    collected_warnings: list[str] = []

    if strict:
        das_id = signal_interface_repository.find_das_by_name(conn, das_name)
        if das_id is None:
            raise HTTPException(
                status_code=422,
                detail=f"DataAcquisitionSystem {das_name!r} not found. "
                "Select an existing DAS or disable strict mode.",
            )
    else:
        das_id, das_created = signal_interface_repository.find_or_create_das(conn, das_name)
        if das_created:
            msg = f"DataAcquisitionSystem {das_name!r} was not found and has been auto-created (ID={das_id})."
            logger.warning(msg)
            collected_warnings.append(msg)

    # --- SignalInterface resolution ---
    signal_interface_id = signal_interface_repository.find_signal_interface_by_das_and_name(
        conn, das_id, tag
    )
    if signal_interface_id is None:
        if strict:
            raise HTTPException(
                status_code=422,
                detail=f"SignalInterface (tag) {tag!r} not found in DAS {das_name!r}. "
                "Select an existing tag or disable strict mode.",
            )
        signal_interface_id, signal_interface_created = (
            signal_interface_repository.find_or_create_signal_interface(
                conn, das_id, tag
            )
        )
        if signal_interface_created:
            msg = (
                f"SignalInterface name={tag!r} (DAS={das_name!r}) was not found and has been "
                f"auto-created (ID={signal_interface_id})."
            )
            logger.warning(msg)
            collected_warnings.append(msg)

    return (
        signal_interface_id,
        tag,
        param_id,
        unit_id,
        channel_kind_id,
        collected_warnings,
    )


def _resolve_tagless_inputs(
    conn,
    das_name: str,
    equipment_name: str,
    parameter_name: str,
    unit_name: str,
    strict: bool = False,
) -> tuple[int, str, int, int, list[str]]:
    """Validate names and resolve tagless ingest inputs to IDs.

    Returns (signal_interface_id, tag_name, parameter_id, unit_id, warnings).

    Raises HTTP 422 for unrecognised parameter_name or unit_name — before any DB writes.
    When strict=True, also raises 422 for unknown DAS or Equipment instead of auto-creating.
    """
    # --- Validation-only lookups first (no writes) ---
    param_id = signal_interface_repository.find_parameter_by_name(conn, parameter_name)
    if param_id is None:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown parameter_name {parameter_name!r}. "
            "Add the parameter to the Parameter table before ingesting.",
        )

    unit_id = signal_interface_repository.find_unit_by_name(conn, unit_name)
    if unit_id is None:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown unit_name {unit_name!r}. "
            "Add the unit to the Unit table before ingesting.",
        )

    # --- DAS resolution ---
    collected_warnings: list[str] = []

    if strict:
        das_id = signal_interface_repository.find_das_by_name(conn, das_name)
        if das_id is None:
            raise HTTPException(
                status_code=422,
                detail=f"DataAcquisitionSystem {das_name!r} not found. "
                "Select an existing DAS or disable strict mode.",
            )
    else:
        das_id, das_created = signal_interface_repository.find_or_create_das(conn, das_name)
        if das_created:
            msg = f"DataAcquisitionSystem {das_name!r} was not found and has been auto-created (ID={das_id})."
            logger.warning(msg)
            collected_warnings.append(msg)

    # --- Equipment resolution ---
    equip_id, equip_created = (
        signal_interface_repository.find_or_create_equipment_by_identifier(
            conn, equipment_name
        )
    )
    if equip_created:
        if strict:
            raise HTTPException(
                status_code=422,
                detail=f"Equipment {equipment_name!r} not found. "
                "Select an existing equipment or disable strict mode.",
            )
        msg = (
            f"Equipment identifier={equipment_name!r} was not found and has been "
            f"auto-created (ID={equip_id})."
        )
        logger.warning(msg)
        collected_warnings.append(msg)

    # Resolve SignalInterface via active EquipmentWiringHistory, or create one.
    wiring = signal_interface_repository.find_active_equipment_wiring(conn, equip_id)
    signal_interface_id: int | None = None
    if wiring is not None:
        signal_interface_id = wiring[0]

    signal_interface_created = False
    if signal_interface_id is None:
        synthetic_interface_name = signal_interface_repository.generate_tagless_tagname(
            equipment_name, parameter_name
        )
        signal_interface_id, signal_interface_created = (
            signal_interface_repository.find_or_create_signal_interface(
                conn, das_id, synthetic_interface_name
            )
        )
        if signal_interface_created:
            msg = (
                f"SignalInterface name={synthetic_interface_name!r} (DAS={das_name!r}) was not found "
                f"and has been auto-created (ID={signal_interface_id})."
            )
            logger.warning(msg)
            collected_warnings.append(msg)
        # Open wiring history so provenance is recorded at ingest time.
        signal_interface_repository.open_equipment_wiring_history(
            conn, equip_id, signal_interface_id, None
        )

    synthetic_tag = signal_interface_repository.generate_tagless_tagname(
        equipment_name, parameter_name
    )

    return signal_interface_id, synthetic_tag, param_id, unit_id, collected_warnings


# ---------------------------------------------------------------------------
# Lookup endpoints (for form dropdowns)
# ---------------------------------------------------------------------------


@router.get("/lookup/units")
def get_units_lookup(conn=Depends(get_db)):
    """Return units list for dropdowns."""
    return lookup_repository.get_units_lookup(conn)


@router.post("/lookup/units", status_code=201)
def create_unit(body: dict, conn=Depends(get_db)):
    """Create a new unit."""
    unit_name = (body.get("unit") or "").strip()
    if not unit_name:
        raise HTTPException(status_code=422, detail="unit field is required")
    return lookup_repository.insert_unit(
        conn,
        unit_name,
        qudt_iri=body.get("qudt_iri"),
        unit_vector=body.get("unit_vector"),
    )


@router.put("/lookup/units/{unit_id}")
def update_unit(unit_id: int, body: dict, conn=Depends(get_db)):
    """Update a unit."""
    unit_name = (body.get("unit") or "").strip()
    if not unit_name:
        raise HTTPException(status_code=422, detail="unit field is required")
    updated = lookup_repository.update_unit(
        conn,
        unit_id,
        unit_name,
        qudt_iri=body.get("qudt_iri"),
        unit_vector=body.get("unit_vector"),
    )
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Unit {unit_id} not found.")
    return updated


@router.delete("/lookup/units/{unit_id}", status_code=204)
def delete_unit(unit_id: int, conn=Depends(get_db)):
    """Delete a unit."""
    if not lookup_repository.delete_unit(conn, unit_id):
        raise HTTPException(status_code=404, detail=f"Unit {unit_id} not found.")


@router.get("/lookup/laboratories")
def get_laboratories_lookup(conn=Depends(get_db)):
    """Return laboratories list for dropdowns."""
    return lookup_repository.get_laboratories_lookup(conn)


@router.post("/lookup/laboratories", status_code=201)
def create_laboratory(body: dict, conn=Depends(get_db)):
    """Create a new laboratory."""
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="name field is required")
    site_id = body.get("site_id") or None
    description = body.get("description") or None
    return lookup_repository.insert_laboratory(conn, name, site_id, description)


@router.put("/lookup/laboratories/{laboratory_id}")
def update_laboratory(laboratory_id: int, body: dict, conn=Depends(get_db)):
    """Update a laboratory."""
    name = (body.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="name field is required")
    site_id = body.get("site_id") or None
    description = body.get("description") or None
    updated = lookup_repository.update_laboratory(
        conn, laboratory_id, name, site_id, description
    )
    if updated is None:
        raise HTTPException(
            status_code=404, detail=f"Laboratory {laboratory_id} not found."
        )
    return updated


@router.delete("/lookup/laboratories/{laboratory_id}", status_code=204)
def delete_laboratory(laboratory_id: int, conn=Depends(get_db)):
    """Delete a laboratory."""
    if not lookup_repository.delete_laboratory(conn, laboratory_id):
        raise HTTPException(
            status_code=404, detail=f"Laboratory {laboratory_id} not found."
        )


@router.get("/lookup/procedures")
def get_procedures_lookup(conn=Depends(get_db)):
    """Return procedures list for dropdowns."""
    return lookup_repository.get_procedures_lookup(conn)


@router.get("/lookup/samples")
def get_samples_lookup(conn=Depends(get_db)):
    """Return samples list for dropdowns (most recent first)."""
    return lookup_repository.get_samples_lookup(conn)


@router.get("/lookup/sampling-points")
def get_sampling_points_lookup(conn=Depends(get_db)):
    """Return sampling points list for dropdowns."""
    return lookup_repository.get_sampling_points_lookup(conn)


@router.get("/lookup/equipment-events")
def get_equipment_events_lookup(conn=Depends(get_db)):
    """Return equipment events list for dropdowns."""
    return lookup_repository.get_equipment_events_lookup(conn)


@router.get("/lookup/data-provenance")
def get_data_provenance_lookup(conn=Depends(get_db)):
    """Return data provenance types for dropdowns."""
    return lookup_repository.get_data_provenance_kind_lookup(conn)


@router.get("/lookup/tags")
def get_tags_lookup(das_id: int, conn=Depends(get_db)):
    """Return SignalInterface names (tags) for a DAS. Used by strict-mode dropdowns."""
    return lookup_repository.get_tags_lookup(conn, das_id)


# ---------------------------------------------------------------------------
# Deduplication helper
# ---------------------------------------------------------------------------


@router.get("/last-timestamp")
def get_last_timestamp(
    channel_id: int,
    conn=Depends(get_db),
):
    """Return the most-recent ingested Timestamp for a sensor channel.

    Used by the table-import CLI for watermark-based deduplication.
    Returns {"last_timestamp": "<ISO 8601>" | null}.
    """
    ts = ingestion_repository.get_last_timestamp_for_channel(
        conn, channel_id=channel_id
    )
    return {"last_timestamp": ts.isoformat() if ts is not None else None}


# ---------------------------------------------------------------------------
# Ingest endpoints
# ---------------------------------------------------------------------------


@router.post("/resolve-channel", response_model=ChannelResolveResponse, status_code=200)
def resolve_channel(data: SensorChannelResolveRequest, conn=Depends(get_db)):
    """Resolve (or create) a tagged sensor channel without writing any values.

    Runs the same validation and find-or-create logic as POST /ingest/sensor steps 1–3,
    then returns the channel_id.  Use this to pre-resolve channels before bulk ingestion.
    """
    (
        signal_interface_id,
        tag_name,
        param_id,
        unit_id,
        channel_kind_id,
        warnings,
    ) = _resolve_tag_inputs(
        conn,
        das_name=data.das_name,
        tag=data.tag,
        channel_kind=data.channel_kind,
        parameter_name=data.parameter_name,
        unit_name=data.unit_name,
    )

    parent_channel_id = None
    if data.parent_tag is not None:
        parent_si_id = (
            signal_interface_repository.find_signal_interface_by_das_and_name(
                conn, signal_interface_id, data.parent_tag
            )
        )
        if parent_si_id is None:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"parent_tag {data.parent_tag!r} not found in DAS {data.das_name!r}. "
                    "The parent signal interface must exist before creating a sub-signal."
                ),
            )
        parent_channel = channel_repository.find_channel_by_identity(
            conn,
            signal_interface_id=parent_si_id,
            tag_name=data.parent_tag,
            parameter_id=param_id,
            data_provenance_id=data.data_provenance_kind_id,
        )
        if parent_channel is None:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"parent_tag {data.parent_tag!r} found as SignalInterface but no matching "
                    f"Channel exists for parameter={data.parameter_name!r}, provenance={data.data_provenance_kind_id}."
                ),
            )
        parent_channel_id = parent_channel["channel_id"]

    channel_id = ingestion_repository.find_or_create_sensor_metadata(
        conn,
        signal_interface_id=signal_interface_id,
        tag_name=tag_name,
        parameter_id=param_id,
        unit_id=unit_id,
        data_provenance_id=data.data_provenance_kind_id,
        value_kind_id=data.value_kind_id,
        channel_kind_id=channel_kind_id,
        parent_channel_id=parent_channel_id,
    )
    return ChannelResolveResponse(channel_id=channel_id, warnings=warnings)


@router.post(
    "/resolve-channel-tagless", response_model=ChannelResolveResponse, status_code=200
)
def resolve_channel_tagless(
    data: TaglessSensorChannelResolveRequest, conn=Depends(get_db)
):
    """Resolve (or create) a tagless sensor channel without writing any values.

    Runs the same validation and find-or-create logic as POST /ingest/sensor-tagless steps 1–3,
    then returns the channel_id.  Use this to pre-resolve channels before bulk ingestion.
    """
    (
        signal_interface_id,
        tag_name,
        param_id,
        unit_id,
        warnings,
    ) = _resolve_tagless_inputs(
        conn,
        das_name=data.das_name,
        equipment_name=data.equipment_name,
        parameter_name=data.parameter_name,
        unit_name=data.unit_name,
    )

    channel_id = ingestion_repository.find_or_create_sensor_metadata(
        conn,
        signal_interface_id=signal_interface_id,
        tag_name=tag_name,
        parameter_id=param_id,
        unit_id=unit_id,
        data_provenance_id=data.data_provenance_kind_id,
        value_kind_id=data.value_kind_id,
    )
    return ChannelResolveResponse(channel_id=channel_id, warnings=warnings)


@router.post("/sensor", response_model=IngestResponse, status_code=201)
def ingest_sensor(data: SensorIngestRequest, conn=Depends(get_db)):
    """Ingest raw sensor measurements.

    Resolves (or creates) the Channel via the UNIQUE stream identity:
    (das_name, tag, parameter_name, data_provenance_kind_id, processing_degree).
    DAS and SignalPort are auto-created with a warning on first encounter.
    Unrecognised parameter_name or unit_name returns 422 before any DB write.
    """
    (
        signal_interface_id,
        tag_name,
        param_id,
        unit_id,
        channel_kind_id,
        ingest_warnings,
    ) = _resolve_tag_inputs(
        conn,
        das_name=data.das_name,
        tag=data.tag,
        channel_kind=data.channel_kind,
        parameter_name=data.parameter_name,
        unit_name=data.unit_name,
        strict=data.strict,
    )

    # --- parent_tag: link sub-signal to parent channel ---
    parent_channel_id = None
    if data.parent_tag is not None:
        parent_si_id = (
            signal_interface_repository.find_signal_interface_by_das_and_name(
                conn, signal_interface_id, data.parent_tag
            )
        )
        if parent_si_id is None:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"parent_tag {data.parent_tag!r} not found in DAS {data.das_name!r}. "
                    "The parent signal interface must exist before creating a sub-signal."
                ),
            )
        parent_channel = channel_repository.find_channel_by_identity(
            conn,
            signal_interface_id=parent_si_id,
            tag_name=data.parent_tag,
            parameter_id=param_id,
            data_provenance_id=data.data_provenance_kind_id,
        )
        if parent_channel is None:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"parent_tag {data.parent_tag!r} found as SignalInterface but no matching "
                    f"Channel exists for parameter={data.parameter_name!r}, provenance={data.data_provenance_kind_id}."
                ),
            )
        parent_channel_id = parent_channel["channel_id"]

    channel_id = ingestion_repository.find_or_create_sensor_metadata(
        conn,
        signal_interface_id=signal_interface_id,
        tag_name=tag_name,
        parameter_id=param_id,
        unit_id=unit_id,
        data_provenance_id=data.data_provenance_kind_id,
        channel_kind_id=channel_kind_id,
        parent_channel_id=parent_channel_id,
    )

    rows = value_repository.insert_scalar_values(
        conn,
        channel_id,
        [v.model_dump() for v in data.values],
    )

    return IngestResponse(
        channel_id=channel_id, rows_written=rows, warnings=ingest_warnings
    )


@router.post("/sensor-tagless", response_model=IngestResponse, status_code=201)
def ingest_sensor_tagless(data: TaglessSensorIngestRequest, conn=Depends(get_db)):
    """Ingest raw sensor measurements from a direct-connect station (no SCADA tag).

    A synthetic SignalPort tag is auto-generated as
    ``"{equipment_name}/{parameter_name}"`` (lowercased, trimmed) — deterministic
    and stable across repeated runs.

    On first ingest a SignalPortEquipmentHistory row is opened immediately so
    provenance is recorded from the start.  Subsequent ingests for the same
    (DAS, equipment_name, parameter_name) are idempotent.

    Unrecognised equipment name produces a warning and auto-creates the
    Equipment record.  Unrecognised parameter_name or unit_name returns 422 before
    any DB write.
    """
    (
        signal_interface_id,
        tag_name,
        param_id,
        unit_id,
        ingest_warnings,
    ) = _resolve_tagless_inputs(
        conn,
        das_name=data.das_name,
        equipment_name=data.equipment_name,
        parameter_name=data.parameter_name,
        unit_name=data.unit_name,
        strict=data.strict,
    )

    channel_id = ingestion_repository.find_or_create_sensor_metadata(
        conn,
        signal_interface_id=signal_interface_id,
        tag_name=tag_name,
        parameter_id=param_id,
        unit_id=unit_id,
        data_provenance_id=data.data_provenance_kind_id,
    )

    rows = value_repository.insert_scalar_values(
        conn,
        channel_id,
        [v.model_dump() for v in data.values],
    )

    return IngestResponse(
        channel_id=channel_id, rows_written=rows, warnings=ingest_warnings
    )


@router.post("/lab", response_model=LabIngestResponse, status_code=201)
def ingest_lab(data: LabIngestRequest, conn=Depends(get_db)):
    """Ingest one LabExperiment session worth of lab measurements.

    Flow (new experiment):
    1. Insert a single ``LabExperiment`` row (the session).
    2. For each measurement: find-or-create its ``AnalysisSeries``,
       insert a ``LabAnalysis`` row, then insert an ``Observation`` routed
       to ``Value`` / ``ValueVector`` / ``ValueMatrix`` based on the
       measurement's ``value_kind_id``.

    Flow (existing experiment — ``experiment_id`` is set):
    1. Verify the ``LabExperiment`` row exists; 404 if not.
    2. Same per-measurement loop, appending to the existing session.
    """
    if data.experiment_id is not None:
        if not ingestion_repository.lab_experiment_exists(conn, data.experiment_id):
            raise HTTPException(
                status_code=404,
                detail=f"LabExperiment {data.experiment_id} not found.",
            )
        lab_experiment_id = data.experiment_id
    else:
        lab_experiment_id = ingestion_repository.insert_lab_experiment(
            conn,
            name=data.name,  # type: ignore[arg-type]  # validated in model_post_init
            experiment_datetime=data.experiment_datetime,  # type: ignore[arg-type]
            campaign_id=data.campaign_id,
            description=data.description,
            created_by_person_id=data.created_by_person_id,
            lab_panel_id=data.lab_panel_id,
        )

    rows = 0
    for item in data.measurements:
        analysis_series_id = ingestion_repository.find_or_create_analysis_series(
            conn,
            parameter_id=item.parameter_id,
            sampling_point_id=item.sampling_point_id,
            value_kind_id=item.value_kind_id,
            processing_kind_id=item.processing_kind_id,
            unit_id=item.unit_id,
            name=item.series_name,
        )

        lab_analysis_id = ingestion_repository.insert_lab_analysis(
            conn,
            lab_experiment_id=lab_experiment_id,
            analysis_series_id=analysis_series_id,
            sample_id=item.sample_id,
            laboratory_id=item.laboratory_id,
            analyst_person_id=item.analyst_person_id,
            procedure_id=item.procedure_id,
            analysis_datetime=item.analysis_datetime,
            replicate=item.replicate,
            quality_code_id=item.quality_code_id,
            notes=item.notes,
        )

        # Observation Timestamp mirrors LabAnalysis.AnalysisDateTime; when the
        # caller omitted it the LabAnalysis row carries the default
        # SYSUTCDATETIME() — re-read it so the Observation row matches.
        if item.analysis_datetime is None:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT [AnalysisDateTime] FROM [dbo].[LabAnalysis] WHERE [LabAnalysis_ID] = ?",
                lab_analysis_id,
            )
            obs_timestamp = cursor.fetchone()[0]
        else:
            obs_timestamp = item.analysis_datetime

        ingestion_repository.insert_lab_observation(
            conn,
            lab_analysis_id=lab_analysis_id,
            analysis_series_id=analysis_series_id,
            timestamp=obs_timestamp,
            value_kind_id=item.value_kind_id,
            value=item.value,
            quality_code=item.quality_code_id,
        )
        rows += 1

    return LabIngestResponse(
        lab_experiment_id=lab_experiment_id, rows_written=rows
    )


@router.post("/lab-image", response_model=LabImageIngestResponse, status_code=201)
def ingest_lab_image(
    name: str = Form(...),
    experiment_datetime: str = Form(...),
    sample_id: int = Form(...),
    parameter_id: int = Form(...),
    sampling_point_id: int = Form(...),
    unit_id: int = Form(...),
    series_name: str = Form(...),
    processing_kind_id: int = Form(1),
    campaign_id: int | None = Form(None),
    description: str | None = Form(None),
    created_by_person_id: int | None = Form(None),
    laboratory_id: int | None = Form(None),
    analyst_person_id: int | None = Form(None),
    procedure_id: int | None = Form(None),
    quality_code: int | None = Form(None),
    notes: str | None = Form(None),
    images: list[UploadFile] = File(...),
    conn=Depends(get_db),
):
    """Ingest one or more lab images (multiple files = replicates of the same measurement).

    Creates a LabExperiment, finds/creates an AnalysisSeries (value_kind_id=4),
    then for each uploaded file creates a LabAnalysis + Observation + ValueImage row.
    Files are stored under {upload_dir}/lab_images/{lab_experiment_id}/.
    """
    try:
        ts = datetime.fromisoformat(experiment_datetime)
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail="experiment_datetime must be ISO format (YYYY-MM-DDTHH:MM:SS)"
        ) from exc

    lab_experiment_id = ingestion_repository.insert_lab_experiment(
        conn,
        name=name,
        experiment_datetime=ts,
        campaign_id=campaign_id,
        description=description,
        created_by_person_id=created_by_person_id,
    )

    analysis_series_id = ingestion_repository.find_or_create_analysis_series(
        conn,
        parameter_id=parameter_id,
        sampling_point_id=sampling_point_id,
        value_kind_id=4,
        processing_kind_id=processing_kind_id,
        unit_id=unit_id,
        name=series_name,
    )

    storage_paths: list[str] = []
    for replicate, img_file in enumerate(images, start=1):
        image_bytes = img_file.file.read()
        file_ext = Path(img_file.filename or "image.bin").suffix.lower().lstrip(".")

        width, height, n_channels = 0, 0, 0
        img_format = file_ext.upper() or "BIN"
        thumbnail_bytes = None

        if PILLOW_AVAILABLE:
            try:
                pil_img = PILImage.open(io.BytesIO(image_bytes))
                width, height = pil_img.size
                n_channels = len(pil_img.getbands())
                img_format = pil_img.format or img_format
                thumb = pil_img.copy()
                thumb.thumbnail((400, 400))
                thumb_buf = io.BytesIO()
                thumb.convert("RGB").save(thumb_buf, format="JPEG", quality=85)
                thumbnail_bytes = thumb_buf.getvalue()
            except Exception:
                pass

        lab_analysis_id = ingestion_repository.insert_lab_analysis(
            conn,
            lab_experiment_id=lab_experiment_id,
            analysis_series_id=analysis_series_id,
            sample_id=sample_id,
            laboratory_id=laboratory_id,
            analyst_person_id=analyst_person_id,
            procedure_id=procedure_id,
            replicate=replicate,
            quality_code_id=quality_code,
            notes=notes,
        )

        ts_safe = ts.isoformat().replace(":", "-")
        rel_path = f"lab_images/{lab_experiment_id}/{replicate}_{ts_safe}.{file_ext}"
        abs_path = Path(settings.upload_dir) / "lab_images" / str(lab_experiment_id) / f"{replicate}_{ts_safe}.{file_ext}"
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        abs_path.write_bytes(image_bytes)

        value_repository.insert_lab_image_value(
            conn,
            lab_analysis_id=lab_analysis_id,
            timestamp=ts,
            image_width=width,
            image_height=height,
            number_of_channels=n_channels,
            image_format=img_format,
            file_size_bytes=len(image_bytes),
            storage_path=rel_path,
            quality_code=quality_code,
            thumbnail=thumbnail_bytes,
        )
        storage_paths.append(rel_path)

    return LabImageIngestResponse(
        lab_experiment_id=lab_experiment_id,
        rows_written=len(images),
        storage_paths=storage_paths,
    )


@router.post("/processed", response_model=IngestResponse, status_code=201)
def ingest_processed(data: ProcessedIngestRequest, conn=Depends(get_db)):
    """Ingest processed data with full lineage tracking.

    Creates the ProcessingStep first (to get its ID), then finds or creates
    the output Channel with ProducedByStep_ID set, writes values, and records
    the ProcessingLineage input edges.
    """
    if not data.source_channel_ids:
        raise HTTPException(
            status_code=400, detail="source_channel_ids must not be empty."
        )

    primary_source_id = data.source_channel_ids[0]

    step_id = lineage_service.persist_processing(
        conn,
        source_metadata_ids=data.source_channel_ids,
        method_name=data.processing.method_name,
        method_version=data.processing.method_version,
        processing_kind_id=data.processing.processing_kind_id,
        method_parameters=data.processing.method_parameters,
        executed_at=data.processing.executed_at,
        executed_by_person_id=data.processing.executed_by_person_id,
    )

    output_channel_id = ingestion_repository.find_or_create_derived_metadata(
        conn,
        source_channel_id=primary_source_id,
        produced_by_step_id=step_id,
    )

    rows = value_repository.insert_scalar_values(
        conn,
        output_channel_id,
        [v.model_dump() for v in data.output.values],
    )

    return IngestResponse(
        channel_id=output_channel_id,
        rows_written=rows,
        processing_step_id=step_id,
    )


@router.post("/sensor-vector", response_model=IngestResponse, status_code=201)
def ingest_sensor_vector(data: VectorSensorIngestRequest, conn=Depends(get_db)):
    """Ingest vector sensor data (spectral or distribution measurements).

    Each observation contains a timestamp and an array of bin values.
    Channel is resolved/created with value_kind_id=2 (Vector).
    """
    (
        signal_interface_id,
        tag_name,
        param_id,
        unit_id,
        channel_kind_id,
        ingest_warnings,
    ) = _resolve_tag_inputs(
        conn,
        das_name=data.das_name,
        tag=data.tag,
        channel_kind=data.channel_kind,
        parameter_name=data.parameter_name,
        unit_name=data.unit_name,
        strict=data.strict,
    )

    channel_id = ingestion_repository.find_or_create_sensor_metadata(
        conn,
        signal_interface_id=signal_interface_id,
        tag_name=tag_name,
        parameter_id=param_id,
        unit_id=unit_id,
        data_provenance_id=data.data_provenance_kind_id,
        value_kind_id=2,
        channel_kind_id=channel_kind_id,
    )
    ingestion_repository.upsert_channel_axis(
        conn, channel_id, axis_role=0, binning_axis_id=data.binning_axis_id
    )
    observations = [o.model_dump() for o in data.observations]
    rows = value_repository.insert_vector_values(
        conn, channel_id, data.binning_axis_id, observations
    )
    return IngestResponse(
        channel_id=channel_id, rows_written=rows, warnings=ingest_warnings
    )


@router.post("/sensor-vector-tagless", response_model=IngestResponse, status_code=201)
def ingest_sensor_vector_tagless(data: TaglessVectorSensorIngestRequest, conn=Depends(get_db)):
    """Ingest vector sensor data from a direct-connect station (no SCADA tag).

    Uses the same equipment-based channel resolution as /sensor-tagless, but
    creates a Vector channel (value_kind_id=2) and stores bin values.
    """
    (
        signal_interface_id,
        tag_name,
        param_id,
        unit_id,
        ingest_warnings,
    ) = _resolve_tagless_inputs(
        conn,
        das_name=data.das_name,
        equipment_name=data.equipment_name,
        parameter_name=data.parameter_name,
        unit_name=data.unit_name,
        strict=data.strict,
    )

    channel_id = ingestion_repository.find_or_create_sensor_metadata(
        conn,
        signal_interface_id=signal_interface_id,
        tag_name=tag_name,
        parameter_id=param_id,
        unit_id=unit_id,
        data_provenance_id=data.data_provenance_kind_id,
        value_kind_id=2,
    )
    ingestion_repository.upsert_channel_axis(
        conn, channel_id, axis_role=0, binning_axis_id=data.binning_axis_id
    )
    observations = [o.model_dump() for o in data.observations]
    rows = value_repository.insert_vector_values(
        conn, channel_id, data.binning_axis_id, observations
    )
    return IngestResponse(
        channel_id=channel_id, rows_written=rows, warnings=ingest_warnings
    )


@router.post("/sensor-matrix", response_model=IngestResponse, status_code=201)
def ingest_sensor_matrix(data: MatrixSensorIngestRequest, conn=Depends(get_db)):
    """Ingest matrix sensor data (2D distribution measurements).

    Each observation contains a timestamp and a 2D matrix of values.
    Channel is resolved/created with value_kind_id=3 (Matrix).
    """
    (
        signal_interface_id,
        tag_name,
        param_id,
        unit_id,
        channel_kind_id,
        ingest_warnings,
    ) = _resolve_tag_inputs(
        conn,
        das_name=data.das_name,
        tag=data.tag,
        channel_kind=data.channel_kind,
        parameter_name=data.parameter_name,
        unit_name=data.unit_name,
        strict=data.strict,
    )

    channel_id = ingestion_repository.find_or_create_sensor_metadata(
        conn,
        signal_interface_id=signal_interface_id,
        tag_name=tag_name,
        parameter_id=param_id,
        unit_id=unit_id,
        data_provenance_id=data.data_provenance_kind_id,
        value_kind_id=3,
        channel_kind_id=channel_kind_id,
    )
    ingestion_repository.upsert_channel_axis(
        conn, channel_id, axis_role=0, binning_axis_id=data.row_axis_id
    )
    ingestion_repository.upsert_channel_axis(
        conn, channel_id, axis_role=1, binning_axis_id=data.col_axis_id
    )
    observations = [o.model_dump() for o in data.observations]
    rows = value_repository.insert_matrix_values(
        conn, channel_id, data.row_axis_id, data.col_axis_id, observations
    )
    return IngestResponse(
        channel_id=channel_id, rows_written=rows, warnings=ingest_warnings
    )


@router.post("/sensor-image", response_model=ImageIngestResponse, status_code=201)
def ingest_sensor_image(
    das_name: str = Form(...),
    tag: str | None = Form(None),
    equipment_name: str | None = Form(None),
    channel_kind: str = Form("value"),
    parameter_name: str = Form(...),
    unit_name: str = Form(...),
    timestamp: str = Form(...),  # ISO datetime string
    quality_code: int | None = Form(None),
    data_provenance_kind_id: int = Form(1),
    image: UploadFile = File(...),
    conn=Depends(get_db),
):
    """Ingest an image file from a sensor.

    Supports both tagged (tag) and tagless (equipment_name) channel resolution.
    Saves the file to disk and stores metadata in ValueImage table.
    Creates/uses a channel with value_kind_id=4 (Image).
    """
    if tag is None and equipment_name is None:
        raise HTTPException(
            status_code=422, detail="Either 'tag' or 'equipment_name' must be provided."
        )

    # 1. Parse timestamp
    try:
        ts = datetime.fromisoformat(timestamp)
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail="timestamp must be ISO format (YYYY-MM-DDTHH:MM:SS)"
        ) from exc

    # 2. Read image bytes
    image_bytes = image.file.read()
    file_ext = Path(image.filename).suffix.lower().lstrip(".") or "bin"

    # 3. Get image metadata using Pillow
    width, height, n_channels = 0, 0, 0
    img_format = file_ext.upper()
    thumbnail_bytes = None

    if PILLOW_AVAILABLE:
        try:
            pil_img = PILImage.open(io.BytesIO(image_bytes))
            width, height = pil_img.size
            n_channels = len(pil_img.getbands())
            img_format = pil_img.format or file_ext.upper()
            # Generate thumbnail (400x400 max, JPEG bytes)
            thumb = pil_img.copy()
            thumb.thumbnail((400, 400))
            thumb_buf = io.BytesIO()
            thumb.convert("RGB").save(thumb_buf, format="JPEG", quality=85)
            thumbnail_bytes = thumb_buf.getvalue()
        except Exception:
            # Pillow failed — store without metadata
            pass

    # 4. Resolve channel (tagged or tagless) and find/create (value_kind_id=4 = Image)
    if tag is not None:
        (
            signal_interface_id,
            tag_name,
            param_id,
            unit_id,
            channel_kind_id,
            _,
        ) = _resolve_tag_inputs(
            conn,
            das_name=das_name,
            tag=tag,
            channel_kind=channel_kind,
            parameter_name=parameter_name,
            unit_name=unit_name,
        )
    else:
        assert equipment_name is not None
        (
            signal_interface_id,
            tag_name,
            param_id,
            unit_id,
            _,
        ) = _resolve_tagless_inputs(
            conn,
            das_name=das_name,
            equipment_name=equipment_name,
            parameter_name=parameter_name,
            unit_name=unit_name,
        )
        channel_kind_id = (
            signal_interface_repository.find_channel_kind_by_name(conn, "value") or 1
        )
    channel_id = ingestion_repository.find_or_create_sensor_metadata(
        conn,
        signal_interface_id=signal_interface_id,
        tag_name=tag_name,
        parameter_id=param_id,
        unit_id=unit_id,
        data_provenance_id=data_provenance_kind_id,
        value_kind_id=4,
        channel_kind_id=channel_kind_id,
    )

    # 5. Save file to disk
    ts_safe = ts.isoformat().replace(":", "-")
    rel_path = f"images/{channel_id}/{ts_safe}.{file_ext}"
    abs_path = Path(settings.upload_dir) / str(channel_id) / f"{ts_safe}.{file_ext}"
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_bytes(image_bytes)

    # 6. Insert DB record
    value_image_id = value_repository.insert_image_value(
        conn,
        channel_id=channel_id,
        timestamp=ts,
        image_width=width,
        image_height=height,
        number_of_channels=n_channels,
        image_format=img_format,
        file_size_bytes=len(image_bytes),
        storage_path=rel_path,
        quality_code=quality_code,
        thumbnail=thumbnail_bytes,
    )

    return ImageIngestResponse(
        channel_id=channel_id,
        value_image_id=value_image_id,
        storage_path=rel_path,
    )


@router.post("/samples", response_model=SampleCreateResponse, status_code=201)
def create_sample(data: SampleCreateRequest, conn=Depends(get_db)):
    """Create a new sample and return its ID."""
    sample_id = ingestion_repository.insert_sample(
        conn,
        sampling_point_id=data.sampling_point_id,
        sampled_by_person_id=data.sampled_by_person_id,
        campaign_id=data.campaign_id,
        sample_datetime_start=data.sample_datetime_start,
        sample_datetime_end=data.sample_datetime_end,
        sample_collection_kind_id=data.sample_collection_kind_id,
        sample_equipment_id=data.sample_equipment_id,
        description=data.description,
    )
    return SampleCreateResponse(sample_id=sample_id)
