"""SVD Anisotropy Filter: corpus-mean centering and dominant-anisotropy
removal via orthogonal projection.

Centers each input vector by the fitted corpus mean (removing the shared
bias) and projects out the first right singular vector (u1, the dominant
anisotropic direction of the embedding cone). The L2 norm of the
centered-and-projected vector -- the residual norm -- is exposed as a
reusable per-vector signal, before the vector is re-normalized to unit L2
norm (Traianus substrate invariant, AGENTS 3.1). Supersedes the prior,
anisotropy-reduction-only revision, which projected u1 out of the raw
(uncentered) vector and discarded the residual norm entirely. Pure NumPy,
no side effects.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


class SVDAnisotropyFilter:
    """Centers by the corpus mean and projects out the dominant component (u1).

    Removes the corpus's shared mean (bias) and its dominant anisotropic
    direction (u1, the first right singular vector) from each vector, then
    exposes the pre-renormalization residual norm as a reusable per-vector
    signal before returning a unit-L2-norm vector.

    Parameters
    ----------
    eps : float
        Numerical guard for near-zero norms.
    """

    def __init__(self, eps: float = 1e-12, dominance_ratio: float = 1.5) -> None:
        self.eps = float(eps)
        self.dominance_ratio = float(dominance_ratio)
        self.u1_: NDArray[np.float64] = np.empty(0, dtype=np.float64)
        self.mean_: NDArray[np.float64] = np.empty(0, dtype=np.float64)

    def fit(self, X: NDArray[np.float64]) -> SVDAnisotropyFilter:
        """Compute u1 from the first right singular vector of X, and store
        the corpus mean.

        For n >= 2 the data is mean-centered (standard PCA) to find u1; for
        n == 1 the raw vector is used so the single dominant direction is
        captured. The corpus mean is always stored in self.mean_ (computed
        the same way regardless of n), for transform()/fit_transform() to
        center by.

        If the first singular value is not dominant relative to the remaining
        ones (ratio <= dominance_ratio), u1 is set to zero (isotropic data).

        Parameters
        ----------
        X : NDArray[np.float64] of shape (n, d)
            Input data matrix.
        """
        X_arr = np.asarray(X, dtype=np.float64)
        d = X_arr.shape[1]
        self.mean_ = np.mean(X_arr, axis=0)
        X_work = X_arr - np.mean(X_arr, axis=0) if X_arr.shape[0] >= 2 else X_arr
        _, S, Vt = np.linalg.svd(X_work, full_matrices=False)
        if (
            S.size == 0
            or S[0] < self.eps
            or (S.size > 1 and S[0] <= self.dominance_ratio * np.mean(S[1:]))
        ):
            self.u1_ = np.zeros(d, dtype=np.float64)
        else:
            self.u1_ = Vt[0].copy()
        return self

    def transform(self, v: NDArray[np.float64]) -> tuple[NDArray[np.float64], float]:
        """Center v by the corpus mean, project out u1, and return the unit
        vector together with the pre-renormalization residual norm.

        v_centered = v - self.mean_
        v_filtered = v_centered - (u1 . v_centered) u1
        norm_residual = ||v_filtered||

        v_filtered is divided by norm_residual unless that norm is at or
        below self.eps (e.g. the single-vector fit case, where centering by
        the corpus's own single-row mean yields an all-zero centered
        vector), in which case it is returned unmodified. Returns
        (v_unit, norm_residual): the residual norm is a reusable per-vector
        signal, not discarded.
        """
        v_arr = np.asarray(v, dtype=np.float64)
        v_centered = v_arr - self.mean_
        proj = np.dot(self.u1_, v_centered)
        filtered = v_centered - proj * self.u1_
        norm_residual = float(np.linalg.norm(filtered))
        if norm_residual > self.eps:
            v_unit = filtered / norm_residual
        else:
            v_unit = filtered
        return v_unit, norm_residual

    def fit_transform(
        self, X: NDArray[np.float64]
    ) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
        """Fit u1/mean_ and transform all rows of X (row-wise equivalent of
        fit() followed by transform()). Returns (unit_vectors, residual_norms),
        each row guard-renormalized the same way as transform()."""
        self.fit(X)
        X_arr = np.asarray(X, dtype=np.float64)
        X_centered = X_arr - self.mean_
        projections = X_centered @ self.u1_  # (n,)
        filtered = X_centered - np.outer(projections, self.u1_)
        norms = np.linalg.norm(filtered, axis=1)
        safe_norms = np.where(norms > self.eps, norms, 1.0)
        unit_vectors = np.where(
            (norms > self.eps)[:, None], filtered / safe_norms[:, None], filtered
        )
        return unit_vectors, norms
