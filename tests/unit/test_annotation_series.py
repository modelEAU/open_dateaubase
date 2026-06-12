"""Unit tests for the Stream-anchored annotation repository + service (Slice 13).

No database — the pyodbc connection/cursor are MagicMocks. After the Stream
refactor every annotation anchors to a single ``Stream_ID`` (a sensor Channel
and a lab AnalysisSeries both *are* a Stream — they share Stream_ID as their PK),
replacing the former ``Channel_ID`` / ``AnalysisSeries_ID`` XOR. We assert that:

Repository:
  - create_annotation writes a single Stream_ID (no XOR branch).
  - get_annotations_for_stream filters on Stream_ID and carries stream_id
    through _row_to_annotation; StreamKind_ID rides along to label the anchor.
  - get_observation_anchor resolves an Observation to one Stream_ID.
  - the /recent and /by-type feeds UNION a Channel-enriched half and an
    AnalysisSeries-enriched half, both filtering on Stream_ID and differing only
    by which enrichment table they join — both a sensor and a lab stream surface.

Service:
  - the anchor kind ("channel" vs "series") is derived from StreamKind_ID, and
    the anchor id is the Stream_ID.
  - the pin guard compares the Observation's Stream_ID against the anchor's.
  - create/read for both a sensor stream and a lab stream run the identical code
    path (that parity is the whole point of the refactor).
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from api.v1.repositories import annotation_repository as repo
from api.v1.services import annotation_service as svc
from api.v1.schemas.annotations import AnnotationCreate, AnnotationUpdate


FROM = datetime(2026, 1, 1, tzinfo=timezone.utc)
TO = datetime(2026, 2, 1, tzinfo=timezone.utc)

# StreamKind discriminator seed ids: Sensor=Channel, Lab=AnalysisSeries.
SENSOR = 1
LAB = 2


def _conn_returning(rows: list):
    conn = MagicMock()
    cursor = MagicMock()
    cursor.fetchall.return_value = rows
    conn.cursor.return_value = cursor
    return conn, cursor


def _sql(cursor) -> str:
    return "\n".join(c.args[0] for c in cursor.execute.call_args_list)


# A full _ANNOTATION_SELECT row (18 columns); index 1 = Stream_ID,
# index 16 = StreamKind_ID, index 17 = Observation_ID.
def _stream_row(stream_id: int = 7, stream_kind_id: int = LAB, observation_id=None):
    return (
        1,               # Annotation_ID
        stream_id,       # Stream_ID
        3,               # AnnotationKind_ID
        "Fault",         # Name
        "#FF0000",       # Color
        FROM,            # StartTime
        TO,              # EndTime
        "title",         # Title
        "comment",       # Comment
        None,            # AuthorPerson_ID
        None,            # AuthorName
        None,            # Campaign_ID
        None,            # CampaignName
        None,            # EquipmentEvent_ID
        FROM,            # CreatedDateTime
        None,            # ModifiedDateTime
        stream_kind_id,  # StreamKind_ID
        observation_id,  # Observation_ID
    )


# ---------------------------------------------------------------------------
# Repository — create
# ---------------------------------------------------------------------------


class TestRepositoryCreate:
    def test_create_writes_single_stream_id(self):
        conn, cursor = _conn_returning([])
        cursor.fetchone.return_value = (42, FROM)
        out = repo.create_annotation(
            conn,
            stream_id=7,
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
        # The INSERT writes Stream_ID and no longer the XOR pair.
        assert "[Stream_ID]" in sql
        assert "[Channel_ID]" not in sql
        assert "[AnalysisSeries_ID]" not in sql
        # Stream_ID is the first bound param of the INSERT.
        assert cursor.execute.call_args_list[0].args[1] == 7
        assert out["annotation_id"] == 42

    def test_create_sensor_and_lab_streams_use_same_insert(self):
        """A sensor stream and a lab stream insert through identical code — the
        only difference is the Stream_ID value (no anchor branching remains)."""
        for stream_id in (42, 7):  # 42 ~ a sensor stream, 7 ~ a lab stream
            conn, cursor = _conn_returning([])
            cursor.fetchone.return_value = (99, FROM)
            repo.create_annotation(
                conn,
                stream_id=stream_id,
                annotation_kind_id=3,
                start_time=FROM,
                end_time=None,
                author_person_id=None,
                campaign_id=None,
                equipment_event_id=None,
                title=None,
                comment=None,
            )
            assert cursor.execute.call_args_list[0].args[1] == stream_id

    def test_create_threads_observation_id_pin(self):
        conn, cursor = _conn_returning([])
        cursor.fetchone.return_value = (42, FROM)
        repo.create_annotation(
            conn,
            stream_id=7,
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
    def test_resolves_lab_observation_to_stream_id(self):
        # Lab path through LabAnalysis: COALESCE yields the AnalysisSeries Stream_ID.
        conn, cursor = _conn_returning([])
        cursor.fetchone.return_value = (7,)
        out = repo.get_observation_anchor(conn, 50)
        sql = _sql(cursor)
        assert "[LabAnalysis]" in sql
        assert "[AnalysisSeries_ID]" in sql  # column NAME persists on LabAnalysis
        assert out == 7

    def test_resolves_sensor_observation_to_stream_id(self):
        conn, cursor = _conn_returning([])
        cursor.fetchone.return_value = (42,)
        out = repo.get_observation_anchor(conn, 70)
        assert out == 42

    def test_missing_observation_returns_none(self):
        conn, cursor = _conn_returning([])
        cursor.fetchone.return_value = None
        assert repo.get_observation_anchor(conn, 999) is None


class TestRepositoryRead:
    def test_get_for_stream_filters_on_stream_id(self):
        conn, cursor = _conn_returning([_stream_row(7, LAB)])
        rows = repo.get_annotations_for_stream(conn, 7, FROM, TO)
        sql = _sql(cursor)
        assert "a.[Stream_ID] = ?" in sql
        assert "a.[Channel_ID] = ?" not in sql
        assert "a.[AnalysisSeries_ID] = ?" not in sql
        assert cursor.execute.call_args_list[0].args[1] == 7
        assert rows[0]["stream_id"] == 7

    def test_get_for_stream_serves_sensor_and_lab_identically(self):
        """Same function, same SQL shape, for a sensor stream and a lab stream."""
        for stream_id, kind in ((42, SENSOR), (7, LAB)):
            conn, cursor = _conn_returning([_stream_row(stream_id, kind)])
            rows = repo.get_annotations_for_stream(conn, stream_id, FROM, TO)
            assert cursor.execute.call_args_list[0].args[1] == stream_id
            assert rows[0]["stream_id"] == stream_id
            assert rows[0]["stream_kind_id"] == kind


# ---------------------------------------------------------------------------
# Service — anchor derivation, create, read
# ---------------------------------------------------------------------------


def _patch_series_exists(monkeypatch, exists: bool = True):
    monkeypatch.setattr(
        svc.ingestion_repository,
        "get_analysis_series_by_id",
        lambda conn, sid: ({"analysis_series_id": sid} if exists else None),
    )


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


def _patch_observation_anchor(monkeypatch, stream_id: int | None):
    monkeypatch.setattr(
        svc.annotation_repository,
        "get_observation_anchor",
        lambda conn, oid: stream_id,
    )


class TestServiceAnchorFromStreamKind:
    """_build_annotation_response labels the anchor from StreamKind_ID, and the
    anchor id is the Stream_ID (which is also the channel/series id)."""

    def test_lab_stream_row_builds_series_anchor(self):
        out = svc._build_annotation_response(repo._row_to_annotation(_stream_row(7, LAB)))
        assert out["anchor"] == {"kind": "series", "id": 7}

    def test_sensor_stream_row_builds_channel_anchor(self):
        out = svc._build_annotation_response(
            repo._row_to_annotation(_stream_row(42, SENSOR))
        )
        assert out["anchor"] == {"kind": "channel", "id": 42}


class TestServiceCreate:
    def test_create_for_series_returns_series_anchor_and_stream_id(self, monkeypatch):
        _patch_series_exists(monkeypatch, True)
        _patch_kind(monkeypatch)
        captured: dict = {}
        _patch_create(monkeypatch, captured)
        data = AnnotationCreate(annotation_type="Fault", start_time=FROM, end_time=TO)
        out = svc.create_annotation_for_series(MagicMock(), 7, data)
        assert out["anchor"] == {"kind": "series", "id": 7}
        assert out["annotation_id"] == 99
        # the series id is threaded to the repo as the single Stream_ID anchor.
        assert captured["stream_id"] == 7

    def test_create_for_channel_returns_channel_anchor_and_stream_id(self, monkeypatch):
        _patch_channel_exists(monkeypatch, True)
        _patch_kind(monkeypatch)
        captured: dict = {}
        _patch_create(monkeypatch, captured)
        data = AnnotationCreate(annotation_type="Fault", start_time=FROM, end_time=TO)
        out = svc.create_annotation(MagicMock(), 42, data)
        assert out["anchor"] == {"kind": "channel", "id": 42}
        # the channel id is threaded to the repo as the single Stream_ID anchor.
        assert captured["stream_id"] == 42

    def test_create_for_missing_series_404(self, monkeypatch):
        _patch_series_exists(monkeypatch, False)
        data = AnnotationCreate(annotation_type="Fault", start_time=FROM)
        with pytest.raises(HTTPException) as exc:
            svc.create_annotation_for_series(MagicMock(), 999, data)
        assert exc.value.status_code == 404


class TestPinIntegrityGuard:
    """The pin guard compares the Observation's Stream_ID against the anchor's
    Stream_ID. A pin from a different stream is rejected 422 on BOTH arms; a
    matching pin persists Observation_ID."""

    # --- lab arm -----------------------------------------------------------
    def test_series_pin_from_different_stream_422(self, monkeypatch):
        _patch_series_exists(monkeypatch, True)
        _patch_kind(monkeypatch)
        _patch_create(monkeypatch, {})
        # Observation 50 resolves to stream 8, but we anchor to stream 7.
        _patch_observation_anchor(monkeypatch, 8)
        data = AnnotationCreate(
            annotation_type="Fault", start_time=FROM, observation_id=50
        )
        with pytest.raises(HTTPException) as exc:
            svc.create_annotation_for_series(MagicMock(), 7, data)
        assert exc.value.status_code == 422

    def test_series_pin_matching_stream_persists_observation(self, monkeypatch):
        _patch_series_exists(monkeypatch, True)
        _patch_kind(monkeypatch)
        captured: dict = {}
        _patch_create(monkeypatch, captured)
        _patch_observation_anchor(monkeypatch, 7)
        data = AnnotationCreate(
            annotation_type="Fault", start_time=FROM, observation_id=50
        )
        out = svc.create_annotation_for_series(MagicMock(), 7, data)
        assert out["observation_id"] == 50
        assert captured["observation_id"] == 50  # threaded to repo INSERT
        assert out["anchor"] == {"kind": "series", "id": 7}

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

    # --- sensor arm --------------------------------------------------------
    def test_channel_pin_from_different_stream_422(self, monkeypatch):
        _patch_channel_exists(monkeypatch, True)
        _patch_kind(monkeypatch)
        _patch_create(monkeypatch, {})
        # Observation 70 resolves to stream 99, but we anchor to stream 42.
        _patch_observation_anchor(monkeypatch, 99)
        data = AnnotationCreate(
            annotation_type="Fault", start_time=FROM, observation_id=70
        )
        with pytest.raises(HTTPException) as exc:
            svc.create_annotation(MagicMock(), 42, data)
        assert exc.value.status_code == 422

    def test_channel_pin_matching_stream_persists_observation(self, monkeypatch):
        _patch_channel_exists(monkeypatch, True)
        _patch_kind(monkeypatch)
        captured: dict = {}
        _patch_create(monkeypatch, captured)
        _patch_observation_anchor(monkeypatch, 42)
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

        monkeypatch.setattr(svc.annotation_repository, "get_observation_anchor", _boom)
        data = AnnotationCreate(annotation_type="Fault", start_time=FROM)
        assert (
            svc.create_annotation_for_series(MagicMock(), 7, data)["observation_id"]
            is None
        )
        assert svc.create_annotation(MagicMock(), 42, data)["observation_id"] is None


class TestServiceRead:
    def test_get_for_series_builds_series_anchor(self, monkeypatch):
        _patch_series_exists(monkeypatch, True)
        monkeypatch.setattr(
            svc.annotation_repository,
            "get_annotations_for_stream",
            lambda *a, **k: [repo._row_to_annotation(_stream_row(7, LAB))],
        )
        out = svc.get_annotations_for_series(MagicMock(), 7, FROM, TO)
        assert out["analysis_series_id"] == 7
        assert out["count"] == 1
        assert out["annotations"][0]["anchor"] == {"kind": "series", "id": 7}

    def test_get_for_channel_builds_channel_anchor(self, monkeypatch):
        _patch_channel_exists(monkeypatch, True)
        monkeypatch.setattr(
            svc.annotation_repository,
            "get_annotations_for_stream",
            lambda *a, **k: [repo._row_to_annotation(_stream_row(42, SENSOR))],
        )
        out = svc.get_annotations_for_timeseries(MagicMock(), 42, FROM, TO)
        assert out["channel_id"] == 42
        assert out["count"] == 1
        assert out["annotations"][0]["anchor"] == {"kind": "channel", "id": 42}

    def test_get_for_missing_series_404(self, monkeypatch):
        _patch_series_exists(monkeypatch, False)
        with pytest.raises(HTTPException) as exc:
            svc.get_annotations_for_series(MagicMock(), 999, FROM, TO)
        assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# Edit / delete — keyed on annotation_id, anchor-agnostic. Pin that a
# Stream-anchored row survives the read/update/delete paths intact, and that
# the shared read SELECT does not inner-join a subtype table (which would drop
# the other subtype's rows).
# ---------------------------------------------------------------------------


class TestRepositoryGetByIdStreamSafe:
    def test_get_by_id_returns_stream_anchored_row(self):
        conn, cursor = _conn_returning([])
        cursor.fetchone.return_value = _stream_row(7, LAB)
        out = repo.get_annotation_by_id(conn, 1)
        assert out is not None
        assert out["stream_id"] == 7
        assert out["stream_kind_id"] == LAB

    def test_get_by_id_select_does_not_inner_join_a_subtype(self):
        """Regression: the shared read SELECT must not inner-join Channel or
        AnalysisSeries — either would drop the rows of the other subtype. It
        joins only Stream (the supertype every annotation has)."""
        conn, cursor = _conn_returning([])
        cursor.fetchone.return_value = _stream_row(7, LAB)
        repo.get_annotation_by_id(conn, 1)
        sql = _sql(cursor)
        assert "JOIN [dbo].[Channel]" not in sql
        assert "JOIN [dbo].[AnalysisSeries]" not in sql
        assert "JOIN [dbo].[Stream]" in sql


class TestRepositoryUpdateStreamSafe:
    def test_update_returns_via_stream_safe_select(self):
        conn, cursor = _conn_returning([])
        # First execute = UPDATE (fetchone unused), second = get_annotation_by_id.
        cursor.fetchone.return_value = _stream_row(7, LAB)
        out = repo.update_annotation(
            conn,
            1,
            annotation_kind_id=None,
            start_time=None,
            end_time=None,
            title=None,
            comment="edited",
        )
        sql = _sql(cursor)
        assert "JOIN [dbo].[Channel]" not in sql
        assert "JOIN [dbo].[AnalysisSeries]" not in sql
        assert out is not None
        assert out["stream_id"] == 7


class TestServiceUpdateDelete:
    def _patch_get_by_id(self, monkeypatch, row: dict | None):
        monkeypatch.setattr(
            svc.annotation_repository,
            "get_annotation_by_id",
            lambda conn, aid: row,
        )

    def test_update_preserves_series_anchor(self, monkeypatch):
        existing = repo._row_to_annotation(_stream_row(7, LAB))
        self._patch_get_by_id(monkeypatch, existing)
        monkeypatch.setattr(
            svc.annotation_repository,
            "update_annotation",
            lambda conn, aid, **kw: repo._row_to_annotation(_stream_row(7, LAB)),
        )
        data = AnnotationUpdate(comment="edited")
        out = svc.update_annotation(MagicMock(), 1, data)
        assert out["anchor"] == {"kind": "series", "id": 7}

    def test_update_missing_annotation_404(self, monkeypatch):
        self._patch_get_by_id(monkeypatch, None)
        with pytest.raises(HTTPException) as exc:
            svc.update_annotation(MagicMock(), 999, AnnotationUpdate(comment="x"))
        assert exc.value.status_code == 404

    def test_delete_stream_anchored_annotation(self, monkeypatch):
        existing = repo._row_to_annotation(_stream_row(7, LAB))
        self._patch_get_by_id(monkeypatch, existing)
        deleted: dict = {}
        monkeypatch.setattr(
            svc.annotation_repository,
            "delete_annotation",
            lambda conn, aid: deleted.update({"id": aid}) or True,
        )
        svc.delete_annotation(MagicMock(), 1)
        assert deleted["id"] == 1

    def test_delete_missing_annotation_404(self, monkeypatch):
        self._patch_get_by_id(monkeypatch, None)
        with pytest.raises(HTTPException) as exc:
            svc.delete_annotation(MagicMock(), 999)
        assert exc.value.status_code == 404


# ---------------------------------------------------------------------------
# Cross-stream feeds (/recent, /by-type)
#
# get_recent_annotations / get_annotations_by_kind UNION a Channel-enriched half
# with an AnalysisSeries-enriched half. Both halves now filter on the single
# Stream_ID (the sensor half joins Channel ON Stream_ID, which restricts it to
# sensor streams; the lab half joins AnalysisSeries ON Stream_ID, restricting it
# to lab streams). The lab half derives location from SamplingPoint and variable
# from Parameter. A sensor stream and a lab stream both surface.
# ---------------------------------------------------------------------------


def _feed_row(
    annotation_id: int,
    *,
    stream_id,
    stream_kind_id,
    location=None,
    parameter=None,
    created=FROM,
    start=FROM,
):
    """A 20-column feed row: 18 _row_to_annotation cols + LocationName + ParameterName."""
    return (
        annotation_id,    # Annotation_ID
        stream_id,        # Stream_ID
        3,                # AnnotationKind_ID
        "Fault",          # Name
        "#FF0000",        # Color
        start,            # StartTime
        TO,               # EndTime
        "title",          # Title
        "comment",        # Comment
        None,             # AuthorPerson_ID
        None,             # AuthorName
        None,             # Campaign_ID
        None,             # CampaignName
        None,             # EquipmentEvent_ID
        created,          # CreatedDateTime
        None,             # ModifiedDateTime
        stream_kind_id,   # StreamKind_ID
        None,             # Observation_ID
        location,         # LocationName
        parameter,        # ParameterName
    )


class TestRecentAnnotationsUnion:
    def test_sql_unions_sensor_and_lab_halves_on_stream_id(self):
        conn, cursor = _conn_returning([])
        repo.get_recent_annotations(conn, limit=20)
        sql = _sql(cursor)
        # Both halves anchor on Stream_ID; the two halves differ only by which
        # enrichment subtype they join (Channel vs AnalysisSeries).
        assert "UNION ALL" in sql
        assert "[dbo].[Channel]" in sql
        assert "[dbo].[AnalysisSeries]" in sql
        assert "s.[Stream_ID] = a.[Stream_ID]" in sql
        # The retired XOR NOT-NULL filters are gone.
        assert "a.[Channel_ID] IS NOT NULL" not in sql
        assert "a.[AnalysisSeries_ID] IS NOT NULL" not in sql

    def test_sensor_and_lab_rows_surface_with_location_and_variable(self):
        conn, cursor = _conn_returning(
            [
                _feed_row(1, stream_id=42, stream_kind_id=SENSOR, parameter="TSS"),
                _feed_row(
                    2,
                    stream_id=7,
                    stream_kind_id=LAB,
                    location="Effluent",
                    parameter="COD",
                ),
            ]
        )
        rows = repo.get_recent_annotations(conn, limit=20)
        sensor = next(r for r in rows if r["stream_id"] == 42)
        lab = next(r for r in rows if r["stream_id"] == 7)
        assert sensor["stream_kind_id"] == SENSOR
        assert sensor["parameter_name"] == "TSS"
        assert lab["stream_kind_id"] == LAB
        assert lab["location_name"] == "Effluent"
        assert lab["parameter_name"] == "COD"

    def test_limit_applies_to_combined_set(self):
        conn, cursor = _conn_returning([])
        repo.get_recent_annotations(conn, limit=5)
        sql = _sql(cursor)
        # TOP wraps the UNION (outer select), so the limit spans both halves.
        assert "TOP (?)" in sql
        assert sql.index("TOP (?)") < sql.index("UNION ALL")
        assert cursor.execute.call_args_list[0].args[1] == 5  # limit bound first


class TestByKindAnnotationsUnion:
    def test_sql_unions_sensor_and_lab_halves(self):
        conn, cursor = _conn_returning([])
        repo.get_annotations_by_kind(conn, 3, FROM, TO)
        sql = _sql(cursor)
        assert "UNION ALL" in sql
        assert "[dbo].[Channel]" in sql
        assert "[dbo].[AnalysisSeries]" in sql
        # kind + time-range filter on BOTH halves => AnnotationKind_ID bound twice.
        bound = cursor.execute.call_args_list[0].args[1:]
        assert bound.count(3) == 2  # kind id repeated per half

    def test_sensor_and_lab_rows_surface(self):
        conn, cursor = _conn_returning(
            [
                _feed_row(1, stream_id=42, stream_kind_id=SENSOR, parameter="TSS"),
                _feed_row(
                    2,
                    stream_id=7,
                    stream_kind_id=LAB,
                    location="Effluent",
                    parameter="COD",
                ),
            ]
        )
        rows = repo.get_annotations_by_kind(conn, 3, FROM, TO)
        lab = next(r for r in rows if r["stream_id"] == 7)
        assert lab["stream_kind_id"] == LAB
        assert lab["location_name"] == "Effluent"
        assert lab["parameter_name"] == "COD"


class TestServiceFeedsSurfaceBothStreams:
    """The service maps both halves onto the generic location/variable fields and
    builds the correct anchor per row (channel vs series) from StreamKind_ID."""

    def test_recent_includes_channel_and_series_anchored_rows(self, monkeypatch):
        monkeypatch.setattr(
            svc.annotation_repository,
            "get_recent_annotations",
            lambda conn, limit, kind_id: [
                repo._feed_row(
                    _feed_row(1, stream_id=42, stream_kind_id=SENSOR, parameter="TSS")
                ),
                repo._feed_row(
                    _feed_row(
                        2,
                        stream_id=7,
                        stream_kind_id=LAB,
                        location="Effluent",
                        parameter="COD",
                    )
                ),
            ],
        )
        out = svc.get_recent_annotations(MagicMock(), limit=20)
        anchors = {a["anchor"]["kind"] for a in out["annotations"]}
        assert anchors == {"channel", "series"}
        lab = next(
            a for a in out["annotations"] if a["anchor"] == {"kind": "series", "id": 7}
        )
        assert lab["location"] == "Effluent"
        assert lab["variable"] == "COD"

    def test_by_type_includes_series_anchored_row(self, monkeypatch):
        monkeypatch.setattr(
            svc.annotation_repository,
            "get_annotation_kind_by_name",
            lambda conn, name: {"annotation_kind_id": 3},
        )
        monkeypatch.setattr(
            svc.annotation_repository,
            "get_annotations_by_kind",
            lambda conn, kind_id, f, t: [
                repo._feed_row(
                    _feed_row(
                        2,
                        stream_id=7,
                        stream_kind_id=LAB,
                        location="Effluent",
                        parameter="COD",
                    )
                ),
            ],
        )
        out = svc.get_annotations_by_kind(MagicMock(), "Fault", FROM, TO)
        ann = out["annotations"][0]
        assert ann["anchor"] == {"kind": "series", "id": 7}
        assert ann["location"] == "Effluent"
        assert ann["variable"] == "COD"


class TestAnnotationUpdateSchema:
    def test_update_has_no_observation_id_field(self):
        """Pin-mutation is deliberately out of scope: AnnotationUpdate must NOT
        expose observation_id (changing the pin would require re-running
        _assert_pin_in_anchor against the stored anchor)."""
        assert "observation_id" not in AnnotationUpdate.model_fields
