"""R1-INV4 (REMEDIATION-01 3.1): /ingesta/vector enforces the idempotency
contract P(k) = (k != empty) and at most one manifold_nodes row carries k.

A repeated key is answered 200 with `duplicate: true` and the stored identity;
nothing is evaluated or written. The key is global to manifold_nodes."""
import sqlite3

import numpy as np
import pytest

import traianus.app as main
from traianus import storage

FIRST_TIME_KEYS = {
    "status", "node_id", "seq", "lifecycle_state", "spectral_variance", "k_cin",
    "projections", "dual_key_status",
}


def _vector(seed):
    return np.random.default_rng(seed).standard_normal(384).tolist()


def _post(client, auth_headers, key, vector, label=None):
    body = {"vector": vector}
    if label is not None:
        body["label"] = label
    return client.post(
        "/ingesta/vector", json=body, headers={**auth_headers, "X-Idempotency-Key": key}
    )


def _revisions(db_path, node_id):
    with sqlite3.connect(db_path) as conn:
        return conn.execute(
            "SELECT seq, lifecycle_state FROM manifold_nodes WHERE id = ? ORDER BY seq",
            (node_id,),
        ).fetchall()


def _row_count(db_path):
    with sqlite3.connect(db_path) as conn:
        return conn.execute("SELECT COUNT(*) FROM manifold_nodes").fetchone()[0]


def _consolidate(client, auth_headers, node_id):
    res = client.post(
        f"/nodos/{node_id}/consolidar",
        json={"text": "x", "ethical_key": True},
        headers=auth_headers,
    )
    assert res.json()["new_state"] == "consolidated"


def _duplicate_of(first):
    stored = first.json()
    return {
        "status": "accepted",
        "node_id": stored["node_id"],
        "seq": stored["seq"],
        "duplicate": True,
    }


def test_repeated_key_with_the_same_body_is_a_duplicate(client, auth_headers, isolate_db):
    vector = _vector(1)
    first = _post(client, auth_headers, "k-same", vector, "alpha")
    assert first.status_code == 201
    second = _post(client, auth_headers, "k-same", vector, "alpha")
    assert second.status_code == 200
    assert second.json() == _duplicate_of(first)
    assert len(_revisions(isolate_db, first.json()["node_id"])) == 1


def test_repeated_key_with_another_vector_and_label_is_still_a_duplicate(
    client, auth_headers, isolate_db
):
    first = _post(client, auth_headers, "k-other", _vector(2), "alpha")
    assert first.status_code == 201
    second = _post(client, auth_headers, "k-other", _vector(3), "beta")
    assert second.status_code == 200
    assert second.json() == _duplicate_of(first)
    assert _revisions(isolate_db, "VEC_beta") == []
    assert len(_revisions(isolate_db, "VEC_alpha")) == 1


def test_repeated_key_after_consolidation_is_a_duplicate_not_a_409(
    client, auth_headers, isolate_db
):
    first = _post(client, auth_headers, "k-consolidated", _vector(4), "keep")
    assert first.status_code == 201
    node_id = first.json()["node_id"]
    _consolidate(client, auth_headers, node_id)
    before = _revisions(isolate_db, node_id)
    replay = _post(client, auth_headers, "k-consolidated", _vector(4), "keep")
    assert replay.status_code == 200
    assert replay.json() == _duplicate_of(first)
    assert _revisions(isolate_db, node_id) == before
    assert before[-1][1] == "consolidated"


def test_distinct_keys_with_one_label_append_revisions(client, auth_headers, isolate_db):
    first = _post(client, auth_headers, "k-a", _vector(5), "beta")
    second = _post(client, auth_headers, "k-b", _vector(6), "beta")
    assert (first.status_code, second.status_code) == (201, 201)
    assert [seq for seq, _ in _revisions(isolate_db, "VEC_beta")] == [1, 2]


@pytest.mark.parametrize("key", ["", " ", "   ", "\t"])
def test_empty_or_blank_key_is_rejected_before_any_write(client, auth_headers, isolate_db, key):
    resp = _post(client, auth_headers, key, _vector(7), "alpha")
    assert resp.status_code == 422
    assert _row_count(isolate_db) == 0


def test_first_time_response_and_stored_bytes_are_unchanged(client, auth_headers, isolate_db):
    vector = _vector(8)
    res = _post(client, auth_headers, "k-bits", vector, "bits")
    assert res.status_code == 201
    assert set(res.json()) == FIRST_TIME_KEYS
    arr = np.asarray(vector, dtype=np.float64)
    expected = (arr / np.linalg.norm(arr)).astype(np.float64).tobytes()
    with sqlite3.connect(isolate_db) as conn:
        (blob,) = conn.execute(
            "SELECT vector_blob FROM manifold_nodes WHERE id = ?", ("VEC_bits",)
        ).fetchone()
    assert blob == expected


def test_only_the_ingest_revision_carries_the_key(client, auth_headers, isolate_db):
    first = _post(client, auth_headers, "k-only", _vector(9), "solo")
    assert first.status_code == 201
    _consolidate(client, auth_headers, first.json()["node_id"])
    with sqlite3.connect(isolate_db) as conn:
        rows = conn.execute(
            "SELECT seq, idempotency_key FROM manifold_nodes ORDER BY id, seq"
        ).fetchall()
    assert rows == [(1, "k-only"), (2, None)]


def test_text_path_revisions_keep_a_null_key(ingesta, isolate_db):
    assert ingesta("a probe entity").status_code == 200
    with sqlite3.connect(isolate_db) as conn:
        total, keyed = conn.execute(
            "SELECT COUNT(*), COUNT(idempotency_key) FROM manifold_nodes"
        ).fetchone()
    assert total >= 1
    assert keyed == 0


def test_duplicate_replay_evaluates_and_writes_nothing(
    client, auth_headers, isolate_db, monkeypatch
):
    first = _post(client, auth_headers, "k-quiet", _vector(10), "quiet")
    assert first.status_code == 201

    def forbidden(*args, **kwargs):
        raise AssertionError("a duplicate replay must not evaluate or write")

    monkeypatch.setattr(main, "auto_calibrate_critical_threshold", forbidden)
    monkeypatch.setattr(main, "evaluate_gate", forbidden)
    monkeypatch.setattr(storage, "insert_node_revision", forbidden)
    replay = _post(client, auth_headers, "k-quiet", _vector(10), "quiet")
    assert replay.status_code == 200
    assert replay.json() == _duplicate_of(first)


def test_key_taken_between_lookup_and_insert_resolves_to_the_duplicate(
    client, auth_headers, isolate_db, monkeypatch
):
    first = _post(client, auth_headers, "k-race", _vector(11), "race")
    assert first.status_code == 201
    monkeypatch.setattr(storage, "node_by_idempotency_key", lambda conn, key: None)
    second = _post(client, auth_headers, "k-race", _vector(12), "other")
    assert second.status_code == 200
    assert second.json() == _duplicate_of(first)
    assert _revisions(isolate_db, "VEC_other") == []


def test_unsafe_label_is_still_rejected_when_the_key_repeats(client, auth_headers, isolate_db):
    vector = _vector(13)
    assert _post(client, auth_headers, "k-label", vector, "alpha").status_code == 201
    resp = _post(client, auth_headers, "k-label", vector, "not a safe label!")
    assert resp.status_code == 422
