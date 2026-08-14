"""Real offline sentence-transformer provider (issue #46).

Wraps ``SentenceTransformer("all-MiniLM-L6-v2")`` behind the
``RepresentationProvider`` contract. Centralizes ``MODEL_ID`` /
``MODEL_REVISION`` (previously duplicated in app.py and bootstrap.py) and
enforces the M3 offline guard: ``HF_HUB_OFFLINE=1`` + ``local_files_only=True``
— no HF Hub downloads at runtime.

Import side effect (declared): importing this module sets
``HF_HUB_OFFLINE=1`` via ``os.environ.setdefault`` if the variable is unset.
This is the single ownership point of the offline guard; ``traianus.app`` and
``traianus.bootstrap`` keep their own idempotent ``setdefault`` calls purely
for audit framing (M3).
"""

from __future__ import annotations

import os

import numpy as np

os.environ.setdefault("HF_HUB_OFFLINE", "1")

MODEL_ID = "all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"

_model = None


def _construct(model_id, revision):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_id, revision=revision, local_files_only=True)


def build_encoder():
    global _model
    if _model is None:
        _model = _construct(MODEL_ID, MODEL_REVISION)
    return _model


class SentenceTransformerProvider:
    """Offline all-MiniLM-L6-v2 encoder satisfying ``RepresentationProvider``."""

    @property
    def dimension(self) -> int:
        return int(build_encoder().get_sentence_embedding_dimension())

    def encode(self, text: str) -> np.ndarray:
        return build_encoder().encode(text)

    def encode_batch(self, texts: list[str]) -> np.ndarray:
        return build_encoder().encode(texts)
