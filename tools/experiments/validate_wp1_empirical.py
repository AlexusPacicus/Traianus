#!/usr/bin/env python3
"""WP1 Empirical Validation — Spectral Variance Separation Hypothesis."""
import argparse
import json
import os
import sys
import numpy as np


os.environ.setdefault("HF_HUB_OFFLINE", "1")
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


from tools.experiments._wp1_corpus import (
    ALL_CATEGORIES,
    category_description,
    iter_corpus,
    validate_corpus,
)
import traianus.storage as storage
from traianus.core import calibrate_critical_threshold


def run_analysis(json_output: bool = False) -> dict:
    validate_corpus()
    storage.init_db()
    matrix = storage.get_geodetic_matrix_db()
    if not matrix:
        return {"status": "EMPTY_MATRIX"}
    axes = [entry["vector"] for entry in matrix.values()]
    theta_dyn = calibrate_critical_threshold(axes)
    return {"status": "SUCCESS", "theta_dyn": theta_dyn, "axes_count": len(axes)}


if __name__ == "__main__":
    print(json.dumps(run_analysis(), indent=2))
