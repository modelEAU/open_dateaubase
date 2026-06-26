"""Systematic catch for CRUD form field drift.

The bug this guards against: a Create/Edit form silently omits (or misnames) a
field that the API's request schema accepts, so a user can't set it — a latent
bug invisible unless you know the whole data model.

Source of truth = the FastAPI request schema (``*In``/``*Patch`` in
``api/v1/schemas/``), which is exactly what ``app.api_client`` posts. For every
editable entity in ``app.components.form_specs``, the fields the form builds must
equal that schema's fields. When the API contract gains a field, this test fails
until the form is updated.

Pages whose forms are NOT yet routed through ``form_specs`` are listed in
``PENDING_PAGES`` with a reason, and the meta-test asserts no page builds a form
outside that system without being registered.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.components.form_specs import FORM_FIELD_BUILDERS, get_form_fields
from app.components.schema_registry import load_table

# Request schemas (the contract the forms post to).
from api.v1.endpoints.annotations import AnnotationKindIn
from api.v1.endpoints.persons import PersonIn
from api.v1.schemas.annotations import AnnotationCreate
from api.v1.schemas.campaigns import CampaignIn
from api.v1.schemas.channel import ChannelIn, ParameterIn, UnitIn
from api.v1.schemas.control_loop import ControlLoopCreateRequest
from api.v1.schemas.equipment import EquipmentIn, EquipmentModelIn
from api.v1.schemas.ingestion import LabPanelCreateRequest
from api.v1.schemas.metadata import (
    CampaignKindIn,
    EquipmentEventKindIn,
    LaboratoryIn,
    ProcedureIn,
    ProcedureKindIn,
    ProcessUnitKindIn,
    QualityCodeIn,
    SampleCollectionKindIn,
    SamplingLocationIn,
    SampleKindIn,
    SiteKindIn,
)
from api.v1.schemas.process_unit import ProcessUnitIn
from api.v1.schemas.signal_interface import DasCreateIn, SignalInterfaceIn

# entity slug -> request schema whose fields the form must cover exactly.
ENTITY_SCHEMA = {
    "campaign_kind": CampaignKindIn,
    "equipment_event_kind": EquipmentEventKindIn,
    "process_unit_kind": ProcessUnitKindIn,
    "procedure_kind": ProcedureKindIn,
    "sample_kind": SampleKindIn,
    "sample_collection_kind": SampleCollectionKindIn,
    "site_kind": SiteKindIn,
    "quality_code": QualityCodeIn,
    "procedure": ProcedureIn,
    "process_unit": ProcessUnitIn,
    "equipment_model": EquipmentModelIn,
    "signal_interface": SignalInterfaceIn,
    "parameter": ParameterIn,
    "channel": ChannelIn,
    "equipment": EquipmentIn,
    "laboratory": LaboratoryIn,
    "person": PersonIn,
    "annotation_kind": AnnotationKindIn,
    "campaign": CampaignIn,
    "sampling_location": SamplingLocationIn,
    "annotation": AnnotationCreate,
    "control_loop": ControlLoopCreateRequest,
    "lab_panel": LabPanelCreateRequest,
    "unit": UnitIn,
    "das": DasCreateIn,
}

# Schema fields a form may legitimately omit, with the reason. These are set by
# the server or the page out-of-band rather than collected as a form field.
EXCEPTIONS: dict[str, dict[str, str]] = {
    "annotation": {"observation_id": "set server-side from the anchor (UI channel_id)"},
}


@pytest.mark.parametrize("entity", sorted(ENTITY_SCHEMA))
def test_form_fields_match_request_schema(entity: str) -> None:
    """The form's field names equal the endpoint's request-schema field names."""
    form_names = {f["name"] for f in get_form_fields(entity)}
    schema_names = set(ENTITY_SCHEMA[entity].model_fields)
    allowed_absent = set(EXCEPTIONS.get(entity, {}))
    missing = schema_names - form_names - allowed_absent
    extra = form_names - schema_names
    assert not missing, f"{entity}: form is missing API fields {sorted(missing)}"
    assert not extra, f"{entity}: form has fields the API ignores {sorted(extra)}"


def test_every_builder_entity_is_schema_checked() -> None:
    """No entity defines a form builder without a contract to check it against."""
    unchecked = set(FORM_FIELD_BUILDERS) - set(ENTITY_SCHEMA)
    assert not unchecked, f"entities lack a request-schema mapping: {sorted(unchecked)}"


# --- build_form_fields exclude/overrides self-check -------------------------


def test_build_form_fields_exclude_and_override() -> None:
    meta = load_table("Equipment")
    base = {f["name"] for f in meta.build_form_fields()}
    assert "equipment_model_id" in base and "is_active" in base

    fields = meta.build_form_fields(
        exclude={"is_active", "storage_location"},
        overrides={"equipment_model_id": {"name": "model_id"}},
    )
    names = {f["name"] for f in fields}
    assert "is_active" not in names and "storage_location" not in names
    assert "model_id" in names and "equipment_model_id" not in names


# --- meta-test: every form-building page is registered ----------------------

_PAGES_DIR = Path(__file__).resolve().parents[2] / "app" / "pages"
_FORM_BUILDERS = ("create_form_dialog", "edit_form_dialog", "render_crud_page", "render_form_field")

# Pages that build a form but are not yet routed through form_specs.
# Each must be migrated; the entry documents why it isn't covered yet.
PENDING_PAGES: dict[str, str] = {
    "sites.py": "hand-built st.form + location_picker; kept custom by design decision",
    "watersheds.py": "hand-built st.form; kept custom by design decision",
    "binning_axes.py": "hand-built st.form with nested bins editor; kept custom by design decision",
    "operation_kinds.py": "seed-only vocab; no create request schema",
    "bin_kinds.py": "seed-only vocab; no create request schema",
}


def _page_builds_form(src: str) -> bool:
    return any(b in src for b in _FORM_BUILDERS)


def _page_uses_form_specs(src: str) -> bool:
    return "get_form_fields" in src


@pytest.mark.parametrize(
    "page", sorted(p.name for p in _PAGES_DIR.glob("*.py") if p.name != "__init__.py")
)
def test_form_page_is_registered_or_pending(page: str) -> None:
    """Any page that renders a form must route through form_specs or be PENDING."""
    src = (_PAGES_DIR / page).read_text()
    if not _page_builds_form(src):
        return
    if _page_uses_form_specs(src):
        return
    assert page in PENDING_PAGES, (
        f"{page} builds a form but does not use form_specs.get_form_fields and is "
        f"not listed in PENDING_PAGES. Route it through form_specs or register it."
    )
