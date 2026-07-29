"""A rejected write says what the database refused, not "Internal Server Error"."""

from __future__ import annotations

import pyodbc
from fastapi import FastAPI
from fastapi.testclient import TestClient

from api.main import _integrity_error_handler

DUPLICATE_SAMPLE = (
    "('23000', \"[23000] [Microsoft][ODBC Driver 18 for SQL Server][SQL Server]"
    "Violation of UNIQUE KEY constraint 'UQ_Sample_Identity'. Cannot insert "
    "duplicate key in object 'dbo.Sample'. The duplicate key value is "
    "(4, 2026-07-15 18:30:00, 1, 1, <NULL>). (2627)\")"
)


def _client(error: Exception) -> TestClient:
    app = FastAPI()
    app.add_exception_handler(pyodbc.IntegrityError, _integrity_error_handler)

    @app.get("/boom")
    def boom():
        raise error

    return TestClient(app, raise_server_exceptions=False)


def test_a_duplicate_sample_is_a_409_explaining_itself():
    response = _client(pyodbc.IntegrityError(DUPLICATE_SAMPLE)).get("/boom")
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert "sampling point" in detail and "field replicate" in detail
    assert "Internal Server Error" not in detail


def test_an_unmapped_constraint_still_names_itself():
    error = pyodbc.IntegrityError("Violation of UNIQUE KEY constraint 'UQ_Whatever'.")
    response = _client(error).get("/boom")
    assert response.status_code == 409
    assert "UQ_Whatever" in response.json()["detail"]


def test_an_unrecognisable_violation_is_still_a_409():
    response = _client(pyodbc.IntegrityError("something went wrong")).get("/boom")
    assert response.status_code == 409
    assert response.json()["detail"]
