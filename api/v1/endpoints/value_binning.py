"""ValueBinningAxis endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.database import get_db
from ..repositories import lookup_repository, value_binning_repository
from ..schemas.metadata import BinModeOut
from ..schemas.value_binning import (
    ValueBinningAxisIn,
    ValueBinningAxisOut,
    ValueBinningAxisDetail,
    ValueBinningAxisUpdate,
    ValueBinningAxisResolveRequest,
    ValueBinningAxisResolveResponse,
)

router = APIRouter()


@router.get("/bin-modes", response_model=list[BinModeOut])
def list_bin_modes(conn=Depends(get_db)):
    """Return all BinMode vocabulary entries."""
    return lookup_repository.get_bin_modes(conn)


@router.get("", response_model=list[ValueBinningAxisOut])
def list_binning_axes(conn=Depends(get_db)):
    """Return all ValueBinningAxis rows with unit names."""
    return value_binning_repository.list_binning_axes(conn)


@router.get("/lookup", response_model=list[dict])
def lookup_binning_axes(conn=Depends(get_db)):
    """Return lightweight list for dropdowns."""
    return value_binning_repository.lookup_binning_axes(conn)


@router.get("/{axis_id}", response_model=ValueBinningAxisDetail)
def get_binning_axis(axis_id: int, conn=Depends(get_db)):
    """Return a single ValueBinningAxis with its bins."""
    axis = value_binning_repository.get_binning_axis(conn, axis_id)
    if axis is None:
        raise HTTPException(
            status_code=404, detail=f"ValueBinningAxis {axis_id} not found."
        )
    return axis


@router.post("/resolve", response_model=ValueBinningAxisResolveResponse, status_code=200)
def resolve_binning_axis(body: ValueBinningAxisResolveRequest, conn=Depends(get_db)):
    """Find-or-create a ValueBinningAxis by name + bin fingerprint.

    Returns axis_id and whether it was newly created.
    HTTP 409 if an axis with the same name exists but bins diverge.
    """
    try:
        result = value_binning_repository.resolve_binning_axis(conn, body.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return result


@router.post("", response_model=ValueBinningAxisOut, status_code=201)
def create_binning_axis(body: ValueBinningAxisIn, conn=Depends(get_db)):
    """Create a new ValueBinningAxis with bins."""
    axis_id = value_binning_repository.insert_binning_axis(conn, body.model_dump())
    axis = value_binning_repository.get_binning_axis(conn, axis_id)
    if axis is None:
        raise HTTPException(status_code=500, detail="Failed to create axis.")
    # Remove bins for the response (use base schema)
    axis.pop("bins", None)
    return axis


@router.patch("/{axis_id}", response_model=ValueBinningAxisOut)
def patch_binning_axis(axis_id: int, body: ValueBinningAxisUpdate, conn=Depends(get_db)):
    """Partial update of a ValueBinningAxis."""
    try:
        updated = value_binning_repository.patch_binning_axis(
            conn, axis_id, body.model_dump(exclude_unset=True)
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if updated is None:
        raise HTTPException(
            status_code=404, detail=f"ValueBinningAxis {axis_id} not found."
        )
    updated.pop("bins", None)
    return updated


@router.delete("/{axis_id}", status_code=204)
def delete_binning_axis(axis_id: int, conn=Depends(get_db)):
    """Delete a ValueBinningAxis and its bins."""
    try:
        value_binning_repository.delete_binning_axis(conn, axis_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
