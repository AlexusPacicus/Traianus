"""SVD projection and chromatic scaling (Ulpia 5D).

Pure mathematical functions for dimensionality reduction and chromatic
channel mapping. These are lab/test helpers — never invoked by app.py.
"""

import numpy as np
import pytest

from traianus.geometry.observables import (
    project_to_5d,
    sigmoid_scale,
    svd_reduce,
)


class TestSvdReduce:
    def test_output_shape(self):
        rng = np.random.default_rng(42)
        X = rng.standard_normal((10, 8)).astype(np.float32)
        coords, residual = svd_reduce(X, k=2)
        assert coords.shape == (10, 2)
        assert residual.shape == (10, 3)

    def test_single_vector(self):
        rng = np.random.default_rng(43)
        X = rng.standard_normal((1, 8)).astype(np.float32)
        coords, residual = svd_reduce(X, k=2)
        assert coords.shape == (1, 2)
        assert residual.shape == (1, 3)

    def test_coords_are_centered(self):
        rng = np.random.default_rng(42)
        X = rng.standard_normal((20, 8)).astype(np.float32)
        coords, _ = svd_reduce(X, k=2)
        assert coords.shape == (20, 2)
        # PCA on centered input yields zero-mean coordinates.
        assert np.allclose(coords.mean(axis=0), 0.0, atol=1e-6)

    def test_dimension_error_too_few_columns(self):
        rng = np.random.default_rng(44)
        X = rng.standard_normal((5, 1)).astype(np.float32)
        with pytest.raises(ValueError):
            svd_reduce(X, k=2)


class TestSigmoidScale:
    def test_output_range(self):
        vals = np.array([-10.0, -1.0, 0.0, 1.0, 10.0])
        result = sigmoid_scale(vals, min_val=0.15, max_val=1.0)
        assert result.min() >= 0.15
        assert result.max() <= 1.0

    def test_deterministic(self):
        vals = np.random.default_rng(45).standard_normal(50)
        r1 = sigmoid_scale(vals)
        r2 = sigmoid_scale(vals)
        np.testing.assert_array_equal(r1, r2)

    def test_custom_range(self):
        vals = np.array([0.0, 1.0, 2.0, 3.0])
        result = sigmoid_scale(vals, min_val=0.0, max_val=1.0)
        assert result.min() >= 0.0
        assert result.max() <= 1.0

    def test_constant_input(self):
        vals = np.ones(10) * 5.0
        result = sigmoid_scale(vals)
        assert result.shape == (10,)
        assert np.all(result >= 0.15)
        assert np.all(result <= 1.0)


class TestProjectTo5d:
    def test_output_shape(self):
        rng = np.random.default_rng(46)
        X = rng.standard_normal((10, 8)).astype(np.float32)
        result = project_to_5d(X)
        assert result.shape == (10, 5)

    def test_xy_range(self):
        rng = np.random.RandomState(7)
        X = rng.randn(15, 8).astype(np.float32)
        result = project_to_5d(X)
        assert result[:, 0].min() >= -1.0
        assert result[:, 0].max() <= 1.0
        assert result[:, 1].min() >= -1.0
        assert result[:, 1].max() <= 1.0

    def test_rgb_range(self):
        rng = np.random.RandomState(9)
        X = rng.randn(15, 8).astype(np.float32)
        result = project_to_5d(X)
        assert result[:, 2].min() >= 0.15
        assert result[:, 2].max() <= 1.0
        assert result[:, 3].min() >= 0.15
        assert result[:, 3].max() <= 1.0
        assert result[:, 4].min() >= 0.15
        assert result[:, 4].max() <= 1.0

    def test_deterministic(self):
        rng = np.random.RandomState(42)
        X = rng.randn(10, 8).astype(np.float32)
        r1 = project_to_5d(X)
        r2 = project_to_5d(X)
        np.testing.assert_array_equal(r1, r2)

    def test_dimension_error(self):
        rng = np.random.default_rng(47)
        X = rng.standard_normal((5, 3)).astype(np.float32)
        with pytest.raises(ValueError):
            project_to_5d(X)


def test_svd_reduce_rejects_empty_matrix():
    with pytest.raises(ValueError):
        svd_reduce(np.zeros((0, 6)))


def test_svd_reduce_rejects_non_finite_input():
    X = np.ones((5, 6))
    X[2, 3] = np.nan
    with pytest.raises(ValueError):
        svd_reduce(X)
    X[2, 3] = np.inf
    with pytest.raises(ValueError):
        svd_reduce(X)


def test_svd_reduce_sign_canonicalization():
    """Global input flip must not flip canonical component signs."""
    rng = np.random.default_rng(11)
    X = rng.standard_normal((12, 7))
    c1, r1 = svd_reduce(X, k=2)
    c2, r2 = svd_reduce(-X, k=2)
    assert np.allclose(c1, c2)
    assert np.allclose(r1, r2)


def test_project_to_5d_stable_under_global_sign_flip():
    rng = np.random.default_rng(13)
    X = rng.standard_normal((10, 8))
    p1 = project_to_5d(X / np.linalg.norm(X, axis=1, keepdims=True))
    p2 = project_to_5d(-X / np.linalg.norm(-X, axis=1, keepdims=True))
    assert np.allclose(p1, p2)
