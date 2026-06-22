"""Structured JSON logging for the importer.

One single-line JSON record per event to stderr/stdout, matching the API's
format so Vector hoists level/traceback as queryable columns. A failed run
(non-zero exit) leaves one error record with the full traceback.
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
    level = os.environ.get("LOG_LEVEL", "INFO").upper()
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
