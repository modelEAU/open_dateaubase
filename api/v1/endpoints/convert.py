"""Unit conversion endpoint and parameter-unit validation lookup."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from api.database import get_db
from ..repositories import lookup_repository
from ..schemas.convert import ConvertRequest, ConvertResponse, UnitOut

router = APIRouter()

_SI_DIMENSION_LABELS = ["m", "kg", "s", "A", "K", "mol", "cd"]


def _si_unit_label(unit_vector: str | None) -> str:
    """Derive a human-readable SI unit label from a dimension vector string."""
    if not unit_vector:
        return "SI"
    try:
        exponents = [int(x) for x in unit_vector.split(",")]
    except ValueError:
        return "SI"
    parts = []
    for exp, sym in zip(exponents, _SI_DIMENSION_LABELS):
        if exp == 1:
            parts.append(sym)
        elif exp != 0:
            parts.append(f"{sym}^{exp}")
    return "·".join(parts) if parts else "-"


@router.post("/convert", response_model=ConvertResponse)
def convert_to_si(body: ConvertRequest, conn=Depends(get_db)):
    unit = lookup_repository.get_unit_by_id(conn, body.unit_id)
    if unit is None:
        raise HTTPException(status_code=404, detail=f"Unit {body.unit_id} not found.")
    if unit["si_multiplier"] is None:
        raise HTTPException(
            status_code=422,
            detail=f"Unit '{unit['unit']}' has no linear SI conversion.",
        )
    multiplier: float = unit["si_multiplier"]
    offset: float = unit["si_offset"] or 0.0
    converted = [v * multiplier + offset for v in body.values]
    return ConvertResponse(
        si_unit=_si_unit_label(unit["unit_vector"]),
        values=converted,
    )


@router.get("/units/valid-for/{parameter_id}", response_model=list[UnitOut])
def units_valid_for_parameter(parameter_id: int, conn=Depends(get_db)):
    return lookup_repository.get_units_valid_for_parameter(conn, parameter_id)
