"""Reading date and time columns out of a spreadsheet, explicitly.

A spreadsheet's times are wall-clock times in some zone, written in some
order. Which zone is a statement only the user can make, so it is asked for
outright. Which order the day and month come in can often be told from the
data — but only sometimes, so detection reports the evidence it used and
refuses when a sample is genuinely ambiguous rather than flipping a coin.

Pure: no Streamlit, no database.
"""

from __future__ import annotations

import datetime as dt
import re
import zoneinfo
from dataclasses import dataclass
from typing import Any

import pandas as pd

# Strptime presets, label → format. Labels open with an example of themselves
# so the user recognises their own sheet. Anything outside this list is still
# reachable as a custom format string; detection only ever proposes a preset.
FORMAT_PRESETS: dict[str, str] = {
    "2026-04-03 — year first (ISO)": "%Y-%m-%d",
    "2026-04-03 14:30 — year first (ISO)": "%Y-%m-%d %H:%M",
    "2026-04-03 14:30:05 — year first (ISO)": "%Y-%m-%d %H:%M:%S",
    "03/04/2026 — day first": "%d/%m/%Y",
    "03/04/2026 14:30 — day first": "%d/%m/%Y %H:%M",
    "04/03/2026 — month first": "%m/%d/%Y",
    "04/03/2026 14:30 — month first": "%m/%d/%Y %H:%M",
}

# Detection looks at this many values; a real column's mind is made up well
# before that.
_SAMPLE_SIZE = 100
# How many disagreeing values are quoted when detection refuses.
_MAX_QUOTED = 3


@dataclass(frozen=True)
class Detection:
    """What auto-detection concluded, and why.

    ``format`` is ``None`` when detection refuses — either no preset fits
    every sampled value, or several do and choosing would be a guess. In
    that case ``contenders`` lists the labels of the formats still possible.
    ``evidence`` is always populated: the reasoning, in plain sentences,
    meant to be shown to the user verbatim.
    """

    format: str | None
    label: str | None
    evidence: tuple[str, ...]
    contenders: tuple[str, ...] = ()
    sampled: int = 0


@dataclass(frozen=True)
class Parsed:
    """A column read as wall-clock datetimes.

    ``wall_clock`` keeps the input's index — rows are never dropped. Values
    that would not parse are ``NaT`` there and are named in ``failures`` as
    ``(row, raw text)`` pairs.
    """

    wall_clock: pd.Series
    failures: tuple[tuple[Any, str], ...]


def detect_format(values: pd.Series) -> Detection:
    """Work out the date format of a column, showing the work.

    A preset *fits* when every sampled value parses with it. Exactly one fit
    is a detection; several fits mean the sample cannot tell the contenders
    apart, which is a refusal — the user chooses instead.
    """
    sample = _text_values(values).iloc[:_SAMPLE_SIZE]
    if sample.empty:
        return Detection(
            format=None,
            label=None,
            evidence=(
                "No text values to read a format from — the column may "
                "already hold real dates.",
            ),
        )
    fitting = [
        (label, fmt)
        for label, fmt in FORMAT_PRESETS.items()
        if _all_parse(sample, fmt)
    ]
    if len(fitting) == 1:
        label, fmt = fitting[0]
        evidence: list[str] = [f"All {len(sample)} sampled values fit “{label}”."]
        mirror = _mirror(fmt)
        if mirror is not None:
            mirror_label, mirror_fmt = mirror
            rejected = next((t for t in sample if not _parses(t, mirror_fmt)), None)
            if rejected is not None:
                evidence.append(_mirror_evidence(rejected, mirror_label, mirror_fmt, fmt))
        return Detection(fmt, label, tuple(evidence), sampled=len(sample))
    if len(fitting) > 1:
        evidence = []
        (label_a, fmt_a), (label_b, fmt_b) = fitting[0], fitting[1]
        quoted = 0
        for text in sample:
            read_a = pd.to_datetime(text, format=fmt_a)
            read_b = pd.to_datetime(text, format=fmt_b)
            if read_a != read_b and quoted < _MAX_QUOTED:
                evidence.append(
                    f"“{text}” could be {_words(read_a)} (“{label_a}”) or "
                    f"{_words(read_b)} (“{label_b}”)."
                )
                quoted += 1
        if quoted == 0:
            evidence.append(
                "Every sampled value has the same day and month, so day-first "
                "and month-first read identically here."
            )
        evidence.append(
            "More than one format fits every sampled value — refusing to guess."
        )
        return Detection(
            format=None,
            label=None,
            evidence=tuple(evidence),
            contenders=tuple(label for label, _ in fitting),
            sampled=len(sample),
        )
    return Detection(
        format=None,
        label=None,
        evidence=(
            "No preset fits every sampled value — enter a Custom… strptime "
            "format.",
        ),
        sampled=len(sample),
    )


