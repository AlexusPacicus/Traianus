"""
G4 — No-fake-200 (findings H1/M5, audit TRAIANUS_AUDIT.md:44,53).

Normative (RFC 2119): on persistence or database failure, the
API MUST NOT return a synthetic 200; MUST propagate a noisy 5xx
(503 ingestion / 500 rest) to avoid silent data loss.

Normative: docs/archive/legacy_docs/development/tests/SPEC-global.md
Coverage: G4
"""
import sqlite3

import pytest

import traianus.app as main
from helpers.endpoint_registry import BLOCKS

HTTP_BLOCKS = ["ingestion", "consolidation", "relations", "mutation", "observability"]


@pytest.mark.parametrize("block", HTTP_BLOCKS)
def test_g4_no_fake_200_on_db_error(block, client, monkeypatch, auth_headers):
    """MUST: with broken DB, the block responds 5xx, never 200."""

    def broken_connect(*args, **kwargs):
        raise sqlite3.OperationalError("db locked")

    monkeypatch.setattr(main.sqlite3, "connect", broken_connect)

    if block == "ingestion":
        response = client.post(
            "/ingesta", json={"type": "text/plain", "text": "x"}, headers=auth_headers
        )
        assert response.status_code == 503
    elif block == "consolidation":
        response = client.post(
            "/nodos/NODE_X/consolidar",
            json={"text": "x", "ethical_key": True},
            headers=auth_headers,
        )
        assert response.status_code >= 500
    elif block == "relations":
        assert client.get("/relations", headers=auth_headers).status_code >= 500
        response = client.post(
            "/relations",
            json={"source": "A", "target": "B", "state": "s"},
            headers=auth_headers,
        )
        assert response.status_code >= 500
    elif block == "mutation":
        assert client.post("/mutate/\u2605", headers=auth_headers).status_code >= 500
    elif block == "observability":
        assert client.get("/nodos").status_code >= 500
        assert client.get("/telemetry", headers=auth_headers).status_code >= 500
