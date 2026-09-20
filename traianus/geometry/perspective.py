"""Perspective at a vector q: the poles are the two axes with the largest projection on q.

The perspective at q (frontend/audits/R4.md, "Perspective at q") is drawn in a frame built from
q and two poles, the axes a_k with the largest <q, a_k>, ties by axis id ascending, c_A the
larger. Pure NumPy, no storage, no state (AGENTS 4.3).
"""

from __future__ import annotations

import numpy as np

N_POLES = 2


def select_poles(q: np.ndarray, basis: dict[str, np.ndarray]) -> tuple[str, str]:
    """Ids (c_A, c_B) of the two axes with the largest <q, a_k>, a_k the unit axis; c_A the larger.

    The projection is exact in float64 with q as given; ties go to the smaller axis id (str order),
    so the result depends neither on the insertion order of `basis` nor on the scale of q.
    """
    v = np.asarray(q, dtype=np.float64)
    if v.ndim != 1:
        raise ValueError(f"q must be 1-D, got {v.ndim} dimensions")
    if not np.all(np.isfinite(v)):
        raise ValueError("q must be finite")
    if float(np.linalg.norm(v)) <= 0.0:
        raise ValueError("q has zero norm")
    if len(basis) < N_POLES:
        raise ValueError(f"the perspective needs at least {N_POLES} axes, got {len(basis)}")
    projection = {}
    for axis_id, axis in basis.items():
        a = np.asarray(axis, dtype=np.float64)
        if a.shape != v.shape:
            raise ValueError(
                f"dimension mismatch: q has shape {v.shape}, axis {axis_id} has shape {a.shape}"
            )
        if not np.all(np.isfinite(a)):
            raise ValueError(f"axis {axis_id} must be finite")
        norm = float(np.linalg.norm(a))
        if norm <= 0.0:
            raise ValueError(f"axis {axis_id} has zero norm")
        projection[axis_id] = float(v @ (a / norm))
    pole_a, pole_b, *_ = sorted(projection, key=lambda axis_id: (-projection[axis_id], axis_id))
    return pole_a, pole_b
