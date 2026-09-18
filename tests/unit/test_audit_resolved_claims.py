"""Characterization tests for AUDIT.md findings marked Resolved that had no
covering test (REMEDIATION-01 INV-8): the behaviour is implemented, the
regression net was missing. Names match the citations in AUDIT.md."""
import sqlite3
import uuid

import numpy as np
import pytest

import traianus.app as main
import traianus.storage as storage


def test_ingesta_returns_503_on_persistence_failure(ingesta, monkeypatch):
    """H1: a persistence failure is a loud 503, never a synthetic 200."""
    def boom(*_args, **_kwargs):
        raise storage.StorageError("injected")

    monkeypatch.setattr(storage, "enqueue_ingest", boom)
    assert ingesta("x").status_code == 503


def test_consolidar_missing_node_returns_404(client, auth_headers):
    """M7: consolidating a node that does not exist is a 404, not an insert."""
    res = client.post(
        "/nodos/NODE_DOES_NOT_EXIST/consolidar",
        json={"text": "x", "ethical_key": True},
        headers=auth_headers,
    )
    assert res.status_code == 404


def test_cors_origins_are_enumerated_no_wildcard(client):
    """H3: credentials are allowed only for the enumerated origins."""
    assert "*" not in main.ALLOWED_ORIGINS
    allowed = main.ALLOWED_ORIGINS[0]
    ok = client.options(
        "/nodos", headers={"Origin": allowed, "Access-Control-Request-Method": "GET"}
    )
    assert ok.headers.get("access-control-allow-origin") == allowed
    bad = client.options(
        "/nodos",
        headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in bad.headers


def test_telemetry_requires_token(client):
    """M5: /telemetry exposes the error log and must reject a missing token."""
    assert client.get("/telemetry").status_code == 401


def test_action_potential_is_variance_not_scaled(client, auth_headers, isolate_db):
    """M6 (ADR-005): the vector path stores the measured variance, unscaled."""
    rng = np.random.default_rng(3)
    vec = rng.standard_normal(384)
    res = client.post(
        "/ingesta/vector",
        json={"vector": (vec / np.linalg.norm(vec)).tolist(), "label": "m6"},
        headers={**auth_headers, "X-Idempotency-Key": uuid.uuid4().hex},
    )
    body = res.json()
    with sqlite3.connect(isolate_db) as conn:
        stored = conn.execute(
            "SELECT action_potential FROM manifold_nodes WHERE id = ? ORDER BY seq DESC LIMIT 1",
            (body["node_id"],),
        ).fetchone()[0]
    assert stored == pytest.approx(body["spectral_variance"], abs=1e-12)
