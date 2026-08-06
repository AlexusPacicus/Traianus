"""
E2E integration tests with the real model (all-MiniLM-L6-v2).
"""
import pytest
import traianus.storage as storage
from helpers.db_factory import create_test_db

pytestmark = pytest.mark.model

@pytest.fixture(autouse=True)
def realistic_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "e2e_clean.db")
    monkeypatch.setattr(storage, "DB_PATH", db_path)
    create_test_db(db_path, seed="realistic")
    return db_path

def test_e2e_pipeline_journey(client, ingesta, auth_headers):
    """Full journey: ingestion -> L2 vector (384D) -> projection spectrum."""
    res = ingesta("Sovereign knowledge vector")
    assert res.status_code == 200
    
    nodes = client.get("/nodos", headers=auth_headers).json().get("nodes", [])
    assert len(nodes) == 1
    assert nodes[0]["lifecycle_state"] == "pending_approval"
    assert len(nodes[0]["projections_json"]) == 8
