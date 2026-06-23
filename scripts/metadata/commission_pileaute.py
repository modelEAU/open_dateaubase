"""Step E: apply a filled pilEAUte commissioning worksheet.

For each row that has a SamplingLocation (and EquipmentIdentifier), in order:
  1. resolve EquipmentModel "Manufacturer - Model" -> model_id  (if provided)
  2. resolve SamplingLocation code -> sampling_point_id
  3. find-or-create Equipment by identifier; patch model_id + serial_number
  4. register the equipment against the row's SignalInterface (wiring)
  5. POST /campaigns/{id}/deployments -> links campaign + location + places equipment

Idempotent: already-wired (409) and already-deployed (400) are treated as no-ops.
Safe by default: prints a plan; pass --apply to perform writes.

Usage:
    uv run --isolated --with openpyxl python scripts/metadata/commission_pileaute.py [worksheet.xlsx] [--apply]
"""

from __future__ import annotations

import re
import sys
import json
import argparse
import datetime as dt
import urllib.request
import urllib.error
from pathlib import Path

from openpyxl import load_workbook

API = "http://127.0.0.1:8010/api/v1"
DEFAULT_WS = Path(r"C:\Users\admin_modeleau\Desktop\legacy_metadata") / "commissioning_worksheet.xlsx"
CAMPAIGN_ID = 1


