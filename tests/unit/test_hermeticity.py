"""Hermeticity contract guards for the default pytest suite (issue #51).

The default suite (addopts -m "not model") MUST run with
MockRepresentationProvider only: no PyTorch initialization, no
SentenceTransformerProvider construction, and a generous latency budget for
the full hermetic round trip.
"""
import time

import pytest

import traianus.app as main
import traianus.bootstrap as bootstrap
from traianus.representation.mock_provider import MockRepresentationProvider
from traianus.representation.sentence_transformer import SentenceTransformerProvider


def test_default_markexpr_excludes_model(pytestconfig):
    """The default suite MUST deselect @pytest.mark.model (hermetic default)."""
    assert pytestconfig.getoption("markexpr") == "not model"


def test_model_and_security_markers_registered(pytestconfig):
    """Strict markers: the 'model'/'security' markers must be declared."""
    markers = {m.split(":", 1)[0].strip() for m in pytestconfig.getini("markers")}
    assert "model" in markers
    assert "security" in markers


def test_app_provider_is_mock_in_hermetic_tests():
    """The active app provider MUST be the deterministic mock, never the model."""
    provider = main.get_provider()
    assert isinstance(provider, MockRepresentationProvider)
    assert not isinstance(provider, SentenceTransformerProvider)


def test_bootstrap_provider_is_mock_in_hermetic_tests():
    """The bootstrap provider MUST mirror the app provider (mock)."""
    provider = bootstrap.get_provider()
    assert isinstance(provider, MockRepresentationProvider)
    assert not isinstance(provider, SentenceTransformerProvider)


def test_hermetic_model_cache_stays_none(client, ingesta, auth_headers):
    """Hermetic ingestion MUST NOT build the real model (no PyTorch init)."""
    from traianus.representation import sentence_transformer as stp
    stp._model = None
    res = ingesta("hermetic round trip")
    assert res.status_code == 200
    client.get("/nodos", headers=auth_headers)
    assert stp._model is None


def test_hermetic_roundtrip_under_1s(client, ingesta, auth_headers):
    """Full hermetic round trip (ingest -> consolidate) MUST finish in < 1s."""
    start = time.monotonic()
    res = ingesta("hermetic latency guard")
    assert res.status_code == 200
    node_id = f"NODE_{res.json()['ingestion_id']}"
    resp = client.post(
        f"/nodos/{node_id}/consolidar",
        json={"text": "hermetic latency guard", "ethical_key": True},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert time.monotonic() - start < 1.0
