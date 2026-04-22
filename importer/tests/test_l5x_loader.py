"""Unit tests for table_import.l5x_loader.

Uses a synthetic L5X XML string built inline — no real .L5X file required.

Topology:
  Modules:    Local (chassis, slot 0), AIN_Slot3 (slot 3), AIN_Slot6 (slot 6)
  Controller tags (unknown-port): BatchID, RecipePhase
  Program tags (io-mapped):
    DO_Probe  -> Local:3:I.Ch0Data  (unique)
    Turb_A    -> Local:6:I.Ch0Data  (mux with Turb_B)
    Turb_B    -> Local:6:I.Ch0Data  (mux with Turb_A)
"""

from __future__ import annotations

from unittest.mock import MagicMock
from xml.etree import ElementTree as ET

import pytest

from table_import.l5x_loader import (
    LoadPlan,
    apply_l5x_load,
    parse_io_mapping,
    parse_modules,
    parse_tags,
    plan_l5x_load,
)

# ---------------------------------------------------------------------------
# Synthetic L5X fixture
# ---------------------------------------------------------------------------

SYNTHETIC_L5X = """\
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<RSLogix5000Content SoftwareRevision="32">
  <Controller Name="TestPLC" ProcessorType="1756-L73">
    <Tags>
      <Tag Name="BatchID" TagType="Base" DataType="DINT" ExternalAccess="Read/Write">
        <Description>Batch identifier</Description>
      </Tag>
      <Tag Name="RecipePhase" TagType="Base" DataType="INT" ExternalAccess="Read/Write"/>
    </Tags>
    <Modules>
      <Module Name="Local" CatalogNumber="1756-L73" Vendor="Rockwell"
              ProductType="Controller" ProductCode="94"
              ParentModule="Local" ParentModPortId="1" Inhibited="false">
        <Ports><Port Address="0"/></Ports>
      </Module>
      <Module Name="AIN_Slot3" CatalogNumber="1756-IF8" Vendor="Rockwell"
              ProductType="Analog" ProductCode="10"
              ParentModule="Local" ParentModPortId="1" Inhibited="false">
        <Ports><Port Address="3"/></Ports>
      </Module>
      <Module Name="AIN_Slot6" CatalogNumber="1756-IF8" Vendor="Rockwell"
              ProductType="Analog" ProductCode="10"
              ParentModule="Local" ParentModPortId="1" Inhibited="false">
        <Ports><Port Address="6"/></Ports>
      </Module>
    </Modules>
    <Programs>
      <Program Name="MainProgram">
        <Tags>
          <Tag Name="DO_Probe" TagType="Base" DataType="REAL" ExternalAccess="Read/Write">
            <Description>Dissolved oxygen sensor</Description>
          </Tag>
          <Tag Name="Turb_A" TagType="Base" DataType="REAL" ExternalAccess="Read/Write">
            <Description>Turbidity channel A (mux)</Description>
          </Tag>
          <Tag Name="Turb_B" TagType="Base" DataType="REAL" ExternalAccess="Read/Write">
            <Description>Turbidity channel B (mux)</Description>
          </Tag>
        </Tags>
        <Routines>
          <Routine Name="MainRoutine">
            <Rung Number="0" Type="N">
              <Text><![CDATA[MOV(Local:3:I.Ch0Data,DO_Probe);]]></Text>
            </Rung>
          </Routine>
          <Routine Name="MuxRoutine">
            <Rung Number="0" Type="N">
              <Text><![CDATA[MOV(Local:6:I.Ch0Data,Turb_A);]]></Text>
            </Rung>
            <Rung Number="1" Type="N">
              <Text><![CDATA[MOV(Local:6:I.Ch0Data,Turb_B);]]></Text>
            </Rung>
          </Routine>
        </Routines>
      </Program>
    </Programs>
  </Controller>
</RSLogix5000Content>
"""

FIXED_VALID_FROM = "2026-01-01T00:00:00"


