"""Lab ingest endpoints — experiments, series, and template lookup/CRUD.

These complement the main lab ingestion POST in :mod:`api.v1.endpoints.ingest`
by providing the lookup and management endpoints the UI needs.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.database import get_db
from ..repositories import ingestion_repository
from ..schemas.ingestion import (
    AnalysisSeriesCreateRequest,
    AnalysisSeriesLookupItem,
    LabExperimentLookupItem,
    LabPanelCreateRequest,
    LabPanelDetailResponse,
    LabPanelPatchRequest,
    LabPanelResponse,
    LabPanelSeriesAddRequest,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Experiments
# ---------------------------------------------------------------------------


@router.get(
    "/experiments/lookup",
    response_model=list[LabExperimentLookupItem],
)
def list_lab_experiments_lookup(conn=Depends(get_db)):
    """Return recent LabExperiments for dropdown (top 50, newest first)."""
    return ingestion_repository.list_lab_experiments_lookup(conn)


@router.get(
    "/experiments/{lab_experiment_id}/series",
    response_model=list[AnalysisSeriesLookupItem],
)
def get_lab_experiment_series(
    lab_experiment_id: int, conn=Depends(get_db)
):
    """Return distinct AnalysisSeries used in a LabExperiment."""
    return ingestion_repository.get_lab_experiment_series(
        conn, lab_experiment_id
    )


# ---------------------------------------------------------------------------
# AnalysisSeries
# ---------------------------------------------------------------------------


@router.get(
    "/analysis-series/lookup",
    response_model=list[AnalysisSeriesLookupItem],
)
def list_analysis_series_lookup(conn=Depends(get_db)):
    """Return all AnalysisSeries for dropdown."""
    return ingestion_repository.list_analysis_series_lookup(conn)


@router.post("/analysis-series", status_code=201)
def create_analysis_series(
    body: AnalysisSeriesCreateRequest, conn=Depends(get_db)
):
    """Create a new AnalysisSeries. Raises 409 if duplicate identity exists.

    The identity constraint is (Parameter_ID, SamplingPoint_ID, ValueKind_ID, ProcessingKind_ID).
    """
    try:
        series_id = ingestion_repository.create_analysis_series(
            conn,
            parameter_id=body.parameter_id,
            sampling_point_id=body.sampling_point_id,
            unit_id=body.unit_id,
            value_kind_id=body.value_kind_id,
            processing_kind_id=body.processing_kind_id,
            name=body.name,
        )
        return {"analysis_series_id": series_id}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


@router.get(
    "/templates",
    response_model=list[LabPanelResponse],
)
def list_lab_panels(conn=Depends(get_db)):
    """Return all panels with series count."""
    return ingestion_repository.list_lab_panels(conn)


@router.get(
    "/templates/{template_id}",
    response_model=LabPanelDetailResponse,
)
def get_lab_panel(
    template_id: int, conn=Depends(get_db)
):
    """Return a template with its full series list."""
    series = ingestion_repository.get_template_series(conn, template_id)
    if not series:
        # Check if the template itself exists
        templates = ingestion_repository.list_lab_panels(conn)
        t = next(
            (t for t in templates if t["lab_panel_id"] == template_id),
            None,
        )
        if t is None:
            raise HTTPException(
                status_code=404,
                detail=f"Template {template_id} not found.",
            )
        # Template exists but has no series yet
        return LabPanelDetailResponse(
            lab_panel_id=template_id,
            name=t["name"],
            description=t["description"],
            default_sample_collection_kind_id=t.get("default_sample_collection_kind_id"),
            default_sample_equipment_id=t.get("default_sample_equipment_id"),
            series=[],
        )
    # Reconstruct template metadata from first series lookup
    templates = ingestion_repository.list_lab_panels(conn)
    t = next(
        (t for t in templates if t["lab_panel_id"] == template_id),
        None,
    )
    if t is None:
        raise HTTPException(
            status_code=404,
            detail=f"Template {template_id} not found.",
        )
    return LabPanelDetailResponse(
        lab_panel_id=template_id,
        name=t["name"],
        description=t["description"],
        default_sample_collection_kind_id=t.get("default_sample_collection_kind_id"),
        default_sample_equipment_id=t.get("default_sample_equipment_id"),
        series=[AnalysisSeriesLookupItem(**s) for s in series],
    )


@router.patch("/templates/{template_id}", response_model=LabPanelResponse)
def patch_lab_panel(
    template_id: int, body: LabPanelPatchRequest, conn=Depends(get_db)
):
    """Partial update of a LabPanel. If series_ids is included, replaces the full list."""
    result = ingestion_repository.patch_lab_panel(
        conn, template_id, body.model_dump(exclude_unset=True)
    )
    if result is None:
        raise HTTPException(status_code=404, detail=f"Panel {template_id} not found.")
    return result


@router.post("/templates", status_code=201)
def create_lab_panel(
    body: LabPanelCreateRequest, conn=Depends(get_db)
):
    """Create a template with its series in one transaction."""
    template_id = ingestion_repository.create_lab_panel(
        conn,
        name=body.name,
        description=body.description,
        created_by_person_id=body.created_by_person_id,
        default_sample_collection_kind_id=body.default_sample_collection_kind_id,
        default_sample_equipment_id=body.default_sample_equipment_id,
        series_ids=body.series_ids,
    )
    return {"lab_panel_id": template_id}


@router.post("/templates/{template_id}/series", status_code=201)
def add_series_to_template(
    template_id: int,
    body: LabPanelSeriesAddRequest,
    conn=Depends(get_db),
):
    """Add an AnalysisSeries to a template."""
    ingestion_repository.add_series_to_template(
        conn, template_id, body.analysis_series_id
    )
    return {"status": "ok"}


@router.delete(
    "/templates/{template_id}/series/{analysis_series_id}",
    status_code=204,
)
def remove_series_from_template(
    template_id: int,
    analysis_series_id: int,
    conn=Depends(get_db),
):
    """Remove an AnalysisSeries from a template."""
    ingestion_repository.remove_series_from_template(
        conn, template_id, analysis_series_id
    )


@router.delete("/templates/{template_id}", status_code=204)
def delete_lab_panel(template_id: int, conn=Depends(get_db)):
    """Delete a LabPanel and all its series rows. Returns 404 if not found."""
    panels = ingestion_repository.list_lab_panels(conn)
    if not any(p["lab_panel_id"] == template_id for p in panels):
        raise HTTPException(status_code=404, detail=f"Panel {template_id} not found.")
    ingestion_repository.delete_lab_panel(conn, template_id)