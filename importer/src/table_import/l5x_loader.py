"""Logix5000 L5X parser and API loader.

Provides:
  parse_modules / parse_tags / parse_io_mapping  — pure XML parsing
  plan_l5x_load(root, si_name, ...)               — pure plan derivation
  apply_l5x_load(plan, client, *, dry_run)         — HTTP writes via DateaubaseClient
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from xml.etree import ElementTree as ET

if TYPE_CHECKING:
    from table_import.api_client import DateaubaseClient

# Match Logix I/O references: Local:6:I.Ch0Data, Local:2:O.Data.3, etc.
IO_REF_RE = re.compile(r"Local:(\d+):([IO])\.(Ch\d+Data|Data(?:\.\d+)?)")
MOV_RE = re.compile(r"\b(?:MOV|COP|CPS|CPT)\s*\(\s*([^,\s)]+)\s*,\s*([^,\s)]+)")


# ---------------------------------------------------------------------------
# Parse functions (moved verbatim from scripts/parse_l5x.py)
# ---------------------------------------------------------------------------


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
                        direction = "input"
                        io_ref, tag_ref = a, b
                        mod_match = a_is_io
                    elif b_is_io and not a_is_io:
                        direction = "output"
                        io_ref, tag_ref = b, a
                        mod_match = b_is_io
                    else:
                        continue
                    slot, io_dir, channel = mod_match.groups()
                    rows.append(
                        {
                            "slot": slot,
                            "io_direction": io_dir,
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


# ---------------------------------------------------------------------------
# Plan types
# ---------------------------------------------------------------------------


@dataclass
class PortCreate:
    port_identifier: str
    kind_name: str  # "analog_input" | "analog_output"


@dataclass
class ChannelCreate:
    tag_name: str
    port_identifier: str | None  # None → unknown-port channel
    is_mux: bool  # True → shared port, use ChannelPortHistory for disambiguation


@dataclass
class PortHistoryOpen:
    tag_name: str
    port_identifier: str
    valid_from: str
    gating_note: str  # e.g. "MainProgram/MuxRoutine rung 1"


@dataclass
class LoadPlan:
    signal_interface_name: str
    das_name: str | None
    si_type_name: str = "PLC"
    ports_to_create: list[PortCreate] = field(default_factory=list)
    channels_to_create: list[ChannelCreate] = field(default_factory=list)
    port_history_to_open: list[PortHistoryOpen] = field(default_factory=list)


@dataclass
class LoadResult:
    signal_interface_id: int
    ports_created: int
    channels_created: int
    port_histories_opened: int


# ---------------------------------------------------------------------------
# Pure planner
# ---------------------------------------------------------------------------


def plan_l5x_load(
    root: ET.Element,
    signal_interface_name: str,
    *,
    das_name: str | None = None,
    si_type_name: str = "PLC",
    valid_from: str | None = None,
) -> LoadPlan:
    """Derive a LoadPlan from a parsed L5X root element without any HTTP calls."""
    if valid_from is None:
        valid_from = datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    io_map = parse_io_mapping(root)

    # Group io_mapping rows by io_reference
    ref_to_rows: dict[str, list[dict]] = defaultdict(list)
    for row in io_map:
        ref_to_rows[row["io_reference"]].append(row)

    # One port per unique io_reference
    ports: list[PortCreate] = []
    for io_ref, rows in ref_to_rows.items():
        io_dir = rows[0]["io_direction"]
        kind = "analog_input" if io_dir == "I" else "analog_output"
        ports.append(PortCreate(port_identifier=io_ref, kind_name=kind))

    # Mux: io_references shared by more than one distinct instrument_tag
    mux_refs: set[str] = {
        io_ref
        for io_ref, rows in ref_to_rows.items()
        if len({r["instrument_tag"] for r in rows}) > 1
    }

    # Map each unique tag to its io_reference (first occurrence)
    tag_to_io_ref: dict[str, str] = {}
    tag_to_gating: dict[str, str] = {}
    for io_ref, rows in ref_to_rows.items():
        seen: set[str] = set()
        for row in rows:
            tag = row["instrument_tag"]
            if tag not in seen:
                seen.add(tag)
                tag_to_io_ref[tag] = io_ref
                if io_ref in mux_refs:
                    tag_to_gating[tag] = (
                        f"{row['program']}/{row['routine']} rung {row['rung']}"
                    )

    io_tags = set(tag_to_io_ref.keys())

    # Controller-scope tags with no IO mapping → unknown-port channels
    all_tags = parse_tags(root)
    controller_tag_names = {t["name"] for t in all_tags if t["scope"] == "controller"}
    unknown_port_tags = controller_tag_names - io_tags

    channels: list[ChannelCreate] = [
        ChannelCreate(
            tag_name=tag,
            port_identifier=tag_to_io_ref[tag],
            is_mux=(tag_to_io_ref[tag] in mux_refs),
        )
        for tag in sorted(io_tags)
    ] + [
        ChannelCreate(tag_name=tag, port_identifier=None, is_mux=False)
        for tag in sorted(unknown_port_tags)
    ]

    port_histories: list[PortHistoryOpen] = [
        PortHistoryOpen(
            tag_name=tag,
            port_identifier=tag_to_io_ref[tag],
            valid_from=valid_from,
            gating_note=tag_to_gating[tag],
        )
        for tag in sorted(tag_to_gating.keys())
    ]

    return LoadPlan(
        signal_interface_name=signal_interface_name,
        das_name=das_name,
        si_type_name=si_type_name,
        ports_to_create=ports,
        channels_to_create=channels,
        port_history_to_open=port_histories,
    )


# ---------------------------------------------------------------------------
# Apply (HTTP writes via DateaubaseClient)
# ---------------------------------------------------------------------------


def apply_l5x_load(
    plan: LoadPlan,
    client: DateaubaseClient,
    *,
    dry_run: bool = False,
) -> LoadResult:
    """Execute a LoadPlan: provision SI → ports → channels → ChannelPortHistory."""
    if dry_run:
        _print_plan(plan)
        return LoadResult(
            signal_interface_id=0,
            ports_created=len(plan.ports_to_create),
            channels_created=len(plan.channels_to_create),
            port_histories_opened=len(plan.port_history_to_open),
        )

    das = plan.das_name or plan.signal_interface_name
    si_id = client.create_signal_interface(
        das_name=das,
        name=plan.signal_interface_name,
        type_name=plan.si_type_name,
    )

    port_id_map: dict[str, int] = {}
    for port in plan.ports_to_create:
        pid = client.create_signal_interface_port(
            signal_interface_id=si_id,
            port_identifier=port.port_identifier,
            kind_name=port.kind_name,
        )
        port_id_map[port.port_identifier] = pid

    channel_id_map: dict[str, int] = {}
    for ch in plan.channels_to_create:
        # Mux channels are linked to their port via ChannelPortHistory, not directly.
        # Unknown-port channels get port_id=None.
        si_port_id: int | None = None
        if ch.port_identifier is not None and not ch.is_mux:
            si_port_id = port_id_map[ch.port_identifier]
        ch_id = client.create_channel(
            signal_interface_id=si_id,
            tag_name=ch.tag_name,
            signal_interface_port_id=si_port_id,
        )
        channel_id_map[ch.tag_name] = ch_id

    port_histories_opened = 0
    for ph in plan.port_history_to_open:
        client.open_channel_port_history(
            channel_id=channel_id_map[ph.tag_name],
            port_id=port_id_map[ph.port_identifier],
            valid_from=ph.valid_from,
            gating_note=ph.gating_note,
        )
        port_histories_opened += 1

    return LoadResult(
        signal_interface_id=si_id,
        ports_created=len(plan.ports_to_create),
        channels_created=len(plan.channels_to_create),
        port_histories_opened=port_histories_opened,
    )


def _print_plan(plan: LoadPlan) -> None:
    das = plan.das_name or plan.signal_interface_name
    print(f"[DRY-RUN] SignalInterface: {plan.signal_interface_name!r}  DAS: {das!r}  Type: {plan.si_type_name!r}")
    print(f"  Ports to create ({len(plan.ports_to_create)}):")
    for p in plan.ports_to_create:
        print(f"    {p.port_identifier}  [{p.kind_name}]")
    print(f"  Channels to create ({len(plan.channels_to_create)}):")
    for ch in plan.channels_to_create:
        mux_flag = " [MUX]" if ch.is_mux else ""
        port_label = ch.port_identifier or "unknown-port"
        print(f"    {ch.tag_name}  ->  {port_label}{mux_flag}")
    print(f"  ChannelPortHistory rows ({len(plan.port_history_to_open)}):")
    for ph in plan.port_history_to_open:
        print(f"    {ph.tag_name}  ->  {ph.port_identifier}  |  {ph.gating_note}")
