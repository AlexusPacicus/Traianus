"""Z — three-point zoom against a two-point benchmark.

Implements docs/methodology/instrument-audit/Z.md (instrument audit record, revision 10) against
docs/methodology/instrument-audit/contracts.md (§0 data layer, §4 Z) and
docs/methodology/instrument-audit/derivations.md (D5, D17, D19–D21, D23–D26).
Two arms zoom from the FIT barycentre to each EVAL note in axis coordinates: along the segment
(two-point) or along two straight legs through the middle m that a Newton search finds on the
equal-friction-time surface (three-point). Z1 compares the middle states' D25 scores by block
bootstrap; Z2 times keyframes against per-step frames.

Refuses to run unless the K6 module file matches its pin, the known world passes, and the three
input digests match; never runs on anything else.

Usage:
    python3 tools/experiments/zoom_three_point.py [--out PATH]
"""

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_var] = "1"

import argparse
import hashlib
import json
import math
import platform
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.experiments import k6_colour_predictability as k6

Array = NDArray[np.float64]

EMBEDDINGS = REPO_ROOT / ".data" / "spinoza_frozen" / "embeddings.npy"
LABELS = REPO_ROOT / ".data" / "spinoza_frozen" / "labels.json"
AXES = REPO_ROOT / "tests" / "fixtures" / "nsm_axes_8.json"
RESULT = REPO_ROOT / "data" / "refapp" / "Z_result.json"
EXPECTED_DIGESTS = {
    EMBEDDINGS: "eafb0e97172830f2404e96fa08d74bf6cccc0b6cbe84d47b790a476603e7d8d1",
    LABELS: "1d60699353d810f089730c6203ee28f9c416e3004b60781bc965cec284097f4f",
    AXES: "b14e5d6700d1a7478a357ca26f0f38f5240f97a42daad45722d21f1c3f964e35",
}
K6_FILE = Path(str(k6.__file__))
K6_SHA256 = "6289c596792154f6bb799606265c68719c6b8c7ae8b69084116dfb23c77876d2"

SEED = 20260924
KNOWN_SEED = 20260925
GRID = (1, 2, 5, 10, 20, 50)
MIN_BLOCKS = 20
N_BOOT = 10_000
INTERVAL_RANKS = (249, 9749)
MC_RANKS = (233, 265, 9733, 9765)
TIE_TOL = 1e-12
N_FRAMES = 60
N_WARMUP = 10
N_TIMER = 1000
READY_LIMIT_NS = 100_000_000
THREAD_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")
CONDITIONS = (
    "null_world",
    "tube_defined",
    "search_converged",
    "search_code",
    "lloyd_converged",
    "n_scored",
    "arms_share_start_end",
    "identity",
    "permutation",
    "quadrature",
    "search_reproduced",
)
ARMS = ("two_point", "three_point")
STATES = ("start", "middle", "end")
SECTIONS = ("targets", "z1", "controls", "z2", "counts", "reported")

EPS = float(np.finfo(np.float64).eps)
N_AXES = 8
N_OFFSET = N_AXES - 1
TUBE = 4.0 * math.sqrt(2.0)
N_NODES = 64
N_NODES_CONTROL = 128
C_ARM = 1e-4
MAX_ITERATIONS = 100
LLOYD_CAP = 1000
DEGENERACY = 8.0 * EPS


class SearchStop(Exception):
    """A search ended without a converged stop: the condition it fails and why."""

    def __init__(self, condition: str, reason: str) -> None:
        super().__init__(f"{condition}: {reason}")
        self.condition = condition
        self.reason = reason


# Friction and friction-time (D17, D20) ------------------------------------------------------------


@dataclass(frozen=True)
class Friction:
    """√f and ∇√f, row by row."""

    root: Callable[[Array], Array]
    root_grad: Callable[[Array], Array]


def variance_gradient(x: Array) -> Array:
    """∇Var = ¼(c − c̄·1) for 8 components, row by row (D17)."""
    grad: Array = (x - x.mean(axis=-1, keepdims=True)) / 4.0
    return grad


def _var_root(x: Array) -> Array:
    root: Array = np.sqrt(1.0 + x.var(axis=1))
    return root


def _var_root_grad(x: Array) -> Array:
    grad: Array = variance_gradient(x) / (2.0 * _var_root(x))[:, None]
    return grad


VAR_FRICTION = Friction(_var_root, _var_root_grad)


@dataclass(frozen=True)
class Rule:
    """Quadrature nodes s_i ∈ [0, 1] and weights w_i, and the friction they integrate."""

    nodes: Array
    weights: Array
    friction: Friction = VAR_FRICTION


def gauss_legendre(n: int, friction: Friction = VAR_FRICTION) -> Rule:
    """numpy.polynomial.legendre.leggauss(n) mapped to [0, 1]."""
    x, w = np.polynomial.legendre.leggauss(n)
    return Rule((x + 1.0) / 2.0, w / 2.0, friction)


RULE_64 = gauss_legendre(N_NODES)
RULE_128 = gauss_legendre(N_NODES_CONTROL)
Z0 = np.zeros(N_OFFSET)


def tau_seg(p: Array, q: Array, rule: Rule) -> float:
    """τ_seg(P, Q) = ‖Q − P‖ Σ_i w_i √f(P + s_i(Q − P)), D20's node-sum form."""
    diff = q - p
    points = p + rule.nodes[:, None] * diff
    return float(np.sqrt(diff @ diff)) * float(rule.weights @ rule.friction.root(points))


def tau_seg_grad(p: Array, q: Array, rule: Rule) -> tuple[Array, Array]:
    """(∇_Q τ_seg, ∇_P τ_seg) of the node-sum form (D20), P ≠ Q."""
    diff = q - p
    length = float(np.sqrt(diff @ diff))
    points = p + rule.nodes[:, None] * diff
    along = diff / length * float(rule.weights @ rule.friction.root(points))
    grads = rule.friction.root_grad(points)
    grad_q: Array = along + length * ((rule.weights * rule.nodes) @ grads)
    grad_p: Array = -along + length * ((rule.weights * (1.0 - rule.nodes)) @ grads)
    return grad_q, grad_p


def route_e(a: Array, m: Array, b: Array, rule: Rule) -> float:
    """E(m) = τ_seg(A, m) − τ_seg(m, B)."""
    return tau_seg(a, m, rule) - tau_seg(m, b, rule)


def gamma(n: int) -> float:
    """γ_N = N(ε/2) / (1 − N(ε/2))."""
    u = n * EPS / 2.0
    return u / (1.0 - u)


def h_max(d: float) -> float:
    """D23's tube radius (4√2 − d)·√(d / (8√2 − d))."""
    return (TUBE - d) * math.sqrt(d / (2.0 * TUBE - d))


# The line and its bisection, shared by both arms ---------------------------------------------------


@dataclass(frozen=True)
class Line:
    a: Array
    b: Array
    d: float
    u: Array
    zn: Array

    def point(self, z: Array, xi: float) -> Array:
        """ℓ_z(ξ) = A + ξ·u + Z_N z."""
        p: Array = self.a + xi * self.u + self.zn @ z
        return p


def make_line(a: Array, b: Array) -> Line:
    """u = (B − A)/d and Z_N, the last 7 columns of the complete QR factor of u."""
    diff = b - a
    d = float(np.sqrt(diff @ diff))
    u = diff / d
    q, _ = np.linalg.qr(u[:, None], mode="complete")
    return Line(a, b, d, u, q[:, 1:])


