"""Perspective at a vector q: the poles are the two axes with the largest projection on q.

The perspective at q (frontend/audits/R4.md, "Perspective at q") is drawn in a frame built from
q and two poles, the axes a_k with the largest <q, a_k>, ties by axis id ascending, c_A the
larger. Pure NumPy, no storage, no state (AGENTS 4.3).

perspective_frame builds the frame at q from those poles; observe gives the z-scored coordinates of
every vector in it (frontend/audits/R4.md, "Observed space").
"""

from __future__ import annotations

from typing import NamedTuple

import numpy as np
from numpy.typing import NDArray

from traianus.geometry.polar_projector import PolarFrame, PolarProjector

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


class PerspectiveFrame(NamedTuple):
    """Frame at q: the poles (c_A, c_B), the PolarProjector frame, and whether it is the fallback."""

    poles: tuple[str, str]
    frame: PolarFrame
    fallback: bool


def _unit(axis: np.ndarray) -> NDArray[np.float64]:
    a = np.asarray(axis, dtype=np.float64)
    return a / float(np.linalg.norm(a))


def _as_finite(name: str, value: np.ndarray) -> NDArray[np.float64]:
    a = np.asarray(value, dtype=np.float64)
    if not np.all(np.isfinite(a)):
        raise ValueError(f"{name} must be finite")
    return a


def perspective_frame(q: np.ndarray, basis: dict[str, np.ndarray]) -> PerspectiveFrame:
    """Frame of the perspective at q: PolarProjector.prepare(q, a_A, a_B) with default parameters.

    (c_A, c_B) are the poles of `select_poles` and a_A, a_B their unit axes; q enters as given, so
    frame.c1_hat is q normalised. `fallback` is True iff the projector's collinearity test holds on
    the poles' projections orthogonal to c1_hat; the frame then keeps the projector's canonical
    dipole. ValueError from `select_poles` or `prepare` propagates.
    """
    poles = select_poles(q, basis)
    a_a, a_b = _unit(basis[poles[0]]), _unit(basis[poles[1]])
    projector = PolarProjector()
    frame = projector.prepare(q, a_a, a_b)
    fallback = projector._is_collinear(
        projector._project_perp(a_a, frame.c1_hat), projector._project_perp(a_b, frame.c1_hat)
    )
    return PerspectiveFrame(poles, frame, fallback)


def observe(
    vectors: np.ndarray,
    anchor_index: int,
    horizontal: np.ndarray | None = None,
    colours: np.ndarray | None = None,
) -> NDArray[np.float64]:
    """Observed coordinates [x, y, colours...] of every vector, for q = vectors[anchor_index].

    x = <v, horizontal> (only if given), y = <v, q_hat>, then the columns of `colours` as given.
    Each column is z-scored with its mean and population sd (ddof=0) over the N - 1 rows other than
    the anchor, the anchor row taking the same transform; a column constant over those rows maps to
    0.0. Row i of the (N, k) float64 result belongs to vectors[i].
    """
    v = _as_finite("vectors", vectors)
    if v.ndim != 2 or v.shape[0] < 2:
        raise ValueError(f"vectors must be (N, d) with N >= 2, got shape {v.shape}")
    n, d = v.shape
    is_index = isinstance(anchor_index, (int, np.integer)) and not isinstance(anchor_index, bool)
    if not is_index or not 0 <= anchor_index < n:
        raise ValueError(f"anchor_index must be an integer in [0, {n}), got {anchor_index!r}")
    q = v[anchor_index]
    norm = float(np.linalg.norm(q))
    if norm <= 0.0:
        raise ValueError("the anchor row has zero norm")
    parts: list[NDArray[np.float64]] = []
    if horizontal is not None:
        h = _as_finite("horizontal", horizontal)
        if h.shape != (d,):
            raise ValueError(f"horizontal must have shape ({d},), got {h.shape}")
        parts.append(v @ h)
    parts.append(v @ (q / norm))
    if colours is not None:
        c = _as_finite("colours", colours)
        if c.ndim != 2 or c.shape[0] != n or c.shape[1] < 1:
            raise ValueError(f"colours must have shape ({n}, m) with m >= 1, got {c.shape}")
        parts.append(c)
    raw = np.column_stack(parts)
    others = np.delete(raw, anchor_index, axis=0)
    flat = others.max(axis=0) == others.min(axis=0)
    spread = np.where(flat, 1.0, others.std(axis=0))
    return np.where(flat, 0.0, (raw - others.mean(axis=0)) / spread)