@pytest.fixture
def l5x_root() -> ET.Element:
    return ET.fromstring(SYNTHETIC_L5X)


# ---------------------------------------------------------------------------
# parse_modules
# ---------------------------------------------------------------------------


def test_parse_modules_returns_three_rows(l5x_root):
    modules = parse_modules(l5x_root)
    assert len(modules) == 3
    names = {m["name"] for m in modules}
    assert names == {"Local", "AIN_Slot3", "AIN_Slot6"}


def test_parse_modules_slot_addresses(l5x_root):
    modules = parse_modules(l5x_root)
    by_name = {m["name"]: m for m in modules}
    assert by_name["AIN_Slot3"]["slot_address"] == "3"
    assert by_name["AIN_Slot6"]["slot_address"] == "6"
    assert by_name["Local"]["slot_address"] == "0"


# ---------------------------------------------------------------------------
# parse_tags
# ---------------------------------------------------------------------------


def test_parse_tags_count(l5x_root):
    tags = parse_tags(l5x_root)
    assert len(tags) == 5  # 2 controller + 3 program


def test_parse_tags_scopes(l5x_root):
    tags = parse_tags(l5x_root)
    controller_tags = [t for t in tags if t["scope"] == "controller"]
    program_tags = [t for t in tags if t["scope"] == "program"]
    assert len(controller_tags) == 2
    assert len(program_tags) == 3


def test_parse_tags_controller_names(l5x_root):
    tags = parse_tags(l5x_root)
    ctrl_names = {t["name"] for t in tags if t["scope"] == "controller"}
    assert ctrl_names == {"BatchID", "RecipePhase"}


def test_parse_tags_program_names(l5x_root):
    tags = parse_tags(l5x_root)
    prog_names = {t["name"] for t in tags if t["scope"] == "program"}
    assert prog_names == {"DO_Probe", "Turb_A", "Turb_B"}


def test_parse_tags_description(l5x_root):
    tags = parse_tags(l5x_root)
    by_name = {t["name"]: t for t in tags}
    assert by_name["BatchID"]["description"] == "Batch identifier"
    assert by_name["RecipePhase"]["description"] == ""


# ---------------------------------------------------------------------------
# parse_io_mapping
# ---------------------------------------------------------------------------


def test_parse_io_mapping_returns_three_rows(l5x_root):
    rows = parse_io_mapping(l5x_root)
    assert len(rows) == 3


def test_parse_io_mapping_unique_port(l5x_root):
    rows = parse_io_mapping(l5x_root)
    do_rows = [r for r in rows if r["instrument_tag"] == "DO_Probe"]
    assert len(do_rows) == 1
    assert do_rows[0]["io_reference"] == "Local:3:I.Ch0Data"
    assert do_rows[0]["io_direction"] == "I"
    assert do_rows[0]["mapping_direction"] == "input"


def test_parse_io_mapping_mux_rows(l5x_root):
    rows = parse_io_mapping(l5x_root)
    mux_rows = [r for r in rows if r["io_reference"] == "Local:6:I.Ch0Data"]
    assert len(mux_rows) == 2
    mux_tags = {r["instrument_tag"] for r in mux_rows}
    assert mux_tags == {"Turb_A", "Turb_B"}


def test_parse_io_mapping_rung_numbers(l5x_root):
    rows = parse_io_mapping(l5x_root)
    by_tag = {r["instrument_tag"]: r for r in rows}
    assert by_tag["Turb_A"]["rung"] == "0"
    assert by_tag["Turb_B"]["rung"] == "1"
    assert by_tag["Turb_A"]["routine"] == "MuxRoutine"


# ---------------------------------------------------------------------------
# plan_l5x_load
# ---------------------------------------------------------------------------


@pytest.fixture
def plan(l5x_root) -> LoadPlan:
    return plan_l5x_load(
        l5x_root,
        "test_plc",
        das_name="hedi_das",
        valid_from=FIXED_VALID_FROM,
    )


