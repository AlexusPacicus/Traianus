"""Module split regression (issue #48).

Geometry (observational) lives in traianus.geometry.observables; the dual-key
gate lives in traianus.governance.gate. traianus.core stays a re-export shim
so every legacy import (tests, tools, storage.py, app.py) resolves unchanged
and symbol identity is preserved.
"""
import importlib


def _modules():
    core = importlib.import_module("traianus.core")
    geometry = importlib.import_module("traianus.geometry.observables")
    governance = importlib.import_module("traianus.governance.gate")
    return core, geometry, governance


KERNEL_EXPORTS_V1_0_0 = {
    "calibrate_critical_threshold",
    "compute_epsilon_edges",
    "compute_kinetic_resistance",
    "discrimination_ratio",
    "ortho_distance",
    "project_dimensional_relief",
}


def test_geometry_symbols_identical_in_core_shim():
    core, geometry, _ = _modules()
    for name in KERNEL_EXPORTS_V1_0_0:
        assert getattr(geometry, name) is getattr(core, name), name


def test_core_kernel_exports_frozen_at_v1_0_0():
    """The decision-kernel namespace stays identical to v1.0.0: the Ulpia
    visualization helpers live in geometry.observables only (seq 28)."""
    core, geometry, _ = _modules()
    assert set(core.__all__) == KERNEL_EXPORTS_V1_0_0 | {
        "evaluate_gate",
        "evaluate_gate_v01",
    }
    # Client-facing helpers remain available at their canonical home.
    for name in ("project_to_5d", "sigmoid_scale", "svd_reduce"):
        assert hasattr(geometry, name), name


def test_gate_symbols_identical_in_core_shim():
    core, _, governance = _modules()
    assert governance.evaluate_gate is core.evaluate_gate
    assert governance.evaluate_gate_v01 is governance.evaluate_gate
    assert governance.evaluate_gate_v01 is core.evaluate_gate_v01
