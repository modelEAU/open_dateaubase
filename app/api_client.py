"""Typed HTTP client for the open_datEAUbase FastAPI backend.

One function per API route. All functions are synchronous (no async/await).
On non-2xx responses: raises APIError(status_code, message).
On connection failure: raises APIError(503, "Cannot reach API").
"""

from __future__ import annotations

from typing import Any

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


def _request(
    method: str,
    path: str,
    *,
    params=None,
    json=None,
    data=None,
    files=None,
    return_: str = "json",
) -> Any:
    """Single request boilerplate shared by every endpoint wrapper.

    Owns the client context, ConnectError→503 mapping, status handling, and
    response decoding. ``return_`` selects the body shape: "json" (default,
    None on empty body), "content" (raw bytes). Any non-GET invalidates the
    reference-data caches so freshly-mutated lookups are visible immediately.
    """
    try:
        with _get_client() as client:
            r = client.request(
                method, path, params=params, json=json, data=data, files=files
            )
    except httpx.ConnectError:
        raise APIError(503, "Cannot reach API")
    _raise_for_status(r)
    if method.upper() != "GET":
        clear_lookup_caches()
    if return_ == "content":
        return r.content
    if not r.content:
        return None
    return r.json()


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def get_health() -> dict:
    return _request("GET", "/health")


# ---------------------------------------------------------------------------
# Sites
# ---------------------------------------------------------------------------


def list_sites(page: int = 1, page_size: int = 100) -> dict:
    return _request("GET", "/sites", params={"page": page, "page_size": page_size})


def get_site(site_id: int) -> dict:
    return _request("GET", f"/sites/{site_id}")


def create_site(data: dict) -> dict:
    return _request("POST", "/sites", json=data)


def update_site(site_id: int, data: dict) -> dict:
    return _request("PUT", f"/sites/{site_id}", json=data)


def delete_site(site_id: int) -> None:
    return _request("DELETE", f"/sites/{site_id}")


def patch_site(site_id: int, data: dict) -> dict:
    return _request("PATCH", f"/sites/{site_id}", json=data)


def list_sites_lookup() -> list[dict]:
    """Return lightweight site list for dropdowns."""
    return _request("GET", "/sites/lookup/list")


def list_site_kinds() -> list[dict]:
    """Return all site kinds for dropdowns."""
    return _request("GET", "/sites/site-kinds")


def create_site_kind(data: dict) -> dict:
    return _request("POST", "/sites/site-kinds", json=data)


def update_site_kind(site_kind_id: int, data: dict) -> dict:
    return _request("PUT", f"/sites/site-kinds/{site_kind_id}", json=data)


def delete_site_kind(site_kind_id: int) -> None:
    return _request("DELETE", f"/sites/site-kinds/{site_kind_id}")


def list_site_sampling_locations(site_id: int) -> list[dict]:
    """Return all sampling locations for a site."""
    return _request("GET", f"/sites/{site_id}/sampling-locations")


def create_sampling_location(site_id: int, data: dict) -> dict:
    """Create a new sampling location for a site."""
    return _request("POST", f"/sites/{site_id}/sampling-locations", json=data)


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
    return _request("GET", "/sites/sampling-locations", params=params)


def update_sampling_location(sp_id: int, data: dict) -> dict:
    """Update a sampling location."""
    return _request("PUT", f"/sites/sampling-locations/{sp_id}", json=data)


def delete_sampling_location(sp_id: int) -> None:
    """Delete a sampling location."""
    return _request("DELETE", f"/sites/sampling-locations/{sp_id}")


# ---------------------------------------------------------------------------
# Equipment
# ---------------------------------------------------------------------------


def list_equipment(page: int = 1, page_size: int = 100) -> dict:
    return _request("GET", "/equipment", params={"page": page, "page_size": page_size})


def get_equipment(equipment_id: int) -> dict:
    return _request("GET", f"/equipment/{equipment_id}")


def create_equipment(data: dict) -> dict:
    return _request("POST", "/equipment", json=data)


def update_equipment(equipment_id: int, data: dict) -> dict:
    return _request("PUT", f"/equipment/{equipment_id}", json=data)


def delete_equipment(equipment_id: int) -> None:
    return _request("DELETE", f"/equipment/{equipment_id}")


def patch_equipment(equipment_id: int, data: dict) -> dict:
    return _request("PATCH", f"/equipment/{equipment_id}", json=data)


def list_equipment_models_lookup() -> list[dict]:
    """Return equipment models for dropdowns."""
    return _request("GET", "/equipment/models/lookup")


def list_equipment_models() -> list[dict]:
    """Return all equipment models (full rows)."""
    return _request("GET", "/equipment/models")


def create_equipment_model(data: dict) -> dict:
    return _request("POST", "/equipment/models", json=data)


def update_equipment_model(model_id: int, data: dict) -> dict:
    return _request("PUT", f"/equipment/models/{model_id}", json=data)


