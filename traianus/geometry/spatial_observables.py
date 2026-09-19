"""Per-node spatial observables for the Ulpia renderer (AGENTS / Ulpia Fase 0).

Pure, observational geometry over S^{d-1}: given a node's current 384D
L2-normalized vector and the active geodetic basis B_0, derive the 6-channel
spatial contract consumed by the client:
    {x, y, z, l (density), c (affective voltage), h (escape distance)}

Position is a direct readout of the PolarProjector decomposition: x is the
voltage λ along the dipole, y the component on the anchor ⟨v, ĉ₁⟩. It is
therefore local and O(d) — a node's coordinates depend only on its own vector
and the active frame, never on the rest of the corpus, so incremental ingestion
cannot displace already-placed nodes.

The escape distance is deliberately NOT a position channel. On S^{d-1} with a
unit anchor it is analytically redundant with the anchor component:

    ‖r‖² = ‖v − c₁‖² − ⟨v − c₁, ĉ₁⟩² = (2 − 2z) − (z − 1)² = 1 − z²
    d_esc² = ‖r‖² − λ²‖v_dipole‖² = 1 − z² − λ²‖v_dipole‖²

so it carries no information the pair (λ, z) does not already hold. Measured on
the frozen Spinoza corpus (n = 2,221) that redundancy shows up as Pearson
corr(tanh d_esc, z) = −0.968 and a third principal component worth 1.03% of the
standardized variance. Promoting it to an axis would amplify float noise into
apparent structure; it stays on the chromatic channel h, where its narrow
spread needs no amplification. Recovering a genuine third axis needs a second
dipole (a fourth and fifth ranked geodetic axis), not a rescaling of this one.

Raw positions occupy a narrow band (λ: 7.2% of [-1,1], anchor: 19.1% on that
same corpus), so the client applies a SpatialCalibration frozen per epoch.

Chromatic channels are normalized to [0,1] (Ulpia binary contract;
C = (λ+1)/2 maps the PolarProjector voltage λ ∈ [-1,1]). Pure NumPy; no side
effects, no DB access. Recomputed on read (observational), never mutating
lifecycle state (AGENTS 4.3).
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import NamedTuple

import numpy as np

from traianus.geometry.polar_projector import PolarProjector

EPOCH_PROVENANCE = "PROSTHETIC_NSM_V1"
DEFAULT_K_SIGMA = 3.0


def _standardize(value: float, mu: float, sigma: float, k_sigma: float) -> float:
    """Center, scale to k sigma, clip into [-1, 1].

    A degenerate spread (every node on one coordinate) carries no separation to
    expand, so the channel collapses to the center of the box rather than
    dividing by zero and emitting NaN into the GPU buffer.
    """
    spread = k_sigma * sigma
    if not np.isfinite(spread) or spread <= 0.0:
        return 0.0
    return float(np.clip((value - mu) / spread, -1.0, 1.0))


class SpatialCalibration(NamedTuple):
    """Frozen affine map from raw polar coordinates into the renderer's box.

    Fitted once per epoch and stored under that epoch tag, so a node's rendered
    position is stable for the whole life of the epoch and moves only on an
    explicit, logged recalibration (the ADR-025 §2.2 Schmitt Trigger boundary).
    Fitting per request instead would re-place every existing node on each
    ingestion — the incremental drift this operator exists to avoid.
    """

    epoch_provenance: str
    mu_x: float
    sigma_x: float
    mu_y: float
    sigma_y: float
    k_sigma: float = DEFAULT_K_SIGMA

    def apply(self, x: float, y: float) -> tuple[float, float]:
        return (
            _standardize(x, self.mu_x, self.sigma_x, self.k_sigma),
            _standardize(y, self.mu_y, self.sigma_y, self.k_sigma),
        )


def fit_spatial_calibration(
    raw_positions: Iterable[tuple[float, float]],
    epoch_provenance: str,
    k_sigma: float = DEFAULT_K_SIGMA,
) -> SpatialCalibration:
    """Fit the per-epoch affine map from the observed raw (x, y) pairs."""
    pairs = np.asarray(list(raw_positions), dtype=np.float64)
    if pairs.size == 0:
        raise ValueError("Cannot fit a calibration from an empty population")
    if pairs.ndim != 2 or pairs.shape[1] != 2:
        raise ValueError(f"Need an (n, 2) array of (x, y) pairs, got {pairs.shape}")
    mu = pairs.mean(axis=0)
    sigma = pairs.std(axis=0)
    return SpatialCalibration(
        epoch_provenance,
        float(mu[0]),
        float(sigma[0]),
        float(mu[1]),
        float(sigma[1]),
        float(k_sigma),
    )


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
    calibration: SpatialCalibration | None = None,
) -> dict[str, float]:
    """Derive the 6-channel spatial observable for a single node vector.

    Parameters
    ----------
    vector : np.ndarray of shape (d,)
        Current L2-normalized node vector v ∈ S^{d-1}.
    geodetic_matrix : dict[str, np.ndarray]
        Active geodetic basis mapping axis_id -> axis vector (k x d), k >= 3.
    calibration : SpatialCalibration, optional
        Frozen per-epoch affine map applied to (x, y). Omitted, the raw polar
        coordinates are returned unscaled.

    Returns
    -------
    dict[str, float]
        Channels: x (voltage λ ∈ [-1,1]); y (anchor component ⟨v, ĉ₁⟩);
        z (reserved, always 0.0 — see the module docstring); l (density
        ∈ [0,1], normalized projection variance); c (affective voltage
        C = (λ+1)/2 ∈ [0,1]); h (escape distance d_esc normalized to [0,1]).
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

    # --- affective voltage λ and escape distance d_esc (PolarProjector) ---
    # Anchor = dominant axis, dipole A/B = next two by projection ranking
    # (mirrors async_spectral_processor ADR-025 §2.3 selection).
    ranked = _rank_axes_for(v, geodetic_matrix)
    a1, a2, a3 = ranked[0], ranked[1], ranked[2]
    centroid_id = axis_ids.index(a1)
    c_1 = np.asarray(geodetic_matrix[a1], dtype=np.float64)
    _, lambda_val, d_esc = PolarProjector().project(
        v,
        c_1,
        np.asarray(geodetic_matrix[a2], dtype=np.float64),
        np.asarray(geodetic_matrix[a3], dtype=np.float64),
        centroid_id,
    )

    # --- spatial coords: the two independent channels of the decomposition ---
    # x = voltage along the dipole, y = component on the anchor. z stays 0.0:
    # d_esc is analytically determined by (λ, y) here, so there is no third
    # independent axis to place a node on (module docstring).
    x = float(np.clip(lambda_val, -1.0, 1.0))
    c1_norm = float(np.linalg.norm(c_1))
    y = float(np.dot(v, c_1) / c1_norm) if c1_norm > 0.0 else 0.0
    y = float(np.clip(y, -1.0, 1.0))
    if calibration is not None:
        x, y = calibration.apply(x, y)
    z = 0.0

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
