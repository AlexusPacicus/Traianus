#!/usr/bin/env python3
"""EAS-01 Fase 1b — Non-orthogonal sparse logographic probe."""
import argparse
import json
import os
import random
import sys
import numpy as np


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


from tools.experiments._wp1_corpus import ALL_CATEGORIES, validate_corpus
from tools.experiments.exp_logographic_sparse import (
    cohens_d,
    mannwhitney_u_p,
    tokenize,
)
from traianus.core import calibrate_critical_threshold


LOGOGRAM_WEIGHTS: dict[str, dict[str, float]] = {
    "ContinuoSomatico": {
        "continuous": 1.0, "continuum": 1.0, "somatic": 1.0, "indivisible": 0.8,
        "organism": 0.8, "state": 0.4, "transition": 0.4,
    },
    "Metrica": {
        "metric": 1.0, "distance": 1.0, "norm": 0.9, "normalized": 0.9, "l2": 0.9,
        "cosine": 0.8, "epsilon": 0.7, "vector": 0.5, "projection": 0.4,
    },
    "Ortogonalidad": {
        "orthogonal": 1.0, "orthogonality": 1.0, "basis": 0.9, "axis": 0.9,
        "axes": 0.9, "geodetic": 0.8, "independent": 0.6, "projection": 0.4,
    },
    "DespliegueDimensional": {
        "dimension": 1.0, "dimensional": 1.0, "expand": 0.8, "expansion": 0.8,
        "canonical": 0.7, "hyperspace": 0.9, "basis": 0.4, "axis": 0.3,
    },
    "DobleLlave": {
        "consolidation": 1.0, "consolidated": 1.0, "consolidate": 1.0,
        "ethical": 0.9, "topological": 0.7, "threshold": 0.8, "gate": 0.7,
        "variance": 0.4, "state": 0.3,
    },
    "AppendOnly": {
        "append-only": 1.0, "immutable": 0.9, "revision": 0.9, "seq": 0.8,
        "history": 0.7, "overwrite": 0.7, "insert": 0.6, "persistence": 0.5,
        "state": 0.3,
    },
    "FronteraDual": {
        "boundary": 1.0, "perimeter": 1.0, "ingress": 0.9, "zero-trust": 1.0,
        "reject": 0.7, "token": 0.7, "cors": 0.7, "immutable": 0.4,
        "validation": 0.5,
    },
    "DispersionEspectral": {
        "variance": 1.0, "dispersion": 1.0, "spectral": 1.0, "sigma": 0.9,
        "projection": 0.7, "projections": 0.7, "spread": 0.6, "threshold": 0.4,
    },
    "SustratoDeterminista": {
        "deterministic": 1.0, "determinism": 1.0, "substrate": 1.0,
        "reproducible": 0.8, "algebraic": 0.7, "vector": 0.5, "vectors": 0.5,
        "transition": 0.4,
    },
    "TopologiaManifold": {
        "manifold": 1.0, "topology": 1.0, "topological": 0.8, "simplicial": 0.9,
        "adjacency": 0.8, "node": 0.7, "nodes": 0.7, "edges": 0.7,
        "persistence": 0.4,
    },
}


AXIS_NAMES: list[str] = list(LOGOGRAM_WEIGHTS)
K = len(AXIS_NAMES)


def build_axis_matrix(table=None):
    table = table if table is not None else LOGOGRAM_WEIGHTS
    vocab = sorted({t for w in table.values() for t in w})
    index = {t: i for i, t in enumerate(vocab)}
    rows = []
    for name in table:
        row = np.zeros(len(vocab), dtype=np.float64)
        for term, weight in table[name].items():
            row[index[term]] = weight
        norm = np.linalg.norm(row)
        rows.append(row / norm if norm > 0 else row)
    return np.stack(rows), vocab


def term_vector(text: str, vocab: list[str]):
    index = {t: i for i, t in enumerate(vocab)}
    counts = np.zeros(len(vocab), dtype=np.float64)
    tokens = tokenize(text)
    for tok in tokens:
        i = index.get(tok)
        if i is not None:
            counts[i] += 1.0
    return counts, len(tokens)


def project(text: str, axis_matrix: np.ndarray, vocab: list[str]):
    counts, n_tokens = term_vector(text, vocab)
    alpha = axis_matrix @ counts
    rho = float(alpha.sum() / n_tokens) if n_tokens else 0.0
    total = alpha.sum()
    shape = alpha / total if total > 0 else alpha
    return alpha, rho, float(np.var(shape))


def measure(table=None):
    A, vocab = build_axis_matrix(table)
    out = {}
    for label, paragraphs in ALL_CATEGORIES.items():
        rhos, sigmas = [], []
        for text in paragraphs:
            _, rho, sigma2 = project(text, A, vocab)
            rhos.append(rho)
            sigmas.append(sigma2)
        out[label] = {"rho": rhos, "sigma2": sigmas}
    return out, A, vocab


def run_experiment(tau: float = 0.02) -> dict:
    validate_corpus()
    measured, A, vocab = measure()
    theta_dyn = calibrate_critical_threshold([A[i] for i in range(K)])
    return {"status": "SUCCESS", "theta_dyn": theta_dyn, "k": K}


if __name__ == "__main__":
    print(json.dumps(run_experiment(), indent=2))
