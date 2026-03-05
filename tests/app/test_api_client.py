"""Tests for app/api_client.py public functions using httpx mock transport."""
from __future__ import annotations

import httpx
import pytest

import app.api_client as ac
from app.api_client import APIError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _handler(status_code: int, body: dict | None = None):
    """Return an httpx handler that responds with the given status and JSON body."""

    def handle(request: httpx.Request) -> httpx.Response:
        if body is not None:
            return httpx.Response(status_code, json=body)
        return httpx.Response(status_code)

    return handle


def _patch(monkeypatch, handler) -> None:
    """Monkeypatch _get_client to return a fresh client backed by handler each call."""
    monkeypatch.setattr(
        ac,
        "_get_client",
        lambda: httpx.Client(
            transport=httpx.MockTransport(handler), base_url="http://test"
        ),
    )


# ---------------------------------------------------------------------------
# Sites — GET list, GET single, POST, PUT, DELETE
# ---------------------------------------------------------------------------


class TestSites:
    def test_list_sites_returns_items(self, monkeypatch):
        body = {"items": [{"id": 1, "name": "Site A"}], "total": 1}
        _patch(monkeypatch, _handler(200, body))
        result = ac.list_sites()
        assert "items" in result

    def test_get_site_returns_dict(self, monkeypatch):
        body = {"id": 1, "name": "Site A"}
        _patch(monkeypatch, _handler(200, body))
        result = ac.get_site(1)
        assert result["id"] == 1

    def test_create_site_returns_created(self, monkeypatch):
        body = {"id": 99, "name": "New Site"}
        _patch(monkeypatch, _handler(201, body))
        result = ac.create_site({"name": "New Site"})
        assert result["id"] == 99

    def test_update_site_returns_updated(self, monkeypatch):
        body = {"id": 1, "name": "Updated"}
        _patch(monkeypatch, _handler(200, body))
        result = ac.update_site(1, {"name": "Updated"})
        assert result["name"] == "Updated"

    def test_delete_site_returns_none(self, monkeypatch):
        _patch(monkeypatch, _handler(204))
        result = ac.delete_site(1)
        assert result is None

    def test_get_site_404_raises_api_error(self, monkeypatch):
        _patch(monkeypatch, _handler(404, {"detail": "Not found"}))
        with pytest.raises(APIError) as exc_info:
            ac.get_site(999)
        assert exc_info.value.status_code == 404

    def test_create_site_422_raises_api_error(self, monkeypatch):
        _patch(monkeypatch, _handler(422, {"detail": "Validation error"}))
        with pytest.raises(APIError) as exc_info:
            ac.create_site({})
        assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# Connection error → 503
# ---------------------------------------------------------------------------


class TestConnectionError:
    def test_connect_error_raises_503(self, monkeypatch):
        def raise_connect_error(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Connection refused")

        _patch(monkeypatch, raise_connect_error)
        with pytest.raises(APIError) as exc_info:
            ac.get_site(1)
        assert exc_info.value.status_code == 503

    def test_list_sites_connect_error_raises_503(self, monkeypatch):
        def raise_connect_error(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("Connection refused")

        _patch(monkeypatch, raise_connect_error)
        with pytest.raises(APIError) as exc_info:
            ac.list_sites()
        assert exc_info.value.status_code == 503


# ---------------------------------------------------------------------------
# Channels — filter param forwarding
# ---------------------------------------------------------------------------


class TestChannels:
    def test_list_channels_with_parameter_id_included_in_url(self, monkeypatch):
        received: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            received.update(dict(request.url.params))
            return httpx.Response(200, json={"items": []})

        _patch(monkeypatch, handler)
        ac.list_channels(parameter_id=5)
        assert received.get("parameter_id") == "5"

    def test_list_channels_without_parameter_id_omits_param(self, monkeypatch):
        received: dict = {}

        def handler(request: httpx.Request) -> httpx.Response:
            received.update(dict(request.url.params))
            return httpx.Response(200, json={"items": []})

        _patch(monkeypatch, handler)
        ac.list_channels(parameter_id=None)
        assert "parameter_id" not in received


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------


class TestIngestion:
    def test_ingest_sensor_returns_channel_id_and_rows_written(self, monkeypatch):
        body = {"channel_id": 42, "rows_written": 100}
        _patch(monkeypatch, _handler(201, body))
        result = ac.ingest_sensor({"equipment_id": 1, "parameter_id": 2})
        assert result["channel_id"] == 42
        assert result["rows_written"] == 100

    def test_ingest_lab_returns_dict(self, monkeypatch):
        body = {"lab_analysis_id": 7, "rows_written": 5}
        _patch(monkeypatch, _handler(201, body))
        result = ac.ingest_lab({"sample_id": 1})
        assert "lab_analysis_id" in result
