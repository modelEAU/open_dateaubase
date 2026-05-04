from __future__ import annotations

from pydantic import BaseModel, Field


class ConvertRequest(BaseModel):
    unit_id: int
    values: list[float] = Field(..., min_length=1)


class ConvertResponse(BaseModel):
    si_unit: str
    values: list[float | None]


class UnitOut(BaseModel):
    unit_id: int
    unit: str
    qudt_iri: str | None
    unit_vector: str | None
    si_multiplier: float | None
    si_offset: float | None
