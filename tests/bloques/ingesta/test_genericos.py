"""
This file verifies MUST/MUST NOT requirements from the SPEC (RFC 2119).
BLOCK: ingestion — applicable generics (Phase 2).

The G1–G9 catalog lives in tests/genericos/ and is parametrized by block.
This file verifies the registry coherence and the endpoints smoke of the
block (deep coverage lives in tests/genericos).

SPEC: docs/development/tests/SPEC-ingesta.md
Normative: docs/development/tests/SPEC-ingesta.md
Coverage: IN09, IN10"""
import pytest

from helpers.endpoint_registry import endpoints_for, generics_for


def test_ingestion_IN09_generics_registry_matches():
    # The registry must declare exactly the generics that apply to this block
    # (SPEC-ingesta). A drift in GENERICS_BY_BLOCK fails here.
    assert set(generics_for("ingestion")) == {"G1", "G2", "G3", "G4", "G6", "G7"}


@pytest.mark.parametrize("method,path", endpoints_for("ingestion"))
def test_ingestion_IN10_endpoints_respond_with_token(method, path, client, auth_headers):
    url = path.format(node_id="NODE_X", new_symbol="\u2605")
    response = client.request(
        method, url, json={"type": "text/plain", "text": "smoke"}, headers=auth_headers
    )
    assert response.status_code != 500
    assert response.status_code != 401
