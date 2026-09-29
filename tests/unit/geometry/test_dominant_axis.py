"""dominant_axis: the axis k maximising <v, a_k/||a_k||>, ties to the lower sorted id.

Pure and observational. It must agree with the frozen analysis
(tools/experiments/relational_graph_exploration.axis_cells, contracts.md section 0, Conversions).
"""
import numpy as np
import pytest

from tools.experiments import relational_graph_exploration as rge
from traianus.geometry.spatial_observables import dominant_axis

D = 384


def test_returns_the_axis_of_largest_normalised_projection():
    basis = {"A": np.array([1.0, 0.0, 0.0]), "B": np.array([0.0, 1.0, 0.0])}
    assert dominant_axis(np.array([0.2, 0.9, 0.0]), basis) == "B"
    assert dominant_axis(np.array([0.9, 0.2, 0.0]), basis) == "A"


def test_a_longer_axis_does_not_win_by_its_length():
    basis = {"A": np.array([1.0, 0.0]), "B": np.array([0.0, 100.0])}
    assert dominant_axis(np.array([0.9, 0.1]), basis) == "A"


def test_ties_go_to_the_lower_sorted_id():
    basis = {"AXIS_2": np.array([1.0, 0.0]), "AXIS_1": np.array([0.0, 1.0])}
    assert dominant_axis(np.array([1.0, 1.0]), basis) == "AXIS_1"


def test_positive_scaling_of_the_vector_changes_nothing():
    rng = np.random.default_rng(1)
    basis = {f"AXIS_{i}": rng.standard_normal(D) for i in range(1, 9)}
    v = rng.standard_normal(D)
    assert dominant_axis(3.5 * v, basis) == dominant_axis(v, basis)


def test_an_empty_basis_raises():
    with pytest.raises(ValueError):
        dominant_axis(np.array([1.0, 0.0]), {})


def test_a_zero_norm_axis_raises():
    with pytest.raises(ValueError):
        dominant_axis(np.array([1.0, 0.0]), {"A": np.array([1.0, 0.0]), "B": np.zeros(2)})


def test_agrees_with_the_frozen_analysis_row_by_row():
    rng = np.random.default_rng(20260929)
    ids = [f"AXIS_{i}" for i in range(1, 9)]
    a = rng.standard_normal((8, D)) * np.arange(1, 9)[:, None]
    v = rng.standard_normal((200, D))
    basis = dict(zip(ids, a, strict=True))
    expected = [ids[k] for k in rge.axis_cells(v, a)]
    assert [dominant_axis(row, basis) for row in v] == expected
