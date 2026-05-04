"""Pydantic schemas for ValueBinningAxis and ValueBin."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, field_validator, model_validator


class BinKind(str, Enum):
    interval = "interval"
    interval_with_nominal = "interval_with_nominal"
    nominal = "nominal"


class ValueBinItem(BaseModel):
    """A single bin definition. Valid states:
    - interval: lower_bound + upper_bound only
    - interval_with_nominal: lower_bound + upper_bound + nominal_value
    - nominal: nominal_value only
    """

    bin_index: int
    lower_bound: float | None = None
    upper_bound: float | None = None
    nominal_value: float | None = None

    @model_validator(mode="after")
    def validate_bin_state(self) -> ValueBinItem:
        has_lower = self.lower_bound is not None
        has_upper = self.upper_bound is not None
        has_nominal = self.nominal_value is not None

        if has_lower != has_upper:
            raise ValueError("lower_bound and upper_bound must both be set or both be null")
        if not has_lower and not has_nominal:
            raise ValueError("At least one of bounds or nominal_value must be provided")
        if has_lower and self.upper_bound <= self.lower_bound:  # type: ignore[operator]
            raise ValueError("upper_bound must be greater than lower_bound")
        return self


def _validate_bins_match_mode(bins: list[ValueBinItem], mode: BinKind) -> None:
    """Raise ValueError if any bin's populated fields don't match the declared mode."""
    for i, b in enumerate(bins):
        has_bounds = b.lower_bound is not None
        has_nominal = b.nominal_value is not None
        match mode:
            case BinKind.interval:
                if not has_bounds or has_nominal:
                    raise ValueError(
                        f"bin[{i}]: mode 'interval' requires lower_bound and upper_bound, no nominal_value"
                    )
            case BinKind.interval_with_nominal:
                if not has_bounds or not has_nominal:
                    raise ValueError(
                        f"bin[{i}]: mode 'interval_with_nominal' requires lower_bound, upper_bound, and nominal_value"
                    )
            case BinKind.nominal:
                if has_bounds or not has_nominal:
                    raise ValueError(
                        f"bin[{i}]: mode 'nominal' requires nominal_value only, no bounds"
                    )


class ValueBinningAxisIn(BaseModel):
    """Input schema for creating a new ValueBinningAxis."""

    name: str
    description: str | None = None
    unit_id: int
    bin_kind: BinKind
    bins: list[ValueBinItem]

    @field_validator("bins")
    @classmethod
    def bins_not_empty(cls, v: list[ValueBinItem]) -> list[ValueBinItem]:
        if not v:
            raise ValueError("bins must not be empty")
        return v

    @model_validator(mode="after")
    def bins_match_mode(self) -> ValueBinningAxisIn:
        _validate_bins_match_mode(self.bins, self.bin_kind)
        return self


class ValueBinningAxisOut(BaseModel):
    """Output schema for ValueBinningAxis (list view)."""

    value_binning_axis_id: int
    name: str
    description: str | None
    unit_id: int
    unit_name: str | None
    number_of_bins: int
    bin_kind: BinKind


class ValueBinningAxisDetail(ValueBinningAxisOut):
    """Output schema with full bin details."""

    bins: list[ValueBinItem]


class ValueBinningAxisUpdate(BaseModel):
    """Partial update schema for ValueBinningAxis (PATCH)."""

    name: str | None = None
    description: str | None = None
    unit_id: int | None = None
    bin_kind: BinKind | None = None
    bins: list[ValueBinItem] | None = None

    @model_validator(mode="after")
    def bins_match_mode_if_both_present(self) -> ValueBinningAxisUpdate:
        if self.bins is not None and self.bin_kind is not None:
            _validate_bins_match_mode(self.bins, self.bin_kind)
        return self


class ValueBinningAxisResolveRequest(BaseModel):
    """Find-or-create a ValueBinningAxis by name + bin fingerprint.

    unit_name is resolved to Unit_ID server-side.
    If an axis with the same name already exists, its bins are compared against
    the request. Fields present in the request must match; extra fields in the
    DB (e.g. bounds when request only has nominal_value) are ignored.
    A mismatch raises HTTP 409.
    """

    name: str
    description: str | None = None
    unit_name: str
    bin_kind: BinKind
    bins: list[ValueBinItem]

    @field_validator("bins")
    @classmethod
    def bins_not_empty(cls, v: list[ValueBinItem]) -> list[ValueBinItem]:
        if not v:
            raise ValueError("bins must not be empty")
        return v

    @model_validator(mode="after")
    def bins_match_mode(self) -> ValueBinningAxisResolveRequest:
        _validate_bins_match_mode(self.bins, self.bin_kind)
        return self


class ValueBinningAxisResolveResponse(BaseModel):
    """Response for find-or-create axis resolution."""

    axis_id: int
    created: bool
    warnings: list[str] = []