def delete_equipment_model(model_id: int) -> None:
    return _request("DELETE", f"/equipment/models/{model_id}")


# ---------------------------------------------------------------------------
# Campaigns
# ---------------------------------------------------------------------------


def list_campaigns(page: int = 1, page_size: int = 100) -> dict:
    return _request("GET", "/campaigns", params={"page": page, "page_size": page_size})


def get_campaign(campaign_id: int) -> dict:
    return _request("GET", f"/campaigns/{campaign_id}")


def create_campaign(data: dict) -> dict:
    return _request("POST", "/campaigns", json=data)


def update_campaign(campaign_id: int, data: dict) -> dict:
    return _request("PUT", f"/campaigns/{campaign_id}", json=data)


def delete_campaign(campaign_id: int) -> None:
    return _request("DELETE", f"/campaigns/{campaign_id}")


def patch_campaign(campaign_id: int, data: dict) -> dict:
    return _request("PATCH", f"/campaigns/{campaign_id}", json=data)


def list_campaign_kinds() -> list[dict]:
    """Return all campaign types for dropdowns."""
    return _request("GET", "/campaigns/types")


def list_campaigns_lookup() -> list[dict]:
    """Return campaigns list for dropdowns (id + name only)."""
    return _request("GET", "/campaigns/lookup")


def list_campaign_deployments(campaign_id: int) -> list[dict]:
    """Return all deployments for a campaign."""
    return _request("GET", f"/campaigns/{campaign_id}/deployments")


def create_campaign_deployment(campaign_id: int, data: dict) -> dict:
    """Create a deployment (equipment + sampling point) for a campaign."""
    return _request("POST", f"/campaigns/{campaign_id}/deployments", json=data)


def delete_campaign_deployment(campaign_id: int, installation_id: int) -> None:
    """Delete a deployment by its installation_id."""
    return _request("DELETE", f"/campaigns/{campaign_id}/deployments/{installation_id}")


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
    return _request("GET", "/channels", params=params)


def get_channel(channel_id: int) -> dict:
    return _request("GET", f"/channels/{channel_id}")


def create_channel(data: dict) -> dict:
    return _request("POST", "/channels", json=data)


def update_channel(channel_id: int, data: dict) -> dict:
    return _request("PUT", f"/channels/{channel_id}", json=data)


def delete_channel(channel_id: int) -> None:
    return _request("DELETE", f"/channels/{channel_id}")


def list_equipment_lookup() -> list[dict]:
    """Return equipment list for dropdowns."""
    return _request("GET", "/equipment/lookup")


def list_parameters_lookup() -> list[dict]:
    """Return parameters list for dropdowns."""
    return _request("GET", "/channels/lookup/parameters")


def list_operation_kinds_lookup() -> list[dict]:
    """Return operation kinds for dropdowns (OperationKind vocabulary).

    Returns rows shaped ``{operation_kind_id, name, ...}``.
    """
    return _request("GET", "/vocab/operation-kinds")


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
    return _request("GET", "/signal-interfaces", params=params)


def create_signal_interface(data: dict) -> dict:
    return _request("POST", "/signal-interfaces", json=data)


def update_signal_interface(si_id: int, data: dict) -> dict:
    return _request("PATCH", f"/signal-interfaces/{si_id}", json=data)


def delete_signal_interface(si_id: int) -> None:
    return _request("DELETE", f"/signal-interfaces/{si_id}")


def list_signal_interfaces_lookup() -> list[dict]:
    """Return lightweight signal interface list for dropdowns."""
    return _request("GET", "/signal-interfaces/lookup")


# ---------------------------------------------------------------------------
# SignalInterfacePort CRUD
# ---------------------------------------------------------------------------


def list_signal_interface_ports(si_id: int) -> list[dict]:
    return _request("GET", f"/signal-interfaces/{si_id}/ports").get("items", [])


def create_signal_interface_port(si_id: int, data: dict) -> dict:
    return _request("POST", f"/signal-interfaces/{si_id}/ports", json=data)


def delete_signal_interface_port(si_id: int, port_id: int) -> None:
    return _request("DELETE", f"/signal-interfaces/{si_id}/ports/{port_id}")


# ---------------------------------------------------------------------------
# ChannelKind
# ---------------------------------------------------------------------------


def list_channel_roles() -> list[dict]:
    return _request("GET", "/channels/lookup/channel-kinds")


# ---------------------------------------------------------------------------
# SignalInterface traversal
# ---------------------------------------------------------------------------


def list_channels_for_interface(si_id: int) -> list[dict]:
    return _request("GET", f"/signal-interfaces/{si_id}/channels").get("items", [])


# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------


def list_parameters_full() -> list[dict]:
    """Return all parameters (full rows, distinct from list_parameters_lookup)."""
    return _request("GET", "/parameters")


def create_parameter(data: dict) -> dict:
    return _request("POST", "/parameters", json=data)


