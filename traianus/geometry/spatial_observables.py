"""Spatial observables in one frame per epoch (Ulpia observation, ADR-024, ADR-026).

The frame is fitted once on the nodes present and frozen with the epoch: the geodetic axes are
ranked by their mean projection ⟨v, â_k⟩ (descending, ties by axis id); rank 1 is the anchor ĉ₁,
ranks (2, 3) and (6, 7) the dipoles used, rank 8 the leftover axis; poles are always the
normalised â. Every node is measured in that one frame, so the overview is a single map, and a
node never moves until an explicit, logged re-fit.

Raw channels, unclipped (the ones K6 measured, docs/methodology/instrument-audit/contracts.md §1):
    x = λ₁ = ⟨v, w₁⟩/‖w₁‖²,  y = ⟨v, ĉ₁⟩,  λ₃ = ⟨v, w₃⟩/‖w₃‖²,  a₈ = ⟨v, P⊥â_(8)⟩/‖P⊥â_(8)‖²
with w_j the PolarProjector dipole. K6 admitted λ₃ and a₈ as colour (data/refapp/K6_result.json);
λ₂ and the projection-variance density were second-order predictable from the position, and
d_esc is fixed by (λ, y) (ADR-026 §1).

Observables: each raw channel is standardised by the frozen mean and k·sd and clipped to
[-1, 1]; x and y as is; h = (s(λ₃) + 1)/2 and c = (s(a₈) + 1)/2; l constant (lightness fixed
for legibility, the author's choice); z = 0 until K8 measures an orthogonalised second dipole.
Pure NumPy, no DB access, never mutates state (AGENTS 4.3).
"""

from __future__ import annotations

from typing import NamedTuple

import numpy as np
from numpy.typing import NDArray

from traianus.geometry.polar_projector import PolarFrame, PolarProjector

EPOCH_PROVENANCE = "PROSTHETIC_NSM_V1"
DEFAULT_K_SIGMA = 3.0
CHANNELS = ("x", "y", "lambda_3", "a_8")
L_CONSTANT = 0.5
N_RANKED = 8


class EpochFrame(NamedTuple):
    """Frozen frame of one epoch: axis ranking plus mean and population sd per channel."""

    epoch_provenance: str
    ranking: tuple[str, ...]
    mu: tuple[float, ...]
    sigma: tuple[float, ...]
    k_sigma: float = DEFAULT_K_SIGMA


def _standardize(value: float, mu: float, sigma: float, k_sigma: float) -> float:
    """Center, scale to k sigma, clip into [-1, 1]; a zero spread maps to the centre."""
    spread = k_sigma * sigma
    if not np.isfinite(spread) or spread <= 0.0:
        return 0.0
    return float(np.clip((value - mu) / spread, -1.0, 1.0))


def _unit_axes(basis: dict[str, np.ndarray]) -> dict[str, NDArray[np.float64]]:
    if len(basis) < N_RANKED:
        raise ValueError(f"the epoch frame needs at least {N_RANKED} axes, got {len(basis)}")
    unit = {}
    for axis_id, axis in basis.items():
        a = np.asarray(axis, dtype=np.float64)
        norm = float(np.linalg.norm(a))
        if norm <= 0.0:
            raise ValueError(f"axis {axis_id} has zero norm")
        unit[axis_id] = a / norm
    return unit


def rank_axes(vectors: np.ndarray, basis: dict[str, np.ndarray]) -> tuple[str, ...]:
    """Axis ids by mean projection over `vectors`, descending; ties by axis id."""
    v = np.atleast_2d(np.asarray(vectors, dtype=np.float64))
    unit = _unit_axes(basis)
    means = {axis_id: float(np.mean(v @ a)) for axis_id, a in unit.items()}
    return tuple(sorted(unit, key=lambda axis_id: (-means[axis_id], axis_id)))


def _geometry(
    basis: dict[str, np.ndarray], ranking: tuple[str, ...]
) -> tuple[NDArray[np.float64], PolarFrame, PolarFrame, NDArray[np.float64]]:
    unit = _unit_axes(basis)
    r = [unit[axis_id] for axis_id in ranking[:N_RANKED]]
    projector = PolarProjector()
    dipoles = []
    for name, (a, b) in (("dipole 1", (r[1], r[2])), ("dipole 3", (r[5], r[6]))):
        frame = projector.prepare(r[0], a, b)
        if projector._is_collinear(
            projector._project_perp(a, frame.c1_hat), projector._project_perp(b, frame.c1_hat)
        ):
            raise ValueError(f"{name} is on the operator's collinear fallback, not a contrast")
        dipoles.append(frame)
    c1_hat = dipoles[0].c1_hat
    p8 = r[7] - float(r[7] @ c1_hat) * c1_hat
    if float(p8 @ p8) <= 0.0:
        raise ValueError("degenerate rank-8 axis: ||P_perp a_(8)||^2 underflowed to zero")
    return c1_hat, dipoles[0], dipoles[1], p8


