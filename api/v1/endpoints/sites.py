"""Site and sampling location endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.database import get_db
from ..repositories import site_repository
from ..schemas.metadata import (
    SamplingLocationIn,
    SamplingLocationOut,
    SiteIn,
    SiteOut,
    SitePatch,
    SiteLookupOut,
    SiteTypeOut,
)

router = APIRouter()


@router.get("", response_model=list[SiteOut])
def list_sites(conn=Depends(get_db)):
    """Return all sites."""
    return site_repository.get_all_sites(conn)


@router.get("/lookup/list", response_model=list[SiteLookupOut])
def list_sites_lookup(conn=Depends(get_db)):
    """Return lightweight site list for dropdowns (id, name only)."""
    return site_repository.get_sites_lookup(conn)


@router.get("/site-types", response_model=list[SiteTypeOut])
def list_site_types(conn=Depends(get_db)):
    """Return all site types."""
    return site_repository.get_all_site_types(conn)


@router.get("/{site_id}", response_model=SiteOut)
def get_site(site_id: int, conn=Depends(get_db)):
    """Return a single site by ID."""
    site = site_repository.get_site_by_id(conn, site_id)
    if site is None:
        raise HTTPException(status_code=404, detail=f"Site {site_id} not found.")
    return site


@router.post("", response_model=SiteOut, status_code=201)
def create_site(body: SiteIn, conn=Depends(get_db)):
    """Create a new site."""
    return site_repository.insert_site(conn, body.model_dump())


@router.put("/{site_id}", response_model=SiteOut)
def update_site(site_id: int, body: SiteIn, conn=Depends(get_db)):
    """Update an existing site."""
    updated = site_repository.update_site(conn, site_id, body.model_dump())
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Site {site_id} not found.")
    return updated


@router.delete("/{site_id}", status_code=204)
def delete_site(site_id: int, conn=Depends(get_db)):
    """Delete a site by ID."""
    deleted = site_repository.delete_site(conn, site_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Site {site_id} not found.")


@router.patch("/{site_id}", response_model=SiteOut)
def patch_site(site_id: int, body: SitePatch, conn=Depends(get_db)):
    """Partial update of a site."""
    updated = site_repository.patch_site(
        conn, site_id, body.model_dump(exclude_unset=True)
    )
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Site {site_id} not found.")


@router.get("/{site_id}/sampling-locations", response_model=list[SamplingLocationOut])
def list_sampling_locations(site_id: int, conn=Depends(get_db)):
    """Return all sampling locations for a site."""
    site = site_repository.get_site_by_id(conn, site_id)
    if site is None:
        raise HTTPException(status_code=404, detail=f"Site {site_id} not found.")
    return site_repository.get_sampling_locations_for_site(conn, site_id)


@router.post(
    "/{site_id}/sampling-locations",
    response_model=SamplingLocationOut,
    status_code=201,
)
def create_sampling_location(
    site_id: int, body: SamplingLocationIn, conn=Depends(get_db)
):
    """Create a new sampling location (SamplingPoint) for a site."""
    site = site_repository.get_site_by_id(conn, site_id)
    if site is None:
        raise HTTPException(status_code=404, detail=f"Site {site_id} not found.")
    return site_repository.insert_sampling_location(conn, site_id, body.model_dump())
