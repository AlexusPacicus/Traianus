"""Label hardening for POST /ingesta/vector (audit M3-medium).

The label flows verbatim into the persistent node id (`VEC_<label>`) and,
downstream, into edge ids (`edge-<src>-<tgt>`). Unbounded/unsafe labels
allow path-like, whitespace, unicode or oversized identifiers into the
manifold namespace. Contract: `[A-Za-z0-9_-]{1,64}`, else 422.
"""
import numpy as np
import pytest


def _unit_vector(dim: int = 384, seed: int = 42) -> list[float]:
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(dim).astype(np.float64)
    v /= np.linalg.norm(v)
    return v.tolist()


# NOTE: an EMPTY label is not unsafe — it routes to the content-addressed
# digest node-id path by design (same as omitting the field).
@pytest.mark.parametrize(
    "bad_label",
    ["../evil", "has space", "a" * 65, "caf\u00e9", "a/b", "\ttab"],
)
def test_unsafe_label_rejected_422(client, auth_headers, bad_label):
    res = client.post(
        "/ingesta/vector",
        json={"vector": _unit_vector(), "label": bad_label},
        headers=auth_headers,
    )
    assert res.status_code == 422


def test_safe_label_accepted_verbatim(client, auth_headers):
    res = client.post(
        "/ingesta/vector",
        json={"vector": _unit_vector(), "label": "ok-LABEL_9"},
        headers=auth_headers,
    )
    assert res.status_code == 201
    assert res.json()["node_id"] == "VEC_ok-LABEL_9"


def test_max_length_label_accepted(client, auth_headers):
    res = client.post(
        "/ingesta/vector",
        json={"vector": _unit_vector(), "label": "a" * 64},
        headers=auth_headers,
    )
    assert res.status_code == 201
