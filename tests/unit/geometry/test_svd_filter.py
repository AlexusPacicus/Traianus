"""Unit tests for SVDAnisotropyFilter - mean centering, u1 removal, residual norm."""
import numpy as np

from traianus.geometry.svd_filter import SVDAnisotropyFilter


class TestSVDAnisotropyFilterComponentRemoval:
    """Subtraction of the corpus mean and the dominant singular component u1."""

    def setup_method(self) -> None:
        self.rng = np.random.default_rng(101)
        self.n, self.d = 50, 16

    def test_filter_removes_dominant_component(self) -> None:
        direction = self.rng.normal(size=self.d)
        direction /= np.linalg.norm(direction)
        X = 10.0 * self.rng.normal(size=(self.n, 1)) * direction + 0.1 * self.rng.normal(
            size=(self.n, self.d)
        )
        filt = SVDAnisotropyFilter()
        filt.fit(X)
        filtered, residual = filt.transform(X[0])
        proj_u1 = np.dot(filtered, filt.u1_)
        assert abs(proj_u1) < 1e-8, f"Projection onto u1 after filter: {proj_u1}"
        # Substrate invariant (AGENTS 3.1): output vectors are unit-L2-norm.
        np.testing.assert_allclose(np.linalg.norm(filtered), 1.0, atol=1e-8)
        # residual is the post-projection norm, independently recomputed.
        v_centered = X[0] - filt.mean_
        expected_proj = np.dot(filt.u1_, v_centered)
        expected_filtered = v_centered - expected_proj * filt.u1_
        expected_residual = np.linalg.norm(expected_filtered)
        np.testing.assert_allclose(residual, expected_residual, atol=1e-10)
        assert residual > 0.0
        assert np.isfinite(residual)

    def test_filter_preserves_orthogonal_components(self) -> None:
        """Per-row variation orthogonal to u1 (not just a row-constant offset,
        which mean-centering would fully absorb into self.mean_ and hence
        remove entirely) survives centering and projection. Checked against
        an independent reformulation of the same 5-step formula, since the
        exact residual direction is no longer hand-derivable once u1_ is
        found from correlated multi-dimensional variance."""
        u1 = np.zeros(self.d)
        u1[0] = 1.0
        ortho = np.zeros(self.d)
        ortho[1] = 1.0
        a = np.linspace(1, 10, self.n)
        b = 0.5 + 0.1 * self.rng.normal(size=self.n)
        X = np.outer(a, u1) + np.outer(b, ortho)
        filt = SVDAnisotropyFilter()
        filt.fit(X)
        filtered, residual = filt.transform(X[0])

        v_centered = X[0] - filt.mean_
        proj = np.dot(filt.u1_, v_centered)
        v_filtered = v_centered - proj * filt.u1_
        expected_residual = np.linalg.norm(v_filtered)
        np.testing.assert_allclose(residual, expected_residual, atol=1e-10)
        assert expected_residual > filt.eps, (
            "fixture must have genuine 2D spread so u1-removal leaves a "
            "nonzero residual"
        )
        expected_unit = v_filtered / expected_residual
        np.testing.assert_allclose(filtered, expected_unit, atol=1e-10)
        # Dimensions never populated by X (2..d-1) stay exactly zero: X only
        # varies within span{u1, ortho}, so neither centering nor projecting
        # (which both stay within that span) can leak into them.
        for i in range(2, self.d):
            np.testing.assert_allclose(filtered[i], 0.0, atol=1e-10)


class TestSVDAnisotropyFilterMeanCenteringAndResidual:
    """B1/T1/T2: transform() centers by the corpus mean before projecting
    out u1, and returns (unit_vector, residual_norm)."""

    def test_transform_centers_by_corpus_mean_before_projecting(self) -> None:
        """T1: the prior revision (commit 3d03bfa) projected u1 out of the
        raw, uncentered v -- for a fixture whose corpus mean is nonzero,
        centering first gives a materially different result."""
        rng = np.random.default_rng(707)
        n, d = 40, 12
        direction = rng.normal(size=d)
        direction /= np.linalg.norm(direction)
        X = 10.0 * rng.normal(size=(n, 1)) * direction + rng.normal(size=(n, d)) + 3.0
        filt = SVDAnisotropyFilter()
        filt.fit(X)
        v = X[0]
        filtered, residual = filt.transform(v)

        # Reference: the decided 5-step formula, independently recomputed.
        v_centered = v - filt.mean_
        proj = np.dot(filt.u1_, v_centered)
        v_filtered_expected = v_centered - proj * filt.u1_
        residual_expected = np.linalg.norm(v_filtered_expected)
        np.testing.assert_allclose(residual, residual_expected, atol=1e-10)
        np.testing.assert_allclose(
            filtered, v_filtered_expected / residual_expected, atol=1e-10
        )

        # Contrast: projecting the RAW (uncentered) v -- what the prior
        # revision did -- gives a materially different residual, because
        # mean_ is nonzero and not fully re-absorbed by projecting u1 out
        # of the raw v.
        assert np.linalg.norm(filt.mean_) > 1e-6
        proj_raw = np.dot(filt.u1_, v)
        v_filtered_raw = v - proj_raw * filt.u1_
        residual_raw = np.linalg.norm(v_filtered_raw)
        assert not np.isclose(residual, residual_raw, atol=1e-6), (
            "centering by the corpus mean must change the result"
        )

    def test_transform_returns_unit_vector_and_residual_norm_tuple(self) -> None:
        """T2: transform() returns (unit_vector, residual_norm) -- a tuple,
        not a bare array -- and residual_norm is the post-projection norm,
        not the raw projection scalar proj."""
        rng = np.random.default_rng(808)
        n, d = 30, 8
        direction = rng.normal(size=d)
        direction /= np.linalg.norm(direction)
        X = 5.0 * rng.normal(size=(n, 1)) * direction + rng.normal(size=(n, d))
        filt = SVDAnisotropyFilter()
        filt.fit(X)
        v = X[0]

        result = filt.transform(v)
        assert isinstance(result, tuple) and len(result) == 2
        unit_vector, residual_norm = result
        assert isinstance(residual_norm, float)

        v_centered = v - filt.mean_
        proj = np.dot(filt.u1_, v_centered)
        v_filtered = v_centered - proj * filt.u1_
        expected_residual = float(np.linalg.norm(v_filtered))

        # residual_norm must be the post-projection norm, not proj itself.
        assert not np.isclose(residual_norm, proj, atol=1e-6)
        np.testing.assert_allclose(residual_norm, expected_residual, atol=1e-10)
        np.testing.assert_allclose(
            unit_vector, v_filtered / expected_residual, atol=1e-10
        )
        np.testing.assert_allclose(np.linalg.norm(unit_vector), 1.0, atol=1e-8)


