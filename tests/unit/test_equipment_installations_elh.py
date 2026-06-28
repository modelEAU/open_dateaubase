"""Regression (F4): get_equipment_installations must read EquipmentLocationHistory.

The EquipmentInstallation table was dropped in the v2 schema, but
get_equipment_installations still queried [dbo].[EquipmentInstallation], so
GET /equipment/{id}/lifecycle 500'd ('Invalid object name EquipmentInstallation').
Location history now lives in EquipmentLocationHistory (ValidFrom/ValidTo rows).
These pin the source table and the dict mapping the InstallationOut schema expects.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

from api.v1.repositories import equipment_repository


def test_installations_query_targets_location_history_not_dropped_table():
    cursor = MagicMock()
    cursor.fetchall.return_value = []
    conn = MagicMock()
    conn.cursor.return_value = cursor

    equipment_repository.get_equipment_installations(conn, 5, None, None)

    executed = cursor.execute.call_args.args[0]
    assert "[dbo].[EquipmentLocationHistory]" in executed
    assert "EquipmentInstallation" not in executed


def test_installations_maps_elh_rows_to_installationout_shape():
    cursor = MagicMock()
    installed = datetime(2024, 1, 1)
    cursor.fetchall.return_value = [
        (7, 3, "Influent", installed, None, 2, "Baseline", "note"),
    ]
    conn = MagicMock()
    conn.cursor.return_value = cursor

    rows = equipment_repository.get_equipment_installations(conn, 5, None, None)

    assert rows == [
        {
            "installation_id": 7,
            "sampling_location_id": 3,
            "location_name": "Influent",
            "installed_date": installed,
            "removed_date": None,
            "campaign_id": 2,
            "campaign_name": "Baseline",
            "notes": "note",
        }
    ]


def test_installations_date_filters_use_validfrom_validto():
    cursor = MagicMock()
    cursor.fetchall.return_value = []
    conn = MagicMock()
    conn.cursor.return_value = cursor

    equipment_repository.get_equipment_installations(
        conn, 5, datetime(2024, 1, 1), datetime(2024, 12, 31)
    )

    executed = cursor.execute.call_args.args[0]
    assert "elh.[ValidTo] IS NULL OR elh.[ValidTo] >= ?" in executed
    assert "elh.[ValidFrom] <= ?" in executed
