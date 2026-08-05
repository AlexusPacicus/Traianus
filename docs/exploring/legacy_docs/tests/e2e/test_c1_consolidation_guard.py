"""
This file verifies MUST/MUST NOT requirements from the SPEC (RFC 2119).
C1 Regression Guard (consolidation rate in [5%, 95%]): port of the
tools/audit_harness.py harness to pytest E2E with the cached real model.

The CLI harness remains intact (tools/audit_harness.py) for manual use;
this test reproduces it deterministically in CI (@pytest.mark.model partition).
Normative: docs/archive/legacy_docs/development/tests/SPEC-global.md
Coverage: G10"""
import os
import sqlite3

import pytest

import traianus.app as main
import traianus.bootstrap as gb
from helpers.db_factory import create_test_db

pytestmark = pytest.mark.model


# Corpus calibrated against the corrected C1 threshold (see harness): 6 notes of
# high contrast in NSM primitives (variance >> threshold) and 14 thematic
# low-contrast notes (variance << threshold). Expected rate ~30%.
CORPUS = [
    # --- High contrast with a geodetic axis (expected: PASS) ---
    "Something happens.",
    "Someone.",
    "There is something here.",
    "Be in a place.",
    "One, two, and some more are part of the same collection.",
    "After a long time, before now, things were different.",
    # --- Varied low-contrast thematic notes (expected: FAIL) ---
    "The cat sees the bird and hears it singing.",
    "Meeting on Tuesday at 10am to review the quarterly budget.",
    "The audit report confirms the documentation matches the code.",
    "I want to know if this is true.",
    "All the others agree with me now.",
    "The cat sees the bird and hears its song.",
    "The audit report confirms the documentation matches the code.",
    "Meeting on Tuesday at 10 to review the quarterly budget.",
    "I want to know if I can do something more with very little time.",
    "There is no one here right now.",
    "A very good and very big person lives very far from here.",
    "The distance between two places can be large or small.",
    "The ingestion process records a note in the system deterministically.",
    "Move.",
]


@pytest.fixture(autouse=True)
def realistic_db(tmp_path, monkeypatch):
    """
    Database with FROZEN real geometry (nsm_axes_8.json) — the same produced by
    `bootstrap.extract_pure_octagon()` with the real model (off-diag cosine ≈ 0.23).
    Overrides the root fixture's one-hot basis for the C1 guard.
    """
    db_path = str(tmp_path / "c1_realistic.db")
    monkeypatch.setattr(main, "DB_PATH", db_path)
    monkeypatch.setattr(gb, "DB_PATH", db_path)
    create_test_db(db_path, seed="realistic")
    return db_path


def test_e2e_global_G10_c1_consolidation_guard(client, auth_headers, realistic_db):
    """
    C1 Regression: with the real model and realistic geometry, the dual-key
    consolidation rate MUST NOT degenerate (0/20 pre-fix): must stay within
    the gate [5%, 95%].
    """
    token = os.environ.get("TRAIANUS_TOKEN", "test-operator-token")
    headers = {"x-traianus-token": token, **auth_headers}

    accepted = 0
    for text in CORPUS:
        res = client.post(
            "/ingesta",
            json={"type": "text/plain", "text": text},
            headers=headers,
        )
        if res.status_code == 200:
            accepted += 1
    assert accepted == len(CORPUS), f"ingestion accepted {accepted}/{len(CORPUS)}"

    nodes = client.get("/nodos", headers=headers).json().get("nodes", [])
    assert len(nodes) == len(CORPUS), f"expected {len(CORPUS)} nodes, got {len(nodes)}"

    consolidated = 0
    for n in nodes:
        resp = client.post(
            f"/nodos/{n['id']}/consolidar",
            json={"text": n["text"], "ethical_key": True},
            headers=headers,
        ).json()
        if resp.get("new_state") == "consolidated":
            consolidated += 1

    rate = consolidated / len(nodes) if nodes else 0.0
    assert 0.05 <= rate <= 0.95, (
        f"C1 GUARD: degenerate consolidation rate {rate:.0%} "
        f"({consolidated}/{len(nodes)}) — outside gate [5%, 95%]"
    )
