"""Unit tests for VarianceTracker - EWMA variance tracking with Welford."""
import pytest
import numpy as np
from traianus.telemetry.variance_tracker import VarianceTracker


class TestVarianceTrackerUnit:
    """Unit tests for EWMA variance tracking."""

    def setup_method(self):
        self.tracker = VarianceTracker(alpha=0.05)

    def test_ewma_initial_state_zero(self):
        """Initial state: all zeros, not initialized."""
        assert self.tracker.var_lambda == 0.0
        assert self.tracker.var_esc == 0.0
        assert self.tracker.mu_lambda == 0.0
        assert self.tracker.mu_esc == 0.0
        assert not self.tracker.check_drift_ratio(1.0)

    def test_ewma_alpha_default_005(self):
        """Default alpha is 0.05."""
        tracker = VarianceTracker()
        assert tracker.alpha == 0.05

    def test_ewma_alpha_validation(self):
        """Alpha must be in (0, 1)."""
        with pytest.raises(ValueError):
            VarianceTracker(alpha=0.0)
        with pytest.raises(ValueError):
            VarianceTracker(alpha=1.0)
        with pytest.raises(ValueError):
            VarianceTracker(alpha=-0.1)
        with pytest.raises(ValueError):
            VarianceTracker(alpha=1.5)

    def test_update_first_sample_initializes_mean_zero_var(self):
        """First sample: mean = x, var = 0."""
        self.tracker.update(1.0, 0.5)
        assert self.tracker.mu_lambda == 1.0
        assert self.tracker.var_lambda == 0.0
        assert self.tracker.mu_esc == 0.5
        assert self.tracker.var_esc == 0.0

    def test_update_second_sample_updates_mean_and_var(self):
        """Second sample: mean moves toward x, var becomes positive."""
        self.tracker.update(1.0, 1.0)
        self.tracker.update(2.0, 1.0)
        
        # mu_lambda = 1.0 + 0.05 * (2.0 - 1.0) = 1.05
        assert np.isclose(self.tracker.mu_lambda, 1.05)
        # var_lambda = 0.05 * (2.0 - 1.05)^2 = 0.05 * 0.9025 = 0.045125
        assert np.isclose(self.tracker.var_lambda, 0.045125, rtol=1e-6)

    def test_check_drift_ratio_below_threshold_false(self):
        """Low variance → ratio below threshold → False."""
        self.tracker.update(1.0, 1.0)
        self.tracker.update(1.0, 1.0)
        assert not self.tracker.check_drift_ratio(10.0)

    def test_check_drift_ratio_above_threshold_true(self):
        """High lambda variance, low esc variance → ratio exceeds threshold."""
        # Alternate lambda values to maintain high variance, vary esc slightly
        for i in range(100):
            lambda_val = 5.0 if i % 2 == 0 else -5.0
            esc_val = 0.1 if i % 3 == 0 else 0.2  # Small variation in esc
            self.tracker.update(lambda_val, esc_val)
        assert self.tracker.check_drift_ratio(1.0)

    def test_lambda_esc_independent_tracking(self):
        """Lambda and esc trackers evolve independently."""
        # Update only lambda
        for _ in range(10):
            self.tracker.update(5.0, 0.1)
        var_lambda_1 = self.tracker.var_lambda
        var_esc_1 = self.tracker.var_esc

        # Update only esc
        for _ in range(10):
            self.tracker.update(0.0, 5.0)
        var_lambda_2 = self.tracker.var_lambda
        var_esc_2 = self.tracker.var_esc

        assert var_lambda_2 > var_lambda_1
        assert var_esc_2 > var_esc_1

    def test_ewma_convergence_constant_input(self):
        """Constant input → variance → 0."""
        for _ in range(1000):
            self.tracker.update(1.0, 1.0)
        assert self.tracker.var_lambda < 1e-10
        assert self.tracker.var_esc < 1e-10

    def test_ewma_reacts_to_step_change(self):
        """Step change → variance spikes then decays."""
        # Stable at 0
        for _ in range(100):
            self.tracker.update(0.0, 0.0)
        var_before = self.tracker.var_lambda

        # Step to 10
        for _ in range(10):
            self.tracker.update(10.0, 0.0)
        var_spike = self.tracker.var_lambda

        # Return to 0
        for _ in range(100):
            self.tracker.update(0.0, 0.0)
        var_after = self.tracker.var_lambda

        assert var_spike > var_before
        assert var_after < var_spike

    def test_drift_ratio_property(self):
        """drift_ratio = var_lambda / var_esc when var_esc > 0."""
        self.tracker.update(1.0, 0.5)
        self.tracker.update(2.0, 1.5)  # Different esc values to build variance
        
        expected = self.tracker.var_lambda / self.tracker.var_esc
        assert np.isclose(self.tracker.drift_ratio, expected)

    def test_drift_ratio_infinite_when_esc_zero(self):
        """drift_ratio = inf when var_esc = 0 and var_lambda > 0."""
        self.tracker.update(1.0, 1.0)
        self.tracker.update(2.0, 1.0)
        # var_esc should be 0 (constant input)
        assert self.tracker.drift_ratio == float('inf')

    def test_drift_ratio_zero_when_both_zero(self):
        """drift_ratio = 0 when both variances are 0."""
        tracker = VarianceTracker()
        assert tracker.drift_ratio == 0.0

    def test_reset_clears_all_state(self):
        """reset() clears all internal state."""
        for _ in range(10):
            self.tracker.update(5.0, 5.0)
        
        self.tracker.reset()
        
        assert self.tracker.var_lambda == 0.0
        assert self.tracker.var_esc == 0.0
        assert self.tracker.mu_lambda == 0.0
        assert self.tracker.mu_esc == 0.0
        assert not self.tracker.check_drift_ratio(1.0)

    def test_band_defaults_adr025(self):
        """ADR-025 defaults: θ_lower=10, θ_upper=500, Δ=2."""
        tracker = VarianceTracker()
        assert tracker.theta_lower == 10.0
        assert tracker.theta_upper == 500.0
        assert tracker.hysteresis == 2.0
        assert tracker.alert_state == VarianceTracker.NOMINAL

    def test_band_invalid_params_rejected(self):
        """0 < θ_lower < θ_upper and 0 <= Δ < (θ_upper-θ_lower)/2 enforced."""
        with pytest.raises(ValueError):
            VarianceTracker(theta_lower=500.0, theta_upper=10.0)
        with pytest.raises(ValueError):
            VarianceTracker(theta_lower=10.0, theta_upper=500.0, hysteresis=500.0)
        with pytest.raises(ValueError):
            VarianceTracker(theta_lower=-1.0)

    def test_check_band_unevaluable_is_nominal(self):
        """Fresh tracker (no signal) evaluates NOMINAL, never alerts."""
        assert self.tracker.check_band() == VarianceTracker.NOMINAL
        assert self.tracker.update_alert() == VarianceTracker.NOMINAL

    def test_check_band_high_on_lambda_concentration(self):
        """Alternating c_A/c_B drives ratio above θ_upper -> ALERT_HIGH."""
        for i in range(100):
            lambda_val = 5.0 if i % 2 == 0 else -5.0
            esc_val = 0.1 if i % 3 == 0 else 0.2
            self.tracker.update(lambda_val, esc_val)
        assert self.tracker.check_band() == VarianceTracker.ALERT_HIGH
        assert self.tracker.update_alert() == VarianceTracker.ALERT_HIGH

    def test_check_band_low_on_burst_collapse(self):
        """Burst-dominated stream collapses ratio below θ_lower -> ALERT_LOW."""
        # Baseline first so both trackers are initialized
        for i in range(20):
            self.tracker.update(0.5 if i % 2 == 0 else -0.5, 0.5)
        # Burst: lambda pinned near constant, esc highly dispersed
        rng = np.random.default_rng(7)
        for _ in range(200):
            self.tracker.update(0.01, float(rng.normal(0, 5)))
        assert self.tracker.check_band() == VarianceTracker.ALERT_LOW
        assert self.tracker.update_alert() == VarianceTracker.ALERT_LOW

    def test_hysteresis_latch_prevents_oscillation(self):
        """Latched alert persists inside the hysteresis margin (white-box)."""
        tracker = VarianceTracker(theta_lower=10.0, theta_upper=500.0, hysteresis=2.0)
        tracker._lambda_initialized = True
        tracker._esc_initialized = True
        # Latch HIGH, then steer ratio to 499: inside band edge but above
        # the clear line (θ_upper - Δ = 498) -> latch MUST hold.
        tracker._alert = VarianceTracker.ALERT_HIGH
        tracker._var_lambda = 499.0
        tracker._var_esc = 1.0
        assert tracker.check_band() == VarianceTracker.NOMINAL
        assert tracker.update_alert() == VarianceTracker.ALERT_HIGH
        # Latch LOW, ratio at 11: above θ_lower but below θ_lower + Δ = 12.
        tracker._alert = VarianceTracker.ALERT_LOW
        tracker._var_lambda = 11.0
        tracker._var_esc = 1.0
        assert tracker.check_band() == VarianceTracker.NOMINAL
        assert tracker.update_alert() == VarianceTracker.ALERT_LOW
        # Ratio strictly inside (12, 498) clears either latch.
        tracker._var_lambda = 100.0
        assert tracker.update_alert() == VarianceTracker.NOMINAL

    def test_latched_alert_clears_inside_clear_band(self):
        """After latch, nominal traffic returning inside (θl+Δ, θu-Δ) clears."""
        for i in range(100):
            self.tracker.update(5.0 if i % 2 == 0 else -5.0, 0.1 if i % 3 == 0 else 0.2)
        assert self.tracker.update_alert() == VarianceTracker.ALERT_HIGH
        # Steer back to nominal regime: balanced traffic drives ratio into band
        for i in range(500):
            self.tracker.update(0.5 if i % 2 == 0 else -0.5, 0.5 if i % 3 == 0 else 0.6)
        state = self.tracker.update_alert()
        assert state == VarianceTracker.NOMINAL
        assert self.tracker.alert_state == VarianceTracker.NOMINAL

    def test_latched_alert_holds_when_ratio_unevaluable(self):
        """Latched alert + zero denominator keeps the latch (fail-closed)."""
        self.tracker._lambda_initialized = True
        self.tracker._esc_initialized = True
        self.tracker._alert = VarianceTracker.ALERT_LOW
        self.tracker._var_lambda = 1.0
        self.tracker._var_esc = 0.0
        assert self.tracker.update_alert() == VarianceTracker.ALERT_LOW

    def test_reset_clears_latched_alert(self):
        """reset() clears EWMA state AND the latched alert."""
        for i in range(100):
            self.tracker.update(5.0 if i % 2 == 0 else -5.0, 0.1 if i % 3 == 0 else 0.2)
        assert self.tracker.update_alert() == VarianceTracker.ALERT_HIGH
        self.tracker.reset()
        assert self.tracker.alert_state == VarianceTracker.NOMINAL
        assert self.tracker.check_band() == VarianceTracker.NOMINAL

    def test_verify_orthogonal_reset_true(self):
        """Gram-Schmidt rebuilt u⊥ satisfies u⊥ · û == 0 within tol."""
        rng = np.random.default_rng(3)
        u = rng.normal(size=384).astype(np.float64)
        u = u / np.linalg.norm(u)
        k = int(np.argmin(np.abs(u)))
        e_k = np.zeros_like(u)
        e_k[k] = 1.0
        u_perp = e_k - float(np.dot(e_k, u)) * u
        u_perp = u_perp / np.linalg.norm(u_perp)
        assert VarianceTracker.verify_orthogonal_reset(u, u_perp)

    def test_verify_orthogonal_reset_false(self):
        """Non-orthogonal pair fails verification."""
        u = np.array([1.0, 0.0, 0.0])
        u_perp = np.array([0.5, 0.5, 0.0])
        assert not VarianceTracker.verify_orthogonal_reset(u, u_perp)

    def test_verify_orthogonal_reset_degenerate(self):
        """Zero reference axis fails closed."""
        assert not VarianceTracker.verify_orthogonal_reset(
            np.zeros(4), np.ones(4)
        )

    def test_multiple_trackers_independent(self):
        """Multiple tracker instances are independent."""
        t1 = VarianceTracker(alpha=0.05)
        t2 = VarianceTracker(alpha=0.05)

        # Build variance with varying inputs
        for i in range(10):
            t1.update(10.0 if i % 2 == 0 else -10.0, 1.0)
            t2.update(1.0, 1.0)

        assert t1.var_lambda > t2.var_lambda