def update_parameter(param_id: int, data: dict) -> dict:
    return _request("PUT", f"/parameters/{param_id}", json=data)


def delete_parameter(param_id: int) -> None:
    return _request("DELETE", f"/parameters/{param_id}")


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
    return _request("GET", "/timeseries", params=params)


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
    return _request("GET", f"/timeseries/{channel_id}", params=params)


def get_channel_stats(channel_id: int) -> dict:
    """Fetch min/max timestamp and observation count for a channel (no data rows)."""
    return _request("GET", f"/timeseries/{channel_id}/stats")


def get_stream_provenance(stream_id: int) -> dict:
    """Fetch the resolved provenance graph rooted at a Stream (sensor channel or
    lab series): nodes (with labels, provenance kind, traits) plus ancestor and
    descendant processing steps. Powers the Data Explorer Provenance panel."""
    return _request("GET", f"/lineage/streams/{stream_id}/provenance")


def get_channel_thumbnail(channel_id: int, timestamp: str) -> bytes:
    """Fetch the JPEG thumbnail bytes for an image channel entry."""
    return _request("GET", f"/timeseries/{channel_id}/thumbnail/{timestamp}", return_="content")


def get_channel_image(channel_id: int, timestamp: str) -> bytes:
    """Fetch the full-resolution image bytes for an image channel entry."""
    return _request("GET", f"/timeseries/{channel_id}/image/{timestamp}", return_="content")


# ---------------------------------------------------------------------------
# Lab AnalysisSeries time series (Traces) — mirror of the channel helpers.
# Timestamps are sample collection times (ADR 0002).
# ---------------------------------------------------------------------------


def get_analysis_series_timeseries(
    analysis_series_id: int,
    start: str | None = None,
    end: str | None = None,
) -> dict:
    """Fetch time series for a lab AnalysisSeries via /analysis-series/{id}."""
    params: dict = {}
    if start is not None:
        params["from"] = start
    if end is not None:
        params["to"] = end
    return _request("GET", f"/analysis-series/{analysis_series_id}", params=params)


def get_analysis_series_stats(analysis_series_id: int) -> dict:
    """Fetch min/max sample-collection time and measurement count for a series."""
    return _request("GET", f"/analysis-series/{analysis_series_id}/stats")


def get_analysis_series_thumbnail(analysis_series_id: int, timestamp: str) -> bytes:
    """Fetch the JPEG thumbnail bytes for a lab image measurement."""
    return _request("GET", f"/analysis-series/{analysis_series_id}/thumbnail/{timestamp}", return_="content")


def get_analysis_series_image(analysis_series_id: int, timestamp: str) -> bytes:
    """Fetch the full-resolution image bytes for a lab image measurement."""
    return _request("GET", f"/analysis-series/{analysis_series_id}/image/{timestamp}", return_="content")


# ---------------------------------------------------------------------------
# Sampling point pictures
# ---------------------------------------------------------------------------


def get_sampling_point_picture(site_id: int, sp_id: int) -> bytes:
    """Fetch the reference photo bytes for a sampling location."""
    return _request("GET", f"/sites/{site_id}/sampling-locations/{sp_id}/picture", return_="content")


def upload_sampling_point_picture(
    site_id: int, sp_id: int, file_bytes: bytes, filename: str
) -> dict:
    """Upload or replace the reference photo for a sampling location."""
    return _request("POST", f"/sites/{site_id}/sampling-locations/{sp_id}/picture", files={"picture": (filename, file_bytes)},)


def delete_sampling_point_picture(site_id: int, sp_id: int) -> None:
    """Delete the reference photo for a sampling location."""
    return _request("DELETE", f"/sites/{site_id}/sampling-locations/{sp_id}/picture")


# ---------------------------------------------------------------------------
# Annotation types
# ---------------------------------------------------------------------------


def list_annotation_kinds() -> list[dict]:
    """Return all annotation types for dropdowns."""
    data = _request("GET", "/annotation-kinds")
    return data.get("annotation_types", data) if isinstance(data, dict) else data


def create_annotation_kind(data: dict) -> dict:
    return _request("POST", "/annotation-kinds", json=data)


def update_annotation_kind(annotation_kind_id: int, data: dict) -> dict:
    return _request("PUT", f"/annotation-kinds/{annotation_kind_id}", json=data)


def delete_annotation_kind(annotation_kind_id: int) -> None:
    return _request("DELETE", f"/annotation-kinds/{annotation_kind_id}")


# ---------------------------------------------------------------------------
# Annotations
# ---------------------------------------------------------------------------


def list_annotations(stream_id: int | None = None) -> dict:
    """List annotations, optionally filtered to one anchored stream.

    The backend list endpoint (``GET /annotations``) still echoes the filter as
    a ``channel_id`` query param, so the wire param name is kept; ``stream_id``
    is the anchored Stream_ID identifying the channel/series.
    """
    params: dict = {}
    if stream_id is not None:
        params["channel_id"] = stream_id
    return _request("GET", "/annotations", params=params)


