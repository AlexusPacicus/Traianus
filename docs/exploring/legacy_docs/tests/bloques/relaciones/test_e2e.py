"""
This file verifies MUST/MUST NOT requirements from the SPEC (RFC 2119).
BLOCK: relations — E2E with a real model (Phase 6).

Full journey: ingest two nodes → POST /relations (edge validated L2)
→ GET /relations returns it.
Normative: docs/archive/legacy_docs/development/tests/SPEC-relaciones.md
Coverage: RE06"""
import pytest

import traianus.app as main
import traianus.bootstrap as gb
from helpers.db_factory import create_test_db

pytestmark = pytest.mark.model


@pytest.fixture(autouse=True)
def realistic_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "relaciones_e2e.db")
    monkeypatch.setattr(main, "DB_PATH", db_path)
    monkeypatch.setattr(gb, "DB_PATH", db_path)
    create_test_db(db_path, seed="realistic")
    return db_path


def test_e2e_relations_RE06_full_journey(client, auth_headers, realistic_db):
    for text in ("Something happens.", "Someone."):
        client.post(
            "/ingesta",
            json={"type": "text/plain", "text": text},
            headers=auth_headers,
        )
    nodes = client.get("/nodos", headers=auth_headers).json().get("nodes", [])
    ids = [n["id"] for n in nodes]
    assert len(ids) == 2

    res = client.post(
        "/relations",
        json={"source": ids[0], "target": ids[1], "state": "incubating"},
        headers=auth_headers,
    )
    assert res.status_code == 200
    assert res.json()["id"] == f"edge-{sorted(ids)[0]}-{sorted(ids)[1]}"

    edges = client.get("/relations", headers=auth_headers).json()
    assert len(edges) == 1
    assert {edges[0]["source"], edges[0]["target"]} == set(ids)
