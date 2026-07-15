"""Unit tests for wayfinder ticket 006: AnnotationKind is five verdicts.

Red→green: these fail on the eleven-kind vocabulary and pass only once the six
cause-named kinds are retired (ADR-0007) and equipment moves stop auto-writing
an annotation.
"""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parent.parent.parent
ANNOTATION_KIND_YAML = REPO_ROOT / "schema_dictionary" / "tables" / "AnnotationKind.yaml"

VERDICTS = {"Anomaly", "Data Quality", "Note", "Exclusion", "Confirmed"}
RETIRED = {
    "Fault",
    "Maintenance",
    "Calibration Period",
    "Experiment",
    "Process Event",
    "Equipment Relocation",
}


def _seed() -> list[dict]:
    with ANNOTATION_KIND_YAML.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)["table"]["seed_data"]


def test_only_the_five_verdicts_survive():
    names = {row["Name"] for row in _seed()}
    assert names == VERDICTS
    assert not names & RETIRED


def test_retired_ids_stay_burned():
    """Survivors keep their original IDs, so old rows never change meaning."""
    ids = {row["Name"]: row["AnnotationKind_ID"] for row in _seed()}
    assert ids == {
        "Anomaly": 4,
        "Data Quality": 7,
        "Note": 8,
        "Exclusion": 9,
        "Confirmed": 10,
    }


def test_verdict_colors_are_distinguishable():
    colors = [row["Color"] for row in _seed()]
    assert len(set(colors)) == len(colors)


def test_equipment_move_writes_no_annotation():
    """A move is a cause: the history rows are its record, not an Annotation."""
    from api.v1.repositories import annotation_repository
    from api.v1.schemas.equipment_move import (
        EquipmentRelocateResponse,
        EquipmentRewireResponse,
    )

    assert not hasattr(annotation_repository, "create_equipment_move_annotations")
    assert "annotation_ids" not in EquipmentRelocateResponse.model_fields
    assert "annotation_ids" not in EquipmentRewireResponse.model_fields
