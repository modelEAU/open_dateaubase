"""Unit tests for the pure zip-export builder (app.components.explore_export).

Covers the non-trivial rules: annotation/event overlay matching (range + point),
UTC timestamp column, per-stream CSV+YAML pairing, image embedding, and basename
collision handling.
"""

from __future__ import annotations

import csv
import io
import zipfile

import yaml

from app.components import explore_export as ex


def _read_zip(blob: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        return {n: zf.read(n) for n in zf.namelist()}


def _rows(csv_bytes: bytes) -> list[dict]:
    return list(csv.DictReader(io.StringIO(csv_bytes.decode())))


# --- overlay matching -------------------------------------------------------

class TestOverlay:
    def test_range_annotation_tags_covered_rows_only(self):
        cols_in = ex._overlay_columns(
            "2026-06-19T06:00:00",
            [{"kind": "Outlier", "note": "fouling",
              "start": "2026-06-19T05:00:00", "end": "2026-06-19T07:00:00"}],
            [],
        )
        cols_out = ex._overlay_columns(
            "2026-06-19T08:00:00",
            [{"kind": "Outlier", "note": "fouling",
              "start": "2026-06-19T05:00:00", "end": "2026-06-19T07:00:00"}],
            [],
        )
        assert cols_in["annotation_kind"] == "Outlier"
        assert cols_in["annotation_note"] == "fouling"
        assert cols_out["annotation_kind"] == ""

    def test_point_annotation_matches_exact_timestamp(self):
        ann = [{"kind": "Spike", "note": None,
                "start": "2026-06-19T06:00:00", "end": None}]
        assert ex._overlay_columns("2026-06-19T06:00:00", ann, [])["annotation_kind"] == "Spike"
        assert ex._overlay_columns("2026-06-19T06:00:01", ann, [])["annotation_kind"] == ""

    def test_timezone_offsets_compared_correctly(self):
        # 06:00Z == 02:00-04:00; both must fall in a 05:00Z–07:00Z range.
        ann = [{"kind": "X", "note": None,
                "start": "2026-06-19T05:00:00Z", "end": "2026-06-19T07:00:00Z"}]
        assert ex._overlay_columns("2026-06-19T02:00:00-04:00", ann, [])["annotation_kind"] == "X"

    def test_multiple_overlaps_semicolon_joined(self):
        anns = [
            {"kind": "A", "note": "n1", "start": "2026-06-19T05:00:00", "end": "2026-06-19T07:00:00"},
            {"kind": "B", "note": "n2", "start": "2026-06-19T05:30:00", "end": "2026-06-19T06:30:00"},
        ]
        cols = ex._overlay_columns("2026-06-19T06:00:00", anns, [])
        assert cols["annotation_kind"] == "A; B"
        assert cols["annotation_note"] == "n1; n2"


def test_normalizers_map_raw_api_shapes():
    # AnnotationResponse: kind nested under type.name.
    a = ex.overlay_from_annotation(
        {"type": {"name": "Mask"}, "title": "Fault", "comment": "masked",
         "start_time": "2026-06-01T00:00:00", "end_time": None}
    )
    assert a == {"kind": "Mask", "note": "Fault — masked",
                 "start": "2026-06-01T00:00:00", "end": None}
    # Equipment lifecycle event: kind under event_type_name, text under notes.
    e = ex.overlay_from_event(
        {"event_type_name": "Calibration", "notes": "zero check",
         "start_datetime": "2026-06-19T08:00:00", "end_datetime": "2026-06-19T09:00:00"}
    )
    assert e["kind"] == "Calibration"
    assert e["note"] == "zero check"
    assert e["start"] == "2026-06-19T08:00:00"


# --- full zip ---------------------------------------------------------------

def test_scalar_zip_has_paired_csv_and_yaml_with_overlay():
    entry = {
        "filename": "CH-5 TSS",  # space -> sanitized
        "value_kind": 1,
        "data": {
            "parameter": "TSS", "unit": "mg/L",
            "data": [
                {"timestamp": "2026-06-19T04:00:00", "value": 10.0, "quality_code": 1},
                {"timestamp": "2026-06-19T06:00:00", "value": 11.0, "quality_code": 2},
            ],
        },
        "annotations": [{"kind": "Outlier", "note": "fouling",
                         "start": "2026-06-19T06:00:00", "end": None}],
        "events": [{"kind": "Calib", "note": "zero",
                    "start": "2026-06-19T04:00:00", "end": "2026-06-19T04:30:00"}],
        "pedigree": {"stream_id": 5, "site": {"name": "pilEAU"}},
    }
    files = _read_zip(ex.build_export_zip([entry]))

    assert "CH-5_TSS.csv" in files
    assert "CH-5_TSS.yaml" in files

    rows = _rows(files["CH-5_TSS.csv"])
    assert rows[0]["timestamp_utc"] == "2026-06-19T04:00:00"
    assert rows[0]["value"] == "10.0"
    assert rows[0]["event_kind"] == "Calib"      # covered by event range
    assert rows[0]["annotation_kind"] == ""
    assert rows[1]["annotation_kind"] == "Outlier"  # point match at 06:00
    assert rows[1]["event_kind"] == ""

    ped = yaml.safe_load(files["CH-5_TSS.yaml"])
    assert ped["site"]["name"] == "pilEAU"


def test_quality_code_rendered_as_label_not_id():
    entry = {
        "filename": "CH-5_TSS", "value_kind": 1,
        "data": {"parameter": "TSS", "unit": "mg/L", "data": [
            {"timestamp": "2026-06-19T04:00:00", "value": 10.0, "quality_code": 1},
            {"timestamp": "2026-06-19T06:00:00", "value": 11.0, "quality_code": 2},
        ]},
        "annotations": [], "events": [], "pedigree": {},
    }
    files = _read_zip(ex.build_export_zip([entry], {1: "Accepted", 2: "Suspect"}))
    rows = _rows(files["CH-5_TSS.csv"])
    assert rows[0]["quality_code"] == "Accepted"
    assert rows[1]["quality_code"] == "Suspect"


def test_unknown_quality_code_falls_back_to_raw_value():
    entry = {
        "filename": "CH-5_TSS", "value_kind": 1,
        "data": {"parameter": "TSS", "unit": "mg/L", "data": [
            {"timestamp": "2026-06-19T04:00:00", "value": 10.0, "quality_code": 9},
        ]},
        "annotations": [], "events": [], "pedigree": {},
    }
    row = _rows(_read_zip(ex.build_export_zip([entry], {1: "Accepted"}))["CH-5_TSS.csv"])[0]
    assert row["quality_code"] == "9"


def test_per_row_location_and_campaign_follow_deployment_timeline():
    """The spicy case: rows before/after an equipment move carry the location and
    campaign that were active at their timestamp (resolved from the timeline)."""
    entry = {
        "filename": "CH-5_TSS",
        "value_kind": 1,
        "data": {
            "parameter": "TSS", "unit": "mg/L",
            "data": [
                {"timestamp": "2026-02-15T00:00:00", "value": 9.8, "quality_code": 1},
                {"timestamp": "2026-05-15T00:00:00", "value": 7.1, "quality_code": 1},
            ],
        },
        "annotations": [], "events": [],
        "pedigree": {
            "stream_id": 5,
            "deployments": [
                {"valid_from": "2026-01-01T00:00:00", "valid_to": "2026-04-01T00:00:00",
                 "sampling_location": {"name": "Inlet"},
                 "campaign": {"name": "Winter 2026"}},
                {"valid_from": "2026-04-01T00:00:00", "valid_to": None,
                 "sampling_location": {"name": "Effluent"},
                 "campaign": {"name": "Spring 2026"}},
            ],
        },
    }
    rows = _rows(_read_zip(ex.build_export_zip([entry]))["CH-5_TSS.csv"])
    assert rows[0]["sampling_location"] == "Inlet"
    assert rows[0]["campaign"] == "Winter 2026"
    assert rows[1]["sampling_location"] == "Effluent"   # after the move
    assert rows[1]["campaign"] == "Spring 2026"


def test_lab_fixed_segment_applies_to_all_rows():
    entry = {
        "filename": "LAB-1_TSS",
        "value_kind": 1,
        "data": {"parameter": "TSS", "unit": "mg/L",
                 "data": [{"timestamp": "2026-05-15T00:00:00", "value": 7.1}]},
        "annotations": [], "events": [],
        "pedigree": {"deployments": [
            {"valid_from": None, "valid_to": None,
             "sampling_location": {"name": "Effluent"},
             "campaign": {"name": "Routine"}}]},
    }
    row = _rows(_read_zip(ex.build_export_zip([entry]))["LAB-1_TSS.csv"])[0]
    assert row["sampling_location"] == "Effluent"
    assert row["campaign"] == "Routine"


def test_image_stream_embeds_files_and_references_them():
    entry = {
        "filename": "CH-7_cam",
        "value_kind": 4,
        "data": {"parameter": "Image", "unit": "",
                 "data": [{"timestamp": "2026-06-19T04:00:00", "width": 640,
                           "observation_id": 91}]},
        "annotations": [], "events": [],
        "pedigree": {"stream_id": 7},
        "images": {91: b"\xff\xd8\xff jpegbytes"},
    }
    files = _read_zip(ex.build_export_zip([entry]))
    img_path = "images/CH-7_cam/2026-06-19T04_00_00_obs91.jpg"
    assert img_path in files
    assert files[img_path] == b"\xff\xd8\xff jpegbytes"
    row = _rows(files["CH-7_cam.csv"])[0]
    assert row["image_file"] == img_path


def test_lab_replicates_sharing_a_timestamp_embed_as_separate_files():
    """Two replicates of one sample share the sample-collection time. Keyed by
    timestamp, the second overwrote the first and the bundle held one picture."""
    ts = "2026-07-14T16:00:00"
    entry = {
        "filename": "LAB-22_floc",
        "value_kind": 4,
        "data": {"parameter": "floc_morphology", "unit": "",
                 "data": [{"timestamp": ts, "observation_id": 501},
                          {"timestamp": ts, "observation_id": 502}]},
        "annotations": [], "events": [],
        "pedigree": {},
        "images": {501: b"replicate-one", 502: b"replicate-two"},
    }
    files = _read_zip(ex.build_export_zip([entry]))
    embedded = {p: b for p, b in files.items() if p.startswith("images/")}
    assert len(embedded) == 2, f"replicates collapsed into {list(embedded)}"
    assert set(embedded.values()) == {b"replicate-one", b"replicate-two"}
    assert len({r["image_file"] for r in _rows(files["LAB-22_floc.csv"])}) == 2


def test_duplicate_basenames_do_not_collide():
    e = {"filename": "dup", "value_kind": 1,
         "data": {"parameter": "p", "unit": "u", "data": []},
         "annotations": [], "events": [], "pedigree": {}}
    files = _read_zip(ex.build_export_zip([dict(e), dict(e)]))
    assert "dup.csv" in files
    assert "dup_2.csv" in files
