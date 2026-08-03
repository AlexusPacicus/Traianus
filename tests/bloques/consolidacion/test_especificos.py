"""
This file verifies MUST/MUST NOT requirements from the SPEC (RFC 2119).
BLOCK: consolidation — specific tests (Phase 2 + Phase 5).

Tests moved from tests/test_control_plane.py and tests/test_append_only_log.py
WITHOUT changing assertions. Cover: dual-key consolidation (ADR-022),
key symmetry (CO-11), autocalibrated threshold (C1), 404 on missing
node (M7), append-only (H4), and automatic E_n persistence
(auto-edge-*, ADR-023/H5).
Normative: docs/development/tests/SPEC-consolidacion.md
Coverage: CO01, CO02, CO03, CO04, CO05, CO06, CO07, CO11, CO12"""
import os
import sqlite3

import numpy as np
import pytest

import traianus.app as main
from traianus.app import serialize_vector
from helpers.fake_encoder import FakeSentenceTransformer


def test_consolidation_CO01_dual_key_consolidation(client, auth_headers, isolate_db):
    with sqlite3.connect(isolate_db) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO manifold_nodes
            (id, seq, text, toon_factor, lifecycle_state, action_potential, revision_milestone, vector_blob, projections_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("NODE_100", 1, "Initial pending text", "\u25b2", "pending_approval", 0.1, 0,
              serialize_vector(np.zeros(384)), "{}"))
        conn.commit()

    response = client.post(
        "/nodos/NODE_100/consolidar",
        json={"text": "Consolidated human edited text", "ethical_key": True},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "SUCCESS"
    assert response.json()["new_state"] == "consolidated"
    assert response.json()["dual_key_status"]["ethical_key"] is True
    assert response.json()["dual_key_status"]["consolidated"] is True

    with sqlite3.connect(isolate_db) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT text, toon_factor, revision_milestone, lifecycle_state FROM manifold_nodes WHERE id = ? ORDER BY seq DESC LIMIT 1",
            ("NODE_100",)
        )
        row = cursor.fetchone()

        assert row[0] == "Consolidated human edited text"
        assert len(row[1]) == 1
        assert row[2] == 1
        assert row[3] == response.json()["new_state"]


def test_consolidation_CO02_threshold_excludes_self_projection(isolate_db):
    """
    C1 Regression: autocalibration must project each axis ONLY against
    the others (j != i). With the one-hot fixture basis, every cross projection
    is 0.0, so the threshold must be exactly 0.0. If self-projection were
    included (dot == 1.0), the threshold would be > 0 and the consolidation
    gate would sit at an unreachable scale (audit C1: 0/20).
    """
    threshold = main.auto_calibrate_critical_threshold()
    assert threshold == pytest.approx(0.0)


def test_consolidation_CO03_missing_node_404(client, auth_headers):
    """
    M7 Regression: consolidating a missing node must return 404, not
    fake SUCCESS (the UPDATE silently affected 0 rows).
    """
    response = client.post(
        "/nodos/NODE_DOES_NOT_EXIST/consolidar",
        json={"text": "x", "ethical_key": True},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_consolidation_CO04_requires_ethical_key(client, auth_headers, isolate_db):
    with sqlite3.connect(isolate_db) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO manifold_nodes
            (id, seq, text, toon_factor, lifecycle_state, action_potential, revision_milestone, vector_blob, projections_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("NODE_200", 1, "Pending node", "\u25b2", "pending_approval", 0.1, 0,
              serialize_vector(np.zeros(384)), "{}"))
        conn.commit()

    response = client.post("/nodos/NODE_200/consolidar", json={"text": "no ethical confirmation"}, headers=auth_headers)
    assert response.status_code == 422

    with sqlite3.connect(isolate_db) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT lifecycle_state, revision_milestone FROM manifold_nodes WHERE id = ?",
            ("NODE_200",)
        )
        row = cursor.fetchone()

    assert row[0] == "pending_approval"
    assert row[1] == 0


