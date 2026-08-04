"""Persons CRUD endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.database import get_db
from ..repositories import lookup_repository


class PersonIn(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    company: str | None = None
    role: str | None = None
    assigned_functions: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    website: str | None = None
    is_active: bool = True


class PersonLookupOut(BaseModel):
    person_id: int
    label: str
    is_active: bool = True


class PersonOut(BaseModel):
    person_id: int
    first_name: str | None = None
    last_name: str | None = None
    company: str | None = None
    role: str | None = None
    assigned_functions: str | None = None
    email: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    website: str | None = None
    is_active: bool = True


router = APIRouter()

# Editable Person columns, in the order returned by OUTPUT/_row_to_person.
_PERSON_COLS = (
    "[FirstName]",
    "[LastName]",
    "[Company]",
    "[Role]",
    "[AssignedFunctions]",
    "[Email]",
    "[Phone]",
    "[Linkedin]",
    "[Website]",
    "[IsActive]",
)
_PERSON_OUTPUT = "inserted.[Person_ID], " + ", ".join(
    f"inserted.{c}" for c in _PERSON_COLS
)


def _person_values(data: PersonIn) -> tuple:
    return (
        data.first_name,
        data.last_name,
        data.company,
        data.role,
        data.assigned_functions,
        data.email,
        data.phone,
        data.linkedin,
        data.website,
        data.is_active,
    )


def _row_to_person(row) -> PersonOut:
    return PersonOut(
        person_id=row[0],
        first_name=row[1],
        last_name=row[2],
        company=row[3],
        role=row[4],
        assigned_functions=row[5],
        email=row[6],
        phone=row[7],
        linkedin=row[8],
        website=row[9],
        is_active=bool(row[10]),
    )


@router.get("", response_model=list[PersonOut])
def list_persons(conn=Depends(get_db)):
    """Return all persons with full fields."""
    return lookup_repository.get_all_persons(conn)


@router.get("/lookup", response_model=list[PersonLookupOut])
def list_persons_lookup(conn=Depends(get_db)):
    """Return all persons as id + label for dropdowns."""
    return lookup_repository.get_persons_lookup(conn)


@router.post("/", response_model=PersonOut, status_code=201)
def create_person(data: PersonIn, conn=Depends(get_db)):
    """Create a new person."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"INSERT INTO [dbo].[Person] ({', '.join(_PERSON_COLS)})"
            f" OUTPUT {_PERSON_OUTPUT}"
            f" VALUES ({', '.join(['?'] * len(_PERSON_COLS))})",
            *_person_values(data),
        )
        row = cursor.fetchone()
        conn.commit()
        return _row_to_person(row)
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create person: {e}")


@router.put("/{person_id}", response_model=PersonOut)
def update_person(person_id: int, data: PersonIn, conn=Depends(get_db)):
    """Update an existing person."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            f"UPDATE [dbo].[Person]"
            f" SET {', '.join(f'{c}=?' for c in _PERSON_COLS)}"
            f" OUTPUT {_PERSON_OUTPUT}"
            f" WHERE [Person_ID]=?",
            *_person_values(data),
            person_id,
        )
        row = cursor.fetchone()
        conn.commit()
        if row is None:
            raise HTTPException(status_code=404, detail=f"Person {person_id} not found.")
        return _row_to_person(row)
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update person: {e}")


@router.delete("/{person_id}", status_code=204)
def delete_person(person_id: int, conn=Depends(get_db)):
    """Delete a person by ID."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "DELETE FROM [dbo].[Person] WHERE [Person_ID]=?",
            person_id,
        )
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Person {person_id} not found.")
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete person: {e}")
