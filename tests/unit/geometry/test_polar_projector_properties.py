"""Property tests for PolarProjector mathematical invariants.

Deterministic seeded sweeps (numpy + stdlib only): same inputs across
dimensions produce bitwise identical outputs, lambda stays bounded, and
escape distance satisfies the triangle inequality.
"""
import numpy as np
from traianus.geometry.polar_projector import PolarProjector


def _random_unit_vectors(d: int, seed: int, n: int = 4) -> list:
    rng = np.random.default_rng(seed)
    vecs = []
    for _ in range(n):
        v = rng.normal(size=d).astype(np.float64)
        vecs.append(v / np.linalg.norm(v))
    return vecs


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
