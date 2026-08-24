"""Pure decision and geometry kernel — re-export shim (issue #48).

Canonical homes: ``traianus.geometry.observables`` (observational geometry)
and ``traianus.governance.gate`` (dual-key C1 gate). This module aggregates
both so every historical import path (`traianus.core.X`) keeps resolving:
tests, tools, `traianus.storage` and `traianus.app` are untouched by the
split.
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
from traianus.governance.gate import evaluate_gate, evaluate_gate_v01

__all__ = [
    "calibrate_critical_threshold",
    "compute_epsilon_edges",
    "compute_kinetic_resistance",
    "discrimination_ratio",
    "ortho_distance",
    "project_dimensional_relief",
    "project_to_5d",
    "sigmoid_scale",
    "svd_reduce",
    "evaluate_gate",
    "evaluate_gate_v01",
]
