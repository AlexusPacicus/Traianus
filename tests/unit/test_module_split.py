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


def test_geometry_symbols_identical_in_core_shim():
    core, geometry, _ = _modules()
    geometry_symbols = {
        "calibrate_critical_threshold",
        "compute_epsilon_edges",
        "compute_kinetic_resistance",
        "discrimination_ratio",
        "ortho_distance",
        "project_dimensional_relief",
        "project_to_5d",
        "sigmoid_scale",
        "svd_reduce",
    }
    for name in geometry_symbols:
        assert getattr(geometry, name) is getattr(core, name), name


def test_gate_symbols_identical_in_core_shim():
    core, _, governance = _modules()
    assert governance.evaluate_gate is core.evaluate_gate
    assert governance.evaluate_gate_v01 is governance.evaluate_gate
    assert governance.evaluate_gate_v01 is core.evaluate_gate_v01
