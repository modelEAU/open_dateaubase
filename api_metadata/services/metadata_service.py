# api_metadata/services/metadata_service.py
from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

import pandas as pd

from api_metadata.services.db_client import api_get, api_post, ApiError


def fetch_metadata(
    *,
    limit: int = 200,
    offset: int = 0,
    active_only: bool = False,
    equipment_id: Optional[int] = None,
    parameter_id: Optional[int] = None,
    project_id: Optional[int] = None,
    sampling_point_id: Optional[int] = None,
    q: Optional[str] = None,
) -> pd.DataFrame:
    """
    Récupère la liste paginée des metadata via GET /metadata
    Retourne un DataFrame prêt à afficher.
    """
    params: Dict[str, Any] = {
        "limit": max(1, min(int(limit), 2000)),
        "offset": max(0, int(offset)),
        "active_only": bool(active_only),
    }

    if equipment_id is not None:
        params["equipment_id"] = int(equipment_id)
    if parameter_id is not None:
        params["parameter_id"] = int(parameter_id)
    if project_id is not None:
        params["project_id"] = int(project_id)
    if sampling_point_id is not None:
        params["sampling_point_id"] = int(sampling_point_id)
    if q and q.strip():
        params["q"] = q.strip()

    data = api_get("/metadata", params=params) 
    items = data.get("items", [])

    rows: List[Dict[str, Any]] = []
    for it in items:
        rows.append(
            {
                "Metadata_ID": it.get("metadata_id"),
                "Equipment_ID": (it.get("equipment") or {}).get("id"),
                "Equipment": (it.get("equipment") or {}).get("label"),
                "Parameter_ID": (it.get("parameter") or {}).get("id"),
                "Parameter": (it.get("parameter") or {}).get("label"),
                "Unit_ID": (it.get("unit") or {}).get("id"),
                "Unit": (it.get("unit") or {}).get("label"),
                "Purpose_ID": (it.get("purpose") or {}).get("id"),
                "Purpose": (it.get("purpose") or {}).get("label"),
                "Project_ID": (it.get("project") or {}).get("id"),
                "Project": (it.get("project") or {}).get("label"),
                "Sampling_point_ID": (it.get("sampling_point") or {}).get("id"),
                "Sampling_point": (it.get("sampling_point") or {}).get("label"),
                "StartDate": it.get("start_ts"),
                "EndDate": it.get("end_ts"),
            }
        )

    return pd.DataFrame(rows)

_LOOKUP_ENDPOINTS = {
    "equipment": "/lookups/equipment",
    "parameter": "/lookups/parameter",
    "unit": "/lookups/unit",
    "purpose": "/lookups/purpose",
    "project": "/lookups/project",
    "sampling_points": "/lookups/sampling_points",
}


def fetch_lookup(kind: str) -> List[Dict[str, Any]]:
    """
    Retourne une liste [{id, label}, ...] via endpoints /lookups/...
    """
    if kind not in _LOOKUP_ENDPOINTS:
        raise ValueError(f"Lookup kind invalide: {kind}. Attendus: {list(_LOOKUP_ENDPOINTS.keys())}")

    return api_get(_LOOKUP_ENDPOINTS[kind])


def fetch_pairs(kind: str):
    """
    Compat avec ton code existant: retourne [(id, label), ...]
    """
    items = fetch_lookup(kind)
    return [(it["id"], it["label"]) for it in items]




def create_or_get_id(*args, **kwargs) -> int:
    raise NotImplementedError(
        "create_or_get_id() ne peut pas fonctionner en mode API-first tant que "
        "l'API n'expose pas de endpoints POST pour créer des items de lookups (equipment, parameter, etc.)."
    )


def create_metadata(*args, **kwargs) -> int:
    raise NotImplementedError(
        "create_metadata() ne peut pas fonctionner en mode API-first tant que "
        "l'API n'expose pas de endpoint POST /metadata pour créer une nouvelle metadata."
    )
