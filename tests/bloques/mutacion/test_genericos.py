"""
This file verifies MUST/MUST NOT requirements from the SPEC (RFC 2119).
BLOCK: mutation — applicable generics (Phase 2).

SPEC: docs/development/tests/SPEC-mutacion.md
Normative: docs/development/tests/SPEC-mutacion.md
Coverage: MU02, MU03"""
import pytest

from helpers.endpoint_registry import endpoints_for, generics_for


def test_mutation_MU02_generics_registry_matches():
    # The registry must declare exactly the generics that apply to this block
    # (SPEC-mutacion). A drift in GENERICS_BY_BLOCK fails here.
    assert set(generics_for("mutation")) == {"G1", "G3", "G5", "G8"}


@pytest.mark.parametrize("method,path", endpoints_for("mutation"))
def test_mutation_MU03_endpoints_respond_with_token(method, path, client, auth_headers):
    url = path.format(node_id="NODE_X", new_symbol="\u2605")
    response = client.request(method, url, json=None, headers=auth_headers)
    assert response.status_code != 500
    assert response.status_code != 401
