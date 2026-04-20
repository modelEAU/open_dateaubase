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


def list_site_types() -> list[dict]:
    """Return all site types for dropdowns."""
    try:
        with _get_client() as client:
            r = client.get("/sites/site-types")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def create_site_type(data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post("/sites/site-types", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def update_site_type(site_type_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.put(f"/sites/site-types/{site_type_id}", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def delete_site_type(site_type_id: int) -> None:
    try:
        with _get_client() as client:
            r = client.delete(f"/sites/site-types/{site_type_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)


def list_site_sampling_locations(site_id: int) -> list[dict]:
    """Return all sampling locations for a site."""
    try:
        with _get_client() as client:
            r = client.get(f"/sites/{site_id}/sampling-locations")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def create_sampling_location(site_id: int, data: dict) -> dict:
    """Create a new sampling location for a site."""
    try:
        with _get_client() as client:
            r = client.post(f"/sites/{site_id}/sampling-locations", json=data)
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


def list_equipment_models() -> list[dict]:
    """Return all equipment models (full rows)."""
    try:
        with _get_client() as client:
            r = client.get("/equipment/models")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def create_equipment_model(data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post("/equipment/models", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def update_equipment_model(model_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.put(f"/equipment/models/{model_id}", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def delete_equipment_model(model_id: int) -> None:
    try:
        with _get_client() as client:
            r = client.delete(f"/equipment/models/{model_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)


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


def list_campaign_deployments(campaign_id: int) -> list[dict]:
    """Return all deployments for a campaign."""
    try:
        with _get_client() as client:
            r = client.get(f"/campaigns/{campaign_id}/deployments")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def create_campaign_deployment(campaign_id: int, data: dict) -> dict:
    """Create a deployment (equipment + sampling point) for a campaign."""
    try:
        with _get_client() as client:
            r = client.post(f"/campaigns/{campaign_id}/deployments", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def delete_campaign_deployment(campaign_id: int, installation_id: int) -> None:
    """Delete a deployment by its installation_id."""
    try:
        with _get_client() as client:
            r = client.delete(f"/campaigns/{campaign_id}/deployments/{installation_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)


# ---------------------------------------------------------------------------
# Channels
# ---------------------------------------------------------------------------


def list_channels(
    parameter_id: int | None = None,
    equipment_id: int | None = None,
    processing_degree_id: int | None = None,
    value_type_id: int | None = None,
    campaign_id: int | None = None,
    signal_port_id: int | None = None,
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
    if value_type_id is not None:
        params["value_type_id"] = value_type_id
    if campaign_id is not None:
        params["campaign_id"] = campaign_id
    if signal_port_id is not None:
        params["signal_port_id"] = signal_port_id
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
# Parameters
# ---------------------------------------------------------------------------


def list_parameters_full() -> list[dict]:
    """Return all parameters (full rows, distinct from list_parameters_lookup)."""
    try:
        with _get_client() as client:
            r = client.get("/parameters")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def create_parameter(data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post("/parameters", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def update_parameter(param_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.put(f"/parameters/{param_id}", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def delete_parameter(param_id: int) -> None:
    try:
        with _get_client() as client:
            r = client.delete(f"/parameters/{param_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)


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


def get_channel_timeseries(
    channel_id: int,
    start: str | None = None,
    end: str | None = None,
) -> dict:
    """Fetch time series for a channel using the correct /timeseries/{channel_id} endpoint."""
    params: dict = {}
    if start is not None:
        params["from"] = start
    if end is not None:
        params["to"] = end
    try:
        with _get_client() as client:
            r = client.get(f"/timeseries/{channel_id}", params=params)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def get_channel_stats(channel_id: int) -> dict:
    """Fetch min/max timestamp and observation count for a channel (no data rows)."""
    try:
        with _get_client() as client:
            r = client.get(f"/timeseries/{channel_id}/stats")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def get_channel_thumbnail(channel_id: int, timestamp: str) -> bytes:
    """Fetch the JPEG thumbnail bytes for an image channel entry."""
    try:
        with _get_client() as client:
            r = client.get(f"/timeseries/{channel_id}/thumbnail/{timestamp}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.content


def get_channel_image(channel_id: int, timestamp: str) -> bytes:
    """Fetch the full-resolution image bytes for an image channel entry."""
    try:
        with _get_client() as client:
            r = client.get(f"/timeseries/{channel_id}/image/{timestamp}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.content


# ---------------------------------------------------------------------------
# Sampling point pictures
# ---------------------------------------------------------------------------


def get_sampling_point_picture(site_id: int, sp_id: int) -> bytes:
    """Fetch the reference photo bytes for a sampling location."""
    try:
        with _get_client() as client:
            r = client.get(f"/sites/{site_id}/sampling-locations/{sp_id}/picture")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.content


def upload_sampling_point_picture(
    site_id: int, sp_id: int, file_bytes: bytes, filename: str
) -> dict:
    """Upload or replace the reference photo for a sampling location."""
    try:
        with _get_client() as client:
            r = client.post(
                f"/sites/{site_id}/sampling-locations/{sp_id}/picture",
                files={"picture": (filename, file_bytes)},
            )
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def delete_sampling_point_picture(site_id: int, sp_id: int) -> None:
    """Delete the reference photo for a sampling location."""
    try:
        with _get_client() as client:
            r = client.delete(f"/sites/{site_id}/sampling-locations/{sp_id}/picture")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)


# ---------------------------------------------------------------------------
# Annotation types
# ---------------------------------------------------------------------------


def list_annotation_types() -> list[dict]:
    """Return all annotation types for dropdowns."""
    try:
        with _get_client() as client:
            r = client.get("/annotation-types")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    data = r.json()
    return data.get("annotation_types", data) if isinstance(data, dict) else data


def create_annotation_type(data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post("/annotation-types", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def update_annotation_type(annotation_type_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.put(f"/annotation-types/{annotation_type_id}", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def delete_annotation_type(annotation_type_id: int) -> None:
    try:
        with _get_client() as client:
            r = client.delete(f"/annotation-types/{annotation_type_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)


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


def create_unit(unit: str) -> dict:
    """Create a new unit and return it."""
    try:
        with _get_client() as client:
            r = client.post("/ingest/lookup/units", json={"unit": unit})
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def update_unit(unit_id: int, unit: str) -> dict:
    try:
        with _get_client() as client:
            r = client.put(f"/ingest/lookup/units/{unit_id}", json={"unit": unit})
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def delete_unit(unit_id: int) -> None:
    try:
        with _get_client() as client:
            r = client.delete(f"/ingest/lookup/units/{unit_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)


def list_laboratories_lookup() -> list[dict]:
    """Return laboratories list for dropdowns."""
    try:
        with _get_client() as client:
            r = client.get("/ingest/lookup/laboratories")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def create_laboratory(data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post("/ingest/lookup/laboratories", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def update_laboratory(laboratory_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.put(f"/ingest/lookup/laboratories/{laboratory_id}", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def delete_laboratory(laboratory_id: int) -> None:
    try:
        with _get_client() as client:
            r = client.delete(f"/ingest/lookup/laboratories/{laboratory_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)


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


def list_equipment_event_types() -> list[dict]:
    """Return all equipment event types for dropdowns."""
    try:
        with _get_client() as client:
            r = client.get("/equipment/event-types")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def create_equipment_event(data: dict) -> dict:
    """Create a new equipment event."""
    try:
        with _get_client() as client:
            r = client.post("/equipment/events", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def get_equipment_events(
    equipment_id: int,
    from_dt: str | None = None,
    to_dt: str | None = None,
) -> list[dict]:
    """Fetch equipment events for a single equipment via the lifecycle endpoint."""
    params: dict = {}
    if from_dt is not None:
        params["from"] = from_dt
    if to_dt is not None:
        params["to"] = to_dt
    try:
        with _get_client() as client:
            r = client.get(f"/equipment/{equipment_id}/lifecycle", params=params)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json().get("events", [])


def list_data_provenance_lookup() -> list[dict]:
    """Return data provenance types for dropdowns."""
    try:
        with _get_client() as client:
            r = client.get("/ingest/lookup/data-provenance")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------


def ingest_sensor_image(
    equipment_id: int,
    parameter_id: int,
    unit_id: int,
    timestamp: str,
    image_bytes: bytes,
    filename: str,
    quality_code: int | None = None,
    data_provenance_id: int = 1,
    processing_degree_id: int = 1,
) -> dict:
    """Upload an image file with metadata to POST /ingest/sensor-image."""
    try:
        with _get_client() as client:
            r = client.post(
                "/ingest/sensor-image",
                data={
                    "equipment_id": equipment_id,
                    "parameter_id": parameter_id,
                    "unit_id": unit_id,
                    "timestamp": timestamp,
                    "quality_code": quality_code,
                    "data_provenance_id": data_provenance_id,
                    "processing_degree_id": processing_degree_id,
                },
                files={"image": (filename, image_bytes)},
            )
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def ingest_sensor(data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post("/ingest/sensor", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def ingest_sensor_vector(data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post("/ingest/sensor-vector", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def ingest_sensor_matrix(data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post("/ingest/sensor-matrix", json=data)
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


def create_sample(data: dict) -> dict:
    """Create a new sample and return sample_id."""
    try:
        with _get_client() as client:
            r = client.post("/ingest/samples", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


# ---------------------------------------------------------------------------
# Value Binning Axes
# ---------------------------------------------------------------------------


def list_binning_axes() -> list[dict]:
    """Return all ValueBinningAxis rows with unit names."""
    try:
        with _get_client() as client:
            r = client.get("/value-binning-axes")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def get_binning_axis(axis_id: int) -> dict:
    """Return a single ValueBinningAxis with its bins."""
    try:
        with _get_client() as client:
            r = client.get(f"/value-binning-axes/{axis_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def list_binning_axes_lookup() -> list[dict]:
    """Return lightweight list for dropdowns."""
    try:
        with _get_client() as client:
            r = client.get("/value-binning-axes/lookup")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def create_binning_axis(data: dict) -> dict:
    """Create a new ValueBinningAxis with bins."""
    try:
        with _get_client() as client:
            r = client.post("/value-binning-axes", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def delete_binning_axis(axis_id: int) -> None:
    """Delete a ValueBinningAxis and its bins."""
    try:
        with _get_client() as client:
            r = client.delete(f"/value-binning-axes/{axis_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)


def update_binning_axis(axis_id: int, data: dict) -> dict:
    """Partial update of a ValueBinningAxis."""
    try:
        with _get_client() as client:
            r = client.patch(f"/value-binning-axes/{axis_id}", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


# ---------------------------------------------------------------------------
# SignalPort CRUD
# ---------------------------------------------------------------------------


def list_signal_ports(
    das_id: int | None = None,
    is_active: bool | None = None,
    signal_port_type_id: int | None = None,
    equipment_id: int | None = None,
    page: int = 1,
    page_size: int = 100,
) -> dict:
    params: dict = {"page": page, "page_size": page_size}
    if das_id is not None:
        params["das_id"] = das_id
    if is_active is not None:
        params["is_active"] = is_active
    if signal_port_type_id is not None:
        params["signal_port_type_id"] = signal_port_type_id
    if equipment_id is not None:
        params["equipment_id"] = equipment_id
    try:
        with _get_client() as client:
            r = client.get("/ports", params=params)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def get_signal_port(signal_port_id: int) -> dict:
    try:
        with _get_client() as client:
            r = client.get(f"/ports/{signal_port_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def create_signal_port(data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post("/ports", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def patch_signal_port(signal_port_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.patch(f"/ports/{signal_port_id}", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def relocate_sensor(
    signal_port_id: int,
    sampling_point_id: int,
    start_time: str,
    notes: str | None = None,
) -> dict:
    """Move a sensor to a new sampling point. Returns {new_location_id, closed_location_id, channel_ids}."""
    try:
        with _get_client() as client:
            data = {
                "sampling_point_id": sampling_point_id,
                "start_time": start_time,
            }
            if notes:
                data["notes"] = notes
            r = client.post(f"/ports/{signal_port_id}/relocate", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def list_das_lookup() -> list[dict]:
    """Return list of {das_id, name} for dropdowns."""
    try:
        with _get_client() as client:
            r = client.get("/ports/lookup/das")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def create_das(data: dict) -> dict:
    """Create a new Data Acquisition System."""
    try:
        with _get_client() as client:
            r = client.post("/ports/das", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def update_das(das_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.put(f"/ports/das/{das_id}", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def delete_das(das_id: int) -> None:
    try:
        with _get_client() as client:
            r = client.delete(f"/ports/das/{das_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)


def list_persons() -> list[dict]:
    """Return all persons with full fields."""
    try:
        with _get_client() as client:
            r = client.get("/persons")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def list_persons_lookup() -> list[dict]:
    """Return list of {person_id, label} for dropdowns."""
    try:
        with _get_client() as client:
            r = client.get("/persons/lookup")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def create_person(data: dict) -> dict:
    """Create a new person. Returns {person_id, first_name, last_name, email}."""
    try:
        with _get_client() as client:
            r = client.post("/persons/", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def update_person(person_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.put(f"/persons/{person_id}", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def delete_person(person_id: int) -> None:
    try:
        with _get_client() as client:
            r = client.delete(f"/persons/{person_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)


def list_signal_port_types_lookup() -> list[dict]:
    """Return list of {signal_port_type_id, name} for dropdowns."""
    try:
        with _get_client() as client:
            r = client.get("/ports/lookup/types")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


# ---------------------------------------------------------------------------
# SignalPort lifecycle
# ---------------------------------------------------------------------------


def register_equipment_at_port(signal_port_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post(f"/ports/{signal_port_id}/register-equipment", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def swap_equipment_at_port(signal_port_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post(f"/ports/{signal_port_id}/swap-equipment", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def relocate_signal_port(signal_port_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post(f"/ports/{signal_port_id}/relocate", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def get_equipment_at_port(signal_port_id: int, at: str) -> dict:
    try:
        with _get_client() as client:
            r = client.get(f"/ports/{signal_port_id}/equipment-at", params={"at": at})
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def get_location_at_port(signal_port_id: int, at: str) -> dict:
    try:
        with _get_client() as client:
            r = client.get(f"/ports/{signal_port_id}/location-at", params={"at": at})
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def get_sub_signals(signal_port_id: int) -> dict:
    try:
        with _get_client() as client:
            r = client.get(f"/ports/{signal_port_id}/sub-signals")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


# ---------------------------------------------------------------------------
# ControlLoop
# ---------------------------------------------------------------------------


def list_control_loops() -> list[dict]:
    try:
        with _get_client() as client:
            r = client.get("/control-loops")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def create_control_loop(data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post("/control-loops", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def get_control_loop(loop_id: int) -> dict:
    try:
        with _get_client() as client:
            r = client.get(f"/control-loops/{loop_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def list_control_loop_ports(loop_id: int) -> dict:
    try:
        with _get_client() as client:
            r = client.get(f"/control-loops/{loop_id}/ports")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def add_control_loop_port(loop_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post(f"/control-loops/{loop_id}/ports", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def get_active_application(loop_id: int) -> dict | None:
    """Return the active application for a control loop, or None if none exists."""
    try:
        with _get_client() as client:
            r = client.get(f"/control-loops/{loop_id}/active-application")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def open_application(loop_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post(f"/control-loops/{loop_id}/applications", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def retune_control_loop(loop_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post(f"/control-loops/{loop_id}/retune", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def get_fallback_chain(loop_id: int) -> dict:
    try:
        with _get_client() as client:
            r = client.get(f"/control-loops/{loop_id}/fallback-chain")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


# ---------------------------------------------------------------------------
# Tagless sensor ingest
# ---------------------------------------------------------------------------


def ingest_sensor_tagless(data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post("/ingest/sensor-tagless", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


# ---------------------------------------------------------------------------
# QualityCode
# ---------------------------------------------------------------------------


def list_quality_codes() -> list[dict]:
    try:
        with _get_client() as client:
            r = client.get("/quality-codes")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def create_quality_code(data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post("/quality-codes", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def update_quality_code(qc_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.put(f"/quality-codes/{qc_id}", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def delete_quality_code(qc_id: int) -> None:
    try:
        with _get_client() as client:
            r = client.delete(f"/quality-codes/{qc_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)


def bulk_set_quality_code(
    channel_id: int,
    start_time: str,
    end_time: str,
    quality_code_id: int,
) -> dict:
    """Set a quality code on all value rows in [start_time, end_time] for a channel."""
    try:
        with _get_client() as client:
            r = client.patch(
                f"/timeseries/{channel_id}/quality-code",
                json={
                    "start_time": start_time,
                    "end_time": end_time,
                    "quality_code_id": quality_code_id,
                },
            )
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


# ---------------------------------------------------------------------------
# SampleType
# ---------------------------------------------------------------------------


def list_sample_types() -> list[dict]:
    try:
        with _get_client() as client:
            r = client.get("/sample-types")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def create_sample_type(data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post("/sample-types", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def update_sample_type(sample_type_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.put(f"/sample-types/{sample_type_id}", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def delete_sample_type(sample_type_id: int) -> None:
    try:
        with _get_client() as client:
            r = client.delete(f"/sample-types/{sample_type_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)


# ---------------------------------------------------------------------------
# SampleMethod
# ---------------------------------------------------------------------------


def list_sample_methods() -> list[dict]:
    try:
        with _get_client() as client:
            r = client.get("/sample-methods")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def create_sample_method(data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post("/sample-methods", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def update_sample_method(sample_method_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.put(f"/sample-methods/{sample_method_id}", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def delete_sample_method(sample_method_id: int) -> None:
    try:
        with _get_client() as client:
            r = client.delete(f"/sample-methods/{sample_method_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)


# ---------------------------------------------------------------------------
# ProcessUnit
# ---------------------------------------------------------------------------


def list_process_unit_types() -> list[dict]:
    try:
        with _get_client() as client:
            r = client.get("/process-unit-types")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def create_process_unit_type(data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post("/process-unit-types", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def update_process_unit_type(process_unit_type_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.put(f"/process-unit-types/{process_unit_type_id}", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def delete_process_unit_type(process_unit_type_id: int) -> None:
    try:
        with _get_client() as client:
            r = client.delete(f"/process-unit-types/{process_unit_type_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)


def list_process_units(site_id: int | None = None, tree: bool = False) -> list[dict]:
    params: dict = {}
    if site_id is not None:
        params["site_id"] = site_id
    if tree:
        params["tree"] = "true"
    try:
        with _get_client() as client:
            r = client.get("/process-units", params=params)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def get_process_unit(process_unit_id: int) -> dict:
    try:
        with _get_client() as client:
            r = client.get(f"/process-units/{process_unit_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def list_process_units_lookup(site_id: int | None = None) -> list[dict]:
    params: dict = {}
    if site_id is not None:
        params["site_id"] = site_id
    try:
        with _get_client() as client:
            r = client.get("/process-units/lookup", params=params)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def create_process_unit(data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post("/process-units", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def update_process_unit(process_unit_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.put(f"/process-units/{process_unit_id}", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def patch_process_unit(process_unit_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.patch(f"/process-units/{process_unit_id}", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def delete_process_unit(process_unit_id: int) -> None:
    try:
        with _get_client() as client:
            r = client.delete(f"/process-units/{process_unit_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