def _token() -> str:
    for line in Path(r"C:\source\open_dateaubase\.env.staging").read_text().splitlines():
        if line.startswith("API_SERVICE_TOKEN="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("token not found")


TOKEN = _token()


def api(method: str, path: str, body: dict | None = None) -> tuple[int, object]:
    """Return (status_code, parsed_body_or_text). Does not raise on HTTP errors."""
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        API + path, data=data, method=method,
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, raw


def get_list(path: str) -> list:
    _, d = api("GET", path)
    return d.get("items", d) if isinstance(d, dict) else d


def cell(v) -> str:
    """Trim a cell; treat blank and the 'x' marker (no signal / not deployed) as empty."""
    if v is None:
        return ""
    s = str(v).strip()
    return "" if s.lower() == "x" else s


def placeholder_ident(si_name: str) -> str:
    """Synthesize a placeholder equipment identifier for a tagged SCADA interface
    that has no real equipment recorded, so the channel becomes positionable.
    '[PCL_001]AIT_241_EU' -> 'pilEAUte_AIT_241_EU'."""
    t = re.sub(r"^\[[^\]]*\]", "", str(si_name or ""))
    t = re.sub(r"[^0-9A-Za-z]+", "_", t).strip("_")
    return f"pilEAUte_{t}"


def norm_dt(v) -> str:
    if isinstance(v, dt.datetime):
        return v.replace(tzinfo=dt.timezone.utc).isoformat()
    if isinstance(v, dt.date):
        return dt.datetime(v.year, v.month, v.day, tzinfo=dt.timezone.utc).isoformat()
    s = str(v or "2026-01-01").strip()[:10]
    return f"{s}T00:00:00+00:00"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("worksheet", nargs="?", default=str(DEFAULT_WS))
    ap.add_argument("--apply", action="store_true", help="perform writes (default: plan only)")
    args = ap.parse_args()

    # lookups
    model_by_str = {f"{(m.get('manufacturer') or '?')} - {m.get('equipment_model') or '?'}": m["model_id"]
                    for m in get_list("/equipment/models")}
    sp_by_code = {s["name"]: s["id"] for s in get_list("/sites/1/sampling-locations")}
    equip_by_id = {e["identifier"]: e["equipment_id"] for e in get_list("/equipment")}

    wb = load_workbook(args.worksheet, data_only=True)
    ws = wb["Commissioning"]
    header = [str(c.value).strip() if c.value is not None else "" for c in ws[1]]
    col = {h: i for i, h in enumerate(header)}

    planned = skipped = errors = placeholders = 0
    for r in ws.iter_rows(min_row=2, values_only=True):
        def g(name):
            i = col.get(name)
            return r[i] if i is not None and i < len(r) else None

        si_id = g("SignalInterfaceID")
        si_name = g("SignalInterface")
        ident_ws = cell(g("EquipmentIdentifier"))
        sp_code = cell(g("SamplingLocation"))
        model_str = cell(g("EquipmentModel"))
        serial = cell(g("SerialNumber")) or None
        valid_from = norm_dt(g("DeployFrom"))
        notes = cell(g("Notes")) or None

        deploying = bool(sp_code)

        # Equipment identity: the worksheet value (monEAU placeholder already wired)
        # or, for a tagged SCADA tag the user located but left equipment-less, a
        # synthesized placeholder so the channel becomes positionable (Option A).
        is_placeholder = False
        if ident_ws:
            ident = ident_ws
        elif deploying:
            ident = placeholder_ident(si_name)
            is_placeholder = True
        else:
            skipped += 1            # not deployed and no equipment recorded -> nothing to do
            continue

        if deploying and sp_code not in sp_by_code:
            print(f"  ! {si_name}: unknown SamplingLocation {sp_code!r} -> skip")
            errors += 1
            continue
        model_id = None
        if model_str:
            model_id = model_by_str.get(model_str)
            if model_id is None:
                print(f"  ! {si_name}: unknown EquipmentModel {model_str!r} -> skip")
                errors += 1
                continue

        if not deploying and not model_str and not serial:
            skipped += 1            # existing equipment, nothing new to record
            continue

        tag = " +placeholder" if is_placeholder else ""
        dest = sp_code if deploying else "(not deployed)"
        action = f"{ident}{tag} -> {dest}" + (f" [{model_str}]" if model_str else "")
        if not args.apply:
            print(f"  [plan] {action}")
            planned += 1
            if is_placeholder:
                placeholders += 1
            continue

        # find-or-create equipment, patch model+serial
        eq_id = equip_by_id.get(ident)
        if eq_id is None:
            st, res = api("POST", "/equipment",
                          {"identifier": ident, "serial_number": serial, "model_id": model_id})
            if st >= 400:
                print(f"  ! {ident}: create equipment failed {st}: {res}")
                errors += 1
                continue
            eq_id = res["equipment_id"]
            equip_by_id[ident] = eq_id
            if is_placeholder:
                placeholders += 1
        else:
            patch = {}
            if model_id is not None:
                patch["model_id"] = model_id
            if serial:
                patch["serial_number"] = serial
            if patch:
                api("PATCH", f"/equipment/{eq_id}", patch)

        if deploying:
            # wire to the signal interface (409 = already wired -> ok)
            st, res = api("POST", f"/equipment/{eq_id}/register-interface",
                          {"signal_interface_id": si_id, "valid_from": valid_from})
            if st >= 400 and st != 409:
                print(f"  ! {ident}: register-interface failed {st}: {res}")
                errors += 1
                continue

            # deploy under the campaign (400 = already deployed -> ok)
            st, res = api("POST", f"/campaigns/{CAMPAIGN_ID}/deployments",
                          {"equipment_id": eq_id, "sampling_point_id": sp_by_code[sp_code],
                           "valid_from": valid_from, "notes": notes})
            if st >= 400 and st != 400:
                print(f"  ! {ident}: deployment failed {st}: {res}")
                errors += 1
                continue
            if st == 400 and isinstance(res, dict) and "already deployed" not in str(res.get("detail", "")):
                print(f"  ! {ident}: deployment 400: {res}")
                errors += 1
                continue

        print(f"  [done] {action}")
        planned += 1

    verb = "applied" if args.apply else "planned"
    print(f"\n{verb}: {planned} | skipped: {skipped} | errors: {errors} | placeholders: {placeholders}")
    if not args.apply:
        print("Re-run with --apply to write.")


if __name__ == "__main__":
    main()
