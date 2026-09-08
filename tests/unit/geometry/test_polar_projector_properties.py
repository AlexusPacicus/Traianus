"""Property tests for PolarProjector mathematical invariants.

Deterministic seeded sweeps (numpy + stdlib only): same inputs across
dimensions produce bitwise identical outputs, lambda stays bounded, and
escape distance satisfies the triangle inequality.

Dimensions/seed counts are declarative @pytest.mark.parametrize (not
hardcoded loops). L2 normalization makes the invariant geometry invariant
to d; the small dimension set only guards shape/index parity.
"""
import numpy as np
import pytest

from traianus.geometry.polar_projector import PolarProjector

DIMS = (128, 384, 768)
DIMS_LIGHT = (128, 384)
P_DIMS = pytest.mark.parametrize("d", DIMS)
P_DIMS_LIGHT = pytest.mark.parametrize("d", DIMS_LIGHT)
P_SEED_25 = pytest.mark.parametrize("seed", range(25))
P_SEED_20 = pytest.mark.parametrize("seed", range(20))

# Multiplier over ||v_dipole|| that drives the residual into the saturated
# band: v_n = c_1 + K·v̂_dipole ⇒ r = K·v̂_dipole ⇒ λ* = K / ||v_dipole||.
# K = 2 forces λ* = 2 > 1 deterministically, past the clamp.
_SATURATION_DRIVE = 2.0


def _random_unit_vectors(d: int, seed: int, n: int = 4) -> list:
    rng = np.random.default_rng(seed)
    vecs = []
    for _ in range(n):
        v = rng.normal(size=d).astype(np.float64)
        vecs.append(v / np.linalg.norm(v))
    return vecs


def _recompute_internals(
    projector: PolarProjector,
    v_n: np.ndarray,
    c_1: np.ndarray,
    c_A: np.ndarray,
    c_B: np.ndarray,
    lambda_val: float,
    d_esc: float,
) -> dict:
    """Reconstruct intermediate quantities from the project() pipeline."""
    c1_hat = projector._normalize_anchor(c_1)
    P_perp = projector._orthogonal_projector(c1_hat)
    cA_perp = P_perp @ c_A
    cB_perp = P_perp @ c_B
    v_dipole = projector._compute_dipole(cA_perp, cB_perp, c1_hat)
    r = P_perp @ (v_n - c_1)
    v_dipole_norm_sq = float(np.dot(v_dipole, v_dipole))
    if v_dipole_norm_sq > 0:
        lambda_raw = float(np.dot(r, v_dipole) / v_dipole_norm_sq)
    else:
        lambda_raw = 0.0
    return {
        "c1_hat": c1_hat,
        "P_perp": P_perp,
        "v_dipole": v_dipole,
        "r": r,
        "lambda_raw": lambda_raw,
        "v_dipole_norm_sq": v_dipole_norm_sq,
    }