def parse_values(values: pd.Series, fmt: str | None) -> Parsed:
    """Read a column as wall-clock datetimes.

    ``fmt`` is the strptime format for text values, or ``None`` when the
    column already carries native datetimes. Empty cells are missing, not
    failures; anything else that will not parse is listed with its row.
    """
    if fmt is None:
        parsed = pd.to_datetime(values, errors="coerce")
    else:
        parsed = pd.to_datetime(values, format=fmt, errors="coerce")
    failures = tuple(
        (idx, str(value).strip())
        for idx, value in values.items()
        if pd.isna(parsed.loc[idx]) and _is_unparsed_text(value)
    )
    return Parsed(wall_clock=parsed, failures=failures)


def to_utc(wall_clock: pd.Series, tz: zoneinfo.ZoneInfo) -> pd.Series:
    """The UTC instant of each wall-clock time in the file's zone.

    A daylight-saving change skips one hour of wall clock and repeats
    another, so a time inside either has no single UTC instant. Those become
    ``NaT`` rather than a guess, and ``dst_gaps`` names them.
    """
    moments = pd.to_datetime(wall_clock)
    if moments.dt.tz is not None:
        return moments.dt.tz_convert(dt.timezone.utc)
    localised = moments.dt.tz_localize(tz, nonexistent="NaT", ambiguous="NaT")
    return localised.dt.tz_convert(dt.timezone.utc)


def dst_gaps(wall_clock: pd.Series, utc: pd.Series) -> tuple[tuple[Any, str], ...]:
    """Rows a daylight-saving change left without a UTC instant.

    ``(row, wall-clock text)`` pairs — a time that parsed but does not exist,
    or happens twice, in the file's zone.
    """
    return tuple(
        (idx, str(value))
        for idx, value in wall_clock.items()
        if pd.notna(value) and pd.isna(utc.loc[idx])
    )


def _text_values(values: pd.Series) -> pd.Series:
    """The non-empty text cells of a column — what a format must explain."""
    texts: dict[Any, str] = {}
    for idx, value in values.items():
        if _is_unparsed_text(value):
            texts[idx] = str(value).strip()
    return pd.Series(texts, dtype=object)


def _is_unparsed_text(value: Any) -> bool:
    """Whether a cell holds text a format must explain (not empty, not a date)."""
    if value is None or isinstance(value, (pd.Timestamp, dt.datetime, dt.date)):
        return False
    try:
        if pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass
    return bool(str(value).strip())


def _parses(text: str, fmt: str) -> bool:
    try:
        dt.datetime.strptime(text, fmt)
    except ValueError:
        return False
    return True


def _all_parse(sample: pd.Series, fmt: str) -> bool:
    return bool(pd.to_datetime(sample, format=fmt, errors="coerce").notna().all())


def _mirror(fmt: str) -> tuple[str, str] | None:
    """The preset with day and month swapped, when there is one."""
    if "%d" not in fmt or "%m" not in fmt:
        return None
    swapped = fmt.replace("%d", "\x00").replace("%m", "%d").replace("\x00", "%m")
    return next(
        ((label, candidate) for label, candidate in FORMAT_PRESETS.items() if candidate == swapped),
        None,
    )


def _mirror_evidence(rejected: str, mirror_label: str, mirror_fmt: str, fmt: str) -> str:
    """Why the day/month-swapped reading was ruled out, in one sentence."""
    numbers = re.findall(r"\d+", rejected.split()[0])
    month_pos = 0 if mirror_fmt.index("%m") < mirror_fmt.index("%d") else 1
    if len(numbers) > month_pos and int(numbers[month_pos]) > 12:
        word = "day" if fmt.index("%d") < fmt.index("%m") else "month"
        return (
            f"“{rejected}” puts {numbers[month_pos]} where “{mirror_label}” "
            f"would need the month, and a month cannot exceed 12 — so the "
            f"dates are {word}-first."
        )
    return f"“{rejected}” does not fit “{mirror_label}”."


def _words(moment: pd.Timestamp) -> str:
    """A date as a human would say it: 3 April 2026."""
    return f"{moment.day} {moment:%B} {moment.year}"