def bisect(e: Callable[[float], float], d: float) -> tuple[float, float, float]:
    """(ξ, lo, hi): E(lo) < 0 ≤ E(hi) kept from lo = 0, hi = d until hi − lo ≤ ε·d."""
    lo, hi = 0.0, d
    while hi - lo > EPS * d:
        xi = (lo + hi) / 2.0
        if e(xi) < 0.0:
            lo = xi
        else:
            hi = xi
    return (lo + hi) / 2.0, lo, hi


def mid(line: Line, z: Array, rule: Rule) -> tuple[float, Array] | None:
    """(ξ, mid(z)); None when E has no sign change on the line: E(ℓ_z(0)) < 0 ≤ E(ℓ_z(d)) fails."""

    def e(xi: float) -> float:
        return route_e(line.a, line.point(z, xi), line.b, rule)

    if not e(0.0) < 0.0 <= e(line.d):
        return None
    xi, _, _ = bisect(e, line.d)
    return xi, line.point(z, xi)


# The search for m (Z.md, Routes; D23, D24) ----------------------------------------------------------


@dataclass(frozen=True)
class Point:
    """A middle mid(z) with g = S, E, their gradients and the rounding bounds of Z.md."""

    z: Array
    xi: float
    m: Array
    s: float
    e: float
    grad_s: Array
    grad_e: Array
    slope: float
    mu_hat: float
    grad: Array
    nu: float
    nu_g: float
    rho_pt: float


def _route_c(a: Array, m: Array, b: Array, rule: Rule) -> float:
    """C: the largest absolute axis coordinate among the route's quadrature points."""
    nodes = rule.nodes[:, None]
    return max(float(np.abs(a + nodes * (m - a)).max()), float(np.abs(m + nodes * (b - m)).max()))


def evaluate(line: Line, z: Array, rule: Rule) -> Point | None:
    """mid(z), g, ∇g = Z_Nᵀ(∇S − μ̂∇E) (D24), ν, ν_g and ρ_pt; None without a sign change."""
    found = mid(line, z, rule)
    if found is None:
        return None
    xi, m = found
    tau_a, tau_b = tau_seg(line.a, m, rule), tau_seg(m, line.b, rule)
    grad_a, _ = tau_seg_grad(line.a, m, rule)
    _, grad_b = tau_seg_grad(m, line.b, rule)
    grad_s, grad_e = grad_a + grad_b, grad_a - grad_b
    slope = float(grad_e @ line.u)
    if slope <= 0.0:
        raise SearchStop("search_code", "slope_not_positive")
    along_s = float(grad_s @ line.u)
    mu_hat = along_s / slope
    s = tau_a + tau_b
    nu = gamma(256) * max(1.0, _route_c(line.a, m, line.b, rule) ** 2) * s
    reach = np.abs(line.a) + xi * np.abs(line.u) + np.abs(line.zn) @ np.abs(z)
    rho_pt = gamma(10) * float(np.linalg.norm(reach))
    nu_g = (
        (1.0 + abs(mu_hat)) * nu
        + abs(along_s) * line.d * EPS
        + (float(np.linalg.norm(grad_s)) + abs(mu_hat) * float(np.linalg.norm(grad_e))) * rho_pt
    )
    return Point(
        z=z, xi=xi, m=m, s=s, e=tau_a - tau_b, grad_s=grad_s, grad_e=grad_e, slope=slope,
        mu_hat=mu_hat, grad=line.zn.T @ (grad_s - mu_hat * grad_e), nu=nu, nu_g=nu_g,
        rho_pt=rho_pt,
    )


def _inside(z: Array, hmax: float) -> bool:
    return float(np.sqrt(z @ z)) <= hmax


def objective(line: Line, z: Array, hmax: float, rule: Rule) -> float | None:
    """g(z) = S(mid(z)) inside the tube (D23); None outside it or without a sign change."""
    if not _inside(z, hmax):
        return None
    found = mid(line, z, rule)
    if found is None:
        return None
    _, m = found
    return tau_seg(line.a, m, rule) + tau_seg(m, line.b, rule)


def hessian(line: Line, z: Array, hmax: float, rule: Rule) -> Array:
    """Central differences of ∇g with ζ = ε^{1/3}·d, representable steps, symmetrised."""
    zeta = EPS ** (1.0 / 3.0) * line.d
    columns = []
    for k in range(len(z)):
        plus, minus = z.copy(), z.copy()
        plus[k] = z[k] + zeta
        minus[k] = z[k] - zeta
        grads = []
        for shifted in (plus, minus):
            point = evaluate(line, shifted, rule) if _inside(shifted, hmax) else None
            if point is None:
                raise SearchStop("search_converged", "edge")
            grads.append(point.grad)
        columns.append((grads[0] - grads[1]) / ((plus[k] - z[k]) + (z[k] - minus[k])))
    h = np.column_stack(columns)
    sym: Array = (h + h.T) / 2.0
    return sym


def newton_step(grad: Array, h: Array) -> tuple[Array | None, float | None]:
    """(−H⁻¹∇g, ½∇gᵀH⁻¹∇g) when a Cholesky factorisation of H succeeds; (None, None) otherwise."""
    try:
        chol = np.linalg.cholesky(h)
    except np.linalg.LinAlgError:
        return None, None
    y = np.linalg.solve(chol, grad)
    step: Array = -np.linalg.solve(chol.T, y)
    return step, 0.5 * float(y @ y)


def direction(grad: Array, newton: Array | None) -> Array:
    """p = −H⁻¹∇g when H is positive definite, otherwise −∇g."""
    return newton if newton is not None else -grad


def line_search(line: Line, point: Point, p: Array, dg: float, hmax: float, rule: Rule) -> Array:
    """From α = 1, halving: the first trial inside the domain that passes Armijo; floor at α|Dg| ≤ 2ν_g."""
    alpha = 1.0
    while alpha * abs(dg) > 2.0 * point.nu_g:
        trial = point.z + alpha * p
        value = objective(line, trial, hmax, rule)
        if value is not None and value <= point.s + C_ARM * alpha * dg:
            return trial
        alpha /= 2.0
    raise SearchStop("search_converged", "floor")


@dataclass(frozen=True)
class Search:
    """Where a search stopped: "converged" at (2), or the reason and the condition it fails."""

    stop: str
    condition: str | None
    iterations: int
    fallback_steps: int
    first: Point | None
    point: Point | None
    decrement: float | None
    theta: float | None
    omega_min: float | None
    hmax: float

    @property
    def m(self) -> Array | None:
        return None if self.point is None else self.point.m


def search(line: Line, rule: Rule) -> Search:
    """Newton on g(z) = S(mid(z)) from z = 0 in D23's tube, in Z.md's order (1)–(5)."""
    hmax = h_max(line.d)
    z = np.zeros(N_OFFSET)
    first: Point | None = None
    point: Point | None = None
    steps = fallback = 0
    decrement: float | None = None
    theta: float | None = None
    omega: float | None = None
    try:
        for _ in range(MAX_ITERATIONS):
            decrement = theta = omega = None
            point = evaluate(line, z, rule)
            if point is None:
                raise SearchStop("search_code", "no_sign_change")
            if first is None:
                first = point
            h = hessian(line, z, hmax, rule)
            theta = 2.0 * point.nu_g / (1.0 - 2.0 * C_ARM)
            newton, decrement = newton_step(point.grad, h)
            omega = float(np.linalg.eigvalsh(h)[0])
            if decrement is not None and decrement <= theta:
                return Search(
                    "converged", None, steps, fallback, first, point, decrement, theta, omega, hmax
                )
            if newton is None:
                if not point.grad.any():
                    raise SearchStop("search_converged", "critical_point")
                fallback += 1
            p = direction(point.grad, newton)
            dg = float(point.grad @ p)
            if dg >= 0.0:
                raise SearchStop("search_code", "ascent_direction")
            z = line_search(line, point, p, dg, hmax, rule)
            steps += 1
        raise SearchStop("search_converged", "cap")
    except SearchStop as stop:
        return Search(
            stop.reason, stop.condition, steps, fallback, first, point, decrement, theta, omega, hmax
        )