def create_annotation(
    stream_id: int, data: dict, *, anchor_kind: str = "channel"
) -> dict:
    """Create an annotation anchored to a stream.

    The write path is URL-anchored: the path id is a Stream_ID. ``anchor_kind``
    selects the arm — ``"channel"`` posts to ``/timeseries/{stream_id}/annotations``
    (sensor), ``"series"`` posts to ``/analysis-series/{stream_id}/annotations``
    (lab).
    """
    if anchor_kind == "series":
        path = f"/analysis-series/{stream_id}/annotations"
    else:
        path = f"/timeseries/{stream_id}/annotations"
    return _request("POST", path, json=data)


def update_annotation(annotation_id: int, data: dict) -> dict:
    return _request("PUT", f"/annotations/{annotation_id}", json=data)


def delete_annotation(annotation_id: int) -> None:
    return _request("DELETE", f"/annotations/{annotation_id}")


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Lookup helpers
# ---------------------------------------------------------------------------


def list_units_lookup() -> list[dict]:
    """Return units list for dropdowns."""
    return _request("GET", "/ingest/lookup/units")


def create_unit(unit: str) -> dict:
    """Create a new unit and return it."""
    return _request("POST", "/ingest/lookup/units", json={"unit": unit})


def update_unit(unit_id: int, unit: str) -> dict:
    return _request("PUT", f"/ingest/lookup/units/{unit_id}", json={"unit": unit})


def delete_unit(unit_id: int) -> None:
    return _request("DELETE", f"/ingest/lookup/units/{unit_id}")


def list_laboratories_lookup() -> list[dict]:
    """Return laboratories list for dropdowns."""
    return _request("GET", "/ingest/lookup/laboratories")


def create_laboratory(data: dict) -> dict:
    return _request("POST", "/ingest/lookup/laboratories", json=data)


def update_laboratory(laboratory_id: int, data: dict) -> dict:
    return _request("PUT", f"/ingest/lookup/laboratories/{laboratory_id}", json=data)


def delete_laboratory(laboratory_id: int) -> None:
    return _request("DELETE", f"/ingest/lookup/laboratories/{laboratory_id}")


def list_procedures_lookup() -> list[dict]:
    """Return procedures list for dropdowns."""
    return _request("GET", "/ingest/lookup/procedures")


def list_samples_lookup() -> list[dict]:
    """Return samples list for dropdowns (most recent first)."""
    return _request("GET", "/ingest/lookup/samples")


def list_sampling_points_lookup() -> list[dict]:
    """Return sampling points list for dropdowns."""
    return _request("GET", "/ingest/lookup/sampling-points")


def list_equipment_events_lookup() -> list[dict]:
    """Return equipment events list for dropdowns."""
    return _request("GET", "/ingest/lookup/equipment-events")


def list_equipment_event_kinds() -> list[dict]:
    """Return all equipment event types for dropdowns."""
    return _request("GET", "/equipment/event-types")


def create_equipment_event(data: dict) -> dict:
    """Create a new equipment event."""
    return _request("POST", "/equipment/events", json=data)


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
    return _request("GET", f"/equipment/{equipment_id}/lifecycle", params=params).get("events", [])


def list_data_provenance_lookup() -> list[dict]:
    """Return data provenance types for dropdowns."""
    return _request("GET", "/ingest/lookup/data-provenance")


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
    return _request("POST", "/ingest/sensor-image", data=form_data, files={"image": (filename, image_bytes)},)


def ingest_sensor(data: dict) -> dict:
    return _request("POST", "/ingest/sensor", json=data)


def ingest_sensor_vector(data: dict) -> dict:
    return _request("POST", "/ingest/sensor-vector", json=data)


def ingest_sensor_matrix(data: dict) -> dict:
    return _request("POST", "/ingest/sensor-matrix", json=data)


def ingest_lab(data: dict) -> dict:
    return _request("POST", "/ingest/lab", json=data)


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
    return _request("POST", "/ingest/lab-image", data=form_data, files=files)


def create_sample(data: dict) -> dict:
    """Create a new sample and return sample_id."""
    return _request("POST", "/ingest/samples", json=data)


# ---------------------------------------------------------------------------
# Value Binning Axes
# ---------------------------------------------------------------------------


def list_binning_axes() -> list[dict]:
    """Return all ValueBinningAxis rows with unit names."""
    return _request("GET", "/value-binning-axes")


def get_binning_axis(axis_id: int) -> dict:
    """Return a single ValueBinningAxis with its bins."""
    return _request("GET", f"/value-binning-axes/{axis_id}")


def list_binning_axes_lookup() -> list[dict]:
    """Return lightweight list for dropdowns."""
    return _request("GET", "/value-binning-axes/lookup")


def create_binning_axis(data: dict) -> dict:
    """Create a new ValueBinningAxis with bins."""
    return _request("POST", "/value-binning-axes", json=data)


