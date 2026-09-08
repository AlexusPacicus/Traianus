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
from traianus.geometry.polar_projector import PolarProjector
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

    @pytest.mark.parametrize("d", [128, 384, 768])
    @pytest.mark.parametrize("seed", range(25))
    def test_chromatic_channel_exact_formulae(self, d, seed):
        """C = (λ+1)/2 and H = tanh(d_esc), locked to PolarProjector output."""
        basis = _onehot_matrix(dim=d)
        projector = PolarProjector()
        axis_ids = sorted(basis.keys())
        v = random_unit_vector(d, 2000 + seed)
        obs = derive_spatial_observables(v, basis)
        # Mirror derive_spatial_observables ranking: top-3 by projection
        proj_rank = sorted(
            axis_ids,
            key=lambda k: float(np.dot(v, basis[k])),
            reverse=True,
        )
        a1, a2, a3 = proj_rank[0], proj_rank[1], proj_rank[2]
        _, lambda_val, d_esc = projector.project(
            v,
            np.asarray(basis[a1], dtype=np.float64),
            np.asarray(basis[a2], dtype=np.float64),
            np.asarray(basis[a3], dtype=np.float64),
            axis_ids.index(a1),
        )
        expected_c = float((lambda_val + 1.0) / 2.0)
        expected_h = float(np.tanh(d_esc))
        assert np.isclose(obs["c"], expected_c, atol=1e-12), (
            f"seed={seed}: C formula mismatch"
        )
        assert np.isclose(obs["h"], expected_h, atol=1e-12), (
            f"seed={seed}: H formula mismatch"
        )

    @pytest.mark.parametrize("d", [128, 384, 768])
    @pytest.mark.parametrize("seed", range(25))
    def test_density_channel_exact_formula(self, d, seed):
        """L = 1 / (1 + σ²) where σ² = var(projections onto geodetic basis)."""
        basis = _onehot_matrix(dim=d)
        axis_ids = sorted(basis.keys())
        basis_vecs = [np.asarray(basis[k], dtype=np.float64) for k in axis_ids]
        B = np.vstack(basis_vecs).T  # (d, k) orthonormal columns
        v = random_unit_vector(d, 3000 + seed)
        obs = derive_spatial_observables(v, basis)
        projections = np.dot(v, B)  # (k,)
        sigma_sq = float(np.var(projections))
        expected_l = 1.0 / (1.0 + sigma_sq)
        assert np.isclose(obs["l"], expected_l, atol=1e-12), (
            f"seed={seed}: L formula mismatch"
        )
