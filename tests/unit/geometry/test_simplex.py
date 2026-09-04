"""Unit tests for SemanticSimplex - Z-score control, overlap, re-anchoring."""
import numpy as np
import pytest

from traianus.geometry.simplex import RECALIBRATION_SIGNAL, SemanticSimplex


class TestSemanticSimplexZScore:
    """Z-score computation: z_i = ||v_n_perp - c_i_perp|| / (sigma_i + eps)."""

    def setup_method(self) -> None:
        self.d = 8
        self.rng = np.random.default_rng(42)
        self.c1 = self.rng.normal(size=self.d).astype(np.float64)
        self.c1 /= np.linalg.norm(self.c1)
        self.cA = self.rng.normal(size=self.d).astype(np.float64)
        self.cA /= np.linalg.norm(self.cA)
        self.cB = self.rng.normal(size=self.d).astype(np.float64)
        self.cB /= np.linalg.norm(self.cB)
        self.sigma1, self.sigmaA, self.sigmaB = 0.3, 0.5, 0.4
        self.simplex = SemanticSimplex(
            c1_perp=self.c1,
            cA_perp=self.cA,
            cB_perp=self.cB,
            sigma1=self.sigma1,
            sigmaA=self.sigmaA,
            sigmaB=self.sigmaB,
        )

    def test_zscore_zero_for_coincident_vector(self) -> None:
        z = self.simplex.zscore(self.c1)
        assert z["c1"] == pytest.approx(0.0, abs=1e-12)
        assert z["cA"] > 0.0
        assert z["cB"] > 0.0

    def test_zscore_increases_with_distance(self) -> None:
        step = 0.01 * (self.rng.normal(size=self.d))
        z_near = self.simplex.zscore(self.c1 + step)
        z_far = self.simplex.zscore(self.c1 + 10.0 * step)
        assert z_near["c1"] < z_far["c1"]

    def test_zscore_scale_invariant(self) -> None:
        scale = 3.0
        simplex_a = SemanticSimplex(
            c1_perp=self.c1,
            cA_perp=self.cA,
            cB_perp=self.cB,
            sigma1=self.sigma1,
            sigmaA=self.sigmaA,
            sigmaB=self.sigmaB,
        )
        simplex_b = SemanticSimplex(
            c1_perp=scale * self.c1,
            cA_perp=scale * self.cA,
            cB_perp=scale * self.cB,
            sigma1=scale * self.sigma1,
            sigmaA=scale * self.sigmaA,
            sigmaB=scale * self.sigmaB,
        )
        v_a = self.c1 + 0.1 * self.cA
        v_b = scale * v_a
        za = simplex_a.zscore(v_a)
        zb = simplex_b.zscore(v_b)
        assert za["c1"] == pytest.approx(zb["c1"], rel=1e-10)
        assert za["cA"] == pytest.approx(zb["cA"], rel=1e-10)
        assert za["cB"] == pytest.approx(zb["cB"], rel=1e-10)

    def test_zscore_epsilon_guard(self) -> None:
        simplex_zero = SemanticSimplex(
            c1_perp=self.c1,
            cA_perp=self.cA,
            cB_perp=self.cB,
            sigma1=0.0,
            sigmaA=0.0,
            sigmaB=0.0,
        )
        z = simplex_zero.zscore(self.c1)
        assert np.isfinite(z["c1"])
        assert z["c1"] == 0.0

    def test_zscore_all_keys(self) -> None:
        z = self.simplex.zscore(self.c1)
        assert set(z.keys()) == {"c1", "cA", "cB"}


class TestSemanticSimplexOverlap:
    """Face overlap: M_ij = (sigma_i + sigma_j) - ||c_i_perp - c_j_perp||."""

    def setup_method(self) -> None:
        self.d = 8
        self.rng = np.random.default_rng(7)
        self.c1 = self.rng.normal(size=self.d).astype(np.float64)
        self.c1 /= np.linalg.norm(self.c1)

    def test_overlap_positive_when_intersecting(self) -> None:
        close_cA = self.c1 + 0.01 * np.ones(self.d)
        simplex = SemanticSimplex(
            c1_perp=self.c1,
            cA_perp=close_cA,
            cB_perp=-self.c1,
            sigma1=0.5,
            sigmaA=0.5,
            sigmaB=0.5,
        )
        assert simplex.overlap("c1", "cA") > 0.0

    def test_overlap_negative_when_gap(self) -> None:
        far_cA = 100.0 * np.ones(self.d)
        simplex = SemanticSimplex(
            c1_perp=self.c1,
            cA_perp=far_cA,
            cB_perp=-self.c1,
            sigma1=0.1,
            sigmaA=0.1,
            sigmaB=0.1,
        )
        assert simplex.overlap("c1", "cA") < 0.0

    def test_overlap_zero_at_tangent(self) -> None:
        dist = 0.6
        cA = self.c1.copy()
        cA[0] += dist
        simplex = SemanticSimplex(
            c1_perp=self.c1,
            cA_perp=cA,
            cB_perp=-self.c1,
            sigma1=0.3,
            sigmaA=0.3,
            sigmaB=0.5,
        )
        assert simplex.overlap("c1", "cA") == pytest.approx(0.0, abs=1e-12)


class TestSemanticSimplexClassify:
    """Re-anchoring vs RECALIBRATION_SIGNAL detection."""

    def setup_method(self) -> None:
        self.d = 8
        self.c1 = np.array([1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        self.cA = np.array([0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        self.cB = np.array([0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0])

    def test_reanchoring_when_close(self) -> None:
        simplex = SemanticSimplex(
            c1_perp=self.c1, cA_perp=self.cA, cB_perp=self.cB,
            sigma1=10.0, sigmaA=10.0, sigmaB=10.0,
        )
        result = simplex.classify(self.c1)
        assert result["action"] == "REANCHORING"

    def test_recalibration_signal_when_far(self) -> None:
        simplex = SemanticSimplex(
            c1_perp=self.c1, cA_perp=self.cA, cB_perp=self.cB,
            sigma1=0.001, sigmaA=0.001, sigmaB=0.001,
        )
        far = 100.0 * np.ones(self.d)
        result = simplex.classify(far)
        assert result["action"] == RECALIBRATION_SIGNAL

    def test_classify_returns_z_scores_and_overlap(self) -> None:
        simplex = SemanticSimplex(
            c1_perp=self.c1, cA_perp=self.cA, cB_perp=self.cB,
            sigma1=1.0, sigmaA=1.0, sigmaB=1.0,
        )
        result = simplex.classify(self.c1)
        assert "z_scores" in result
        assert "overlap_min" in result
        assert "action" in result


class TestSemanticSimplexDeterminism:
    """Same inputs produce bitwise identical outputs."""

    def test_deterministic(self) -> None:
        d = 16
        rng = np.random.default_rng(99)
        c1 = rng.normal(size=d)
        cA = rng.normal(size=d)
        cB = rng.normal(size=d)
        v = rng.normal(size=d)
        s1 = SemanticSimplex(c1, cA, cB, 0.3, 0.4, 0.5)
        s2 = SemanticSimplex(c1, cA, cB, 0.3, 0.4, 0.5)
        assert s1.zscore(v) == s2.zscore(v)
        assert s1.overlap("c1", "cA") == s2.overlap("c1", "cA")
        assert s1.classify(v) == s2.classify(v)
