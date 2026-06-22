"""Request-timing middleware — emits one JSON line per request to stdout.

Vector tails the NSSM-captured stdout log, detects lines starting with '{'
as JSON records, and hoists duration_ms / status / method / uri / level as
queryable columns in the OpenObserve dashboards.

Health/liveness probes are skipped (they fired every 10s with no users and were
a top source of log noise). Unhandled exceptions emit a single-line JSON record
with level="error" and the full traceback so failures are queryable, not lost.
"""

from __future__ import annotations

import json
import time
import traceback
import uuid
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Liveness/readiness paths — hit on a timer by Docker/nginx, carry no signal.
_SKIP_PATHS = frozenset({"/", "/api/v1/health"})


def _emit(record: dict) -> None:
    print(json.dumps(record, default=str), flush=True)


class RequestTimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = uuid.uuid4().hex[:8]
        request.state.request_id = request_id
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            # Unhandled error: log it with a traceback (one record, since the
            # traceback lives inside a JSON string field) then let the framework
            # produce the 500.
            _emit(
                {
                    "time": datetime.now(timezone.utc).isoformat(),
                    "level": "error",
                    "request_id": request_id,
                    "method": request.method,
                    "uri": request.url.path,
                    "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                    "traceback": traceback.format_exc(),
                }
            )
            raise

        if request.url.path in _SKIP_PATHS:
            return response

        _emit(
            {
                "time": datetime.now(timezone.utc).isoformat(),
                "level": "info",
                "request_id": request_id,
                "method": request.method,
                "uri": request.url.path,
                "status": response.status_code,
                "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                "db_connect_ms": getattr(request.state, "db_connect_ms", None),
            }
        )
        return response
