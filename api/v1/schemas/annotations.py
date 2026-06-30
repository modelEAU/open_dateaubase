"""Pydantic models for annotation request/response shapes."""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class AnnotationKindResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    color: Optional[str] = None


class AnnotationAuthor(BaseModel):
    person_id: int
    name: str


class AnnotationAnchor(BaseModel):
    """What an annotation is anchored to: a sensor Channel or a lab AnalysisSeries."""

    kind: Literal["channel", "series"]
    id: int


class AnnotationResponse(BaseModel):
    annotation_id: int
    anchor: AnnotationAnchor
    observation_id: Optional[int] = None  # set when the annotation pins one exact Observation
    type: AnnotationKindResponse
    start_time: datetime
    end_time: Optional[datetime] = None
    title: Optional[str] = None
    comment: Optional[str] = None
    author: Optional[AnnotationAuthor] = None
    campaign_id: Optional[int] = None
    campaign_name: Optional[str] = None
    event_id: Optional[int] = None
    created_at: datetime
    modified_at: Optional[datetime] = None
    # Cross-stream feed enrichment (/recent, /by-type): derived location +
    # variable for the anchored stream (sensor: Parameter; lab: SamplingPoint +
    # Parameter). Omitted on per-stream list endpoints.
    location: Optional[str] = None
    variable: Optional[str] = None


class AnnotationListResponse(BaseModel):
    # Top-level echo of the queried stream (sensor list/timeseries endpoints
    # echo channel_id; the lab series-annotations endpoint echoes
    # analysis_series_id). This is a query-parameter echo, NOT a per-annotation
    # field — the per-row anchor lives on each AnnotationResponse.anchor.
    channel_id: Optional[int] = None
    analysis_series_id: Optional[int] = None
    query_range: Optional[dict] = None
    annotations: list[AnnotationResponse]
    count: int


class AnnotationCreate(BaseModel):
    annotation_type: str | int  # Name (str) or AnnotationKind_ID (int)
    start_time: datetime
    end_time: Optional[datetime] = None
    title: Optional[str] = Field(None, max_length=200)
    comment: Optional[str] = None
    campaign_id: Optional[int] = None
    event_id: Optional[int] = None
    author_person_id: Optional[int] = None  # TODO: replace with auth context
    observation_id: Optional[int] = None  # optional point pin (one exact Observation/Replicate)

    @field_validator("end_time")
    @classmethod
    def end_after_start(cls, v: datetime | None, info) -> datetime | None:
        if v is not None and "start_time" in info.data and info.data["start_time"] is not None:
            if v < info.data["start_time"]:
                raise ValueError("end_time must be >= start_time")
        return v


class AnnotationUpdate(BaseModel):
    annotation_type: Optional[str | int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    title: Optional[str] = Field(None, max_length=200)
    comment: Optional[str] = None

    @field_validator("end_time")
    @classmethod
    def end_after_start(cls, v: datetime | None, info) -> datetime | None:
        if v is not None and "start_time" in info.data and info.data["start_time"] is not None:
            if v < info.data["start_time"]:
                raise ValueError("end_time must be >= start_time")
        return v


class AnnotationKindListResponse(BaseModel):
    annotation_types: list[AnnotationKindResponse]
