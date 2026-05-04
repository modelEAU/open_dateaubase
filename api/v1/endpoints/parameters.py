"""Parameter endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.database import get_db
from ..repositories import metadata_repository
from ..schemas.channel import ParameterIn, ParameterOut

router = APIRouter()


@router.get("", response_model=list[ParameterOut])
def list_parameters(conn=Depends(get_db)):
    """Return all parameters."""
    return metadata_repository.list_parameters(conn)


@router.post("", response_model=ParameterOut, status_code=201)
def create_parameter(body: ParameterIn, conn=Depends(get_db)):
    return metadata_repository.insert_parameter(conn, body.model_dump())


@router.get("/by-name/{name}", response_model=ParameterOut)
def get_parameter_by_name(name: str, conn=Depends(get_db)):
    param = metadata_repository.get_parameter_by_name(conn, name)
    if param is None:
        raise HTTPException(status_code=404, detail=f"Parameter '{name}' not found.")
    return param


@router.get("/{parameter_id}", response_model=ParameterOut)
def get_parameter(parameter_id: int, conn=Depends(get_db)):
    param = metadata_repository.get_parameter_by_id(conn, parameter_id)
    if param is None:
        raise HTTPException(status_code=404, detail=f"Parameter {parameter_id} not found.")
    return param


@router.put("/{parameter_id}", response_model=ParameterOut)
def update_parameter(parameter_id: int, body: ParameterIn, conn=Depends(get_db)):
    updated = metadata_repository.update_parameter(conn, parameter_id, body.model_dump())
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Parameter {parameter_id} not found.")
    return updated


@router.delete("/{parameter_id}", status_code=204)
def delete_parameter(parameter_id: int, conn=Depends(get_db)):
    if not metadata_repository.delete_parameter(conn, parameter_id):
        raise HTTPException(status_code=404, detail=f"Parameter {parameter_id} not found.")
