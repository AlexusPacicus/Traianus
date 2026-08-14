"""Deterministic hermetic representation provider (issue #46).

``MockRepresentationProvider`` absorbs the logic previously owned by
``tests/helpers/fake_encoder.py`` and becomes the canonical test double: no
model, no network, deterministic hash-seeded 384D float32 vectors that satisfy
the ``RepresentationProvider`` contract. Unit tests run without loading
PyTorch into RAM.
"""

from __future__ import annotations

import hashlib

import numpy as np

from traianus.representation.protocol import RepresentationProvider

DIMENSION = 384


class MockRepresentationProvider:
    """Deterministic text encoder without model or network."""

    dimension = DIMENSION

    def encode(self, text: str) -> np.ndarray:
        return self._vector_for(text)

    def encode_batch(self, texts: list[str]) -> np.ndarray:
        return np.stack([self._vector_for(text) for text in texts])

    def _vector_for(self, text: str) -> np.ndarray:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        seed = int.from_bytes(digest[:8], "little")
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(DIMENSION).astype(np.float32)
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec
