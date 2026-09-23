"""Decompose PolarProjector per-call cost into frame-invariant vs per-vector work.

The published figure (~13.7 us/call, docs/papers/polar-projector-paper.md §3) is measured
against the stateless API, which rebuilds the local frame — normalized anchor, projected
dipole poles, dipole vector, its squared norm — on every call, even though the benchmark
holds c_1/c_A/c_B fixed across all iterations. This measures how much of the per-call cost
that rebuild accounts for, i.e. what a prepare()/evaluate() split would leave on the hot path.

It also compares two d_esc formulations at equal frame cost:

    vector form (current):  ||r - lambda*v_dipole||
    scalar form (Prop 3):   sqrt(<r,r> - 2*lambda*<r,v_dipole> + lambda^2*<v_dipole,v_dipole>)

reporting both speed and numerical agreement, since the scalar form subtracts nearly-equal
quantities when d_esc is small relative to ||r|| and can underflow negative before the sqrt.

The decomposition calls the projector's own private helpers rather than re-implementing
them, so the split measures the identical code paths that project() executes.

Read-only, offline, deterministic (fixed seeds). numpy + traianus only.
"""

import math
import sys
import time
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(REPO_ROOT))

from tests.fixtures.polar_fixtures import random_unit_vector
from traianus.geometry.polar_projector import PolarProjector

D = 384
N_VECTORS = 25_000
SEED_ANCHOR = 1
SEED_POLE_A = 2
SEED_POLE_B = 3
SEED_BASE = 1000


def _eval_scalar_form(p, v_n, frame):
    """Prop-3 scalar form of d_esc, for the conditioning comparison only."""
    r = p._project_perp(v_n - frame.c_1, frame.c1_hat)
    rv = float(np.dot(r, frame.v_dipole))
    lam = float(np.clip(rv / frame.v_dipole_norm_sq, -1.0, 1.0))
    sq = float(np.dot(r, r)) - 2.0 * lam * rv + lam * lam * frame.v_dipole_norm_sq
    return lam, (math.sqrt(sq) if sq > 0.0 else 0.0), sq


def _stats(lat: np.ndarray) -> tuple[float, float]:
    s = np.sort(lat)
    return float(lat.mean()) * 1e6, float(s[int(0.95 * len(s))]) * 1e6


