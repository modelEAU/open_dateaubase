"""Campaign endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from api.database import get_db
from ..repositories import campaign_repository
from ..repositories import lookup_repository
from ..schemas.campaigns import (
    CampaignContextOut,
    CampaignIn,
    CampaignOut,
    CampaignOverviewOut,
    CampaignPatch,
    CampaignKindOut,
    DeploymentCreateIn,
    DeploymentCreateOut,
    DeploymentOut,
)
from ..schemas.metadata import CampaignKindIn

router = APIRouter()


@router.get("", response_model=list[CampaignOut])
def list_campaigns(
    site_id: int | None = Query(None),
    campaign_kind_id: int | None = Query(None),
    conn=Depends(get_db),
):
    """Return all campaigns, optionally filtered by site or type."""
    return campaign_repository.list_campaigns(
        conn, site_id=site_id, campaign_kind_id=campaign_kind_id
    )


@router.post("", response_model=CampaignOut, status_code=201)
def create_campaign(body: CampaignIn, conn=Depends(get_db)):
    return campaign_repository.insert_campaign(conn, body.model_dump())


@router.put("/{campaign_id}", response_model=CampaignOut)
def update_campaign(campaign_id: int, body: CampaignIn, conn=Depends(get_db)):
    updated = campaign_repository.update_campaign(conn, campaign_id, body.model_dump())
    if updated is None:
        raise HTTPException(
            status_code=404, detail=f"Campaign {campaign_id} not found."
        )
    return updated


@router.delete("/{campaign_id}", status_code=204)
def delete_campaign(campaign_id: int, conn=Depends(get_db)):
    if not campaign_repository.delete_campaign(conn, campaign_id):
        raise HTTPException(
            status_code=404, detail=f"Campaign {campaign_id} not found."
        )


@router.patch("/{campaign_id}", response_model=CampaignOut)
def patch_campaign(campaign_id: int, body: CampaignPatch, conn=Depends(get_db)):
    """Partial update of a campaign."""
    updated = campaign_repository.patch_campaign(
        conn, campaign_id, body.model_dump(exclude_unset=True)
    )
    if updated is None:
        raise HTTPException(
            status_code=404, detail=f"Campaign {campaign_id} not found."
        )
    return updated


@router.get("/lookup")
def get_campaigns_lookup(conn=Depends(get_db)):
    """Return lightweight campaigns list for dropdowns."""
    cursor = conn.cursor()
    cursor.execute("SELECT Campaign_ID, Name FROM [dbo].[Campaign] ORDER BY Name")
    return [{"campaign_id": row[0], "name": row[1]} for row in cursor.fetchall()]


@router.get("/types", response_model=list[CampaignKindOut])
def list_campaign_kinds(conn=Depends(get_db)):
    """Return all campaign types for dropdowns."""
    return campaign_repository.get_campaign_kinds(conn)


@router.post("/types", response_model=CampaignKindOut, status_code=201)
def create_campaign_kind(body: CampaignKindIn, conn=Depends(get_db)):
    return lookup_repository.insert_campaign_kind(conn, body.name)


@router.put("/types/{campaign_kind_id}", response_model=CampaignKindOut)
def update_campaign_kind(campaign_kind_id: int, body: CampaignKindIn, conn=Depends(get_db)):
    updated = lookup_repository.update_campaign_kind(conn, campaign_kind_id, body.name)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"CampaignKind {campaign_kind_id} not found.")
    return updated


@router.delete("/types/{campaign_kind_id}", status_code=204)
def delete_campaign_kind(campaign_kind_id: int, conn=Depends(get_db)):
    deleted = lookup_repository.delete_campaign_kind(conn, campaign_kind_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"CampaignKind {campaign_kind_id} not found.")


@router.get("/{campaign_id}", response_model=CampaignOut)
def get_campaign(campaign_id: int, conn=Depends(get_db)):
    """Return a single campaign by ID."""
    campaign = campaign_repository.get_campaign_by_id(conn, campaign_id)
    if campaign is None:
        raise HTTPException(
            status_code=404, detail=f"Campaign {campaign_id} not found."
        )
    return campaign


@router.get("/{campaign_id}/context", response_model=CampaignContextOut)
def get_campaign_context(campaign_id: int, conn=Depends(get_db)):
    """Return full campaign context: locations, equipment, parameters, metadata count."""
    campaign = campaign_repository.get_campaign_by_id(conn, campaign_id)
    if campaign is None:
        raise HTTPException(
            status_code=404, detail=f"Campaign {campaign_id} not found."
        )
    context = campaign_repository.get_campaign_context(conn, campaign_id)
    return CampaignContextOut(campaign=campaign, **context)


@router.get("/{campaign_id}/overview", response_model=CampaignOverviewOut)
def get_campaign_overview(campaign_id: int, conn=Depends(get_db)):
    """Read-only Campaign Story aggregate: watershed, DAS, equipment+status,
    lab series/panels, campaign annotations, and per-stream freshness."""
    campaign = campaign_repository.get_campaign_by_id(conn, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found.")
    overview = campaign_repository.get_campaign_overview(conn, campaign_id)
    return CampaignOverviewOut(campaign=campaign, **overview)


@router.get("/{campaign_id}/deployments", response_model=list[DeploymentOut])
def list_campaign_deployments(campaign_id: int, conn=Depends(get_db)):
    """Return all deployments (equipment + sampling point pairs) for a campaign."""
    return campaign_repository.list_campaign_deployments(conn, campaign_id)


@router.post(
    "/{campaign_id}/deployments", response_model=DeploymentCreateOut, status_code=201
)
def create_campaign_deployment(
    campaign_id: int, body: DeploymentCreateIn, conn=Depends(get_db)
):
    """Create a deployment: pair equipment with sampling point for a campaign."""
    try:
        installation_id = campaign_repository.create_campaign_deployment(
            conn,
            campaign_id=campaign_id,
            equipment_id=body.equipment_id,
            sampling_point_id=body.sampling_point_id,
            valid_from=body.valid_from,
            notes=body.notes,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return DeploymentCreateOut(installation_id=installation_id)


@router.delete("/{campaign_id}/deployments/{installation_id}", status_code=204)
def remove_campaign_deployment(
    campaign_id: int,
    installation_id: int,
    conn=Depends(get_db),
):
    deleted = campaign_repository.delete_campaign_deployment_by_installation(
        conn, campaign_id, installation_id
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Deployment not found.")
    return Response(status_code=204)
