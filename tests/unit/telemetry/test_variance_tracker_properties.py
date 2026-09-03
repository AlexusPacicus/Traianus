"""Property tests for VarianceTracker EWMA invariants.

Deterministic seeded sweeps (numpy + stdlib only): monotonic decay for
constant input, scale invariance of the drift ratio, bounded variance for
bounded input, non-negativity, and mean convergence.
"""
import numpy as np

from traianus.telemetry.variance_tracker import VarianceTracker


class TestVarianceTrackerProperties:
    """Property tests for EWMA invariants."""

    def test_ewma_monotonic_for_constant_input(self):
        """Constant input -> variance monotonically decreases after first sample."""
        for alpha in (0.01, 0.05, 0.2, 0.5):
            for value in (-10.0, 0.0, 3.5):
                tracker = VarianceTracker(alpha=alpha)
                variances = []
                for i in range(50):
                    tracker.update(value, value)
                    if i > 0:  # First sample has var=0
                        variances.append(tracker.var_lambda)
                for i in range(1, len(variances)):
                    assert variances[i] <= variances[i - 1] + 1e-12

    def test_drift_ratio_scale_invariant(self):
        """Scaling both inputs by same factor -> drift ratio invariant."""
        for alpha in (0.05, 0.2):
            for scale in (0.1, 2.0, 10.0):
                tracker1 = VarianceTracker(alpha=alpha)
                tracker2 = VarianceTracker(alpha=alpha)
                rng = np.random.default_rng(42)
                for _ in range(100):
                    x = float(rng.normal(0, 1))
                    tracker1.update(x, x)
                    tracker2.update(x * scale, x * scale)
                ratio1 = tracker1.drift_ratio
                ratio2 = tracker2.drift_ratio
                if np.isfinite(ratio1) and np.isfinite(ratio2):
                    assert np.isclose(ratio1, ratio2, rtol=1e-10)

    def test_ewma_bounded_for_bounded_input(self):
        """Bounded input -> bounded variance."""
        for alpha in (0.05, 0.3):
            for bound in (1.0, 10.0):
                tracker = VarianceTracker(alpha=alpha)
                rng = np.random.default_rng(42)
                for _ in range(1000):
                    x = float(rng.uniform(-bound, bound))
                    tracker.update(x, x)
                # Variance of bounded variable cannot exceed bound^2
                assert tracker.var_lambda <= bound ** 2 + 1e-6
                assert tracker.var_esc <= bound ** 2 + 1e-6

    def test_variance_nonnegative(self):
        """Variance always non-negative."""
        for alpha in (0.05, 0.3):
            tracker = VarianceTracker(alpha=alpha)
            rng = np.random.default_rng(42)
            for _ in range(100):
                x = float(rng.normal(0, 5))
                tracker.update(x, x)
                assert tracker.var_lambda >= -1e-12  # Numerical tolerance
                assert tracker.var_esc >= -1e-12

    def test_mean_converges_to_expected(self):
        """Running mean converges to expected value for stationary input."""
        for alpha in (0.02, 0.05, 0.1):
            tracker = VarianceTracker(alpha=alpha)
            true_mean = 2.5
            rng = np.random.default_rng(42)
            for _ in range(20000):
                x = float(rng.normal(true_mean, 1.0))
                tracker.update(x, x)
            # EWMA mean has inherent variance ~alpha/(2-alpha)*sigma^2;
            # generous tolerance for small alpha.
            assert np.isclose(tracker.mu_lambda, true_mean, atol=0.5)
