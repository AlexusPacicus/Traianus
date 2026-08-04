"""
G1 — Authentication (finding H3, audit TRAIANUS_AUDIT.md:76).

Normative (RFC 2119): every route that mutates state or exposes sensitive
observability MUST require the operator token (X-Traianus-Token); without
a valid token MUST respond 401 (fail-closed). Public read-only observation
(GET /nodos) is allowed by design (Zero Observation Mutagenicity,
ADR-025#2).

Normative: docs/archive/legacy_docs/development/tests/SPEC-global.md
Coverage: G1
"""
import pytest

from traianus.app import app
from helpers.endpoint_registry import BLOCKS, endpoints_for

# Endpoints that by design MUST require token (H3). GET /nodos is read
# observation (not mutation) and is excluded.
TOKEN_PROTECTED = {
    ("post", "/ingesta"),
    ("post", "/nodos/{node_id}/consolidar"),
    ("get", "/relations"),
    ("post", "/relations"),
    ("post", "/mutate/{new_symbol}"),
    ("get", "/telemetry"),
}

BODY_BY_ENDPOINT = {
    ("post", "/ingesta"): {"type": "text/plain", "text": "x"},
    ("post", "/nodos/{node_id}/consolidar"): {"text": "x", "ethical_key": True},
    ("post", "/relations"): {"source": "NODE_A", "target": "NODE_B", "state": "consolidated"},
}


def _url_for(method, path):
    return path.format(node_id="NODE_X", new_symbol="\u2605")


@pytest.mark.parametrize("block", BLOCKS)
def test_g1_block_endpoints_require_token(block, client):
    """MUST: without valid token, every protected route responds 401."""
    endpoints = endpoints_for(block)
    if not endpoints:
        pytest.skip("bootstrap exposes no HTTP surface (covered by G6)")
    for method, path in endpoints:
        if (method, path) not in TOKEN_PROTECTED:
            continue
        url = _url_for(method, path)
        body = BODY_BY_ENDPOINT.get((method, path))
        response = client.request(method, url, json=body)
        assert response.status_code == 401, (
            f"{method.upper()} {url} must require token (H3), got {response.status_code}"
        )


@pytest.mark.parametrize("block", BLOCKS)
def test_g1_block_endpoints_accept_valid_token(block, client, auth_headers):
    """MUST: with valid token, response must not be 401."""
    endpoints = endpoints_for(block)
    if not endpoints:
        pytest.skip("bootstrap exposes no HTTP surface")
    for method, path in endpoints:
        url = _url_for(method, path)
        body = BODY_BY_ENDPOINT.get((method, path))
        response = client.request(method, url, json=body, headers=auth_headers)
        assert response.status_code != 401, (
            f"{method.upper()} {url} must not reject a valid token"
        )


def test_g1_get_nodos_is_public_observation(client):
    """SHOULD: GET /nodos is read-only observation and can be public."""
    response = client.get("/nodos")
    assert response.status_code == 200
