"""
Spatial substrate S_n - basic functional tests.
Covers: ingestion, C1 calibration (variance), append-only persistence (id, seq) and ε-adjacency.
"""
import sqlite3
import numpy as np
import pytest
import traianus.app as main
import traianus.storage as storage
from traianus.app import serialize_vector, async_spectral_processor
from traianus.core import evaluate_gate_v01

def test_c1_threshold_excludes_self_projection(isolate_db):
    """C1 calibration: the orthonormal basis variance without self-projection must be 0.0."""
    threshold = main.auto_calibrate_critical_threshold()
    assert threshold == pytest.approx(0.0)

def test_append_only_revision_log(client, ingesta, auth_headers, isolate_db):
    """Invariant H4: consolidation inserts a new revision without overwriting (seq 1 -> 2)."""
    res_ingest = ingesta("Entidad inmutable")
    node_id = f"NODE_{res_ingest.json()['ingestion_id']}"
    
    res_consolidate = client.post(
        f"/nodos/{node_id}/consolidar",
        json={"text": "Entidad inmutable", "ethical_key": True},
        headers=auth_headers
    )
    assert res_consolidate.status_code == 200
    
    with sqlite3.connect(isolate_db) as conn:
        rows = conn.execute(
            "SELECT seq, lifecycle_state FROM manifold_nodes WHERE id = ? ORDER BY seq ASC",
            (node_id,)
        ).fetchall()
    
    assert len(rows) >= 2
    assert [r[0] for r in rows] == [1, 2]
    assert rows[0][1] == "pending_approval"
    assert rows[-1][1] == "consolidated"

