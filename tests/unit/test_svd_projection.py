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
        X = np.random.randn(10, 8).astype(np.float32)
        coords, residual = svd_reduce(X, k=2)
        assert coords.shape == (10, 2)
        assert residual.shape == (10, 3)

    def test_single_vector(self):
        X = np.random.randn(1, 8).astype(np.float32)
        coords, residual = svd_reduce(X, k=2)
        assert coords.shape == (1, 2)
        assert residual.shape == (1, 3)

    def test_coords_are_centered(self):
        rng = np.random.RandomState(42)
        X = rng.randn(20, 8).astype(np.float32)
        coords, _ = svd_reduce(X, k=2)
        assert coords.shape == (20, 2)

    def test_dimension_error_too_few_columns(self):
        X = np.random.randn(5, 1).astype(np.float32)
        with pytest.raises(ValueError):
            svd_reduce(X, k=2)


class TestSigmoidScale:
    def test_output_range(self):
        vals = np.array([-10.0, -1.0, 0.0, 1.0, 10.0])
        result = sigmoid_scale(vals, min_val=0.15, max_val=1.0)
        assert result.min() >= 0.15
        assert result.max() <= 1.0

    def test_deterministic(self):
        vals = np.random.randn(50)
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
        X = np.random.randn(10, 8).astype(np.float32)
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
        X = np.random.randn(5, 3).astype(np.float32)
        with pytest.raises(ValueError):
            project_to_5d(X)
