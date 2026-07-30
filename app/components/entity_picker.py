"""Pick the entity a source text means, or create it without leaving the page.

Names resolve exactly, so a value the database does not hold stops an import
dead. This is the way out, offered where the problem appeared: search the rows
on record, or create the missing one with the same form its own CRUD page uses.

A close name is shown as a hint and never selected for the user — accepting a
guess is their decision, which is the whole point of asking.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable

import streamlit as st

from app import api_client as api
from app.components.crud_form import render_form_field, validate_required_fields
from app.components.form_specs import get_form_fields
from app.components.generic_crud import _resolve_fk_options
from app.components.measurement_builder import label_key, suggest
from app.components.schema_registry import load_table

CHOOSE = "— choose —"

#: fk_table -> (form slug, api_client create function, the form's name field).
#: Neither the form's shape nor the create signature is uniform across entities,
#: so this cannot be derived. A table absent from here is still pickable, just
#: not creatable — Person, whose name is two fields, is deliberately absent.
_FORM_ENTITY = {
    "SamplingPoint": ("sampling_location", "create_sampling_location", "name"),
    "Parameter": ("parameter", "create_parameter", "parameter"),
    "Unit": ("unit", "create_unit", "unit"),
    "Laboratory": ("laboratory", "create_laboratory", "name"),
    "SampleKind": ("sample_kind", "create_sample_kind", "name"),
    "SampleMaterialKind": ("sample_material_kind", "create_sample_material_kind", "name"),
    "SampleCollectionKind": (
        "sample_collection_kind",
        "create_sample_collection_kind",
        "name",
    ),
    "Equipment": ("equipment", "create_equipment", "identifier"),
    "Campaign": ("campaign", "create_campaign", "name"),
    "Procedures": ("procedure", "create_procedure", "procedure_name"),
    "QualityCode": ("quality_code", "create_quality_code", "name"),
    "DataAcquisitionSystem": ("das", "create_das", "name"),
    "SignalInterface": ("signal_interface", "create_signal_interface", "name"),
}

#: Entities that belong to a parent the form deliberately leaves to the page.
_NEEDS_PARENT = {"SamplingPoint", "SignalInterface"}

#: Only one create form is open at a time: the forms are built from field names,
#: so two of the same entity's forms on one page would collide on widget id.
_OPEN = "entity_picker::open"

LookupFn = Callable[[str], list[dict]]


def can_create_from_name(fk_table: str) -> bool:
    """Whether a row of this table can be made from its name alone."""
    entry = _FORM_ENTITY.get(fk_table)
    if entry is None or fk_table in _NEEDS_PARENT:
        return False
    slug, _, name_field = entry
    return not [
        f for f in get_form_fields(slug) if f.get("required") and f["name"] != name_field
    ]


def create_from_name(fk_table: str, name: str, lookup: LookupFn) -> int:
    """Create one row of a name-only entity and return its id."""
    _, create_fn, name_field = _FORM_ENTITY[fk_table]
    getattr(api, create_fn)({name_field: name})
    api.clear_lookup_caches()
    return _id_of(lookup, fk_table, name)


def entity_picker(
    key: str,
    *,
    fk_table: str,
    lookup: LookupFn,
    text: str | None = None,
    label: str = "",
    allow_create: bool = True,
) -> tuple[int, str] | None:
    """Pick the entity for one source text. ``(id, name)`` once decided, else None."""
    pool = lookup(fk_table)
    name_key = label_key(fk_table)
    names = sorted(str(c[name_key]) for c in pool if c.get(name_key))
    hint = suggest(pool, name_key, text) if text else None

    picked = st.selectbox(
        label or f"Which {fk_table}?",
        options=[CHOOSE, *names],
        key=f"{key}::pick",
        help="Names must match exactly, so say which row this value means."
        + (f" '{hint}' is the closest one on record." if hint else ""),
    )
    if hint:
        st.caption(f"Closest on record: **{hint}** — accept it above only if it is the same thing.")

    if allow_create and fk_table in _FORM_ENTITY:
        creating = st.session_state.get(_OPEN) == key
        if st.button(
            "▲ Close the create form"
            if creating
            else (f'➕ Create "{text}"' if text else f"➕ Create a {fk_table}"),
            key=f"{key}::toggle",
        ):
            st.session_state[_OPEN] = None if creating else key
            st.rerun()
        if st.session_state.get(_OPEN) == key:
            made = _create_form(key, fk_table=fk_table, text=text, lookup=lookup)
            if made is not None:
                st.session_state[_OPEN] = None
                return made

    if picked != CHOOSE:
        return _id_of(lookup, fk_table, picked), picked
    return None


def _payload(data: dict) -> dict:
    """What the form actually sends: an untouched optional field is not sent.

    A blank text box reads as ``""``, which an optional integer or date column
    refuses; leaving the key out lets the server apply its own default.
    """
    return {
        k: v.isoformat() if isinstance(v, dt.date) else v
        for k, v in data.items()
        if v is not None and v != ""
    }


def _create_form(
    key: str, *, fk_table: str, text: str | None, lookup: LookupFn
) -> tuple[int, str] | None:
    """The entity's own CRUD form, inline, with its name prefilled from the sheet."""
    slug, create_fn, name_field = _FORM_ENTITY[fk_table]
    fields = _resolve_fk_options(get_form_fields(slug))
    with st.container(border=True):
        st.caption(f"New {fk_table}, on the same form its own page uses.")
        parent_id = _parent_input(key, fk_table)
        data = {
            f["name"]: render_form_field(
                f["name"],
                f.get("type", "text"),
                value=text if f["name"] == name_field else None,
                required=bool(f.get("required")),
                options=f.get("options"),
                help_text=f.get("help"),
            )
            for f in fields
        }
        if not st.button("Create", key=f"{key}::create", type="primary"):
            return None
        required = list(
            dict.fromkeys([f["name"] for f in fields if f.get("required")] + [name_field])
        )
        problems = validate_required_fields(data, required)
        if fk_table in _NEEDS_PARENT and parent_id is None:
            problems.append(f"a {fk_table} needs a parent — create one first")
        if problems:
            st.error(" · ".join(problems))
            return None
        try:
            payload = _payload(data)
            args = (parent_id, payload) if fk_table in _NEEDS_PARENT else (payload,)
            getattr(api, create_fn)(*args)
        except Exception as exc:
            st.error(f"Could not create it: {exc}")
            return None
        api.clear_lookup_caches()  # the lookups are cached; a new row is invisible otherwise
        name = str(data[name_field])
        return _id_of(lookup, fk_table, name), name


