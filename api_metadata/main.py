from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
import time

from db import get_connection

app = FastAPI(title="datEAUbase Metadata API")

class IngestRequest(BaseModel):
    equipment_id: int
    parameter_id: int
    unit_id: int
    purpose_id: int
    sampling_point_id: int
    project_id: int
    value: float
    timestamp: datetime

@app.get("/health")
def health():
    # on teste aussi la connexion DB
    try:
        conn = get_connection()
        conn.close()
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        return {"status": "ok", "db": f"error: {e}"}

@app.post("/ingest")
def ingest(data: IngestRequest):
    # TODO: on fera le vrai resolver metadata
    metadata_id = 1  # temporaire

    ts_unix = int(time.mktime(data.timestamp.timetuple()))

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

    return {"status": "inserted", "metadata_id": metadata_id}
