"""Persons CRUD endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.database import get_db
from ..repositories import lookup_repository


class PersonIn(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    role: str | None = None
    organization: str | None = None
    phone: str | None = None


class PersonLookupOut(BaseModel):
    person_id: int
    label: str


class PersonOut(BaseModel):
    person_id: int
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    role: str | None = None
    organization: str | None = None
    phone: str | None = None


router = APIRouter()


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
            "INSERT INTO [dbo].[Person]"
            " ([FirstName], [LastName], [Email], [Role], [Organization], [Phone])"
            " OUTPUT"
            "  inserted.[Person_ID], inserted.[FirstName], inserted.[LastName],"
            "  inserted.[Email], inserted.[Role], inserted.[Organization], inserted.[Phone]"
            " VALUES (?, ?, ?, ?, ?, ?)",
            data.first_name,
            data.last_name,
            data.email,
            data.role,
            data.organization,
            data.phone,
        )
        row = cursor.fetchone()
        conn.commit()
        return PersonOut(
            person_id=row[0],
            first_name=row[1],
            last_name=row[2],
            email=row[3],
            role=row[4],
            organization=row[5],
            phone=row[6],
        )
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create person: {e}")


@router.put("/{person_id}", response_model=PersonOut)
def update_person(person_id: int, data: PersonIn, conn=Depends(get_db)):
    """Update an existing person."""
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE [dbo].[Person]"
            " SET [FirstName]=?, [LastName]=?, [Email]=?, [Role]=?, [Organization]=?, [Phone]=?"
            " OUTPUT"
            "  inserted.[Person_ID], inserted.[FirstName], inserted.[LastName],"
            "  inserted.[Email], inserted.[Role], inserted.[Organization], inserted.[Phone]"
            " WHERE [Person_ID]=?",
            data.first_name,
            data.last_name,
            data.email,
            data.role,
            data.organization,
            data.phone,
            person_id,
        )
        row = cursor.fetchone()
        conn.commit()
        if row is None:
            raise HTTPException(status_code=404, detail=f"Person {person_id} not found.")
        return PersonOut(
            person_id=row[0],
            first_name=row[1],
            last_name=row[2],
            email=row[3],
            role=row[4],
            organization=row[5],
            phone=row[6],
        )
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