class TestSVDAnisotropyFilterIsotropic:
    """Filter on isotropic data: u1_ is zero, but centering still applies."""

    def test_filter_identity_on_isotropic_data(self) -> None:
        """On isotropic data u1_ is zero, so transform's projection step is
        a no-op -- but centering by the corpus mean still happens (B1 is not
        conditioned on anisotropy): transform is not a pure renormalization
        of the raw vector."""
        rng = np.random.default_rng(202)
        n, d = 200, 32
        X = rng.normal(size=(n, d))
        filt = SVDAnisotropyFilter()
        filt.fit(X)
        np.testing.assert_allclose(filt.u1_, 0.0, atol=1e-10)
        v = X[0].copy()
        filtered, residual = filt.transform(v)

        v_centered = v - filt.mean_
        expected_residual = np.linalg.norm(v_centered)  # proj is 0 since u1_ is 0
        np.testing.assert_allclose(residual, expected_residual, atol=1e-10)
        np.testing.assert_allclose(
            filtered, v_centered / expected_residual, atol=1e-10
        )
        np.testing.assert_allclose(np.linalg.norm(filtered), 1.0, atol=1e-10)


class TestSVDAnisotropyFilterDeterminism:
    """Same inputs produce bitwise identical outputs."""

    def test_deterministic(self) -> None:
        rng = np.random.default_rng(303)
        X = rng.normal(size=(30, 12))
        f1 = SVDAnisotropyFilter()
        f1.fit(X)
        r1, res1 = f1.transform(X[0])
        f2 = SVDAnisotropyFilter()
        f2.fit(X)
        r2, res2 = f2.transform(X[0])
        np.testing.assert_array_equal(r1, r2)
        assert res1 == res2


class TestSVDAnisotropyFilterEdgeCases:
    """Edge cases."""

    def test_filter_single_vector(self) -> None:
        X = np.array([[1.0, 2.0, 3.0]])
        filt = SVDAnisotropyFilter()
        filt.fit(X)
        filtered, residual = filt.transform(X[0])
        # Single-row fit: mean_ equals the row itself, so centering yields
        # the exact zero vector regardless of u1_ (a - a == 0 exactly in
        # IEEE754) -- the eps guard prevents dividing by the resulting zero
        # residual norm (B3).
        assert np.all(np.isfinite(filtered)), (
            f"eps guard failed to prevent division by a near-zero norm: {filtered}"
        )
        np.testing.assert_allclose(filtered, 0.0, atol=1e-12)
        assert residual == 0.0

    def test_filter_output_norms_are_unit(self) -> None:
        """Every transformed row has unit L2 norm (B1). Supersedes the old
        escape-distance coefficient-of-variation check, which became trivial
        (cv_after ~ 0 for any input) once every output is unit-normalized.
        residual_norm is positive and finite for every row of this
        dominant-component-removal fixture (no row collapses)."""
        rng = np.random.default_rng(404)
        n, d = 100, 20
        direction = rng.normal(size=d)
        direction /= np.linalg.norm(direction)
        X = 5.0 * rng.normal(size=(n, 1)) * direction + rng.normal(size=(n, d))
        filt = SVDAnisotropyFilter()
        filt.fit(X)
        results = [filt.transform(x) for x in X]
        filtered = np.array([r[0] for r in results])
        residuals = np.array([r[1] for r in results])
        norms_after = np.linalg.norm(filtered, axis=1)
        np.testing.assert_allclose(norms_after, 1.0, atol=1e-8)
        assert np.all(np.isfinite(residuals))
        assert np.all(residuals > 0.0)


class TestSVDAnisotropyFilterFitTransform:
    """fit_transform convenience method (B2)."""

    def test_fit_transform_matches_sequential(self) -> None:
        rng = np.random.default_rng(505)
        X = rng.normal(size=(25, 10))
        filt = SVDAnisotropyFilter()
        unit_vectors, residual_norms = filt.fit_transform(X)

        filt2 = SVDAnisotropyFilter()
        filt2.fit(X)
        expected_units = []
        expected_residuals = []
        for x in X:
            u, r = filt2.transform(x)
            expected_units.append(u)
            expected_residuals.append(r)

        np.testing.assert_allclose(unit_vectors, np.array(expected_units), atol=1e-14)
        np.testing.assert_allclose(
            residual_norms, np.array(expected_residuals), atol=1e-14
        )
