"""HTTP client for the open_datEAUbase REST API.

Provides synchronous access to:
- POST /api/v1/ingest/resolve-channel          (tagged — channel pre-resolution)
- POST /api/v1/ingest/resolve-channel-tagless  (tagless — channel pre-resolution)
- GET  /api/v1/ingest/last-timestamp           (deduplication watermark, by channel_id)
- POST /api/v1/ingest/sensor                   (tagged bulk scalar ingest)
- POST /api/v1/ingest/sensor-tagless           (tagless bulk scalar ingest)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx


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