def rho_2(point: Point, line: Line) -> float:
    """ρ₂ = (ν + ‖∇E‖·ρ_pt)/⟨∇E, u⟩ + d·ε + ρ_pt."""
    return (
        (point.nu + float(np.linalg.norm(point.grad_e)) * point.rho_pt) / point.slope
        + line.d * EPS
        + point.rho_pt
    )


def rho_3(found: Search, line: Line) -> float | None:
    """ρ₃ = ρ₂ + √(2Θ/ω_min(H))·(1 + ‖Z_Nᵀ∇E‖/⟨∇E, u⟩), only at a converged stop."""
    if found.stop != "converged" or found.point is None:
        return None
    point = found.point
    assert found.theta is not None and found.omega_min is not None
    lateral = float(np.linalg.norm(line.zn.T @ point.grad_e)) / point.slope
    return rho_2(point, line) + math.sqrt(2.0 * found.theta / found.omega_min) * (1.0 + lateral)


# Notes in view, Voronoi levels and frames (Z.md, States) --------------------------------------------


@dataclass(frozen=True)
class Corpus:
    """FIT and EVAL axis coordinates, their dominant attractors, and EVAL's 384-d ranks (D25)."""

    fit: Array
    ev: Array
    fit_cell: NDArray[np.intp]
    eval_cell: NDArray[np.intp]
    ranks: NDArray[np.intp]
    x_eval: Array
    rows: NDArray[np.intp]


def attractor(c: Array) -> NDArray[np.intp]:
    """argmax_k of the axis coordinates, ties to the lower axis index."""
    return np.argmax(c, axis=-1)


def make_corpus(v: Array, a_hat: Array) -> Corpus:
    """c(v) = (⟨v, â_k⟩)_k; FIT = even rows, EVAL = odd rows; Γ = X_E X_Eᵀ over EVAL."""
    c = v @ a_hat.T
    fit_rows, eval_rows = np.arange(0, len(v), 2), np.arange(1, len(v), 2)
    x_eval = v[eval_rows]
    return Corpus(
        fit=c[fit_rows], ev=c[eval_rows], fit_cell=attractor(c[fit_rows]),
        eval_cell=attractor(c[eval_rows]), ranks=hyp_ranks(x_eval @ x_eval.T), x_eval=x_eval,
        rows=eval_rows,
    )


@dataclass(frozen=True)
class State:
    """P, the FIT notes that fit its frame, the EVAL notes in view, and their display (None: degenerate)."""

    point: Array
    fit_view: NDArray[np.intp]
    view: NDArray[np.intp]
    display: Array | None
    eigen_gap: float | None

    @property
    def degenerate(self) -> bool:
        return self.display is None


def frame(p: Array, points: Array) -> tuple[Array | None, float | None]:
    """(e₁ e₂, (ω₂ − ω₃)/ω₁) of T = ½ Σ (c_i − P)(c_i − P)ᵀ; (None, None) when degenerate."""
    if len(points) < 2:
        return None, None
    x = points - p
    omega, vectors = np.linalg.eigh(0.5 * x.T @ x)
    omega, vectors = omega[::-1], vectors[:, ::-1]
    if omega[1] <= DEGENERACY * omega[0]:
        return None, None
    return vectors[:, :2], float((omega[1] - omega[2]) / omega[0])


def display(p: Array, basis: Array, points: Array) -> Array:
    """(⟨c_j − P, e₁⟩, ⟨c_j − P, e₂⟩) for each EVAL note j in view."""
    shown: Array = (points - p) @ basis
    return shown


def make_state(corpus: Corpus, p: Array, fit_view: NDArray[np.intp], view: NDArray[np.intp]) -> State:
    basis, gap = frame(p, corpus.fit[fit_view])
    shown = None if basis is None else display(p, basis, corpus.ev[view])
    return State(p, fit_view, view, shown, gap)


def level0(corpus: Corpus, p: Array) -> State:
    """Level 0: all notes."""
    return make_state(corpus, p, np.arange(len(corpus.fit)), np.arange(len(corpus.ev)))


def level1(corpus: Corpus, p: Array) -> State:
    """Level 1: the axis cell of P."""
    k = attractor(p)
    return make_state(
        corpus, p, np.flatnonzero(corpus.fit_cell == k), np.flatnonzero(corpus.eval_cell == k)
    )


@dataclass(frozen=True)
class Lloyd:
    labels: NDArray[np.intp]
    means: Array
    iterations: int
    converged: bool


def first_assignment(x: Array, p: Array) -> NDArray[np.intp]:
    """Each note to the site σ ∈ (+e₁, −e₁, …, +e₈, −e₈) of T_cell with the largest ⟨c_i − P, σ⟩."""
    d = x - p
    _, vectors = np.linalg.eigh(0.5 * d.T @ d)
    e = vectors[:, ::-1].T
    sites = np.empty((2 * len(e), e.shape[1]))
    sites[0::2], sites[1::2] = e, -e
    return np.argmax(d @ sites.T, axis=1)


def _cell_means(x: Array, labels: NDArray[np.intp]) -> tuple[NDArray[np.intp], Array]:
    """Empty cells dropped (cells renumbered in site order) and each cell's mean."""
    _, labels = np.unique(labels, return_inverse=True)
    means = np.array([x[labels == c].mean(axis=0) for c in range(int(labels.max()) + 1)])
    return labels, means


def _sq_dist(x: Array, means: Array) -> Array:
    dist: Array = ((x[:, None, :] - means[None, :, :]) ** 2).sum(axis=2)
    return dist


def lloyd(x: Array, p: Array) -> Lloyd:
    """Centroidal Voronoi partition of a cell's FIT notes around P: move to the nearest mean,
    keeping the current cell on a tie, until no note changes cell (cap LLOYD_CAP)."""
    labels = first_assignment(x, p)
    rows = np.arange(len(x))
    for iteration in range(1, LLOYD_CAP + 1):
        labels, means = _cell_means(x, labels)
        dist = _sq_dist(x, means)
        nearest = np.argmin(dist, axis=1)
        moved = np.where(dist[rows, labels] <= dist[rows, nearest], labels, nearest)
        if np.array_equal(moved, labels):
            return Lloyd(labels, means, iteration, True)
        labels = moved
    labels, means = _cell_means(x, labels)
    return Lloyd(labels, means, LLOYD_CAP, False)


def level2(corpus: Corpus, b: Array) -> tuple[State, Lloyd | None]:
    """Level 2: q's cell of the Lloyd partition of q's axis cell; degenerate without FIT notes."""
    k = attractor(b)
    fit_cell = np.flatnonzero(corpus.fit_cell == k)
    eval_cell = np.flatnonzero(corpus.eval_cell == k)
    if len(fit_cell) == 0:
        return State(b, fit_cell, eval_cell, None, None), None
    found = lloyd(corpus.fit[fit_cell], b)
    assigned = np.argmin(_sq_dist(corpus.ev[eval_cell], found.means), axis=1)
    own = int(np.argmin(_sq_dist(b[None, :], found.means)[0]))
    state = make_state(corpus, b, fit_cell[found.labels == own], eval_cell[assigned == own])
    return state, found


def argmax_margin(p: Array) -> float:
    """First minus second largest axis coordinate."""
    top = np.sort(p)[::-1]
    return float(top[0] - top[1])


