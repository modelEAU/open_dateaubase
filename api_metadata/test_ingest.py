# test_ingest.py
from fastapi.testclient import TestClient
from main import app
import os

client = TestClient(app)

def test_ingest_ok():
    os.environ["API_KEY"] = "test-key"

    payload = {
        "equipment_id": 1,
        "parameter_id": 1,
        "unit_id": 1,
        "purpose_id": 1,
        "sampling_point_id": 1,
        "project_id": 1,
        "value": 12.34,
        "timestamp": "2025-11-30T01:30:00"
    }

    headers = {"x-api-key": "test-key"}

    response = client.post("/ingest", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "inserted"
    assert "metadata_id" in data
