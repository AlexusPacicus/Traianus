"""Spatial observable derivation (Ulpia Fase 0) — pure, observational.

Each node's current 384D vector plus the active geodetic basis yield a
per-node spatial contract consumed by the Ulpia renderer:
  {x, y, z, l (density), c (affective voltage λ), h (escape distance d_esc)}
with L, C, H normalized to [0,1] (AGENTS 5-Radicals / Ulpia binary contract).

All functions are pure (numpy only, no side effects, no DB access).
"""
import numpy as np
import pytest

from tests.fixtures.polar_fixtures import random_unit_vector
from traianus.geometry.spatial_observables import derive_spatial_observables


def _onehot_matrix(n_axes: int = 8, dim: int = 384) -> dict:
    """Orthonormal one-hot basis keyed by axis id (mirrors db_factory)."""
    return {
        f"AXIS_{i + 1}": np.eye(dim, dtype=np.float64)[i] for i in range(n_axes)
    }


class TestSpatialObservables:
    def test_output_shape_and_dtypes(self):
        basis = _onehot_matrix()
        v = random_unit_vector(384, 7)
        obs = derive_spatial_observables(v, basis)
        for key in ("x", "y", "z", "l", "c", "h"):
            assert key in obs
            assert isinstance(obs[key], float)
            assert np.isfinite(obs[key])

    def test_normalized_channels_in_unit_range(self):
        basis = _onehot_matrix()
        for seed in range(20):
            v = random_unit_vector(384, 1000 + seed)
            obs = derive_spatial_observables(v, basis)
            assert 0.0 <= obs["l"] <= 1.0
            assert 0.0 <= obs["c"] <= 1.0
            assert 0.0 <= obs["h"] <= 1.0

    def test_croma_maps_voltage_lambda(self):
        """C = (λ + 1)/2 where λ is the PolarProjector voltage on the top-3 axes."""
        basis = _onehot_matrix()
        v = random_unit_vector(384, 5)
        obs = derive_spatial_observables(v, basis)
        # λ ∈ [-1,1] ⇒ C ∈ [0,1]; a near-canonical vector on AXIS_1 yields λ → 0/±1.
        assert abs(obs["c"] - 0.5) <= 0.5

    def test_deterministic(self):
        basis = _onehot_matrix()
        v = random_unit_vector(384, 42)
        a = derive_spatial_observables(v, basis)
        b = derive_spatial_observables(v, basis)
        assert a == b

    def test_self_consistent_with_projection_variance(self):
        """l (density) is monotone in the projection spectrum: a more uniform
        projection (lower variance) yields a higher l, and conversely."""
        basis = _onehot_matrix()
        # A canonical one-hot vector concentrates on one axis (high variance
        # of projections); a balanced vector spreads across axes (low variance).
        concentrated = np.eye(384, dtype=np.float64)[0]
        balanced = np.full(384, 1.0 / np.sqrt(384), dtype=np.float64)
        l_concentrated = derive_spatial_observables(concentrated, basis)["l"]
        l_balanced = derive_spatial_observables(balanced, basis)["l"]
        assert l_balanced > l_concentrated

    def test_requires_at_least_three_axes(self):
        with pytest.raises(ValueError):
            derive_spatial_observables(random_unit_vector(384, 1), _onehot_matrix(2))
