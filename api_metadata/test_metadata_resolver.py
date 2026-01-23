# test_metadata_resolver.py
from metadata_resolver import resolve_metadata_id, MetadataNotFound
from .db import get_connection

def test_resolve_metadata_id_existing():
    # Arrange: on suppose qu'on a déjà un metadata (1,1,1,1,1,1)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT TOP 1 Metadata_ID, Equipment_ID, Parameter_ID, Unit_ID,
        Purpose_ID, Sampling_point_ID, Project_ID, StartDate, EndDate
        FROM metadata
        WHERE Metadata_ID = 1
    """)
    row = cur.fetchone()
    cur.close()
    conn.close()
    assert row is not None

    metadata_id = resolve_metadata_id(
        equipment_id=row.Equipment_ID,
        parameter_id=row.Parameter_ID,
        unit_id=row.Unit_ID,
        purpose_id=row.Purpose_ID,
        sampling_point_id=row.Sampling_point_ID,
        project_id=row.Project_ID,
        ts_unix=row.StartDate or 1764484200,  # valeur par défaut si NULL
    )

    assert metadata_id == row.Metadata_ID


def test_resolve_metadata_id_not_found():
    # On essaie une combinaison qui n'existe pas
    try:
        resolve_metadata_id(
            equipment_id=9999,
            parameter_id=9999,
            unit_id=9999,
            purpose_id=9999,
            sampling_point_id=9999,
            project_id=9999,
            ts_unix=1764484200,
        )
        assert False, "Aurait dû lever MetadataNotFound"
    except MetadataNotFound:
        assert True
