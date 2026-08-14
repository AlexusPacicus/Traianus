"""Structural contract tests for the RepresentationProvider protocol (issue #45).

The protocol is the abstract boundary between the substrate and any
text->vector engine. Conformance is verified via runtime_checkable isinstance
gates over probe providers (no real model, no mock module yet).
"""
import numpy as np

from traianus.representation.protocol import RepresentationProvider


class _ConformingProvider:
    dimension = 384

    def encode(self, text: str) -> np.ndarray:
        return np.zeros(self.dimension, dtype=np.float32)

    def encode_batch(self, texts: list[str]) -> np.ndarray:
        return np.zeros((len(texts), self.dimension), dtype=np.float32)


class _NonConformingProvider:
    def encode(self, text: str) -> np.ndarray:
        return np.zeros(1, dtype=np.float32)


def test_protocol_exposes_contract_members():
    annotations = RepresentationProvider.__annotations__
    members = dir(RepresentationProvider)
    assert "dimension" in annotations
    for name in ("encode", "encode_batch"):
        assert name in members


def test_conforming_provider_satisfies_protocol():
    assert isinstance(_ConformingProvider(), RepresentationProvider)


def test_non_conforming_provider_fails_protocol():
    assert not isinstance(_NonConformingProvider(), RepresentationProvider)
