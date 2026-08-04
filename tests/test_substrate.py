"""
Sustrato Espacial S_n - Pruebas Funcionales Básicas.
Cubre: Ingesta, Calibración C1 (varianza), Persistencia Append-Only (id, seq) y Adyacencia ε.
"""
import sqlite3
import numpy as np
import pytest
import traianus.app as main
from traianus.app import serialize_vector, async_spectral_processor

def test_c1_threshold_excludes_self_projection(isolate_db):
    """Calibración C1: la varianza de la base ortonormal sin autoproyección debe ser 0.0."""
    threshold = main.auto_calibrate_critical_threshold()
    assert threshold == pytest.approx(0.0)

def test_append_only_revision_log(client, auth_headers, isolate_db):
    """Invariant H4: La consolidación inserta una nueva revisión sin sobrescribir (seq 1 -> 2)."""
    res_ingest = client.post(
        "/ingesta",
        json={"type": "text/plain", "text": "Entidad inmutable"},
        headers=auth_headers
    )
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
    """Invariant H5: Cálculo determinista de adyacencia epsilon sobre la variedad."""
    main.DB_PATH = isolate_db
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
    
    count = main.persist_epsilon_edges(0.8)
    assert count == 1
