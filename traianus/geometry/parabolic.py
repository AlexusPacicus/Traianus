"""Parabolic Corrector: 3-point quadratic trajectory reconstruction.

Given three waypoints (v_ini, v_mid, v_fin) and a continuous parameter
t in [0, 1], reconstructs intermediate positions via:

    v_reconst(t) = (1-t)*v_ini + t*v_fin + 4t(1-t)*D_mid

where D_mid = v_mid - (v_ini + v_fin)/2 is the curvature deviation.

Pure NumPy, no side effects.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


class ParabolicCorrector:
    """Stateless 3-point quadratic interpolator."""

    def deviation_vector(
        self,
        v_ini: NDArray[np.float64],
        v_mid: NDArray[np.float64],
        v_fin: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        """D_mid = v_mid - (v_ini + v_fin) / 2."""
        ini = np.asarray(v_ini, dtype=np.float64)
        mid = np.asarray(v_mid, dtype=np.float64)
        fin = np.asarray(v_fin, dtype=np.float64)
        return mid - 0.5 * (ini + fin)

    def reconstruct(
        self,
        v_ini: NDArray[np.float64],
        v_mid: NDArray[np.float64],
        v_fin: NDArray[np.float64],
        t: float,
    ) -> NDArray[np.float64]:
        """Evaluate reconstructed position at parameter t in [0, 1]."""
        ini = np.asarray(v_ini, dtype=np.float64)
        mid = np.asarray(v_mid, dtype=np.float64)
        fin = np.asarray(v_fin, dtype=np.float64)
        D_mid = mid - 0.5 * (ini + fin)
        coeff = 4.0 * t * (1.0 - t)
        return (1.0 - t) * ini + t * fin + coeff * D_mid

    def reconstruct_batch(
        self,
        v_ini: NDArray[np.float64],
        v_mid: NDArray[np.float64],
        v_fin: NDArray[np.float64],
        t_values: list[float],
    ) -> list[NDArray[np.float64]]:
        """Evaluate reconstructed positions for multiple t values."""
        ini = np.asarray(v_ini, dtype=np.float64)
        mid = np.asarray(v_mid, dtype=np.float64)
        fin = np.asarray(v_fin, dtype=np.float64)
        D_mid = mid - 0.5 * (ini + fin)
        results: list[NDArray[np.float64]] = []
        for t in t_values:
            coeff = 4.0 * t * (1.0 - t)
            results.append((1.0 - t) * ini + t * fin + coeff * D_mid)
        return results