def raw_channels(
    vectors: np.ndarray, basis: dict[str, np.ndarray], ranking: tuple[str, ...]
) -> dict[str, NDArray[np.float64]]:
    """Unclipped x, y, λ₃, a₈ of one vector (d,) or of each row of (n, d), in the given frame."""
    v = np.asarray(vectors, dtype=np.float64)
    c1_hat, d1, d3, p8 = _geometry(basis, ranking)
    return {
        "x": v @ d1.v_dipole / d1.v_dipole_norm_sq,
        "y": v @ c1_hat,
        "lambda_3": v @ d3.v_dipole / d3.v_dipole_norm_sq,
        "a_8": v @ p8 / (p8 @ p8),
    }


_U = np.finfo(np.float64).eps / 2  # unit roundoff


def _gamma(n: int) -> float:
    """Higham, *Accuracy and Stability of Numerical Algorithms* (2nd ed.), §3.1: the relative
    bound on n chained roundings, e.g. an n-term dot product."""
    nu = n * _U
    return nu / (1.0 - nu)


def _effective_axes(
    basis: dict[str, np.ndarray], ranking: tuple[str, ...]
) -> dict[str, NDArray[np.float64]]:
    """The direction each channel of raw_channels is a dot product with (division folded in)."""
    c1_hat, d1, d3, p8 = _geometry(basis, ranking)
    return {
        "x": d1.v_dipole / d1.v_dipole_norm_sq,
        "y": c1_hat,
        "lambda_3": d3.v_dipole / d3.v_dipole_norm_sq,
        "a_8": p8 / (p8 @ p8),
    }


def _rounding_floor(name: str, axis: NDArray[np.float64], d: int, max_row_norm: float) -> float:
    """A channel's population sd cannot be measured below this (γ_d, Higham §3.1): by
    Cauchy-Schwarz the rounding error of one row's dot product is at most γ_d * ||row|| * ||axis||;
    x, lambda_3, a_8 divide by a squared norm after the dot product, one further rounding, so γ_d
    is taken over d + 1 terms for them; y is the undivided dot product with c1_hat, over d."""
    n = d if name == "y" else d + 1
    return _gamma(n) * max_row_norm * float(np.linalg.norm(axis))


def fit_epoch_frame(
    vectors: np.ndarray,
    basis: dict[str, np.ndarray],
    epoch_provenance: str,
    k_sigma: float = DEFAULT_K_SIGMA,
) -> EpochFrame:
    """Fit the frame once, on the (n, d) population present; the caller freezes it."""
    v = np.asarray(vectors, dtype=np.float64)
    if v.ndim != 2 or v.shape[0] == 0:
        raise ValueError("cannot fit an epoch frame on an empty population")
    ranking = rank_axes(v, basis)[:N_RANKED]
    raw = raw_channels(v, basis, ranking)
    axes = _effective_axes(basis, ranking)
    d, max_row_norm = v.shape[1], float(np.max(np.linalg.norm(v, axis=1)))
    sigma = tuple(
        0.0 if (std := float(np.std(raw[name]))) <= _rounding_floor(name, axes[name], d, max_row_norm)
        else std
        for name in CHANNELS
    )
    return EpochFrame(
        epoch_provenance,
        ranking,
        tuple(float(np.mean(raw[name])) for name in CHANNELS),
        sigma,
        float(k_sigma),
    )


def derive_spatial_observables(
    vector: np.ndarray, basis: dict[str, np.ndarray], frame: EpochFrame
) -> dict[str, float]:
    """{x, y, z, l, c, h} of one node in the frozen epoch frame (module docstring)."""
    raw = raw_channels(vector, basis, frame.ranking)
    s = {
        name: _standardize(float(raw[name]), frame.mu[j], frame.sigma[j], frame.k_sigma)
        for j, name in enumerate(CHANNELS)
    }
    return {
        "x": s["x"],
        "y": s["y"],
        "z": 0.0,
        "l": L_CONSTANT,
        "c": (s["a_8"] + 1.0) / 2.0,
        "h": (s["lambda_3"] + 1.0) / 2.0,
    }
