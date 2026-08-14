"""Abstract representation contract (issue #45).

``RepresentationProvider`` is the single abstract boundary between the
substrate control plane and any text->vector engine. Concrete providers
(real model, deterministic mock) MUST satisfy this protocol so that
``traianus.app`` / ``traianus.bootstrap`` stay engine-agnostic.

Native output contract (audit G4 / plan decision): ``encode`` returns the
engine's raw float32 output WITHOUT normalization. The orchestration boundary
(``traianus.app._encode_vector``) owns L2 normalization and the binary
dtype/dimension validation; ``dimension`` reflects the provider's native
embedding width (384 for all-MiniLM-L6-v2).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np


@runtime_checkable
class RepresentationProvider(Protocol):
    """Structural contract for deterministic text encoders."""

    dimension: int

    def encode(self, text: str) -> np.ndarray:
        """Encode a single text into a 1-D float32 vector of size ``dimension``.

        Native model output, unnormalized. The caller performs L2
        normalization and binary validation.
        """
        ...

    def encode_batch(self, texts: list[str]) -> np.ndarray:
        """Encode ``texts`` into an (N, dimension) float32 matrix."""
        ...
