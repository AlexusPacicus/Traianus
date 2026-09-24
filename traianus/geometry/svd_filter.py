"""SVD Anisotropy Filter: local anisotropy reduction via orthogonal projection.

Projects each input vector onto the null space of the first right singular
vector (u1), removing the dominant component of the embedding cone. Output
vectors are re-normalized to unit L2 norm (Traianus substrate invariant,
AGENTS 3.1). Pure NumPy, no side effects.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


class SVDAnisotropyFilter:
    """Projects vectors onto the null space of the dominant component (u1).

    Local anisotropy reduction via orthogonal projection onto the null space
    of the first right singular vector (u1), removing the dominant component
    of the embedding cone. Output is re-normalized to unit L2 norm.

    Parameters
    ----------
    eps : float
        Numerical guard for near-zero norms.
    """

    def __init__(self, eps: float = 1e-12, dominance_ratio: float = 1.5) -> None:
        self.eps = float(eps)
        self.dominance_ratio = float(dominance_ratio)
        self.u1_: NDArray[np.float64] = np.empty(0, dtype=np.float64)

    def fit(self, X: NDArray[np.float64]) -> SVDAnisotropyFilter:
        """Compute u1 from the first right singular vector of X.

        For n >= 2 the data is mean-centered (standard PCA); for n == 1 the
        raw vector is used so the single dominant direction is captured.

        If the first singular value is not dominant relative to the remaining
        ones (ratio <= dominance_ratio), u1 is set to zero (isotropic data).

        Parameters
        ----------
        X : NDArray[np.float64] of shape (n, d)
            Input data matrix.
        """
        X_arr = np.asarray(X, dtype=np.float64)
        d = X_arr.shape[1]
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

    def transform(self, v: NDArray[np.float64]) -> NDArray[np.float64]:
        """Subtract u1-projection from v, then re-normalize to unit L2 norm.

        v_filtered = v - (u1 . v) u1, divided by its own L2 norm unless that
        norm is at or below self.eps (the single-vector edge case: fitting on
        one row makes u1 that row's own direction, so subtracting it leaves a
        near-zero vector), in which case it is returned unmodified.
        """
        v_arr = np.asarray(v, dtype=np.float64)
        proj = np.dot(self.u1_, v_arr)
        filtered = v_arr - proj * self.u1_
        norm = np.linalg.norm(filtered)
        if norm > self.eps:
            return filtered / norm
        return filtered

    def fit_transform(self, X: NDArray[np.float64]) -> NDArray[np.float64]:
        """Fit u1 and transform all rows of X (same guarded re-normalization as transform())."""
        self.fit(X)
        X_arr = np.asarray(X, dtype=np.float64)
        projections = X_arr @ self.u1_  # (n,)
        filtered = X_arr - np.outer(projections, self.u1_)
        norms = np.linalg.norm(filtered, axis=1, keepdims=True)
        safe_norms = np.where(norms > self.eps, norms, 1.0)
        return np.where(norms > self.eps, filtered / safe_norms, filtered)
