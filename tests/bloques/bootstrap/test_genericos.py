"""
This file verifies MUST/MUST NOT requirements from the SPEC (RFC 2119).
BLOCK: bootstrap — applicable generics (Phase 2).

SPEC: docs/development/tests/SPEC-bootstrap.md
Normative: docs/development/tests/SPEC-bootstrap.md
Coverage: BO06, BO07"""
import pytest

from helpers.endpoint_registry import GENERICS_BY_BLOCK, endpoints_for, generics_for


def test_bootstrap_BO06_generics_registry_matches():
    assert set(generics_for("bootstrap")) == {"G3", "G6", "G7", "G8"}
    assert GENERICS_BY_BLOCK["bootstrap"] == ["G3", "G6", "G7", "G8"]


def test_bootstrap_BO07_does_not_expose_http_endpoints():
    assert endpoints_for("bootstrap") == []
