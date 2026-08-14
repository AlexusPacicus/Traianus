"""Representation layer: engine-agnostic text->vector providers.

The substrate consumes embeddings exclusively through the abstract
``RepresentationProvider`` protocol, never through a concrete engine import.
Concrete providers live in sibling modules: the real sentence-transformer
wrapper and the deterministic mock used by hermetic tests.
"""

from traianus.representation.protocol import RepresentationProvider

__all__ = ["RepresentationProvider"]
