"""EWMA variance tracker with bidirectional Schmitt Trigger (ADR-025 §2.2)."""

import numpy as np
from numpy.typing import NDArray


class VarianceTracker:
    """
    Tracks independent EWMA variances for lambda (affective voltage)
    and d_esc (escape distance) using Welford online algorithm.

    Update rule per sample:
        μₜ = (1 - α) * μₜ₋₁ + α * xₜ
        σ²ₜ = (1 - α) * σ²ₜ₋₁ + α * (xₜ - μₜ)²

    Band diagnosis (Schmitt Trigger, ADR-025 §2.2) over the ratio
    R = σ²_λ / σ²_esc:
        Alert  = (R > θ_upper) ∨ (R < θ_lower)
        Clear  = θ_lower + Δ < R < θ_upper - Δ   (hysteresis, latched)

    The lower band captures ratio collapse from misaligned bursts or
    semantic injection (denominator dispersion); the upper band captures
    anomalous concentration on the current semantic axis.

    This implements an exponentially weighted moving average of the
    squared deviations from the running mean, which is mathematically
    rigorous for continuous streams and avoids false positives from
    scale changes.
    """

    NOMINAL = "NOMINAL"
    ALERT_HIGH = "ALERT_HIGH"
    ALERT_LOW = "ALERT_LOW"

    def __init__(
        self,
        alpha: float = 0.05,
        theta_lower: float = 10.0,
        theta_upper: float = 500.0,
        hysteresis: float = 2.0,
    ) -> None:
        """
        Initialize VarianceTracker.

        Args:
            alpha: EWMA smoothing factor in (0, 1). Default 0.05.
                   Lower = more smoothing, higher = more responsive.
            theta_lower: Lower band edge; ratio collapse below it alerts
                (misaligned burst / semantic injection). Default 10.0.
            theta_upper: Upper band edge; ratio above it alerts (anomalous
                concentration on the semantic axis). Default 500.0.
            hysteresis: Hysteresis margin Δ; a latched alert clears only
                inside (θ_lower + Δ, θ_upper - Δ). Default 2.0.
        """
        if not 0 < alpha < 1:
            raise ValueError("alpha must be in (0, 1)")
        if not 0 < theta_lower < theta_upper:
            raise ValueError("require 0 < theta_lower < theta_upper")
        if not 0 <= hysteresis < (theta_upper - theta_lower) / 2:
            raise ValueError("hysteresis must satisfy 0 <= Δ < (θ_upper - θ_lower)/2")
        self.alpha = alpha
        self.theta_lower = theta_lower
        self.theta_upper = theta_upper
        self.hysteresis = hysteresis

        # Lambda (affective voltage) tracking
        self._mu_lambda = 0.0
        self._var_lambda = 0.0
        self._lambda_initialized = False

        # Escape distance tracking
        self._mu_esc = 0.0
        self._var_esc = 0.0
        self._esc_initialized = False

        # Latched alert state for hysteresis (Schmitt Trigger)
        self._alert: str = self.NOMINAL

    def update(self, lambda_val: float, d_esc: float) -> None:
        """
        Update both trackers with new observations.

        Args:
            lambda_val: Affective voltage λ ∈ [-1, 1].
            d_esc: Escape distance ≥ 0.
        """
        # Lambda tracker: Welford online mean + EWMA of squared deviation
        if not self._lambda_initialized:
            self._mu_lambda = lambda_val
            self._var_lambda = 0.0
            self._lambda_initialized = True
        else:
            # Update mean first
            delta = lambda_val - self._mu_lambda
            self._mu_lambda += self.alpha * delta
            # Then variance with NEW mean (Welford-style)
            self._var_lambda = (
                (1 - self.alpha) * self._var_lambda
                + self.alpha * (lambda_val - self._mu_lambda) ** 2
            )

        # Escape distance tracker: independent Welford + EWMA
        if not self._esc_initialized:
            self._mu_esc = d_esc
            self._var_esc = 0.0
            self._esc_initialized = True
        else:
            delta = d_esc - self._mu_esc
            self._mu_esc += self.alpha * delta
            self._var_esc = (
                (1 - self.alpha) * self._var_esc
                + self.alpha * (d_esc - self._mu_esc) ** 2
            )

    def check_drift_ratio(self, threshold: float) -> bool:
        """
        Legacy single-threshold upper check (stateless, no latch).

        Return True if λ variance / esc variance exceeds threshold.
        Returns False if not initialized or esc variance is zero (no signal).
        Preserved for backward compatibility; new code SHOULD use
        :meth:`check_band` / :meth:`update_alert` (ADR-025 §2.2).

        Args:
            threshold: Drift ratio threshold.

        Returns:
            True if drift detected, False otherwise.
        """
        if not self._esc_initialized or not self._lambda_initialized:
            return False
        if self._var_esc <= 0:
            return False
        return (self._var_lambda / self._var_esc) > threshold

    def _ratio_or_none(self) -> float | None:
        """Current ratio, or None when it cannot be evaluated."""
        if not self._esc_initialized or not self._lambda_initialized:
            return None
        if self._var_esc <= 0:
            return None
        return self._var_lambda / self._var_esc

    def check_band(self) -> str:
        """
        Stateless band evaluation (no latch).

        Returns:
            NOMINAL if θ_lower <= R <= θ_upper,
            ALERT_HIGH if R > θ_upper,
            ALERT_LOW if R < θ_lower.
            Unevaluable ratio (uninitialized / zero denominator) is NOMINAL.
        """
        ratio = self._ratio_or_none()
        if ratio is None:
            return self.NOMINAL
        if ratio > self.theta_upper:
            return self.ALERT_HIGH
        if ratio < self.theta_lower:
            return self.ALERT_LOW
        return self.NOMINAL

    def update_alert(self) -> str:
        """
        Latched Schmitt Trigger evaluation with hysteresis.

        A fresh out-of-band ratio latches the corresponding alert; a
        latched alert clears only when the ratio returns strictly inside
        (θ_lower + Δ, θ_upper - Δ), preventing limit-cycle oscillation.

        Returns:
            Current alert state after evaluation.
        """
        state = self.check_band()
        if self._alert == self.NOMINAL:
            self._alert = state
            return self._alert
        ratio = self._ratio_or_none()
        if ratio is None:
            return self._alert
        if self.theta_lower + self.hysteresis < ratio < self.theta_upper - self.hysteresis:
            self._alert = self.NOMINAL
        return self._alert

    @property
    def alert_state(self) -> str:
        """Latched alert state (NOMINAL | ALERT_HIGH | ALERT_LOW)."""
        return self._alert

    @staticmethod
    def verify_orthogonal_reset(
        u: NDArray[np.float64],
        u_perp: NDArray[np.float64],
        tol: float = 1e-9,
    ) -> bool:
        """
        Orthogonality guarantee on recalibration reset (ADR-025 §2.2).

        After an out-of-band alert, rebuilding the vortex basis from the
        data plane MUST re-project via Gram-Schmidt so that u⊥ · u == 0.

        Args:
            u: Reference axis (non-zero).
            u_perp: Reconstructed support vector.
            tol: Absolute tolerance on |u⊥ · û|.

        Returns:
            True iff u is non-degenerate and |dot(u_perp, u/||u||)| <= tol.
        """
        u = np.asarray(u, dtype=np.float64)
        u_perp = np.asarray(u_perp, dtype=np.float64)
        norm = float(np.linalg.norm(u))
        if norm <= 0:
            return False
        return bool(abs(float(np.dot(u_perp, u / norm))) <= tol)

    # --- Properties for observability ---

    @property
    def var_lambda(self) -> float:
        """Current EWMA variance of lambda (affective voltage)."""
        return self._var_lambda

    @property
    def var_esc(self) -> float:
        """Current EWMA variance of d_esc (escape distance)."""
        return self._var_esc

    @property
    def mu_lambda(self) -> float:
        """Current running mean of lambda."""
        return self._mu_lambda

    @property
    def mu_esc(self) -> float:
        """Current running mean of d_esc."""
        return self._mu_esc

    @property
    def drift_ratio(self) -> float:
        """Current drift ratio var_lambda / var_esc."""
        if self._var_esc <= 0:
            return float('inf') if self._var_lambda > 0 else 0.0
        return self._var_lambda / self._var_esc

    def reset(self) -> None:
        """Reset all internal state (including latched alert) for new calibration."""
        self._mu_lambda = 0.0
        self._var_lambda = 0.0
        self._lambda_initialized = False
        self._mu_esc = 0.0
        self._var_esc = 0.0
        self._esc_initialized = False
        self._alert = self.NOMINAL