"""
This file verifies MUST/MUST NOT requirements from the SPEC (RFC 2119).
BLOCK: relations — applicable generics (Phase 2).

SPEC: docs/development/tests/SPEC-relaciones.md
Normative: docs/development/tests/SPEC-relaciones.md
Coverage: RE04, RE05"""
import pytest

from helpers.endpoint_registry import endpoints_for, generics_for


def test_relations_RE04_generics_registry_matches():
    # The registry must declare exactly the generics that apply to this block
    # (SPEC-relaciones). A drift in GENERICS_BY_BLOCK fails here.
    assert set(generics_for("relations")) == {"G1", "G3", "G5", "G8"}


@pytest.mark.parametrize("method,path", endpoints_for("relations"))
def test_relations_RE05_endpoints_respond_with_token(method, path, client, auth_headers):
    url = path.format(node_id="NODE_X", new_symbol="\u2605")
    response = client.request(
        method, url, json={"source": "NODE_A", "target": "NODE_B", "state": "consolidated"},
        headers=auth_headers,
    )
    assert response.status_code != 500
    assert response.status_code != 401