def main() -> int:
    c_1 = random_unit_vector(D, SEED_ANCHOR)
    c_A = random_unit_vector(D, SEED_POLE_A)
    c_B = random_unit_vector(D, SEED_POLE_B)
    vectors = np.asarray([random_unit_vector(D, SEED_BASE + i) for i in range(N_VECTORS)])

    p = PolarProjector()

    print(f"PolarProjector latency decomposition (d={D}, N={N_VECTORS}, float64, fixed seeds)\n")

    # A. Full stateless call — the published methodology.
    lat = np.empty(N_VECTORS)
    bulk0 = time.perf_counter()
    for i in range(N_VECTORS):
        t0 = time.perf_counter()
        p.project(vectors[i], c_1, c_A, c_B, i)
        lat[i] = time.perf_counter() - t0
    bulk_full = (time.perf_counter() - bulk0) / N_VECTORS
    mean_full, p95_full = _stats(lat)

    # B. prepare() alone, repeated the same number of times.
    lat_frame = np.empty(N_VECTORS)
    for i in range(N_VECTORS):
        t0 = time.perf_counter()
        p.prepare(c_1, c_A, c_B)
        lat_frame[i] = time.perf_counter() - t0
    mean_frame, p95_frame = _stats(lat_frame)

    # C/D. Per-stimulus work only, against one prepared frame.
    frame = p.prepare(c_1, c_A, c_B)

    lat_vec = np.empty(N_VECTORS)
    d_vec = np.empty(N_VECTORS)
    bulk0 = time.perf_counter()
    for i in range(N_VECTORS):
        t0 = time.perf_counter()
        _, _, d = p.evaluate(vectors[i], frame, i)
        lat_vec[i] = time.perf_counter() - t0
        d_vec[i] = d
    bulk_vec = (time.perf_counter() - bulk0) / N_VECTORS
    mean_vec, p95_vec = _stats(lat_vec)

    lat_sca = np.empty(N_VECTORS)
    d_sca = np.empty(N_VECTORS)
    neg_sq = 0
    bulk0 = time.perf_counter()
    for i in range(N_VECTORS):
        t0 = time.perf_counter()
        _, d, sq = _eval_scalar_form(p, vectors[i], frame)
        lat_sca[i] = time.perf_counter() - t0
        d_sca[i] = d
        neg_sq += int(sq <= 0.0)
    bulk_sca = (time.perf_counter() - bulk0) / N_VECTORS
    mean_sca, p95_sca = _stats(lat_sca)

    print(f"{'stage':<42}{'mean us':>10}{'p95 us':>10}{'bulk us':>10}")
    print("-" * 72)
    print(f"{'A. project() [stateless, as published]':<42}{mean_full:>10.2f}{p95_full:>10.2f}{bulk_full*1e6:>10.2f}")
    print(f"{'B. prepare() only (invariant frame)':<42}{mean_frame:>10.2f}{p95_frame:>10.2f}{'-':>10}")
    print(f"{'C. evaluate() only [shipped API]':<42}{mean_vec:>10.2f}{p95_vec:>10.2f}{bulk_vec*1e6:>10.2f}")
    print(f"{'D. evaluate() w/ scalar-form d_esc':<42}{mean_sca:>10.2f}{p95_sca:>10.2f}{bulk_sca*1e6:>10.2f}")
    print("-" * 72)
    print(f"frame share of full call:      {100.0*mean_frame/mean_full:.1f}%")
    print(f"hot path after prepare() split: {100.0*mean_vec/mean_full:.1f}% of published cost "
          f"({mean_full/mean_vec:.2f}x faster)")
    print(f"  ... with scalar d_esc too:    {100.0*mean_sca/mean_full:.1f}% of published cost "
          f"({mean_full/mean_sca:.2f}x faster)")

    rel = np.abs(d_sca - d_vec) / np.maximum(d_vec, 1e-300)
    print("\nd_esc agreement on random unit vectors (benign regime):")
    print(f"  max relative error : {rel.max():.3e}")
    print(f"  median rel. error  : {np.median(rel):.3e}")
    print(f"  negative-under-sqrt: {neg_sq} / {N_VECTORS}")
    print(f"  d_esc range        : [{d_vec.min():.6e}, {d_vec.max():.6e}]")
    print("  (random 384-d vectors are near-orthogonal to any fixed direction, so d_esc")
    print("   stays close to ||r|| — this regime never stresses the scalar form.)")

    _adversarial_conditioning(p, frame)
    return 0


def _adversarial_conditioning(p: PolarProjector, frame) -> None:
    """Drive d_esc/||r|| toward zero, where the scalar form subtracts near-equal terms.

    Constructs r = alpha*v_hat + eps*w with w orthogonal to both the anchor and the
    dipole, so the exact escape distance is eps by construction and both formulations
    can be scored against a known truth rather than against each other.
    """
    v_norm = math.sqrt(frame.v_dipole_norm_sq)
    v_hat = frame.v_dipole / v_norm

    w = random_unit_vector(D, 77)
    w = w - np.dot(w, frame.c1_hat) * frame.c1_hat
    w = w - np.dot(w, v_hat) * v_hat
    w /= np.linalg.norm(w)

    alpha = 0.5 * v_norm  # keeps |lambda| = 0.5, away from the clip

    print("\nAdversarial conditioning sweep (exact d_esc known by construction):")
    print(f"{'d_esc/||r||':>13}{'exact d_esc':>15}{'vector-form err':>18}{'scalar-form err':>18}")
    print("-" * 64)
    for exponent in range(1, 15):
        eps = alpha * (10.0**-exponent)
        v_n = frame.c_1 + alpha * v_hat + eps * w

        _, _, d_v = p.evaluate(v_n, frame, 0)
        _, d_s, _ = _eval_scalar_form(p, v_n, frame)

        err_v = abs(d_v - eps) / eps
        err_s = abs(d_s - eps) / eps
        print(f"{10.0**-exponent:>13.0e}{eps:>15.3e}{err_v:>18.3e}{err_s:>18.3e}")


if __name__ == "__main__":
    raise SystemExit(main())
