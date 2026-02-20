"""Pydantic models for annotation request/response shapes."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class AnnotationTypeResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    color: Optional[str] = None


class AnnotationAuthor(BaseModel):
    person_id: int
    name: str


class AnnotationResponse(BaseModel):
    annotation_id: int
    metadata_id: int
    type: AnnotationTypeResponse
    start_time: datetime
    end_time: Optional[datetime] = None
    title: Optional[str] = None
    comment: Optional[str] = None
    author: Optional[AnnotationAuthor] = None
    campaign_id: Optional[int] = None
    campaign_name: Optional[str] = None
    equipment_event_id: Optional[int] = None
    created_at: datetime
    modified_at: Optional[datetime] = None


class AnnotationListResponse(BaseModel):
    metadata_id: Optional[int] = None
    query_range: Optional[dict] = None
    annotations: list[AnnotationResponse]
    count: int


class AnnotationCreate(BaseModel):
    annotation_type: str | int  # AnnotationTypeName (str) or AnnotationType_ID (int)
    start_time: datetime
    end_time: Optional[datetime] = None
    title: Optional[str] = Field(None, max_length=200)
    comment: Optional[str] = None
    campaign_id: Optional[int] = None
    equipment_event_id: Optional[int] = None
    author_person_id: Optional[int] = None  # TODO: replace with auth context

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


class AnnotationTypeListResponse(BaseModel):
    annotation_types: list[AnnotationTypeResponse]
