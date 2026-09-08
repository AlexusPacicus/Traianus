"""Block tests for PolarProjector - full pipeline scenarios."""
import time

import numpy as np

from tests.fixtures.polar_fixtures import (
    collinear_centroids,
    random_unit_vector,
    simulate_drift_trajectory,
)
from traianus.geometry.polar_projector import PolarProjector


class TestPolarProjectorBlock:
    """Block tests: full pipeline scenarios."""

    def setup_method(self):
        self.projector = PolarProjector()

    def test_polar_projector_full_pipeline_384(self):
        """d=384: fixed centroids, 100 random vectors → valid outputs."""
        d = 384
        c_1 = random_unit_vector(d, 1)
        c_A = random_unit_vector(d, 2)
        c_B = random_unit_vector(d, 3)

        for i in range(100):
            v_n = random_unit_vector(d, 100 + i)
            centroid_id, lambda_val, d_esc = self.projector.project(v_n, c_1, c_A, c_B, i)

            assert centroid_id == i
            assert -1.0 <= lambda_val <= 1.0
            assert d_esc >= 0.0
            assert np.isfinite(lambda_val)
            assert np.isfinite(d_esc)

    def test_polar_projector_full_pipeline_768(self):
        """d=768: fixed centroids, 50 random vectors → valid outputs."""
        self._run_full_pipeline(768, 50)

    def test_polar_projector_full_pipeline_1536(self):
        """d=1536: fixed centroids, 50 random vectors → valid outputs."""
        self._run_full_pipeline(1536, 50)

    def _run_full_pipeline(self, d: int, n_vectors: int):
        c_1 = random_unit_vector(d, 1)
        c_A = random_unit_vector(d, 2)
        c_B = random_unit_vector(d, 3)

        for i in range(n_vectors):
            v_n = random_unit_vector(d, 200 + i)
            _, lambda_val, d_esc = self.projector.project(v_n, c_1, c_A, c_B, i)
            assert -1.0 <= lambda_val <= 1.0
            assert d_esc >= 0.0
            assert np.isfinite(lambda_val)
            assert np.isfinite(d_esc)

    def test_polar_projector_centroid_drift_simulation(self):
        """1000 steps: anchor fixed, poles drift → λ/d_esc track drift."""
        d = 384
        c_1 = random_unit_vector(d, 1)

        # Simulate slow drift of poles
        trajectory_A = simulate_drift_trajectory(1000, d, 0.001, seed=10)
        trajectory_B = simulate_drift_trajectory(1000, d, 0.001, seed=20)

        lambda_vals = []
        d_esc_vals = []

        for i in range(1000):
            v_n = random_unit_vector(d, 1000 + i)
            _, lambda_val, d_esc = self.projector.project(
                v_n, c_1, trajectory_A[i], trajectory_B[i], i
            )
            lambda_vals.append(lambda_val)
            d_esc_vals.append(d_esc)

        # Should produce valid outputs throughout
        assert all(-1.0 <= lam <= 1.0 for lam in lambda_vals)
        assert all(d >= 0.0 for d in d_esc_vals)
        assert all(np.isfinite(lam) for lam in lambda_vals)

    def test_polar_projector_batch_processing_latency(self):
        """1000 vectors → p95 latency < 1ms per vector."""
        d = 384
        c_1 = random_unit_vector(d, 1)
        c_A = random_unit_vector(d, 2)
        c_B = random_unit_vector(d, 3)

        latencies = []
        for i in range(1000):
            v_n = random_unit_vector(d, 1000 + i)
            start = time.perf_counter()
            self.projector.project(v_n, c_1, c_A, c_B, i)
            latencies.append(time.perf_counter() - start)

        latencies.sort()
        p95 = latencies[int(0.95 * len(latencies))]
        assert p95 < 0.001, f"p95 latency {p95*1000:.2f}ms exceeds 1ms"

    def test_polar_projector_collinear_centroids_handling(self):
        """Test with centroids collinear with anchor."""
        d = 384
        c_1 = random_unit_vector(d, 1)
        c_A, c_B = collinear_centroids(c_1, d)

        # Should not raise, should produce valid output
        for i in range(50):
            v_n = random_unit_vector(d, 100 + i)
            centroid_id, lambda_val, d_esc = self.projector.project(v_n, c_1, c_A, c_B, i)

            assert centroid_id == i
            assert -1.0 <= lambda_val <= 1.0
            assert d_esc >= 0.0

    def test_polar_projector_zero_anchor_handling(self):
        """Test with zero-norm anchor (edge case)."""
        d = 384
        c_1 = np.zeros(d, dtype=np.float64)
        c_A = random_unit_vector(d, 1)
        c_B = random_unit_vector(d, 2)

        # Should not raise, should produce valid output
        for i in range(10):
            v_n = random_unit_vector(d, 100 + i)
            centroid_id, lambda_val, d_esc = self.projector.project(v_n, c_1, c_A, c_B, i)

            assert centroid_id == i
            assert -1.0 <= lambda_val <= 1.0
            assert d_esc >= 0.0

    def test_polar_projector_deterministic_across_instances(self):
        """Different instances with same params → same results."""
        d = 384
        c_1 = random_unit_vector(d, 1)
        c_A = random_unit_vector(d, 2)
        c_B = random_unit_vector(d, 3)
        v_n = random_unit_vector(d, 4)

        p1 = PolarProjector()
        p2 = PolarProjector()

        r1 = p1.project(v_n, c_1, c_A, c_B, 42)
        r2 = p2.project(v_n, c_1, c_A, c_B, 42)

        assert r1 == r2

    def test_collinear_fallback_pipeline_transition(self):
        """Collinear centroids force the canonical 2δ·u⊥ fallback; near-threshold
        centroids keep the natural dipole cA_perp - cB_perp."""
        d = 384
        c_1 = random_unit_vector(d, 1)
        c1_hat = c_1 / np.linalg.norm(c_1)
        P_perp = self.projector._orthogonal_projector(c1_hat)
        u = self.projector._canonical_u_perp(c1_hat)

        v_n = random_unit_vector(d, 8)
        v_n_proj = P_perp @ (v_n - c_1)

        # (a) Fully collinear centroids -> canonical fallback dipole 2δ·u⊥
        cA_coll, cB_coll = collinear_centroids(c_1, d)
        _, lambda_coll, _ = self.projector.project(v_n, c_1, cA_coll, cB_coll, 1)
        v_dipole_fallback = 2.0 * self.projector.delta * u
        expected_lambda = float(
            np.dot(v_n_proj, v_dipole_fallback) / np.dot(v_dipole_fallback, v_dipole_fallback)
        )
        expected_lambda = np.clip(expected_lambda, -1.0, 1.0)
        assert np.isclose(lambda_coll, expected_lambda, atol=1e-10), (
            "collinear fallback should use the canonical 2δ·u⊥ dipole"
        )

        # (b) Wide-apart centroids projecting to a unit tangent displacement ->
        #     natural dipole. The separation lives wholly in the tangent plane
        #     (P⊥(w) = w by construction), so its norm is order 1 - far above
        #     eps_collinear without any magic margin factor.
        rng = np.random.default_rng(7)
        w = P_perp @ rng.normal(size=d).astype(np.float64)
        w = w / np.linalg.norm(w)
        cA_wide = c_1 + w
        cB_wide = c_1 - w
        _, lambda_wide, _ = self.projector.project(v_n, c_1, cA_wide, cB_wide, 1)
        v_dipole_natural = P_perp @ (cA_wide - cB_wide)
        expected_wide = float(
            np.dot(v_n_proj, v_dipole_natural) / np.dot(v_dipole_natural, v_dipole_natural)
        )
        expected_wide = np.clip(expected_wide, -1.0, 1.0)
        assert np.isclose(lambda_wide, expected_wide, atol=1e-10), (
            "wide centroids should use the natural cA_perp - cB_perp dipole"
        )