def delete_binning_axis(axis_id: int) -> None:
    """Delete a ValueBinningAxis and its bins."""
    return _request("DELETE", f"/value-binning-axes/{axis_id}")


def update_binning_axis(axis_id: int, data: dict) -> dict:
    """Partial update of a ValueBinningAxis."""
    return _request("PATCH", f"/value-binning-axes/{axis_id}", json=data)


def list_das_lookup() -> list[dict]:
    """Return list of {das_id, name} for dropdowns."""
    return _request("GET", "/signal-interfaces/das/lookup")


def list_tags_lookup(das_id: int) -> list[dict]:
    """Return [{signal_interface_id, name}] tags for a DAS (strict-mode dropdowns)."""
    return _request("GET", "/ingest/lookup/tags", params={"das_id": das_id})


def list_das_kinds() -> list[dict]:
    """Return [{das_kind_id, name, description}] for DAS category dropdowns."""
    return _request("GET", "/vocab/das-kinds")


def list_controller_kinds() -> list[dict]:
    """Return [{controller_kind_id, name, description}] for controller type dropdowns."""
    return _request("GET", "/vocab/controller-kinds")


def create_das(data: dict) -> dict:
    """Create a new Data Acquisition System."""
    return _request("POST", "/signal-interfaces/das", json=data)


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
    return _request("POST", f"/das/{das_id}/deploy", json=payload)


def get_das_conflict(das_id: int, site_id: int) -> dict | None:
    """Return conflict info if DAS is currently active at a different site, else None."""
    data = _request("GET", f"/das/{das_id}/conflict-check", params={"site_id": site_id})
    return data if data.get("conflict") else None


def update_das(das_id: int, data: dict) -> dict:
    return _request("PUT", f"/signal-interfaces/das/{das_id}", json=data)


def delete_das(das_id: int) -> None:
    return _request("DELETE", f"/signal-interfaces/das/{das_id}")


def list_persons() -> list[dict]:
    """Return all persons with full fields."""
    return _request("GET", "/persons")


def list_persons_lookup() -> list[dict]:
    """Return list of {person_id, label} for dropdowns."""
    return _request("GET", "/persons/lookup")


def create_person(data: dict) -> dict:
    """Create a new person. Returns {person_id, first_name, last_name, email}."""
    return _request("POST", "/persons/", json=data)


def update_person(person_id: int, data: dict) -> dict:
    return _request("PUT", f"/persons/{person_id}", json=data)


def delete_person(person_id: int) -> None:
    return _request("DELETE", f"/persons/{person_id}")


# ---------------------------------------------------------------------------
# Equipment move (v4.0.0 — EquipmentWiringHistory / EquipmentLocationHistory)
# ---------------------------------------------------------------------------


def register_equipment_at_interface(equipment_id: int, data: dict) -> dict:
    return _request("POST", f"/equipment/{equipment_id}/register-interface", json=data)


def rewire_equipment(equipment_id: int, data: dict) -> dict:
    return _request("POST", f"/equipment/{equipment_id}/rewire", json=data)


def relocate_equipment(equipment_id: int, data: dict) -> dict:
    return _request("POST", f"/equipment/{equipment_id}/relocate", json=data)


def get_wiring_at_time(equipment_id: int, at: str) -> dict:
    return _request("GET", f"/equipment/{equipment_id}/wiring-at", params={"at": at})


def get_location_at_time(equipment_id: int, at: str) -> dict:
    return _request("GET", f"/equipment/{equipment_id}/location-at", params={"at": at})


# ---------------------------------------------------------------------------
# ControlLoop
# ---------------------------------------------------------------------------


def list_control_loops() -> list[dict]:
    return _request("GET", "/control-loops")


def create_control_loop(data: dict) -> dict:
    return _request("POST", "/control-loops", json=data)


def get_control_loop(loop_id: int) -> dict:
    return _request("GET", f"/control-loops/{loop_id}")


def list_control_loop_ports(loop_id: int) -> dict:
    return _request("GET", f"/control-loops/{loop_id}/ports")


def add_control_loop_port(loop_id: int, data: dict) -> dict:
    return _request("POST", f"/control-loops/{loop_id}/ports", json=data)


def get_active_application(loop_id: int) -> dict | None:
    """Return the active application for a control loop, or None if none exists."""
    return _request("GET", f"/control-loops/{loop_id}/active-application")


def open_application(loop_id: int, data: dict) -> dict:
    return _request("POST", f"/control-loops/{loop_id}/applications", json=data)


def retune_control_loop(loop_id: int, data: dict) -> dict:
    return _request("POST", f"/control-loops/{loop_id}/retune", json=data)


def get_fallback_chain(loop_id: int) -> dict:
    return _request("GET", f"/control-loops/{loop_id}/fallback-chain")


