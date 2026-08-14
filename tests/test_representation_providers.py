"""Behavioral tests for concrete representation providers (issue #46).

MockRepresentationProvider is hermetic (no model, no network, deterministic).
SentenceTransformerProvider wraps the real offline model; its tests carry the
``model`` marker and run with the locally cached all-MiniLM-L6-v2.
"""
import numpy as np
import pytest
import os

from traianus.representation.mock_provider import MockRepresentationProvider
from traianus.representation.protocol import RepresentationProvider

DIMENSION = 384


class TestMockProviderContract:
    def test_dimension_is_384(self):
        assert MockRepresentationProvider().dimension == DIMENSION

    def test_encode_returns_1d_float32(self):
        vec = MockRepresentationProvider().encode("hello")
        assert isinstance(vec, np.ndarray)
        assert vec.ndim == 1
        assert vec.shape == (DIMENSION,)
        assert vec.dtype == np.float32

    def test_encode_batch_shape(self):
        out = MockRepresentationProvider().encode_batch(["a", "b", "c"])
        assert isinstance(out, np.ndarray)
        assert out.shape == (3, DIMENSION)
        assert out.dtype == np.float32

    def test_deterministic_same_text(self):
        provider = MockRepresentationProvider()
        assert np.array_equal(provider.encode("x"), provider.encode("x"))

    def test_distinct_texts_differ(self):
        provider = MockRepresentationProvider()
        assert not np.array_equal(provider.encode("x"), provider.encode("y"))

    def test_satisfies_protocol(self):
        assert isinstance(MockRepresentationProvider(), RepresentationProvider)


@pytest.mark.model
class TestSentenceTransformerProviderContract:
    @pytest.fixture(scope="class")
    def provider(self):
        from traianus.representation.sentence_transformer import SentenceTransformerProvider

        return SentenceTransformerProvider()

    def test_satisfies_protocol(self, provider):
        assert isinstance(provider, RepresentationProvider)

    def test_dimension_is_384(self, provider):
        assert provider.dimension == DIMENSION

    def test_encode_returns_1d_float32(self, provider):
        vec = provider.encode("something")
        assert vec.ndim == 1
        assert vec.shape == (DIMENSION,)
        assert vec.dtype == np.float32

    def test_encode_batch_shape(self, provider):
        out = provider.encode_batch(["a", "b"])
        assert out.shape == (2, DIMENSION)
        assert out.dtype == np.float32


def test_constructs_offline_with_local_files_only(monkeypatch):
    """M3 invariant: the single construction site passes the offline flags.

    Behavioral, not textual: ``_construct`` must forward ``local_files_only=True``
    and the pinned revision to ``SentenceTransformer``.
    """
    captured = {}

    import sentence_transformers as st

    def fake_init(self, model_id, revision=None, local_files_only=None, **kwargs):
        captured["model_id"] = model_id
        captured["revision"] = revision
        captured["local_files_only"] = local_files_only
        self.model_id = model_id

    monkeypatch.setattr(st.SentenceTransformer, "__init__", fake_init)

    from traianus.representation import sentence_transformer as stp

    assert os.environ.get("HF_HUB_OFFLINE") == "1"

    monkeypatch.setattr(stp, "_model", None)
    assert stp.build_encoder() is not None
    assert captured["model_id"] == stp.MODEL_ID
    assert captured["revision"] == stp.MODEL_REVISION
    assert captured["local_files_only"] is True
