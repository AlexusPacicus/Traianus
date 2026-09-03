"""Block tests: PolarProjector → VarianceTracker integration."""
import numpy as np

from tests.fixtures.polar_fixtures import random_unit_vector
from traianus.geometry.polar_projector import PolarProjector
from traianus.telemetry.variance_tracker import VarianceTracker


class TestPolarTelemetryIntegration:
    """Block tests: projector → tracker flow."""

    def setup_method(self):
        self.projector = PolarProjector()
        self.tracker = VarianceTracker(alpha=0.05)

    def test_single_spike_dampened(self):
        """1 spike in d_esc among 100 normal → ratio stays high (no false trigger with high threshold)."""
        d = 384
        c_1 = random_unit_vector(d, 1)
        c_A = random_unit_vector(d, 2)
        c_B = random_unit_vector(d, 3)

        # 100 normal events
        for i in range(100):
            v_n = random_unit_vector(d, 100 + i)
            _, lambda_val, d_esc = self.projector.project(v_n, c_1, c_A, c_B, i)
            self.tracker.update(lambda_val, d_esc)

        # 1 spike event (amplified d_esc)
        v_spike = random_unit_vector(d, 999)
        _, lambda_val, d_esc = self.projector.project(v_spike, c_1, c_A, c_B, 999)
        self.tracker.update(lambda_val, d_esc * 10)

        # Normal ratio ~200. With high threshold (500), single spike won't trigger
        assert not self.tracker.check_drift_ratio(threshold=500.0)

    def test_sustained_burst_lowers_ratio(self):
        """20 sustained high d_esc events (vectors opposite anchor) → ratio DROPS."""
        d = 384
        c_1 = random_unit_vector(d, 1)
        c_A = random_unit_vector(d, 2)
        c_B = random_unit_vector(d, 3)

        # Baseline (normal traffic)
        for i in range(50):
            v_n = random_unit_vector(d, 100 + i)
            _, lambda_val, d_esc = self.projector.project(v_n, c_1, c_A, c_B, i)
            self.tracker.update(lambda_val, d_esc)

        baseline_ratio = self.tracker.drift_ratio
        assert baseline_ratio > 100  # Normal traffic has high ratio

        # Sustained burst: vectors far from anchor → high d_esc variance
        for i in range(20):
            v_n = -c_1 + np.random.default_rng(1000 + i).normal(scale=0.1, size=d).astype(np.float64)
            v_n = v_n / np.linalg.norm(v_n)
            _, lambda_val, d_esc = self.projector.project(v_n, c_1, c_A, c_B, 200 + i)
            self.tracker.update(lambda_val, d_esc)

        burst_ratio = self.tracker.drift_ratio
        # Burst increases d_esc variance, ratio DROPS significantly
        assert burst_ratio < baseline_ratio
        assert burst_ratio < 10  # Much lower than baseline

    def test_lambda_variance_drives_drift(self):
        """High λ variance (alternating c_A/c_B) with stable d_esc → ratio INCREASES dramatically."""
        d = 384
        c_1 = random_unit_vector(d, 1)
        c_A = random_unit_vector(d, 2)
        c_B = random_unit_vector(d, 3)

        for i in range(100):
            # Alternate between aligned and anti-aligned with dipole
            if i % 2 == 0:
                v_n = c_A + np.random.default_rng(i).normal(scale=0.01, size=d).astype(np.float64)
            else:
                v_n = c_B + np.random.default_rng(i).normal(scale=0.01, size=d).astype(np.float64)
            v_n = v_n / np.linalg.norm(v_n)

            _, lambda_val, d_esc = self.projector.project(v_n, c_1, c_A, c_B, i)
            self.tracker.update(lambda_val, d_esc)

        # High lambda variance should drive ratio up dramatically
        assert self.tracker.var_lambda > 0.1
        # Threshold of 500: normal ~200, high lambda variance ~5000+
        assert self.tracker.check_drift_ratio(threshold=500.0)

    def test_mixed_traffic_realistic_false_positive_rate(self):
        """Realistic Poisson traffic → false positive rate < 5% with high threshold."""
        d = 384
        c_1 = random_unit_vector(d, 1)
        c_A = random_unit_vector(d, 2)
        c_B = random_unit_vector(d, 3)

        np.random.seed(42)
        false_positives = 0
        total_windows = 0

        for window in range(100):
            tracker = VarianceTracker(alpha=0.05)

            # Normal traffic (Poisson rate)
            n_events = np.random.poisson(50)
            for i in range(n_events):
                v_n = random_unit_vector(d, window * 1000 + i)
                _, lambda_val, d_esc = self.projector.project(v_n, c_1, c_A, c_B, i)
                tracker.update(lambda_val, d_esc)

            total_windows += 1
            # High threshold (500) to avoid false positives on normal traffic
            if tracker.check_drift_ratio(threshold=500.0):
                false_positives += 1

        fp_rate = false_positives / total_windows
        assert fp_rate < 0.05, f"False positive rate {fp_rate:.2%} exceeds 5%"

    def test_band_collapse_alert_low_end_to_end(self):
        """ADR-025 §2.2: burst opposite the anchor collapses ratio -> ALERT_LOW."""
        d = 384
        c_1 = random_unit_vector(d, 1)
        c_A = random_unit_vector(d, 2)
        c_B = random_unit_vector(d, 3)

        for i in range(50):
            v_n = random_unit_vector(d, 100 + i)
            _, lambda_val, d_esc = self.projector.project(v_n, c_1, c_A, c_B, i)
            self.tracker.update(lambda_val, d_esc)
        assert self.tracker.update_alert() == VarianceTracker.NOMINAL

        for i in range(60):
            v_n = -c_1 + np.random.default_rng(1000 + i).normal(scale=0.1, size=d).astype(np.float64)
            v_n = v_n / np.linalg.norm(v_n)
            _, lambda_val, d_esc = self.projector.project(v_n, c_1, c_A, c_B, 200 + i)
            self.tracker.update(lambda_val, d_esc)

        assert self.tracker.update_alert() == VarianceTracker.ALERT_LOW

    def test_band_high_alert_end_to_end(self):
        """ADR-025 §2.2: alternating dipole alignment -> ALERT_HIGH."""
        d = 384
        c_1 = random_unit_vector(d, 1)
        c_A = random_unit_vector(d, 2)
        c_B = random_unit_vector(d, 3)

        for i in range(100):
            if i % 2 == 0:
                v_n = c_A + np.random.default_rng(i).normal(scale=0.01, size=d).astype(np.float64)
            else:
                v_n = c_B + np.random.default_rng(i).normal(scale=0.01, size=d).astype(np.float64)
            v_n = v_n / np.linalg.norm(v_n)
            _, lambda_val, d_esc = self.projector.project(v_n, c_1, c_A, c_B, i)
            self.tracker.update(lambda_val, d_esc)

        assert self.tracker.update_alert() == VarianceTracker.ALERT_HIGH

    def test_reorthogonalization_guarantee_on_reset(self):
        """ADR-025 §2.2: Gram-Schmidt rebuild after alert satisfies u⊥ · u == 0."""
        d = 384
        c_1 = random_unit_vector(d, 1)
        c_A = random_unit_vector(d, 2)
        c_B = random_unit_vector(d, 3)

        for i in range(100):
            if i % 2 == 0:
                v_n = c_A + np.random.default_rng(i).normal(scale=0.01, size=d).astype(np.float64)
            else:
                v_n = c_B + np.random.default_rng(i).normal(scale=0.01, size=d).astype(np.float64)
            v_n = v_n / np.linalg.norm(v_n)
            _, lambda_val, d_esc = self.projector.project(v_n, c_1, c_A, c_B, i)
            self.tracker.update(lambda_val, d_esc)
        assert self.tracker.update_alert() == VarianceTracker.ALERT_HIGH

        # Recalibration reset: rebuild u⊥ from the data plane via the
        # projector's deterministic Gram-Schmidt, then verify orthogonality.
        c1_hat = c_1 / np.linalg.norm(c_1)
        u_perp = self.projector._canonical_u_perp(c1_hat)
        assert VarianceTracker.verify_orthogonal_reset(c1_hat, u_perp)
        self.tracker.reset()
        assert self.tracker.alert_state == VarianceTracker.NOMINAL

    def test_drift_detection_resets_after_calibration(self):
        """After drift detected, reset() clears state for new calibration."""
        d = 384
        c_1 = random_unit_vector(d, 1)
        c_A = random_unit_vector(d, 2)
        c_B = random_unit_vector(d, 3)

        # Generate high lambda variance drift (alternating c_A/c_B)
        for i in range(30):
            if i % 2 == 0:
                v_n = c_A + np.random.default_rng(1000 + i).normal(scale=0.01, size=d).astype(np.float64)
            else:
                v_n = c_B + np.random.default_rng(1000 + i).normal(scale=0.01, size=d).astype(np.float64)
            v_n = v_n / np.linalg.norm(v_n)
            _, lambda_val, d_esc = self.projector.project(v_n, c_1, c_A, c_B, i)
            self.tracker.update(lambda_val, d_esc)

        # Should trigger with high threshold
        assert self.tracker.check_drift_ratio(threshold=500.0)

        # Reset for new calibration period
        self.tracker.reset()

        # Normal traffic should not trigger (ratio ~200 < 500)
        for i in range(50):
            v_n = random_unit_vector(d, 2000 + i)
            _, lambda_val, d_esc = self.projector.project(v_n, c_1, c_A, c_B, i)
            self.tracker.update(lambda_val, d_esc)

        assert not self.tracker.check_drift_ratio(threshold=500.0)