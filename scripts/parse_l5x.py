"""Parse a Logix5000 L5X export and produce catalogs of modules, tags, and
the (physical I/O port -> named instrument tag) mapping inferred from ladder
logic.

Usage:
    uv run python scripts/parse_l5x.py <path-to.L5X> [--out-dir out/]

Produces:
    modules.csv    - I/O chassis inventory (slot, catalog, name, parent)
    tags.csv       - Base tags (scope, name, datatype, description)
    io_mapping.csv - (Local:slot:I|O.ChN) <-> instrument tag mapping, from
                     MOV/CPS instructions in ladder routines
    io_mapping.md  - Same, grouped by module for human consultation
"""

from __future__ import annotations

import argparse
import csv
import re
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET

# Match Logix I/O references: Local:6:I.Ch0Data, Local:2:O.Data.3, etc.
IO_REF_RE = re.compile(r"Local:(\d+):([IO])\.(Ch\d+Data|Data(?:\.\d+)?)")

# MOV(src, dst) and CPS/CPT variants. We capture both arguments; if one side is
# a Local:* reference, the other side is the named tag that mirrors it.
MOV_RE = re.compile(r"\b(?:MOV|COP|CPS|CPT)\s*\(\s*([^,\s)]+)\s*,\s*([^,\s)]+)")


def parse_modules(root: ET.Element) -> list[dict]:
    rows = []
    for mod in root.iter("Module"):
        port = mod.find("./Ports/Port")
        address = port.get("Address") if port is not None else ""
        rows.append(
            {
                "name": mod.get("Name", ""),
                "catalog": mod.get("CatalogNumber", ""),
                "vendor": mod.get("Vendor", ""),
                "product_type": mod.get("ProductType", ""),
                "product_code": mod.get("ProductCode", ""),
                "parent": mod.get("ParentModule", ""),
                "parent_port": mod.get("ParentModPortId", ""),
                "slot_address": address,
                "inhibited": mod.get("Inhibited", ""),
            }
        )
    return rows


def _tag_description(tag: ET.Element) -> str:
    desc = tag.find("Description")
    if desc is None or desc.text is None:
        return ""
    return " ".join(desc.text.split())


def parse_tags(root: ET.Element) -> list[dict]:
    rows = []
    # Controller-scope tags: direct <Tags><Tag> under <Controller>
    controller = root.find("Controller")
    if controller is None:
        return rows
    ctrl_tags = controller.find("Tags")
    if ctrl_tags is not None:
        for tag in ctrl_tags.findall("Tag"):
            rows.append(
                {
                    "scope": "controller",
                    "program": "",
                    "name": tag.get("Name", ""),
                    "tag_type": tag.get("TagType", ""),
                    "data_type": tag.get("DataType", ""),
                    "alias_for": tag.get("AliasFor", ""),
                    "external_access": tag.get("ExternalAccess", ""),
                    "description": _tag_description(tag),
                }
            )
    # Program-scope tags
    for prog in controller.iter("Program"):
        prog_name = prog.get("Name", "")
        prog_tags = prog.find("Tags")
        if prog_tags is None:
            continue
        for tag in prog_tags.findall("Tag"):
            rows.append(
                {
                    "scope": "program",
                    "program": prog_name,
                    "name": tag.get("Name", ""),
                    "tag_type": tag.get("TagType", ""),
                    "data_type": tag.get("DataType", ""),
                    "alias_for": tag.get("AliasFor", ""),
                    "external_access": tag.get("ExternalAccess", ""),
                    "description": _tag_description(tag),
                }
            )
    return rows


