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


def _channel_fields() -> list[dict]:
    """Channel form: YAML-derived columns plus the current port.

    F3 dropped the denormalised Channel.SignalInterfacePort_ID column (the port
    is now resolved from the active ChannelPortHistory row), but ChannelIn still
    accepts ``signal_interface_port_id`` as the channel's current port — writes
    route through ``channel_repository.set_channel_active_port``. The field is no
    longer in the YAML, so re-add it explicitly to keep the form↔schema contract.
    """
    fields = load_table("Channel").build_form_fields(exclude={"unit_id"})
    fields.append(
        {
            "name": "signal_interface_port_id",
            "type": "select",
            "required": False,
            "options_fn": "list_signal_interface_port_lookup",
        }
    )
    return fields


def _explicit(fields: list[dict]) -> Callable[[], list[dict]]:
    """For entities whose API request schema diverges too far from the YAML to
    derive (renamed date fields, anchor-derived ids, non-column list inputs).
    Field names are still verified against the request schema by the test."""
    return lambda: [dict(f) for f in fields]


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
    "laboratory": _yaml("Laboratory"),
    "person": _yaml("Person"),
    "annotation_kind": _yaml("AnnotationKind"),
    "unit": _yaml("Unit"),
    # DasCreateIn renames the kind FK; manufacturer/model/parent are persisted too.
    "das": _yaml(
        "DataAcquisitionSystem",
        overrides={
            "data_acquisition_system_kind_id": {
                "name": "das_kind_id",
                "options_fn": "list_das_kinds",
            }
        },
    ),
    # ChannelIn carries no unit (a channel's unit follows its parameter);
    # produced_by_step_id is included (manual link to a derived channel's step).
    "channel": _channel_fields,
    # --- explicit: API schema diverges from YAML too far to derive -----------
    # CampaignIn renames the YAML *DateTime columns to start_date/end_date.
    "campaign": _explicit(
        [
            {"name": "name", "type": "text", "required": True},
            {"name": "campaign_kind_id", "type": "select", "required": True},
            {"name": "site_id", "type": "select", "required": True},
            {"name": "description", "type": "textarea", "required": False},
            {"name": "start_date", "type": "date", "required": False},
            {"name": "end_date", "type": "date", "required": False},
            {"name": "responsible_person_id", "type": "select", "required": False},
        ]
    ),
    # SamplingLocationIn; site_id is a UI-only scope field added by the page.
    "sampling_location": _explicit(
        [
            {"name": "name", "type": "text", "required": True},
            {"name": "description", "type": "textarea", "required": False},
            {"name": "latitude", "type": "number", "required": False},
            {"name": "longitude", "type": "number", "required": False},
            {"name": "process_unit_id", "type": "select", "required": False},
        ]
    ),
    # AnnotationCreate minus observation_id (set server-side from the anchor;
    # the page collects the anchor via a UI-only channel_id field).
    "annotation": _explicit(
        [
            {"name": "annotation_type", "type": "text", "required": False},
            {"name": "start_time", "type": "datetime", "required": True},
            {"name": "end_time", "type": "datetime", "required": False},
            {"name": "title", "type": "text", "required": False},
            {"name": "comment", "type": "textarea", "required": False},
            {"name": "campaign_id", "type": "number", "required": False},
            {"name": "equipment_event_id", "type": "number", "required": False},
            {"name": "author_person_id", "type": "number", "required": False},
        ]
    ),
    # ControlLoopCreateRequest (the loop entity itself; port/application dialogs
    # on the page are separate workflow actions with their own schemas).
    "control_loop": _explicit(
        [
            {"name": "name", "type": "text", "required": True},
            {"name": "controller_kind_id", "type": "select", "required": True},
            {"name": "fallback_control_loop_id", "type": "number", "required": False},
            {"name": "algorithm_reference", "type": "text", "required": False},
            {"name": "description", "type": "textarea", "required": False},
        ]
    ),
    # LabPanelCreateRequest; series_ids is a non-column list driven by series_picker.
    "lab_panel": _explicit(
        [
            {"name": "name", "type": "text", "required": True},
            {"name": "description", "type": "textarea", "required": False},
            {"name": "created_by_person_id", "type": "select", "required": False},
            {"name": "default_sample_collection_kind_id", "type": "select", "required": False},
            {"name": "default_sample_equipment_id", "type": "select", "required": False},
            {"name": "series_ids", "type": "multiselect", "required": True},
        ]
    ),
    # --- need exclude: YAML has columns the API won't accept ----------------
    # ParameterIn = {parameter, description, envo_iri}; ValueKind_ID and the
    # QUDT IRI are populated at build time, not via the edit form.
    "parameter": _yaml(
        "Parameter", exclude={"qudt_quantity_kind_iri", "value_kind_id"}
    ),
    # ChannelIn carries no unit (a channel's unit follows its parameter); the
    # port is re-added by _channel_fields (dropped from YAML by F3).
    "channel": _channel_fields,
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
