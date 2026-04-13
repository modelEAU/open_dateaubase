"""Persons lookup endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from api.database import get_db
from ..repositories import lookup_repository

router = APIRouter()


class PersonLookupOut(BaseModel):
    person_id: int
    label: str


@router.get("/lookup", response_model=list[PersonLookupOut])
def list_persons_lookup(conn=Depends(get_db)):
    """Return all persons as id + label for dropdowns."""
    return lookup_repository.get_persons_lookup(conn)