def test_plan_signal_interface_name(plan):
    assert plan.signal_interface_name == "test_plc"
    assert plan.das_name == "hedi_das"


def test_plan_ports_count(plan):
    assert len(plan.ports_to_create) == 2


def test_plan_ports_identifiers(plan):
    identifiers = {p.port_identifier for p in plan.ports_to_create}
    assert identifiers == {"Local:3:I.Ch0Data", "Local:6:I.Ch0Data"}


def test_plan_ports_kind(plan):
    for p in plan.ports_to_create:
        assert p.kind_name == "analog_input"


def test_plan_channels_count(plan):
    # 3 io-mapped + 2 unknown-port
    assert len(plan.channels_to_create) == 5


def test_plan_channels_io_mapped(plan):
    ch_by_name = {c.tag_name: c for c in plan.channels_to_create}
    do = ch_by_name["DO_Probe"]
    assert do.port_identifier == "Local:3:I.Ch0Data"
    assert do.is_mux is False


def test_plan_channels_mux(plan):
    ch_by_name = {c.tag_name: c for c in plan.channels_to_create}
    for tag in ("Turb_A", "Turb_B"):
        ch = ch_by_name[tag]
        assert ch.port_identifier == "Local:6:I.Ch0Data"
        assert ch.is_mux is True


def test_plan_channels_unknown_port(plan):
    ch_by_name = {c.tag_name: c for c in plan.channels_to_create}
    for tag in ("BatchID", "RecipePhase"):
        ch = ch_by_name[tag]
        assert ch.port_identifier is None
        assert ch.is_mux is False


def test_plan_port_histories_count(plan):
    # Only mux channels get ChannelPortHistory rows
    assert len(plan.port_history_to_open) == 2


def test_plan_port_histories_tags(plan):
    ph_tags = {ph.tag_name for ph in plan.port_history_to_open}
    assert ph_tags == {"Turb_A", "Turb_B"}


def test_plan_port_histories_gating_notes(plan):
    ph_by_tag = {ph.tag_name: ph for ph in plan.port_history_to_open}
    assert ph_by_tag["Turb_A"].gating_note == "MainProgram/MuxRoutine rung 0"
    assert ph_by_tag["Turb_B"].gating_note == "MainProgram/MuxRoutine rung 1"


def test_plan_port_histories_valid_from(plan):
    for ph in plan.port_history_to_open:
        assert ph.valid_from == FIXED_VALID_FROM


# ---------------------------------------------------------------------------
# apply_l5x_load — mocked DateaubaseClient
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_client():
    from table_import.api_client import DateaubaseClient

    client = MagicMock(spec=DateaubaseClient)
    client.create_signal_interface.return_value = 1
    # Two ports: slot-3 → id 10, slot-6 → id 11
    client.create_signal_interface_port.side_effect = [10, 11]
    # Five channels in order: DO_Probe→20, Turb_A→21, Turb_B→22, BatchID→23, RecipePhase→24
    client.create_channel.side_effect = [20, 21, 22, 23, 24]
    # Two port history rows
    client.open_channel_port_history.side_effect = [30, 31]
    return client


def test_apply_creates_signal_interface(plan, mock_client):
    result = apply_l5x_load(plan, mock_client)
    mock_client.create_signal_interface.assert_called_once_with(
        das_name="hedi_das",
        name="test_plc",
        type_name="PLC",
    )
    assert result.signal_interface_id == 1


def test_apply_creates_two_ports(plan, mock_client):
    result = apply_l5x_load(plan, mock_client)
    assert mock_client.create_signal_interface_port.call_count == 2
    assert result.ports_created == 2


def test_apply_creates_five_channels(plan, mock_client):
    result = apply_l5x_load(plan, mock_client)
    assert mock_client.create_channel.call_count == 5
    assert result.channels_created == 5


