"""
This file verifies MUST/MUST NOT requirements from the SPEC (RFC 2119).
BLOCK: consolidation — applicable generics (Phase 2).

SPEC: docs/development/tests/SPEC-consolidacion.md
Normative: docs/development/tests/SPEC-consolidacion.md
Coverage: CO08, CO09"""
import pytest

from helpers.endpoint_registry import GENERICS_BY_BLOCK, endpoints_for, generics_for


def test_consolidation_CO08_generics_registry_matches():
    assert set(generics_for("consolidation")) == {"G1", "G2", "G3", "G5", "G7", "G8"}
    assert GENERICS_BY_BLOCK["consolidation"] == ["G1", "G2", "G3", "G5", "G7", "G8"]


@pytest.mark.parametrize("method,path", endpoints_for("consolidation"))
def test_consolidation_CO09_endpoints_respond_with_token(method, path, client, auth_headers):
    url = path.format(node_id="NODE_X", new_symbol="\u2605")
    response = client.request(
        method, url, json={"text": "smoke", "ethical_key": True}, headers=auth_headers
    )
    assert response.status_code != 500
    assert response.status_code != 401
