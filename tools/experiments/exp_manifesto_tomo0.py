#!/usr/bin/env python3
"""Tomo 0 projection basis (B_Tomo0) and hyperdimensional phase transition."""
import argparse
import json
import os
import sys
import numpy as np


os.environ.setdefault("HF_HUB_OFFLINE", "1")
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


from sentence_transformers import SentenceTransformer
from tools.experiments.shared._wp1_corpus import ALL_CATEGORIES, validate_corpus
from traianus.core import calibrate_critical_threshold


MODEL_ID = "all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
BASIS_CARDINALITY = 8
ANCHOR_AXIOM = "CONTINUO_SOMATICO"


TOMO0_GLOSSARY = {
    "TODO_ABSOLUTO": "The absolute, continuous and unfragmentable order of the cosmos encompassing all dimensions and its relational edges.",
    "EL_SER": "The cognitive entity understood as a local, inseparable and geometric expression of the Absolute Totality.",
    "CONTINUO_SOMATICO": "The postulate that cognitive activity is a physical, continuous and indivisible process of the total organism, prohibiting fragmentation of input data.",
    "CORPORA_SIMPLICISSIMA": "The infinitely small elements and therefore indivisible that form the Absolute Totality; their units lack attributes and their identity is determined exclusively by metric proximity.",
    "DIFERENCIAL_SOMATICO": "The raw relational variance fingerprint of the continuous interaction between the corpora simplicissima that configure thought.",
    "MUTILACION_CORTICAL": "Neurocentric reduction of the hyperdimensional complexity of the living fold to a fragmentary sampling via invasive penetration of the cranial nerve tissue.",
    "TRAUMA_GLIAL": "Defensive immune response of astrocytes that encapsulates rigid electrodes in the flesh.",
    "RESONANCIA_ENDOVASCULAR": "Architecture that assumes the complete cardiovascular system as a unified medium for wave propagation and a natural continuous transducer.",
}


def l2_normalize(v: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(v)
    return v / norm if norm > 0.0 else v


def project(vector: np.ndarray, axes: list[np.ndarray]) -> tuple[list[float], float]:
    spectrum = [float(np.dot(vector, axis)) for axis in axes]
    return spectrum, float(np.var(spectrum))


if __name__ == "__main__":
    print("Tomo0 experiment module ready.")
