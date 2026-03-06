# test_metadata_resolver.py
import pytest
from api_metadata.metadata_resolver import resolve_metadata_id, MetadataNotFound
from api_metadata.db import get_connection


def _seed_exists() -> bool:
    """Vérifie que la ligne seed Metadata_ID=1 est présente."""
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM metadata WHERE Metadata_ID = 1")
        count = cur.fetchone()[0]
        cur.close()
        conn.close()
        return count > 0
    except Exception:
        return False


@pytest.mark.skipif(not _seed_exists(), reason="Seed data absent de la DB")
def test_resolve_metadata_id_existing():
    conn = get_connection()
    cur  = conn.cursor()
    cur.execute("""
        SELECT TOP 1
            Metadata_ID, Equipment_ID, Parameter_ID, Unit_ID,
            Purpose_ID, Sampling_point_ID, Project_ID, StartDate
        FROM metadata
        WHERE Metadata_ID = 1
    """)
    row = cur.fetchone()
    cur.close()
    conn.close()

    assert row is not None

    metadata_id = resolve_metadata_id(
        equipment_id      = row[1],
        parameter_id      = row[2],
        unit_id           = row[3],
        purpose_id        = row[4],
        sampling_point_id = row[5],
        project_id        = row[6],
        ts_unix           = row[7] if row[7] is not None else 1764484200,
    )

    assert metadata_id == row[0]


def test_resolve_metadata_id_not_found():
    with pytest.raises(MetadataNotFound):
        resolve_metadata_id(
            equipment_id=9999,
            parameter_id=9999,
            unit_id=9999,
            purpose_id=9999,
            sampling_point_id=9999,
            project_id=9999,
            ts_unix=1764484200,
        )