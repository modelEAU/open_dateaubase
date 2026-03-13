"""HTTP client for the open_datEAUbase REST API.

Provides synchronous access to:
- Name→ID resolution for Equipment, Parameter, and Unit (cached per instance)
- GET /api/v1/ingest/last-timestamp  (deduplication watermark)
- POST /api/v1/ingest/sensor         (bulk scalar ingest)
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
    """Thin synchronous wrapper around the open_datEAUbase REST API.

    All name→ID caches are populated lazily on first use and held for the
    lifetime of the client instance (one import run).
    """

    def __init__(self, api_url: str, timeout: float = 300.0) -> None:
        self._base = api_url.rstrip("/")
        self._client = httpx.Client(timeout=timeout)
        self._equipment_by_name: dict[str, int] | None = None
        self._parameter_by_name: dict[str, int] | None = None
        self._unit_by_name: dict[str, int] | None = None

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

    def _ensure_equipment_cache(self) -> None:
        if self._equipment_by_name is not None:
            return
        items = self._get("/api/v1/channels/lookup/equipment")
        # [{"equipment_id": int, "identifier": str}]
        self._equipment_by_name = {row["identifier"]: row["equipment_id"] for row in items}

    def _ensure_parameter_cache(self) -> None:
        if self._parameter_by_name is not None:
            return
        items = self._get("/api/v1/channels/lookup/parameters")
        # [{"parameter_id": int, "parameter_name": str}]
        self._parameter_by_name = {row["parameter_name"]: row["parameter_id"] for row in items}

    def _ensure_unit_cache(self) -> None:
        if self._unit_by_name is not None:
            return
        items = self._get("/api/v1/ingest/lookup/units")
        # [{"unit_id": int, "unit": str}]
        self._unit_by_name = {row["unit"]: row["unit_id"] for row in items}

    # ------------------------------------------------------------------
    # Public name→ID resolution
    # ------------------------------------------------------------------

    def resolve_equipment_id(self, identifier: str) -> int:
        """Return Equipment_ID for the given Identifier string.

        Raises ValueError if no matching equipment exists.
        """
        self._ensure_equipment_cache()
        assert self._equipment_by_name is not None
        if identifier not in self._equipment_by_name:
            available = sorted(self._equipment_by_name)
            raise ValueError(
                f"Equipment identifier {identifier!r} not found. "
                f"Available: {available}"
            )
        return self._equipment_by_name[identifier]

    def resolve_parameter_id(self, name: str) -> int:
        """Return Parameter_ID for the given parameter name.

        Raises ValueError if no matching parameter exists.
        """
        self._ensure_parameter_cache()
        assert self._parameter_by_name is not None
        if name not in self._parameter_by_name:
            available = sorted(self._parameter_by_name)
            raise ValueError(
                f"Parameter {name!r} not found. Available: {available}"
            )
        return self._parameter_by_name[name]

    def resolve_unit_id(self, name: str) -> int:
        """Return Unit_ID for the given unit name.

        Raises ValueError if no matching unit exists.
        """
        self._ensure_unit_cache()
        assert self._unit_by_name is not None
        if name not in self._unit_by_name:
            available = sorted(self._unit_by_name)
            raise ValueError(
                f"Unit {name!r} not found. Available: {available}"
            )
        return self._unit_by_name[name]

    # ------------------------------------------------------------------
    # Deduplication watermark
    # ------------------------------------------------------------------

    def get_last_timestamp(
        self,
        *,
        equipment_id: int,
        parameter_id: int,
        data_provenance_id: int,
        processing_degree_id: int,
    ) -> datetime | None:
        """Return the most recent ingested timestamp for a channel, or None.

        The returned datetime is always UTC-aware.
        """
        payload = self._get(
            "/api/v1/ingest/last-timestamp",
            equipment_id=equipment_id,
            parameter_id=parameter_id,
            data_provenance_id=data_provenance_id,
            processing_degree_id=processing_degree_id,
        )
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
        equipment_id: int,
        parameter_id: int,
        unit_id: int,
        data_provenance_id: int,
        processing_degree_id: int,
        values: list[dict],
    ) -> dict:
        """POST a batch of scalar sensor values.

        Each item in values: {"timestamp": "<ISO 8601>", "value": float}.
        Returns IngestResponse dict: {"channel_id": int, "rows_written": int}.
        """
        body = {
            "equipment_id": equipment_id,
            "parameter_id": parameter_id,
            "unit_id": unit_id,
            "data_provenance_id": data_provenance_id,
            "processing_degree_id": processing_degree_id,
            "values": values,
        }
        return self._post("/api/v1/ingest/sensor", body)
