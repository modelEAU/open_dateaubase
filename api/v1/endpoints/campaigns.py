"""Campaign endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from api.database import get_db
from ..repositories import campaign_repository
from ..schemas.campaigns import CampaignContextOut, CampaignIn, CampaignOut

router = APIRouter()


@router.get("", response_model=list[CampaignOut])
def list_campaigns(
    site_id: int | None = Query(None),
    campaign_type_id: int | None = Query(None),
    conn=Depends(get_db),
):
    """Return all campaigns, optionally filtered by site or type."""
    return campaign_repository.list_campaigns(conn, site_id=site_id, campaign_type_id=campaign_type_id)


@router.post("", response_model=CampaignOut, status_code=201)
def create_campaign(body: CampaignIn, conn=Depends(get_db)):
    return campaign_repository.insert_campaign(conn, body.model_dump())


@router.put("/{campaign_id}", response_model=CampaignOut)
def update_campaign(campaign_id: int, body: CampaignIn, conn=Depends(get_db)):
    updated = campaign_repository.update_campaign(conn, campaign_id, body.model_dump())
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found.")
    return updated


@router.delete("/{campaign_id}", status_code=204)
def delete_campaign(campaign_id: int, conn=Depends(get_db)):
    if not campaign_repository.delete_campaign(conn, campaign_id):
        raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found.")


@router.get("/{campaign_id}", response_model=CampaignOut)
def get_campaign(campaign_id: int, conn=Depends(get_db)):
    """Return a single campaign by ID."""
    campaign = campaign_repository.get_campaign_by_id(conn, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found.")
    return campaign


@router.get("/{campaign_id}/context", response_model=CampaignContextOut)
def get_campaign_context(campaign_id: int, conn=Depends(get_db)):
    """Return full campaign context: locations, equipment, parameters, metadata count."""
    campaign = campaign_repository.get_campaign_by_id(conn, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=404, detail=f"Campaign {campaign_id} not found.")
    context = campaign_repository.get_campaign_context(conn, campaign_id)
    return CampaignContextOut(campaign=campaign, **context)
