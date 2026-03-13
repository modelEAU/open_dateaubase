"""Pure datetime utility functions used by source readers.

All SQL connection / insert functions have been removed — data is now
written via the REST API (see api_client.py and import_script.py).
"""

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pandas as pd


def unix_seconds_to_local_datetime(seconds: int, local_timezone: str = "America/Montreal") -> pd.Timestamp:
    try:
        ZoneInfo(local_timezone)
    except ZoneInfoNotFoundError:
        raise ValueError(f"Provided timezone is not a valid timezone name: {local_timezone}")
    return pd.to_datetime(seconds, unit="s", origin="unix").tz_localize("UTC").tz_convert(local_timezone).tz_localize(None)


def local_datetime_to_unix_seconds(date: pd.Timestamp, local_timezone: str = "America/Montreal") -> float:
    try:
        ZoneInfo(local_timezone)
    except ZoneInfoNotFoundError:
        raise ValueError(f"Provided timezone is not a valid timezone name: {local_timezone}")
    return date.tz_localize(local_timezone).tz_convert("UTC").timestamp()
