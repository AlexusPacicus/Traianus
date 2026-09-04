"""Per-node spatial observables for the Ulpia renderer (AGENTS / Ulpia Fase 0).

Pure, observational geometry over S^{d-1}: given a node's current 384D
L2-normalized vector and the active geodetic basis B_0, derive the 6-channel
spatial contract consumed by the client:
    {x, y, z, l (density), c (affective voltage), h (escape distance)}

All channels are normalized to [0,1] (Ulpia binary contract; C = (λ+1)/2 maps
the PolarProjector voltage λ ∈ [-1,1]). Pure NumPy; no side effects, no DB
access. Recomputed on read (observational), never mutating lifecycle state
(AGENTS 4.3).
"""

from __future__ import annotations

import numpy as np

from traianus.geometry.polar_projector import PolarProjector


def _rank_axes_for(vector: np.ndarray, geodetic_matrix: dict) -> list[str]:
    """Rank geodetic axis ids by projection magnitude onto `vector` (desc)."""
    return sorted(
        geodetic_matrix.keys(),
        key=lambda k: float(np.dot(vector, geodetic_matrix[k])),
        reverse=True,
    )


def derive_spatial_observables(
    vector: np.ndarray,
    geodetic_matrix: dict[str, np.ndarray],
) -> dict[str, float]:
    """Derive the 6-channel spatial observable for a single node vector.

    Parameters
    ----------
    vector : np.ndarray of shape (d,)
        Current L2-normalized node vector v ∈ S^{d-1}.
    geodetic_matrix : dict[str, np.ndarray]
        Active geodetic basis mapping axis_id -> axis vector (k x d), k >= 3.

    Returns
    -------
    dict[str, float]
        Channels: x, y (top-2 SVD spatial coords, min-max to [-1,1]);
        z (3rd residual component); l (density ∈ [0,1], normalized projection
        variance); c (affective voltage C = (λ+1)/2 ∈ [0,1]); h (escape
        distance d_esc normalized to [0,1]).
    """
    v = np.asarray(vector, dtype=np.float64)
    axis_ids = sorted(geodetic_matrix.keys())
    if len(axis_ids) < 3:
        raise ValueError(f"Need >= 3 geodetic axes, got {len(axis_ids)}")

    basis_vecs = [np.asarray(geodetic_matrix[k], dtype=np.float64) for k in axis_ids]
    projections = np.dot(v, np.vstack(basis_vecs).T)  # (k,)

    # --- density l: normalized projection variance over the full spectrum ---
    var = float(np.var(projections))
    l = float(1.0 / (1.0 + var))  # monotone down, in (0, 1]

    # --- spatial coords x, y, z: SVD over the projection spectrum ---
    # Mean-center the (k,) projection vector reshaped to (1, k) and take the
    # principal component as the dominant axis of variation; recover x,y from
    # the top-2 left singular vectors' scores and z from the 3rd residual.
    P = projections.reshape(1, -1)
    Pc = P - np.mean(P, axis=0, keepdims=True)
    _U, S, _Vt = np.linalg.svd(Pc, full_matrices=False)
    scores = np.zeros(3)
    n_sing = min(Pc.shape[1], 3)
    scores[:n_sing] = S[:n_sing]
    max_abs = max(abs(scores[0:2])) if len(scores) > 0 else 1.0
    if max_abs == 0.0:
        max_abs = 1.0
    x = float(scores[0] / max_abs)
    y = float(scores[1] / max_abs) if len(scores) > 1 else 0.0
    z = float(scores[2] / max_abs) if len(scores) > 2 else 0.0
    x = float(np.clip(x, -1.0, 1.0))
    y = float(np.clip(y, -1.0, 1.0))
    z = float(np.clip(z, -1.0, 1.0))

    # --- affective voltage λ and escape distance d_esc (PolarProjector) ---
    # Anchor = dominant axis, dipole A/B = next two by projection ranking
    # (mirrors async_spectral_processor ADR-025 §2.3 selection).
    ranked = _rank_axes_for(v, geodetic_matrix)
    a1, a2, a3 = ranked[0], ranked[1], ranked[2]
    centroid_id = axis_ids.index(a1)
    _, lambda_val, d_esc = PolarProjector().project(
        v,
        np.asarray(geodetic_matrix[a1], dtype=np.float64),
        np.asarray(geodetic_matrix[a2], dtype=np.float64),
        np.asarray(geodetic_matrix[a3], dtype=np.float64),
        centroid_id,
    )
    c = float((lambda_val + 1.0) / 2.0)
    c = float(np.clip(c, 0.0, 1.0))

    # --- escape distance normalized to [0,1] (tanh squash for robustness) ---
    h = float(np.tanh(d_esc))
    h = float(np.clip(h, 0.0, 1.0))

    return {
        "x": x,
        "y": y,
        "z": z,
        "l": l,
        "c": c,
        "h": h,
    }
