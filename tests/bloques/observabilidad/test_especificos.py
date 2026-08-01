"""
This file verifies MUST/MUST NOT requirements from the SPEC (RFC 2119).
BLOCK: observability — specific tests (Phase 2).

Tests moved from tests/test_control_plane.py WITHOUT changing assertions.
Cover: enumerated CORS (H3), operator token (H3), telemetry isolation (M5),
MAX(seq) filter, and real 5xx errors.
Normative: docs/development/tests/SPEC-observabilidad.md
Coverage: OB01, OB02, OB03, OB04, OB05, OB06"""
import json
import sqlite3

import numpy as np
import pytest

import traianus.app as main
from traianus.app import app, serialize_vector

AUTH_HEADERS = {"X-Traianus-Token": "test-operator-token"}


def test_observability_OB01_cors_enumerated():
    cors = [m for m in app.user_middleware if m.cls.__name__ == "CORSMiddleware"]
    assert cors, "CORSMiddleware must be configured"
    origins = cors[0].kwargs.get("allow_origins", [])
    assert "*" not in origins
    assert origins == ["http://localhost:5173", "http://127.0.0.1:5173"]


@pytest.mark.parametrize("method,path,payload", [
    ("post", "/ingesta", {"type": "text/plain", "text": "x"}),
    ("post", "/nodos/NODE_X/consolidar", {"text": "x", "ethical_key": True}),
    ("get", "/relations", None),
    ("post", "/relations", {"source": "NODE_A", "target": "NODE_B", "state": "consolidated"}),
    ("post", "/mutate/\u2605", None),
])
def test_observability_OB02_protected_routes_require_token(client, method, path, payload):
    """H3 regression: routes that mutate state (or expose sensitive observability)
    must require the operator token. Without header -> 401."""
    response = client.request(method, path, json=payload)
    assert response.status_code == 401


def test_observability_OB03_valid_token_accepted(client):
    response = client.post(
        "/ingesta",
        json={"type": "text/plain", "text": "token accepted"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"


def test_observability_OB04_nodes_excludes_telemetry_max_seq(client, isolate_db):
    with sqlite3.connect(isolate_db) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO manifold_nodes
            (id, seq, text, toon_factor, lifecycle_state, action_potential, revision_milestone, vector_blob, projections_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("NODE_1", 1, "Clean text", "\u25b2", "consolidated", 1.0, 1,
              serialize_vector(np.zeros(384)), "{}"))
        cursor.execute("""
            INSERT INTO manifold_nodes
            (id, seq, text, toon_factor, lifecycle_state, action_potential, revision_milestone, vector_blob, projections_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("LOG_1", 1, "ValidationError trace", "\U0001f6d1", "telemetry_error", 0.0, 0,
              b"", '{"error": "drift"}'))
        conn.commit()

    res_nodes = client.get("/nodos")
    assert res_nodes.status_code == 200
    nodes_data = res_nodes.json()["nodes"]
    assert len(nodes_data) == 1
    assert nodes_data[0]["id"] == "NODE_1"
    assert nodes_data[0]["toon_factor"] == "\u25b2"

    res_telemetry = client.get("/telemetry", headers=AUTH_HEADERS)
    assert res_telemetry.status_code == 200
    telemetry_data = res_telemetry.json()
    assert len(telemetry_data) == 1
    assert telemetry_data[0]["id"] == "LOG_1"
    assert "ValidationError" in telemetry_data[0]["trace"]


def test_observability_OB05_db_error_real_5xx(client, monkeypatch):
    """
    M5 regression: /nodos MUST NOT return empty SUCCESS on DB error.
    A failure must be a real 5xx, indistinguishable from an empty store.
    """

    def broken_connect(*args, **kwargs):
        raise sqlite3.OperationalError("db locked")

    monkeypatch.setattr(main.sqlite3, "connect", broken_connect)
    response = client.get("/nodos")
    assert response.status_code == 500


def test_observability_OB06_telemetry_requires_token(client):
    """M5 regression: /telemetry exposes stack traces; requires operator token."""
    anon = client.get("/telemetry")
    assert anon.status_code == 401

    authorized = client.get("/telemetry", headers=AUTH_HEADERS)
    assert authorized.status_code == 200
