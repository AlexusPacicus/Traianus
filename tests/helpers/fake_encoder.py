"""
Hermetic fake encoder (finding L1, Phase 0).

Replaces `SentenceTransformer("all-MiniLM-L6-v2")` in unit tests:
- Does not load the model (saves RAM ≤ 8 GB and import time).
- Makes no network requests (Zero-Trust, AGENTS.md §2.3).
- Produces deterministic 384-dim L2-normalized vectors with the same
  contract shape as `model.encode()` from sentence-transformers.

Grounding: TRAIANUS_AUDIT.md:87 — "injecting a fake encoder" (L1).
"""
import hashlib

import numpy as np

DIMENSION = 384


class FakeSentenceTransformer:
    """Deterministic encoder without network or real model."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", **kwargs):
        self.model_name = model_name
        self.kwargs = kwargs

    def encode(self, sentences, **kwargs):
        single = isinstance(sentences, str)
        items = [sentences] if single else list(sentences)
        out = []
        for text in items:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            seed = int.from_bytes(digest[:8], "little")
            rng = np.random.default_rng(seed)
            vec = rng.standard_normal(DIMENSION).astype(np.float64)
            norm = np.linalg.norm(vec)
            out.append(vec / norm if norm > 0 else vec)
        return out[0] if single else np.stack(out)


def build_fake_encoder():
    """Constructor compatible with `build_encoder()` from traianus.app."""
    return FakeSentenceTransformer()
