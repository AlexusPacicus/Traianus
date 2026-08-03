"""
This file verifies MUST/MUST NOT requirements from the SPEC (RFC 2119).
BLOCK: relations — specific tests (Phase 2 + Phase 5).

Tests moved from tests/test_control_plane.py WITHOUT changing assertions.
Cover: /relations endpoints (ADR-002/ADR-014/ADR-020), multichannel spectrum,
schema alignment, edge integrity (L2), deterministic E_n (H5), and
E_n persistence (auto-edge-*, ADR-023/H5 + H4).
Normative: docs/development/tests/SPEC-relaciones.md
Coverage: RE01, RE02, RE03, RE07, RE08, RE09"""
import json
import sqlite3

import numpy as np

import traianus.app as main
from traianus.app import serialize_vector

# Epsilon threshold for automatic E_n persistence (ADR-023/H5). Mirrors the
# Action Plan constant; production code will expose
# `persist_epsilon_edges(epsilon)` that persists auto-edge-* edges.
EPSILON_EDGE = 0.8


def test_relations_RE01_endpoints_relations(client, auth_headers, isolate_db):
    with sqlite3.connect(isolate_db) as conn:
        for node_id in ("NODE_A", "NODE_B"):
            conn.execute("""
                INSERT INTO manifold_nodes
                (id, seq, text, toon_factor, lifecycle_state, action_potential, revision_milestone, vector_blob, projections_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (node_id, 1, "Node", "\u25b2", "pending_approval", 0.1, 0,
                  serialize_vector(np.zeros(384)), "{}"))
        conn.commit()

    payload = {"source": "NODE_A", "target": "NODE_B", "state": "consolidated"}
    res_post = client.post("/relations", json=payload, headers=auth_headers)
    assert res_post.status_code == 200
    assert res_post.json()["status"] == "SUCCESS"
    assert res_post.json()["id"] == "edge-NODE_A-NODE_B"

    res_get = client.get("/relations", headers=auth_headers)
    assert res_get.status_code == 200
    edges = res_get.json()
    assert len(edges) == 1
    assert edges[0]["id"] == "edge-NODE_A-NODE_B"
    assert edges[0]["source"] == "NODE_A"
    assert edges[0]["target"] == "NODE_B"
    assert edges[0]["state"] == "consolidated"


def test_relations_RE02_multichannel_spectrum(isolate_db):
    node_id = "NODE_SPECTRAL_TEST"
    spectrum_dict = {"AXIS_1": 0.85, "AXIS_2": 0.12, "AXIS_3": 0.03}
    spectrum_json = json.dumps(spectrum_dict)

    with sqlite3.connect(isolate_db) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO manifold_nodes
            (id, seq, text, toon_factor, lifecycle_state, action_potential, revision_milestone, vector_blob, projections_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (node_id, 1, "Diffuse payload", "\u25b2", "incubating", 0.5, 0,
              serialize_vector(np.zeros(384)), spectrum_json))
        conn.commit()

        cursor.execute("SELECT projections_json, toon_factor, lifecycle_state FROM manifold_nodes WHERE id = ?", (node_id,))
        row = cursor.fetchone()

    assert row is not None
    assert row[1] == "\u25b2"
    assert row[2] == "incubating"
    retrieved_spectrum = json.loads(row[0])
    assert retrieved_spectrum["AXIS_1"] == 0.85
    assert retrieved_spectrum["AXIS_2"] == 0.12


def test_relations_RE03_adr020_schema(isolate_db):
    with sqlite3.connect(isolate_db) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(manifold_nodes)")
        columns = [row[1] for row in cursor.fetchall()]

    assert "action_potential" in columns
    assert "revision_milestone" in columns
    assert "sys_internal_timestamp" in columns


def test_relations_RE07_dangling_edge_rejected(client, auth_headers, isolate_db):
    # L2: without prior nodes, POST /relations with non-existent endpoints must
    # respond 4xx (404), not create a dangling edge.
    payload = {"source": "NODE_DOES_NOT_EXIST", "target": "ALSO_MISSING", "state": "incubating"}
    res = client.post("/relations", json=payload, headers=auth_headers)
    assert res.status_code == 404, f"L2 MUST NOT: dangling edge accepted ({res.status_code})"

    # The edge must not persist
    with sqlite3.connect(isolate_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM manifold_edges")
        assert cursor.fetchone()[0] == 0


def test_relations_RE08_epsilon_edges_deterministic(isolate_db):
    # H5/ADR-023: E_n = {(v_i, v_j) : ||v_i - v_j||_2 <= epsilon}. With orthogonal
    # one-hot vectors, the L2 distance between distinct axes is sqrt(2) ≈ 1.4142.
    main.DB_PATH = isolate_db
    with sqlite3.connect(isolate_db) as conn:
        for i, nid in enumerate(("NODE_A", "NODE_B", "NODE_C")):
            vec = np.zeros(384)
            vec[i] = 1.0
            conn.execute("""
                INSERT INTO manifold_nodes
                (id, seq, text, toon_factor, lifecycle_state, action_potential, revision_milestone, vector_blob, projections_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (nid, 1, f"Node {nid}", "\u25b2", "incubating", 0.1, 0,
                  serialize_vector(vec), "{}"))
        conn.commit()

    edges_close = main.rebuild_epsilon_edges(epsilon=1.5)
    assert len(edges_close) == 3  # complete pairs: AB, AC, BC

    edges_far = main.rebuild_epsilon_edges(epsilon=1.0)
    assert edges_far == []  # distance 1.4142 > 1.0

    assert edges_close[0]["source"] < edges_close[0]["target"]
    for e in edges_close:
        assert round(e["distance"], 4) == round(float(np.sqrt(2)), 4)


def test_relations_RE09_persist_epsilon_edges_semantics(isolate_db):
    """
    RE-09 MUST: persist_epsilon_edges(epsilon) persists deterministic E_n:
    writes auto-edge-<src>-<tgt> with state='auto', excludes nodes with
    lifecycle_state='telemetry_error', and preserves manual edges (ADR-023/H5, H4).

    Deterministic E_n (ADR-023/H5): (v_i, v_j) ∈ E_n iff ||v_i − v_j||₂ ≤ ε.
    Append-only (H4): auto edges that are no longer ε-adjacent receive a
    tombstone revision state='removed' instead of being deleted; the current
    view (MAX(seq), state != 'removed') then exposes no stale auto rows.
    Reconstruction operates on current MAX(seq) revisions and the returned
    count == number of currently adjacent auto edges.
    """
    main.DB_PATH = isolate_db

    # L2-normalized one-hot vectors (dim 384) with controlled distances:
    #   NODE_A   = e0                 -> d(A,B) ≈ 0.7654 <= EPSILON_EDGE
    #   NODE_B   = (e0+e1)/sqrt(2)    -> ε-adjacent to A
    #   NODE_C   = e2                 -> d with A/B ≈ 1.4142 > EPSILON_EDGE
    #   NODE_ERR = e0 (telemetry_error) -> d(A) = 0 but excluded by state
    dim = 384
    one_hot = [np.zeros(dim) for _ in range(4)]
    for idx in range(4):
        one_hot[idx][idx] = 1.0
    vec_a, vec_b, vec_c, vec_err = one_hot[0], (one_hot[0] + one_hot[1]) / np.sqrt(2.0), one_hot[2], one_hot[0]

    with sqlite3.connect(isolate_db) as conn:
        for node_id, vec, lifecycle in (
            ("NODE_A", vec_a, "incubating"),
            ("NODE_B", vec_b, "incubating"),
            ("NODE_C", vec_c, "incubating"),
            ("NODE_ERR", vec_err, "telemetry_error"),
        ):
            conn.execute("""
                INSERT INTO manifold_nodes
                (id, seq, text, toon_factor, lifecycle_state, action_potential, revision_milestone, vector_blob, projections_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (node_id, 1, f"Seeded {node_id}", "\u25b2", lifecycle, 0.1, 0,
                  serialize_vector(vec), "{}"))
        # Prior manual (HITL) edge: must survive reconstruction.
        conn.execute(
            "INSERT INTO manifold_edges (id, seq, source, target, state) VALUES (?, ?, ?, ?, ?)",
            ("edge-NODE_A-NODE_B", 1, "NODE_A", "NODE_B", "manual"),
        )
        conn.commit()

    count = main.persist_epsilon_edges(EPSILON_EDGE)
    assert count == 1, f"RE-09 MUST: count == expected auto edges (1), got {count}"

    with sqlite3.connect(isolate_db) as conn:
        rows = conn.execute(
            "SELECT id, source, target, state FROM manifold_edges ORDER BY id"
        ).fetchall()
        manual_row = conn.execute(
            "SELECT state FROM manifold_edges WHERE id = 'edge-NODE_A-NODE_B'"
        ).fetchone()

    assert rows == [
        ("auto-edge-NODE_A-NODE_B", "NODE_A", "NODE_B", "auto"),
        ("edge-NODE_A-NODE_B", "NODE_A", "NODE_B", "manual"),
    ], "RE-09 MUST: deterministic auto-edge-<src>-<tgt> IDs; telemetry_error excluded; manual edge preserved"
    assert manual_row == ("manual",)

    # Idempotence: second call with changed vectors (NODE_A -> e3, far from
    # B and C) replaces the previous auto set: no stale auto rows, and the
    # manual edge stays intact.
    with sqlite3.connect(isolate_db) as conn:
        conn.execute("""
            INSERT INTO manifold_nodes
            (id, seq, text, toon_factor, lifecycle_state, action_potential, revision_milestone, vector_blob, projections_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("NODE_A", 2, "NODE_A moved far", "\u25b2", "incubating", 0.1, 0,
              serialize_vector(one_hot[3]), "{}"))
        conn.commit()

    count2 = main.persist_epsilon_edges(EPSILON_EDGE)
    assert count2 == 0, f"RE-09 MUST: no ε-adjacent pairs after moving NODE_A, count={count2}"

    with sqlite3.connect(isolate_db) as conn:
        stale_auto = conn.execute(
            "SELECT COUNT(*) FROM manifold_edges e "
            "WHERE state = 'auto' "
            "AND seq = (SELECT MAX(seq) FROM manifold_edges e2 WHERE e2.id = e.id)"
        ).fetchone()[0]
        manual_row2 = conn.execute(
            "SELECT id, state FROM manifold_edges WHERE id = 'edge-NODE_A-NODE_B'"
        ).fetchone()
        tombstone = conn.execute(
            "SELECT state FROM manifold_edges WHERE id = 'auto-edge-NODE_A-NODE_B' "
            "ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        edge_seqs = conn.execute(
            "SELECT seq FROM manifold_edges WHERE id = 'auto-edge-NODE_A-NODE_B' ORDER BY seq"
        ).fetchall()

    assert stale_auto == 0, (
        "RE-09 MUST: previous auto set is replaced (no stale auto rows)"
    )
    assert tombstone == ("removed",), (
        "RE-09 MUST (H4): the stale auto edge is tombstoned (append-only), not deleted"
    )
    assert len(edge_seqs) == 2 and edge_seqs == [(1,), (2,)], (
        "RE-09 MUST (H4): auto edge history keeps increasing seq revisions"
    )
    assert manual_row2 == ("edge-NODE_A-NODE_B", "manual"), (
        "RE-09 MUST: manual edge-* stays intact (H4)"
    )
