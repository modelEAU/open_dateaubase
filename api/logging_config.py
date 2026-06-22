"""Structured JSON logging for the API.

Emits one single-line JSON record per log event to stdout so Vector can
parse_json each line and hoist level / logger / traceback as queryable columns
in OpenObserve. Keeping the traceback inside a JSON string field means an error
is a single record, not N lines to stitch back together.
"""

from __future__ import annotations

import json
import logging
import os


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": self.formatTime(record),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["traceback"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    """Install the JSON formatter on the root logger. Level from $LOG_LEVEL."""
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    # RequestTimingMiddleware already emits one timing record per request;
    # uvicorn's access log would double every line, so silence it.
    logging.getLogger("uvicorn.access").disabled = True
