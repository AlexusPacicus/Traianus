"""
This file verifies MUST/MUST NOT requirements from the SPEC (RFC 2119).
Claim CL-R1 (R-1 / M4): the README quickstart starts via
traianus-bootstrap (packaged script).

State: ACTIVE. The README (§ Quickstart) documents startup via
traianus-bootstrap (packaged script) and no longer refers to test_control_plane.py.
Normative: docs/archive/legacy_docs/development/tests/SPEC-afirmaciones.md
Coverage: CL-R1"""
import pytest

from tests.afirmaciones.claims_registry import CLAIMS, resolve


def test_afirmaciones_CL_R1_readme_documents_bootstrap():
    readme = open(resolve("README.md"), encoding="utf-8").read()
    assert "traianus-bootstrap" in readme, "CL-R1 MUST: README starts via traianus-bootstrap"


def test_afirmaciones_CL_R1_readme_does_not_refer_deleted_file():
    readme = open(resolve("README.md"), encoding="utf-8").read()
    assert "test_control_plane.py" not in readme, (
        "CL-R1: README must not refer to deleted test files"
    )


def test_afirmaciones_CL_R1_registry_active():
    claim = CLAIMS["CL-R1"]
    assert claim["state"] == "ACTIVE"
