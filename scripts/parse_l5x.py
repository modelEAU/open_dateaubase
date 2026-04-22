"""Thin shim — logic moved to importer/src/table_import/l5x_loader.py."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "importer" / "src"))

from table_import.l5x_loader import (  # noqa: E402
    parse_modules,
    parse_tags,
    parse_io_mapping,
)


def main() -> None:
    import argparse
    import csv
    from collections import defaultdict
    from xml.etree import ElementTree as ET

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

    def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k, "") for k in fieldnames})

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

    by_slot: dict[str, dict] = {m["slot_address"]: m for m in modules if m["slot_address"]}
    grouped: dict[str, list[dict]] = defaultdict(list)
    for r in io_map:
        grouped[r["slot"]].append(r)
    lines = ["# Logix5000 I/O → Instrument Tag Mapping", ""]
    for slot in sorted(grouped, key=lambda s: int(s) if s.isdigit() else 0):
        mod = by_slot.get(slot, {})
        label = f"Slot {slot}"
        if mod:
            label += f" — {mod.get('catalog', '')}"
            if mod.get("name"):
                label += f" ({mod['name']})"
        lines += [f"## {label}", "",
                  "| Dir | Channel | I/O reference | Instrument tag | Program / Routine |",
                  "| --- | --- | --- | --- | --- |"]
        for r in sorted(grouped[slot], key=lambda x: (x["io_direction"], x["channel"])):
            lines.append(
                f"| {r['io_direction']} | {r['channel']} | `{r['io_reference']}` | "
                f"`{r['instrument_tag']}` | {r['program']} / {r['routine']} |"
            )
        lines.append("")
    (args.out_dir / "io_mapping.md").write_text("\n".join(lines), encoding="utf-8")

    print(f"modules:    {len(modules):4d}  -> {args.out_dir/'modules.csv'}")
    print(f"tags:       {len(tags):4d}  -> {args.out_dir/'tags.csv'}")
    print(f"io_mapping: {len(io_map):4d}  -> {args.out_dir/'io_mapping.csv'}")
    print(f"           (grouped view -> {args.out_dir/'io_mapping.md'})")


if __name__ == "__main__":
    main()
