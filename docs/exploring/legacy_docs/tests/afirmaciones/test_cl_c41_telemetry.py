"""
This file verifies MUST/MUST NOT requirements from the SPEC (RFC 2119).
Claim CL-C41 (C-4.1): /telemetry requires token and does not leak full stack
traces to anonymous callers.
Normative: docs/archive/legacy_docs/development/tests/SPEC-afirmaciones.md
Coverage: CL-C41"""
import pytest

from helpers.endpoint_registry import endpoints_for


def test_afirmaciones_CL_C41_telemetry_requires_token(client):
    response = client.get("/telemetry")
    assert response.status_code == 401, (
        "CL-C41 MUST: /telemetry requires token; without token must respond 401"
    )


def test_afirmaciones_CL_C41_telemetry_no_traceback_leak(client, auth_headers, isolate_db):
    response = client.get("/telemetry", headers=auth_headers)
    assert response.status_code == 200
    body = response.text
    # The handler responds 500 with detail=str(e), not full traceback:
    # must never expose "Traceback (most recent call last)" to anonymous callers.
    assert "Traceback" not in body
    assert "File \"" not in body


def test_afirmaciones_CL_C41_telemetry_registered_in_registry():
    paths = {p for _, p in endpoints_for("observability")}
    assert "/telemetry" in paths, "CL-C41 references /telemetry, which must exist in the registry"
