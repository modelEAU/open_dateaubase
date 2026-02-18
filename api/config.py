"""API configuration loaded from environment variables."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env.local first, fall back to .env
_env_local = Path(__file__).parent.parent / ".env.local"
_env = Path(__file__).parent.parent / ".env"
if _env_local.exists():
    load_dotenv(_env_local)
else:
    load_dotenv(_env)


class Settings:
    db_host: str = os.getenv("DB_HOST", "")
    db_port: int = int(os.getenv("DB_PORT", "1433"))
    db_name: str = os.getenv("DB_NAME", "")
    db_user: str = os.getenv("DB_USER", "")
    db_password: str = os.getenv("DB_PASSWORD", "")
    db_driver: str = os.getenv("DB_DRIVER", "ODBC Driver 18 for SQL Server")

    api_title: str = "open_datEAUbase API"
    api_description: str = (
        "REST API for the open_datEAUbase water quality database. "
        "Provides access to time series data, metadata, campaigns, equipment, "
        "ingestion routes, and processing lineage."
    )
    api_version: str = "1.0.0"
    schema_version: str = "1.6.0"


settings = Settings()
