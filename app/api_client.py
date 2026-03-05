"""Typed HTTP client for the open_datEAUbase FastAPI backend.

One function per API route. All functions are synchronous (no async/await).
On non-2xx responses: raises APIError(status_code, message).
On connection failure: raises APIError(503, "Cannot reach API").
"""

from __future__ import annotations

import httpx

from app.config import settings


class APIError(Exception):
    """Raised when the API returns a non-2xx response or is unreachable."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"APIError {status_code}: {message}")


def _get_client() -> httpx.Client:
    return httpx.Client(base_url=settings.API_BASE_URL, timeout=30)


def _raise_for_status(response: httpx.Response) -> None:
    if not response.is_success:
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text
        raise APIError(response.status_code, str(detail))


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def get_health() -> dict:
    try:
        with _get_client() as client:
            r = client.get("/health")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


# ---------------------------------------------------------------------------
# Sites
# ---------------------------------------------------------------------------


def list_sites(page: int = 1, page_size: int = 100) -> dict:
    try:
        with _get_client() as client:
            r = client.get("/sites", params={"page": page, "page_size": page_size})
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def get_site(site_id: int) -> dict:
    try:
        with _get_client() as client:
            r = client.get(f"/sites/{site_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def create_site(data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post("/sites", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def update_site(site_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.put(f"/sites/{site_id}", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def delete_site(site_id: int) -> None:
    try:
        with _get_client() as client:
            r = client.delete(f"/sites/{site_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)


def patch_site(site_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.patch(f"/sites/{site_id}", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def list_sites_lookup() -> list[dict]:
    """Return lightweight site list for dropdowns."""
    try:
        with _get_client() as client:
            r = client.get("/sites/lookup/list")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


# ---------------------------------------------------------------------------
# Equipment
# ---------------------------------------------------------------------------


def list_equipment(page: int = 1, page_size: int = 100) -> dict:
    try:
        with _get_client() as client:
            r = client.get("/equipment", params={"page": page, "page_size": page_size})
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def get_equipment(equipment_id: int) -> dict:
    try:
        with _get_client() as client:
            r = client.get(f"/equipment/{equipment_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def create_equipment(data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post("/equipment", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def update_equipment(equipment_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.put(f"/equipment/{equipment_id}", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def delete_equipment(equipment_id: int) -> None:
    try:
        with _get_client() as client:
            r = client.delete(f"/equipment/{equipment_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)


def patch_equipment(equipment_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.patch(f"/equipment/{equipment_id}", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def list_equipment_models_lookup() -> list[dict]:
    """Return equipment models for dropdowns."""
    try:
        with _get_client() as client:
            r = client.get("/equipment/models/lookup")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


# ---------------------------------------------------------------------------
# Campaigns
# ---------------------------------------------------------------------------


def list_campaigns(page: int = 1, page_size: int = 100) -> dict:
    try:
        with _get_client() as client:
            r = client.get("/campaigns", params={"page": page, "page_size": page_size})
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def get_campaign(campaign_id: int) -> dict:
    try:
        with _get_client() as client:
            r = client.get(f"/campaigns/{campaign_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def create_campaign(data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post("/campaigns", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def update_campaign(campaign_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.put(f"/campaigns/{campaign_id}", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def delete_campaign(campaign_id: int) -> None:
    try:
        with _get_client() as client:
            r = client.delete(f"/campaigns/{campaign_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)


def patch_campaign(campaign_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.patch(f"/campaigns/{campaign_id}", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def list_campaign_types() -> list[dict]:
    """Return all campaign types for dropdowns."""
    try:
        with _get_client() as client:
            r = client.get("/campaigns/types")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def list_campaigns_lookup() -> list[dict]:
    """Return campaigns list for dropdowns (id + name only)."""
    try:
        with _get_client() as client:
            r = client.get("/campaigns/lookup")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


# ---------------------------------------------------------------------------
# Channels
# ---------------------------------------------------------------------------


def list_channels(
    parameter_id: int | None = None,
    equipment_id: int | None = None,
    processing_degree_id: int | None = None,
    page: int = 1,
    page_size: int = 100,
) -> dict:
    params: dict = {"page": page, "page_size": page_size}
    if parameter_id is not None:
        params["parameter_id"] = parameter_id
    if equipment_id is not None:
        params["equipment_id"] = equipment_id
    if processing_degree_id is not None:
        params["processing_degree_id"] = processing_degree_id
    try:
        with _get_client() as client:
            r = client.get("/channels", params=params)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def get_channel(channel_id: int) -> dict:
    try:
        with _get_client() as client:
            r = client.get(f"/channels/{channel_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def create_channel(data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post("/channels", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def update_channel(channel_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.put(f"/channels/{channel_id}", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def delete_channel(channel_id: int) -> None:
    try:
        with _get_client() as client:
            r = client.delete(f"/channels/{channel_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)


def list_equipment_lookup() -> list[dict]:
    """Return equipment list for dropdowns."""
    try:
        with _get_client() as client:
            r = client.get("/equipment/lookup")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def list_parameters_lookup() -> list[dict]:
    """Return parameters list for dropdowns."""
    try:
        with _get_client() as client:
            r = client.get("/channels/lookup/parameters")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def list_processing_degrees_lookup() -> list[dict]:
    """Return processing degrees list for dropdowns."""
    try:
        with _get_client() as client:
            r = client.get("/channels/lookup/processing-degrees")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


# ---------------------------------------------------------------------------
# Timeseries
# ---------------------------------------------------------------------------


def get_timeseries(
    channel_id: int,
    start: str | None = None,
    end: str | None = None,
) -> dict:
    params: dict = {"channel_id": channel_id}
    if start is not None:
        params["start"] = start
    if end is not None:
        params["end"] = end
    try:
        with _get_client() as client:
            r = client.get("/timeseries", params=params)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


# ---------------------------------------------------------------------------
# Annotations
# ---------------------------------------------------------------------------


def list_annotations(channel_id: int | None = None) -> dict:
    params: dict = {}
    if channel_id is not None:
        params["channel_id"] = channel_id
    try:
        with _get_client() as client:
            r = client.get("/annotations", params=params)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def create_annotation(data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post("/annotations", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def update_annotation(annotation_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.put(f"/annotations/{annotation_id}", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def delete_annotation(annotation_id: int) -> None:
    try:
        with _get_client() as client:
            r = client.delete(f"/annotations/{annotation_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------


def list_units_lookup() -> list[dict]:
    """Return units list for dropdowns."""
    try:
        with _get_client() as client:
            r = client.get("/ingest/lookup/units")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def list_laboratories_lookup() -> list[dict]:
    """Return laboratories list for dropdowns."""
    try:
        with _get_client() as client:
            r = client.get("/ingest/lookup/laboratories")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def list_procedures_lookup() -> list[dict]:
    """Return procedures list for dropdowns."""
    try:
        with _get_client() as client:
            r = client.get("/ingest/lookup/procedures")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def list_samples_lookup() -> list[dict]:
    """Return samples list for dropdowns (most recent first)."""
    try:
        with _get_client() as client:
            r = client.get("/ingest/lookup/samples")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def list_sampling_points_lookup() -> list[dict]:
    """Return sampling points list for dropdowns."""
    try:
        with _get_client() as client:
            r = client.get("/ingest/lookup/sampling-points")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def list_equipment_events_lookup() -> list[dict]:
    """Return equipment events list for dropdowns."""
    try:
        with _get_client() as client:
            r = client.get("/ingest/lookup/equipment-events")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------


def ingest_sensor(data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post("/ingest/sensor", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def ingest_lab(data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post("/ingest/lab", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()
