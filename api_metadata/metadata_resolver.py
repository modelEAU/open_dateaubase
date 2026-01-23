# metadata_resolver.py

from .db import get_connection

class MetadataNotFound(Exception):
    """Levée quand aucune ligne de metadata ne correspond à la combinaison."""
    pass


def resolve_metadata_id(
    equipment_id: int,
    parameter_id: int,
    unit_id: int,
    purpose_id: int,
    sampling_point_id: int,
    project_id: int,
    ts_unix: int,
) -> int:
    """
    Retourne le Metadata_ID correspondant à la combinaison d'IDs et au timestamp.
    - Filtre sur Equipment/Parameter/Unit/Purpose/Sampling_point/Project
    - Filtre sur StartDate/EndDate pour la période de validité
    """

    conn = get_connection()
    cur = conn.cursor()

    # On cherche la ligne de metadata active au moment ts_unix
    # StartDate/EndDate peuvent être NULL -> on les ignore dans ce cas
    cur.execute(
        """
        SELECT TOP 1 Metadata_ID
        FROM metadata
        WHERE Equipment_ID = ?
        AND Parameter_ID = ?
        AND Unit_ID = ?
        AND Purpose_ID = ?
        AND Sampling_point_ID = ?
        AND Project_ID = ?
        AND (StartDate IS NULL OR StartDate <= ?)
        AND (EndDate   IS NULL OR EndDate   >= ?)
        ORDER BY
        -- On privilégie la ligne avec StartDate le plus récent
        CASE WHEN StartDate IS NULL THEN 1 ELSE 0 END,
        StartDate DESC
        """,
        equipment_id,
        parameter_id,
        unit_id,
        purpose_id,
        sampling_point_id,
        project_id,
        ts_unix,
        ts_unix,
    )

    row = cur.fetchone()
    cur.close()
    conn.close()

    if row is None:
        raise MetadataNotFound(
            "Aucun metadata trouvé pour cette combinaison et ce timestamp."
        )

    return row[0]
