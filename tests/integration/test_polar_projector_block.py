"""Block tests for PolarProjector - full pipeline scenarios."""
import numpy as np
import time
from traianus.geometry.polar_projector import PolarProjector
from tests.fixtures.polar_fixtures import random_unit_vector, simulate_drift_trajectory, collinear_centroids


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