def _parent_input(key: str, fk_table: str) -> int | None:
    """The parent a nested entity needs, which its own form leaves to the page."""
    if fk_table == "SamplingPoint":
        sites = {str(s["name"]): s["site_id"] for s in api.list_sites_lookup()}
        return sites.get(
            st.selectbox(
                "Site *",
                options=list(sites),
                key=f"{key}::site",
                help="The site this sampling point belongs to — a sampling point "
                "cannot exist outside one.",
            )
        )
    if fk_table == "SignalInterface":
        systems = {
            str(d["name"]): d["data_acquisition_system_id"] for d in api.list_das_lookup()
        }
        return systems.get(
            st.selectbox(
                "Data acquisition system *",
                options=list(systems),
                key=f"{key}::das",
                help="The system this interface is wired to.",
            )
        )
    return None


def _id_of(lookup: LookupFn, fk_table: str, name: str) -> int:
    """One name's id, read back from the lookup — after a create as well.

    ponytail: a round trip rather than trusting the create response's shape,
    which differs per endpoint. Read the id off the response instead if this
    ever shows up in a profile.
    """
    key = label_key(fk_table)
    pk = load_table(fk_table).pk_field
    for row in lookup(fk_table):
        if str(row.get(key)) == name:
            return row[pk]
    raise KeyError(f"{name!r} is not in the {fk_table} lookup")