# ---------------------------------------------------------------------------
# Tagless sensor ingest
# ---------------------------------------------------------------------------


def ingest_sensor_tagless(data: dict) -> dict:
    return _request("POST", "/ingest/sensor-tagless", json=data)


# ---------------------------------------------------------------------------
# QualityCode
# ---------------------------------------------------------------------------


def list_quality_codes() -> list[dict]:
    return _request("GET", "/quality-codes")


def create_quality_code(data: dict) -> dict:
    return _request("POST", "/quality-codes", json=data)


def update_quality_code(qc_id: int, data: dict) -> dict:
    return _request("PUT", f"/quality-codes/{qc_id}", json=data)


def delete_quality_code(qc_id: int) -> None:
    return _request("DELETE", f"/quality-codes/{qc_id}")


def bulk_set_quality_code(
    channel_id: int,
    start_time: str,
    end_time: str,
    quality_code_id: int,
) -> dict:
    """Set a quality code on all value rows in [start_time, end_time] for a channel."""
    return _request("PATCH", f"/timeseries/{channel_id}/quality-code", json={ "start_time": start_time, "end_time": end_time, "quality_code_id": quality_code_id, },)


# ---------------------------------------------------------------------------
# SampleKind
# ---------------------------------------------------------------------------


def list_sample_kinds() -> list[dict]:
    return _request("GET", "/sample-kinds")


def create_sample_kind(data: dict) -> dict:
    return _request("POST", "/sample-kinds", json=data)


def update_sample_kind(sample_kind_id: int, data: dict) -> dict:
    return _request("PUT", f"/sample-kinds/{sample_kind_id}", json=data)


def delete_sample_kind(sample_kind_id: int) -> None:
    return _request("DELETE", f"/sample-kinds/{sample_kind_id}")


# ---------------------------------------------------------------------------
# SampleCollectionKind
# ---------------------------------------------------------------------------


def list_sample_collection_kinds() -> list[dict]:
    return _request("GET", "/sample-collection-kinds")


def create_sample_collection_kind(data: dict) -> dict:
    return _request("POST", "/sample-collection-kinds", json=data)


def update_sample_collection_kind(sample_collection_kind_id: int, data: dict) -> dict:
    return _request("PUT", f"/sample-collection-kinds/{sample_collection_kind_id}", json=data)


def delete_sample_collection_kind(sample_collection_kind_id: int) -> None:
    return _request("DELETE", f"/sample-collection-kinds/{sample_collection_kind_id}")


# ---------------------------------------------------------------------------
# ProcessUnit
# ---------------------------------------------------------------------------


def list_process_unit_types() -> list[dict]:
    return _request("GET", "/process-unit-kinds")


def create_process_unit_type(data: dict) -> dict:
    return _request("POST", "/process-unit-kinds", json=data)


def update_process_unit_type(process_unit_kind_id: int, data: dict) -> dict:
    return _request("PUT", f"/process-unit-kinds/{process_unit_kind_id}", json=data)


def delete_process_unit_type(process_unit_kind_id: int) -> None:
    return _request("DELETE", f"/process-unit-kinds/{process_unit_kind_id}")


def list_process_units(site_id: int | None = None, tree: bool = False) -> list[dict]:
    params: dict = {}
    if site_id is not None:
        params["site_id"] = site_id
    if tree:
        params["tree"] = "true"
    return _request("GET", "/process-units", params=params)


def get_process_unit(process_unit_id: int) -> dict:
    return _request("GET", f"/process-units/{process_unit_id}")


def list_process_units_lookup(site_id: int | None = None) -> list[dict]:
    params: dict = {}
    if site_id is not None:
        params["site_id"] = site_id
    return _request("GET", "/process-units/lookup", params=params)


def create_process_unit(data: dict) -> dict:
    return _request("POST", "/process-units", json=data)


def update_process_unit(process_unit_id: int, data: dict) -> dict:
    return _request("PUT", f"/process-units/{process_unit_id}", json=data)


def patch_process_unit(process_unit_id: int, data: dict) -> dict:
    return _request("PATCH", f"/process-units/{process_unit_id}", json=data)


def delete_process_unit(process_unit_id: int) -> None:
    return _request("DELETE", f"/process-units/{process_unit_id}")


# ---------------------------------------------------------------------------
# CampaignKind
# ---------------------------------------------------------------------------


def create_campaign_kind(data: dict) -> dict:
    return _request("POST", "/campaigns/types", json=data)


def update_campaign_kind(campaign_kind_id: int, data: dict) -> dict:
    return _request("PUT", f"/campaigns/types/{campaign_kind_id}", json=data)


def delete_campaign_kind(campaign_kind_id: int) -> None:
    return _request("DELETE", f"/campaigns/types/{campaign_kind_id}")


# ---------------------------------------------------------------------------
# BinKind (read-only)
# ---------------------------------------------------------------------------


def list_bin_kinds() -> list[dict]:
    return _request("GET", "/value-binning-axes/bin-kinds")


