"""
This file verifies MUST/MUST NOT requirements from the SPEC (RFC 2119).
BLOCK: ingestion — E2E with real model (Phase 6).

Complete offline journey with all-MiniLM-L6-v2 (cached): the spectral pipeline
creates a pending_approval node with a 384-dim L2 vector and 8 projections.
Normative: docs/development/tests/SPEC-ingesta.md
Coverage: IN11"""
import sqlite3

import pytest

import traianus.app as main
import traianus.bootstrap as gb
from helpers.db_factory import create_test_db

pytestmark = pytest.mark.model


@pytest.fixture(autouse=True)
def realistic_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "ingesta_e2e.db")
    monkeypatch.setattr(main, "DB_PATH", db_path)
    monkeypatch.setattr(gb, "DB_PATH", db_path)
    create_test_db(db_path, seed="realistic")
    return db_path


def test_e2e_ingestion_IN11_full_journey(client, auth_headers, realistic_db):
    text = "Something happens."
    res = client.post(
        "/ingesta",
        json={"type": "text/plain", "text": text},
        headers=auth_headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "accepted"
    assert isinstance(body["ingestion_id"], int)

    nodes = client.get("/nodos", headers=auth_headers).json().get("nodes", [])
    assert len(nodes) == 1
    node = nodes[0]
    assert node["text"] == text
    assert node["lifecycle_state"] == "pending_approval"
    assert len(node["projections_json"]) == 8, "8 projections over geodetic axes"

    with sqlite3.connect(realistic_db) as conn:
        row = conn.execute(
            "SELECT seq, action_potential, length(vector_blob) FROM manifold_nodes WHERE id = ?",
            (node["id"],),
        ).fetchone()
    assert row is not None
    assert row[0] == 1
    assert row[1] >= 0.0
    assert row[2] == 384 * 8, "384-dim L2 vector (float64) persisted"