class TestPolarProjectorProperties:
    """Property tests for mathematical invariants."""

    def test_polar_projector_deterministic_all_dims(self):
        """Same inputs -> bitwise identical outputs across dimensions."""
        for d in (384, 768, 1536):
            for seed in range(20):
                v_n, c_1, c_A, c_B = _random_unit_vectors(d, seed)
                projector = PolarProjector()
                r1 = projector.project(v_n, c_1, c_A, c_B, 1)
                r2 = projector.project(v_n, c_1, c_A, c_B, 1)
                assert r1 == r2  # Exact tuple equality (bitwise)

    def test_lambda_bounded_for_random_unit_vectors(self):
        """lambda in [-1, 1] for all random unit vectors."""
        for d in (384, 768):
            for seed in range(20):
                v_n, c_1, c_A, c_B = _random_unit_vectors(d, seed)
                projector = PolarProjector()
                _, lambda_val, _ = projector.project(v_n, c_1, c_A, c_B, 1)
                assert -1.0 <= lambda_val <= 1.0

    def test_escape_distance_nonnegative_for_random_vectors(self):
        """d_esc >= 0 for all random unit vectors."""
        for d in (384, 768):
            for seed in range(20):
                v_n, c_1, c_A, c_B = _random_unit_vectors(d, seed)
                projector = PolarProjector()
                _, _, d_esc = projector.project(v_n, c_1, c_A, c_B, 1)
                assert d_esc >= 0.0

    def test_escape_distance_triangle_inequality(self):
        """d_esc <= ||r|| + |lambda| * ||v_dipole||."""
        for d in (384, 768):
            for seed in range(20):
                v_n, c_1, c_A, c_B = _random_unit_vectors(d, seed)
                projector = PolarProjector()
                _, lambda_val, d_esc = projector.project(v_n, c_1, c_A, c_B, 1)

                # Recompute internal values for verification
                c1_norm = np.linalg.norm(c_1)
                c1_hat = c_1 / c1_norm if c1_norm > projector.eps_norm else np.zeros_like(c_1)
                P_perp = np.eye(d) - np.outer(c1_hat, c1_hat)
                cA_perp = P_perp @ c_A
                cB_perp = P_perp @ c_B
                dipole_diff = cA_perp - cB_perp

                if np.linalg.norm(dipole_diff) < projector.eps_collinear:
                    u_perp = projector._canonical_u_perp(c1_hat)
                    v_dipole = 2.0 * projector.delta * u_perp
                else:
                    v_dipole = dipole_diff

                r = P_perp @ (v_n - c_1)
                bound = np.linalg.norm(r) + abs(lambda_val) * np.linalg.norm(v_dipole)
                assert d_esc <= bound + 1e-10  # Numerical tolerance

    def test_centroid_id_preserved(self):
        """Centroid ID passed through unchanged."""
        for d in (384, 768):
            for seed in range(10):
                v_n, c_1, c_A, c_B = _random_unit_vectors(d, seed)
                projector = PolarProjector()
                for centroid_id in (0, 1, 42, 255, 65536, 1000000):
                    result = projector.project(v_n, c_1, c_A, c_B, centroid_id)
                    assert result[0] == centroid_id

    def test_outputs_finite(self):
        """All outputs must be finite (no NaN/inf)."""
        for d in (384, 768):
            for seed in range(10):
                v_n, c_1, c_A, c_B = _random_unit_vectors(d, seed)
                projector = PolarProjector()
                _, lambda_val, d_esc = projector.project(v_n, c_1, c_A, c_B, 1)
                assert np.isfinite(lambda_val)
                assert np.isfinite(d_esc)

    @P_DIMS
    @P_SEED_25
    def test_energy_conservation_pythagorean(self, d, seed):
        """Paper §4: ||r||² = λ²||v_dipole||² + d_esc² when |λ*| ≤ 1."""
        v_n, c_1, c_A, c_B = _random_unit_vectors(d, seed)
        projector = PolarProjector()
        _, lambda_val, d_esc = projector.project(v_n, c_1, c_A, c_B, 1)
        internals = _recompute_internals(
            projector, v_n, c_1, c_A, c_B, lambda_val, d_esc,
        )
        if abs(internals["lambda_raw"]) <= 1.0:
            norm_r_sq = float(np.dot(internals["r"], internals["r"]))
            lambda_sq_vd_sq = lambda_val**2 * internals["v_dipole_norm_sq"]
            energy_gap = abs(norm_r_sq - lambda_sq_vd_sq - d_esc**2)
            assert energy_gap < 1e-10, (
                f"seed={seed} d={d}: |‖r‖² - λ²‖v‖² - d_esc²| = {energy_gap}"
            )

    def _saturated_case(
        self,
        projector: PolarProjector,
        d: int,
        seed: int,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray] | None:
        """Build (v_n, c_1, c_A, c_B) forcing |λ*| > 1 past the clamp."""
        rng = np.random.default_rng(seed)
        c_1 = rng.normal(size=d).astype(np.float64)
        c_1 = c_1 / np.linalg.norm(c_1)
        c_A = rng.normal(size=d).astype(np.float64)
        c_A = c_A / np.linalg.norm(c_A)
        c_B = rng.normal(size=d).astype(np.float64)
        c_B = c_B / np.linalg.norm(c_B)
        internals_pre = _recompute_internals(
            projector, c_1, c_1, c_A, c_B, 0.0, 0.0,
        )
        vd = internals_pre["v_dipole"]
        vd_norm = np.linalg.norm(vd)
        if vd_norm < projector.eps_collinear:
            return None
        vd_hat = vd / vd_norm
        drive = _SATURATION_DRIVE * vd_norm
        v_n = c_1 + drive * vd_hat
        return v_n, c_1, c_A, c_B

    @P_DIMS_LIGHT
    @P_SEED_25
    def test_energy_inequality_under_saturation(self, d, seed):
        """Paper §4: when |λ*| > 1 (clamped), ||r||² > λ²||v_dipole||² + d_esc²."""
        projector = PolarProjector()
        case = self._saturated_case(projector, d, seed)
        if case is None:
            return
        v_n, c_1, c_A, c_B = case
        _, lambda_val, d_esc = projector.project(v_n, c_1, c_A, c_B, 1)
        internals = _recompute_internals(
            projector, v_n, c_1, c_A, c_B, lambda_val, d_esc,
        )
        assert abs(internals["lambda_raw"]) > 1.0, "drive failed to saturate"
        assert abs(lambda_val) == 1.0, "Clamping failed"
        norm_r_sq = float(np.dot(internals["r"], internals["r"]))
        energy_sum = lambda_val**2 * internals["v_dipole_norm_sq"] + d_esc**2
        assert norm_r_sq > energy_sum + 1e-10, (
            f"seed={seed}: expected strict inequality under saturation"
        )

    @P_DIMS
    @P_SEED_25
    def test_residual_orthogonal_to_v_dipole(self, d, seed):
        """⟨r - λ·v_dipole, v_dipole⟩ = 0 when λ is unclamped (least-squares)."""
        v_n, c_1, c_A, c_B = _random_unit_vectors(d, seed)
        projector = PolarProjector()
        _, lambda_val, d_esc = projector.project(v_n, c_1, c_A, c_B, 1)
        internals = _recompute_internals(
            projector, v_n, c_1, c_A, c_B, lambda_val, d_esc,
        )
        if abs(internals["lambda_raw"]) <= 1.0:
            residual = internals["r"] - lambda_val * internals["v_dipole"]
            dot_product = abs(float(np.dot(residual, internals["v_dipole"])))
            assert dot_product < 1e-10, (
                f"seed={seed} d={d}: ⟨r-λv, v⟩ = {dot_product}"
            )

    @P_DIMS
    @P_SEED_25
    def test_residual_orthogonal_to_anchor(self, d, seed):
        """⟨r, ĉ₁⟩ = 0 for all outputs of project()."""
        v_n, c_1, c_A, c_B = _random_unit_vectors(d, seed)
        projector = PolarProjector()
        _, lambda_val, d_esc = projector.project(v_n, c_1, c_A, c_B, 1)
        internals = _recompute_internals(
            projector, v_n, c_1, c_A, c_B, lambda_val, d_esc,
        )
        dot_product = abs(float(np.dot(internals["r"], internals["c1_hat"])))
        assert dot_product < 1e-10, (
            f"seed={seed} d={d}: ⟨r, ĉ₁⟩ = {dot_product}"
        )

    @P_DIMS
    @P_SEED_20
    def test_lambda_sign_matches_dipole_orientation(self, d, seed):
        """Stimulus along +ĉ_dipole → λ > 0; along −ĉ_dipole → λ < 0."""
        rng = np.random.default_rng(seed)
        c_1 = rng.normal(size=d).astype(np.float64)
        c_1 = c_1 / np.linalg.norm(c_1)
        c_A = rng.normal(size=d).astype(np.float64)
        c_A = c_A / np.linalg.norm(c_A)
        c_B = rng.normal(size=d).astype(np.float64)
        c_B = c_B / np.linalg.norm(c_B)
        projector = PolarProjector()
        internals = _recompute_internals(
            projector, c_1, c_1, c_A, c_B, 0.0, 0.0,
        )
        vd = internals["v_dipole"]
        if np.linalg.norm(vd) < projector.eps_collinear:
            return
        vd_hat = vd / np.linalg.norm(vd)
        # v_n = c_1 ± drive·v̂ keeps r = ±drive·v̂ exactly in the dipole axis
        drive = _SATURATION_DRIVE * np.linalg.norm(vd)
        v_plus = c_1 + drive * vd_hat
        v_minus = c_1 - drive * vd_hat
        _, lam_plus, _ = projector.project(v_plus, c_1, c_A, c_B, 1)
        _, lam_minus, _ = projector.project(v_minus, c_1, c_A, c_B, 1)
        assert lam_plus > 0.0, f"seed={seed}: λ along +dipole should be positive, got {lam_plus}"
        assert lam_minus < 0.0, f"seed={seed}: λ along -dipole should be negative, got {lam_minus}"