# ---------------------------------------------------------------------------
# OperationKind (read-only, ADR 0005 — replaces ProcessingKind)
# ---------------------------------------------------------------------------


def list_operation_kinds() -> list[dict]:
    return _request("GET", "/vocab/operation-kinds")


# ---------------------------------------------------------------------------
# EquipmentEventKind CRUD (list already exists above at /equipment/event-types)
# ---------------------------------------------------------------------------


def create_equipment_event_kind(data: dict) -> dict:
    return _request("POST", "/equipment/event-types", json=data)


def update_equipment_event_kind(event_type_id: int, data: dict) -> dict:
    return _request("PUT", f"/equipment/event-types/{event_type_id}", json=data)


def delete_equipment_event_kind(event_type_id: int) -> None:
    return _request("DELETE", f"/equipment/event-types/{event_type_id}")


# ---------------------------------------------------------------------------
# ProcedureKind
# ---------------------------------------------------------------------------


def list_procedure_kinds() -> list[dict]:
    return _request("GET", "/vocab/procedure-kinds")


def create_procedure_kind(data: dict) -> dict:
    return _request("POST", "/vocab/procedure-kinds", json=data)


def update_procedure_kind(procedure_kind_id: int, data: dict) -> dict:
    return _request("PUT", f"/vocab/procedure-kinds/{procedure_kind_id}", json=data)


def delete_procedure_kind(procedure_kind_id: int) -> None:
    return _request("DELETE", f"/vocab/procedure-kinds/{procedure_kind_id}")


# ---------------------------------------------------------------------------
# Procedures
# ---------------------------------------------------------------------------


def list_procedures() -> list[dict]:
    return _request("GET", "/vocab/procedures")


def create_procedure(data: dict) -> dict:
    return _request("POST", "/vocab/procedures", json=data)


def update_procedure(procedure_id: int, data: dict) -> dict:
    return _request("PUT", f"/vocab/procedures/{procedure_id}", json=data)


def delete_procedure(procedure_id: int) -> None:
    return _request("DELETE", f"/vocab/procedures/{procedure_id}")


# ---------------------------------------------------------------------------
# Watershed
# ---------------------------------------------------------------------------


def list_watersheds() -> list[dict]:
    return _request("GET", "/vocab/watersheds")


def create_watershed(data: dict) -> dict:
    return _request("POST", "/vocab/watersheds", json=data)


def update_watershed(watershed_id: int, data: dict) -> dict:
    return _request("PUT", f"/vocab/watersheds/{watershed_id}", json=data)


def delete_watershed(watershed_id: int) -> None:
    return _request("DELETE", f"/vocab/watersheds/{watershed_id}")


def get_land_use(watershed_id: int) -> dict | None:
    """Return land use data for a watershed, or None if not set."""
    # ponytail: 404→None is this route's only special case; not worth a _request flag
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
    return _request("PUT", f"/vocab/watersheds/{watershed_id}/land-use", json=data)


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


def list_operation_kind_lookup() -> list[dict]:
    return list_operation_kinds()


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
    return _request("GET", f"/equipment/models/{model_id}/parameters")


def add_model_parameter(model_id: int, parameter_id: int) -> dict:
    return _request("POST", f"/equipment/models/{model_id}/parameters", json={"parameter_id": parameter_id})


def remove_model_parameter(model_id: int, parameter_id: int) -> None:
    return _request("DELETE", f"/equipment/models/{model_id}/parameters/{parameter_id}")


def list_model_procedures(model_id: int) -> list[dict]:
    return _request("GET", f"/equipment/models/{model_id}/procedures")


def add_model_procedure(model_id: int, procedure_id: int) -> dict:
    return _request("POST", f"/equipment/models/{model_id}/procedures", json={"procedure_id": procedure_id})


def remove_model_procedure(model_id: int, procedure_id: int) -> None:
    return _request("DELETE", f"/equipment/models/{model_id}/procedures/{procedure_id}")


# ---------------------------------------------------------------------------
# ParameterHasUnit associations
# ---------------------------------------------------------------------------


def list_parameter_units(parameter_id: int) -> list[dict]:
    return _request("GET", f"/parameters/{parameter_id}/units")


def add_parameter_unit(parameter_id: int, unit_id: int) -> dict:
    return _request("POST", f"/parameters/{parameter_id}/units", json={"unit_id": unit_id})


def remove_parameter_unit(parameter_id: int, unit_id: int) -> None:
    return _request("DELETE", f"/parameters/{parameter_id}/units/{unit_id}")


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


def signup(email: str, full_name: str, password: str) -> dict:
    return _request("POST", "/auth/signup", json={"email": email, "full_name": full_name, "password": password},)


def login(email: str, password: str) -> dict:
    return _request("POST", "/auth/login", json={"email": email, "password": password},)


def get_me() -> dict:
    return _request("GET", "/auth/me")


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
    return _request("GET", "/audit/logs", params=params)



