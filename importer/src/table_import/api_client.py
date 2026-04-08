"""HTTP client for the open_datEAUbase REST API.

Provides synchronous access to:
- POST /api/v1/ingest/resolve-channel          (tagged — channel pre-resolution)
- POST /api/v1/ingest/resolve-channel-tagless  (tagless — channel pre-resolution)
- GET  /api/v1/ingest/last-timestamp           (deduplication watermark, by channel_id)
- POST /api/v1/ingest/sensor                   (tagged bulk scalar ingest)
- POST /api/v1/ingest/sensor-tagless           (tagless bulk scalar ingest)
- POST /api/v1/binning-axes/resolve            (find-or-create binning axis)
- POST /api/v1/ingest/sensor-vector            (tagged bulk vector ingest)
- POST /api/v1/ingest/sensor-image             (tagged/tagless image ingest, multipart)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx

from table_import.config import AxisConfig


class ApiError(Exception):
    """Raised when the API returns an unexpected HTTP status."""

    def __init__(self, method: str, url: str, status: int, body: str) -> None:
        super().__init__(f"{method} {url} → HTTP {status}: {body}")
        self.status_code = status


class DateaubaseClient:
    """Thin synchronous wrapper around the open_datEAUbase REST API."""

    def __init__(self, api_url: str, timeout: float = 300.0) -> None:
        self._base = api_url.rstrip("/")
        self._client = httpx.Client(timeout=timeout)

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
    ) -> tuple[int, list[str]]:
        """POST /api/v1/ingest/resolve-channel → (channel_id, warnings)."""
        body = {
            "das_name": das_name,
            "tag": tag,
            "signal_port_type": signal_port_type,
            "parent_tag": parent_tag,
            "parameter_name": parameter_name,
            "unit_name": unit_name,
            "data_provenance_id": data_provenance_id,
            "processing_degree_id": processing_degree_id,
        }
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
    ) -> tuple[int, list[str]]:
        """POST /api/v1/ingest/resolve-channel-tagless → (channel_id, warnings)."""
        body = {
            "das_name": das_name,
            "equipment_name": equipment_name,
            "parameter_name": parameter_name,
            "unit_name": unit_name,
            "data_provenance_id": data_provenance_id,
            "processing_degree_id": processing_degree_id,
        }
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
    ) -> dict:
        """POST /api/v1/ingest/sensor — tagged bulk scalar ingest.

        Each item in values: {"timestamp": "<ISO 8601>", "value": float}.
        Returns IngestResponse dict: {"channel_id": int, "rows_written": int, "warnings": list}.
        """
        body = {
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
    ) -> dict:
        """POST /api/v1/ingest/sensor-tagless — tagless bulk scalar ingest.

        Each item in values: {"timestamp": "<ISO 8601>", "value": float}.
        Returns IngestResponse dict: {"channel_id": int, "rows_written": int, "warnings": list}.
        """
        body = {
            "das_name": das_name,
            "equipment_name": equipment_name,
            "parameter_name": parameter_name,
            "unit_name": unit_name,
            "data_provenance_id": data_provenance_id,
            "processing_degree_id": processing_degree_id,
            "values": values,
        }
        return self._post("/api/v1/ingest/sensor-tagless", body)

    # ------------------------------------------------------------------
    # Binning axis find-or-create
    # ------------------------------------------------------------------

    def resolve_binning_axis(self, *, axis: AxisConfig) -> tuple[int, bool, list[str]]:
        """POST /api/v1/binning-axes/resolve → (axis_id, created, warnings).

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
            "bin_mode": axis.bin_mode,
            "bins": bins_payload,
        }
        payload = self._post("/api/v1/binning-axes/resolve", body)
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
        parent_tag: str | None = None,
        parameter_name: str,
        unit_name: str,
        binning_axis_id: int,
        data_provenance_id: int = 1,
        processing_degree_id: int = 1,
        observations: list[dict],
    ) -> dict:
        """POST /api/v1/ingest/sensor-vector — tagged bulk vector ingest.

        Each observation: {"timestamp": "<ISO 8601>", "bin_values": list[float|None],
                           "quality_code": int|None}.
        Returns IngestResponse dict: {"channel_id": int, "rows_written": int, "warnings": list}.
        """
        body = {
            "das_name": das_name,
            "tag": tag,
            "signal_port_type": signal_port_type,
            "parent_tag": parent_tag,
            "parameter_name": parameter_name,
            "unit_name": unit_name,
            "binning_axis_id": binning_axis_id,
            "data_provenance_id": data_provenance_id,
            "processing_degree_id": processing_degree_id,
            "observations": observations,
        }
        return self._post("/api/v1/ingest/sensor-vector", body)

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
        return self._post_multipart("/api/v1/ingest/sensor-image", form_data, image_path)
