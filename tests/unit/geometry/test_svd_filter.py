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

    def test_filter_preserves_orthogonal_components(self) -> None:
        u1 = np.zeros(self.d)
        u1[0] = 1.0
        ortho = np.zeros(self.d)
        ortho[1] = 1.0
        X = np.outer(np.linspace(1, 10, self.n), u1) + 0.5 * ortho
        filt = SVDAnisotropyFilter()
        filt.fit(X)
        filtered = filt.transform(X[0])
        np.testing.assert_allclose(filtered[1], X[0][1], atol=1e-10)
        for i in range(2, self.d):
            np.testing.assert_allclose(filtered[i], X[0][i], atol=1e-10)


class TestSVDAnisotropyFilterIsotropic:
    """Filter on isotropic data should change vectors minimally."""

    def test_filter_identity_on_isotropic_data(self) -> None:
        rng = np.random.default_rng(202)
        n, d = 200, 32
        X = rng.normal(size=(n, d))
        filt = SVDAnisotropyFilter()
        filt.fit(X)
        v = X[0].copy()
        filtered = filt.transform(v)
        diff = np.linalg.norm(filtered - v)
        original_norm = np.linalg.norm(v)
        assert diff / original_norm < 0.15, (
            f"Isotropic filter changed vector by {diff / original_norm:.3f} (>15%)"
        )


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
        np.testing.assert_allclose(filtered, 0.0, atol=1e-12)

    def test_filter_increases_escape_distance_uniformity(self) -> None:
        rng = np.random.default_rng(404)
        n, d = 100, 20
        direction = rng.normal(size=d)
        direction /= np.linalg.norm(direction)
        X = 5.0 * rng.normal(size=(n, 1)) * direction + rng.normal(size=(n, d))
        filt = SVDAnisotropyFilter()
        filt.fit(X)
        norms_before = np.linalg.norm(X, axis=1)
        filtered = np.array([filt.transform(x) for x in X])
        norms_after = np.linalg.norm(filtered, axis=1)
        cv_before = np.std(norms_before) / (np.mean(norms_before) + 1e-12)
        cv_after = np.std(norms_after) / (np.mean(norms_after) + 1e-12)
        assert cv_after <= cv_before + 0.01, (
            f"CV not reduced: before={cv_before:.4f}, after={cv_after:.4f}"
        )


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
