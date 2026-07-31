import sys
import os
import json
import pytest
import sqlite3
import numpy as np
from typing import List, Literal
from pydantic import ValidationError
from fastapi.testclient import TestClient


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "py"))
import main
from main import (
    app, LifecycleState, RawDump, RefinedEntity,
    serialize_vector, async_spectral_processor,
)


client = TestClient(app)


# =====================================================================
# ISOLATED DATABASE FIXTURE (Pytest Isolation + Monkeypatching)
# =====================================================================


@pytest.fixture(autouse=True)
def isolate_test_database(tmp_path, monkeypatch):
    """
    Isolates each test inside an ephemeral SQLite database in tmp_path.
    Monkeypatches main.DB_PATH and initializes schema with context managers.
    """
    test_db_path = str(tmp_path / "test_traianus.db")
    monkeypatch.setattr(main, "DB_PATH", test_db_path)

    with sqlite3.connect(test_db_path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS geodesic_axes (
                id TEXT PRIMARY KEY,
                simbolo TEXT NOT NULL,
                tag TEXT NOT NULL,
                vector_blob BLOB NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS manifold_nodes (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                toon_factor TEXT NOT NULL,
                lifecycle_state TEXT NOT NULL,
                action_potential REAL NOT NULL,
                revision_milestone INTEGER NOT NULL,
                vector_blob BLOB NOT NULL,
                projections_json TEXT NOT NULL,
                sys_internal_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ingestion_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                payload TEXT NOT NULL,
                status TEXT DEFAULT 'PENDING',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS manifold_edges (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                state TEXT NOT NULL
            )
        """)

        for idx in range(8):
            vec = np.zeros(384, dtype=np.float64)
            vec[idx] = 1.0
            cursor.execute(
                "INSERT INTO geodesic_axes (id, simbolo, tag, vector_blob) VALUES (?, ?, ?, ?)",
                (f"AXIS_{idx+1}", chr(0x25B2 + idx), f"_AXIS_{idx+1}", serialize_vector(vec))
            )
        conn.commit()

    return test_db_path


# =====================================================================
# CYCLE 1: UTILITIES & DATA CONTRACTS
# =====================================================================


def test_vector_serialization_roundtrip():
    original_vec = np.random.randn(384).astype(np.float64)
    blob = serialize_vector(original_vec)
    reconstructed_vec = np.frombuffer(blob, dtype=np.float64)
    assert np.allclose(original_vec, reconstructed_vec)


def test_raw_dump_ingress_contract():
    payload = RawDump(text="Canonical coordinate payload", type="text/plain")
    assert payload.type == "text/plain"
    assert payload.text == "Canonical coordinate payload"


def test_refined_entity_enforces_lifecycle_enum():
    with pytest.raises(ValidationError):
        RefinedEntity(
            text="Invalid state payload",
            lifecycle_state="invalid_state_name",
            revision_milestone=False,
            projections=[0.1] * 8
        )


# =====================================================================
# CYCLE 2: FASTAPI ENDPOINT INGRESS & PIPELINE PROCESSOR
# =====================================================================


def test_ingesta_endpoint_accepts_plain_text():
    response = client.post("/ingesta", json={"type": "text/plain", "text": "Canonical test entity"})
    assert response.status_code == 200
    assert response.json()["status"] == 200
    assert response.json()["data"] == "plain text received"


def test_ingesta_endpoint_rejects_non_plain_text_payloads():
    response = client.post("/ingesta", json={"type": "audio/ogg", "text": "audio data"})
    assert response.status_code == 400
    assert "Strictly Plain Text required" in response.json()["detail"]


def test_async_spectral_processor_full_cycle(isolate_test_database):
    with sqlite3.connect(isolate_test_database) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO ingestion_queue (payload, status) VALUES (?, ?)", ("Test spectral text", "PENDING"))
        ingestion_id = cursor.lastrowid
        conn.commit()

    async_spectral_processor(ingestion_id, "Test spectral text")

    with sqlite3.connect(isolate_test_database) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, text, toon_factor, lifecycle_state, action_potential, vector_blob, projections_json "
            "FROM manifold_nodes WHERE id = ?",
            (f"NODE_{ingestion_id}",)
        )
        row = cursor.fetchone()

        assert row is not None
        assert row[0] == f"NODE_{ingestion_id}"
        assert row[1] == "Test spectral text"
        assert len(row[2]) == 1
        assert row[3] == "pending_approval"
        assert row[4] >= 0.0

        vec = np.frombuffer(row[5], dtype=np.float64)
        assert len(vec) == 384
        assert np.isclose(np.linalg.norm(vec), 1.0)

        projections = json.loads(row[6])
        assert len(projections) == 8


# =====================================================================
# CYCLE 3: HITL CONSOLIDATION & SPACE ACCRETION (ADR-015, ADR-022)
# =====================================================================


def test_consolidate_sovereignty_endpoint(isolate_test_database):
    with sqlite3.connect(isolate_test_database) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO manifold_nodes
            (id, text, toon_factor, lifecycle_state, action_potential, revision_milestone, vector_blob, projections_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ("NODE_100", "Initial pending text", "\u25b2", "pending_approval", 0.1, 0,
              serialize_vector(np.zeros(384)), "{}"))
        conn.commit()

    response = client.post("/nodos/NODE_100/consolidar", json={"text": "Consolidated human edited text", "ethical_key": True})
    assert response.status_code == 200
    assert response.json()["status"] == "SUCCESS"
    assert response.json()["new_state"] in ["consolidated", "incubating"]

    with sqlite3.connect(isolate_test_database) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT text, toon_factor, revision_milestone, lifecycle_state FROM manifold_nodes WHERE id = ?",
            ("NODE_100",)
        )
        row = cursor.fetchone()

        assert row[0] == "Consolidated human edited text"
        assert len(row[1]) == 1
        assert row[2] == 1
        assert row[3] == response.json()["new_state"]


def test_logographic_genesis_endpoint(isolate_test_database):
    with sqlite3.connect(isolate_test_database) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO manifold_nodes
            (id, text, toon_factor, lifecycle_state, action_potential, revision_milestone, vector_blob, projections_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ("NODE_ORIG", "Original node", "\u25b2", "consolidated", 1.0, 1,
              serialize_vector(np.ones(384)), "{}"))
        conn.commit()

    response = client.post("/mutate/\u2605")
    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "SUCCESS"
    assert res_data["new_axis"] == "\u2605_CUSTOM"

    with sqlite3.connect(isolate_test_database) as conn:
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

        cursor.execute("SELECT vector_blob FROM manifold_nodes WHERE id = ?", ("NODE_ORIG",))
        node_blob = cursor.fetchone()[0]
        node_vec = np.frombuffer(node_blob, dtype=np.float64)
        assert len(node_vec) == 385


# =====================================================================
# CYCLE 4: GRAPH EDGES, OBSERVABILITY & TELEMETRY (ADR-002, ADR-014, ADR-020)
# =====================================================================


def test_get_manifold_nodes_and_telemetry_isolation(isolate_test_database):
    with sqlite3.connect(isolate_test_database) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO manifold_nodes
            (id, text, toon_factor, lifecycle_state, action_potential, revision_milestone, vector_blob, projections_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ("NODE_1", "Clean text", "\u25b2", "consolidated", 1.0, 1,
              serialize_vector(np.zeros(384)), "{}"))
        cursor.execute("""
            INSERT INTO manifold_nodes
            (id, text, toon_factor, lifecycle_state, action_potential, revision_milestone, vector_blob, projections_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ("LOG_1", "ValidationError trace", "\U0001f6d1", "telemetry_error", 0.0, 0,
              b"", '{"error": "drift"}'))
        conn.commit()

    res_nodes = client.get("/nodos")
    assert res_nodes.status_code == 200
    nodes_data = res_nodes.json()["nodes"]
    assert len(nodes_data) == 1
    assert nodes_data[0]["id"] == "NODE_1"
    assert nodes_data[0]["toon_factor"] == "\u25b2"

    res_telemetry = client.get("/telemetry")
    assert res_telemetry.status_code == 200
    telemetry_data = res_telemetry.json()
    assert len(telemetry_data) == 1
    assert telemetry_data[0]["id"] == "LOG_1"
    assert "ValidationError" in telemetry_data[0]["trace"]


def test_adr002_silent_denial_logs_on_processor_failure(isolate_test_database, monkeypatch):
    monkeypatch.setattr(main, "get_geodetic_matrix_db", lambda: {})
    async_spectral_processor(999, "will fail on empty geodetic matrix")

    with sqlite3.connect(isolate_test_database) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, lifecycle_state, projections_json FROM manifold_nodes WHERE id = ?",
            ("LOG_999",)
        )
        row = cursor.fetchone()

    assert row is not None
    assert row[0] == "LOG_999"
    assert row[1] == "telemetry_error"
    meta = json.loads(row[2])
    assert "error" in meta


def test_relaciones_endpoints(isolate_test_database):
    payload = {"source": "NODE_A", "target": "NODE_B", "state": "consolidated"}
    res_post = client.post("/relations", json=payload)
    assert res_post.status_code == 200
    assert res_post.json()["status"] == "SUCCESS"
    assert res_post.json()["id"] == "edge-NODE_A-NODE_B"

    res_get = client.get("/relations")
    assert res_get.status_code == 200
    edges = res_get.json()
    assert len(edges) == 1
    assert edges[0]["id"] == "edge-NODE_A-NODE_B"
    assert edges[0]["source"] == "NODE_A"
    assert edges[0]["target"] == "NODE_B"
    assert edges[0]["state"] == "consolidated"


def test_spectral_approach_preserves_multichannel_spectrum_adr014(isolate_test_database):
    node_id = "NODE_SPECTRAL_TEST"
    spectrum_dict = {"AXIS_1": 0.85, "AXIS_2": 0.12, "AXIS_3": 0.03}
    spectrum_json = json.dumps(spectrum_dict)

    with sqlite3.connect(isolate_test_database) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO manifold_nodes
            (id, text, toon_factor, lifecycle_state, action_potential, revision_milestone, vector_blob, projections_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (node_id, "Diffuse payload", "\u25b2", "incubating", 0.5, 0,
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


def test_schema_alignment_and_action_potential_field_adr020(isolate_test_database):
    with sqlite3.connect(isolate_test_database) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(manifold_nodes)")
        columns = [row[1] for row in cursor.fetchall()]

    assert "action_potential" in columns
    assert "revision_milestone" in columns
    assert "sys_internal_timestamp" in columns


# =====================================================================
# CYCLE 5: REGRESSION TESTS (review findings)
# =====================================================================


def test_regression_double_underscore_axis_key_does_not_collapse_spectrum(isolate_test_database):
    """
    Regression test for the axis key parsing bug.

    Production bootstrap tags carry a leading underscore (e.g. `_SOMETHING_HAPPENS`)
    and are joined to the symbol with `_`, producing keys like `▲__SOMETHING_HAPPENS`.
    The old `key.split("_")[1]` returned `''` for every axis, collapsing the
    projection spectrum to a single value and forcing the Topological Key
    variance to always be zero. The previous fixture hid this because its
    symbol field (`▲_1`) made `split("_")[1]` return distinct values.
    """
    with sqlite3.connect(isolate_test_database) as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM geodesic_axes")
        prod_tags = [
            "SOMETHING", "SOMETHING_HAPPENS", "BE_IN_A_PLACE", "BE_GOOD",
            "THINK", "KNOW", "VERY", "PART_OF",
        ]
        for i, tag in enumerate(prod_tags):
            vec = np.zeros(384, dtype=np.float64)
            vec[i] = 1.0
            cursor.execute(
                "INSERT INTO geodesic_axes (id, simbolo, tag, vector_blob) VALUES (?, ?, ?, ?)",
                (f"AXIS_{i+1}", f"\u25b2{i+1}", f"_{tag}", serialize_vector(vec))
            )
        cursor.execute("INSERT INTO ingestion_queue (payload, status) VALUES (?, ?)",
                       ("Regression spectrum text", "PENDING"))
        ingestion_id = cursor.lastrowid
        conn.commit()

    async_spectral_processor(ingestion_id, "Regression spectrum text")

    with sqlite3.connect(isolate_test_database) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT action_potential, projections_json FROM manifold_nodes WHERE id = ?",
            (f"NODE_{ingestion_id}",)
        )
        row = cursor.fetchone()

    assert row is not None
    projections = json.loads(row[1])
    assert len(projections) == 8
    assert len(set(projections.values())) > 1
    assert row[0] > 0.0


def test_consolidation_requires_explicit_ethical_key(isolate_test_database):
    with sqlite3.connect(isolate_test_database) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO manifold_nodes
            (id, text, toon_factor, lifecycle_state, action_potential, revision_milestone, vector_blob, projections_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, ("NODE_200", "Pending node", "\u25b2", "pending_approval", 0.1, 0,
              serialize_vector(np.zeros(384)), "{}"))
        conn.commit()

    response = client.post("/nodos/NODE_200/consolidar", json={"text": "no ethical confirmation"})
    assert response.status_code == 422

    with sqlite3.connect(isolate_test_database) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT lifecycle_state, revision_milestone FROM manifold_nodes WHERE id = ?",
            ("NODE_200",)
        )
        row = cursor.fetchone()

    assert row[0] == "pending_approval"
    assert row[1] == 0
