"""Weightless analytic 14D parser (NSM 1972) - deterministic, dependency-free.

Three-phase pipeline (SPEC-TDD-028):

  Phase A -- Vectorial extraction (Tier 1): text -> 3-5 char n-grams ->
             feature hashing (FNV-1a 64-bit) -> raw counts v_raw ->
             strict L2 normalization: v = v_raw / ||v_raw||_2 (||v||_2 == 1.0).

  Phase B -- Spectral projection (Tier 1 -> Tier 2): project v onto the
             NSM prototype basis (P_1..P_14, 14 non-orthogonal prototypes
             derived from NSM 1972 primitives in the same 14D space):
             s_k = <v, P_k> for all k in [1, 14].

  Phase C -- Geometric friction (Tier 2): sigma^2 = var(s), evaluated ONLY
             on the projection spectrum s -- NEVER on the raw hash-bin counts.

No neural networks, no external dependencies, no network. Every byte is
deterministic given the same input string (bitwise reproducibility across
runs and platforms).

The dynamic threshold theta_dyn is calibrated as the P95 of sigma^2 over a
neutral control corpus (SPEC-TDD-028 section 6).
"""

import json
import os

import numpy as np

DIM = 14
NGRAM_MIN = 3
NGRAM_MAX = 5

_CORPUS_PATH = "tools/fixtures/control_corpus_100.txt"
_PROTOTYPES_PATH = "tools/fixtures/nsm_prototypes_14.json"


def _fnv1a64(data: bytes, seed: int = 0xCBF29CE484222325) -> int:
    """FNV-1a 64-bit non-cryptographic hash (deterministic, no external deps)."""
    prime = 0x100000001B3
    h = seed
    for byte in data:
        h ^= byte
        h = (h * prime) & 0xFFFFFFFFFFFFFFFF
    return h


def _ngrams(text: str) -> list[str]:
    """Extracts all 3..5 char substrings (sliding window, morphology-aware)."""
    lower = text.lower()
    grams = []
    for n in range(NGRAM_MIN, NGRAM_MAX + 1):
        for i in range(0, len(lower) - n + 1):
            grams.append(lower[i:i + n])
    return grams


def load_prototype_basis() -> np.ndarray:
    """Phase B basis: 14 NSM prototype vectors in the 14D feature space.

    Each prototype is encode_weightless_14d(NSM_primitive), so the basis
    lives in the SAME space as the encoded inputs (self-consistent by
    construction). The prototypes are deliberately NON-orthogonal: measured
    off-diagonal cosine mean 0.24 / max 0.83, rank 14, cond ~35.
    """
    with open(_PROTOTYPES_PATH, encoding="utf-8") as fh:
        payload = json.load(fh)
    return np.asarray([entry["vector"] for entry in payload], dtype=np.float64)


_BASIS = load_prototype_basis()


def encode_weightless_14d(text: str) -> np.ndarray:
    """Phase A: maps text to an L2-normalized float64 vector v in R^14 (S^13).

    Feature Hashing produces the raw bin counts; those counts are strictly
    L2-normalized so the coordinate v always lives on the unit sphere. This
    function is the ONLY place raw counts may be touched: downstream phases
    operate on the normalized coordinate v.

    Empty or whitespace-only input cannot produce n-grams; to avoid a
    zero vector (division by zero / "flat mass"), it returns the uniform
    vector [1/sqrt(14), ..., 1/sqrt(14)] (TEST-03).
    """
    grams = _ngrams(text.strip())
    if not grams:
        return np.full(DIM, 1.0 / np.sqrt(DIM), dtype=np.float64)

    v_raw = np.zeros(DIM, dtype=np.float64)
    for gram in grams:
        h = _fnv1a64(gram.encode("utf-8"))
        v_raw[h % DIM] += 1.0

    norm = np.linalg.norm(v_raw)
    if norm == 0.0:
        return np.full(DIM, 1.0 / np.sqrt(DIM), dtype=np.float64)
    return (v_raw / norm).astype(np.float64)


def project_onto_basis(v: np.ndarray) -> np.ndarray:
    """Phase B: spectral projection s_k = <v, P_k> for k in [1, 14].

    Projects onto the 14 real NSM prototype vectors. A future basis change
    only touches load_prototype_basis()/nsm_prototypes_14.json, never
    Phase A or C.
    """
    return (_BASIS @ v).astype(np.float64)


def spectral_variance(v: np.ndarray) -> float:
    """Phase C: geometric friction sigma^2 = var(projection spectrum s).

    Computed exclusively on the Phase B spectrum. It never touches the raw
    feature-hashing bin counts: a flat spectrum (all prototypes excited
    equally) yields sigma^2 -> 0; a concentrated spectrum yields high sigma^2.
    """
    s = project_onto_basis(v)
    return float(np.var(s))


def load_control_corpus() -> list[str]:
    """Reads the 100 neutral-phrase control corpus (TEST-06 fixture)."""
    with open(_CORPUS_PATH, encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip()]


def calibrate_control_threshold(corpus: list[str], percentile: float = 95.0) -> float:
    """Calibrates theta_dyn = P95(sigma^2_control) over a neutral corpus."""
    variances = [spectral_variance(encode_weightless_14d(text)) for text in corpus]
    return float(np.percentile(variances, percentile))
