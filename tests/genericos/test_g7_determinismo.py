"""
G7 — Determinism (finding M1, audit TRAIANUS_AUDIT.md:50,303).

Normative (RFC 2119): given the same initial state and same inputs, the
projections and resulting state MUST be identical (deterministic ops:
np.dot / np.var). Unit tests run with deterministic fake encoder (L1),
so repetition MUST produce byte-identical results.

Normative: docs/archive/legacy_docs/development/tests/SPEC-global.md
Coverage: G7
"""
import json
import sqlite3

import numpy as np
import pytest

import traianus.app as main
from traianus.app import serialize_vector
from helpers.endpoint_registry import BLOCKS


def _seed_nodes(db_path):
    """Seeds two current-state nodes so /relations can create a real edge."""
    with sqlite3.connect(db_path) as conn:
        for nid in ("NODE_A", "NODE_B"):
            conn.execute("""
                INSERT INTO manifold_nodes
                (id, seq, text, toon_factor, lifecycle_state, action_potential, revision_milestone, vector_blob, projections_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (nid, 1, f"Seeded {nid}", "\u25b2", "incubating", 0.1, 0,
                  serialize_vector(np.zeros(384)), "{}"))
        conn.commit()


@pytest.mark.parametrize("block", BLOCKS)
def test_g7_repetition_deterministic(block, client, auth_headers, isolate_db):
    """MUST: repeating the same operation produces the same result."""
    if block == "ingestion":
        n1 = _ingest_node(client, auth_headers, "determinism probe")
        n2 = _ingest_node(client, auth_headers, "determinism probe")
        assert _projections(isolate_db, n1) == _projections(isolate_db, n2)
    elif block == "consolidation":
        node_id = _ingest_node(client, auth_headers, "determinism node")
        client.post(
            f"/nodos/{node_id}/consolidar",
            json={"text": "same text", "ethical_key": True},
            headers=auth_headers,
        )
        r1 = _node_revisions(isolate_db, node_id)
        client.post(
            f"/nodos/{node_id}/consolidar",
            json={"text": "same text", "ethical_key": True},
            headers=auth_headers,
        )
        r2 = _node_revisions(isolate_db, node_id)
        # both consolidations with the same text produce identical projections
        assert r1[-1] == r2[-1]
    elif block == "relations":
        # Seed both endpoints so the edge is actually created (the former
        # test posted against dangling nodes and compared two empty lists).
        _seed_nodes(isolate_db)
        payload = {"source": "NODE_A", "target": "NODE_B", "state": "consolidated"}
        first_post = client.post("/relations", json=payload, headers=auth_headers)
        assert first_post.status_code == 200, "relations MUST create the seeded edge"
        first = client.get("/relations", headers=auth_headers).json()
        assert any(e["id"] == "edge-NODE_A-NODE_B" for e in first), (
            "G7 MUST: the edge must exist, not an empty comparison"
        )
        second_post = client.post("/relations", json=payload, headers=auth_headers)
        assert second_post.status_code == 200
        second = client.get("/relations", headers=auth_headers).json()
        assert first == second
    elif block == "mutation":
        t1 = main.auto_calibrate_critical_threshold()
        t2 = main.auto_calibrate_critical_threshold()
        assert t1 == t2
    elif block == "observability":
        first = client.get("/nodos").json()
        second = client.get("/nodos").json()
        assert first == second
    elif block == "bootstrap":
        t1 = main.auto_calibrate_critical_threshold()
        t2 = main.auto_calibrate_critical_threshold()
        assert t1 == t2


def _ingest_node(client, auth_headers, text):
    r = client.post("/ingesta", json={"type": "text/plain", "text": text}, headers=auth_headers)
    assert r.status_code == 200
    return f"NODE_{r.json()['ingestion_id']}"


def _projections(db_path, node_id):
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT projections_json FROM manifold_nodes WHERE id = ?", (node_id,)
        ).fetchone()
    return json.loads(row[0])


def _node_revisions(db_path, node_id):
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT projections_json FROM manifold_nodes WHERE id = ? ORDER BY seq",
            (node_id,),
        ).fetchall()
    return [json.loads(r[0]) for r in rows]
