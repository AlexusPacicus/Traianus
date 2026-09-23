"""Generate the Polar Projector delta-sweep table for the manuscript.

Reproduces the same construction as `verify_polar_delta_table.py` (§5
collinearity scenario, d=384, fixed seed) but at a sample size chosen so the
2-sigma sampling bound on the reported variances is below 3%, instead of the
~9% bound at N=1000 that produced the mismatch flagged during review.

Standard error of a sample variance: SE(sigma2) ~= sigma2 * sqrt(2/(N-1)).
At N=10,000, sqrt(2/9999) ~= 1.41%, so the 2-sigma bound is ~2.8%.
"""

import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tests.fixtures.polar_fixtures import collinear_centroids, random_unit_vector
from traianus.geometry.polar_projector import PolarProjector

D = 384
N_VECTORS = 10_000
DELTAS = (0.001, 0.010, 0.050, 0.100, 0.200, 0.500)


def _measure(delta: float) -> tuple[float, float, float]:
    c_1 = random_unit_vector(D, 1)
    c_A, c_B = collinear_centroids(c_1, D)
    projector = PolarProjector(delta=delta)
    lambdas = np.empty(N_VECTORS, dtype=np.float64)
    d_escs = np.empty(N_VECTORS, dtype=np.float64)
    for i in range(N_VECTORS):
        v_n = random_unit_vector(D, 1000 + i)
        _, lam, d_esc = projector.project(v_n, c_1, c_A, c_B, i)
        lambdas[i] = lam
        d_escs[i] = d_esc
    sigma2_lambda = float(np.var(lambdas))
    sigma2_esc = float(np.var(d_escs))
    return sigma2_lambda, sigma2_esc, sigma2_lambda / sigma2_esc


def main() -> int:
    se_bound = (2 / (N_VECTORS - 1)) ** 0.5
    print(f"Polar Projector delta-sweep table ({D}D, N={N_VECTORS}, seed=42)")
    print(f"2-sigma sampling bound on variances: ~{2 * se_bound:.1%}\n")
    print(f"{'delta':<8}{'sigma2_lambda':<16}{'sigma2_esc':<16}{'R':<12}")
    print("-" * 52)
    for delta in DELTAS:
        s_l, s_e, r = _measure(delta)
        print(f"{delta:<8.3f}{s_l:<16.6e}{s_e:<16.6e}{r:<12.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
