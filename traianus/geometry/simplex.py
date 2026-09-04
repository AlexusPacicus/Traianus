"""Semantic Simplex: local geometric control cell over S^{d-1}.

Continuously self-calibrating simplex with Z-score control, face overlap
detection, and re-anchoring / recalibration classification. Pure NumPy,
no side effects.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

RECALIBRATION_SIGNAL: str = "RECALIBRATION_SIGNAL"

_VERTICES = ("c1", "cA", "cB")


class SemanticSimplex:
    """Triangular control cell defined by three projected vertices and their
    local standard deviations.

    Parameters
    ----------
    c1_perp : NDArray[np.float64]
        Projected anchor centroid (d,).
    cA_perp : NDArray[np.float64]
        Projected dipole pole A (d,).
    cB_perp : NDArray[np.float64]
        Projected dipole pole B (d,).
    sigma1 : float
        Standard deviation of anchor domain (>= 0).
    sigmaA : float
        Standard deviation of dipole A domain (>= 0).
    sigmaB : float
        Standard deviation of dipole B domain (>= 0).
    eps : float
        Small constant to prevent division by zero in Z-score.
    """

    def __init__(
        self,
        c1_perp: NDArray[np.float64],
        cA_perp: NDArray[np.float64],
        cB_perp: NDArray[np.float64],
        sigma1: float,
        sigmaA: float,
        sigmaB: float,
        eps: float = 1e-12,
    ) -> None:
        self.c1_perp = np.asarray(c1_perp, dtype=np.float64)
        self.cA_perp = np.asarray(cA_perp, dtype=np.float64)
        self.cB_perp = np.asarray(cB_perp, dtype=np.float64)
        self.sigma1 = float(sigma1)
        self.sigmaA = float(sigmaA)
        self.sigmaB = float(sigmaB)
        self.eps = float(eps)
        self._centers: list[NDArray[np.float64]] = [self.c1_perp, self.cA_perp, self.cB_perp]
        self._sigmas: list[float] = [self.sigma1, self.sigmaA, self.sigmaB]

    def zscore(self, v_n_perp: NDArray[np.float64]) -> dict[str, float]:
        """Compute local Z-score for each vertex: z_i = ||v - c_i|| / (sigma_i + eps)."""
        v = np.asarray(v_n_perp, dtype=np.float64)
        return {
            name: float(np.linalg.norm(v - c) / (sigma + self.eps))
            for name, c, sigma in zip(_VERTICES, self._centers, self._sigmas)
        }

    def overlap(self, i: str, j: str) -> float:
        """Face overlap M_ij = (sigma_i + sigma_j) - ||c_i - c_j||."""
        idx_map = {"c1": 0, "cA": 1, "cB": 2}
        ii, jj = idx_map[i], idx_map[j]
        dist = float(np.linalg.norm(self._centers[ii] - self._centers[jj]))
        return (self._sigmas[ii] + self._sigmas[jj]) - dist

    def classify(self, v_n_perp: NDArray[np.float64]) -> dict[str, object]:
        """Classify stimulus: RECALIBRATION_SIGNAL if min(z_i) > 1, else REANCHORING."""
        z = self.zscore(v_n_perp)
        min_z = min(z.values())
        min_overlap = min(
            self.overlap(a, b)
            for a, b in (("c1", "cA"), ("c1", "cB"), ("cA", "cB"))
        )
        action = RECALIBRATION_SIGNAL if min_z > 1.0 else "REANCHORING"
        return {"z_scores": z, "overlap_min": float(min_overlap), "action": action}
