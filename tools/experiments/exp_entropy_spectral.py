#!/usr/bin/env python3
"""EAS-01 Fase 1c — Lexicon-free substrates: NCD and Markov spectral gap."""
import argparse
import bz2
import json
import lzma
import os
import random
import sys
import zlib
import numpy as np


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


from tools.experiments._wp1_corpus import ALL_CATEGORIES, validate_corpus
from tools.experiments.exp_logographic_sparse import cohens_d, mannwhitney_u_p


COMPRESSORS = {
    "zlib": lambda b: len(zlib.compress(b, 9)),
    "bz2": lambda b: len(bz2.compress(b, 9)),
    "lzma": lambda b: len(lzma.compress(b, preset=6)),
}


def ncd(x: bytes, y: bytes, compress) -> float:
    cx, cy = compress(x), compress(y)
    cxy = compress(x + y)
    lo, hi = min(cx, cy), max(cx, cy)
    return (cxy - lo) / hi if hi > 0 else 0.0


def ncd_to_corpus(text: str, reference: bytes, compress) -> float:
    return 1.0 - ncd(text.encode("utf-8"), reference, compress)


def spectral_gap(text: str, n: int = 2) -> dict:
    s = text.lower()
    if len(s) <= n:
        return {"gap": 0.0, "lambda2": 0.0, "n_states": 0, "spectral_entropy": 0.0}
    grams = [s[i:i + n] for i in range(len(s) - n + 1)]
    states = sorted(set(grams))
    index = {g: i for i, g in enumerate(states)}
    k = len(states)
    if k < 2:
        return {"gap": 0.0, "lambda2": 0.0, "n_states": k, "spectral_entropy": 0.0}
    counts = np.zeros((k, k), dtype=np.float64)
    for a, b in zip(grams, grams[1:]):
        counts[index[a], index[b]] += 1.0
    rows = counts.sum(axis=1, keepdims=True)
    rows[rows == 0] = 1.0
    P = counts / rows
    eig = np.linalg.eigvals(P)
    mod = np.sort(np.abs(eig))[::-1]
    lam1 = float(mod[0])
    lam2 = float(mod[1]) if len(mod) > 1 else 0.0
    total = mod.sum()
    ent = float(-np.sum((mod/total) * np.log(mod/total))) if total > 0 else 0.0
    return {"gap": lam1 - lam2, "lambda2": lam2, "n_states": k, "spectral_entropy": ent}


def _split_reference(label: str, seed: int = 0) -> tuple[bytes, list[str]]:
    items = list(ALL_CATEGORIES[label])
    rng = random.Random(seed)
    rng.shuffle(items)
    half = len(items) // 2
    reference = "\n".join(items[:half]).encode("utf-8")
    return reference, items[half:]


def run_experiment(compressor: str = "bz2", ngram: int = 2) -> dict:
    validate_corpus()
    compress = COMPRESSORS[compressor]
    ref_a, held_a = _split_reference("A")
    ncd_scores = {
        "A_heldout": [ncd_to_corpus(t, ref_a, compress) for t in held_a],
        "B": [ncd_to_corpus(t, ref_a, compress) for t in ALL_CATEGORIES["B"]],
        "C": [ncd_to_corpus(t, ref_a, compress) for t in ALL_CATEGORIES["C"]],
    }
    return {"status": "SUCCESS", "scores": ncd_scores}


if __name__ == "__main__":
    print(json.dumps(run_experiment(), indent=2))
