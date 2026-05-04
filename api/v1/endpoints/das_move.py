"""DAS deployment endpoints.

Tracks which site a Data Acquisition System is physically located at over
time, using the DASLocationHistory table.

Endpoints:
  POST /das/{das_id}/deploy          — close current deployment + open new one
  GET  /das/{das_id}/active-deployment — return active deployment row (or empty)
  GET  /das/{das_id}/conflict-check  — return conflict if DAS is at a different site
"""

from __future__ import annotations

import pyodbc
from fastapi import APIRouter, Depends, HTTPException

from api.database import get_db
from ..repositories import temporal_history_repository
from ..schemas.das_move import (
    DASActiveDeploymentResponse,
    DASConflictResponse,
    DASDeployRequest,
    DASDeployResponse,
)

router = APIRouter()


@router.post(
    "/{das_id}/deploy",
    response_model=DASDeployResponse,
    status_code=201,
)
def deploy_das_endpoint(
    das_id: int,
    body: DASDeployRequest,
    conn=Depends(get_db),
):
    """Record that a DAS has been deployed to a site.

    Closes any currently active DASLocationHistory row (if any) and opens a
    new one.  Safe to call when the DAS has never been deployed before.
    """
    try:
        new_id, closed_id = temporal_history_repository.deploy_das(
            conn,
            das_id=das_id,
            site_id=body.site_id,
            valid_from=body.valid_from,
            campaign_id=body.campaign_id,
            notes=body.notes,
        )
    except pyodbc.IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail=(
                f"Could not open a new deployment row for DAS {das_id}: "
                "a concurrent active row already exists. "
                f"Database error: {exc}"
            ),
        ) from exc

    return DASDeployResponse(
        das_id=das_id,
        new_history_id=new_id,
        closed_history_id=closed_id,
    )


@router.get(
    "/{das_id}/active-deployment",
    response_model=DASActiveDeploymentResponse,
)
def get_active_deployment_endpoint(
    das_id: int,
    conn=Depends(get_db),
):
    """Return the currently active deployment for a DAS, or an empty response."""
    row = temporal_history_repository.get_active_das_deployment(conn, das_id)
    if row is None:
        return DASActiveDeploymentResponse(
            das_id=das_id,
            history_id=None,
            site_id=None,
            site_name=None,
            campaign_id=None,
            campaign_name=None,
            valid_from=None,
            valid_to=None,
            notes=None,
        )
    return DASActiveDeploymentResponse(
        das_id=das_id,
        history_id=row["history_id"],
        site_id=row["site_id"],
        site_name=row.get("site_name"),
        campaign_id=row.get("campaign_id"),
        campaign_name=row.get("campaign_name"),
        valid_from=row["valid_from"],
        valid_to=row["valid_to"],
        notes=row.get("notes"),
    )


@router.get(
    "/{das_id}/conflict-check",
    response_model=DASConflictResponse,
)
def conflict_check_endpoint(
    das_id: int,
    site_id: int,
    conn=Depends(get_db),
):
    """Check whether a DAS is currently active at a *different* site.

    Returns ``conflict: false`` when:
    - The DAS has no active deployment, OR
    - The active deployment is already at ``site_id`` (shared use is fine).

    Returns ``conflict: true`` when the DAS is actively deployed at a
    different site — the wizard should show a warning.
    """
    conflict = temporal_history_repository.get_das_conflict(conn, das_id, site_id)
    if conflict is None:
        return DASConflictResponse(
            das_id=das_id,
            site_id=site_id,
            conflict=False,
            conflicting_site_id=None,
            conflicting_site_name=None,
            conflicting_campaign_id=None,
            conflicting_campaign_name=None,
        )
    return DASConflictResponse(
        das_id=das_id,
        site_id=site_id,
        conflict=True,
        conflicting_site_id=conflict["site_id"],
        conflicting_site_name=conflict.get("site_name"),
        conflicting_campaign_id=conflict.get("campaign_id"),
        conflicting_campaign_name=conflict.get("campaign_name"),
    )