def test_apply_non_mux_channel_linked_to_port(plan, mock_client):
    """DO_Probe (non-mux) must be created with signal_interface_port_id=10 (slot-3 port)."""
    apply_l5x_load(plan, mock_client)
    create_calls = mock_client.create_channel.call_args_list
    # DO_Probe is first in sorted(io_tags)
    do_call = create_calls[0]
    assert do_call.kwargs["tag_name"] == "DO_Probe"
    assert do_call.kwargs["signal_interface_port_id"] == 10


def test_apply_mux_channels_have_no_direct_port(plan, mock_client):
    """Turb_A and Turb_B (mux) must be created without a direct port link."""
    apply_l5x_load(plan, mock_client)
    create_calls = mock_client.create_channel.call_args_list
    by_tag = {c.kwargs["tag_name"]: c for c in create_calls}
    for tag in ("Turb_A", "Turb_B"):
        assert by_tag[tag].kwargs["signal_interface_port_id"] is None


def test_apply_unknown_port_channels_have_no_port(plan, mock_client):
    apply_l5x_load(plan, mock_client)
    create_calls = mock_client.create_channel.call_args_list
    by_tag = {c.kwargs["tag_name"]: c for c in create_calls}
    for tag in ("BatchID", "RecipePhase"):
        assert by_tag[tag].kwargs["signal_interface_port_id"] is None


def test_apply_opens_two_port_history_rows(plan, mock_client):
    result = apply_l5x_load(plan, mock_client)
    assert mock_client.open_channel_port_history.call_count == 2
    assert result.port_histories_opened == 2


def test_apply_port_history_uses_correct_channel_and_port_ids(plan, mock_client):
    apply_l5x_load(plan, mock_client)
    ph_calls = mock_client.open_channel_port_history.call_args_list
    ph_by_channel = {c.kwargs["channel_id"]: c for c in ph_calls}
    # Turb_A got channel_id=21, Turb_B got channel_id=22; slot-6 port_id=11
    assert 21 in ph_by_channel
    assert ph_by_channel[21].kwargs["port_id"] == 11
    assert "MuxRoutine rung 0" in ph_by_channel[21].kwargs["gating_note"]
    assert 22 in ph_by_channel
    assert ph_by_channel[22].kwargs["port_id"] == 11


def test_apply_result_summary(plan, mock_client):
    result = apply_l5x_load(plan, mock_client)
    assert result.signal_interface_id == 1
    assert result.ports_created == 2
    assert result.channels_created == 5
    assert result.port_histories_opened == 2


# ---------------------------------------------------------------------------
# apply_l5x_load — dry_run
# ---------------------------------------------------------------------------


def test_dry_run_prints_plan_and_makes_no_http_calls(plan, mock_client):
    result = apply_l5x_load(plan, mock_client, dry_run=True)
    mock_client.create_signal_interface.assert_not_called()
    mock_client.create_signal_interface_port.assert_not_called()
    mock_client.create_channel.assert_not_called()
    mock_client.open_channel_port_history.assert_not_called()
    # LoadResult still reflects the plan counts
    assert result.signal_interface_id == 0
    assert result.ports_created == 2
    assert result.channels_created == 5
    assert result.port_histories_opened == 2


def test_dry_run_output_mentions_si_name(plan, mock_client, capsys):
    apply_l5x_load(plan, mock_client, dry_run=True)
    captured = capsys.readouterr()
    assert "test_plc" in captured.out
    assert "DRY-RUN" in captured.out


def test_dry_run_output_mentions_mux(plan, mock_client, capsys):
    apply_l5x_load(plan, mock_client, dry_run=True)
    captured = capsys.readouterr()
    assert "MUX" in captured.out


def test_dry_run_output_mentions_unknown_port(plan, mock_client, capsys):
    apply_l5x_load(plan, mock_client, dry_run=True)
    captured = capsys.readouterr()
    assert "unknown-port" in captured.out
