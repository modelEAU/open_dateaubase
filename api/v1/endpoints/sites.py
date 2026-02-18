"""Site and sampling location endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.database import get_db
from ..repositories import site_repository
from ..schemas.metadata import SamplingLocationOut, SiteOut

router = APIRouter()


@router.get("", response_model=list[SiteOut])
def list_sites(conn=Depends(get_db)):
    """Return all sites."""
    return site_repository.get_all_sites(conn)


@router.get("/{site_id}", response_model=SiteOut)
def get_site(site_id: int, conn=Depends(get_db)):
    """Return a single site by ID."""
    site = site_repository.get_site_by_id(conn, site_id)
    if site is None:
        raise HTTPException(status_code=404, detail=f"Site {site_id} not found.")
    return site


@router.get("/{site_id}/sampling-locations", response_model=list[SamplingLocationOut])
def list_sampling_locations(site_id: int, conn=Depends(get_db)):
    """Return all sampling locations for a site."""
    site = site_repository.get_site_by_id(conn, site_id)
    if site is None:
        raise HTTPException(status_code=404, detail=f"Site {site_id} not found.")
    return site_repository.get_sampling_locations_for_site(conn, site_id)
