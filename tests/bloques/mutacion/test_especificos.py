"""
This file verifies MUST/MUST NOT requirements from the SPEC (RFC 2119).
BLOCK: mutation — specific tests (Phase 2).

Tests moved from tests/test_control_plane.py WITHOUT changing assertions.
Cover: logographic genesis / dimensional expansion (ADR-015).
Normative: docs/development/tests/SPEC-mutacion.md
Coverage: MU01"""
import sqlite3

import numpy as np

import traianus.app as main
from traianus.app import serialize_vector


def test_mutation_MU01_logographic_genesis(client, auth_headers, isolate_db):
    with sqlite3.connect(isolate_db) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO manifold_nodes
            (id, seq, text, toon_factor, lifecycle_state, action_potential, revision_milestone, vector_blob, projections_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("NODE_ORIG", 1, "Original node", "\u25b2", "consolidated", 1.0, 1,
              serialize_vector(np.ones(384)), "{}"))
        conn.commit()

    response = client.post("/mutate/\u2605", headers=auth_headers)
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "SUCCESS"
    assert res_data["new_axis"] == "\u2605_CUSTOM"

    with sqlite3.connect(isolate_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, simbolo, vector_blob FROM geodesic_axes")
        axes = cursor.fetchall()
        assert len(axes) == 9

        axis_vec_0 = np.frombuffer(axes[0][2], dtype=np.float64)
        assert len(axis_vec_0) == 385

        new_axis_vec = np.frombuffer(axes[-1][2], dtype=np.float64)
        assert len(new_axis_vec) == 385
        assert new_axis_vec[-1] == 1.0
        assert np.allclose(new_axis_vec[:-1], 0.0)

        cursor.execute("SELECT vector_blob FROM manifold_nodes WHERE id = ? ORDER BY seq DESC LIMIT 1", ("NODE_ORIG",))
        node_blob = cursor.fetchone()[0]
        node_vec = np.frombuffer(node_blob, dtype=np.float64)
        assert len(node_vec) == 385
