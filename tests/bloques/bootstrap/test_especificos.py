"""
This file verifies MUST/MUST NOT requirements from the SPEC (RFC 2119).
BLOCK: bootstrap — block-specific tests (Phase 2).

Tests moved from tests/test_control_plane.py WITHOUT changing assertions.
They cover: vector utilities, data contracts and the offline guard (M3).
Normative: docs/development/tests/SPEC-bootstrap.md
Coverage: BO01, BO02, BO03, BO04, BO05"""
import os

import numpy as np
import pytest
from pydantic import ValidationError

import traianus.app as main
import traianus.bootstrap as bootstrap
from traianus.app import RawDump, RefinedEntity, serialize_vector


def test_bootstrap_BO01_roundtrip_serialization():
    original_vec = np.random.randn(384).astype(np.float64)
    blob = serialize_vector(original_vec)
    reconstructed_vec = np.frombuffer(blob, dtype=np.float64)
    assert np.allclose(original_vec, reconstructed_vec)


def test_bootstrap_BO02_rawdump_contract():
    payload = RawDump(text="Canonical coordinate payload", type="text/plain")
    assert payload.type == "text/plain"
    assert payload.text == "Canonical coordinate payload"


def test_bootstrap_BO03_refinedentity_validates_lifecycle():
    with pytest.raises(ValidationError):
        RefinedEntity(
            text="Invalid state payload",
            lifecycle_state="invalid_state_name",
            revision_milestone=False,
            projections=[0.1] * 8
        )


def test_bootstrap_BO04_encoder_app_offline(monkeypatch):
    """
    M3 regression: the app encoder must be built with local_files_only=True
    and the environment with HF_HUB_OFFLINE=1 (offline sovereignty; no
    download from the HF Hub at runtime).
    """
    captured = {}

    class FakeST:
        def __init__(self, model_name, **kwargs):
            captured["model_name"] = model_name
            captured["kwargs"] = kwargs

    monkeypatch.setattr(main, "SentenceTransformer", FakeST)
    main.build_encoder()

    assert captured["model_name"] == "all-MiniLM-L6-v2"
    assert captured["kwargs"].get("local_files_only") is True
    assert os.environ.get("HF_HUB_OFFLINE") == "1"


def test_bootstrap_BO05_encoder_bootstrap_offline(monkeypatch):
    """
    M3 regression (bootstrap): same offline requirement for the geodesic
    extraction, which is the first execution that used to download the model.
    """
    captured = {}

    class FakeST:
        def __init__(self, model_name, **kwargs):
            captured["model_name"] = model_name
            captured["kwargs"] = kwargs

    monkeypatch.setattr(bootstrap, "SentenceTransformer", FakeST)
    bootstrap.build_encoder()

    assert captured["model_name"] == "all-MiniLM-L6-v2"
    assert captured["kwargs"].get("local_files_only") is True
    assert os.environ.get("HF_HUB_OFFLINE") == "1"
