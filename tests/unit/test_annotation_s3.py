"""S3 rename tests: Annotation.EquipmentEvent_ID → Event_ID.

Asserts:
  1. The YAML schema dictionary has a column named Event_ID (not EquipmentEvent_ID).
  2. AnnotationCreate accepts event_id as a keyword argument and stores it.
"""

from datetime import datetime
from pathlib import Path

from tools.schema_migrate.loader import load_schema

from api.v1.schemas.annotations import AnnotationCreate


_TABLES_DIR = Path(__file__).parent.parent.parent / "schema_dictionary" / "tables"


def test_annotation_yaml_has_event_id_not_equipment_event_id():
    """The Annotation table YAML defines Event_ID, not EquipmentEvent_ID."""
    schema = load_schema(_TABLES_DIR)
    annotation = schema["Annotation"]
    column_names = [col["name"] for col in annotation["table"]["columns"]]
    assert "Event_ID" in column_names, "Annotation table must have Event_ID column"
    assert "EquipmentEvent_ID" not in column_names, (
        "EquipmentEvent_ID must not appear in Annotation table after S3 rename"
    )


def test_annotation_create_accepts_event_id():
    """AnnotationCreate accepts event_id and exposes it correctly."""
    obj = AnnotationCreate(
        annotation_type="Fault",
        start_time=datetime.now(),
        event_id=42,
    )
    assert obj.event_id == 42
