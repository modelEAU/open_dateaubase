"""Schemas for stream-level provenance endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class StreamLocationAtTimeResponse(BaseModel):
    """Where a Stream was being sourced from at a point in time.

    ``source`` says which path resolved the location:
      - "wiring": Channel -> ChannelPortHistory -> EquipmentWiringHistory ->
        Equipment -> EquipmentLocationHistory (sensor tags; every hop is
        temporal).
      - "analysis_series": AnalysisSeries.SamplingPoint_ID (lab series).
      - None: the stream exists but had no location at ``at_time``.

    ``inherited_from_stream_id`` is set when the stream is a derived channel
    (``::smoothed`` and friends) that has no wiring of its own — the location
    is the one of the ancestor channel named here.
    """

    stream_id: int
    at_time: datetime
    source: Literal["wiring", "analysis_series"] | None = None
    inherited_from_stream_id: int | None = None
    sampling_point_id: int | None = None
    sampling_point_name: str | None = None
    site_id: int | None = None
    site_name: str | None = None
    equipment_id: int | None = None
    equipment_identifier: str | None = None
    history_id: int | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
