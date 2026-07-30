"""An import is written whole or not at all.

Two halves: the transaction that holds the repositories' commits back to one,
and the request shape that lets measurements name samples the same request is
creating.
"""

from __future__ import annotations

import datetime as dt

import pytest

from api.database import transaction
from api.v1.schemas.ingestion import LabIngestRequest


class FakeConn:
    """Records what a repository-style caller did to it."""

    def __init__(self):
        self.commits = 0
        self.rollbacks = 0
        self.cursors = 0

    def cursor(self):
        self.cursors += 1
        return object()

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1


def test_the_repositories_own_commits_are_held_back_to_one():
    conn = FakeConn()
    with transaction(conn) as tx:
        tx.cursor()
        tx.commit()  # what insert_samples does
        tx.cursor()
        tx.commit()  # what insert_lab_experiment does
        assert conn.commits == 0
    assert conn.commits == 1
    assert conn.cursors == 2  # the real connection still does the work


def test_a_failure_part_way_through_rolls_the_whole_thing_back():
    conn = FakeConn()
    with pytest.raises(ValueError, match="halfway"):
        with transaction(conn) as tx:
            tx.commit()
            raise ValueError("halfway")
    assert conn.commits == 0
    assert conn.rollbacks == 1


# --- naming a sample the same request creates -------------------------------


def _measurement(**over) -> dict:
    return {
        "parameter_id": 1,
        "sampling_point_id": 2,
        "unit_id": 3,
        "series_name": "TSS @ Site 1",
        "value": 10.0,
        **over,
    }


def _request(**over) -> dict:
    return {
        "name": "Spring 2026",
        "experiment_datetime": dt.datetime(2026, 4, 1, 9),
        "samples": [{"sampling_point_id": 2, "sample_datetime_start": dt.datetime(2026, 4, 1, 8)}],
        "measurements": [_measurement(sample_index=0)],
        **over,
    }


def test_a_measurement_may_name_a_sample_the_request_is_creating():
    data = LabIngestRequest(**_request())
    assert data.measurements[0].sample_index == 0
    assert data.measurements[0].sample_id is None


def test_a_measurement_may_still_name_a_sample_already_on_record():
    data = LabIngestRequest(**_request(samples=[], measurements=[_measurement(sample_id=77)]))
    assert data.measurements[0].sample_id == 77


@pytest.mark.parametrize(
    "measurement",
    [
        _measurement(),  # neither
        _measurement(sample_id=77, sample_index=0),  # both
    ],
)
def test_a_measurement_names_its_sample_exactly_one_way(measurement):
    with pytest.raises(ValueError, match="exactly one of sample_id or sample_index"):
        LabIngestRequest(**_request(measurements=[measurement]))


def test_an_index_past_the_end_of_the_samples_is_refused():
    with pytest.raises(ValueError, match="outside this request's 1 sample"):
        LabIngestRequest(**_request(measurements=[_measurement(sample_index=3)]))
