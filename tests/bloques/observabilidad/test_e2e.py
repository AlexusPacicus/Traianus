"""
This file verifies MUST/MUST NOT requirements from the SPEC (RFC 2119).
BLOCK: observability — E2E with a real model (Phase 6).

Full journey: /nodos excludes telemetry_error and returns MAX(seq);
/telemetry requires the operator token (M5/ADR-025#2).
Normative: docs/archive/legacy_docs/development/tests/SPEC-observabilidad.md
Coverage: OB09"""
import pytest

import traianus.app as main
import traianus.bootstrap as gb
from helpers.db_factory import create_test_db

pytestmark = pytest.mark.model


@pytest.fixture(autouse=True)
def realistic_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / "observabilidad_e2e.db")
    monkeypatch.setattr(main, "DB_PATH", db_path)
    monkeypatch.setattr(gb, "DB_PATH", db_path)
    create_test_db(db_path, seed="realistic")
    return db_path


def test_e2e_observability_OB09_full_journey(client, auth_headers, realistic_db):
    # /telemetry requires a token (C-4.1/M5): without token -> 401.
    assert client.get("/telemetry").status_code == 401
    assert client.get("/telemetry", headers=auth_headers).status_code == 200

    client.post(
        "/ingesta",
        json={"type": "text/plain", "text": "Something happens."},
        headers=auth_headers,
    )
    nodes = client.get("/nodos", headers=auth_headers).json().get("nodes", [])
    assert len(nodes) == 1
    assert nodes[0]["lifecycle_state"] == "pending_approval"

    # The node list never includes telemetry_error as the current state.
    states = {n["lifecycle_state"] for n in nodes}
    assert "telemetry_error" not in states
