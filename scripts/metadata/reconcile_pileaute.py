"""Steps A & B of the pilEAUte metadata reconciliation.

A: import pilEAUte master data (equipment models, equipment inventory, persons,
   procedures, watershed, parameter/unit gap-fill) -- UNLINKED to any stream.
B: create process units + sampling locations from the confirmed Step 3 workbook.

Idempotent: existing rows (matched by natural key) are skipped. Read-only against
the legacy CSVs + the Step 3 workbook; writes to staging via the REST API.

Usage:
    uv run --isolated --with openpyxl python scripts/metadata/reconcile_pileaute.py [SECTION ...] [--dry-run]
    SECTION in: models equipment persons procedures watershed vocab process_units sampling_locations
    (no section -> run all, in dependency order)
"""

from __future__ import annotations

import csv
import sys
import json
import argparse
import urllib.request
import urllib.error
from pathlib import Path

from openpyxl import load_workbook

API = "http://127.0.0.1:8010/api/v1"
LEGACY = Path(r"C:\Users\admin_modeleau\Desktop\legacy_metadata")
STEP3 = LEGACY / "step3_process_units_and_sampling_locations.xlsx"
SITE_ID = 1
CAMPAIGN_ID = 1
PU_KIND = {"Area": 1, "Zone": 2, "Tank": 3, "Reactor": 4, "Clarifier": 8, "Basin": 9}

DRY = False


