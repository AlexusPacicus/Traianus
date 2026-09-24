"""Unit tests for SVDAnisotropyFilter - dominant component subtraction."""
import numpy as np

from traianus.geometry.svd_filter import SVDAnisotropyFilter


class TestSVDAnisotropyFilterComponentRemoval:
    """Subtraction of dominant singular component u1."""

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
        filtered = filt.transform(X[0])
        proj_u1 = np.dot(filtered, filt.u1_)
        assert abs(proj_u1) < 1e-8, f"Projection onto u1 after filter: {proj_u1}"
        # Substrate invariant (AGENTS 3.1): output vectors are unit-L2-norm.
        np.testing.assert_allclose(np.linalg.norm(filtered), 1.0, atol=1e-8)

    def test_filter_preserves_orthogonal_components(self) -> None:
        u1 = np.zeros(self.d)
        u1[0] = 1.0
        ortho = np.zeros(self.d)
        ortho[1] = 1.0
        X = np.outer(np.linspace(1, 10, self.n), u1) + 0.5 * ortho
        filt = SVDAnisotropyFilter()
        filt.fit(X)
        filtered = filt.transform(X[0])
        # Components outside the {u1, ortho} plane never populated by X stay
        # exactly zero: removing u1 and re-normalizing must not leak into them.
        for i in range(2, self.d):
            np.testing.assert_allclose(filtered[i], 0.0, atol=1e-10)
        # The surviving direction is exactly the (now unit-normalized) ortho axis.
        np.testing.assert_allclose(filtered, ortho, atol=1e-10)


class TestSVDAnisotropyFilterIsotropic:
    """Filter on isotropic data should change vectors minimally."""

    def test_filter_identity_on_isotropic_data(self) -> None:
        """On isotropic data u1_ is zero, so transform only re-normalizes v to
        unit L2 norm without changing its direction."""
        rng = np.random.default_rng(202)
        n, d = 200, 32
        X = rng.normal(size=(n, d))
        filt = SVDAnisotropyFilter()
        filt.fit(X)
        np.testing.assert_allclose(filt.u1_, 0.0, atol=1e-10)
        v = X[0].copy()
        filtered = filt.transform(v)
        np.testing.assert_allclose(np.linalg.norm(filtered), 1.0, atol=1e-10)
        cosine = np.dot(filtered, v) / (np.linalg.norm(filtered) * np.linalg.norm(v))
        assert cosine > 1 - 1e-9, f"Isotropic filter changed direction: cosine={cosine:.9f}"


class TestSVDAnisotropyFilterDeterminism:
    """Same inputs produce bitwise identical outputs."""

    def test_deterministic(self) -> None:
        rng = np.random.default_rng(303)
        X = rng.normal(size=(30, 12))
        f1 = SVDAnisotropyFilter()
        f1.fit(X)
        r1 = f1.transform(X[0])
        f2 = SVDAnisotropyFilter()
        f2.fit(X)
        r2 = f2.transform(X[0])
        np.testing.assert_array_equal(r1, r2)


class TestSVDAnisotropyFilterEdgeCases:
    """Edge cases."""

    def test_filter_single_vector(self) -> None:
        X = np.array([[1.0, 2.0, 3.0]])
        filt = SVDAnisotropyFilter()
        filt.fit(X)
        filtered = filt.transform(X[0])
        # eps guard: the filtered norm is near-zero here (fitting on one row
        # makes u1 the row's own direction), so it must not be divided by it.
        assert np.all(np.isfinite(filtered)), (
            f"eps guard failed to prevent division by a near-zero norm: {filtered}"
        )
        np.testing.assert_allclose(filtered, 0.0, atol=1e-12)

    def test_filter_output_norms_are_unit(self) -> None:
        """Every transformed row has unit L2 norm (B1). Supersedes the old
        escape-distance coefficient-of-variation check, which became trivial
        (cv_after ~ 0 for any input) once every output is unit-normalized."""
        rng = np.random.default_rng(404)
        n, d = 100, 20
        direction = rng.normal(size=d)
        direction /= np.linalg.norm(direction)
        X = 5.0 * rng.normal(size=(n, 1)) * direction + rng.normal(size=(n, d))
        filt = SVDAnisotropyFilter()
        filt.fit(X)
        filtered = np.array([filt.transform(x) for x in X])
        norms_after = np.linalg.norm(filtered, axis=1)
        np.testing.assert_allclose(norms_after, 1.0, atol=1e-8)


class TestSVDAnisotropyFilterFitTransform:
    """fit_transform convenience method."""

    def test_fit_transform_matches_sequential(self) -> None:
        rng = np.random.default_rng(505)
        X = rng.normal(size=(25, 10))
        filt = SVDAnisotropyFilter()
        result = filt.fit_transform(X)
        filt2 = SVDAnisotropyFilter()
        filt2.fit(X)
        expected = np.array([filt2.transform(x) for x in X])
        np.testing.assert_allclose(result, expected, atol=1e-14)
