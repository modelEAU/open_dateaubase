"""Tests for the request-timing middleware and JSON log formatter.

Covers the volume/observability fixes: health probes produce no log line,
normal requests carry level+request_id, unhandled errors emit a single-line
JSON record with a traceback, and the formatter keeps tracebacks on one line.
"""

from __future__ import annotations

import json
import logging

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from api.logging_config import JsonFormatter
from api.observability import RequestTimingMiddleware


def _app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestTimingMiddleware)

    @app.get("/")
    def root():
        return {"ok": True}

    @app.get("/api/v1/health")
    def health():
        return {"ok": True}

    @app.get("/things")
    def things():
        return {"ok": True}

    @app.get("/boom")
    def boom():
        raise RuntimeError("kaboom")

    return app


def _records(captured: str) -> list[dict]:
    return [json.loads(line) for line in captured.splitlines() if line.startswith("{")]


def test_health_paths_emit_no_record(capsys):
    client = TestClient(_app())
    client.get("/")
    client.get("/api/v1/health")
    assert _records(capsys.readouterr().out) == []


def test_normal_request_has_level_and_request_id(capsys):
    client = TestClient(_app())
    client.get("/things")
    recs = _records(capsys.readouterr().out)
    assert len(recs) == 1
    rec = recs[0]
    assert rec["level"] == "info"
    assert rec["uri"] == "/things"
    assert rec["status"] == 200
    assert len(rec["request_id"]) == 8


def test_unhandled_error_emits_traceback_record(capsys):
    client = TestClient(_app(), raise_server_exceptions=False)
    client.get("/boom")
    recs = _records(capsys.readouterr().out)
    err = [r for r in recs if r.get("level") == "error"]
    assert len(err) == 1
    assert "kaboom" in err[0]["traceback"]
    assert err[0]["uri"] == "/boom"
    assert len(err[0]["request_id"]) == 8


def test_json_formatter_is_single_line_with_traceback():
    fmt = JsonFormatter()
    try:
        raise ValueError("nope")
    except ValueError:
        record = logging.LogRecord(
            "t", logging.ERROR, __file__, 1, "boom", None, _exc_info()
        )
    out = fmt.format(record)
    assert "\n" not in out  # one physical line = one OpenObserve record
    parsed = json.loads(out)
    assert parsed["level"] == "error"
    assert "ValueError" in parsed["traceback"]


def _exc_info():
    import sys

    return sys.exc_info()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
