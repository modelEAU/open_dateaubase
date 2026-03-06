from datetime import datetime, timedelta
from typing import List, Optional
import logging
import os

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import JSONResponse
from jose import jwt, JWTError
from pydantic import BaseModel

from .db import get_connection
from .metadata_resolver import resolve_metadata_id, MetadataNotFound


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler("metadata_api.log"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("metadata_api")


SECRET_KEY = os.getenv("JWT_SECRET", "dev-secret-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

UI_ADMIN_USER = os.getenv("UI_ADMIN_USER", "admin")
UI_ADMIN_PASSWORD = os.getenv("UI_ADMIN_PASSWORD", "admin123")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


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


class LookupItem(BaseModel):
    id: int
    label: str


class LookupCreateRequest(BaseModel):
    label: str


class RefLabel(BaseModel):
    id: Optional[int] = None
    label: Optional[str] = None


class MetadataListItem(BaseModel):
    metadata_id: int
    equipment: Optional[RefLabel] = None
    parameter: Optional[RefLabel] = None
    unit: Optional[RefLabel] = None
    purpose: Optional[RefLabel] = None
    project: Optional[RefLabel] = None
    sampling_point: Optional[RefLabel] = None
    start_ts: Optional[int] = None
    end_ts: Optional[int] = None


class MetadataListResponse(BaseModel):
    total: int
    items: List[MetadataListItem]


class MetadataCreateRequest(BaseModel):
    equipment_id: int
    parameter_id: int
    unit_id: int
    purpose_id: int
    sampling_point_id: int
    project_id: int
    procedure_id: Optional[int] = None
    contact_id: Optional[int] = None
    condition_id: Optional[int] = None
    start_ts: int
    end_ts: Optional[int] = None


app = FastAPI(title="datEAUbase Metadata API")


def authenticate_user(username: str, password: str) -> bool:
    return username == UI_ADMIN_USER and password == UI_ADMIN_PASSWORD


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token")
        return {"username": username}
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.get("/")
def root():
    return {
        "message": "datEAUbase Metadata API is running. See /docs for the interactive documentation."
    }


@app.get("/health")
def health():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.fetchone()
        cur.close()
        conn.close()
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        logger.exception("DB healthcheck failed")
        return JSONResponse(
            status_code=503,
            content={"status": "error", "db": str(e)},
        )


@app.post("/auth/login", response_model=TokenResponse)
def login(req: LoginRequest):
    if not authenticate_user(req.username, req.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": req.username})
    return {"access_token": token, "token_type": "bearer"}


@app.get("/auth/me")
def me(user=Depends(get_current_user)):
    return user


def _lookup(table: str, id_col: str, label_col: str) -> List[dict]:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(
            f"""
            SELECT {id_col} AS id, {label_col} AS label
            FROM {table}
            ORDER BY {label_col} ASC
            """
        )
        rows = cur.fetchall()
        return [{"id": int(r[0]), "label": "" if r[1] is None else str(r[1])} for r in rows]
    finally:
        cur.close()
        conn.close()


def _lookup_create(table: str, id_col: str, label_col: str, label: str) -> dict:
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT ISNULL(MAX({id_col}), 0) + 1 FROM {table}")
        new_id = cur.fetchone()[0]

        cur.execute(
            f"INSERT INTO {table} ({id_col}, {label_col}) VALUES (?, ?)",
            new_id,
            label,
        )
        conn.commit()
        return {"id": int(new_id), "label": label}
    finally:
        cur.close()
        conn.close()


@app.get("/lookups/equipment", response_model=List[LookupItem])
def lookups_equipment(user=Depends(get_current_user)):
    return _lookup("equipment", "Equipment_ID", "Equipment_identifier")


@app.post("/lookups/equipment", response_model=LookupItem, status_code=201)
def create_equipment(body: LookupCreateRequest, user=Depends(get_current_user)):
    return _lookup_create("equipment", "Equipment_ID", "Equipment_identifier", body.label)


@app.get("/lookups/parameter", response_model=List[LookupItem])
def lookups_parameter(user=Depends(get_current_user)):
    return _lookup("parameter", "Parameter_ID", "Parameter")


@app.post("/lookups/parameter", response_model=LookupItem, status_code=201)
def create_parameter(body: LookupCreateRequest, user=Depends(get_current_user)):
    return _lookup_create("parameter", "Parameter_ID", "Parameter", body.label)


@app.get("/lookups/unit", response_model=List[LookupItem])
def lookups_unit(user=Depends(get_current_user)):
    return _lookup("unit", "Unit_ID", "Unit")


@app.post("/lookups/unit", response_model=LookupItem, status_code=201)
def create_unit(body: LookupCreateRequest, user=Depends(get_current_user)):
    return _lookup_create("unit", "Unit_ID", "Unit", body.label)


@app.get("/lookups/purpose", response_model=List[LookupItem])
def lookups_purpose(user=Depends(get_current_user)):
    return _lookup("purpose", "Purpose_ID", "Purpose")


@app.post("/lookups/purpose", response_model=LookupItem, status_code=201)
def create_purpose(body: LookupCreateRequest, user=Depends(get_current_user)):
    return _lookup_create("purpose", "Purpose_ID", "Purpose", body.label)


@app.get("/lookups/project", response_model=List[LookupItem])
def lookups_project(user=Depends(get_current_user)):
    return _lookup("project", "Project_ID", "Project_name")


@app.post("/lookups/project", response_model=LookupItem, status_code=201)
def create_project(body: LookupCreateRequest, user=Depends(get_current_user)):
    return _lookup_create("project", "Project_ID", "Project_name", body.label)


@app.get("/lookups/sampling_points", response_model=List[LookupItem])
def lookups_sampling_points(user=Depends(get_current_user)):
    return _lookup("sampling_points", "Sampling_point_ID", "Sampling_point")


@app.post("/lookups/sampling_points", response_model=LookupItem, status_code=201)
def create_sampling_point(body: LookupCreateRequest, user=Depends(get_current_user)):
    return _lookup_create("sampling_points", "Sampling_point_ID", "Sampling_point", body.label)


@app.get("/lookups/procedures", response_model=List[LookupItem])
def lookups_procedures(user=Depends(get_current_user)):
    return _lookup("procedures", "Procedure_ID", "Procedure_name")


@app.post("/lookups/procedures", response_model=LookupItem, status_code=201)
def create_procedure(body: LookupCreateRequest, user=Depends(get_current_user)):
    return _lookup_create("procedures", "Procedure_ID", "Procedure_name", body.label)


@app.get("/lookups/contact", response_model=List[LookupItem])
def lookups_contact(user=Depends(get_current_user)):
    return _lookup("contact", "Contact_ID", "Last_name")


@app.post("/lookups/contact", response_model=LookupItem, status_code=201)
def create_contact(body: LookupCreateRequest, user=Depends(get_current_user)):
    return _lookup_create("contact", "Contact_ID", "Last_name", body.label)


@app.get("/lookups/weather_condition", response_model=List[LookupItem])
def lookups_weather_condition(user=Depends(get_current_user)):
    return _lookup("weather_condition", "Condition_ID", "Weather_condition")


@app.post("/lookups/weather_condition", response_model=LookupItem, status_code=201)
def create_weather_condition(body: LookupCreateRequest, user=Depends(get_current_user)):
    return _lookup_create("weather_condition", "Condition_ID", "Weather_condition", body.label)


@app.get("/dashboard/summary")
def dashboard_summary(
    project_id: int | None = None,
    sampling_point_id: int | None = None,
    equipment_id: int | None = None,
    parameter_id: int | None = None,
    user=Depends(get_current_user),
):
    now_unix = int(datetime.utcnow().timestamp())

    where = []
    params = []

    if project_id is not None:
        where.append("m.Project_ID = ?")
        params.append(project_id)
    if sampling_point_id is not None:
        where.append("m.Sampling_point_ID = ?")
        params.append(sampling_point_id)
    if equipment_id is not None:
        where.append("m.Equipment_ID = ?")
        params.append(equipment_id)
    if parameter_id is not None:
        where.append("m.Parameter_ID = ?")
        params.append(parameter_id)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        f"""
        SELECT COUNT(*)
        FROM dbo.[value] v
        JOIN metadata m ON m.Metadata_ID = v.Metadata_ID
        {where_sql}
        """,
        params,
    )
    total_values = cur.fetchone()[0]

    cur.execute(
        f"""
        SELECT COUNT(DISTINCT m.Sampling_point_ID)
        FROM metadata m
        {where_sql}
        """,
        params,
    )
    sampling_points = cur.fetchone()[0] or 0

    cur.execute(
        f"""
        SELECT COUNT(*)
        FROM metadata m
        {where_sql}
        {"AND" if where_sql else "WHERE"}
        m.StartDate <= ?
        AND (m.EndDate IS NULL OR m.EndDate > ?)
        """,
        params + [now_unix, now_unix],
    )
    active_metadata = cur.fetchone()[0]

    cur.close()
    conn.close()

    return {
        "total_values": int(total_values),
        "sampling_points": int(sampling_points),
        "active_metadata": int(active_metadata),
    }


@app.get("/dashboard/activity_30d")
def dashboard_activity_30d(
    project_id: int | None = None,
    sampling_point_id: int | None = None,
    equipment_id: int | None = None,
    parameter_id: int | None = None,
    user=Depends(get_current_user),
):
    where = []
    params = []

    if project_id is not None:
        where.append("m.Project_ID = ?")
        params.append(project_id)
    if sampling_point_id is not None:
        where.append("m.Sampling_point_ID = ?")
        params.append(sampling_point_id)
    if equipment_id is not None:
        where.append("m.Equipment_ID = ?")
        params.append(equipment_id)
    if parameter_id is not None:
        where.append("m.Parameter_ID = ?")
        params.append(parameter_id)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT
            CONVERT(date, DATEADD(SECOND, v.[Timestamp], '19700101')) AS day,
            COUNT(*) AS cnt
        FROM dbo.[value] v
        JOIN metadata m ON m.Metadata_ID = v.Metadata_ID
        {where_sql}
        {"AND" if where_sql else "WHERE"}
        DATEADD(SECOND, v.[Timestamp], '19700101') >= DATEADD(DAY, -30, GETUTCDATE())
        GROUP BY CONVERT(date, DATEADD(SECOND, v.[Timestamp], '19700101'))
        ORDER BY day
        """,
        params,
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [{"day": str(r[0]), "count": int(r[1])} for r in rows]


@app.get("/dashboard/top_parameters_30d")
def dashboard_top_parameters_30d(
    limit: int = Query(10, ge=1, le=50),
    project_id: int | None = None,
    sampling_point_id: int | None = None,
    equipment_id: int | None = None,
    parameter_id: int | None = None,
    user=Depends(get_current_user),
):
    where = []
    params = []

    if project_id is not None:
        where.append("m.Project_ID = ?")
        params.append(project_id)
    if sampling_point_id is not None:
        where.append("m.Sampling_point_ID = ?")
        params.append(sampling_point_id)
    if equipment_id is not None:
        where.append("m.Equipment_ID = ?")
        params.append(equipment_id)
    if parameter_id is not None:
        where.append("m.Parameter_ID = ?")
        params.append(parameter_id)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT TOP (?)
            m.Parameter_ID,
            p.Parameter,
            COUNT(*) AS cnt
        FROM dbo.[value] v
        JOIN metadata m ON m.Metadata_ID = v.Metadata_ID
        LEFT JOIN parameter p ON p.Parameter_ID = m.Parameter_ID
        {where_sql}
        {"AND" if where_sql else "WHERE"}
        DATEADD(SECOND, v.[Timestamp], '19700101') >= DATEADD(DAY, -30, GETUTCDATE())
        GROUP BY m.Parameter_ID, p.Parameter
        ORDER BY cnt DESC
        """,
        [limit] + params,
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {
            "parameter_id": int(r[0]),
            "parameter": r[1] or f"Parameter {r[0]}",
            "count": int(r[2]),
        }
        for r in rows
    ]


@app.get("/metadata", response_model=MetadataListResponse)
def list_metadata(
    limit: int = 200,
    offset: int = 0,
    active_only: bool = False,
    equipment_id: Optional[int] = None,
    parameter_id: Optional[int] = None,
    project_id: Optional[int] = None,
    sampling_point_id: Optional[int] = None,
    q: Optional[str] = None,
    user=Depends(get_current_user),
):
    limit = max(1, min(limit, 2000))
    offset = max(0, offset)

    where = []
    params: list = []

    if active_only:
        now_unix = int(datetime.utcnow().timestamp())
        where.append("m.StartDate <= ? AND (m.EndDate IS NULL OR m.EndDate > ?)")
        params.extend([now_unix, now_unix])

    if equipment_id is not None:
        where.append("m.Equipment_ID = ?")
        params.append(equipment_id)

    if parameter_id is not None:
        where.append("m.Parameter_ID = ?")
        params.append(parameter_id)

    if project_id is not None:
        where.append("m.Project_ID = ?")
        params.append(project_id)

    if sampling_point_id is not None:
        where.append("m.Sampling_point_ID = ?")
        params.append(sampling_point_id)

    if q and q.strip():
        s = f"%{q.strip()}%"
        where.append(
            """
            (
                e.Equipment_identifier LIKE ?
                OR p.Parameter LIKE ?
                OR pr.Project_name LIKE ?
                OR sp.Sampling_point LIKE ?
            )
            """
        )
        params.extend([s, s, s, s])

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    count_query = f"""
        SELECT COUNT(*)
        FROM metadata m
        LEFT JOIN equipment e ON e.Equipment_ID = m.Equipment_ID
        LEFT JOIN parameter p ON p.Parameter_ID = m.Parameter_ID
        LEFT JOIN project pr ON pr.Project_ID = m.Project_ID
        LEFT JOIN sampling_points sp ON sp.Sampling_point_ID = m.Sampling_point_ID
        {where_sql}
    """

    page_query = f"""
        SELECT
            m.Metadata_ID,
            m.Equipment_ID, e.Equipment_identifier,
            m.Parameter_ID, p.Parameter,
            m.Unit_ID, u.Unit,
            m.Purpose_ID, pu.Purpose,
            m.Project_ID, pr.Project_name,
            m.Sampling_point_ID, sp.Sampling_point,
            m.StartDate, m.EndDate
        FROM metadata m
        LEFT JOIN equipment e ON e.Equipment_ID = m.Equipment_ID
        LEFT JOIN parameter p ON p.Parameter_ID = m.Parameter_ID
        LEFT JOIN unit u ON u.Unit_ID = m.Unit_ID
        LEFT JOIN purpose pu ON pu.Purpose_ID = m.Purpose_ID
        LEFT JOIN project pr ON pr.Project_ID = m.Project_ID
        LEFT JOIN sampling_points sp ON sp.Sampling_point_ID = m.Sampling_point_ID
        {where_sql}
        ORDER BY m.Metadata_ID DESC
        OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
    """

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(count_query, params)
    total = int(cur.fetchone()[0])

    cur.execute(page_query, params + [offset, limit])
    rows = cur.fetchall()

    cur.close()
    conn.close()

    items: List[MetadataListItem] = []
    for r in rows:
        items.append(
            MetadataListItem(
                metadata_id=int(r[0]),
                equipment=RefLabel(id=int(r[1]) if r[1] is not None else None, label=r[2]),
                parameter=RefLabel(id=int(r[3]) if r[3] is not None else None, label=r[4]),
                unit=RefLabel(id=int(r[5]) if r[5] is not None else None, label=r[6]),
                purpose=RefLabel(id=int(r[7]) if r[7] is not None else None, label=r[8]),
                project=RefLabel(id=int(r[9]) if r[9] is not None else None, label=r[10]),
                sampling_point=RefLabel(id=int(r[11]) if r[11] is not None else None, label=r[12]),
                start_ts=int(r[13]) if r[13] is not None else None,
                end_ts=int(r[14]) if r[14] is not None else None,
            )
        )

    return {"total": total, "items": items}


@app.post("/metadata", status_code=201)
def create_metadata(data: MetadataCreateRequest, user=Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SELECT ISNULL(MAX(Metadata_ID), 0) + 1 FROM metadata")
        new_id = cur.fetchone()[0]

        cur.execute(
            """
            INSERT INTO metadata (
                Metadata_ID,
                Equipment_ID, Parameter_ID, Unit_ID, Purpose_ID,
                Sampling_point_ID, Project_ID,
                Procedure_ID, Contact_ID, Condition_ID,
                StartDate, EndDate
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            new_id,
            data.equipment_id,
            data.parameter_id,
            data.unit_id,
            data.purpose_id,
            data.sampling_point_id,
            data.project_id,
            data.procedure_id,
            data.contact_id,
            data.condition_id,
            data.start_ts,
            data.end_ts,
        )
        conn.commit()
    except Exception:
        conn.rollback()
        logger.exception("Erreur lors de la création de metadata")
        raise HTTPException(
            status_code=500,
            detail="Erreur interne lors de la création du metadata.",
        )
    finally:
        cur.close()
        conn.close()

    logger.info("Metadata créée: id=%s user=%s", new_id, user["username"])
    return {"metadata_id": int(new_id)}


@app.post("/ingest")
def ingest(data: IngestRequest, user=Depends(get_current_user)):
    ts_unix = int(data.timestamp.timestamp())

    logger.info(
        "Requête /ingest (user=%s): eq=%s param=%s unit=%s purpose=%s sp=%s proj=%s value=%s ts=%s",
        user.get("username"),
        data.equipment_id,
        data.parameter_id,
        data.unit_id,
        data.purpose_id,
        data.sampling_point_id,
        data.project_id,
        data.value,
        ts_unix,
    )

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
    except MetadataNotFound as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        logger.exception("Erreur résolution metadata")
        raise HTTPException(
            status_code=500,
            detail="Erreur interne lors de la résolution du metadata.",
        )

    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO dbo.[value] (Value, Number_of_experiment, Metadata_ID, Comment_ID, [Timestamp])
            VALUES (?, NULL, ?, NULL, ?)
            """,
            data.value,
            metadata_id,
            ts_unix,
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        logger.exception("Erreur insertion value")
        raise HTTPException(status_code=500, detail="Erreur lors de l'insertion en base.")

    return {"status": "inserted", "metadata_id": metadata_id}


@app.get("/values/latest", response_model=List[ValueItem])
def get_latest_values(limit: int = 50, user=Depends(get_current_user)):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT TOP (?) Value_ID, Value, Metadata_ID, [Timestamp]
        FROM dbo.[value]
        ORDER BY Value_ID DESC
        """,
        limit,
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        ValueItem(
            value_id=int(r[0]),
            value=float(r[1]) if r[1] is not None else 0.0,
            metadata_id=int(r[2]) if r[2] is not None else 0,
            timestamp=int(r[3]) if r[3] is not None else 0,
        )
        for r in rows
    ]


@app.get("/metadata/resolve")
def test_resolve(
    equipment_id: int,
    parameter_id: int,
    unit_id: int,
    purpose_id: int,
    sampling_point_id: int,
    project_id: int,
    ts: int,
    user=Depends(get_current_user),
):
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
        return {"metadata_id": metadata_id}
    except MetadataNotFound as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        logger.exception("Erreur dans /metadata/resolve")
        raise HTTPException(status_code=500, detail="Erreur interne.")