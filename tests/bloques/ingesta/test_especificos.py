"""
This file verifies MUST/MUST NOT requirements from the SPEC (RFC 2119).
BLOCK: ingestion — block-specific tests (Phase 2 + Phase 5).

Tests moved from tests/test_control_plane.py WITHOUT changing assertions.
They cover: ingestion contract, MIME firewall (H2, 5+ rejected types),
persistence failures (H1), spectral pipeline (ADR-002) and metric (M6).
Normative: docs/archive/legacy_docs/development/tests/SPEC-ingesta.md
Coverage: IN01, IN02, IN03, IN04, IN05, IN06, IN07, IN08, IN12"""
import json
import sqlite3

import numpy as np
import pytest

import traianus.app as main
from traianus.app import async_spectral_processor, serialize_vector


def test_ingestion_IN01_accepts_plain_text(client, auth_headers):
    response = client.post(
        "/ingesta",
        json={"type": "text/plain", "text": "Canonical test entity"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "accepted"
    assert isinstance(body["ingestion_id"], int)


def test_ingestion_IN02_rejects_audio_ogg(client, auth_headers):
    response = client.post(
        "/ingesta",
        json={"type": "audio/ogg", "text": "audio data"},
        headers=auth_headers,
    )
    assert response.status_code == 415
    assert "Only text/plain is accepted at ingress" in response.json()["detail"]


def test_ingestion_IN02b_firewall_rejects_5_mime(client, auth_headers):
    """
    Phase 5: the allow-list firewall (H2) must reject a broad spectrum of
    MIME types, not only audio/ogg and application/json. Only text/plain passes.
    """
    rejected = [
        "audio/ogg",
        "application/json",
        "image/png",
        "text/html",
        "application/xml",
        "application/octet-stream",
        "text/csv",
    ]
    for mime in rejected:
        response = client.post(
            "/ingesta",
            json={"type": mime, "text": "payload"},
            headers=auth_headers,
        )
        assert response.status_code == 415, (
            f"IN-02 MUST NOT: /ingesta acepta {mime} ({response.status_code})"
        )
        assert "Only text/plain is accepted at ingress" in response.json()["detail"]


def test_ingestion_IN03_rejects_application_json(client, auth_headers):
    """
    H2 regression: the ingress firewall must be an ALLOW-list.
    Before, it accepted application/json (and everything except audio/ogg|m4a),
    contradicting the documented Zero-Trust customs.
    """
    response = client.post(
        "/ingesta",
        json={"type": "application/json", "text": "{}"},
        headers=auth_headers,
    )
    assert response.status_code == 415
    assert "Only text/plain is accepted at ingress" in response.json()["detail"]


def test_ingestion_IN04_503_on_persistence_failure(client, auth_headers, monkeypatch):
    """
    H1 regression: a persistence failure MUST NOT return a synthetic 200.
    It must fail loudly with 503 to avoid losing data silently.
    """

    def broken_connect(*args, **kwargs):
        raise sqlite3.OperationalError("disk full")

    monkeypatch.setattr(main.sqlite3, "connect", broken_connect)
    response = client.post(
        "/ingesta",
        json={"type": "text/plain", "text": "will fail"},
        headers=auth_headers,
    )
    assert response.status_code == 503
    assert "Ingress persistence unavailable" in response.json()["detail"]


def test_ingestion_IN05_pipeline_creates_pending_node(isolate_db):
    with sqlite3.connect(isolate_db) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO ingestion_queue (payload, status) VALUES (?, ?)", ("Test spectral text", "PENDING"))
        ingestion_id = cursor.lastrowid
        conn.commit()

    async_spectral_processor(ingestion_id, "Test spectral text")

    with sqlite3.connect(isolate_db) as conn:
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


def test_ingestion_IN06_pipeline_records_telemetry_error(isolate_db, monkeypatch):
    monkeypatch.setattr(main, "get_geodetic_matrix_db", lambda: {})
    async_spectral_processor(999, "will fail on empty geodetic matrix")

    with sqlite3.connect(isolate_db) as conn:
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


def test_ingestion_IN07_double_underscore_does_not_collapse_spectrum(isolate_db):
    """
    Regression test for the axis key parsing bug.

    Production bootstrap tags carry a leading underscore (e.g. `_SOMETHING_HAPPENS`)
    and are joined to the symbol with `_`, producing keys like `▲__SOMETHING_HAPPENS`.
    The old `key.split("_")[1]` returned `''` for every axis, collapsing the
    projection spectrum to a single value and forcing the Topological Key
    variance to always be zero. The previous fixture hid this because its
    symbol field (`▲_1`) made `split("_")[1]` return distinct values.
    """
    with sqlite3.connect(isolate_db) as conn:
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

    with sqlite3.connect(isolate_db) as conn:
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


def test_ingestion_IN08_action_potential_is_variance(isolate_db):
    """
    M6 regression: action_potential must derive from the projection spectrum
    WITHOUT the magic constant ×10 (ADR-005 forbids manually injected
    magic numbers).
    """
    with sqlite3.connect(isolate_db) as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO ingestion_queue (payload, status) VALUES (?, ?)", ("M6 text", "PENDING"))
        ingestion_id = cursor.lastrowid
        conn.commit()

    async_spectral_processor(ingestion_id, "M6 text")

    with sqlite3.connect(isolate_db) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT action_potential, projections_json FROM manifold_nodes WHERE id = ?",
            (f"NODE_{ingestion_id}",)
        )
        row = cursor.fetchone()

    assert row is not None
    projections = json.loads(row[1])
    assert row[0] == pytest.approx(float(np.var(list(projections.values()))))


def test_ingestion_IN12_persists_validated_projections(isolate_db, client, auth_headers, monkeypatch):
    """
    L5 regression: the persisted projections_json MUST be derived from the
    VALIDATED RefinedEntity.projections (save what you validate), not from a
    raw dict that bypasses the contract.
    """
    captured = {}
    original = main.RefinedEntity

    def capturing_entity(*args, **kwargs):
        entity = original(*args, **kwargs)
        captured["projections"] = list(entity.projections)
        return entity

    monkeypatch.setattr(main, "RefinedEntity", capturing_entity)

    response = client.post(
        "/ingesta",
        json={"type": "text/plain", "text": "L5 validated projections probe"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    node_id = f"NODE_{response.json()['ingestion_id']}"

    with sqlite3.connect(isolate_db) as conn:
        stored = json.loads(conn.execute(
            "SELECT projections_json FROM manifold_nodes WHERE id = ?", (node_id,)
        ).fetchone()[0])

    assert "projections" in captured, "L5 MUST: RefinedEntity must be constructed"
    assert list(stored.values()) == pytest.approx(captured["projections"]), (
        "L5 MUST: persisted projections_json must equal the validated projections"
    )
