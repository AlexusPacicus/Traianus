"""GET /relations/tree — the minimum spanning tree of the current nodes, observational.

Computed on read from the same current nodes as E_n (MAX(seq) per id, telemetry_error excluded),
cached under the append-only log's version, never persisted (AGENTS 4.3).
"""
import sqlite3

import numpy as np

import traianus.storage._storage as storage_impl
from traianus import storage
from traianus.app import serialize_vector
from traianus.geometry.spanning_tree import compute_minimum_spanning_tree


def _unit(seed: int) -> np.ndarray:
    v = np.random.default_rng(seed).standard_normal(384)
    return v / np.linalg.norm(v)


def _insert(path, node_id, seq, vector, state="pending_approval"):
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            INSERT INTO manifold_nodes
            (id, seq, text, toon_factor, lifecycle_state, action_potential, revision_milestone,
             vector_blob, projections_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (node_id, seq, f"text {node_id}", "▲", state, 0.1, 0, serialize_vector(vector), "{}"),
        )
        conn.commit()


def _counts(path):
    with sqlite3.connect(path) as conn:
        return tuple(
            conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("manifold_nodes", "manifold_edges")
        )


def _expected(current):
    return [
        {
            "id": storage.build_edge_id("tree-edge", e["source"], e["target"]),
            "source": e["source"],
            "target": e["target"],
            "state": "tree",
            "distance": e["distance"],
        }
        for e in compute_minimum_spanning_tree(current)
    ]


def test_tree_is_that_of_the_current_non_error_nodes_and_writes_nothing(
    client, auth_headers, isolate_db
):
    stale, current = _unit(1), _unit(2)
    _insert(isolate_db, "N1", 1, _unit(3))
    _insert(isolate_db, "N2", 1, stale)
    _insert(isolate_db, "N2", 2, current)
    _insert(isolate_db, "N3", 1, _unit(4))
    _insert(isolate_db, "N4", 1, _unit(5))
    _insert(isolate_db, "N5", 1, _unit(6), state="telemetry_error")
    vectors = {"N1": _unit(3), "N2": current, "N3": _unit(4), "N4": _unit(5)}
    before = _counts(isolate_db)

    resp = client.get("/relations/tree", headers=auth_headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body == sorted(_expected(vectors), key=lambda r: r["id"])
    assert len(body) == 3
    assert all(r["id"].startswith("tree-edge-") and r["state"] == "tree" for r in body)
    assert {r["source"] for r in body} | {r["target"] for r in body} == set(vectors)
    assert body != sorted(_expected({**vectors, "N2": stale}), key=lambda r: r["id"])
    assert _counts(isolate_db) == before


def test_tree_requires_the_operator_token(client, isolate_db):
    assert client.get("/relations/tree").status_code == 401


def test_relations_and_tree_route_independently(client, auth_headers, isolate_db):
    _insert(isolate_db, "N1", 1, _unit(1))
    _insert(isolate_db, "N2", 1, _unit(2))
    tree = client.get("/relations/tree", headers=auth_headers).json()
    relations = client.get("/relations", headers=auth_headers).json()
    assert [r["state"] for r in tree] == ["tree"]
    assert all(r["state"] != "tree" for r in relations)


def test_cache_is_kept_while_the_log_is_unchanged_and_dropped_when_it_grows(
    client, auth_headers, isolate_db, monkeypatch
):
    calls = []
    real = storage_impl.compute_minimum_spanning_tree

    def spy(nodes):
        calls.append(len(nodes))
        return real(nodes)

    monkeypatch.setattr(storage_impl, "compute_minimum_spanning_tree", spy)
    _insert(isolate_db, "N1", 1, _unit(1))
    _insert(isolate_db, "N2", 1, _unit(2))

    first = client.get("/relations/tree", headers=auth_headers).json()
    again = client.get("/relations/tree", headers=auth_headers).json()
    assert again == first
    assert calls == [2]

    _insert(isolate_db, "N3", 1, _unit(3))
    grown = client.get("/relations/tree", headers=auth_headers).json()
    assert calls == [2, 3]
    assert len(first) == 1 and len(grown) == 2