# Z1's score (D25) ---------------------------------------------------------------------------------


def hyp_ranks(gamma: Array) -> NDArray[np.intp]:
    """rank[j, i]: 1-based rank of i in j's 384-d order (largest Γ first, ties to the lower index);
    j itself last."""
    n = len(gamma)
    key = -np.asarray(gamma, dtype=np.float64)
    np.fill_diagonal(key, np.inf)
    order = np.argsort(key, axis=1, kind="stable")
    ranks = np.empty((n, n), dtype=np.intp)
    ranks[np.arange(n)[:, None], order] = np.arange(1, n + 1)
    return ranks


def shown_order(shown: Array, pos: int) -> NDArray[np.intp]:
    """Positions of the other notes in view by display distance from `pos`, ties to the lower index.
    Squared Euclidean distance: the same order as the distance, without the square root's rounding."""
    diff = shown - shown[pos]
    order = np.argsort((diff * diff).sum(axis=1), kind="stable")
    kept: NDArray[np.intp] = order[order != pos]
    return kept


def display_orders(shown: Array, view: NDArray[np.intp]) -> list[NDArray[np.intp]]:
    """For each j in view, the EVAL indices of the other notes in view, nearest first."""
    return [view[shown_order(shown, pos)] for pos in range(len(view))]


def overlaps(rank_row: NDArray[np.intp], shown: NDArray[np.intp], n_u: int) -> NDArray[np.intp]:
    """O_j(K), K = 1…N_U − 2: notes at display rank t ≤ K′ whose 384-d rank is ≤ K."""
    key = np.maximum(rank_row[shown], np.arange(1, len(shown) + 1))
    counted: NDArray[np.intp] = np.cumsum(np.bincount(key, minlength=n_u + 1))[1 : n_u - 1]
    return counted


def r_values(o: NDArray[Any], n_m: int, n_u: int) -> Array:
    """R_j(K) = (O_j(K)/K − K′/N_c) / (1 − K′/N_c), K′ = min(K, N_M − 1), N_c = N_U − 1."""
    k = np.arange(1, n_u - 1)
    k_prime = np.minimum(k, n_m - 1)
    n_c = n_u - 1
    r: Array = (o / k - k_prime / n_c) / (1.0 - k_prime / n_c)
    return r


def score_orders(
    orders: list[NDArray[np.intp]], view: NDArray[np.intp], ranks: NDArray[np.intp], n_u: int
) -> Array:
    """R_j(K) for every j in view, from its display order (EVAL indices, nearest first)."""
    o = np.array([overlaps(ranks[j], order, n_u) for j, order in zip(view, orders, strict=True)])
    return r_values(o, len(view), n_u)


def auc(r: Array) -> float:
    """[Σ_K R_NX(K)/K] / [Σ_K 1/K], R_NX(K) the mean of R_j(K) over j."""
    weights = 1.0 / np.arange(1, r.shape[1] + 1)
    return float(r.mean(axis=0) @ weights / weights.sum())


def score_state(state: State, ranks: NDArray[np.intp]) -> tuple[float, Array] | None:
    """(AUC, R_NX) of a state; None when it is not scored (degenerate or N_M < 2)."""
    if state.display is None or len(state.view) < 2:
        return None
    r = score_orders(display_orders(state.display, state.view), state.view, ranks, len(ranks))
    r_nx: Array = r.mean(axis=0)
    return auc(r), r_nx


def state_record(state: State, value: float | None) -> dict[str, Any]:
    return {
        "n_m": len(state.view),
        "degenerate": state.degenerate,
        "eigen_gap": state.eigen_gap,
        "auc": value,
    }


def crossings(diff: Array) -> list[int]:
    """Scales K (1-based) where the sign of diff changes from its last nonzero sign; zeros skipped."""
    found, previous = [], 0.0
    for k, sign in enumerate(np.sign(diff).tolist(), start=1):
        if sign != 0.0:
            if previous != 0.0 and sign != previous:
                found.append(k)
            previous = sign
    return found


# Targets and arms (Z.md, Targets, Routes, States) ---------------------------------------------------


@dataclass(frozen=True)
class Arm:
    """One arm of one target: its middle point, uncertainty radius, states and their scores."""

    middle: Array
    rho: float | None
    states: dict[str, State]
    scores: dict[str, tuple[float, Array] | None]
    lloyd: Lloyd | None


@dataclass(frozen=True)
class Target:
    pos: int
    index: int
    d: float
    tau_2: float | None
    line: Line | None
    search: Search | None
    arms: dict[str, Arm]


def arm_states(corpus: Corpus, a: Array, middle: Array, b: Array) -> tuple[dict[str, State], Lloyd | None]:
    """start (P = A, all notes), middle (the axis cell of P), end (q's Lloyd cell around B)."""
    end, found = level2(corpus, b)
    return {"start": level0(corpus, a), "middle": level1(corpus, middle), "end": end}, found


def _cached_score(
    state: State, ranks: NDArray[np.intp], cache: dict[bytes, tuple[float, Array] | None]
) -> tuple[float, Array] | None:
    """score_state, computed once per identical view and display."""
    if state.display is None:
        return score_state(state, ranks)
    key = state.view.tobytes() + state.display.tobytes()
    if key not in cache:
        cache[key] = score_state(state, ranks)
    return cache[key]


def run_target(
    corpus: Corpus, a: Array, pos: int, rule: Rule, cache: dict[bytes, tuple[float, Array] | None]
) -> Target:
    """The two arms for the EVAL target at position pos; no route at d = 0, no search at d ≥ 4√2."""
    b = corpus.ev[pos]
    diff = b - a
    d = float(np.sqrt(diff @ diff))
    index = int(corpus.rows[pos])
    if d == 0.0 or d >= TUBE:
        return Target(pos, index, d, None, None, None, {})
    line = make_line(a, b)
    found = search(line, rule)
    benchmark = mid(line, Z0, rule)
    middles = {
        "two_point": (
            None if benchmark is None else benchmark[1],
            None if found.first is None else rho_2(found.first, line),
        ),
        "three_point": (found.m, rho_3(found, line)),
    }
    arms = {}
    for name, (middle, rho) in middles.items():
        if middle is None:
            continue
        states, lloyd_found = arm_states(corpus, a, middle, b)
        scores = {state: _cached_score(states[state], corpus.ranks, cache) for state in STATES}
        arms[name] = Arm(middle, rho, states, scores, lloyd_found)
    return Target(pos, index, d, tau_seg(a, b, rule), line, found, arms)


def run_targets(corpus: Corpus, a: Array, rule: Rule) -> list[Target]:
    cache: dict[bytes, tuple[float, Array] | None] = {}
    return [run_target(corpus, a, pos, rule, cache) for pos in range(len(corpus.ev))]


def _middle_auc(target: Target, arm: str) -> float | None:
    found = target.arms.get(arm)
    scored = None if found is None else found.scores["middle"]
    return None if scored is None else scored[0]


def d_q_of(targets: Sequence[Target]) -> tuple[list[Target], Array]:
    """The targets whose middle state is scored in both arms, and D_q = AUC₃ − AUC₂ over them."""
    scored = [
        t for t in targets
        if _middle_auc(t, "two_point") is not None and _middle_auc(t, "three_point") is not None
    ]
    d_q = np.array(
        [float(_middle_auc(t, "three_point")) - float(_middle_auc(t, "two_point")) for t in scored]  # type: ignore[arg-type]
    )
    return scored, d_q


