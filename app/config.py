"""App configuration — reads from environment with sensible defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_dotenv_local() -> None:
    """Load .env.local if it exists (best-effort, no hard dependency on dotenv)."""
    env_local = Path(".env.local")
    if not env_local.exists():
        return
    try:
        from dotenv import load_dotenv  # type: ignore[import]

        load_dotenv(env_local, override=False)
    except ImportError:
        pass


_load_dotenv_local()


@dataclass
class Settings:
    API_BASE_URL: str = field(
        default_factory=lambda: os.getenv(
            "API_BASE_URL", "http://localhost:8000/api/v1"
        )
    )
    APP_TITLE: str = field(
        default_factory=lambda: os.getenv("APP_TITLE", "open_datEAUbase")
    )
    APP_VERSION: str = field(
        default_factory=lambda: os.getenv("APP_VERSION", "1.0.0")
    )


settings = Settings()
