"""Geometry layer: pure observational mathematics (issue #48).

Deterministic, side-effect-free geometry over S^{d-1}: kinematic resistance,
orthogonal distance, discrimination ratio, dimensional relief, ε-adjacency,
threshold calibration, semantic simplex control, parabolic reconstruction,
and SVD anisotropy filtering. No SQLite / FastAPI / governance dependencies
— the dual-key decision gate lives in ``traianus.governance.gate``.
"""

from traianus.geometry.observables import (
    calibrate_critical_threshold,
    compute_epsilon_edges,
    compute_kinetic_resistance,
    discrimination_ratio,
    ortho_distance,
    project_dimensional_relief,
    project_to_5d,
    sigmoid_scale,
    svd_reduce,
)
from traianus.geometry.parabolic import ParabolicCorrector
from traianus.geometry.polar_projector import PolarProjector
from traianus.geometry.simplex import RECALIBRATION_SIGNAL, SemanticSimplex
from traianus.geometry.svd_filter import SVDAnisotropyFilter

__all__ = [
    "RECALIBRATION_SIGNAL",
    "ParabolicCorrector",
    "PolarProjector",
    "SVDAnisotropyFilter",
    "SemanticSimplex",
    "calibrate_critical_threshold",
    "compute_epsilon_edges",
    "compute_kinetic_resistance",
    "discrimination_ratio",
    "ortho_distance",
    "project_dimensional_relief",
    "project_to_5d",
    "sigmoid_scale",
    "svd_reduce",
]
