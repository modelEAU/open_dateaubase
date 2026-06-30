"""Entity resolver: text → existing DB ID with fuzzy suggestion."""
from __future__ import annotations

import re
from difflib import get_close_matches
from typing import Any

# The exclusive-arc Event target levels, smallest logical unit first. Maps a
# level label to the EventIn FK field it sets.
TARGET_LEVELS: dict[str, str] = {
    "Equipment": "equipment_id",
    "SamplingPoint": "sampling_point_id",
    "ProcessUnit": "process_unit_id",
    "Site": "site_id",
    "Campaign": "campaign_id",
}

# Cheap, deterministic level hints (PRD-4 S2) for rows the resolver could not
# match to a known entity — a *suggestion* the user confirms, never an
# auto-commit. An equipment-style tag (e.g. "P-100", "LDO-241") looks like
# Equipment; a handful of keywords hint at site-wide / process-unit scope.
_EQUIPMENT_TAG = re.compile(r"\b[A-Za-z]{1,4}-?\d{2,}\b")
_LEVEL_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Site": ("outage", "power", "panne", "électr", "electr", "building", "bâtiment", "site-wide"),
    "ProcessUnit": ("plc", "automate", "scada", "ups", "onduleur"),
}


def guess_target_level(text: str) -> str | None:
    """Suggest a target *level* (not an entity) from cheap text heuristics.

    Used to pre-fill the level picker for rows with no entity match. Returns a
    key of :data:`TARGET_LEVELS` or None. Never resolves an entity on its own —
    the user still confirms which entity at that level.
    """
    raw = text or ""
    low = raw.lower()
    if not low.strip():
        return None
    if _EQUIPMENT_TAG.search(raw):
        return "Equipment"
    for level, keywords in _LEVEL_KEYWORDS.items():
        if any(k in low for k in keywords):
            return level
    return None


# Label keys a lookup dict may carry, most specific first. Used by target
# resolution, which is key-agnostic across the different target lookups.
_NAME_KEYS = ("identifier", "name", "label", "tag")


def _candidate_name(candidate: dict) -> str:
    """Return the first non-empty label a candidate lookup dict carries."""
    for key in _NAME_KEYS:
        val = candidate.get(key)
        if val:
            return str(val)
    return ""


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
        equipment: list[dict] | None = None,
        sites: list[dict] | None = None,
        process_units: list[dict] | None = None,
        campaigns: list[dict] | None = None,
        persons: list[dict] | None = None,
    ) -> None:
        self._units = units
        self._parameters = parameters
        self._sps = sampling_points
        # Event-target candidate pools (PRD-4 logbook profile). Optional so the
        # lab/sensor profiles construct the resolver unchanged.
        self._equipment = equipment or []
        self._sites = sites or []
        self._process_units = process_units or []
        self._campaigns = campaigns or []
        self._persons = persons or []

    def resolve_unit(self, text: str) -> dict | None:
        """Match unit by symbol (exact, case-insensitive) then by name (fuzzy)."""
        text_lower = text.strip().lower()
        for u in self._units:
            if (u.get("symbol") or "").lower() == text_lower:
                return u
        return _best_match(text, self._units, "name", "unit_id")

    def resolve_parameter(self, text: str) -> dict | None:
        """Match parameter by short_name (exact, case-insensitive) then by name (fuzzy)."""
        text_lower = text.strip().lower()
        for p in self._parameters:
            if (p.get("short_name") or "").lower() == text_lower:
                return p
        return _best_match(text, self._parameters, "name", "parameter_id")

    def resolve_sampling_point(self, text: str) -> dict | None:
        """Match sampling point by name (fuzzy)."""
        return _best_match(text, self._sps, "name", "sampling_point_id")

    def resolve_person(self, text: str) -> dict | None:
        """Match a person by their display label (fuzzy)."""
        return _best_match(text, self._persons, "label", "person_id")

    def resolve_target(self, text: str) -> dict | None:
        """Resolve free text to the *smallest* logical Event target it names.

        Scans the text for any candidate label as a substring, smallest level
        first (Equipment → SamplingPoint → ProcessUnit → Site → Campaign), and
        returns the first level that hits. Within a level the longest matching
        label wins (most specific). Returns a dict with ``arc_field`` (the
        EventIn FK to set), ``level``, ``entity_id``, ``label`` — or None.

        ponytail: substring containment, not word-boundary aware ("P-100"
        matches inside "P-1000"). S2 adds the disambiguation UX + tighter match.
        """
        haystack = (text or "").strip().lower()
        if not haystack:
            return None
        # (level label, candidate pool, EventIn arc-FK field, id key)
        levels = [
            ("Equipment", self._equipment, "equipment_id", "equipment_id"),
            ("SamplingPoint", self._sps, "sampling_point_id", "sampling_point_id"),
            ("ProcessUnit", self._process_units, "process_unit_id", "id"),
            ("Site", self._sites, "site_id", "site_id"),
            ("Campaign", self._campaigns, "campaign_id", "campaign_id"),
        ]
        for level, pool, arc_field, id_key in levels:
            hits = [
                c for c in pool
                if (name := _candidate_name(c)) and len(name) >= 2
                and name.lower() in haystack
            ]
            if hits:
                best = max(hits, key=lambda c: len(_candidate_name(c)))
                return {
                    "arc_field": arc_field,
                    "level": level,
                    "entity_id": best.get(id_key),
                    "label": _candidate_name(best),
                }
        return None