def test_epsilon_edges_adjacency(isolate_db):
    """Invariant H5: deterministic epsilon-adjacency computation over the manifold."""
    with sqlite3.connect(isolate_db) as conn:
        for i, nid in enumerate(("NODE_A", "NODE_B")):
            vec = np.zeros(384)
            vec[i] = 0.3  # Distancia corta <= 0.8
            conn.execute("""
                INSERT INTO manifold_nodes
                (id, seq, text, toon_factor, lifecycle_state, action_potential, revision_milestone, vector_blob, projections_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (nid, 1, f"Nodo {nid}", "▲", "incubating", 0.1, 0, serialize_vector(vec), "{}"))
        conn.commit()
    
    count = storage.persist_epsilon_edges(0.8)
    assert count == 1

def test_consolidar_does_not_persist_auto_edges(client, ingesta, auth_headers, isolate_db):
    """SPEC v0.2 §3.3 (M-a): E_n observational - /consolidar does NOT persist auto-edge-*."""
    vec = np.asarray(main.get_provider().encode("Nodo común"), dtype=np.float64)
    with sqlite3.connect(isolate_db) as conn:
        for nid in ("NODE_A", "NODE_B"):
            conn.execute("""
                INSERT INTO manifold_nodes
                (id, seq, text, toon_factor, lifecycle_state, action_potential, revision_milestone, vector_blob, projections_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (nid, 1, f"Nodo {nid}", "▲", "pending_approval", 0.1, 0, serialize_vector(vec), "{}"))
        conn.commit()

    res = client.post(
        "/nodos/NODE_A/consolidar",
        json={"text": "Nodo común", "ethical_key": True},
        headers=auth_headers,
    )
    assert res.status_code == 200
    with sqlite3.connect(isolate_db) as conn:
        auto = conn.execute(
            "SELECT id FROM manifold_edges WHERE id LIKE 'auto-edge-%'"
        ).fetchall()
    assert auto == []

def test_relations_computes_auto_edges_on_read(client, auth_headers, isolate_db):
    """SPEC v0.2 §3.3: /relations computes E_n on read (observational), without persisting."""
    vec = np.asarray(main.get_provider().encode("Nodo común"), dtype=np.float64)
    with sqlite3.connect(isolate_db) as conn:
        for nid in ("NODE_A", "NODE_B"):
            conn.execute("""
                INSERT INTO manifold_nodes
                (id, seq, text, toon_factor, lifecycle_state, action_potential, revision_milestone, vector_blob, projections_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (nid, 1, f"Nodo {nid}", "▲", "pending_approval", 0.1, 0, serialize_vector(vec), "{}"))
        conn.commit()

    resp = client.get("/relations", headers=auth_headers)
    assert resp.status_code == 200
    edges = {e["id"]: e for e in resp.json()}
    assert "auto-edge-NODE_A-NODE_B" in edges
    assert edges["auto-edge-NODE_A-NODE_B"]["state"] == "auto"

def test_axes_anchored_to_prosthetic_epoch(isolate_db):
    """SPEC v0.2 §3.1: the 8 geodetic-basis axes are labeled PROSTHETIC_NSM_V1."""
    with sqlite3.connect(isolate_db) as conn:
        axes = conn.execute(
            "SELECT id, epoch_provenance FROM geodesic_axes ORDER BY id"
        ).fetchall()
    assert len(axes) == 8
    assert all(a[1] == "PROSTHETIC_NSM_V1" for a in axes)

def test_nodes_anchored_to_base_epoch(client, ingesta, isolate_db):
    """SPEC v0.2 §3.1: nodes (not only axes) stay anchored to their base epoch."""
    res = ingesta("Nodo base")
    node_id = f"NODE_{res.json()['ingestion_id']}"
    with sqlite3.connect(isolate_db) as conn:
        epoch = conn.execute(
            "SELECT epoch_provenance FROM manifold_nodes WHERE id = ?", (node_id,)
        ).fetchone()
    assert epoch is not None
    assert epoch[0] == "PROSTHETIC_NSM_V1"

def test_lifecycle_check_rejects_archived_state(isolate_db):
    """SPEC v0.2 §3.1 (A-e): `archived` does not exist in the schema; the CHECK rejects it."""
    with sqlite3.connect(isolate_db) as conn:
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("""
                INSERT INTO manifold_nodes
                (id, seq, text, toon_factor, lifecycle_state, action_potential, revision_milestone, vector_blob, projections_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, ("BAD_NODE", 1, "x", "▲", "archived", 0.0, 0,
                  serialize_vector(np.zeros(384, dtype=np.float32)), "{}"))

def test_lifecycle_check_accepts_valid_states(isolate_db):
    """SPEC v0.2 §3.1: the CHECK accepts the 4 operational states, incl. telemetry_error."""
    states = ("pending_approval", "incubating", "consolidated", "telemetry_error")
    with sqlite3.connect(isolate_db) as conn:
        for i, state in enumerate(states):
            conn.execute("""
                INSERT INTO manifold_nodes
                (id, seq, text, toon_factor, lifecycle_state, action_potential, revision_milestone, vector_blob, projections_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (f"VALID_{i}", 1, "x", "▲", state, 0.0, 0,
                  serialize_vector(np.zeros(384, dtype=np.float32)), "{}"))

def test_evaluate_gate_v01_dual_key_requires_both():
    """Pure kernel (§3.2): consolidation requires BOTH keys (AND)."""
    res = evaluate_gate_v01([0.9, -0.4, 0.3, -0.5], ethical_key=False, threshold=0.1)
    assert res["topological_key"]["passed"] is True
    assert res["topological_key"]["status"] == "PROVISIONAL_INFORMATIONAL_SCORE"
    assert res["state"] == "incubating"

    res = evaluate_gate_v01([0.9, -0.4, 0.3, -0.5], ethical_key=True, threshold=0.1)
    assert res["state"] == "consolidated"

    res = evaluate_gate_v01([0.5, 0.5, 0.5, 0.5], ethical_key=True, threshold=0.1)
    assert res["topological_key"]["passed"] is False
    assert res["state"] == "incubating"

def test_consolidar_exposes_provisional_score(client, ingesta, auth_headers, isolate_db):
    """§3.3/§4: /consolidar exposes the score in dual_key_status.topological_key."""
    res = ingesta("Entidad con espectro")
    node_id = f"NODE_{res.json()['ingestion_id']}"
    resp = client.post(
        f"/nodos/{node_id}/consolidar",
        json={"text": "Entidad con espectro", "ethical_key": True},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    tk = body["dual_key_status"]["topological_key"]
    assert tk["status"] == "PROVISIONAL_INFORMATIONAL_SCORE"
    assert "variance" in tk and "threshold" in tk and "passed" in tk
    assert body["dual_key_status"]["ethical_key"] is True
    assert body["dual_key_status"]["consolidated"] == (body["new_state"] == "consolidated")

def test_mutate_creates_new_epoch_without_touching_v1(client, auth_headers, isolate_db):
    """SPEC v0.2 §3.3 (M-a): /mutate inserts a full V2 basis; V1 stays immutable."""
    res = client.post("/mutate/Δ", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["new_epoch"] == "PROSTHETIC_NSM_V2"

    with sqlite3.connect(isolate_db) as conn:
        rows = conn.execute(
            "SELECT id, epoch_provenance, length(vector_blob) FROM geodesic_axes ORDER BY id, epoch_provenance"
        ).fetchall()
    v1 = [r for r in rows if r[1] == "PROSTHETIC_NSM_V1"]
    v2 = [r for r in rows if r[1] == "PROSTHETIC_NSM_V2"]
    assert len(v1) == 8
    assert len(v2) == 9  # 8 re-padded + 1 canonical
    # V1 rows unchanged: 384D float64 = 3072 bytes
    assert all(r[2] == 3072 for r in v1)
    # V2 rows re-padded: 385D float64 = 3080 bytes
    assert all(r[2] == 3080 for r in v2)

def test_mutate_does_not_rewrite_v1_vectors(client, auth_headers, isolate_db):
    """M-a: the V1 vector is not altered after /mutate (it was UPDATE in v0.1)."""
    with sqlite3.connect(isolate_db) as conn:
        before = dict(conn.execute("SELECT id, vector_blob FROM geodesic_axes").fetchall())
    res = client.post("/mutate/Ω", headers=auth_headers)
    assert res.status_code == 200
    with sqlite3.connect(isolate_db) as conn:
        v1_now = dict(conn.execute(
            "SELECT id, vector_blob FROM geodesic_axes WHERE epoch_provenance='PROSTHETIC_NSM_V1'"
        ).fetchall())
    assert v1_now == before


def _forge_vector_node(client, auth_headers, label, seed):
    rng = np.random.default_rng(seed)
    vec = rng.standard_normal(384)
    res = client.post(
        "/ingesta/vector",
        json={"vector": (vec / np.linalg.norm(vec)).tolist(), "label": label},
        headers={**auth_headers, "X-Idempotency-Key": f"edge-fixture-{label}"},
    )
    assert res.status_code == 201
    return res.json()["node_id"]


def test_edge_id_is_injective_over_hyphenated_labels(client, auth_headers, isolate_db):
    """R5/INV-6: edge_id(a, b) == edge_id(c, d) must imply {a, b} == {c, d}.

    ('VEC_x', 'VEC_y-VEC_z') and ('VEC_x-VEC_y', 'VEC_z') both flattened to
    'edge-VEC_x-VEC_y-VEC_z' under the '-'-joined encoding, so forging the
    second silently became a revision of the first."""
    ids = {
        label: _forge_vector_node(client, auth_headers, label, seed)
        for seed, label in enumerate(["x", "y-VEC_z", "x-VEC_y", "z"])
    }
    first = client.post(
        "/relations",
        json={"source": ids["x"], "target": ids["y-VEC_z"], "state": "hitl"},
        headers=auth_headers,
    )
    second = client.post(
        "/relations",
        json={"source": ids["x-VEC_y"], "target": ids["z"], "state": "hitl"},
        headers=auth_headers,
    )
    assert first.status_code == second.status_code == 200
    assert first.json()["id"] != second.json()["id"]
    assert len(storage.get_current_edges()) == 2


def test_edge_id_keeps_plain_format_for_hyphen_free_labels(client, auth_headers, isolate_db):
    """Regression guard: the encoding is the identity wherever the old one
    was unambiguous, so existing edge ids stay valid."""
    a = _forge_vector_node(client, auth_headers, "a", 10)
    b = _forge_vector_node(client, auth_headers, "b", 11)
    res = client.post(
        "/relations",
        json={"source": b, "target": a, "state": "hitl"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    assert res.json()["id"] == "edge-VEC_a-VEC_b"


def test_reingesting_consolidated_label_does_not_regress_state(client, auth_headers, isolate_db):
    """R4/INV-5: re-ingesting a label whose node is already consolidated must
    not append an incubating/pending revision -- that would silently demote
    the node with content that never passed the ethical key."""
    node_id = _forge_vector_node(client, auth_headers, "keep", 7)
    granted = client.post(
        f"/nodos/{node_id}/consolidar",
        json={"text": "x", "ethical_key": True},
        headers=auth_headers,
    )
    assert granted.json()["new_state"] == "consolidated"

    rng = np.random.default_rng(99)
    other = rng.standard_normal(384)
    res = client.post(
        "/ingesta/vector",
        json={"vector": (other / np.linalg.norm(other)).tolist(), "label": "keep"},
        headers={**auth_headers, "X-Idempotency-Key": "reingest-keep"},
    )
    assert res.status_code == 409
    with sqlite3.connect(isolate_db) as conn:
        rows = conn.execute(
            "SELECT seq, lifecycle_state FROM manifold_nodes WHERE id = ? ORDER BY seq",
            (node_id,),
        ).fetchall()
    assert rows[-1][1] == "consolidated"
    assert len(rows) == 2


def test_explicit_demotion_from_consolidated_stays_allowed(client, auth_headers, isolate_db):
    """Regression guard: leaving consolidated remains possible through the
    explicit /consolidar action; only the ingestion path is closed."""
    node_id = _forge_vector_node(client, auth_headers, "demote", 7)
    client.post(
        f"/nodos/{node_id}/consolidar",
        json={"text": "x", "ethical_key": True},
        headers=auth_headers,
    )
    denied = client.post(
        f"/nodos/{node_id}/consolidar",
        json={"text": "x", "ethical_key": False},
        headers=auth_headers,
    )
    assert denied.status_code == 200
    assert denied.json()["new_state"] == "incubating"
