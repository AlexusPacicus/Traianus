"""
This file verifies MUST/MUST NOT requirements from the SPEC (RFC 2119).
BLOCK: consolidation — E2E with real model (Phase 6).

Full journey: ingestion → consolidation with dual key (ADR-022) and final
state coherent with the topological + ethical key measured at runtime.
Normative: docs/archive/legacy_docs/development/tests/SPEC-consolidacion.md
Coverage: CO10"""
import pytest

import traianus.app as main
import traianus.bootstrap as gb
from helpers.db_factory import create_test_db

pytestmark = pytest.mark.model


@pytest.fixture(autouse=True)
def realistic_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "consolidacion_e2e.db")
    monkeypatch.setattr(main, "DB_PATH", db_path)
    monkeypatch.setattr(gb, "DB_PATH", db_path)
    create_test_db(db_path, seed="realistic")
    return db_path


def test_e2e_consolidation_CO10_full_journey(client, auth_headers, realistic_db):
    text = "Something happens."
    client.post(
        "/ingesta",
        json={"type": "text/plain", "text": text},
        headers=auth_headers,
    )
    nodes = client.get("/nodos", headers=auth_headers).json().get("nodes", [])
    assert len(nodes) == 1
    nid = nodes[0]["id"]

    res = client.post(
        f"/nodos/{nid}/consolidar",
        json={"text": text, "ethical_key": True},
        headers=auth_headers,
    )
    assert res.status_code == 200
    body = res.json()
    assert body["new_state"] in {"consolidated", "incubating"}
    dual = body["dual_key_status"]
    assert dual["ethical_key"] is True
    assert dual["consolidated"] == (body["new_state"] == "consolidated")
    assert dual["consolidated"] == (dual["topological_key"] and dual["ethical_key"])

    nodes_after = client.get("/nodos", headers=auth_headers).json().get("nodes", [])
    assert nodes_after[0]["lifecycle_state"] == body["new_state"]
