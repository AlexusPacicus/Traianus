"""
This file verifies MUST/MUST NOT requirements from the SPEC (RFC 2119).
Claim CL-R2 (R-2 / M4): the README quickstart documents
`uvicorn traianus.app:app --host 127.0.0.1`.

State: ACTIVE. The README (§ Quickstart) documents the uvicorn command with
local binding: `uvicorn traianus.app:app --host 127.0.0.1 --port 8000`.
Normative: docs/development/tests/SPEC-afirmaciones.md
Coverage: CL-R2"""
import pytest

from tests.afirmaciones.claims_registry import CLAIMS, resolve


def test_afirmaciones_CL_R2_readme_documents_uvicorn_local():
    readme = open(resolve("README.md"), encoding="utf-8").read()
    assert "uvicorn traianus.app:app" in readme, "CL-R2 MUST: README documents uvicorn traianus.app:app"
    assert "127.0.0.1" in readme, "CL-R2 MUST: README documents --host 127.0.0.1"


def test_afirmaciones_CL_R2_registry_active():
    claim = CLAIMS["CL-R2"]
    assert claim["state"] == "ACTIVE"
