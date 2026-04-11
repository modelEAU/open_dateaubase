"""Pydantic schemas for time series data responses."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ScalarValueOut(BaseModel):
    timestamp: datetime
    value: float | None
    quality_code: int | None


class VectorValueOut(BaseModel):
    """One row of a vector measurement (e.g. a single spectral bin)."""

    timestamp: datetime
    bin_index: int
    lower_bound: float | None
    upper_bound: float | None
    nominal_value: float | None
    value: float | None
    quality_code: int | None


class MatrixValueOut(BaseModel):
    """One cell of a 2-D matrix measurement."""

    timestamp: datetime
    row_bin_index: int
    row_lower_bound: float | None
    row_upper_bound: float | None
    row_nominal_value: float | None
    col_bin_index: int
    col_lower_bound: float | None
    col_upper_bound: float | None
    col_nominal_value: float | None
    value: float | None
    quality_code: int | None


class ImageValueOut(BaseModel):
    timestamp: datetime
    image_width: int
    image_height: int
    number_of_channels: int
    image_format: str
    file_size_bytes: int | None
    storage_backend: str
    storage_path: str
    quality_code: int | None


class TimeseriesOut(BaseModel):
    """Uniform time series response regardless of underlying value table."""

    channel_id: int
    location: str | None
    site: str | None
    parameter: str | None
    unit: str | None
    data_shape: str
    provenance: str | None
    processing_degree: str | None
    campaign: str | None
    from_timestamp: datetime | None
    to_timestamp: datetime | None
    row_count: int
    data: list[Any]
