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
)
from traianus.governance.gate import evaluate_gate, evaluate_gate_v01

# Kernel namespace frozen at the v1.0.0 surface (LEDGER seq 28): the Ulpia
# visualization helpers (svd_reduce / sigmoid_scale / project_to_5d) remain
# importable from traianus.geometry.observables but are NOT re-exported
# through the decision-kernel shim.
__all__ = [
    "calibrate_critical_threshold",
    "compute_epsilon_edges",
    "compute_kinetic_resistance",
    "discrimination_ratio",
    "ortho_distance",
    "project_dimensional_relief",
    "evaluate_gate",
    "evaluate_gate_v01",
]
