"""Request-timing middleware — emits one JSON line per request to stdout.

Vector tails the NSSM-captured stdout log, detects lines starting with '{'
as JSON records, and hoists duration_ms / status / method / uri as queryable
columns in the OpenObserve performance dashboard.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestTimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        record = {
            "time": datetime.now(timezone.utc).isoformat(),
            "method": request.method,
            "uri": request.url.path,
            "status": response.status_code,
            "duration_ms": duration_ms,
            "db_connect_ms": getattr(request.state, "db_connect_ms", None),
        }
        print(json.dumps(record), flush=True)
        return response
