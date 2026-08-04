"""
Pruebas de Integración E2E con Modelo Real (all-MiniLM-L6-v2).
"""
import sqlite3
import pytest
import traianus.app as main
import traianus.bootstrap as gb
from helpers.db_factory import create_test_db

pytestmark = pytest.mark.model

@pytest.fixture(autouse=True)
def realistic_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "e2e_clean.db")
    monkeypatch.setattr(main, "DB_PATH", db_path)
    monkeypatch.setattr(gb, "DB_PATH", db_path)
    create_test_db(db_path, seed="realistic")
    return db_path

def test_e2e_pipeline_journey(client, auth_headers):
    """Journey completo: Ingesta -> Cálculo de Vector L2 (384D) -> Proyección."""
    res = client.post(
        "/ingesta",
        json={"type": "text/plain", "text": "Sovereign knowledge vector"},
        headers=auth_headers
    )
    assert res.status_code == 200
    
    nodes = client.get("/nodos", headers=auth_headers).json().get("nodes", [])
    assert len(nodes) == 1
    assert nodes[0]["lifecycle_state"] == "pending_approval"
    assert len(nodes[0]["projections_json"]) == 8
