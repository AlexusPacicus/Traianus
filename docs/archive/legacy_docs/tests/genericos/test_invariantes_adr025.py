"""
ADR-025 Invariants (docs/architecture/ADR/ADR.md:126-131).

Literal Grounding (ADR.md:131): "Integration test suites must validate these
five invariants on every build pipeline."

Normative (RFC 2119): the five non-negotiable state invariants MUST
validate on every build pipeline:
  1. Monotonic Append-Only Evolution
  2. Zero Observation Mutagenicity
  3. External Provider Isolation
  4. Mandatory Control Plane Centrality (Dual-Key Consolidation)
  5. Bitwise State Determinism

Normative: docs/archive/legacy_docs/development/tests/SPEC-global.md
Coverage: INV1, INV2, INV3, INV4, INV5
"""
import json
import sqlite3

import pytest

import traianus.app as main
from traianus.app import RefinedEntity


def _ingest(client, auth_headers, text):
    r = client.post("/ingesta", json={"type": "text/plain", "text": text}, headers=auth_headers)
    assert r.status_code == 200
    return f"NODE_{r.json()['ingestion_id']}"


def test_invariant_1_append_only_monotonic(client, auth_headers, isolate_db):
    """INV-1 MUST: every transition INSERTS a revision with increasing seq."""
    node_id = _ingest(client, auth_headers, "inv-1")
    client.post(
        f"/nodos/{node_id}/consolidar",
        json={"text": "inv-1", "ethical_key": True},
        headers=auth_headers,
    )
    with sqlite3.connect(isolate_db) as conn:
        seqs = [r[0] for r in conn.execute(
            "SELECT seq FROM manifold_nodes WHERE id = ? ORDER BY seq", (node_id,)
        ).fetchall()]
    assert len(seqs) >= 2
    assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)


def test_invariant_2_zero_observation_mutagenicity(client, auth_headers, isolate_db):
    """INV-2 MUST: observation (GET) produces zero side effects."""
    node_id = _ingest(client, auth_headers, "inv-2")
    before = _snapshot(isolate_db)
    client.get("/nodos")
    client.get("/telemetry", headers=auth_headers)
    client.get("/relations", headers=auth_headers)
    after = _snapshot(isolate_db)
    assert before == after


def test_invariant_3_provider_isolation(monkeypatch):
    """INV-3 MUST: control plane operates only on L2 vectors; external
    provider has no topology execution rights."""
    captured = {}

    class FakeST:
        def __init__(self, model_name, **kwargs):
            captured["model_name"] = model_name
            captured["kwargs"] = kwargs

    monkeypatch.setattr(main, "SentenceTransformer", FakeST)
    main.build_encoder()
    assert captured["model_name"] == "all-MiniLM-L6-v2"
    assert captured["kwargs"].get("local_files_only") is True


def test_invariant_4_dual_key_consolidation_centrality(client, auth_headers):
    """INV-4 MUST: consolidation requires BOTH keys (ADR-022). Without
    explicit Ethical Key, state is NEVER consolidated."""
    node_id = _ingest(client, auth_headers, "inv-4")
    r = client.post(
        f"/nodos/{node_id}/consolidar",
        json={"text": "inv-4", "ethical_key": False},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["new_state"] == "incubating"
    assert r.json()["dual_key_status"]["consolidated"] is False


def test_invariant_5_bitwise_state_determinism(client, auth_headers, isolate_db):
    """INV-5 MUST: same input → byte-identical stored vector."""
    n1 = _ingest(client, auth_headers, "bitwise determinism")
    n2 = _ingest(client, auth_headers, "bitwise determinism")
    with sqlite3.connect(isolate_db) as conn:
        b1 = conn.execute(
            "SELECT vector_blob FROM manifold_nodes WHERE id = ?", (n1,)
        ).fetchone()[0]
        b2 = conn.execute(
            "SELECT vector_blob FROM manifold_nodes WHERE id = ?", (n2,)
        ).fetchone()[0]
    assert b1 == b2


def _snapshot(db_path):
    with sqlite3.connect(db_path) as conn:
        nodes = conn.execute("SELECT id, seq, lifecycle_state FROM manifold_nodes ORDER BY id, seq").fetchall()
        edges = conn.execute("SELECT id, source, target, state FROM manifold_edges ORDER BY id").fetchall()
    return (nodes, edges)