def target_conditions(targets: Sequence[Target]) -> dict[str, bool]:
    searches = [t.search for t in targets if t.search is not None]
    lloyds = [arm.lloyd for t in targets for arm in t.arms.values() if arm.lloyd is not None]
    return {
        "tube_defined": all(t.d < TUBE for t in targets),
        "search_converged": all(s.condition != "search_converged" for s in searches),
        "search_code": all(s.condition != "search_code" for s in searches),
        "lloyd_converged": all(found.converged for found in lloyds),
    }


def _same_state(x: State, y: State) -> bool:
    if not np.array_equal(x.view, y.view):
        return False
    if x.display is None or y.display is None:
        return x.display is None and y.display is None
    return x.display.tobytes() == y.display.tobytes()


def arms_share_start_end(targets: Sequence[Target]) -> bool:
    """Start and end states equal across the arms: same notes in view, same bits, or both degenerate."""
    for t in targets:
        if len(t.arms) != len(ARMS):
            continue
        two, three = t.arms["two_point"].states, t.arms["three_point"].states
        if not (_same_state(two["start"], three["start"]) and _same_state(two["end"], three["end"])):
            return False
    return True


# Controls (Z.md, Controls) ------------------------------------------------------------------------


def identity_control(corpus: Corpus) -> dict[str, Any]:
    """The score on the 384-d vectors as the display, M = U: R_j(K) = 1 everywhere (D25 (a), D5),
    except swaps between notes whose similarities to j lie within TIE_TOL (counted as ties)."""
    x = corpus.x_eval
    n_u = len(x)
    gamma = x @ x.T
    view = np.arange(n_u)
    orders = display_orders(x, view)
    r = score_orders(orders, view, corpus.ranks, n_u)
    ties, passed = 0, True
    for j in np.flatnonzero((r != 1.0).any(axis=1)):
        hyp = np.argsort(corpus.ranks[j], kind="stable")[: n_u - 1]
        shown = orders[j][: n_u - 1]
        wrong = np.flatnonzero(shown != hyp)
        if np.all(np.abs(gamma[j, shown[wrong]] - gamma[j, hyp[wrong]]) <= TIE_TOL):
            ties += len(wrong)
        else:
            passed = False
    return {"passed": passed, "ties": ties}


def permutation_control(rng: np.random.Generator, ranks: NDArray[np.intp]) -> dict[str, Any]:
    """M = U, each note's display order a rng.permutation(N_c) of U \\ {j}: AUC within ±4/√(N_U(N_U − 2))."""
    n_u = len(ranks)
    view = np.arange(n_u)
    orders = [np.delete(view, j)[rng.permutation(n_u - 1)] for j in view]
    value = auc(score_orders(orders, view, ranks, n_u))
    band = 4.0 / math.sqrt(n_u * (n_u - 2))
    return {"auc": value, "band": band, "passed": abs(value) <= band}


def quadrature_control(
    corpus: Corpus,
    targets: Sequence[Target],
    state: Mapping[str, Any],
    levels: Mapping[str, str],
    rule: Rule,
) -> dict[str, Any]:
    """m kept; m₀ and the benchmark's middle state, |E(m)| and ∇g at m recomputed with `rule`;
    Z1 decided again per L on the same bootstrap draws (replayed from `state`)."""
    before = {t.pos for t in d_q_of(targets)[0]}
    after, d_q, abs_e, grad_norm = [], [], [], []
    changed = 0
    for t in targets:
        three = t.arms.get("three_point")
        if t.line is None or three is None:
            abs_e.append(None)
            grad_norm.append(None)
        else:
            line, m = t.line, three.middle
            abs_e.append(abs(route_e(line.a, m, line.b, rule)))
            grad_a, _ = tau_seg_grad(line.a, m, rule)
            _, grad_b = tau_seg_grad(m, line.b, rule)
            grad_s, grad_e = grad_a + grad_b, grad_a - grad_b
            mu = float(grad_s @ line.u) / float(grad_e @ line.u)
            grad_norm.append(float(np.linalg.norm(line.zn.T @ (grad_s - mu * grad_e))))
        if t.line is None:
            continue
        benchmark = mid(t.line, Z0, rule)
        new: tuple[int | None, float | None] = (None, None)
        if benchmark is not None:
            scored = score_state(level1(corpus, benchmark[1]), corpus.ranks)
            new = (int(attractor(benchmark[1])), None if scored is None else scored[0])
        two = t.arms.get("two_point")
        old = (None, None) if two is None else (int(attractor(two.middle)), _middle_auc(t, "two_point"))
        changed += new != old
        three_auc = _middle_auc(t, "three_point")
        if new[1] is not None and three_auc is not None:
            after.append(t.pos)
            d_q.append(three_auc - new[1])
    replay = np.random.Generator(np.random.PCG64())
    replay.bit_generator.state = dict(state)
    levels_128 = {length: z1_level(r) for length, r in z1_per_l(replay, np.array(d_q)).items()}
    keys = sorted(set(levels) | set(levels_128), key=int)
    return {
        "passed": set(after) == before and dict(levels) == levels_128,
        "decisions": {key: {"64": levels.get(key), "128": levels_128.get(key)} for key in keys},
        "changed": changed,
        "abs_e_128": abs_e,
        "grad_norm_128": grad_norm,
    }


# Block bootstrap and decisions (Z.md, Dependence between targets, Rule (Z1), Z2) --------------------


