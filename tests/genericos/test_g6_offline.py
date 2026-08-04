"""
G6 — Offline (finding M3, audit TRAIANUS_AUDIT.md:51,81).

Normative (RFC 2119): the encoder MUST be built with local_files_only=True
and the environment MUST have HF_HUB_OFFLINE=1; the runtime MUST NOT download
the model from HF Hub (offline sovereignty, edge ≤ 8 GB RAM).

Normative: docs/archive/legacy_docs/development/tests/SPEC-global.md
Coverage: G6
"""
import os

import pytest

import traianus.app as main
import traianus.bootstrap as bootstrap
from helpers.endpoint_registry import BLOCKS


class _FakeST:
    def __init__(self, model_name, **kwargs):
        self.captured = {"model_name": model_name, "kwargs": kwargs}


@pytest.mark.parametrize("block", BLOCKS)
def test_g6_encoder_offline_local_files_only(block, monkeypatch):
    """MUST: build_encoder uses local_files_only=True and HF_HUB_OFFLINE=1."""
    captured = {}

    class FakeST:
        def __init__(self, model_name, **kwargs):
            captured["model_name"] = model_name
            captured["kwargs"] = kwargs

    if block == "bootstrap":
        monkeypatch.setattr(bootstrap, "SentenceTransformer", FakeST)
        bootstrap.build_encoder()
    else:
        monkeypatch.setattr(main, "SentenceTransformer", FakeST)
        main.build_encoder()

    assert captured["model_name"] == "all-MiniLM-L6-v2"
    assert captured["kwargs"].get("local_files_only") is True
    assert os.environ.get("HF_HUB_OFFLINE") == "1"