# ---------------------------------------------------------------------------
# Lab ingest lookups (experiments, series, templates)
# ---------------------------------------------------------------------------


def list_lab_experiments_lookup() -> list[dict]:
    """Return recent LabExperiments for dropdown."""
    return _request("GET", "/ingest/lab/experiments/lookup")


def get_lab_experiment_series(experiment_id: int) -> list[dict]:
    """Return distinct AnalysisSeries used in a LabExperiment."""
    return _request("GET", f"/ingest/lab/experiments/{experiment_id}/series")


def list_deployment_traces_lookup(
    sampling_point_id: int | None = None,
    campaign_id: int | None = None,
    parameter_id: int | None = None,
    value_kind_id: int | None = None,
    from_dt: str | None = None,
    to_dt: str | None = None,
) -> list[dict]:
    """Return Deployment Trace lookup rows for the Data Explorer sensor picker."""
    params: dict = {}
    if sampling_point_id is not None:
        params["sampling_point_id"] = sampling_point_id
    if campaign_id is not None:
        params["campaign_id"] = campaign_id
    if parameter_id is not None:
        params["parameter_id"] = parameter_id
    if value_kind_id is not None:
        params["value_kind_id"] = value_kind_id
    if from_dt is not None:
        params["from_dt"] = from_dt
    if to_dt is not None:
        params["to_dt"] = to_dt
    return _request("GET", "/deployment-traces/lookup", params=params)


def list_analysis_series_lookup() -> list[dict]:
    """Return all AnalysisSeries for dropdown."""
    return _request("GET", "/ingest/lab/analysis-series/lookup")


def create_analysis_series(data: dict) -> dict:
    """Create a new AnalysisSeries. Returns {analysis_series_id}."""
    return _request("POST", "/ingest/lab/analysis-series", json=data)


def list_lab_panels() -> list[dict]:
    """Return templates with series count."""
    return _request("GET", "/ingest/lab/templates")


def get_lab_panel(template_id: int) -> dict:
    """Return template with its series list."""
    return _request("GET", f"/ingest/lab/templates/{template_id}")


def create_lab_panel(data: dict) -> dict:
    """Create panel with series. Returns {lab_panel_id}."""
    return _request("POST", "/ingest/lab/templates", json=data)


def patch_lab_panel(lab_panel_id: int, data: dict) -> dict:
    """Partial update of a panel. If series_ids is included, replaces the full list."""
    return _request("PATCH", f"/ingest/lab/templates/{lab_panel_id}", json=data)


def delete_lab_panel(lab_panel_id: int) -> None:
    """Delete a panel and its series rows."""
    return _request("DELETE", f"/ingest/lab/templates/{lab_panel_id}")


def add_series_to_template(template_id: int, analysis_series_id: int) -> None:
    """Add an AnalysisSeries to a template."""
    return _request("POST", f"/ingest/lab/templates/{template_id}/series", json={"analysis_series_id": analysis_series_id},)


def remove_series_from_template(template_id: int, analysis_series_id: int) -> None:
    """Remove an AnalysisSeries from a template."""
    return _request("DELETE", f"/ingest/lab/templates/{template_id}/series/{analysis_series_id}")



def list_sample_collection_kinds_lookup() -> list[dict]:
    """Return sample collection kinds for dropdown (wrapper for consistency)."""
    return list_sample_collection_kinds()


def list_sample_kinds_lookup() -> list[dict]:
    """Return sample kinds for dropdown (wrapper for consistency)."""
    return list_sample_kinds()


# ---------------------------------------------------------------------------
# Reference-data caching
# ---------------------------------------------------------------------------
# The ``list_*_lookup`` functions return slowly-changing reference data that
# pages re-fetch on every Streamlit rerun (i.e. on every keystroke/widget
# change), hammering the API. Wrap them all in st.cache_data so repeated reads
# within the TTL are served from memory. Auto-discovery keeps new lookups
# cached without touching this block. Mutations invalidate via
# clear_lookup_caches() (called by generic_crud after create/update/delete).
import types as _types

_LOOKUP_TTL_SECONDS = 60

_CACHED_LOOKUP_NAMES = sorted(
    name
    for name, obj in list(globals().items())
    if name.startswith("list_")
    and name.endswith("_lookup")
    and isinstance(obj, _types.FunctionType)
)

for _name in _CACHED_LOOKUP_NAMES:
    globals()[_name] = st.cache_data(ttl=_LOOKUP_TTL_SECONDS)(globals()[_name])


def clear_lookup_caches() -> None:
    """Invalidate all cached reference-data lookups.

    Call after any create/update/delete so freshly changed reference data is
    visible immediately instead of waiting for the cache TTL to expire.
    """
    for _name in _CACHED_LOOKUP_NAMES:
        fn = globals().get(_name)
        clear = getattr(fn, "clear", None)
        if callable(clear):
            clear()
