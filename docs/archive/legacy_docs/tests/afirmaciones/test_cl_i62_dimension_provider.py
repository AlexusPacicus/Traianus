"""
This file verifies MUST/MUST NOT requirements from the SPEC (RFC 2119).
Claim CL-I62 (I-6.2 / L6): a provider with dimension greater than the basis
is rejected or handled explicitly without breaking projections.

State: ACTIVE. The pipeline handles both directions: if dim_db > dim_in it
zero-pads; if dim_in > dim_db it explicitly rejects (422 in /consolidar and
telemetry_error in the spectral processor of /ingesta) BEFORE projecting.
Normative: docs/archive/legacy_docs/development/tests/SPEC-afirmaciones.md
Coverage: CL-I62"""
import re
import sqlite3

import numpy as np
import pytest

import traianus.app as main
from tests.afirmaciones.claims_registry import CLAIMS, resolve
from traianus.app import async_spectral_processor, serialize_vector


def test_afirmaciones_CL_I62_provider_dim_greater_handled():
    src = open(resolve("traianus/app.py"), encoding="utf-8").read()
    # Explicit handling must exist: a branch that treats dim_in > dim_db
    # (truncation, rejection, or adaptation) BEFORE projecting.
    has_guard = bool(re.search(r"dim_in\s*>\s*dim_db", src)) or bool(
        re.search(r"dim_in\s*[>=]=\s*dim_db", src)
    )
    assert has_guard, "CL-I62 MUST: explicit handling branch exists for provider with dim > basis"


def test_afirmaciones_CL_I62_registry_active_without_disposition():
    claim = CLAIMS["CL-I62"]
    assert claim["state"] == "ACTIVE"
    assert "disposition" not in claim


def test_afirmaciones_CL_I62_consolidate_rejects_dim_greater(client, auth_headers, isolate_db, monkeypatch):
    """Regression I-6.2/L6: provider with dim_in > dim_db → explicit 422, without
    breaking projections (np.dot with mismatched dimensions)."""
    with sqlite3.connect(isolate_db) as conn:
        conn.execute("""
            INSERT INTO manifold_nodes
            (id, seq, text, toon_factor, lifecycle_state, action_potential, revision_milestone, vector_blob, projections_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, ("NODE_I62", 1, "Pending provider node", "\u25b2", "pending_approval", 0.1, 0,
              serialize_vector(np.zeros(384)), "{}"))

    monkeypatch.setattr(main, "get_current_dimension_db", lambda: 8)
    response = client.post(
        "/nodos/NODE_I62/consolidar",
        json={"text": "provider with higher dimension", "ethical_key": True},
        headers=auth_headers,
    )
    assert response.status_code == 422
    assert "dimension" in response.json()["detail"].lower()


def test_afirmaciones_CL_I62_ingest_dim_greater_records_telemetry_error(isolate_db, monkeypatch):
    """Regression I-6.2/L6: in the spectral processor of /ingesta, dim_in >
    dim_db is explicitly rejected and recorded as telemetry_error (never
    an np.dot with mismatched dimensions breaking the pipeline)."""
    monkeypatch.setattr(main, "get_current_dimension_db", lambda: 8)
    with sqlite3.connect(isolate_db) as conn:
        conn.execute("INSERT INTO ingestion_queue (payload, status) VALUES (?, ?)", ("higher dim provider", "PENDING"))
        ingestion_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    async_spectral_processor(ingestion_id, "higher dim provider")

    with sqlite3.connect(isolate_db) as conn:
        row = conn.execute(
            "SELECT id, lifecycle_state FROM manifold_nodes WHERE id = ?",
            (f"LOG_{ingestion_id}",),
        ).fetchone()

    assert row is not None
    assert row[0] == f"LOG_{ingestion_id}"
    assert row[1] == "telemetry_error"
