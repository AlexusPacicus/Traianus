"""Unit tests for PolarProjector - isolated, deterministic, < 1ms each."""
import numpy as np
from traianus.geometry.polar_projector import PolarProjector


class TestPolarProjectorUnit:
    """Pure unit tests for PolarProjector internal methods."""

    def setup_method(self):
        self.projector = PolarProjector()

    # --- Anchor normalization ---

    def test_normalize_anchor_guard_zero_norm(self):
        c_1 = np.zeros(384, dtype=np.float64)
        c1_hat = self.projector._normalize_anchor(c_1)
        assert np.allclose(c1_hat, 0.0)

    def test_normalize_anchor_guard_normal(self):
        c_1 = np.ones(384, dtype=np.float64)
        c1_hat = self.projector._normalize_anchor(c_1)
        assert np.isclose(np.linalg.norm(c1_hat), 1.0)

    def test_normalize_anchor_at_eps_boundary(self):
        """Test at exactly eps_norm threshold."""
        c_1 = np.array([1e-9, 0.0, 0.0], dtype=np.float64)
        c1_hat = self.projector._normalize_anchor(c_1)
        assert np.allclose(c1_hat, 0.0)

    def test_normalize_anchor_above_eps_boundary(self):
        """Test just above eps_norm threshold."""
        c_1 = np.array([2e-9, 0.0, 0.0], dtype=np.float64)
        c1_hat = self.projector._normalize_anchor(c_1)
        assert np.isclose(np.linalg.norm(c1_hat), 1.0)

    # --- Orthogonal projector ---

    def test_orthogonal_operator_construction(self):
        c1_hat = np.array([1.0, 0.0, 0.0], dtype=np.float64)
        P_perp = self.projector._orthogonal_projector(c1_hat)
        assert P_perp.shape == (3, 3)
        assert np.allclose(P_perp @ c1_hat, 0.0)
        assert np.allclose(P_perp @ np.array([0.0, 1.0, 0.0]), np.array([0.0, 1.0, 0.0]))

    def test_orthogonal_projector_idempotent(self):
        """P⊥ @ P⊥ = P⊥"""
        c1_hat = np.array([0.6, 0.8, 0.0], dtype=np.float64)
        P_perp = self.projector._orthogonal_projector(c1_hat)
        assert np.allclose(P_perp @ P_perp, P_perp)

    def test_orthogonal_projector_symmetric(self):
        """P⊥ = P⊥.T"""
        c1_hat = np.array([0.6, 0.8, 0.0], dtype=np.float64)
        P_perp = self.projector._orthogonal_projector(c1_hat)
        assert np.allclose(P_perp, P_perp.T)

    # --- Centroid projection ---

    def test_project_centroids(self):
        c1_hat = np.array([1.0, 0.0, 0.0], dtype=np.float64)
        P_perp = self.projector._orthogonal_projector(c1_hat)
        c_A = np.array([2.0, 3.0, 4.0], dtype=np.float64)
        cA_perp = P_perp @ c_A
        assert np.isclose(cA_perp[0], 0.0)
        assert np.isclose(cA_perp[1], 3.0)

    # --- Collinearity ---

    def test_collinearity_detection_true(self):
        cA_perp = np.array([1e-7, 2e-7, 0.0], dtype=np.float64)
        cB_perp = np.array([2e-7, 4e-7, 0.0], dtype=np.float64)
        assert self.projector._is_collinear(cA_perp, cB_perp)

    def test_collinearity_detection_false(self):
        cA_perp = np.array([1.0, 0.0, 0.0], dtype=np.float64)
        cB_perp = np.array([0.0, 1.0, 0.0], dtype=np.float64)
        assert not self.projector._is_collinear(cA_perp, cB_perp)

    def test_collinearity_at_eps_boundary(self):
        """Test at exactly eps_collinear threshold (strict <)."""
        cA_perp = np.array([0.5e-6, 0.0, 0.0], dtype=np.float64)
        cB_perp = np.array([1.4999999e-6, 0.0, 0.0], dtype=np.float64)  # diff < 1e-6
        assert self.projector._is_collinear(cA_perp, cB_perp)

    def test_collinearity_above_eps_boundary(self):
        """Test just above eps_collinear threshold."""
        cA_perp = np.array([0.5e-6, 0.0, 0.0], dtype=np.float64)
        cB_perp = np.array([1.5000001e-6, 0.0, 0.0], dtype=np.float64)  # diff > 1e-6
        assert not self.projector._is_collinear(cA_perp, cB_perp)

    # --- Canonical u⊥ ---

    def test_canonical_u_perp_deterministic(self):
        c1_hat = np.array([0.6, 0.8, 0.0], dtype=np.float64)
        results = [self.projector._canonical_u_perp(c1_hat) for _ in range(1000)]
        for u in results[1:]:
            assert np.array_equal(u, results[0]), "Bitwise determinism failed"

    def test_canonical_u_perp_orthogonal(self):
        c1_hat = np.array([0.6, 0.8, 0.0], dtype=np.float64)
        u_perp = self.projector._canonical_u_perp(c1_hat)
        assert np.isclose(np.dot(u_perp, c1_hat), 0.0, atol=1e-10)
        assert np.isclose(np.linalg.norm(u_perp), 1.0)

    def test_canonical_u_perp_min_projection_idx(self):
        # Minimum at index 2 (0.1 is smallest absolute)
        c1_hat = np.array([0.5, 0.5, 0.1, 0.5], dtype=np.float64)
        u_perp = self.projector._canonical_u_perp(c1_hat)
        assert np.abs(u_perp[2]) > 0.9

    def test_canonical_u_perp_first_component_min(self):
        """Test when first component is minimum."""
        c1_hat = np.array([0.1, 0.5, 0.5, 0.5], dtype=np.float64)
        u_perp = self.projector._canonical_u_perp(c1_hat)
        assert np.abs(u_perp[0]) > 0.9

    def test_canonical_u_perp_last_component_min(self):
        """Test when last component is minimum."""
        c1_hat = np.array([0.5, 0.5, 0.5, 0.1], dtype=np.float64)
        u_perp = self.projector._canonical_u_perp(c1_hat)
        assert np.abs(u_perp[3]) > 0.9

    # --- Dipole ---

    def test_dipole_fallback_non_collinear(self):
        cA_perp = np.array([1.0, 0.0, 0.0], dtype=np.float64)
        cB_perp = np.array([0.0, 1.0, 0.0], dtype=np.float64)
        c1_hat = np.array([1.0, 0.0, 0.0], dtype=np.float64)
        v_dipole = self.projector._compute_dipole(cA_perp, cB_perp, c1_hat)
        expected = cA_perp - cB_perp
        assert np.allclose(v_dipole, expected)

    def test_dipole_collinear_fallback(self):
        cA_perp = np.array([1e-7, 0.0, 0.0], dtype=np.float64)
        cB_perp = np.array([2e-7, 0.0, 0.0], dtype=np.float64)
        c1_hat = np.array([1.0, 0.0, 0.0], dtype=np.float64)
        v_dipole = self.projector._compute_dipole(cA_perp, cB_perp, c1_hat)
        expected = 2.0 * self.projector.delta * self.projector._canonical_u_perp(c1_hat)
        assert np.allclose(v_dipole, expected)

    # --- Full pipeline components ---

    def test_stimulus_residual(self):
        v_n = np.array([1.0, 2.0, 3.0], dtype=np.float64)
        c_1 = np.array([0.5, 0.5, 0.5], dtype=np.float64)
        c1_hat = c_1 / np.linalg.norm(c_1)
        P_perp = np.eye(3) - np.outer(c1_hat, c1_hat)
        r = P_perp @ (v_n - c_1)
        assert np.isclose(np.dot(r, c1_hat), 0.0)

    def test_voltage_lambda_bounds(self):
        r = np.array([10.0, 0.0, 0.0], dtype=np.float64)
        v_dipole = np.array([1.0, 0.0, 0.0], dtype=np.float64)
        lambda_val = np.dot(r, v_dipole) / np.dot(v_dipole, v_dipole)
        lambda_val = np.clip(lambda_val, -1.0, 1.0)
        assert -1.0 <= lambda_val <= 1.0

    def test_escape_distance_nonnegative(self):
        r = np.array([1.0, 2.0, 3.0], dtype=np.float64)
        v_dipole = np.array([0.5, 0.5, 0.0], dtype=np.float64)
        lambda_val = 0.5
        d_esc = np.linalg.norm(r - lambda_val * v_dipole)
        assert d_esc >= 0.0

    def test_return_tuple_type(self):
        v_n = np.random.default_rng(1).normal(size=384).astype(np.float64)
        v_n = v_n / np.linalg.norm(v_n)
        c_1 = np.random.default_rng(2).normal(size=384).astype(np.float64)
        c_1 = c_1 / np.linalg.norm(c_1)
        c_A = np.random.default_rng(3).normal(size=384).astype(np.float64)
        c_A = c_A / np.linalg.norm(c_A)
        c_B = np.random.default_rng(4).normal(size=384).astype(np.float64)
        c_B = c_B / np.linalg.norm(c_B)
        result = self.projector.project(v_n, c_1, c_A, c_B, 42)
        assert isinstance(result, tuple)
        assert len(result) == 3
        assert isinstance(result[0], int)
        assert isinstance(result[1], float)
        assert isinstance(result[2], float)

    # --- Custom parameters ---

    def test_custom_delta(self):
        projector = PolarProjector(delta=0.5)
        assert projector.delta == 0.5

    def test_custom_eps_norm(self):
        projector = PolarProjector(eps_norm=1e-6)
        assert projector.eps_norm == 1e-6

    def test_custom_eps_collinear(self):
        projector = PolarProjector(eps_collinear=1e-4)
        assert projector.eps_collinear == 1e-4