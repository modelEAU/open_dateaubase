"""Unit tests for the lab AnalysisSeries annotation arm (Slice 2).

No database — the pyodbc connection/cursor are MagicMocks. We assert that:

Repository:
  - create_annotation writes AnalysisSeries_ID (not Channel_ID) when anchored to
    a series, and the XOR is guarded.
  - get_annotations_for_series filters on AnalysisSeries_ID and carries the
    analysis_series_id through _row_to_annotation.

Service:
  - create_annotation_for_series + get_annotations_for_series build the
    series-anchored response (anchor.kind == "series").
  - both 404 when the AnalysisSeries does not exist (mirrors the channel guard).
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from api.v1.repositories import annotation_repository as repo
from api.v1.services import annotation_service as svc
from api.v1.schemas.annotations import AnnotationCreate


FROM = datetime(2026, 1, 1, tzinfo=timezone.utc)
TO = datetime(2026, 2, 1, tzinfo=timezone.utc)


def _conn_returning(rows: list):
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchall.return_value = rows
    conn.cursor.return_value = cursor
    return conn, cursor


def _sql(cursor) -> str:
    return "\n".join(c.args[0] for c in cursor.execute.call_args_list)


# A full _ANNOTATION_SELECT row (18 columns); index 1 = Channel_ID (NULL for
# lab), index 16 = AnalysisSeries_ID, index 17 = Observation_ID.
def _series_row(series_id: int = 7, observation_id=None):
    return (
        1,              # Annotation_ID
        None,           # Channel_ID
        3,              # AnnotationKind_ID
        "Fault",        # Name
        "#FF0000",      # Color
        FROM,           # StartTime
        TO,             # EndTime
        "title",        # Title
        "comment",      # Comment
        None,           # AuthorPerson_ID
        None,           # AuthorName
        None,           # Campaign_ID
        None,           # CampaignName
        None,           # EquipmentEvent_ID
        FROM,           # CreatedDateTime
        None,           # ModifiedDateTime
        series_id,      # AnalysisSeries_ID
        observation_id, # Observation_ID
    )


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------


class TestRepositoryCreate:
    def test_create_writes_analysis_series_id_not_channel(self):
        conn, cursor = _conn_returning([])
        cursor.fetchone.return_value = (42, FROM)
        out = repo.create_annotation(
            conn,
            analysis_series_id=7,
            annotation_kind_id=3,
            start_time=FROM,
            end_time=TO,
            author_person_id=None,
            campaign_id=None,
            equipment_event_id=None,
            title=None,
            comment=None,
        )
        sql = _sql(cursor)
        assert "[AnalysisSeries_ID]" in sql
        # Bound params: Channel_ID is None, AnalysisSeries_ID is 7 (positions 1,2)
        args = cursor.execute.call_args_list[0].args
        assert args[1] is None  # channel_id
        assert args[2] == 7  # analysis_series_id
        assert out["annotation_id"] == 42

    def test_create_rejects_both_anchors(self):
        conn, _ = _conn_returning([])
        with pytest.raises(ValueError):
            repo.create_annotation(
                conn,
                channel_id=5,
                analysis_series_id=7,
                annotation_kind_id=3,
                start_time=FROM,
                end_time=None,
                author_person_id=None,
                campaign_id=None,
                equipment_event_id=None,
                title=None,
                comment=None,
            )

    def test_create_rejects_neither_anchor(self):
        conn, _ = _conn_returning([])
        with pytest.raises(ValueError):
            repo.create_annotation(
                conn,
                annotation_kind_id=3,
                start_time=FROM,
                end_time=None,
                author_person_id=None,
                campaign_id=None,
                equipment_event_id=None,
                title=None,
                comment=None,
            )


    def test_create_threads_observation_id_pin(self):
        conn, cursor = _conn_returning([])
        cursor.fetchone.return_value = (42, FROM)
        repo.create_annotation(
            conn,
            analysis_series_id=7,
            annotation_kind_id=3,
            start_time=FROM,
            end_time=None,
            author_person_id=None,
            campaign_id=None,
            equipment_event_id=None,
            title=None,
            comment=None,
            observation_id=61,
        )
        sql = _sql(cursor)
        assert "[Observation_ID]" in sql
        # Observation_ID is the last bound param of the INSERT.
        assert cursor.execute.call_args_list[0].args[-1] == 61


class TestObservationAnchorLookup:
    def test_resolves_lab_observation_via_lab_analysis(self):
        # Channel_ID NULL, AnalysisSeries_ID 7 (lab path through LabAnalysis).
        conn, cursor = _conn_returning([])
        cursor.fetchone.return_value = (None, 7)
        out = repo.get_observation_anchor(conn, 50)
        sql = _sql(cursor)
        assert "[LabAnalysis]" in sql
        assert "[AnalysisSeries_ID]" in sql
        assert out == {"channel_id": None, "analysis_series_id": 7}

    def test_resolves_sensor_observation_via_channel(self):
        conn, cursor = _conn_returning([])
        cursor.fetchone.return_value = (42, None)
        out = repo.get_observation_anchor(conn, 70)
        assert out == {"channel_id": 42, "analysis_series_id": None}

    def test_missing_observation_returns_none(self):
        conn, cursor = _conn_returning([])
        cursor.fetchone.return_value = None
        assert repo.get_observation_anchor(conn, 999) is None


class TestRepositoryRead:
    def test_get_for_series_filters_on_series_id(self):
        conn, cursor = _conn_returning([_series_row(7)])
        rows = repo.get_annotations_for_series(conn, 7, FROM, TO)
        sql = _sql(cursor)
        assert "a.[AnalysisSeries_ID] = ?" in sql
        assert "a.[Channel_ID] = ?" not in sql
        assert cursor.execute.call_args_list[0].args[1] == 7
        assert rows[0]["analysis_series_id"] == 7
        assert rows[0]["channel_id"] is None


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


def _patch_series_exists(monkeypatch, exists: bool = True):
    monkeypatch.setattr(
        svc.ingestion_repository,
        "get_analysis_series_by_id",
        lambda conn, sid: ({"analysis_series_id": sid} if exists else None),
    )


class TestServiceCreate:
    def test_create_for_series_returns_series_anchor(self, monkeypatch):
        _patch_series_exists(monkeypatch, True)
        monkeypatch.setattr(
            svc.annotation_repository,
            "get_annotation_kind_by_name",
            lambda conn, name: {
                "annotation_kind_id": 3,
                "annotation_type_name": "Fault",
                "color": "#FF0000",
            },
        )
        monkeypatch.setattr(
            svc.annotation_repository,
            "create_annotation",
            lambda conn, **kw: {"annotation_id": 99, "created_datetime": FROM},
        )
        data = AnnotationCreate(annotation_type="Fault", start_time=FROM, end_time=TO)
        out = svc.create_annotation_for_series(MagicMock(), 7, data)
        assert out["anchor"] == {"kind": "series", "id": 7}
        assert out["annotation_id"] == 99

    def test_create_for_missing_series_404(self, monkeypatch):
        _patch_series_exists(monkeypatch, False)
        data = AnnotationCreate(annotation_type="Fault", start_time=FROM)
        with pytest.raises(HTTPException) as exc:
            svc.create_annotation_for_series(MagicMock(), 999, data)
        assert exc.value.status_code == 404


def _patch_channel_exists(monkeypatch, exists: bool = True):
    monkeypatch.setattr(
        svc.channel_repository,
        "get_channel_by_id",
        lambda conn, cid: ({"channel_id": cid} if exists else None),
    )


def _patch_kind(monkeypatch):
    monkeypatch.setattr(
        svc.annotation_repository,
        "get_annotation_kind_by_name",
        lambda conn, name: {
            "annotation_kind_id": 3,
            "annotation_type_name": "Fault",
            "color": "#FF0000",
        },
    )


def _patch_create(monkeypatch, capture: dict):
    def _create(conn, **kw):
        capture.update(kw)
        return {"annotation_id": 99, "created_datetime": FROM}

    monkeypatch.setattr(svc.annotation_repository, "create_annotation", _create)


def _patch_observation_anchor(monkeypatch, anchor: dict | None):
    monkeypatch.setattr(
        svc.annotation_repository,
        "get_observation_anchor",
        lambda conn, oid: anchor,
    )


class TestPinIntegrityGuard:
    """Slice 3 — _assert_pin_in_anchor wired into both create paths.

    A pinned Observation from a *different* stream must be rejected with 422
    on both the sensor arm and the lab arm; a matching pin persists Observation_ID.
    """

    # --- lab arm -----------------------------------------------------------
    def test_series_pin_from_different_series_422(self, monkeypatch):
        _patch_series_exists(monkeypatch, True)
        _patch_kind(monkeypatch)
        _patch_create(monkeypatch, {})
        # Observation 50 belongs to series 8, but we anchor to series 7.
        _patch_observation_anchor(
            monkeypatch, {"channel_id": None, "analysis_series_id": 8}
        )
        data = AnnotationCreate(
            annotation_type="Fault", start_time=FROM, observation_id=50
        )
        with pytest.raises(HTTPException) as exc:
            svc.create_annotation_for_series(MagicMock(), 7, data)
        assert exc.value.status_code == 422

    def test_series_pin_matching_series_201_persists_observation(self, monkeypatch):
        _patch_series_exists(monkeypatch, True)
        _patch_kind(monkeypatch)
        captured: dict = {}
        _patch_create(monkeypatch, captured)
        _patch_observation_anchor(
            monkeypatch, {"channel_id": None, "analysis_series_id": 7}
        )
        data = AnnotationCreate(
            annotation_type="Fault", start_time=FROM, observation_id=50
        )
        out = svc.create_annotation_for_series(MagicMock(), 7, data)
        assert out["observation_id"] == 50
        assert captured["observation_id"] == 50  # threaded to repo INSERT
        assert out["anchor"] == {"kind": "series", "id": 7}

    def test_series_pin_replicate2_of_correct_series_201(self, monkeypatch):
        """Exact-replicate case: replicate-2's Observation of the anchored series."""
        _patch_series_exists(monkeypatch, True)
        _patch_kind(monkeypatch)
        captured: dict = {}
        _patch_create(monkeypatch, captured)
        # Observation 61 = replicate-2 reading, still resolves to series 7.
        _patch_observation_anchor(
            monkeypatch, {"channel_id": None, "analysis_series_id": 7}
        )
        data = AnnotationCreate(
            annotation_type="Fault", start_time=FROM, observation_id=61
        )
        out = svc.create_annotation_for_series(MagicMock(), 7, data)
        assert out["observation_id"] == 61
        assert captured["observation_id"] == 61

    def test_series_pin_missing_observation_422(self, monkeypatch):
        _patch_series_exists(monkeypatch, True)
        _patch_kind(monkeypatch)
        _patch_create(monkeypatch, {})
        _patch_observation_anchor(monkeypatch, None)  # observation does not exist
        data = AnnotationCreate(
            annotation_type="Fault", start_time=FROM, observation_id=999
        )
        with pytest.raises(HTTPException) as exc:
            svc.create_annotation_for_series(MagicMock(), 7, data)
        assert exc.value.status_code == 422

    # --- sensor arm (backfilled guard) ------------------------------------
    def test_channel_pin_from_different_channel_422(self, monkeypatch):
        _patch_channel_exists(monkeypatch, True)
        _patch_kind(monkeypatch)
        _patch_create(monkeypatch, {})
        # Observation 70 belongs to channel 99, but we anchor to channel 42.
        _patch_observation_anchor(
            monkeypatch, {"channel_id": 99, "analysis_series_id": None}
        )
        data = AnnotationCreate(
            annotation_type="Fault", start_time=FROM, observation_id=70
        )
        with pytest.raises(HTTPException) as exc:
            svc.create_annotation(MagicMock(), 42, data)
        assert exc.value.status_code == 422

    def test_channel_pin_matching_channel_201_persists_observation(self, monkeypatch):
        _patch_channel_exists(monkeypatch, True)
        _patch_kind(monkeypatch)
        captured: dict = {}
        _patch_create(monkeypatch, captured)
        _patch_observation_anchor(
            monkeypatch, {"channel_id": 42, "analysis_series_id": None}
        )
        data = AnnotationCreate(
            annotation_type="Fault", start_time=FROM, observation_id=70
        )
        out = svc.create_annotation(MagicMock(), 42, data)
        assert out["observation_id"] == 70
        assert captured["observation_id"] == 70
        assert out["anchor"] == {"kind": "channel", "id": 42}

    def test_no_pin_skips_guard_both_arms(self, monkeypatch):
        """Without observation_id the guard must not be consulted (no lookup)."""
        _patch_series_exists(monkeypatch, True)
        _patch_channel_exists(monkeypatch, True)
        _patch_kind(monkeypatch)
        _patch_create(monkeypatch, {})

        def _boom(conn, oid):
            raise AssertionError("guard should not run without a pin")

        monkeypatch.setattr(
            svc.annotation_repository, "get_observation_anchor", _boom
        )
        data = AnnotationCreate(annotation_type="Fault", start_time=FROM)
        assert svc.create_annotation_for_series(MagicMock(), 7, data)["observation_id"] is None
        assert svc.create_annotation(MagicMock(), 42, data)["observation_id"] is None


class TestServiceRead:
    def test_get_for_series_builds_series_anchor(self, monkeypatch):
        _patch_series_exists(monkeypatch, True)
        monkeypatch.setattr(
            svc.annotation_repository,
            "get_annotations_for_series",
            lambda *a, **k: [repo._row_to_annotation(_series_row(7))],
        )
        out = svc.get_annotations_for_series(MagicMock(), 7, FROM, TO)
        assert out["analysis_series_id"] == 7
        assert out["count"] == 1
        assert out["annotations"][0]["anchor"] == {"kind": "series", "id": 7}

    def test_get_for_missing_series_404(self, monkeypatch):
        _patch_series_exists(monkeypatch, False)
        with pytest.raises(HTTPException) as exc:
            svc.get_annotations_for_series(MagicMock(), 999, FROM, TO)
        assert exc.value.status_code == 404
