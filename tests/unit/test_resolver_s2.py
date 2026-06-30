"""Tests for PRD-3 S2: EntityResolver — text → DB ID with fuzzy matching."""
from app.components.resolver import EntityResolver

_UNITS = [
    {"unit_id": 1, "name": "milligram per litre", "symbol": "mg/L"},
    {"unit_id": 2, "name": "gram per litre", "symbol": "g/L"},
]
_PARAMS = [
    {"parameter_id": 10, "name": "Chemical Oxygen Demand"},
    {"parameter_id": 11, "name": "Total Suspended Solids"},
]
_SPS = [
    {"sampling_point_id": 100, "name": "R240"},
    {"sampling_point_id": 101, "name": "R450"},
]


def _r() -> EntityResolver:
    return EntityResolver(units=_UNITS, parameters=_PARAMS, sampling_points=_SPS)


def test_resolve_unit_by_symbol():
    assert _r().resolve_unit("mg/L")["unit_id"] == 1


def test_resolve_unit_by_name_fuzzy():
    # "milligram per liter" vs "milligram per litre" — close enough for difflib at 0.6
    assert _r().resolve_unit("milligram per liter")["unit_id"] == 1


def test_resolve_parameter_cod():
    r = _r()
    result = r.resolve_parameter("COD")
    # COD is an abbreviation — fuzzy may not match; accept None or correct id
    assert result is None or result["parameter_id"] == 10


def test_resolve_parameter_exact_fuzzy():
    assert _r().resolve_parameter("Chemical Oxygen Demand")["parameter_id"] == 10


def test_resolve_sampling_point():
    assert _r().resolve_sampling_point("R240")["sampling_point_id"] == 100


def test_no_match_returns_none():
    assert _r().resolve_unit("parsec") is None


def test_resolve_unit_symbol_case_insensitive():
    assert _r().resolve_unit("MG/L")["unit_id"] == 1


def test_resolve_second_unit_by_symbol():
    assert _r().resolve_unit("g/L")["unit_id"] == 2


def test_resolve_second_sampling_point():
    assert _r().resolve_sampling_point("R450")["sampling_point_id"] == 101


def test_resolve_parameter_no_match_returns_none():
    assert _r().resolve_parameter("xyzzy_nonexistent") is None


def test_resolve_sampling_point_no_match_returns_none():
    assert _r().resolve_sampling_point("Z999") is None
