"""Pure builder for the Data Explorer zip export.

Turns a list of already-fetched stream entries into a single zip: one CSV per
stream (UTC timestamps, value, annotation + equipment-event overlay columns) and
a paired pedigree YAML. Image streams additionally embed their files under
images/<basename>/.

No Streamlit, no API calls — all I/O happens in explore.py, which assembles the
entries and calls build_export_zip. That keeps every non-trivial rule (overlay
matching, CSV shaping, filename safety) unit-testable in isolation.

Entry contract (one dict per active stream)::

    {
        "filename":   "CH-5_TSS",           # base name; sanitized here
        "value_kind": 1,                      # VALUE_TYPE_* (explore_data)
        "data":       {"parameter": str, "unit": str, "data": [ {timestamp, ...} ]},
        "annotations": [ {kind, note, start, end} ],   # normalized, UTC strings
        "events":      [ {kind, note, start, end} ],   # normalized, UTC strings
        "pedigree":    { ... },               # /lineage/streams/{id}/pedigree
        "images":      { ts_str: bytes },     # image streams only
    }

Use overlay_from_annotation / overlay_from_event to normalize raw API dicts into
the {kind, note, start, end} overlay shape.
"""

from __future__ import annotations

import csv
import io
import re
import zipfile
from datetime import datetime, timezone

import yaml

from app.components.explore_data import VALUE_TYPE_IMAGE


def _to_utc_naive(ts) -> datetime | None:
    """Parse an ISO timestamp to a naive-UTC datetime for safe comparison."""
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _covers(item: dict, ts_dt: datetime | None) -> bool:
    """True if a {start, end} overlay item covers the given timestamp.

    end=None means a point annotation: matches only the exact start timestamp
    (avoids an open-ended range silently tagging every later row)."""
    if ts_dt is None:
        return False
    start = _to_utc_naive(item.get("start"))
    if start is None:
        return False
    end = _to_utc_naive(item.get("end"))
    if end is None:
        return ts_dt == start
    return start <= ts_dt <= end


def _segment_covers(seg: dict, ts_dt: datetime | None) -> bool:
    """True if a deployment segment was active at the timestamp.

    A segment with both bounds null is a fixed/unbounded context (a lab series'
    inherent sampling point + campaign) and covers every row. valid_to null is an
    open-ended deployment (still active), covering everything from valid_from on."""
    start = _to_utc_naive(seg.get("valid_from"))
    end = _to_utc_naive(seg.get("valid_to"))
    if start is None and end is None:
        return True
    if ts_dt is None:
        return False
    if start is not None and ts_dt < start:
        return False
    if end is not None and ts_dt > end:
        return False
    return True


def _segment_columns(ts, deployments: list[dict]) -> dict:
    """Resolve the sampling location + campaign active at a row's timestamp from
    the deployment timeline (the time-bound pedigree)."""
    ts_dt = _to_utc_naive(ts)
    hits = [d for d in deployments if _segment_covers(d, ts_dt)]

    def _name(seg: dict, key: str) -> str | None:
        obj = seg.get(key)
        return obj.get("name") if isinstance(obj, dict) else None

    return {
        "sampling_location": "; ".join(
            dict.fromkeys(n for s in hits if (n := _name(s, "sampling_location")))
        ),
        "campaign": "; ".join(
            dict.fromkeys(n for s in hits if (n := _name(s, "campaign")))
        ),
    }


def _overlay_columns(ts, annotations: list[dict], events: list[dict]) -> dict:
    ts_dt = _to_utc_naive(ts)
    a_hits = [a for a in annotations if _covers(a, ts_dt)]
    e_hits = [e for e in events if _covers(e, ts_dt)]
    return {
        "annotation_kind": "; ".join(a["kind"] for a in a_hits if a.get("kind")),
        "annotation_note": "; ".join(a["note"] for a in a_hits if a.get("note")),
        "event_kind": "; ".join(e["kind"] for e in e_hits if e.get("kind")),
        "event_note": "; ".join(e["note"] for e in e_hits if e.get("note")),
    }


