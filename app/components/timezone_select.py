"""The one timezone selector, shared by every ingest surface.

Times read out of a file are wall-clock times in *some* zone. Which zone is a
statement only the user can make, so it is asked explicitly and defaults to the
machine's local zone — never silently to UTC.
"""

from __future__ import annotations

import zoneinfo

import streamlit as st
import tzlocal

KNOWN_TIMEZONES = sorted(zoneinfo.available_timezones())

_DEFAULT_HELP = (
    "Timezone of the timestamps in your data. They will be converted to UTC on submit."
)


def local_timezone_name() -> str:
    """The machine's timezone, falling back to UTC when it cannot be determined."""
    name = tzlocal.get_localzone_name() or "UTC"
    return name if name in KNOWN_TIMEZONES else "UTC"


def timezone_selector(
    key: str, label: str = "CSV timezone", help: str | None = None
) -> zoneinfo.ZoneInfo:
    """Render a timezone selectbox pre-filled with the local timezone."""
    default = local_timezone_name()
    name = st.selectbox(
        label,
        options=KNOWN_TIMEZONES,
        index=KNOWN_TIMEZONES.index(default),
        key=key,
        help=help or _DEFAULT_HELP,
    )
    return zoneinfo.ZoneInfo(name)
