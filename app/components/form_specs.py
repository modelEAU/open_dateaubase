"""Single source of truth for CRUD form fields, keyed by entity.

Every database-editing page should build its create/edit form from
``get_form_fields(entity)`` rather than an inline literal. The field set is
derived from the YAML schema dictionary via
:func:`schema_registry.TableMeta.build_form_fields`, with two knobs:

* ``exclude``   — drop columns the API's request schema (``*In``/``*Patch`` in
  ``api/v1/schemas/``) does NOT accept for editing (managed server-side, via a
  junction table, or at build time).
* ``overrides`` — rename a field to the API's name, or fix its ``options_fn``,
  where the YAML→snake name diverges from the hand-written request schema.

``tests/unit/test_form_coverage.py`` asserts, for every entity here, that the
resulting field names equal the endpoint's request-schema fields — so a form can
never silently drift from the contract it posts to. Pure data: this module must
not import ``streamlit`` or ``api`` (keeps the app↔api HTTP boundary intact and
lets the test import it cheaply).
"""

from __future__ import annotations

from typing import Callable

from app.components.schema_registry import load_table


def _yaml(
    table: str,
    *,
    exclude: set[str] = frozenset(),  # type: ignore[assignment]
    overrides: dict[str, dict] | None = None,
) -> Callable[[], list[dict]]:
    return lambda: load_table(table).build_form_fields(exclude=exclude, overrides=overrides)


# entity slug -> builder returning a form_fields list whose names match the
# corresponding api/v1/schemas request model (verified by test_form_coverage).
FORM_FIELD_BUILDERS: dict[str, Callable[[], list[dict]]] = {
    # --- name/description vocab (YAML already matches *In) -------------------
    "campaign_kind": _yaml("CampaignKind"),
    "equipment_event_kind": _yaml("EquipmentEventKind"),
    "process_unit_kind": _yaml("ProcessUnitKind"),
    "procedure_kind": _yaml("ProcedureKind"),
    "sample_kind": _yaml("SampleKind"),
    "sample_collection_kind": _yaml("SampleCollectionKind"),
    "site_kind": _yaml("SiteKind"),
    "quality_code": _yaml("QualityCode"),
    # --- richer tables, YAML matches *In as-is ------------------------------
    "procedure": _yaml("Procedures"),
    "process_unit": _yaml("ProcessUnit"),
    "equipment_model": _yaml("EquipmentModel"),
    "signal_interface": _yaml("SignalInterface"),
    # --- need exclude: YAML has columns the API won't accept ----------------
    # ParameterIn = {parameter, description, envo_iri}; ValueKind_ID and the
    # QUDT IRI are populated at build time, not via the edit form.
    "parameter": _yaml(
        "Parameter", exclude={"qudt_quantity_kind_iri", "value_kind_id"}
    ),
    # ChannelIn carries no unit (a channel's unit follows its parameter).
    "channel": _yaml("Channel", exclude={"unit_id"}),
    # --- need rename: API name diverges from YAML→snake ---------------------
    # EquipmentIn uses model_id; is_active/storage_location are managed via the
    # commission/decommission lifecycle endpoints, not the edit form.
    "equipment": _yaml(
        "Equipment",
        exclude={"is_active", "storage_location"},
        overrides={
            "equipment_model_id": {
                "name": "model_id",
                "options_fn": "list_equipment_models_lookup",
            }
        },
    ),
}


def get_form_fields(entity: str) -> list[dict]:
    """Return the form_fields list for an editable entity (see module docstring)."""
    return FORM_FIELD_BUILDERS[entity]()
