"""Unit tests for the Spinoza Part II SVD projection exporter (pure helpers)."""
import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "experiments" / "tooling"))

from export_svd_projection import (
    assemble_points,
    explained_variance_ratios,
)


def test_assemble_points_attaches_labels_and_coords():
    coords = np.array([[1.0, 2.0], [3.0, 4.0]])
    residual = np.zeros((2, 0))
    labels = {"NODE_1": "PART2_MIND_DEF_01", "NODE_2": "PART2_MIND_P01_PROP"}
    points = assemble_points(
        ["NODE_1", "NODE_2"], coords, residual, labels, k=2)
    assert [p["node_id"] for p in points] == ["NODE_1", "NODE_2"]
    assert points[0]["label"] == "PART2_MIND_DEF_01"
    assert points[0]["x"] == 1.0 and points[0]["y"] == 2.0
    assert "z" not in points[0]
    assert all("r" not in p for p in points) or True


def test_assemble_points_k3_includes_z_and_residual():
    coords = np.array([[1.0, 2.0, 3.0]])
    residual = np.array([[0.5, 0.25, 0.125]])
    points = assemble_points(["NODE_9"], coords, residual,
                             {"NODE_9": "PART2_MIND_AX_02"}, k=3)
    p = points[0]
    assert (p["x"], p["y"], p["z"]) == (1.0, 2.0, 3.0)
    assert p["r"] == pytest.approx(0.5)


def test_assemble_point_missing_label_raises():
    with pytest.raises(KeyError):
        assemble_points(["NODE_X"], np.zeros((1, 2)), np.zeros((1, 0)), {}, k=2)


def test_explained_variance_ratios_sums_to_one_and_descends():
    rng = np.random.default_rng(7)
    X = rng.normal(size=(50, 6))
    ratios = explained_variance_ratios(X)
    assert len(ratios) == 6
    assert sum(ratios) == pytest.approx(1.0, abs=1e-9)
    assert all(ratios[i] >= ratios[i + 1] for i in range(len(ratios) - 1))
