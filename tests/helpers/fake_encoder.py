"""
Hermetic fake encoder (finding L1, Phase 0).

Since Phase 2 the canonical test double is
``traianus.representation.mock_provider.MockRepresentationProvider``
(issue #46). This module is a compatibility alias preserving the historical
``FakeSentenceTransformer`` surface (``model_name`` / ``kwargs`` attributes
and flexible ``encode``) used by conftest and the cinematic pipeline tests.

Grounding: AUDIT.md:87 — "injecting a fake encoder" (L1).
"""
from traianus.representation.mock_provider import (
    DIMENSION,
    MockRepresentationProvider,
)


class FakeSentenceTransformer(MockRepresentationProvider):
    """Deterministic encoder without network or real model (alias)."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", **kwargs):
        super().__init__()
        self.model_name = model_name
        self.kwargs = kwargs

    def encode(self, sentences, **kwargs):
        if isinstance(sentences, str):
            return super().encode(sentences)
        return super().encode_batch(list(sentences))