def _token() -> str:
    for line in Path(r"C:\source\open_dateaubase\.env.staging").read_text().splitlines():
        if line.startswith("API_SERVICE_TOKEN="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("API_SERVICE_TOKEN not found in .env.staging")


TOKEN = _token()


def api(method: str, path: str, body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        API + path, data=data, method=method,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        raise SystemExit(f"{method} {path} -> {e.code}: {e.read().decode(errors='replace')[:400]}")


def get_list(path: str) -> list:
    d = api("GET", path)
    return d.get("items", d) if isinstance(d, dict) else d


def clean(v: str | None) -> str | None:
    if v is None:
        return None
    v = v.strip().lstrip("﻿")
    return None if v in ("", "NULL") else v


def load_csv(name: str) -> list[list[str | None]]:
    rows = []
    with open(LEGACY / name, encoding="utf-8-sig", newline="") as f:
        for r in csv.reader(f):
            if r and any(c.strip() for c in r):
                rows.append([clean(c) for c in r])
    return rows


def post(path: str, body: dict, label: str):
    if DRY:
        print(f"   [dry] POST {path} {body.get('identifier') or body.get('name') or body.get('equipment_model') or label}")
        return None
    return api("POST", path, body)


# ---------------------------------------------------------------------------
# Step A
# ---------------------------------------------------------------------------

def import_models() -> dict[str, int]:
    """equipment_model.csv -> /equipment/models. Returns legacy_id -> new model_id."""
    existing = {m["equipment_model"]: m["model_id"] for m in get_list("/equipment/models")}
    legacy_map: dict[str, int] = {}
    created = skipped = dropped_manual = 0
    for row in load_csv("equipment_model.csv"):
        legacy_id, name, method, functions, manufacturer = row[0], row[1], row[2], row[3], row[4]
        manual = row[11] if len(row) > 11 else None
        # ManualLocation is NVARCHAR(1000); drop anything still longer (recoverable from CSV)
        if manual and len(manual) > 1000:
            manual = None
            dropped_manual += 1
        if not name:
            continue
        if name in existing:
            legacy_map[legacy_id] = existing[name]
            skipped += 1
            continue
        body = {"equipment_model": name, "method": method, "functions": functions,
                "manufacturer": manufacturer, "manual_location": manual}
        res = post("/equipment/models", body, name)
        if res:
            legacy_map[legacy_id] = res["model_id"]
            existing[name] = res["model_id"]
        created += 1
    print(f"models: +{created} created, {skipped} existing, {dropped_manual} manual URLs dropped (>1000 chars)")
    return legacy_map


def import_equipment(model_map: dict[str, int]) -> None:
    """equipment.csv -> /equipment (unwired). model_id remapped legacy->new."""
    existing = {e["identifier"] for e in get_list("/equipment")}
    created = skipped = 0
    for row in load_csv("equipment.csv"):
        # id, identifier, serial, owner, proc, purchase_date, model_id, status, ?, date
        identifier, serial, owner, purchase, legacy_model = row[1], row[2], row[3], row[5], row[6]
        if not identifier or identifier in existing:
            skipped += 1
            continue
        body = {
            "identifier": identifier, "serial_number": serial, "owner": owner,
            "purchase_date": purchase, "model_id": model_map.get(legacy_model),
        }
        post("/equipment", body, identifier)
        existing.add(identifier)
        created += 1
    print(f"equipment: +{created} created, {skipped} existing/skipped")


def import_persons() -> None:
    existing = {(p.get("first_name"), p.get("last_name")) for p in get_list("/persons")}
    created = skipped = 0
    for row in load_csv("contact.csv"):
        # id, last, first, company, status, role, proc, email, phone, ...
        last, first, company, role, email, phone = row[1], row[2], row[3], row[5], row[7], row[8]
        if not (first or last) or (first, last) in existing:
            skipped += 1
            continue
        body = {"first_name": first, "last_name": last, "email": email,
                "role": role, "company": company, "phone": phone}
        post("/persons/", body, f"{first} {last}")
        existing.add((first, last))
        created += 1
    print(f"persons: +{created} created, {skipped} existing/skipped")


def import_procedures() -> None:
    existing = {p.get("procedure_name") for p in get_list("/vocab/procedures")}
    created = skipped = 0
    for row in load_csv("procedures.csv"):
        # id, name, method, description, proc_location
        name, _method, desc, loc = row[1], row[2], row[3], row[4]
        if not name or name in existing:
            skipped += 1
            continue
        post("/vocab/procedures", {"procedure_name": name, "description": desc,
                                   "procedure_location": loc}, name)
        existing.add(name)
        created += 1
    print(f"procedures: +{created} created, {skipped} existing/skipped")


def import_watershed() -> None:
    existing = {w.get("name") for w in get_list("/vocab/watersheds")}
    created = skipped = 0
    for row in load_csv("watershed.csv"):
        # id, name, description, surface_area, concentration_time, impervious_surface, geojson
        name, desc, area, ct, imp = row[1], row[2], row[3], row[4], row[5]
        if name != "pilEAUte":  # pilEAUte scope only
            continue
        if name in existing:
            skipped += 1
            continue
        body = {"name": name, "description": desc,
                "surface_area": float(area) if area else None,
                "concentration_time": int(float(ct)) if ct else None,
                "impervious_surface": float(imp) if imp else None}
        post("/vocab/watersheds", body, name)
        created += 1
    print(f"watershed: +{created} created, {skipped} existing/skipped")


def reconcile_vocab() -> None:
    """REPORT ONLY: legacy parameters/units not present (by exact name) in the seeded
    vocabulary. Not auto-created -- legacy short names (NH4-N, DO, NO3-N) are aliases of
    the seeded long names the channels already use, so creating them would duplicate.
    Curate manually."""
    have_p = {(p.get("parameter_name") or "").lower() for p in get_list("/parameters")}
    miss_p = [row[1] for row in load_csv("parameter.csv")
              if row[1] and row[1].lower() not in have_p]
    have_u = {(u.get("unit") or u.get("unit_name") or "").lower()
              for u in get_list("/ingest/lookup/units")}
    miss_u = [row[1] for row in load_csv("units.csv")
              if row[1] and row[1].lower() not in have_u]
    print("vocab (REPORT ONLY, nothing created):")
    print(f"  legacy parameters not matched by name ({len(miss_p)}): {miss_p}")
    print(f"  legacy units not matched by name ({len(miss_u)}): {miss_u}")
    print("  -> review: most are aliases of already-seeded entries; add real gaps via the app.")


# ---------------------------------------------------------------------------
# Step 0 — ensure the pilEAUte Site + Operation Campaign exist
# ---------------------------------------------------------------------------

SITE_NAME = "pilEAUte"
SITE_KIND_ID = 12       # Experimental Wastewater Treatment Plant
CAMPAIGN_NAME = "pilEAUte Operation"
CAMPAIGN_KIND_ID = 2    # Regular operation
CAMPAIGN_START = "2026-01-01T00:00:00"


def ensure_site_and_campaign() -> None:
    """Create the pilEAUte Site and 'pilEAUte Operation' Campaign if absent.

    The importer creates channels/interfaces but NOT the Site or Campaign, so on
    a fresh deploy these must be seeded before process units / sampling locations
    (which carry Site_ID) and before commissioning (which deploys under the
    campaign). On an empty DB the first inserts land on ID 1, matching SITE_ID /
    CAMPAIGN_ID used here and by commission_pileaute.py."""
    sites = get_list("/sites")
    site_id = next((s.get("id") for s in sites if s.get("name") == SITE_NAME), None)
    if site_id is None:
        res = post("/sites", {
            "name": SITE_NAME, "site_kind_id": SITE_KIND_ID,
            "description": "pilEAUte pilot wastewater treatment plant (Universite Laval)",
        }, SITE_NAME)
        site_id = res["id"] if res else None
        print(f"site: created {SITE_NAME} (id={site_id})")
    else:
        print(f"site: {SITE_NAME} exists (id={site_id})")
    if site_id not in (None, SITE_ID):
        print(f"  ! WARNING: {SITE_NAME} has id={site_id}, but scripts assume SITE_ID={SITE_ID}")

    camps = get_list("/campaigns")
    camp_id = next((c.get("campaign_id") for c in camps if c.get("name") == CAMPAIGN_NAME), None)
    if camp_id is None:
        res = post("/campaigns", {
            "name": CAMPAIGN_NAME, "campaign_kind_id": CAMPAIGN_KIND_ID,
            "site_id": site_id or SITE_ID, "start_date": CAMPAIGN_START,
            "description": "pilEAUte continuous operation campaign",
        }, CAMPAIGN_NAME)
        camp_id = res["campaign_id"] if res else None
        print(f"campaign: created {CAMPAIGN_NAME} (id={camp_id})")
    else:
        print(f"campaign: {CAMPAIGN_NAME} exists (id={camp_id})")
    if camp_id not in (None, CAMPAIGN_ID):
        print(f"  ! WARNING: {CAMPAIGN_NAME} has id={camp_id}, but scripts assume CAMPAIGN_ID={CAMPAIGN_ID}")


# ---------------------------------------------------------------------------
# Step B
# ---------------------------------------------------------------------------

def _legacy_coords() -> dict[str, tuple]:
    coords = {}
    for row in load_csv("sampling_points.csv"):
        code, lat, lon = row[1], row[4], row[5]
        try:
            coords[code] = (float(lat), float(lon))
        except (TypeError, ValueError):
            pass
    return coords


def _step3_rows(sheet: str) -> list[dict]:
    wb = load_workbook(STEP3, read_only=True, data_only=True)
    ws = wb[sheet]
    rows = list(ws.iter_rows(values_only=True))
    header = [str(h).strip() if h is not None else "" for h in rows[0]]
    out = []
    for r in rows[1:]:
        if r is None or all(c is None for c in r):
            continue
        out.append({header[i]: (r[i] if i < len(r) else None) for i in range(len(header))})
    return out


def create_process_units() -> dict[str, int]:
    """Returns tag -> process_unit_id (existing + created)."""
    tag_to_id = {pu["tag"]: pu["id"] for pu in get_list(f"/process-units?site_id={SITE_ID}")}
    created = skipped = 0
    for row in _step3_rows("ProcessUnits"):
        tag = str(row.get("Tag/Code") or "").strip()
        if not tag or (row.get("Action") or "").upper() != "CREATE":
            continue
        if tag in tag_to_id:
            skipped += 1
            continue
        kind = (row.get("Kind") or "").strip()
        parent_tag = (row.get("Parent") or "").strip()
        body = {
            "site_id": SITE_ID, "tag": tag, "name": (row.get("Name") or tag).strip(),
            "process_unit_kind_id": PU_KIND.get(kind),
            "parent_id": tag_to_id.get(parent_tag) if parent_tag else None,
        }
        res = post("/process-units", body, tag)
        if res:
            tag_to_id[tag] = res["id"]
        created += 1
    print(f"process_units: +{created} created, {skipped} existing")
    return tag_to_id


# Sampling locations discovered during plant commissioning that are not in the
# reviewed Step 3 workbook. (code, description, process_unit_tag)
EXTRA_SAMPLING_LOCATIONS = [
    ("PST_IN", "Primary clarifier influent", "PST"),
]


def create_sampling_locations(pu_map: dict[str, int]) -> None:
    coords = _legacy_coords()
    existing = {sp["name"] for sp in get_list(f"/sites/{SITE_ID}/sampling-locations")}
    created = skipped = 0
    for code, desc, pu_tag in EXTRA_SAMPLING_LOCATIONS:
        if code in existing:
            skipped += 1
            continue
        lat, lon = coords.get(code, (None, None))
        post(f"/sites/{SITE_ID}/sampling-locations", {
            "name": code, "description": desc, "latitude": lat, "longitude": lon,
            "process_unit_id": pu_map.get(pu_tag) if pu_tag else None,
        }, code)
        existing.add(code)
        created += 1
    for row in _step3_rows("SamplingLocations"):
        code = str(row.get("Code") or "").strip()
        if not code or (str(row.get("Create?") or "").strip().lower() not in ("yes", "y", "true")):
            continue
        if code in existing:
            skipped += 1
            continue
        lat, lon = coords.get(code, (None, None))
        pu_tag = (row.get("ProcessUnit") or "").strip()
        body = {
            "name": code,
            "description": (row.get("Name") or "").strip() or None,
            "latitude": lat, "longitude": lon,
            "process_unit_id": pu_map.get(pu_tag) if pu_tag else None,
        }
        post(f"/sites/{SITE_ID}/sampling-locations", body, code)
        existing.add(code)
        created += 1
    print(f"sampling_locations: +{created} created, {skipped} existing")


# ---------------------------------------------------------------------------

def main():
    global DRY
    ap = argparse.ArgumentParser()
    ap.add_argument("sections", nargs="*", help="subset to run; default all")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    DRY = args.dry_run
    sec = set(args.sections) if args.sections else None

    def run(name):
        return sec is None or name in sec

    if run("setup") or run("process_units") or run("sampling_locations"):
        ensure_site_and_campaign()

    model_map: dict[str, int] = {}
    if run("models") or run("equipment"):
        model_map = import_models()
    if run("equipment"):
        import_equipment(model_map)
    if run("persons"):
        import_persons()
    if run("procedures"):
        import_procedures()
    if run("watershed"):
        import_watershed()
    if run("vocab"):
        reconcile_vocab()

    pu_map: dict[str, int] = {}
    if run("process_units") or run("sampling_locations"):
        pu_map = create_process_units()
    if run("sampling_locations"):
        create_sampling_locations(pu_map)


if __name__ == "__main__":
    main()
