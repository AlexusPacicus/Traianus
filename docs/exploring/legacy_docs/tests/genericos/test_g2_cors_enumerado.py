"""
G2 — CORS enumerated (finding H3, audit TRAIANUS_AUDIT.md:76).

Normative (RFC 2119): CORS policy MUST NOT use wildcard "*" combined
with credentials; allowed origins MUST be explicitly enumerated
(ALLOWED_ORIGINS). A foreign origin MUST NOT receive Access-Control-Allow-Origin.

Normative: docs/archive/legacy_docs/development/tests/SPEC-global.md
Coverage: G2
"""
import pytest

from traianus.app import app, ALLOWED_ORIGINS
from helpers.endpoint_registry import BLOCKS, endpoints_for


@pytest.mark.parametrize("block", [b for b in BLOCKS if endpoints_for(b)])
def test_g2_cors_enumerated_no_wildcard(block, client):
    cors = [m for m in app.user_middleware if m.cls.__name__ == "CORSMiddleware"]
    assert cors, "CORSMiddleware MUST be configured"
    origins = cors[0].kwargs.get("allow_origins", [])
    assert "*" not in origins, "CORS wildcard is prohibited with credentials"
    assert origins == ALLOWED_ORIGINS, "origins MUST be explicitly enumerated"

    for method, path in endpoints_for(block):
        url = path.format(node_id="NODE_X", new_symbol="\u2605")
        evil = client.options(
            url,
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": method.upper(),
            },
        )
        acao = evil.headers.get("access-control-allow-origin")
        assert acao != "https://evil.example", (
            f"foreign origin must not be reflected in {method.upper()} {url}"
        )

        local = client.options(
            url,
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": method.upper(),
            },
        )
        assert local.headers.get("access-control-allow-origin") == "http://localhost:5173"
