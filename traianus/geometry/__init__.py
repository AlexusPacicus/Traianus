"""Geometry layer: pure observational mathematics (issue #48).

Deterministic, side-effect-free geometry over S^{d-1}: kinematic resistance,
orthogonal distance, discrimination ratio, dimensional relief, ε-adjacency and
threshold calibration. No SQLite / FastAPI / governance dependencies — the
dual-key decision gate lives in ``traianus.governance.gate``.
"""

from traianus.geometry.observables import (
    calibrate_critical_threshold,
    compute_epsilon_edges,
    compute_kinetic_resistance,
    discrimination_ratio,
    ortho_distance,
    project_dimensional_relief,
)

__all__ = [
    "calibrate_critical_threshold",
    "compute_epsilon_edges",
    "compute_kinetic_resistance",
    "discrimination_ratio",
    "ortho_distance",
    "project_dimensional_relief",
]
