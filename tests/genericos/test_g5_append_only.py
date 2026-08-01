"""
G5 — Append-only (findings H4/ADR-025#1, audit TRAIANUS_AUDIT.md:47,77).

Normative (RFC 2119): node history (manifold_nodes) MUST be
append-only: every transition INSERTS a new revision with increasing `seq`;
UPDATE/REPLACE/DELETE on manifold_nodes is PROHIBITED in production.
Observation (GET) MUST NOT generate mutations (ADR-025#2).

Normative: docs/development/tests/SPEC-global.md
Coverage: G5
"""
import os
import sqlite3

import pytest

import traianus.app as main
from helpers.endpoint_registry import BLOCKS

APPEND_ONLY_BLOCKS = ["ingestion", "consolidation", "relations", "mutation", "observability"]

PROD_FILES = ("traianus/app.py", "traianus/bootstrap.py")


@pytest.mark.parametrize("block", APPEND_ONLY_BLOCKS)
def test_g5_no_destructive_statements_on_nodes(block):
    """MUST: production code contains no destructive statements on nodes."""
    repo_root = os.path.join(os.path.dirname(__file__), "..", "..")
    for rel in PROD_FILES:
        with open(os.path.join(repo_root, rel), encoding="utf-8") as fh:
            source = fh.read()
        assert "UPDATE manifold_nodes" not in source, f"{rel}: UPDATE prohibited (H4)"
        assert "REPLACE INTO manifold_nodes" not in source, f"{rel}: REPLACE prohibited (H4)"
        assert "DELETE FROM manifold_nodes" not in source, f"{rel}: DELETE prohibited (H4)"


def test_g5_consolidation_inserts_new_revision(isolate_db, client, auth_headers):
    """MUST (consolidation): consolidate INSERTS a new revision with increasing seq."""
    response = client.post(
        "/ingesta", json={"type": "text/plain", "text": "append-only probe"}, headers=auth_headers
    )
    assert response.status_code == 200
    node_id = f"NODE_{response.json()['ingestion_id']}"

    client.post(
        f"/nodos/{node_id}/consolidar",
        json={"text": "append-only probe", "ethical_key": True},
        headers=auth_headers,
    )

    with sqlite3.connect(isolate_db) as conn:
        rows = conn.execute(
            "SELECT seq FROM manifold_nodes WHERE id = ? ORDER BY seq", (node_id,)
        ).fetchall()
    assert len(rows) >= 2, "original revision + consolidated revision must exist"
    seqs = [r[0] for r in rows]
    assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)


@pytest.mark.parametrize("block", ["observability", "relations"])
def test_g5_observation_no_state_mutation(block, client, auth_headers, isolate_db):
    """MUST (ADR-025#2): GET creates no new rows."""
    client.post("/ingesta", json={"type": "text/plain", "text": "x"}, headers=auth_headers)
    before_nodes = _count(isolate_db, "manifold_nodes")
    before_edges = _count(isolate_db, "manifold_edges")

    if block == "observability":
        client.get("/nodos")
        client.get("/telemetry", headers=auth_headers)
    else:
        client.get("/relations", headers=auth_headers)

    assert _count(isolate_db, "manifold_nodes") == before_nodes
    assert _count(isolate_db, "manifold_edges") == before_edges


def _count(db_path, table):
    with sqlite3.connect(db_path) as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
