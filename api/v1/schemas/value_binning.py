"""Pydantic schemas for ValueBinningAxis and ValueBin."""

from __future__ import annotations

from pydantic import BaseModel, field_validator


class ValueBinItem(BaseModel):
    """A single bin definition."""

    bin_index: int
    lower_bound: float
    upper_bound: float


class ValueBinningAxisIn(BaseModel):
    """Input schema for creating a new ValueBinningAxis."""

    name: str
    description: str | None = None
    unit_id: int
    bins: list[ValueBinItem]

    @field_validator("bins")
    @classmethod
    def bins_not_empty(cls, v: list[ValueBinItem]) -> list[ValueBinItem]:
        if not v:
            raise ValueError("bins must not be empty")
        return v


class ValueBinningAxisOut(BaseModel):
    """Output schema for ValueBinningAxis (list view)."""

    value_binning_axis_id: int
    name: str
    description: str | None
    unit_id: int
    unit_name: str | None
    number_of_bins: int


class ValueBinningAxisDetail(ValueBinningAxisOut):
    """Output schema with full bin details."""

    bins: list[ValueBinItem]


class ValueBinningAxisUpdate(BaseModel):
    """Partial update schema for ValueBinningAxis (PATCH)."""

    name: str | None = None
    description: str | None = None
    unit_id: int | None = None
    bins: list[ValueBinItem] | None = None
