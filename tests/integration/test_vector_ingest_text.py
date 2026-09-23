"""POST /ingesta/vector: optional node text.

The text is stored as the node's text and never embedded; the vector is taken
as given (RH-1). Absent or empty, the stored text is the label.
"""
import uuid

import numpy as np
import pytest

import traianus.storage as storage
from helpers.db_factory import create_test_db

MAX_NODE_TEXT_CHARS = 20000
RESPONSE_KEYS = {
    "status", "node_id", "seq", "lifecycle_state", "spectral_variance",
    "k_cin", "projections", "dual_key_status",
}
TEXT = "Natura naturans — natura naturata."


def _unit_vector(dim: int = 384, seed: int = 42) -> list[float]:
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(dim).astype(np.float64)
    v /= np.linalg.norm(v)
    return v.tolist()


def _post(client, auth_headers, **fields):
    return client.post(
        "/ingesta/vector",
        json={"vector": _unit_vector(), **fields},
        headers={**auth_headers, "X-Idempotency-Key": str(uuid.uuid4())},
    )


def _revisions(node_id: str) -> list:
    with storage.get_db_connection() as conn:
        return conn.execute(
            "SELECT text, seq, toon_factor, lifecycle_state, action_potential, "
            "revision_milestone, vector_blob, projections_json, epoch_provenance "
            "FROM manifold_nodes WHERE id = ? ORDER BY seq",
            (node_id,),
        ).fetchall()


def test_text_is_stored_as_node_text(client, auth_headers):
    res = _post(client, auth_headers, label="with_text", text=TEXT)
    assert res.status_code == 201
    assert _revisions("VEC_with_text")[0][0] == TEXT
    nodes = client.get("/nodos", headers=auth_headers).json()["nodes"]
    assert {n["id"]: n["text"] for n in nodes}["VEC_with_text"] == TEXT


def test_without_text_the_label_is_the_node_text(client, auth_headers):
    assert _post(client, auth_headers, label="no_text").status_code == 201
    assert _revisions("VEC_no_text")[0][0] == "no_text"


def test_empty_text_keeps_the_label_as_node_text(client, auth_headers):
    assert _post(client, auth_headers, label="empty_text", text="").status_code == 201
    assert _revisions("VEC_empty_text")[0][0] == "empty_text"


def test_null_text_keeps_the_label_as_node_text(client, auth_headers):
    assert _post(client, auth_headers, label="null_text", text=None).status_code == 201
    assert _revisions("VEC_null_text")[0][0] == "null_text"


def test_null_byte_in_text_rejected_422(client, auth_headers):
    res = _post(client, auth_headers, label="nul_byte", text="a\x00b")
    assert res.status_code == 422
    assert _revisions("VEC_nul_byte") == []


def test_text_over_the_cap_rejected_422(client, auth_headers):
    res = _post(client, auth_headers, label="too_long", text="x" * (MAX_NODE_TEXT_CHARS + 1))
    assert res.status_code == 422
    assert _revisions("VEC_too_long") == []


def test_text_at_the_cap_accepted(client, auth_headers):
    text = "x" * MAX_NODE_TEXT_CHARS
    assert _post(client, auth_headers, label="at_cap", text=text).status_code == 201
    assert _revisions("VEC_at_cap")[0][0] == text


@pytest.mark.parametrize("bad_text", [5, 1.5, True, ["a"], {"a": "b"}])
def test_non_string_text_rejected_422(client, auth_headers, bad_text):
    res = _post(client, auth_headers, label="not_str", text=bad_text)
    assert res.status_code == 422
    assert _revisions("VEC_not_str") == []


def test_text_does_not_change_the_stored_vector_state(client, auth_headers, tmp_path, monkeypatch):
    with_text = _post(client, auth_headers, label="same", text=TEXT)
    stored_with = _revisions("VEC_same")
    other_db = str(tmp_path / "other.db")
    create_test_db(other_db)
    monkeypatch.setattr(storage, "DB_PATH", other_db)
    without_text = _post(client, auth_headers, label="same")
    stored_without = _revisions("VEC_same")
    assert len(stored_with) == len(stored_without) == 1
    assert [r[1:] for r in stored_with] == [r[1:] for r in stored_without]
    assert with_text.json() == without_text.json()


def test_response_key_set_is_unchanged(client, auth_headers):
    res = _post(client, auth_headers, label="keys", text=TEXT)
    assert set(res.json()) == RESPONSE_KEYS
