"""Typed HTTP client for the open_datEAUbase FastAPI backend.

One function per API route. All functions are synchronous (no async/await).
On non-2xx responses: raises APIError(status_code, message).
On connection failure: raises APIError(503, "Cannot reach API").
"""

from __future__ import annotations

import httpx
import streamlit as st

from app.config import settings


class APIError(Exception):
    """Raised when the API returns a non-2xx response or is unreachable."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        self.message = message
        super().__init__(f"APIError {status_code}: {message}")


def _get_client() -> httpx.Client:
    headers = {}
    token = st.session_state.get("access_token")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return httpx.Client(base_url=settings.API_BASE_URL, timeout=30, headers=headers)


def _raise_for_status(response: httpx.Response) -> None:
    if response.status_code == 401 and st.session_state.get("access_token"):
        st.session_state.clear()
        st.error("Session expired. Please log in again.")
        st.rerun()
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


def list_site_kinds() -> list[dict]:
    """Return all site kinds for dropdowns."""
    try:
        with _get_client() as client:
            r = client.get("/sites/site-kinds")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def create_site_kind(data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post("/sites/site-kinds", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def update_site_kind(site_kind_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.put(f"/sites/site-kinds/{site_kind_id}", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def delete_site_kind(site_kind_id: int) -> None:
    try:
        with _get_client() as client:
            r = client.delete(f"/sites/site-kinds/{site_kind_id}")
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


def list_all_sampling_locations(
    site_id: int | None = None,
    process_unit_id: int | None = None,
) -> list[dict]:
    """Return sampling locations, optionally filtered by site and/or process unit."""
    params: dict = {}
    if site_id is not None:
        params["site_id"] = site_id
    if process_unit_id is not None:
        params["process_unit_id"] = process_unit_id
    try:
        with _get_client() as client:
            r = client.get("/sites/sampling-locations", params=params)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def update_sampling_location(sp_id: int, data: dict) -> dict:
    """Update a sampling location."""
    try:
        with _get_client() as client:
            r = client.put(f"/sites/sampling-locations/{sp_id}", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def delete_sampling_location(sp_id: int) -> None:
    """Delete a sampling location."""
    try:
        with _get_client() as client:
            r = client.delete(f"/sites/sampling-locations/{sp_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)


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


def list_campaign_kinds() -> list[dict]:
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
    value_kind_id: int | None = None,
    campaign_id: int | None = None,
    signal_interface_id: int | None = None,
    page: int = 1,
    page_size: int = 100,
) -> dict:
    params: dict = {"page": page, "page_size": page_size}
    if parameter_id is not None:
        params["parameter_id"] = parameter_id
    if equipment_id is not None:
        params["equipment_id"] = equipment_id
    if value_kind_id is not None:
        params["value_kind_id"] = value_kind_id
    if campaign_id is not None:
        params["campaign_id"] = campaign_id
    if signal_interface_id is not None:
        params["signal_interface_id"] = signal_interface_id
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


def list_processing_kinds_lookup() -> list[dict]:
    """Return processing kinds for dropdowns (from ProcessingStep vocabulary)."""
    try:
        with _get_client() as client:
            r = client.get("/vocab/processing-kinds")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


# ---------------------------------------------------------------------------
# SignalInterface CRUD
# ---------------------------------------------------------------------------


def list_signal_interfaces(
    das_id: int | None = None,
    page: int = 1,
    page_size: int = 100,
) -> dict:
    params: dict = {"page": page, "page_size": page_size}
    if das_id is not None:
        params["das_id"] = das_id
    try:
        with _get_client() as client:
            r = client.get("/signal-interfaces", params=params)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def create_signal_interface(data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post("/signal-interfaces", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def update_signal_interface(si_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.patch(f"/signal-interfaces/{si_id}", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def delete_signal_interface(si_id: int) -> None:
    try:
        with _get_client() as client:
            r = client.delete(f"/signal-interfaces/{si_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)


def list_signal_interfaces_lookup() -> list[dict]:
    """Return lightweight signal interface list for dropdowns."""
    try:
        with _get_client() as client:
            r = client.get("/signal-interfaces/lookup")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


# ---------------------------------------------------------------------------
# SignalInterfacePort CRUD
# ---------------------------------------------------------------------------


def list_signal_interface_ports(si_id: int) -> list[dict]:
    try:
        with _get_client() as client:
            r = client.get(f"/signal-interfaces/{si_id}/ports")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json().get("items", [])


def create_signal_interface_port(si_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post(f"/signal-interfaces/{si_id}/ports", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def delete_signal_interface_port(si_id: int, port_id: int) -> None:
    try:
        with _get_client() as client:
            r = client.delete(f"/signal-interfaces/{si_id}/ports/{port_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)


# ---------------------------------------------------------------------------
# ChannelKind
# ---------------------------------------------------------------------------


def list_channel_roles() -> list[dict]:
    try:
        with _get_client() as client:
            r = client.get("/channels/lookup/channel-kinds")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


# ---------------------------------------------------------------------------
# SignalInterface traversal
# ---------------------------------------------------------------------------


def list_channels_for_interface(si_id: int) -> list[dict]:
    try:
        with _get_client() as client:
            r = client.get(f"/signal-interfaces/{si_id}/channels")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json().get("items", [])


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


def list_annotation_kinds() -> list[dict]:
    """Return all annotation types for dropdowns."""
    try:
        with _get_client() as client:
            r = client.get("/annotation-kinds")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    data = r.json()
    return data.get("annotation_types", data) if isinstance(data, dict) else data


def create_annotation_kind(data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post("/annotation-kinds", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def update_annotation_kind(annotation_kind_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.put(f"/annotation-kinds/{annotation_kind_id}", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def delete_annotation_kind(annotation_kind_id: int) -> None:
    try:
        with _get_client() as client:
            r = client.delete(f"/annotation-kinds/{annotation_kind_id}")
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


def list_equipment_event_kinds() -> list[dict]:
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
    das_name: str,
    tag: str | None = None,
    equipment_name: str | None = None,
    channel_kind: str = "value",
    parameter_name: str = "",
    unit_name: str = "",
    timestamp: str = "",
    image_bytes: bytes = b"",
    filename: str = "image.bin",
    quality_code: int | None = None,
    data_provenance_kind_id: int = 1,
) -> dict:
    """Upload an image file with metadata to POST /ingest/sensor-image."""
    form_data: dict = {
        "das_name": das_name,
        "channel_kind": channel_kind,
        "parameter_name": parameter_name,
        "unit_name": unit_name,
        "timestamp": timestamp,
        "data_provenance_kind_id": data_provenance_kind_id,
    }
    if tag is not None:
        form_data["tag"] = tag
    if equipment_name is not None:
        form_data["equipment_name"] = equipment_name
    if quality_code is not None:
        form_data["quality_code"] = quality_code
    try:
        with _get_client() as client:
            r = client.post(
                "/ingest/sensor-image",
                data=form_data,
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


def ingest_lab_image(
    name: str,
    experiment_datetime: str,
    sample_id: int,
    parameter_id: int,
    sampling_point_id: int,
    unit_id: int,
    series_name: str,
    image_files: list[tuple[str, bytes]],
    *,
    processing_kind_id: int = 1,
    campaign_id: int | None = None,
    description: str | None = None,
    created_by_person_id: int | None = None,
    laboratory_id: int | None = None,
    analyst_person_id: int | None = None,
    procedure_id: int | None = None,
    quality_code: int | None = None,
    notes: str | None = None,
) -> dict:
    """POST /ingest/lab-image with one or more image files (multiple files = replicates)."""
    form_data: dict = {
        "name": name,
        "experiment_datetime": experiment_datetime,
        "sample_id": sample_id,
        "parameter_id": parameter_id,
        "sampling_point_id": sampling_point_id,
        "unit_id": unit_id,
        "series_name": series_name,
        "processing_kind_id": processing_kind_id,
    }
    for key, val in {
        "campaign_id": campaign_id,
        "description": description,
        "created_by_person_id": created_by_person_id,
        "laboratory_id": laboratory_id,
        "analyst_person_id": analyst_person_id,
        "procedure_id": procedure_id,
        "quality_code": quality_code,
        "notes": notes,
    }.items():
        if val is not None:
            form_data[key] = val
    files = [("images", (fname, data)) for fname, data in image_files]
    try:
        with _get_client() as client:
            r = client.post("/ingest/lab-image", data=form_data, files=files)
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


def list_das_lookup() -> list[dict]:
    """Return list of {das_id, name} for dropdowns."""
    try:
        with _get_client() as client:
            r = client.get("/signal-interfaces/das/lookup")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def list_tags_lookup(das_id: int) -> list[dict]:
    """Return [{signal_interface_id, name}] tags for a DAS (strict-mode dropdowns)."""
    try:
        with _get_client() as client:
            r = client.get("/ingest/lookup/tags", params={"das_id": das_id})
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def list_das_kinds() -> list[dict]:
    """Return [{das_kind_id, name, description}] for DAS category dropdowns."""
    try:
        with _get_client() as client:
            r = client.get("/vocab/das-kinds")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def list_controller_kinds() -> list[dict]:
    """Return [{controller_kind_id, name, description}] for controller type dropdowns."""
    try:
        with _get_client() as client:
            r = client.get("/vocab/controller-kinds")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def create_das(data: dict) -> dict:
    """Create a new Data Acquisition System."""
    try:
        with _get_client() as client:
            r = client.post("/signal-interfaces/das", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def deploy_das(
    das_id: int,
    site_id: int,
    valid_from: str,
    campaign_id: int | None = None,
    notes: str | None = None,
) -> dict:
    """Open a new DASLocationHistory row (closes any current active deployment)."""
    payload = {"site_id": site_id, "valid_from": valid_from}
    if campaign_id is not None:
        payload["campaign_id"] = campaign_id
    if notes is not None:
        payload["notes"] = notes
    try:
        with _get_client() as client:
            r = client.post(f"/das/{das_id}/deploy", json=payload)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def get_das_conflict(das_id: int, site_id: int) -> dict | None:
    """Return conflict info if DAS is currently active at a different site, else None."""
    try:
        with _get_client() as client:
            r = client.get(f"/das/{das_id}/conflict-check", params={"site_id": site_id})
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    data = r.json()
    return data if data.get("conflict") else None


def update_das(das_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.put(f"/signal-interfaces/das/{das_id}", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def delete_das(das_id: int) -> None:
    try:
        with _get_client() as client:
            r = client.delete(f"/signal-interfaces/das/{das_id}")
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


# ---------------------------------------------------------------------------
# Equipment move (v4.0.0 — EquipmentWiringHistory / EquipmentLocationHistory)
# ---------------------------------------------------------------------------


def register_equipment_at_interface(equipment_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post(f"/equipment/{equipment_id}/register-interface", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def rewire_equipment(equipment_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post(f"/equipment/{equipment_id}/rewire", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def relocate_equipment(equipment_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post(f"/equipment/{equipment_id}/relocate", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def get_wiring_at_time(equipment_id: int, at: str) -> dict:
    try:
        with _get_client() as client:
            r = client.get(f"/equipment/{equipment_id}/wiring-at", params={"at": at})
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def get_location_at_time(equipment_id: int, at: str) -> dict:
    try:
        with _get_client() as client:
            r = client.get(f"/equipment/{equipment_id}/location-at", params={"at": at})
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
# SampleKind
# ---------------------------------------------------------------------------


def list_sample_kinds() -> list[dict]:
    try:
        with _get_client() as client:
            r = client.get("/sample-kinds")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def create_sample_kind(data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post("/sample-kinds", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def update_sample_kind(sample_kind_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.put(f"/sample-kinds/{sample_kind_id}", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def delete_sample_kind(sample_kind_id: int) -> None:
    try:
        with _get_client() as client:
            r = client.delete(f"/sample-kinds/{sample_kind_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)


# ---------------------------------------------------------------------------
# SampleCollectionKind
# ---------------------------------------------------------------------------


def list_sample_collection_kinds() -> list[dict]:
    try:
        with _get_client() as client:
            r = client.get("/sample-collection-kinds")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def create_sample_collection_kind(data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post("/sample-collection-kinds", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def update_sample_collection_kind(sample_collection_kind_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.put(f"/sample-collection-kinds/{sample_collection_kind_id}", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def delete_sample_collection_kind(sample_collection_kind_id: int) -> None:
    try:
        with _get_client() as client:
            r = client.delete(f"/sample-collection-kinds/{sample_collection_kind_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)


# ---------------------------------------------------------------------------
# ProcessUnit
# ---------------------------------------------------------------------------


def list_process_unit_types() -> list[dict]:
    try:
        with _get_client() as client:
            r = client.get("/process-unit-kinds")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def create_process_unit_type(data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post("/process-unit-kinds", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def update_process_unit_type(process_unit_kind_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.put(f"/process-unit-kinds/{process_unit_kind_id}", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def delete_process_unit_type(process_unit_kind_id: int) -> None:
    try:
        with _get_client() as client:
            r = client.delete(f"/process-unit-kinds/{process_unit_kind_id}")
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


# ---------------------------------------------------------------------------
# CampaignKind
# ---------------------------------------------------------------------------


def create_campaign_kind(data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post("/campaigns/types", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def update_campaign_kind(campaign_kind_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.put(f"/campaigns/types/{campaign_kind_id}", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def delete_campaign_kind(campaign_kind_id: int) -> None:
    try:
        with _get_client() as client:
            r = client.delete(f"/campaigns/types/{campaign_kind_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)


# ---------------------------------------------------------------------------
# BinKind (read-only)
# ---------------------------------------------------------------------------


def list_bin_kinds() -> list[dict]:
    try:
        with _get_client() as client:
            r = client.get("/value-binning-axes/bin-kinds")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


# ---------------------------------------------------------------------------
# ProcessingKind (read-only)
# ---------------------------------------------------------------------------


def list_processing_kinds() -> list[dict]:
    try:
        with _get_client() as client:
            r = client.get("/vocab/processing-kinds")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


# ---------------------------------------------------------------------------
# EquipmentEventKind CRUD (list already exists above at /equipment/event-types)
# ---------------------------------------------------------------------------


def create_equipment_event_kind(data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post("/equipment/event-types", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def update_equipment_event_kind(event_type_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.put(f"/equipment/event-types/{event_type_id}", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def delete_equipment_event_kind(event_type_id: int) -> None:
    try:
        with _get_client() as client:
            r = client.delete(f"/equipment/event-types/{event_type_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)


# ---------------------------------------------------------------------------
# ProcedureKind
# ---------------------------------------------------------------------------


def list_procedure_kinds() -> list[dict]:
    try:
        with _get_client() as client:
            r = client.get("/vocab/procedure-kinds")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def create_procedure_kind(data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post("/vocab/procedure-kinds", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def update_procedure_kind(procedure_kind_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.put(f"/vocab/procedure-kinds/{procedure_kind_id}", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def delete_procedure_kind(procedure_kind_id: int) -> None:
    try:
        with _get_client() as client:
            r = client.delete(f"/vocab/procedure-kinds/{procedure_kind_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)


# ---------------------------------------------------------------------------
# Procedures
# ---------------------------------------------------------------------------


def list_procedures() -> list[dict]:
    try:
        with _get_client() as client:
            r = client.get("/vocab/procedures")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def create_procedure(data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post("/vocab/procedures", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def update_procedure(procedure_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.put(f"/vocab/procedures/{procedure_id}", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def delete_procedure(procedure_id: int) -> None:
    try:
        with _get_client() as client:
            r = client.delete(f"/vocab/procedures/{procedure_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)


# ---------------------------------------------------------------------------
# Watershed
# ---------------------------------------------------------------------------


def list_watersheds() -> list[dict]:
    try:
        with _get_client() as client:
            r = client.get("/vocab/watersheds")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def create_watershed(data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.post("/vocab/watersheds", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def update_watershed(watershed_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.put(f"/vocab/watersheds/{watershed_id}", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def delete_watershed(watershed_id: int) -> None:
    try:
        with _get_client() as client:
            r = client.delete(f"/vocab/watersheds/{watershed_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)


def get_land_use(watershed_id: int) -> dict | None:
    """Return land use data for a watershed, or None if not set."""
    try:
        with _get_client() as client:
            r = client.get(f"/vocab/watersheds/{watershed_id}/land-use")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    if r.status_code == 404:
        return None
    _raise_for_status(r)
    return r.json()


def upsert_land_use(watershed_id: int, data: dict) -> dict:
    try:
        with _get_client() as client:
            r = client.put(f"/vocab/watersheds/{watershed_id}/land-use", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


# ---------------------------------------------------------------------------
# FK lookup aliases used by schema_registry.fk_lookup_fn()
#
# schema_registry derives the options_fn name as:
#   "list_" + snake_case(TableName) + "_lookup"
# e.g. SiteKind → list_site_kind_lookup
#      CampaignKind → list_campaign_kind_lookup
#
# These thin wrappers make the auto-derived names resolvable via getattr()
# without duplicating any HTTP calls.
# ---------------------------------------------------------------------------


def list_site_kind_lookup() -> list[dict]:
    return list_site_kinds()


def list_campaign_kind_lookup() -> list[dict]:
    return list_campaign_kinds()


def list_watershed_lookup() -> list[dict]:
    return list_watersheds()


def list_site_lookup() -> list[dict]:
    return list_sites_lookup()


def list_person_lookup() -> list[dict]:
    return list_persons_lookup()


def list_process_unit_kind_lookup() -> list[dict]:
    return list_process_unit_types()


def list_annotation_kind_lookup() -> list[dict]:
    return list_annotation_kinds()


def list_bin_kind_lookup() -> list[dict]:
    return list_bin_kinds()


def list_processing_kind_lookup() -> list[dict]:
    return list_processing_kinds()


def list_procedure_kind_lookup() -> list[dict]:
    return list_procedure_kinds()


def list_quality_code_lookup() -> list[dict]:
    return list_quality_codes()


def list_sample_kind_lookup() -> list[dict]:
    return list_sample_kinds()


def list_sample_collection_kind_lookup() -> list[dict]:
    return list_sample_collection_kinds()


def list_equipment_event_kind_lookup() -> list[dict]:
    return list_equipment_event_kinds()


def list_data_acquisition_system_lookup() -> list[dict]:
    return list_das_lookup()


def list_parameter_lookup() -> list[dict]:
    return list_parameters_lookup()


def list_unit_lookup() -> list[dict]:
    return list_units_lookup()


def list_signal_interface_lookup() -> list[dict]:
    return list_signal_interfaces_lookup()


def list_process_unit_lookup(site_id: int | None = None) -> list[dict]:
    return list_process_units_lookup(site_id=site_id)


def list_laboratory_lookup() -> list[dict]:
    return list_laboratories_lookup()


def list_value_binning_axis_lookup() -> list[dict]:
    return list_binning_axes_lookup()


# ---------------------------------------------------------------------------
# EquipmentModel associations
# ---------------------------------------------------------------------------


def list_model_parameters(model_id: int) -> list[dict]:
    try:
        with _get_client() as client:
            r = client.get(f"/equipment/models/{model_id}/parameters")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def add_model_parameter(model_id: int, parameter_id: int) -> dict:
    try:
        with _get_client() as client:
            r = client.post(f"/equipment/models/{model_id}/parameters", json={"parameter_id": parameter_id})
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def remove_model_parameter(model_id: int, parameter_id: int) -> None:
    try:
        with _get_client() as client:
            r = client.delete(f"/equipment/models/{model_id}/parameters/{parameter_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)


def list_model_procedures(model_id: int) -> list[dict]:
    try:
        with _get_client() as client:
            r = client.get(f"/equipment/models/{model_id}/procedures")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def add_model_procedure(model_id: int, procedure_id: int) -> dict:
    try:
        with _get_client() as client:
            r = client.post(f"/equipment/models/{model_id}/procedures", json={"procedure_id": procedure_id})
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def remove_model_procedure(model_id: int, procedure_id: int) -> None:
    try:
        with _get_client() as client:
            r = client.delete(f"/equipment/models/{model_id}/procedures/{procedure_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)


# ---------------------------------------------------------------------------
# ParameterHasUnit associations
# ---------------------------------------------------------------------------


def list_parameter_units(parameter_id: int) -> list[dict]:
    try:
        with _get_client() as client:
            r = client.get(f"/parameters/{parameter_id}/units")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def add_parameter_unit(parameter_id: int, unit_id: int) -> dict:
    try:
        with _get_client() as client:
            r = client.post(f"/parameters/{parameter_id}/units", json={"unit_id": unit_id})
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def remove_parameter_unit(parameter_id: int, unit_id: int) -> None:
    try:
        with _get_client() as client:
            r = client.delete(f"/parameters/{parameter_id}/units/{unit_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def signup(email: str, full_name: str, password: str) -> dict:
    try:
        with _get_client() as client:
            r = client.post(
                "/auth/signup",
                json={"email": email, "full_name": full_name, "password": password},
            )
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def login(email: str, password: str) -> dict:
    try:
        with _get_client() as client:
            r = client.post(
                "/auth/login",
                json={"email": email, "password": password},
            )
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def get_me() -> dict:
    try:
        with _get_client() as client:
            r = client.get("/auth/me")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


def get_audit_logs(
    *,
    user_id: int | None = None,
    action: str | None = None,
    resource_type: str | None = None,
    from_dt: str | None = None,
    to_dt: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    params: dict = {"limit": limit, "offset": offset}
    if user_id is not None:
        params["user_id"] = user_id
    if action:
        params["action"] = action
    if resource_type:
        params["resource_type"] = resource_type
    if from_dt:
        params["from_dt"] = from_dt
    if to_dt:
        params["to_dt"] = to_dt
    try:
        with _get_client() as client:
            r = client.get("/audit/logs", params=params)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()



# ---------------------------------------------------------------------------
# Lab ingest lookups (experiments, series, templates)
# ---------------------------------------------------------------------------


def list_lab_experiments_lookup() -> list[dict]:
    """Return recent LabExperiments for dropdown."""
    try:
        with _get_client() as client:
            r = client.get("/ingest/lab/experiments/lookup")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def get_lab_experiment_series(experiment_id: int) -> list[dict]:
    """Return distinct AnalysisSeries used in a LabExperiment."""
    try:
        with _get_client() as client:
            r = client.get(f"/ingest/lab/experiments/{experiment_id}/series")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def list_analysis_series_lookup() -> list[dict]:
    """Return all AnalysisSeries for dropdown."""
    try:
        with _get_client() as client:
            r = client.get("/ingest/lab/analysis-series/lookup")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def create_analysis_series(data: dict) -> dict:
    """Create a new AnalysisSeries. Returns {analysis_series_id}."""
    try:
        with _get_client() as client:
            r = client.post("/ingest/lab/analysis-series", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def list_lab_experiment_templates() -> list[dict]:
    """Return templates with series count."""
    try:
        with _get_client() as client:
            r = client.get("/ingest/lab/templates")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def get_lab_experiment_template(template_id: int) -> dict:
    """Return template with its series list."""
    try:
        with _get_client() as client:
            r = client.get(f"/ingest/lab/templates/{template_id}")
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def create_lab_experiment_template(data: dict) -> dict:
    """Create template with series. Returns {lab_experiment_template_id}."""
    try:
        with _get_client() as client:
            r = client.post("/ingest/lab/templates", json=data)
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    return r.json()


def add_series_to_template(template_id: int, analysis_series_id: int) -> None:
    """Add an AnalysisSeries to a template."""
    try:
        with _get_client() as client:
            r = client.post(
                f"/ingest/lab/templates/{template_id}/series",
                json={"analysis_series_id": analysis_series_id},
            )
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)


def remove_series_from_template(template_id: int, analysis_series_id: int) -> None:
    """Remove an AnalysisSeries from a template."""
    try:
        with _get_client() as client:
            r = client.delete(
                f"/ingest/lab/templates/{template_id}/series/{analysis_series_id}"
            )
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)



def list_sample_collection_kinds_lookup() -> list[dict]:
    """Return sample collection kinds for dropdown (wrapper for consistency)."""
    return list_sample_collection_kinds()


def list_sample_kinds_lookup() -> list[dict]:
    """Return sample kinds for dropdown (wrapper for consistency)."""
    return list_sample_kinds()