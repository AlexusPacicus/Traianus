"""Unit tests for ParabolicCorrector - 3-point quadratic reconstruction."""
import time

import numpy as np

from traianus.geometry.parabolic import ParabolicCorrector


class TestParabolicCorrectorReconstruction:
    """Exact reconstruction at t=0.0, t=0.5, t=1.0."""

    def setup_method(self) -> None:
        self.corrector = ParabolicCorrector()
        self.rng = np.random.default_rng(123)
        self.d = 8
        self.v_ini = self.rng.normal(size=self.d).astype(np.float64)
        self.v_mid = self.rng.normal(size=self.d).astype(np.float64)
        self.v_fin = self.rng.normal(size=self.d).astype(np.float64)

    def test_reconstruction_exact_at_t0(self) -> None:
        v = self.corrector.reconstruct(self.v_ini, self.v_mid, self.v_fin, 0.0)
        np.testing.assert_allclose(v, self.v_ini, atol=1e-14)

    def test_reconstruction_exact_at_t1(self) -> None:
        v = self.corrector.reconstruct(self.v_ini, self.v_mid, self.v_fin, 1.0)
        np.testing.assert_allclose(v, self.v_fin, atol=1e-14)

    def test_reconstruction_exact_at_t05(self) -> None:
        v = self.corrector.reconstruct(self.v_ini, self.v_mid, self.v_fin, 0.5)
        np.testing.assert_allclose(v, self.v_mid, atol=1e-14)

    def test_correction_zero_at_endpoints(self) -> None:
        D = self.corrector.deviation_vector(self.v_ini, self.v_mid, self.v_fin)
        for t in (0.0, 1.0):
            coeff = 4.0 * t * (1.0 - t)
            np.testing.assert_allclose(coeff * D, 0.0, atol=1e-15)

    def test_correction_symmetric(self) -> None:
        D = self.corrector.deviation_vector(self.v_ini, self.v_mid, self.v_fin)
        for t in (0.1, 0.2, 0.3, 0.4):
            c_left = 4.0 * t * (1.0 - t) * D
            c_right = 4.0 * (1.0 - t) * t * D
            np.testing.assert_allclose(c_left, c_right, atol=1e-15)

    def test_trajectory_is_continuous(self) -> None:
        for t in np.linspace(0.0, 1.0, 100):
            v = self.corrector.reconstruct(self.v_ini, self.v_mid, self.v_fin, float(t))
            assert np.all(np.isfinite(v))

    def test_linear_degeneracy_when_no_curvature(self) -> None:
        v_mid_linear = 0.5 * (self.v_ini + self.v_fin)
        for t in np.linspace(0.0, 1.0, 50):
            v = self.corrector.reconstruct(self.v_ini, v_mid_linear, self.v_fin, float(t))
            v_linear = (1.0 - t) * self.v_ini + t * self.v_fin
            np.testing.assert_allclose(v, v_linear, atol=1e-14)


class TestParabolicCorrectorDeviationVector:
    """D_mid = v_mid - (v_ini + v_fin) / 2."""

    def setup_method(self) -> None:
        self.corrector = ParabolicCorrector()

    def test_deviation_vector_zero_when_collinear(self) -> None:
        v_ini = np.array([0.0, 0.0, 0.0])
        v_fin = np.array([2.0, 0.0, 0.0])
        v_mid = np.array([1.0, 0.0, 0.0])
        D = self.corrector.deviation_vector(v_ini, v_mid, v_fin)
        np.testing.assert_allclose(D, 0.0, atol=1e-15)

    def test_deviation_vector_nonzero_when_curved(self) -> None:
        v_ini = np.array([0.0, 0.0])
        v_fin = np.array([1.0, 0.0])
        v_mid = np.array([0.5, 1.0])
        D = self.corrector.deviation_vector(v_ini, v_mid, v_fin)
        np.testing.assert_allclose(D, np.array([0.0, 1.0]), atol=1e-14)


class TestParabolicCorrectorBatch:
    """Batch reconstruction."""

    def test_batch_matches_individual(self) -> None:
        corrector = ParabolicCorrector()
        rng = np.random.default_rng(456)
        d = 16
        v_ini = rng.normal(size=d)
        v_mid = rng.normal(size=d)
        v_fin = rng.normal(size=d)
        t_values = [0.0, 0.25, 0.5, 0.75, 1.0]
        batch = corrector.reconstruct_batch(v_ini, v_mid, v_fin, t_values)
        for i, t in enumerate(t_values):
            individual = corrector.reconstruct(v_ini, v_mid, v_fin, t)
            np.testing.assert_allclose(batch[i], individual, atol=1e-15)


class TestParabolicCorrectorLatency:
    """Computation budget: single point in 384D < 1ms."""

    def test_latency_budget(self) -> None:
        corrector = ParabolicCorrector()
        rng = np.random.default_rng(789)
        d = 384
        v_ini = rng.normal(size=d)
        v_mid = rng.normal(size=d)
        v_fin = rng.normal(size=d)
        t0 = time.perf_counter()
        for _ in range(100):
            corrector.reconstruct(v_ini, v_mid, v_fin, 0.37)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        assert elapsed_ms < 100.0, f"100 points in 384D took {elapsed_ms:.1f}ms (>100ms)"
