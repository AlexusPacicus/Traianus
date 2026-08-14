"""Unit test suite for exp_manifesto_tomo0 module."""
import pytest
import numpy as np
from tools.experiments.exp_manifesto_tomo0 import l2_normalize, project


def test_l2_normalize_unit_length():
    v = np.array([3.0, 4.0], dtype=np.float64)
    normed = l2_normalize(v)
    assert np.isclose(np.linalg.norm(normed), 1.0)


def test_project_spectrum():
    v = np.array([1.0, 0.0], dtype=np.float64)
    axes = [np.array([1.0, 0.0]), np.array([0.0, 1.0])]
    spectrum, var = project(v, axes)
    assert spectrum == [1.0, 0.0]
    assert var > 0.0