def n_blocks(n: int, length: int) -> int:
    return -(-n // length)


def lengths_used(n: int) -> list[int]:
    """The block lengths of the grid that leave at least MIN_BLOCKS blocks."""
    return [length for length in GRID if n_blocks(n, length) >= MIN_BLOCKS]


def bootstrap(
    rng: np.random.Generator, values: Array, length: int, statistic: Callable[[Array], Any]
) -> Array:
    """N_BOOT resamples of ⌈n/L⌉ contiguous blocks in index order (the last may be shorter), drawn
    with rng.integers(0, n_blocks, n_blocks); the statistic over the drawn blocks' values with multiplicity."""
    n = len(values)
    n_blk = n_blocks(n, length)
    sizes = np.diff(np.append(np.arange(0, n, length), n))
    out = np.empty(N_BOOT)
    for b in range(N_BOOT):
        counts = np.bincount(rng.integers(0, n_blk, n_blk), minlength=n_blk)
        out[b] = statistic(np.repeat(values, np.repeat(counts, sizes)))
    return out


def interval_record(draws: Array) -> dict[str, Any]:
    ordered = np.sort(draws)
    lo, hi = INTERVAL_RANKS
    return {
        "interval": [float(ordered[lo]), float(ordered[hi])],
        "ranks": {str(rank): float(ordered[rank]) for rank in MC_RANKS},
    }


def z1_per_l(rng: np.random.Generator, d_q: Array) -> dict[str, dict[str, Any]]:
    n = len(d_q)
    per_l = {}
    for length in lengths_used(n):
        record = interval_record(bootstrap(rng, d_q, length, np.mean))
        lo, hi = record["interval"]
        per_l[str(length)] = {
            "n_blocks": n_blocks(n, length),
            "d_bar": float(np.mean(d_q)),
            "interval": record["interval"],
            "margins": {"lower": lo, "upper": hi},
            "ranks": record["ranks"],
        }
    return per_l


def z1_level(record: Mapping[str, Any]) -> str:
    lo, hi = record["interval"]
    if hi < 0.0:
        return "refuted"
    if lo > 0.0:
        return "keeps_more"
    return "inconclusive"


def z1_decision(per_l: Mapping[str, Mapping[str, Any]]) -> str | None:
    """refuted iff the upper bound < 0 at every L used; keeps_more iff the lower bound > 0 at every L."""
    if not per_l:
        return None
    levels = {z1_level(record) for record in per_l.values()}
    return levels.pop() if len(levels) == 1 and levels != {"inconclusive"} else "inconclusive"


def _p95(values: Array) -> float:
    return float(np.percentile(values, 95))


def z2_statistics(rng: np.random.Generator, delta: Array, ready: Array) -> dict[str, dict[str, Any]]:
    """Median of Δ_q at every L used, then the 95th percentile of ready at every L used."""
    n = len(delta)
    lengths = lengths_used(n)
    medians = {length: interval_record(bootstrap(rng, delta, length, np.median)) for length in lengths}
    p95 = {length: interval_record(bootstrap(rng, ready, length, _p95)) for length in lengths}
    per_l = {}
    for length in lengths:
        (d_lo, d_hi), (r_lo, r_hi) = medians[length]["interval"], p95[length]["interval"]
        per_l[str(length)] = {
            "n_blocks": n_blocks(n, length),
            "median_delta": {"interval": [d_lo, d_hi], "margins": {"lower": d_lo, "upper": d_hi}},
            "ready_p95": {
                "interval": [r_lo, r_hi],
                "margins": {"lower": r_lo - READY_LIMIT_NS, "upper": r_hi - READY_LIMIT_NS},
            },
        }
    return per_l


def z2_decision(per_l: Mapping[str, Mapping[str, Any]]) -> str | None:
    """refuted iff the median-Δ lower bound ≥ 0 at every L, or the ready-p95 lower bound > 100 ms at
    every L; else confirmed iff the median-Δ upper bound < 0 and the ready-p95 upper bound ≤ 100 ms at
    every L; else inconclusive."""
    if not per_l:
        return None
    delta = [record["median_delta"]["interval"] for record in per_l.values()]
    ready = [record["ready_p95"]["interval"] for record in per_l.values()]
    if all(lo >= 0.0 for lo, _ in delta) or all(lo > READY_LIMIT_NS for lo, _ in ready):
        return "refuted"
    if all(hi < 0.0 for _, hi in delta) and all(hi <= READY_LIMIT_NS for _, hi in ready):
        return "confirmed"
    return "inconclusive"


# Z2: timing (Z.md, Z2) --------------------------------------------------------------------------


@dataclass(frozen=True)
class Z2Pass:
    overhead: float
    keyframes: Array
    per_step: Array
    ready: Array
    reproduced: bool

    @property
    def delta(self) -> Array:
        """Δ_q = time_keyframes(q) − time_per-step(q), paired per target."""
        diff: Array = self.keyframes - self.per_step
        return diff


def frame_times() -> Array:
    times: Array = np.arange(N_FRAMES) / (N_FRAMES - 1)
    return times


def route_point(a: Array, m: Array, b: Array, t: float) -> Array:
    """The three-point route at time t: A → m on [0, ½], m → B on [½, 1], linear in t."""
    point: Array = a + 2.0 * t * (m - a) if t <= 0.5 else m + (2.0 * t - 1.0) * (b - m)
    return point


def _positions(corpus: Corpus, state: State) -> tuple[Array, NDArray[np.bool_]]:
    """Display positions of every EVAL note (zero where not shown) and which are shown."""
    positions = np.zeros((len(corpus.ev), 2))
    shown = np.zeros(len(corpus.ev), dtype=bool)
    if state.display is not None:
        positions[state.view] = state.display
        shown[state.view] = True
    return positions, shown


def interpolate(
    prev: tuple[Array, NDArray[np.bool_]], nxt: tuple[Array, NDArray[np.bool_]], w: float
) -> tuple[NDArray[np.intp], Array]:
    """(1 − w)·pos_prev + w·pos_next for notes in both displays; a note in one keeps its position there."""
    (p_prev, m_prev), (p_next, m_next) = prev, nxt
    notes = np.flatnonzero(m_prev | m_next)
    both = (m_prev & m_next)[notes][:, None]
    only_prev = m_prev[notes][:, None]
    blended = (1.0 - w) * p_prev[notes] + w * p_next[notes]
    return notes, np.where(both, blended, np.where(only_prev, p_prev[notes], p_next[notes]))


def keyframes_arm(
    corpus: Corpus, a: Array, m: Array, b: Array, clock: Callable[[], int]
) -> tuple[list[tuple[NDArray[np.intp], Array]], int]:
    """The three states, a timestamp once the third exists, then N_f interpolated frames."""
    states = (level0(corpus, a), level1(corpus, m), level2(corpus, b)[0])
    stamp = clock()
    shown = [_positions(corpus, state) for state in states]
    frames = [
        interpolate(shown[0], shown[1], 2.0 * t) if t <= 0.5 else interpolate(shown[1], shown[2], 2.0 * t - 1.0)
        for t in frame_times().tolist()
    ]
    return frames, stamp


def per_step_arm(corpus: Corpus, a: Array, m: Array, b: Array) -> list[State]:
    """The level-2 partition, then every frame recomputed at P(t): level 0 for t < ½, level 1 for
    ½ ≤ t < 1, level 2 at t = 1."""
    end, _ = level2(corpus, b)
    frames = []
    for t in frame_times().tolist():
        p = route_point(a, m, b, t)
        if t < 0.5:
            frames.append(level0(corpus, p))
        elif t < 1.0:
            frames.append(level1(corpus, p))
        else:
            frames.append(make_state(corpus, p, end.fit_view, end.view))
    return frames


def timer_overhead(clock: Callable[[], int]) -> float:
    """The median of N_TIMER empty timed calls."""
    samples = []
    for _ in range(N_TIMER):
        start = clock()
        samples.append(clock() - start)
    return float(np.median(samples))


def z2_pass(
    corpus: Corpus, a: Array, targets: Sequence[Target], rule: Rule, clock: Callable[[], int]
) -> Z2Pass:
    """Warm-up on the first N_WARMUP targets with a route, then per target: the line built again and
    the search (timed, shared), and the two arms timed once each, keyframes first at even EVAL
    positions; the keyframes total loses the overhead once more, for its timestamp read."""
    overhead = timer_overhead(clock)
    routed = [t for t in targets if t.line is not None and t.search is not None and t.search.m is not None]
    for t in routed[:N_WARMUP]:
        assert t.search is not None and t.search.m is not None
        b = corpus.ev[t.pos]
        again = search(make_line(a, b), rule)
        m = again.m if again.m is not None else t.search.m
        keyframes_arm(corpus, a, m, b, clock)
        per_step_arm(corpus, a, m, b)
    times: dict[str, list[float]] = {"keyframes": [], "per_step": []}
    ready, reproduced = [], True
    for t in routed:
        assert t.search is not None and t.search.m is not None
        b = corpus.ev[t.pos]
        start = clock()
        again = search(make_line(a, b), rule)
        search_ns = clock() - start - overhead
        reproduced = reproduced and again.m is not None and again.m.tobytes() == t.search.m.tobytes()
        m = again.m if again.m is not None else t.search.m
        order = ("keyframes", "per_step") if t.pos % 2 == 0 else ("per_step", "keyframes")
        to_stamp = 0.0
        for arm in order:
            start = clock()
            if arm == "keyframes":
                _, stamp = keyframes_arm(corpus, a, m, b, clock)
                end = clock()
                to_stamp = stamp - start - overhead
                times[arm].append(end - start - 2.0 * overhead)
            else:
                per_step_arm(corpus, a, m, b)
                times[arm].append(clock() - start - overhead)
        ready.append(search_ns + to_stamp)
    return Z2Pass(
        overhead,
        np.array(times["keyframes"], dtype=float),
        np.array(times["per_step"], dtype=float),
        np.array(ready, dtype=float),
        reproduced,
    )


def z2_section(rng: np.random.Generator, passed: Z2Pass) -> dict[str, Any]:
    n = len(passed.delta)
    per_l = z2_statistics(rng, passed.delta, passed.ready)
    return {
        "timer_overhead_ns": passed.overhead,
        "n": n,
        "median_delta_ns": float(np.median(passed.delta)) if n else None,
        "ready_p95_ns": _p95(passed.ready) if n else None,
        "per_l": per_l,
        "decision": z2_decision(per_l),
    }


# Records ----------------------------------------------------------------------------------------


def search_record(found: Search) -> dict[str, Any]:
    point = found.point
    return {
        "stop": found.stop,
        "iterations": found.iterations,
        "decrement": found.decrement,
        "theta": found.theta,
        "nu_g": None if point is None else point.nu_g,
        "mu_hat": None if point is None else point.mu_hat,
        "h_over_hmax": None if point is None else float(np.linalg.norm(point.z)) / found.hmax,
        "slope": None if point is None else point.slope,
        "abs_e": None if point is None else abs(point.e),
        "xi": None if point is None else point.xi,
        "rho_pt": None if point is None else point.rho_pt,
        "fallback_steps": found.fallback_steps,
    }


def arm_record(arm: Arm) -> dict[str, Any]:
    per_state = {
        state: state_record(arm.states[state], None if arm.scores[state] is None else arm.scores[state][0])  # type: ignore[index]
        for state in STATES
    }
    record: dict[str, Any] = {
        "k_star": int(attractor(arm.middle)),
        "argmax_margin": argmax_margin(arm.middle),
        "rho": arm.rho,
    }
    for key in ("n_m", "degenerate", "eigen_gap", "auc"):
        record[key] = {state: per_state[state][key] for state in STATES}
    return record


def target_record(t: Target) -> dict[str, Any]:
    record: dict[str, Any] = {"index": t.index, "d": t.d, "excluded": t.d == 0.0}
    none = dict.fromkeys(("search", "arms", "tau_2", "tau_3", "m_minus_m0_norm", "crossings", "lloyd"))
    if t.search is None:
        return {**record, **none}
    two, three = t.arms.get("two_point"), t.arms.get("three_point")
    both = two is not None and three is not None
    scored = both and two.scores["middle"] is not None and three.scores["middle"] is not None  # type: ignore[union-attr]
    lloyd_found = None if two is None else two.lloyd
    return {
        **record,
        "search": search_record(t.search),
        "arms": {name: None if name not in t.arms else arm_record(t.arms[name]) for name in ARMS},
        "tau_2": t.tau_2,
        "tau_3": None if t.search.point is None else t.search.point.s,
        "m_minus_m0_norm": float(np.linalg.norm(three.middle - two.middle)) if both else None,  # type: ignore[union-attr]
        "crossings": crossings(three.scores["middle"][1] - two.scores["middle"][1]) if scored else None,  # type: ignore[index, union-attr]
        "lloyd": None if lloyd_found is None else {"iterations": lloyd_found.iterations, "cells": len(lloyd_found.means)},
    }


def counts(targets: Sequence[Target]) -> dict[str, Any]:
    searches = [t.search for t in targets if t.search is not None]
    failed: dict[str, int] = {}
    for found in searches:
        if found.stop != "converged":
            failed[found.stop] = failed.get(found.stop, 0) + 1
    arms = [(name, t.arms[name]) for t in targets for name in ARMS if name in t.arms]

    def per_arm_state(test: Callable[[Arm, str], bool]) -> dict[str, dict[str, int]]:
        return {
            name: {state: sum(test(arm, state) for arm_name, arm in arms if arm_name == name) for state in STATES}
            for name in ARMS
        }

    return {
        "excluded": sum(t.d == 0.0 for t in targets),
        "degenerate": per_arm_state(lambda arm, state: arm.states[state].degenerate),
        "not_scored": per_arm_state(lambda arm, state: arm.scores[state] is None),
        "near_zero_eigen_gap": per_arm_state(
            lambda arm, state: arm.states[state].eigen_gap is not None
            and arm.states[state].eigen_gap < DEGENERACY  # type: ignore[operator]
        ),
        "failed_searches": failed,
        "fallback_steps": sum(found.fallback_steps for found in searches),
        "mu_hat_ge_1": sum(found.point is not None and abs(found.point.mu_hat) >= 1.0 for found in searches),
        "margin_below_2rho": {
            name: sum(
                arm.rho is not None and argmax_margin(arm.middle) < 2.0 * arm.rho
                for arm_name, arm in arms
                if arm_name == name
            )
            for name in ARMS
        },
    }


def reported(corpus: Corpus, a: Array, targets: Sequence[Target], axis_norms: Array) -> dict[str, Any]:
    score_mean: dict[str, dict[str, float | None]] = {}
    for name in ARMS:
        score_mean[name] = {}
        for state in STATES:
            values = [
                t.arms[name].scores[state][0]  # type: ignore[index]
                for t in targets
                if name in t.arms and t.arms[name].scores[state] is not None
            ]
            score_mean[name][state] = float(np.mean(values)) if values else None
    records = [target_record(t) for t in targets]
    found = [r["crossings"] for r in records if r["crossings"] is not None]
    basis, _ = frame(a, corpus.fit)
    return {
        "score_mean": score_mean,
        "middle_cells_differ": [
            t.index for t in targets
            if len(t.arms) == len(ARMS)
            and attractor(t.arms["two_point"].middle) != attractor(t.arms["three_point"].middle)
        ],
        "crossings": {
            "targets_with_crossing": sum(bool(c) for c in found),
            "crossings_total": sum(len(c) for c in found),
        },
        "tau_ratio": [
            None if r["tau_3"] is None or r["tau_2"] is None else r["tau_3"] / r["tau_2"] for r in records
        ],
        "start_leading_direction": None if basis is None else basis[:, 0].tolist(),
        "axis_norms": axis_norms.tolist(),
        "smallest_d": min((t.d for t in targets if t.d > 0.0), default=None),
    }


# The measurement --------------------------------------------------------------------------------


@dataclass(frozen=True)
class Measurement:
    sections: dict[str, Any]
    conditions: dict[str, bool]
    targets: list[Target]
    d_q: Array
    levels: dict[str, str]


def measure(
    v: Array, a: Array, rng: np.random.Generator, clock: Callable[[], int] | None = None
) -> Measurement:
    """Z1, its controls and, given a clock, Z2, on rows v (FIT even, EVAL odd) and raw axes a."""
    axis_norms = np.sqrt((a * a).sum(axis=1))
    a_hat = np.array([a_k / np.sqrt(a_k @ a_k) for a_k in a])
    corpus = make_corpus(v, a_hat)
    p0 = corpus.fit.mean(axis=0)
    targets = run_targets(corpus, p0, RULE_64)
    scored, d_q = d_q_of(targets)
    identity = identity_control(corpus)
    permutation = permutation_control(rng, corpus.ranks)
    z1_state = rng.bit_generator.state
    per_l = z1_per_l(rng, d_q)
    levels = {length: z1_level(record) for length, record in per_l.items()}
    quadrature = quadrature_control(corpus, targets, z1_state, levels, RULE_128)
    shared = arms_share_start_end(targets)
    conditions = target_conditions(targets)
    n_scored = len(d_q) >= MIN_BLOCKS
    z2 = None
    if clock is not None:
        passed = z2_pass(corpus, p0, targets, RULE_64, clock)
        z2 = z2_section(rng, passed)
        n_scored = n_scored and len(passed.delta) >= MIN_BLOCKS
    conditions.update(
        n_scored=n_scored,
        arms_share_start_end=shared,
        identity=identity["passed"],
        permutation=permutation["passed"],
        quadrature=quadrature["passed"],
    )
    if clock is not None:
        conditions["search_reproduced"] = passed.reproduced
    agree = [
        float(dq) for t, dq in zip(scored, d_q, strict=True)
        if attractor(t.arms["two_point"].middle) == attractor(t.arms["three_point"].middle)
    ]
    sections = {
        "targets": [target_record(t) for t in targets],
        "z1": {
            "n": len(d_q),
            "per_l": per_l,
            "d_bar_cells_agree": float(np.mean(agree)) if agree else None,
            "decision": z1_decision(per_l),
        },
        "controls": {
            "identity": identity,
            "permutation": permutation,
            "arms_share_start_end": {"passed": shared},
            "quadrature": quadrature,
        },
        "z2": z2,
        "counts": counts(targets),
        "reported": reported(corpus, p0, targets, axis_norms),
    }
    ordered = {c: conditions[c] for c in CONDITIONS if c in conditions}
    return Measurement(sections, ordered, targets, d_q, levels)


# The known world (Z.md, Controls, null_world; D26) ----------------------------------------------


def known_world() -> tuple[Array, Array]:
    """336 notes in ℝ³⁸⁴ built by formula, axes â_k = o_k: FIT even indices, EVAL odd."""
    pairs = [(k1, k2) for k1 in range(N_AXES) for k2 in range(k1 + 1, N_AXES)]
    golden = (math.sqrt(5.0) - 1.0) / 2.0
    v = np.zeros((4 * 3 * len(pairs), 384))
    for iota in range(1, 3 * len(pairs) + 1):
        k1, k2 = pairs[(iota - 1) // 3]
        x = iota ** 2 * golden
        beta = 0.1 + 0.2 * (x - math.floor(x))
        for r, (first, second) in enumerate(((k1, k2), (k1, k2), (k2, k1), (k2, k1))):
            i = 4 * (iota - 1) + r
            c = np.full(N_AXES, 0.1)
            c[first] += beta
            c[second] -= beta
            v[i, :N_AXES] = c
            v[i, N_AXES + i] = math.sqrt(1.0 - float(c @ c))
    return v, np.eye(N_AXES, 384)


def smallest_relative_gap(states: Sequence[State]) -> float | None:
    """The smallest relative gap between two consecutive displayed distances from a note."""
    gaps = []
    for state in states:
        if state.display is None:
            continue
        for pos in range(len(state.view)):
            diff = np.delete(state.display - state.display[pos], pos, axis=0)
            dist = np.sort(np.sqrt((diff * diff).sum(axis=1)))
            if len(dist) >= 2:
                upper = dist[1:]
                rel = np.divide(upper - dist[:-1], upper, out=np.zeros_like(upper), where=upper > 0.0)
                gaps.append(float(rel.min()))
    return min(gaps, default=None)


def null_world() -> dict[str, Any]:
    """The whole Z1 pipeline on the known world, where m₀ is every target's answer (D26)."""
    v, a = known_world()
    measured = measure(v, a, np.random.default_rng(KNOWN_SEED))
    searches = [t.search for t in measured.targets]
    without_step = all(
        s is not None and s.stop == "converged" and s.iterations == 0
        and s.point is not None and not s.point.z.any()
        for s in searches
    )
    middles = all(
        _middle_auc(t, arm) is not None for t in measured.targets for arm in ARMS
    )
    all_zero = len(measured.d_q) > 0 and bool(np.all(measured.d_q == 0.0))
    inconclusive = bool(measured.levels) and set(measured.levels.values()) == {"inconclusive"}
    return {
        "passed": without_step and middles and all_zero and inconclusive and all(measured.conditions.values()),
        "all_d_q_zero": all_zero,
        "searches_without_step": without_step,
        "middles_scored": middles,
        "decisions": measured.levels,
        "conditions": measured.conditions,
        "smallest_relative_display_gap": smallest_relative_gap(
            [t.arms[arm].states["middle"] for t in measured.targets for arm in ARMS if arm in t.arms]
        ),
    }


# Run --------------------------------------------------------------------------------------------


def environment() -> dict[str, Any]:
    return {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "numpy_config": np.show_config(mode="dicts"),
        "threads": {var: os.environ.get(var) for var in THREAD_VARS},
    }


def _plain(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_plain(v) for v in obj]
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    return obj


def _write(result: Mapping[str, Any], out_path: Path) -> dict[str, Any]:
    text = json.dumps(_plain(result), sort_keys=True, indent=2, allow_nan=False) + "\n"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8", newline="\n")
    loaded: dict[str, Any] = json.loads(text)
    return loaded


def check_pin(k6_file: Path) -> None:
    """The K6 module file's sha256 by hashlib here, not through the module's own check_digests, which
    an edit could disable; a mismatch refuses the run."""
    actual = hashlib.sha256(k6_file.read_bytes()).hexdigest()
    if actual != K6_SHA256:
        raise k6.IntegrityError(f"sha256 mismatch for {k6_file}: expected {K6_SHA256}, got {actual}")


def run(
    k6_file: Path,
    embeddings: Path,
    labels: Path,
    axes: Path,
    expected: Mapping[Path, str],
    out_path: Path,
    clock: Callable[[], int] = time.perf_counter_ns,
) -> dict[str, Any]:
    """Pin check, then the known world, then (only if it passed) the artefacts and the real run."""
    check_pin(Path(k6_file))
    artefacts = (Path(embeddings), Path(labels), Path(axes))
    result: dict[str, Any] = {
        "digests": {Path(k6_file).name: K6_SHA256, **{p.name: None for p in artefacts}},
        "environment": environment(),
    }
    world = null_world()
    if not world["passed"]:
        result.update(
            valid=False,
            first_failed_condition="null_world",
            failed_conditions=["null_world"],
            conditions_checked=["null_world"],
            null_world=world,
            **dict.fromkeys(SECTIONS),
        )
        return _write(result, out_path)
    raw = k6.check_digests(expected)
    v32, label_list, axis_ids, a = k6.load_inputs(*(raw[p] for p in artefacts))
    k6.validate_inputs(v32, label_list, axis_ids, a)
    v64 = v32.astype("<f8")
    v = np.array([row / np.sqrt(row @ row) for row in v64])
    measured = measure(v, a, np.random.default_rng(SEED), clock=clock)
    checks = {"null_world": True, **measured.conditions}
    failed = [c for c, ok in checks.items() if not ok]
    sections = measured.sections
    if failed:
        for key in ("z1", "z2"):
            if sections[key] is not None:
                sections[key]["decision"] = None
    result["digests"].update({p.name: expected[p] for p in artefacts})
    result.update(
        valid=not failed,
        first_failed_condition=failed[0] if failed else None,
        failed_conditions=failed,
        conditions_checked=list(checks),
        null_world=world,
        **sections,
    )
    return _write(result, out_path)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Z three-point zoom against a two-point benchmark.")
    parser.add_argument("--out", type=Path, default=RESULT, help=f"result path (default: {RESULT})")
    out_path: Path = parser.parse_args(argv).out
    result = run(K6_FILE, EMBEDDINGS, LABELS, AXES, EXPECTED_DIGESTS, out_path)
    decisions = [None if result[key] is None else result[key]["decision"] for key in ("z1", "z2")]
    print(f"Z: valid={result['valid']} z1={decisions[0]} z2={decisions[1]} -> {out_path}")
    if not result["valid"]:
        raise SystemExit(f"Z invalid, no decision: {result['failed_conditions']}")


if __name__ == "__main__":
    main()
