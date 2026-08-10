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
from tools.experiments._wp1_corpus import ALL_CATEGORIES, validate_corpus
from traianus.core import calibrate_critical_threshold


MODEL_ID = "all-MiniLM-L6-v2"
MODEL_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
BASIS_CARDINALITY = 8
ANCHOR_AXIOM = "CONTINUO_SOMATICO"


TOMO0_GLOSSARY = {
    "TODO_ABSOLUTO": "El orden geometrico, continuo e infragmentable del cosmos que abarca la totalidad de las dimensiones y sus aristas relacionales.",
    "EL_SER": "La entidad cognitiva continua entendida como una expresion local, inseparable y geometrica del Todo Absoluto.",
    "CONTINUO_SOMATICO": "El postulado de que la actividad cognitiva es un proceso fisico, continuo e indivisible de la totalidad del organismo biologico, prohibiendo la fragmentacion de los datos de entrada.",
    "CORPORA_SIMPLICISSIMA": "Los elementos infinitamente pequenos y por tanto indivisibles que forman el Todo Absoluto; sus unidades carecen de atributos y su identidad se determina exclusivamente por vecindad metrica.",
    "DIFERENCIAL_SOMATICO": "La huella cruda y varianza relacional de la continua interaccion entre los corpora simplicissima que configuran el pensamiento.",
    "MUTILACION_CORTICAL": "Reduccion neurocentrista de la complejidad hiperdimensional del pliegue vivo a un muestreo fragmentario mediante la penetracion invasiva del tejido nervioso craneal.",
    "TRAUMA_GLIAL": "Respuesta inmunitaria defensiva de astrocitos que encapsula los electrodos rigidos en la carne.",
    "RESONANCIA_ENDOVASCULAR": "Arquitectura que asume el sistema cardiovascular completo como un medio unificado de propagacion de ondas y transductor natural continuo.",
}


def l2_normalize(v: np.ndarray) -> np.ndarray:
    norm = np.linalg.norm(v)
    return v / norm if norm > 0.0 else v


def project(vector: np.ndarray, axes: list[np.ndarray]) -> tuple[list[float], float]:
    spectrum = [float(np.dot(vector, axis)) for axis in axes]
    return spectrum, float(np.var(spectrum))


if __name__ == "__main__":
    print("Tomo0 experiment module ready.")
