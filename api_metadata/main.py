from datetime import datetime
from typing import List
import time
import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from db import get_connection
from metadata_resolver import resolve_metadata_id, MetadataNotFound


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler("metadata_api.log"),  # log dans un fichier
        logging.StreamHandler(),                  # log aussi dans la console
    ],
)
logger = logging.getLogger("metadata_api")


class IngestRequest(BaseModel):
    equipment_id: int
    parameter_id: int
    unit_id: int
    purpose_id: int
    sampling_point_id: int
    project_id: int
    value: float
    timestamp: datetime


class ValueItem(BaseModel):
    value_id: int
    value: float
    metadata_id: int
    timestamp: int

app = FastAPI(title="datEAUbase Metadata API")


@app.get("/")
def root():
    return {
        "message": "datEAUbase Metadata API is running. See /docs for the interactive documentation."
    }


@app.get("/health")
def health():
    """
    Vérifie que l'API tourne et que la connexion à la base SQL Server fonctionne.
    """
    try:
        conn = get_connection()
        conn.close()
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        logger.exception("Erreur de connexion à la base dans /health")
        return {"status": "ok", "db": f"error: {e}"}


@app.post("/ingest")
def ingest(data: IngestRequest):
    """
    Reçoit une mesure brute, résout le Metadata_ID correspondant
    puis insère la valeur dans la table [value].
    """
    ts_unix = int(data.timestamp.timestamp())

    logger.info(
        "Requête /ingest reçue: equipment_id=%s parameter_id=%s unit_id=%s "
        "purpose_id=%s sampling_point_id=%s project_id=%s value=%s ts=%s",
        data.equipment_id,
        data.parameter_id,
        data.unit_id,
        data.purpose_id,
        data.sampling_point_id,
        data.project_id,
        data.value,
        ts_unix,
    )

    if data.value < 0:
        logger.warning(
            "Valeur négative refusée pour equipment_id=%s parameter_id=%s : value=%s",
            data.equipment_id,
            data.parameter_id,
            data.value,
        )
        raise HTTPException(status_code=400, detail="Valeur négative interdite.")

    # 2) Résolution du Metadata_ID
    try:
        metadata_id = resolve_metadata_id(
            equipment_id=data.equipment_id,
            parameter_id=data.parameter_id,
            unit_id=data.unit_id,
            purpose_id=data.purpose_id,
            sampling_point_id=data.sampling_point_id,
            project_id=data.project_id,
            ts_unix=ts_unix,
        )
        logger.info(
            "Metadata résolu: Metadata_ID=%s pour equipment_id=%s parameter_id=%s unit_id=%s",
            metadata_id,
            data.equipment_id,
            data.parameter_id,
            data.unit_id,
        )
    except MetadataNotFound as e:
        logger.warning("Metadata non trouvé: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Erreur inattendue lors de la résolution du metadata")
        raise HTTPException(status_code=500, detail="Erreur interne lors de la résolution du metadata.")

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO value (Value, Number_of_experiment, Metadata_ID, Comment_ID, [Timestamp])
            VALUES (?, NULL, ?, NULL, ?)
            """,
            data.value,
            metadata_id,
            ts_unix,
        )

        conn.commit()
        cur.close()
        conn.close()

        logger.info(
            "Insertion OK dans [value]: Metadata_ID=%s value=%s ts=%s",
            metadata_id,
            data.value,
            ts_unix,
        )

    except Exception:
        logger.exception("Erreur lors de l'insertion dans la table [value]")
        raise HTTPException(status_code=500, detail="Erreur lors de l'insertion en base.")

    return {"status": "inserted", "metadata_id": metadata_id}

@app.get("/values/latest", response_model=List[ValueItem])
def get_latest_values(limit: int = 50):
    """
    Retourne les dernières valeurs insérées dans la table [value],
    ordonnées par Value_ID décroissant.
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT TOP (?) Value_ID, Value, Metadata_ID, [Timestamp]
        FROM value
        ORDER BY Value_ID DESC
        """,
        limit,
    )

    rows = cur.fetchall()
    cur.close()
    conn.close()

    results = [
        ValueItem(
            value_id=row[0],
            value=row[1],
            metadata_id=row[2],
            timestamp=row[3],
        )
        for row in rows
    ]

    return results

@app.get("/metadata/resolve")
def test_resolve(
    equipment_id: int,
    parameter_id: int,
    unit_id: int,
    purpose_id: int,
    sampling_point_id: int,
    project_id: int,
    ts: int,
):
    """
    Permet de tester la résolution du Metadata_ID sans insérer de valeur.
    ts = timestamp Unix (int)
    """
    try:
        metadata_id = resolve_metadata_id(
            equipment_id=equipment_id,
            parameter_id=parameter_id,
            unit_id=unit_id,
            purpose_id=purpose_id,
            sampling_point_id=sampling_point_id,
            project_id=project_id,
            ts_unix=ts,
        )
        logger.info(
            "Test /metadata/resolve OK: Metadata_ID=%s (equipment_id=%s, parameter_id=%s)",
            metadata_id,
            equipment_id,
            parameter_id,
        )
        return {"metadata_id": metadata_id}
    except MetadataNotFound as e:
        logger.warning("Test /metadata/resolve: metadata non trouvé: %s", e)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        logger.exception("Erreur inattendue dans /metadata/resolve")
        raise HTTPException(status_code=500, detail="Erreur interne.")
