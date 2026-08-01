"""
G8 — Contracts and glyph (ADR-007, ADR-005; audit L5).

Normative (RFC 2119): Pydantic contracts (RawDump, RefinedEntity) MUST
validate rigidly; an invalid lifecycle_state MUST raise
ValidationError (422 in API). The glyph (toon_factor) MUST be a single
character (ADR-007). The action_potential metric MUST derive from the
projection spectrum without magic constants (ADR-005, M6).

Normative: docs/development/tests/SPEC-global.md
Coverage: G8
"""
import json
import sqlite3

import pytest
from pydantic import ValidationError

from traianus.app import RefinedEntity
from helpers.endpoint_registry import BLOCKS


@pytest.mark.parametrize("block", BLOCKS)
def test_g8_refinedentity_contract_rigid(block):
    """MUST: RefinedEntity rejects invalid lifecycle_state."""
    with pytest.raises(ValidationError):
        RefinedEntity(
            text="invalid payload",
            lifecycle_state="invalid_state_name",
            revision_milestone=False,
            projections=[0.1] * 8,
        )


@pytest.mark.parametrize("block", ["ingestion", "consolidation", "observability"])
def test_g8_toon_factor_is_single_character(block, client, auth_headers, isolate_db):
    """MUST: the glyph assigned to each node is a single character (ADR-007)."""
    r = client.post(
        "/ingesta", json={"type": "text/plain", "text": "glyph contract"}, headers=auth_headers
    )
    assert r.status_code == 200
    node_id = f"NODE_{r.json()['ingestion_id']}"

    with sqlite3.connect(isolate_db) as conn:
        row = conn.execute(
            "SELECT toon_factor FROM manifold_nodes WHERE id = ?", (node_id,)
        ).fetchone()
    assert row is not None
    assert len(row[0]) == 1, "toon_factor MUST be a single character (ADR-007)"


@pytest.mark.parametrize("block", ["ingestion", "observability"])
def test_g8_action_potential_is_variance_no_magic(block, client, auth_headers, isolate_db):
    """MUST: action_potential == var(projections) without magic constant (M6)."""
    r = client.post(
        "/ingesta", json={"type": "text/plain", "text": "variance metric"}, headers=auth_headers
    )
    assert r.status_code == 200
    node_id = f"NODE_{r.json()['ingestion_id']}"

    with sqlite3.connect(isolate_db) as conn:
        row = conn.execute(
            "SELECT action_potential, projections_json FROM manifold_nodes WHERE id = ?",
            (node_id,),
        ).fetchone()
    projections = json.loads(row[1])
    assert row[0] == pytest.approx(float(__import__("numpy").var(list(projections.values()))))
