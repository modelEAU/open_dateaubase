"""HTTP client for the open_datEAUbase REST API.

Provides synchronous access to:
- POST /api/v1/ingest/resolve-channel              (tagged — channel pre-resolution)
- POST /api/v1/ingest/resolve-channel-tagless      (tagless — channel pre-resolution)
- GET  /api/v1/ingest/last-timestamp               (deduplication watermark, by channel_id)
- POST /api/v1/ingest/sensor                       (tagged bulk scalar ingest)
- POST /api/v1/ingest/sensor-tagless               (tagless bulk scalar ingest)
- POST /api/v1/value-binning-axes/resolve          (find-or-create binning axis)
- POST /api/v1/ingest/sensor-vector                (tagged bulk vector ingest)
- POST /api/v1/ingest/sensor-image                 (tagged/tagless image ingest, multipart)
- POST /api/v1/signal-interfaces/provision         (find-or-create SI by name)
- POST /api/v1/signal-interface-ports/provision    (find-or-create port by name)
- POST /api/v1/channels/provision                  (find-or-create channel by name)
- POST /api/v1/channels/{id}/port-history          (open ChannelPortHistory row)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from table_import.config import AxisConfig


class ConfigValidationError(Exception):
    """Raised when a config (parameter, unit) pair is not in ParameterHasUnit."""


class ApiError(Exception):
    """Raised when the API returns an unexpected HTTP status."""

    def __init__(self, method: str, url: str, status: int, body: str) -> None:
        super().__init__(f"{method} {url} → HTTP {status}: {body}")
        self.status_code = status


class DateaubaseClient:
    """Thin synchronous wrapper around the open_datEAUbase REST API."""

    def __init__(
        self, api_url: str, timeout: float = 300.0, token: str | None = None
    ) -> None:
        self._base = api_url.rstrip("/")
        headers = {"Authorization": f"Bearer {token}"} if token else None
        self._client = httpx.Client(timeout=timeout, headers=headers)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> DateaubaseClient:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get(self, path: str, **params: Any) -> Any:
        url = f"{self._base}{path}"
        r = self._client.get(url, params=params)
        if not r.is_success:
            raise ApiError("GET", url, r.status_code, r.text)
        return r.json()

    def _post(self, path: str, body: dict) -> Any:
        url = f"{self._base}{path}"
        r = self._client.post(url, json=body)
        if not r.is_success:
            raise ApiError("POST", url, r.status_code, r.text)
        return r.json()

    # ------------------------------------------------------------------
    # Channel resolution (no data written)
    # ------------------------------------------------------------------

    def resolve_channel(
        self,
        *,
        das_name: str,
        tag: str,
        signal_port_type: str = "value",
        parent_tag: str | None = None,
        parameter_name: str,
        unit_name: str,
        data_provenance_id: int = 1,
        processing_degree_id: int = 1,
        value_type_id: int = 1,
        signal_interface_name: str | None = None,
    ) -> tuple[int, list[str]]:
        """POST /api/v1/ingest/resolve-channel → (channel_id, warnings)."""
        body: dict[str, Any] = {
            "das_name": das_name,
            "tag": tag,
            "channel_kind": signal_port_type,
            "parent_tag": parent_tag,
            "parameter_name": parameter_name,
            "unit_name": unit_name,
            "data_provenance_kind_id": data_provenance_id,
            "processing_kind_id": processing_degree_id,
            "value_kind_id": value_type_id,
        }
        if signal_interface_name is not None:
            body["signal_interface_name"] = signal_interface_name
        payload = self._post("/api/v1/ingest/resolve-channel", body)
        return payload["channel_id"], payload.get("warnings", [])

    def resolve_channel_tagless(
        self,
        *,
        das_name: str,
        equipment_name: str,
        parameter_name: str,
        unit_name: str,
        data_provenance_id: int = 1,
        processing_degree_id: int = 1,
        value_type_id: int = 1,
        signal_interface_name: str | None = None,
        wiring_valid_from: str | None = None,
    ) -> tuple[int, list[str]]:
        """POST /api/v1/ingest/resolve-channel-tagless → (channel_id, warnings).

        ``wiring_valid_from`` (ISO timestamp) backdates a newly-opened wiring row
        so location/equipment views cover the data about to be ingested. Pass the
        source's min_timestamp floor.
        """
        body: dict[str, Any] = {
            "das_name": das_name,
            "equipment_name": equipment_name,
            "parameter_name": parameter_name,
            "unit_name": unit_name,
            "data_provenance_kind_id": data_provenance_id,
            "processing_kind_id": processing_degree_id,
            "value_kind_id": value_type_id,
        }
        if signal_interface_name is not None:
            body["signal_interface_name"] = signal_interface_name
        if wiring_valid_from is not None:
            body["wiring_valid_from"] = wiring_valid_from
        payload = self._post("/api/v1/ingest/resolve-channel-tagless", body)
        return payload["channel_id"], payload.get("warnings", [])

    # ------------------------------------------------------------------
    # Deduplication watermark
    # ------------------------------------------------------------------

    def get_last_timestamp(self, *, channel_id: int) -> datetime | None:
        """GET /api/v1/ingest/last-timestamp?channel_id=X → UTC datetime or None."""
        payload = self._get("/api/v1/ingest/last-timestamp", channel_id=channel_id)
        raw = payload.get("last_timestamp")
        if raw is None:
            return None
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    def ingest_sensor_values(
        self,
        *,
        das_name: str,
        tag: str,
        signal_port_type: str = "value",
        parent_tag: str | None = None,
        parameter_name: str,
        unit_name: str,
        data_provenance_id: int = 1,
        processing_degree_id: int = 1,
        values: list[dict],
        signal_interface_name: str | None = None,
    ) -> dict:
        """POST /api/v1/ingest/sensor — tagged bulk scalar ingest.

        Each item in values: {"timestamp": "<ISO 8601>", "value": float}.
        Returns IngestResponse dict: {"channel_id": int, "rows_written": int, "warnings": list}.
        """
        body: dict[str, Any] = {
            "das_name": das_name,
            "tag": tag,
            "signal_port_type": signal_port_type,
            "parent_tag": parent_tag,
            "parameter_name": parameter_name,
            "unit_name": unit_name,
            "data_provenance_id": data_provenance_id,
            "processing_degree_id": processing_degree_id,
            "values": values,
        }
        if signal_interface_name is not None:
            body["signal_interface_name"] = signal_interface_name
        return self._post("/api/v1/ingest/sensor", body)

    def ingest_sensor_values_tagless(
        self,
        *,
        das_name: str,
        equipment_name: str,
        parameter_name: str,
        unit_name: str,
        data_provenance_id: int = 1,
        processing_degree_id: int = 1,
        values: list[dict],
        signal_interface_name: str | None = None,
    ) -> dict:
        """POST /api/v1/ingest/sensor-tagless — tagless bulk scalar ingest.

        Each item in values: {"timestamp": "<ISO 8601>", "value": float}.
        Returns IngestResponse dict: {"channel_id": int, "rows_written": int, "warnings": list}.
        """
        body: dict[str, Any] = {
            "das_name": das_name,
            "equipment_name": equipment_name,
            "parameter_name": parameter_name,
            "unit_name": unit_name,
            "data_provenance_id": data_provenance_id,
            "processing_degree_id": processing_degree_id,
            "values": values,
        }
        if signal_interface_name is not None:
            body["signal_interface_name"] = signal_interface_name
        return self._post("/api/v1/ingest/sensor-tagless", body)

    # ------------------------------------------------------------------
    # Binning axis find-or-create
    # ------------------------------------------------------------------

    def resolve_binning_axis(self, *, axis: AxisConfig) -> tuple[int, bool, list[str]]:
        """POST /api/v1/value-binning-axes/resolve → (axis_id, created, warnings).

        Raises ApiError on HTTP error (including 409 fingerprint mismatch).
        """
        bins_payload = [
            {
                "bin_index": i,
                "lower_bound": b.lower_bound,
                "upper_bound": b.upper_bound,
                "nominal_value": b.nominal_value,
            }
            for i, b in enumerate(axis.bins)
        ]
        body = {
            "name": axis.name,
            "description": axis.description,
            "unit_name": axis.unit_name,
            "bin_kind": axis.bin_mode,
            "bins": bins_payload,
        }
        payload = self._post("/api/v1/value-binning-axes/resolve", body)
        return payload["axis_id"], payload["created"], payload.get("warnings", [])

    # ------------------------------------------------------------------
    # Vector ingest
    # ------------------------------------------------------------------

    def ingest_vector_observations(
        self,
        *,
        das_name: str,
        tag: str,
        signal_port_type: str = "value",
        parameter_name: str,
        unit_name: str,
        binning_axis_id: int,
        data_provenance_id: int = 1,
        processing_degree_id: int = 1,
        observations: list[dict],
        signal_interface_name: str | None = None,
    ) -> dict:
        """POST /api/v1/ingest/sensor-vector — tagged bulk vector ingest."""
        body: dict[str, Any] = {
            "das_name": das_name,
            "tag": tag,
            "channel_kind": signal_port_type,
            "parameter_name": parameter_name,
            "unit_name": unit_name,
            "binning_axis_id": binning_axis_id,
            "data_provenance_kind_id": data_provenance_id,
            "processing_kind_id": processing_degree_id,
            "observations": observations,
        }
        if signal_interface_name is not None:
            body["signal_interface_name"] = signal_interface_name
        return self._post("/api/v1/ingest/sensor-vector", body)

    def ingest_vector_observations_tagless(
        self,
        *,
        das_name: str,
        equipment_name: str,
        parameter_name: str,
        unit_name: str,
        binning_axis_id: int,
        data_provenance_id: int = 1,
        processing_degree_id: int = 1,
        observations: list[dict],
    ) -> dict:
        """POST /api/v1/ingest/sensor-vector-tagless — tagless bulk vector ingest."""
        body: dict[str, Any] = {
            "das_name": das_name,
            "equipment_name": equipment_name,
            "parameter_name": parameter_name,
            "unit_name": unit_name,
            "binning_axis_id": binning_axis_id,
            "data_provenance_kind_id": data_provenance_id,
            "processing_kind_id": processing_degree_id,
            "observations": observations,
        }
        return self._post("/api/v1/ingest/sensor-vector-tagless", body)

    # ------------------------------------------------------------------
    # Image ingest (multipart)
    # ------------------------------------------------------------------

    def _post_multipart(self, path: str, data: dict[str, Any], file_path: str) -> Any:
        """POST multipart/form-data with a single file field named 'image'."""
        url = f"{self._base}{path}"
        with open(file_path, "rb") as fh:
            import mimetypes

            mime_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
            import os

            filename = os.path.basename(file_path)
            r = self._client.post(
                url,
                data=data,
                files={"image": (filename, fh, mime_type)},
            )
        if not r.is_success:
            raise ApiError("POST", url, r.status_code, r.text)
        return r.json()

    def ingest_image(
        self,
        *,
        das_name: str,
        tag: str | None = None,
        signal_port_type: str = "value",
        equipment_name: str | None = None,
        parameter_name: str,
        unit_name: str,
        timestamp: str,
        data_provenance_id: int = 1,
        processing_degree_id: int = 1,
        image_path: str,
        signal_interface_name: str | None = None,
    ) -> dict:
        """POST /api/v1/ingest/sensor-image — image ingest via multipart/form-data.

        Returns ImageIngestResponse: {"channel_id": int, "value_image_id": int,
                                      "storage_path": str}.
        """
        form_data: dict[str, Any] = {
            "das_name": das_name,
            "signal_port_type": signal_port_type,
            "parameter_name": parameter_name,
            "unit_name": unit_name,
            "timestamp": timestamp,
            "data_provenance_id": str(data_provenance_id),
            "processing_degree_id": str(processing_degree_id),
        }
        if tag is not None:
            form_data["tag"] = tag
        if equipment_name is not None:
            form_data["equipment_name"] = equipment_name
        if signal_interface_name is not None:
            form_data["signal_interface_name"] = signal_interface_name
        return self._post_multipart(
            "/api/v1/ingest/sensor-image", form_data, image_path
        )

    # ------------------------------------------------------------------
    # L5X loader — find-or-create primitives
    # ------------------------------------------------------------------

    def create_signal_interface(
        self,
        *,
        das_name: str,
        name: str,
        type_name: str,
        make: str | None = None,
        model: str | None = None,
        description: str | None = None,
    ) -> int:
        """POST /api/v1/signal-interfaces/provision → signal_interface_id."""
        body: dict[str, Any] = {"das_name": das_name, "name": name, "type_name": type_name}
        if make is not None:
            body["make"] = make
        if model is not None:
            body["model"] = model
        if description is not None:
            body["description"] = description
        payload = self._post("/api/v1/signal-interfaces/provision", body)
        return payload["signal_interface_id"]

    def create_signal_interface_port(
        self,
        *,
        signal_interface_id: int,
        port_identifier: str,
        kind_name: str,
        description: str | None = None,
    ) -> int:
        """POST /api/v1/signal-interface-ports/provision → signal_interface_port_id."""
        body: dict[str, Any] = {
            "signal_interface_id": signal_interface_id,
            "port_identifier": port_identifier,
            "kind_name": kind_name,
        }
        if description is not None:
            body["description"] = description
        payload = self._post("/api/v1/signal-interface-ports/provision", body)
        return payload["signal_interface_port_id"]

    def create_channel(
        self,
        *,
        signal_interface_id: int,
        tag_name: str,
        parameter_name: str | None = None,
        unit_name: str | None = None,
        signal_interface_port_id: int | None = None,
        parent_channel_id: int | None = None,
        channel_kind: str = "value",
        data_provenance_id: int | None = None,
        processing_degree_id: int | None = None,
        value_type_id: int | None = None,
    ) -> int:
        """POST /api/v1/channels/provision → channel_id."""
        body: dict[str, Any] = {
            "signal_interface_id": signal_interface_id,
            "tag_name": tag_name,
            "channel_kind": channel_kind,
        }
        if parameter_name is not None:
            body["parameter_name"] = parameter_name
        if unit_name is not None:
            body["unit_name"] = unit_name
        if signal_interface_port_id is not None:
            body["signal_interface_port_id"] = signal_interface_port_id
        if parent_channel_id is not None:
            body["parent_channel_id"] = parent_channel_id
        if data_provenance_id is not None:
            body["data_provenance_id"] = data_provenance_id
        if processing_degree_id is not None:
            body["processing_degree_id"] = processing_degree_id
        if value_type_id is not None:
            body["value_type_id"] = value_type_id
        payload = self._post("/api/v1/channels/provision", body)
        return payload["channel_id"]

    # ------------------------------------------------------------------
    # Config validation
    # ------------------------------------------------------------------

    def validate_parameter_unit_pair(self, *, parameter_name: str, unit_name: str) -> None:
        """Raise ConfigValidationError if unit_name is not valid for parameter_name.

        Image parameters (ValueKind_ID == 4) are skipped entirely.
        Raises ConfigValidationError before any ingestion if the pair is absent
        from ParameterHasUnit.
        """
        param = self._get(f"/api/v1/parameters/by-name/{parameter_name}")
        value_kind_id = param.get("value_kind_id", 1)
        if value_kind_id == 4:
            return
        parameter_id = param["parameter_id"]
        valid_units = self._get(f"/api/v1/units/valid-for/{parameter_id}")
        valid_names = {u["unit"] for u in valid_units}
        if unit_name not in valid_names:
            raise ConfigValidationError(
                f"Unit '{unit_name}' is not registered as valid for parameter "
                f"'{parameter_name}'. Check ParameterHasUnit."
            )

    def open_channel_port_history(
        self,
        *,
        channel_id: int,
        port_id: int | None = None,
        valid_from: str,
        gating_note: str | None = None,
    ) -> int:
        """POST /api/v1/channels/{channel_id}/port-history → channel_port_history_id."""
        body: dict[str, Any] = {"valid_from": valid_from}
        if port_id is not None:
            body["signal_interface_port_id"] = port_id
        if gating_note is not None:
            body["gating_note"] = gating_note
        payload = self._post(f"/api/v1/channels/{channel_id}/port-history", body)
        return payload["channel_port_history_id"]
