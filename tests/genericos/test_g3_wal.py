"""
G3 — WAL (finding L2, audit TRAIANUS_AUDIT.md:345).

Normative (RFC 2119): every handler that opens the database MUST execute
PRAGMA journal_mode=WAL before operating (storage consistency and
recovery). CODE_FIX applied in Phase 1: get_relations/forge_relation
omitted the pragma (L2).

Normative: docs/development/tests/SPEC-global.md
Coverage: G3
"""
import os
import sqlite3

import numpy as np
import pytest

import traianus.app as main
import traianus.bootstrap as bootstrap
from helpers.endpoint_registry import BLOCKS, endpoints_for


def _journal_mode(db_path):
    with sqlite3.connect(db_path) as conn:
        return conn.execute("PRAGMA journal_mode;").fetchone()[0]


@pytest.mark.parametrize("block", [b for b in BLOCKS if endpoints_for(b)])
def test_g3_handlers_open_db_in_wal(block, client, auth_headers, isolate_db):
    """MUST: after each block operates on DB, journal_mode == wal."""
    if block == "ingestion":
        client.post("/ingesta", json={"type": "text/plain", "text": "x"}, headers=auth_headers)
    elif block == "consolidation":
        client.post(
            "/nodos/NODE_X/consolidar",
            json={"text": "x", "ethical_key": True},
            headers=auth_headers,
        )
    elif block == "relations":
        client.get("/relations", headers=auth_headers)
        client.post(
            "/relations",
            json={"source": "NODE_A", "target": "NODE_B", "state": "consolidated"},
            headers=auth_headers,
        )
    elif block == "mutation":
        client.post("/mutate/\u2605", headers=auth_headers)
    elif block == "observability":
        client.get("/nodos")
        client.get("/telemetry", headers=auth_headers)

    assert _journal_mode(isolate_db) == "wal", f"block {block} MUST operate in WAL"


def test_g3_bootstrap_anchors_in_wal(tmp_path, monkeypatch):
    """MUST: bootstrap's geodetic anchoring operates in WAL."""
    db_path = str(tmp_path / "bootstrap_wal.db")
    monkeypatch.setattr(bootstrap, "DB_PATH", db_path)
    octagon = {
        "AXIS_1": {
            "symbol": "\u25b2",
            "tag": "_SOMETHING",
            "vector": np.zeros(8, dtype=np.float64),
        }
    }
    bootstrap.anchor_in_sqlite(octagon)
    assert _journal_mode(db_path) == "wal"
