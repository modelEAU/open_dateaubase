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


def delete_campaign_deployment(campaign_id: int, data: dict) -> None:
    """Delete a deployment for a campaign."""
    try:
        with _get_client() as client:
            r = client.request(
                "DELETE", f"/campaigns/{campaign_id}/deployments", json=data
            )
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
