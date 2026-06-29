"""Unit tests for channel_repository.get_stream_pedigree.

Pedigree = the organizational/spatial context of a stream, as a time-bound
deployment timeline (sampling location, process unit, site, campaign,
responsible person per deployment) — distinct from its processing provenance.
See CONTEXT.md. A sensor channel can span several deployments over its life
(equipment moves); a lab series has one fixed open segment.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

from api.v1.repositories import channel_repository


def _conn(fetchone_seq, fetchall_seq=()):
    cursor = MagicMock()
    cursor.fetchone.side_effect = list(fetchone_seq)
    cursor.fetchall.side_effect = list(fetchall_seq)
    conn = MagicMock()
    conn.cursor.return_value = cursor
    return conn, cursor


# Column orders mirror _pedigree_sampling_point / _pedigree_campaign SELECTs.
_SP_INLET = ("Inlet", 46.7, -71.2, 7, "R-210", "Bioreactor", "Tank",
             3, "pilEAU", "Quebec", "QC", "Canada")
_SP_EFF = ("Effluent", 46.8, -71.3, 8, "R-310", "Clarifier", "Tank",
           3, "pilEAU", "Quebec", "QC", "Canada")
# Campaign SELECT no longer carries site columns; sites are a separate query.
_CAMP_WINTER = ("Winter 2026", "Experiment", "2026-01-01", "2026-04-01",
                11, "Jean", "Tremblay", "jt@x.io", "PI", "modelEAU")
_CAMP_SPRING = ("Spring 2026", "Experiment", "2026-04-01", "2026-07-01",
                12, "Marie", "Roy", "mr@x.io", "Eng", "modelEAU")
# Derived single-site fallback row (site_id, name, city, province, country).
_CAMP_SITE = (3, "pilEAU", "Quebec", "QC", "Canada")


def test_sensor_spanning_two_deployments_yields_a_timeline():
    """The spicy case: a channel whose data crosses an equipment move resolves to
    two segments, each with its own location + campaign + responsible person."""
    identity = ("TSS", "mg/L", "Scalar", "CH-TSS")
    seg1 = (101, "2026-01-01", "2026-04-01", "EQ5", 21, 5)
    seg2 = (102, "2026-04-01", None, "EQ5", 22, 6)  # open-ended (still active)
    conn, _ = _conn(
        fetchone_seq=[identity, _SP_INLET, _CAMP_WINTER, _SP_EFF, _CAMP_SPRING],
        # segments, then derived sites per campaign (Winter, Spring).
        fetchall_seq=[[seg1, seg2], [_CAMP_SITE], [_CAMP_SITE]],
    )

    ped = channel_repository.get_stream_pedigree(conn, 42)

    assert ped["kind"] == "sensor"
    assert ped["parameter"] == "TSS"
    assert len(ped["deployments"]) == 2

    d0, d1 = ped["deployments"]
    assert d0["valid_from"] == "2026-01-01"
    assert d0["valid_to"] == "2026-04-01"
    assert d0["sampling_location"] == {
        "sampling_point_id": 21, "name": "Inlet", "latitude": 46.7, "longitude": -71.2}
    assert d0["process_unit"]["tag"] == "R-210"
    assert d0["campaign"]["name"] == "Winter 2026"
    assert d0["responsible_person"]["name"] == "Jean Tremblay"

    assert d1["valid_to"] is None  # open deployment
    assert d1["sampling_location"]["name"] == "Effluent"
    assert d1["campaign"]["name"] == "Spring 2026"
    assert d1["responsible_person"]["name"] == "Marie Roy"


def test_sensor_window_filters_segments_in_sql():
    identity = ("pH", "-", "Scalar", "CH-pH")
    conn, cursor = _conn(fetchone_seq=[identity], fetchall_seq=[[]])

    channel_repository.get_stream_pedigree(
        conn, 8, from_dt=datetime(2026, 5, 1), to_dt=datetime(2026, 6, 1)
    )

    seg_call = next(
        c for c in cursor.execute.call_args_list
        if "EquipmentLocationHistory" in c.args[0] and "vw_ChannelResolved" in c.args[0]
    )
    sql = seg_call.args[0]
    assert "elh.[ValidFrom] <= ?" in sql
    assert "elh.[ValidTo] IS NULL OR elh.[ValidTo] >= ?" in sql
    assert datetime(2026, 6, 1) in seg_call.args  # to_dt bound
    assert datetime(2026, 5, 1) in seg_call.args  # from_dt bound


def test_lab_series_single_open_segment():
    lab_identity = ("TSS", "mg/L", "Scalar", "TSS@Eff", 21, 5)
    # sensor identity misses -> lab branch; then one segment's lookups.
    conn, cursor = _conn(
        fetchone_seq=[None, lab_identity, _SP_INLET, _CAMP_WINTER],
        fetchall_seq=[[_CAMP_SITE]],  # derived sites for the campaign
    )

    ped = channel_repository.get_stream_pedigree(conn, 7)

    assert ped["kind"] == "lab"
    assert len(ped["deployments"]) == 1
    seg = ped["deployments"][0]
    assert seg["valid_from"] is None and seg["valid_to"] is None
    assert seg["equipment_identifier"] is None
    assert seg["sampling_location"]["name"] == "Inlet"
    assert seg["campaign"]["name"] == "Winter 2026"
    assert any("AnalysisSeries" in c.args[0] for c in cursor.execute.call_args_list)


def test_unknown_stream_returns_none():
    conn, _ = _conn(fetchone_seq=[None, None])
    assert channel_repository.get_stream_pedigree(conn, 123) is None