def parse_io_mapping(root: ET.Element) -> list[dict]:
    """Scan every rung's ladder text for MOV/CPS instructions that copy
    between a Local:* I/O reference and a named tag."""
    rows = []
    controller = root.find("Controller")
    if controller is None:
        return rows
    for prog in controller.iter("Program"):
        prog_name = prog.get("Name", "")
        for routine in prog.iter("Routine"):
            rout_name = routine.get("Name", "")
            for rung in routine.iter("Rung"):
                rung_num = rung.get("Number", "")
                text_el = rung.find("Text")
                if text_el is None or text_el.text is None:
                    continue
                rung_text = text_el.text
                for match in MOV_RE.finditer(rung_text):
                    a, b = match.group(1), match.group(2)
                    a_is_io = IO_REF_RE.search(a)
                    b_is_io = IO_REF_RE.search(b)
                    if a_is_io and not b_is_io:
                        direction = "input"  # I/O source -> tag
                        io_ref, tag_ref = a, b
                        mod_match = a_is_io
                    elif b_is_io and not a_is_io:
                        direction = "output"  # tag -> I/O destination
                        io_ref, tag_ref = b, a
                        mod_match = b_is_io
                    else:
                        continue
                    slot, io_dir, channel = mod_match.groups()
                    rows.append(
                        {
                            "slot": slot,
                            "io_direction": io_dir,  # I or O
                            "channel": channel,
                            "io_reference": io_ref,
                            "instrument_tag": tag_ref,
                            "mapping_direction": direction,
                            "program": prog_name,
                            "routine": rout_name,
                            "rung": rung_num,
                            "rung_text": rung_text.strip(),
                        }
                    )
    return rows


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def write_io_markdown(path: Path, io_rows: list[dict], modules: list[dict]) -> None:
    by_slot: dict[str, dict] = {m["slot_address"]: m for m in modules if m["slot_address"]}
    grouped: dict[str, list[dict]] = defaultdict(list)
    for r in io_rows:
        grouped[r["slot"]].append(r)

    lines = ["# Logix5000 I/O → Instrument Tag Mapping", ""]
    for slot in sorted(grouped, key=lambda s: int(s) if s.isdigit() else 0):
        mod = by_slot.get(slot, {})
        label = f"Slot {slot}"
        if mod:
            label += f" — {mod.get('catalog', '')}"
            if mod.get("name"):
                label += f" ({mod['name']})"
        lines.append(f"## {label}")
        lines.append("")
        lines.append("| Dir | Channel | I/O reference | Instrument tag | Program / Routine |")
        lines.append("| --- | --- | --- | --- | --- |")
        for r in sorted(grouped[slot], key=lambda x: (x["io_direction"], x["channel"])):
            lines.append(
                f"| {r['io_direction']} | {r['channel']} | `{r['io_reference']}` | "
                f"`{r['instrument_tag']}` | {r['program']} / {r['routine']} |"
            )
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("l5x", type=Path)
    ap.add_argument("--out-dir", type=Path, default=Path("out/l5x"))
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    tree = ET.parse(args.l5x)
    root = tree.getroot()

    modules = parse_modules(root)
    tags = parse_tags(root)
    io_map = parse_io_mapping(root)

    write_csv(
        args.out_dir / "modules.csv",
        modules,
        ["name", "catalog", "slot_address", "parent", "parent_port", "vendor",
         "product_type", "product_code", "inhibited"],
    )
    write_csv(
        args.out_dir / "tags.csv",
        tags,
        ["scope", "program", "name", "tag_type", "data_type", "alias_for",
         "external_access", "description"],
    )
    write_csv(
        args.out_dir / "io_mapping.csv",
        io_map,
        ["slot", "io_direction", "channel", "io_reference", "instrument_tag",
         "mapping_direction", "program", "routine", "rung", "rung_text"],
    )
    write_io_markdown(args.out_dir / "io_mapping.md", io_map, modules)

    print(f"modules:    {len(modules):4d}  -> {args.out_dir/'modules.csv'}")
    print(f"tags:       {len(tags):4d}  -> {args.out_dir/'tags.csv'}")
    print(f"io_mapping: {len(io_map):4d}  -> {args.out_dir/'io_mapping.csv'}")
    print(f"           (grouped view -> {args.out_dir/'io_mapping.md'})")


if __name__ == "__main__":
    main()
