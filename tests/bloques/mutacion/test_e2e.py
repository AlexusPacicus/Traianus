"""
This file verifies MUST/MUST NOT requirements from the SPEC (RFC 2119).
BLOCK: mutation — E2E with real model (Phase 6).

Full journey: /mutate/{symbol} expands the dimension N→N+1 (384→385),
injects the canonical axis [0,...,1] and fills the nodes (ADR-015/H4).
Normative: docs/development/tests/SPEC-mutacion.md
Coverage: MU04"""
import sqlite3

import pytest

import traianus.app as main
import traianus.bootstrap as gb
from helpers.db_factory import create_test_db

pytestmark = pytest.mark.model


@pytest.fixture(autouse=True)
def realistic_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "mutacion_e2e.db")
    monkeypatch.setattr(main, "DB_PATH", db_path)
    monkeypatch.setattr(gb, "DB_PATH", db_path)
    create_test_db(db_path, seed="realistic")
    return db_path


def test_e2e_mutation_MU04_full_journey(client, auth_headers, realistic_db):
    client.post(
        "/ingesta",
        json={"type": "text/plain", "text": "Something happens."},
        headers=auth_headers,
    )
    nodes_before = client.get("/nodos", headers=auth_headers).json().get("nodes", [])
    assert len(nodes_before) == 1
    assert len(nodes_before[0]["projections_json"]) == 8

    res = client.post("/mutate/\u2605", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["status"] == "SUCCESS"
    assert "expanded to 385D" in res.json()["message"]

    with sqlite3.connect(realistic_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM geodesic_axes")
        axis_ids = [r[0] for r in cursor.fetchall()]
        assert any(a.startswith("T") for a in axis_ids), "new canonical axis injected"
        cursor.execute("""
            SELECT vector_blob FROM manifold_nodes m
            WHERE seq = (SELECT MAX(seq) FROM manifold_nodes m2 WHERE m2.id = m.id)
        """)
        blob = cursor.fetchone()[0]
    import numpy as np
    vec = np.frombuffer(blob, dtype=np.float64)
    assert len(vec) == 385, "nodes filled to the new dimension (H4)"
