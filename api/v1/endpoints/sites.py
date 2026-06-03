"""Site and sampling location endpoints."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response

from api.config import settings
from api.database import get_db
from ..repositories import site_repository
from ..schemas.metadata import (
    SamplingLocationIn,
    SamplingLocationOut,
    SiteIn,
    SiteOut,
    SitePatch,
    SiteLookupOut,
    SiteKindIn,
    SiteKindOut,
)
from typing import Optional

router = APIRouter()


@router.get("/sampling-locations", response_model=list[SamplingLocationOut])
def list_all_sampling_locations(
    site_id: Optional[int] = Query(None),
    process_unit_id: Optional[int] = Query(None),
    conn=Depends(get_db),
):
    """Return sampling locations, optionally filtered by site and/or process unit."""
    return site_repository.get_all_sampling_locations(
        conn, site_id=site_id, process_unit_id=process_unit_id
    )


@router.put("/sampling-locations/{sp_id}", response_model=SamplingLocationOut)
def update_sampling_location(sp_id: int, body: SamplingLocationIn, conn=Depends(get_db)):
    """Update a sampling location by ID."""
    updated = site_repository.update_sampling_location(conn, sp_id, body.model_dump())
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Sampling location {sp_id} not found.")
    return updated


@router.delete("/sampling-locations/{sp_id}", status_code=204)
def delete_sampling_location(sp_id: int, conn=Depends(get_db)):
    """Delete a sampling location by ID."""
    deleted = site_repository.delete_sampling_location(conn, sp_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Sampling location {sp_id} not found.")


@router.get("", response_model=list[SiteOut])
def list_sites(conn=Depends(get_db)):
    """Return all sites."""
    return site_repository.get_all_sites(conn)


@router.get("/lookup/list", response_model=list[SiteLookupOut])
def list_sites_lookup(conn=Depends(get_db)):
    """Return lightweight site list for dropdowns (id, name only)."""
    return site_repository.get_sites_lookup(conn)


@router.get("/site-kinds", response_model=list[SiteKindOut])
def list_site_kinds(conn=Depends(get_db)):
    """Return all site kinds."""
    return site_repository.get_all_site_kinds(conn)


@router.post("/site-kinds", response_model=SiteKindOut, status_code=201)
def create_site_kind(body: SiteKindIn, conn=Depends(get_db)):
    """Create a new SiteKind."""
    return site_repository.insert_site_kind(conn, body.name, body.description)


@router.put("/site-kinds/{site_kind_id}", response_model=SiteKindOut)
def update_site_kind(site_kind_id: int, body: SiteKindIn, conn=Depends(get_db)):
    """Update an existing SiteKind."""
    updated = site_repository.update_site_kind(conn, site_kind_id, body.name, body.description)
    if updated is None:
        raise HTTPException(status_code=404, detail=f"SiteKind {site_kind_id} not found.")
    return updated


@router.delete("/site-kinds/{site_kind_id}", status_code=204)
def delete_site_kind(site_kind_id: int, conn=Depends(get_db)):
    """Delete a SiteKind by ID."""
    deleted = site_repository.delete_site_kind(conn, site_kind_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"SiteKind {site_kind_id} not found.")


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


_ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
_MEDIA_TYPES = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}


@router.post("/{site_id}/sampling-locations/{sp_id}/picture", status_code=200)
def upload_sampling_location_picture(
    site_id: int, sp_id: int, picture: UploadFile, conn=Depends(get_db)
):
    """Upload or replace the reference photo for a sampling location."""
    ext = (picture.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=422, detail="Only jpg, jpeg, or png files are accepted.")

    # Fetch existing record to delete old file if present
    rows = site_repository.get_sampling_locations_for_site(conn, site_id)
    sp = next((r for r in rows if r["id"] == sp_id), None)
    if sp is None:
        raise HTTPException(status_code=404, detail=f"Sampling location {sp_id} not found.")

    if sp.get("picture_path"):
        old_file = Path(settings.upload_base_dir) / sp["picture_path"]
        old_file.unlink(missing_ok=True)

    filename = f"{sp_id}_{uuid.uuid4().hex}.{ext}"
    relative_path = f"sampling_points/{filename}"
    abs_path = Path(settings.upload_base_dir) / relative_path
    abs_path.write_bytes(picture.file.read())

    site_repository.update_sampling_location_picture(conn, sp_id, relative_path)
    return {"picture_path": relative_path}


@router.get("/{site_id}/sampling-locations/{sp_id}/picture")
def get_sampling_location_picture(site_id: int, sp_id: int, conn=Depends(get_db)):
    """Return the reference photo for a sampling location."""
    rows = site_repository.get_sampling_locations_for_site(conn, site_id)
    sp = next((r for r in rows if r["id"] == sp_id), None)
    if sp is None:
        raise HTTPException(status_code=404, detail=f"Sampling location {sp_id} not found.")

    picture_path = sp.get("picture_path")
    if not picture_path:
        raise HTTPException(status_code=404, detail="No picture set for this sampling location.")

    abs_path = Path(settings.upload_base_dir) / picture_path
    if not abs_path.exists():
        raise HTTPException(status_code=404, detail="Picture file not found on disk.")

    ext = picture_path.rsplit(".", 1)[-1].lower()
    media_type = _MEDIA_TYPES.get(ext, "application/octet-stream")
    return FileResponse(str(abs_path), media_type=media_type)


@router.delete("/{site_id}/sampling-locations/{sp_id}/picture", status_code=204)
def delete_sampling_location_picture(site_id: int, sp_id: int, conn=Depends(get_db)):
    """Delete the reference photo for a sampling location."""
    rows = site_repository.get_sampling_locations_for_site(conn, site_id)
    sp = next((r for r in rows if r["id"] == sp_id), None)
    if sp is None:
        raise HTTPException(status_code=404, detail=f"Sampling location {sp_id} not found.")

    picture_path = sp.get("picture_path")
    if not picture_path:
        raise HTTPException(status_code=404, detail="No picture set for this sampling location.")

    abs_path = Path(settings.upload_base_dir) / picture_path
    abs_path.unlink(missing_ok=True)

    site_repository.update_sampling_location_picture(conn, sp_id, None)
    return Response(status_code=204)
