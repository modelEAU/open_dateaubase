"""Entity resolver: text → existing DB ID with fuzzy suggestion."""
from __future__ import annotations

from difflib import get_close_matches
from typing import Any


def _best_match(query: str, candidates: list[dict], name_key: str, id_key: str) -> dict | None:
    """Return the best fuzzy match dict or None."""
    names = [c[name_key] for c in candidates if c.get(name_key)]
    matches = get_close_matches(query, names, n=1, cutoff=0.6)
    if not matches:
        return None
    return next(c for c in candidates if c.get(name_key) == matches[0])


class EntityResolver:
    """Resolves text labels to existing DB IDs. Call .resolve_*() for each cell.

    Parameters
    ----------
    units:
        List of unit dicts with keys ``unit_id``, ``name``, and optionally ``symbol``.
    parameters:
        List of parameter dicts with keys ``parameter_id`` and ``name``.
    sampling_points:
        List of sampling-point dicts with keys ``sampling_point_id`` and ``name``.
    """

    def __init__(
        self,
        units: list[dict],
        parameters: list[dict],
        sampling_points: list[dict],
    ) -> None:
        self._units = units
        self._parameters = parameters
        self._sps = sampling_points

    def resolve_unit(self, text: str) -> dict | None:
        """Match unit by symbol (exact, case-insensitive) then by name (fuzzy)."""
        text_lower = text.strip().lower()
        for u in self._units:
            if (u.get("symbol") or "").lower() == text_lower:
                return u
        return _best_match(text, self._units, "name", "unit_id")

    def resolve_parameter(self, text: str) -> dict | None:
        """Match parameter by name (fuzzy)."""
        return _best_match(text, self._parameters, "name", "parameter_id")

    def resolve_sampling_point(self, text: str) -> dict | None:
        """Match sampling point by name (fuzzy)."""
        return _best_match(text, self._sps, "name", "sampling_point_id")