def test_consolidation_CO05_false_ethical_key_incubating(client, auth_headers, isolate_db):
    with sqlite3.connect(isolate_db) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO manifold_nodes
            (id, seq, text, toon_factor, lifecycle_state, action_potential, revision_milestone, vector_blob, projections_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("NODE_201", 1, "Pending node", "\u25b2", "pending_approval", 0.1, 0,
              serialize_vector(np.zeros(384)), "{}"))
        conn.commit()

    response = client.post(
        "/nodos/NODE_201/consolidar",
        json={"text": "no human confirmation", "ethical_key": False},
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert response.json()["new_state"] == "incubating"
    assert response.json()["dual_key_status"]["ethical_key"] is False
    assert response.json()["dual_key_status"]["consolidated"] is False

    with sqlite3.connect(isolate_db) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT lifecycle_state, revision_milestone FROM manifold_nodes WHERE id = ? ORDER BY seq DESC LIMIT 1",
            ("NODE_201",)
        )
        row = cursor.fetchone()

    assert row[0] == "incubating"
    assert row[1] == 0


def test_consolidation_CO06_inserts_new_revision(client, auth_headers, isolate_db):
    """
    Ingestion -> consolidate must create TWO revision rows for the same id
    with increasing seq (1 -> 2): audit trail is preserved and the previous
    state is not destroyed (no UPDATE).
    """
    response = client.post(
        "/ingesta",
        json={"type": "text/plain", "text": "Append-only audit entity"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    ingestion_id = response.json()["ingestion_id"]
    node_id = f"NODE_{ingestion_id}"

    consolidate = client.post(
        f"/nodos/{node_id}/consolidar",
        json={"text": "Append-only audit entity", "ethical_key": True},
        headers=auth_headers,
    )
    assert consolidate.status_code == 200
    assert consolidate.json()["new_state"] == "consolidated"

    with sqlite3.connect(isolate_db) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, seq, lifecycle_state, revision_milestone
            FROM manifold_nodes
            WHERE id = ?
            ORDER BY seq ASC
        """, (node_id,))
        rows = cursor.fetchall()

    # At least two revisions: the original (pending) and the consolidated one.
    assert len(rows) >= 2, (
        f"Expected >= 2 append-only revisions for {node_id}, got {len(rows)}"
    )

    seqs = [row[1] for row in rows]
    assert seqs == sorted(seqs), "seq must be monotonically increasing"
    assert len(set(seqs)) == len(seqs), "seq must be strictly increasing (no overlap)"

    # The first revision preserves the originally ingested state.
    assert rows[0][2] == "pending_approval"
    # The last revision reflects the consolidation.
    assert rows[-1][2] == consolidate.json()["new_state"]
    assert rows[-1][3] == 1


def test_consolidation_CO07_no_destructive_statements():
    """
    Static verification: production code must not contain destructive
    statements on nodes (UPDATE / REPLACE / DELETE on manifold_nodes).
    H4 regression.
    """
    repo_root = os.path.join(os.path.dirname(__file__), "..", "..", "..")
    for rel in ("traianus/app.py", "traianus/bootstrap.py"):
        with open(os.path.join(repo_root, rel), encoding="utf-8") as fh:
            source = fh.read()

        assert "UPDATE manifold_nodes" not in source, f"{rel}: UPDATE on nodes prohibited (H4)"
        assert "REPLACE INTO manifold_nodes" not in source, f"{rel}: REPLACE on nodes prohibited (H4)"
        assert "DELETE FROM manifold_nodes" not in source, f"{rel}: DELETE on nodes prohibited (H4)"


def test_consolidation_CO11_key_symmetry_adr022(client, auth_headers, isolate_db, monkeypatch):
    """
    ADR-022 key symmetry: the ethical key alone does NOT consolidate.
    With ethical_key=True but topological key NOT passed (variance < threshold),
    state remains incubating — no key has unilateral authority.
    """
    with sqlite3.connect(isolate_db) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO manifold_nodes
            (id, seq, text, toon_factor, lifecycle_state, action_potential, revision_milestone, vector_blob, projections_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("NODE_300", 1, "Low contrast note", "\u25b2", "pending_approval", 0.0001, 0,
              serialize_vector(np.zeros(384)), "{}"))
        conn.commit()

    # Force topological key failure: threshold greater than any achievable
    # variance. Only the ethical key remains active.
    monkeypatch.setattr(main, "auto_calibrate_critical_threshold", lambda: 1e9)

    response = client.post(
        "/nodos/NODE_300/consolidar",
        json={"text": "a mundane weekly schedule note without sharp contrasts", "ethical_key": True},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["new_state"] == "incubating", (
        "CO-11 MUST: ethical key alone does NOT consolidate (ADR-022 symmetry)"
    )
    assert body["dual_key_status"]["ethical_key"] is True
    assert body["dual_key_status"]["topological_key"] is False
    assert body["dual_key_status"]["consolidated"] is False


def test_consolidation_CO12_consolidate_persists_epsilon_edges(client, auth_headers, isolate_db, monkeypatch):
    """
    CO-12 MUST: Consolidating a node rebuilds and persists E_n (auto-edge-*
    edges with state='auto') over current MAX(seq) revisions, without altering
    manual edge-* edges (ADR-023/H5, H4).

    Deterministic E_n (ADR-023/H5): (v_i, v_j) ∈ E_n iff ||v_i − v_j||₂ ≤ ε.
    After consolidating NODE_A with the same text seeded in NODE_B, the
    MAX(seq) vector of NODE_A == vector of NODE_B (distance 0 ≤ EPSILON_EDGE),
    so the auto-edge-NODE_A-NODE_B edge must persist with state='auto'
    while the manual edge-NODE_A-NODE_B edge (HITL, state='manual')
    survives intact.
    """
    # Controlled current vectors (L2-normalized, distance <= EPSILON_EDGE):
    # the fake encoder (L1) is deterministic, so shared text produces the same
    # vector within the consolidation endpoint.
    fake = FakeSentenceTransformer()
    shared_text = "anchored vector for NODE_B"
    vec_b = fake.encode(shared_text)
    rng = np.random.default_rng(2026)
    perturb = rng.standard_normal(384)
    perturb = perturb - np.dot(perturb, vec_b) * vec_b
    perturb = perturb / np.linalg.norm(perturb) * 0.5
    vec_a = vec_b + perturb
    vec_a = vec_a / np.linalg.norm(vec_a)

    with sqlite3.connect(isolate_db) as conn:
        for node_id, vec in (("NODE_A", vec_a), ("NODE_B", vec_b)):
            conn.execute("""
                INSERT INTO manifold_nodes
                (id, seq, text, toon_factor, lifecycle_state, action_potential, revision_milestone, vector_blob, projections_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (node_id, 1, f"Seeded {node_id}", "\u25b2", "pending_approval", 0.1, 0,
                  serialize_vector(vec), "{}"))
        conn.commit()

    # Prior manual (HITL) edge: edge-NODE_A-NODE_B with state='manual'.
    manual = client.post(
        "/relations",
        json={"source": "NODE_A", "target": "NODE_B", "state": "manual"},
        headers=auth_headers,
    )
    assert manual.status_code == 200
    assert manual.json()["id"] == "edge-NODE_A-NODE_B"

    # Topological key forced to pass (C1): threshold 0.0 + ethical_key=True.
    monkeypatch.setattr(main, "auto_calibrate_critical_threshold", lambda: 0.0)

    response = client.post(
        "/nodos/NODE_A/consolidar",
        json={"text": shared_text, "ethical_key": True},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    # Response shape unchanged (status/new_state/dual_key_status).
    assert set(body.keys()) == {"status", "new_state", "dual_key_status"}
    assert body["status"] == "SUCCESS"
    assert body["new_state"] == "consolidated"
    assert set(body["dual_key_status"].keys()) == {
        "topological_key", "ethical_key", "consolidated",
    }
    assert body["dual_key_status"]["topological_key"] is True
    assert body["dual_key_status"]["ethical_key"] is True
    assert body["dual_key_status"]["consolidated"] is True

    with sqlite3.connect(isolate_db) as conn:
        auto_row = conn.execute(
            "SELECT id, source, target, state FROM manifold_edges WHERE id = ?",
            ("auto-edge-NODE_A-NODE_B",),
        ).fetchone()
        manual_row = conn.execute(
            "SELECT id, source, target, state FROM manifold_edges WHERE id = ?",
            ("edge-NODE_A-NODE_B",),
        ).fetchone()

    assert auto_row is not None, (
        "CO-12 MUST: consolidation must persist auto-edge-NODE_A-NODE_B (E_n)"
    )
    assert auto_row[1] == "NODE_A"
    assert auto_row[2] == "NODE_B"
    assert auto_row[3] == "auto"
    assert manual_row is not None, "CO-12 MUST: manual edge-* must survive E_n"
    assert manual_row[3] == "manual"