def overlay_from_annotation(ann: dict) -> dict:
    """Normalize a raw annotation (AnnotationResponse) to the overlay shape.

    The kind lives under the nested ``type.name`` on the API response; plain
    ``kind`` is also accepted so callers can pass pre-flattened dicts."""
    type_obj = ann.get("type")
    type_name = type_obj.get("name") if isinstance(type_obj, dict) else None
    note = " — ".join(p for p in (ann.get("title"), ann.get("comment")) if p)
    return {
        "kind": ann.get("kind") or type_name or ann.get("annotation_kind") or ann.get("name"),
        "note": note or None,
        "start": ann.get("start_time") or ann.get("start"),
        "end": ann.get("end_time") or ann.get("end"),
    }


def overlay_from_event(ev: dict) -> dict:
    """Normalize a raw equipment-event dict (lifecycle endpoint) to the overlay shape."""
    note = " — ".join(
        p for p in (ev.get("notes"), ev.get("title"), ev.get("comment")) if p
    )
    return {
        "kind": ev.get("event_type_name") or ev.get("kind") or ev.get("event_kind") or ev.get("name"),
        "note": note or None,
        "start": ev.get("start_datetime") or ev.get("start"),
        "end": ev.get("end_datetime") or ev.get("end"),
    }


def _safe(name: str) -> str:
    """Filesystem-safe basename for zip members."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", str(name)).strip("_")
    return cleaned or "stream"


def _csv_bytes(rows: list[dict]) -> bytes:
    if not rows:
        return b""
    fieldnames: list[str] = []
    seen: set[str] = set()
    for r in rows:
        for k in r:
            if k not in seen:
                seen.add(k)
                fieldnames.append(k)
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode()


def _stream_rows(entry: dict, base: str, zf: zipfile.ZipFile) -> list[dict]:
    """Build the CSV rows for one stream (and embed image files as a side effect).

    Uniform across scalar/vector/matrix: timestamp_utc first, then the original
    row fields (value, quality_code, bin_index/row/col, …), then parameter/unit,
    then overlay columns. Image streams add an image_file column pointing at the
    embedded file."""
    data = entry.get("data") or {}
    parameter = data.get("parameter", "")
    unit = data.get("unit", "")
    annotations = entry.get("annotations") or []
    events = entry.get("events") or []
    deployments = (entry.get("pedigree") or {}).get("deployments") or []
    images = entry.get("images") or {}
    is_image = entry.get("value_kind") == VALUE_TYPE_IMAGE

    rows: list[dict] = []
    for orig in data.get("data", []):
        ts = orig.get("timestamp")
        row: dict = {"timestamp_utc": ts}
        for k, v in orig.items():
            if k != "timestamp":
                row[k] = v
        row["parameter"] = parameter
        row["unit"] = unit
        row.update(_segment_columns(ts, deployments))
        if is_image:
            img = images.get(ts)
            if img is not None:
                path = f"images/{base}/{_safe(str(ts))}.jpg"
                zf.writestr(path, img)
                row["image_file"] = path
            else:
                row["image_file"] = ""
        row.update(_overlay_columns(ts, annotations, events))
        rows.append(row)
    return rows


def build_export_zip(entries: list[dict]) -> bytes:
    """Build the export zip: paired <basename>.csv + <basename>.yaml per stream,
    plus embedded image files for image streams. Returns the zip bytes."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        used: set[str] = set()
        for entry in entries:
            base = _safe(entry.get("filename", "stream"))
            # Guard against duplicate basenames colliding in the archive.
            unique = base
            n = 2
            while unique in used:
                unique = f"{base}_{n}"
                n += 1
            used.add(unique)

            rows = _stream_rows(entry, unique, zf)
            zf.writestr(f"{unique}.csv", _csv_bytes(rows))
            zf.writestr(
                f"{unique}.yaml",
                yaml.safe_dump(
                    entry.get("pedigree") or {}, sort_keys=False, allow_unicode=True
                ),
            )
    return buf.getvalue()
