"""Integration: a note reaches the map as consolidated only through both keys (refuter R3).

The map reads each note's lifecycle state from /nodos (the current revision per id).
Consolidated <=> (variance >= theta_dyn) AND (EthicalKey == True) (AGENTS 3.5, ADR-022). The pure
decision is covered in test_substrate_invariants; these tests drive the routes that write a node
revision and read back both the state the map draws and the stored revision.
"""
import sqlite3
import uuid

import numpy as np
import pytest

import traianus.app as main
from traianus import storage


def _forge(client, auth_headers, label, seed=7, **extra):
    vec = np.random.default_rng(seed).standard_normal(384)
    res = client.post(
        "/ingesta/vector",
        json={"vector": (vec / np.linalg.norm(vec)).tolist(), "label": label, **extra},
        headers={**auth_headers, "X-Idempotency-Key": uuid.uuid4().hex},
    )
    assert res.status_code == 201
    return res.json()["node_id"]


def _consolidate(client, auth_headers, node_id, ethical_key):
    return client.post(
        f"/nodos/{node_id}/consolidar",
        json={"text": "x", "ethical_key": ethical_key},
        headers=auth_headers,
    )


def _map_state(client, node_id):
    nodes = client.get("/nodos").json()["nodes"]
    return next(n["lifecycle_state"] for n in nodes if n["id"] == node_id)


def _revisions():
    with sqlite3.connect(storage.DB_PATH) as conn:
        return conn.execute(
            "SELECT id, seq, lifecycle_state, action_potential, revision_milestone "
            "FROM manifold_nodes ORDER BY id, seq"
        ).fetchall()


class TestTwoKeys:
    def test_both_keys_consolidate(self, client, auth_headers):
        node_id = _forge(client, auth_headers, "both")
        status = _consolidate(client, auth_headers, node_id, True).json()["dual_key_status"]
        assert status["topological_key"]["passed"] is True and status["ethical_key"] is True
        assert _map_state(client, node_id) == "consolidated"

    def test_ethical_key_without_topological_key_does_not_consolidate(
        self, client, auth_headers, monkeypatch
    ):
        node_id = _forge(client, auth_headers, "ethical-only")
        monkeypatch.setattr(main, "auto_calibrate_critical_threshold", lambda: 1e9)
        res = _consolidate(client, auth_headers, node_id, True)
        status = res.json()["dual_key_status"]
        assert status["ethical_key"] is True and status["topological_key"]["passed"] is False
        assert res.json()["new_state"] == "incubating"
        assert _map_state(client, node_id) == "incubating"

    def test_topological_key_without_ethical_key_does_not_consolidate(self, client, auth_headers):
        node_id = _forge(client, auth_headers, "topological-only")
        res = _consolidate(client, auth_headers, node_id, False)
        status = res.json()["dual_key_status"]
        assert status["topological_key"]["passed"] is True and status["ethical_key"] is False
        assert res.json()["new_state"] == "incubating"
        assert _map_state(client, node_id) == "incubating"

    def test_ethical_key_is_required(self, client, auth_headers):
        node_id = _forge(client, auth_headers, "missing-key")
        before = _revisions()
        res = client.post(
            f"/nodos/{node_id}/consolidar", json={"text": "x"}, headers=auth_headers
        )
        assert res.status_code == 422
        assert _revisions() == before

    @pytest.mark.parametrize("value", ["true", "yes", "on", "1", 1])
    def test_ethical_key_must_be_a_json_boolean(self, client, auth_headers, value):
        node_id = _forge(client, auth_headers, "coerced-key")
        before = _revisions()
        res = client.post(
            f"/nodos/{node_id}/consolidar",
            json={"text": "x", "ethical_key": value},
            headers=auth_headers,
        )
        assert res.status_code == 422
        assert _revisions() == before

    def test_no_other_route_consolidates(self, client, auth_headers, ingesta):
        assert ingesta("Primera entidad de prueba").status_code == 200
        assert ingesta("Segunda entidad de seguimiento").status_code == 200
        a = _forge(
            client, auth_headers, "grant-a", 1,
            ethical_key=True, lifecycle_state="consolidated", metadata={"ethical_key": True},
        )
        b = _forge(client, auth_headers, "grant-b", 2)
        relation = {"source": a, "target": b, "state": "hitl"}
        assert client.post("/relations", json=relation, headers=auth_headers).status_code == 200
        assert client.post("/spatial/calibrate", headers=auth_headers).status_code == 201
        assert client.get("/spatial", headers=auth_headers).status_code == 200
        assert "consolidated" not in {row[2] for row in _revisions()}
        assert "consolidated" not in {n["lifecycle_state"] for n in client.get("/nodos").json()["nodes"]}

    def test_map_follows_the_current_revision(self, client, auth_headers):
        node_id = _forge(client, auth_headers, "withdrawn")
        _consolidate(client, auth_headers, node_id, True)
        assert _map_state(client, node_id) == "consolidated"
        _consolidate(client, auth_headers, node_id, False)
        assert _map_state(client, node_id) == "incubating"
        states = [row[2] for row in _revisions() if row[0] == node_id]
        assert states == ["incubating", "consolidated", "incubating"]

    def test_every_consolidated_revision_carries_both_keys(self, client, auth_headers, monkeypatch):
        ids = [_forge(client, auth_headers, f"n{i}", i) for i in range(4)]
        for i, node_id in enumerate(ids):
            _consolidate(client, auth_headers, node_id, i % 2 == 0)
        with monkeypatch.context() as patched:
            patched.setattr(main, "auto_calibrate_critical_threshold", lambda: 1e9)
            for node_id in ids:
                _consolidate(client, auth_headers, node_id, True)
        threshold = main.auto_calibrate_critical_threshold()
        consolidated = [row for row in _revisions() if row[2] == "consolidated"]
        assert len(consolidated) == 2
        for _, _, _, potential, milestone in consolidated:
            assert milestone == 1 and potential >= threshold
