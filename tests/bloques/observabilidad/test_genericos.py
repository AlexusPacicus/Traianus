"""
This file verifies MUST/MUST NOT requirements from the SPEC (RFC 2119).
BLOCK: observability — applicable generics (Phase 2).

SPEC: docs/development/tests/SPEC-observabilidad.md
Normative: docs/development/tests/SPEC-observabilidad.md
Coverage: OB07, OB08"""
import pytest

from helpers.endpoint_registry import endpoints_for, generics_for


def test_observability_OB07_generics_registry_matches():
    # The registry must declare exactly the generics that apply to this block
    # (SPEC-observabilidad). A drift in GENERICS_BY_BLOCK fails here.
    assert set(generics_for("observability")) == {"G1", "G2", "G3", "G4", "G5", "G7"}


@pytest.mark.parametrize("method,path", endpoints_for("observability"))
def test_observability_OB08_endpoints_respond_with_token(method, path, client, auth_headers):
    url = path.format(node_id="NODE_X", new_symbol="\u2605")
    headers = auth_headers if path == "/telemetry" else None
    response = client.request(method, url, json=None, headers=headers)
    assert response.status_code != 500
    if path == "/telemetry":
        assert response.status_code != 401
