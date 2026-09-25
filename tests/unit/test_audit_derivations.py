"""Code verification of docs/methodology/instrument-audit/derivations.md (D1-D12, D17, D19-D21,
D23-D26).

Each derivation is checked by computation, not by reading: algebraic identities numerically in
float64 at d = 384 (d = 8 for Z's axis coordinates) on seeded random inputs that satisfy the stated
conditions, through the real PolarProjector where the operator is involved and through
tools/experiments/zoom_three_point.py where Z's friction-time, bisection and score are;
combinatorial ones exactly with Fraction. Every derivation also has a negative case: violating its
condition must break the equality, so no test is vacuous.
"""

import itertools
import math
from fractions import Fraction

import numpy as np
import pytest

from tools.experiments import zoom_three_point as zoom
from traianus.geometry.polar_projector import PolarProjector

D = 384
TRIALS = 200
ATOL = 1e-9
RTOL = 1e-12


def _unit(x):
    return x / np.linalg.norm(x)


def _perp(x, c_hat):
    return x - np.dot(x, c_hat) * c_hat


def _close(a, b):
    return bool(np.isclose(a, b, rtol=RTOL, atol=ATOL))


def _frame(rng, *, collinear=False, pole_scale=1.0):
    c1 = rng.standard_normal(D)
    if collinear:
        ca, cb = 2.0 * c1, 3.0 * c1
    else:
        ca = pole_scale * rng.standard_normal(D)
        cb = pole_scale * rng.standard_normal(D)
    return PolarProjector().prepare(c1, ca, cb)


def _raw_lambda(v, frame):
    return float(np.dot(v, frame.v_dipole) / frame.v_dipole_norm_sq)


def _r2(y, X):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    return 1.0 - float(resid @ resid) / float(((y - y.mean()) ** 2).sum())


def _z(x):
    return (x - x.mean()) / x.std()


@pytest.fixture
def rng():
    return np.random.default_rng(20260918)


# D1 ---------------------------------------------------------------------------------------------


def test_d1_residual_is_the_projection_of_v(rng):
    for _ in range(TRIALS):
        c1 = rng.uniform(0.1, 10.0) * rng.standard_normal(D)
        c_hat = _unit(c1)
        v = rng.standard_normal(D)
        assert np.allclose(_perp(v - c1, c_hat), _perp(v, c_hat), rtol=RTOL, atol=ATOL)


def test_d1_breaks_with_an_unnormalised_anchor(rng):
    c1 = 3.0 * _unit(rng.standard_normal(D))
    v = rng.standard_normal(D)
    assert not np.allclose(_perp(v - c1, c1), _perp(v, c1), rtol=RTOL, atol=ATOL)


# D2 ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("collinear", [False, True])
def test_d2_residual_and_v_agree_on_the_dipole(rng, collinear):
    for _ in range(TRIALS):
        frame = _frame(rng, collinear=collinear)
        v = rng.standard_normal(D)
        r = _perp(v - frame.c_1, frame.c1_hat)
        assert _close(np.dot(r, frame.v_dipole), np.dot(v, frame.v_dipole))
        _, lam, _ = PolarProjector().evaluate(v, frame, 0)
        assert _close(lam, float(np.clip(_raw_lambda(v, frame), -1.0, 1.0)))


def test_d2_fallback_dipole_is_orthogonal_and_of_norm_two_delta(rng):
    for _ in range(TRIALS):
        frame = _frame(rng, collinear=True)
        assert abs(np.dot(frame.v_dipole, frame.c1_hat)) < ATOL
        assert _close(np.linalg.norm(frame.v_dipole), 2 * PolarProjector().delta)


def test_d2_breaks_for_a_direction_not_orthogonal_to_the_anchor(rng):
    frame = _frame(rng)
    w = frame.v_dipole + frame.c1_hat
    v = rng.standard_normal(D)
    r = _perp(v - frame.c_1, frame.c1_hat)
    assert not _close(np.dot(r, w), np.dot(v, w))


# D3 ---------------------------------------------------------------------------------------------


def test_d3_residual_norm_on_the_unit_sphere(rng):
    for _ in range(TRIALS):
        frame = _frame(rng)
        v = _unit(rng.standard_normal(D))
        r = _perp(v - frame.c_1, frame.c1_hat)
        assert _close(r @ r, 1.0 - np.dot(v, frame.c1_hat) ** 2)


def test_d3_breaks_off_the_unit_sphere(rng):
    frame = _frame(rng)
    v = 2.0 * _unit(rng.standard_normal(D))
    r = _perp(v - frame.c_1, frame.c1_hat)
    assert not _close(r @ r, 1.0 - np.dot(v, frame.c1_hat) ** 2)


# D4, D11, D12 -----------------------------------------------------------------------------------


def _clipped_case(rng):
    """A frame with a small dipole and a v aligned with it, so the raw λ exceeds 1."""
    frame = _frame(rng, pole_scale=0.01)
    v = _unit(_unit(frame.v_dipole) + 0.1 * frame.c1_hat)
    return frame, v


def test_d4_escape_distance_when_lambda_is_unclipped(rng):
    checked = 0
    for _ in range(TRIALS):
        frame = _frame(rng)
        v = _unit(rng.standard_normal(D))
        raw = _raw_lambda(v, frame)
        _, lam, d_esc = PolarProjector().evaluate(v, frame, 0)
        y = np.dot(v, frame.c1_hat)
        r_sq = 1.0 - y**2
        if abs(raw) > 1.0 or d_esc / np.sqrt(r_sq) < 1e-6:
            continue
        assert np.isclose(d_esc**2, r_sq - frame.v_dipole_norm_sq * lam**2, atol=ATOL * r_sq)
        checked += 1
    assert checked == TRIALS


def test_d4_breaks_when_lambda_is_clipped(rng):
    frame, v = _clipped_case(rng)
    assert abs(_raw_lambda(v, frame)) > 1.0
    _, lam, d_esc = PolarProjector().evaluate(v, frame, 0)
    y = np.dot(v, frame.c1_hat)
    assert not _close(d_esc**2, 1.0 - y**2 - frame.v_dipole_norm_sq * lam**2)


def test_d11_escape_distance_when_lambda_is_clipped(rng):
    frame, v = _clipped_case(rng)
    _, lam, d_esc = PolarProjector().evaluate(v, frame, 0)
    s = float(np.sign(lam))
    y = np.dot(v, frame.c1_hat)
    expected = 1.0 - y**2 - 2 * s * np.dot(v, frame.v_dipole) + frame.v_dipole_norm_sq
    assert _close(d_esc**2, expected)
    wrong_sign = 1.0 - y**2 + 2 * s * np.dot(v, frame.v_dipole) + frame.v_dipole_norm_sq
    assert not _close(d_esc**2, wrong_sign)


def test_d12_no_clip_when_the_dipole_norm_is_at_least_one(rng):
    for _ in range(TRIALS):
        frame = _frame(rng)
        assert frame.v_dipole_norm_sq >= 1.0
        for _ in range(20):
            v = _unit(rng.standard_normal(D))
            assert abs(_raw_lambda(v, frame)) <= 1.0


def test_d12_clips_below_the_bound(rng):
    frame, v = _clipped_case(rng)
    y = np.dot(v, frame.c1_hat)
    assert np.sqrt(frame.v_dipole_norm_sq) < np.sqrt(1.0 - y**2)
    assert abs(_raw_lambda(v, frame)) > 1.0


# D5 ---------------------------------------------------------------------------------------------


def test_d5_similarity_order_is_distance_order_on_the_sphere(rng):
    q = _unit(rng.standard_normal(D))
    notes = np.array([_unit(rng.standard_normal(D)) for _ in range(500)])
    by_similarity = np.argsort(-(notes @ q), kind="stable")
    by_distance = np.argsort(np.linalg.norm(notes - q, axis=1), kind="stable")
    assert np.array_equal(by_similarity, by_distance)


def test_d5_breaks_with_unequal_norms(rng):
    q = _unit(rng.standard_normal(D))
    notes = np.array([_unit(rng.standard_normal(D)) for _ in range(500)])
    notes[::2] *= 3.0
    by_similarity = np.argsort(-(notes @ q), kind="stable")
    by_distance = np.argsort(np.linalg.norm(notes - q, axis=1), kind="stable")
    assert not np.array_equal(by_similarity, by_distance)


# D6 ---------------------------------------------------------------------------------------------


def test_d6_r2_invariant_to_affine_maps_with_an_intercept(rng):
    n = 1110
    X = rng.standard_normal((n, 5))
    y = X @ rng.standard_normal(5) + rng.standard_normal(n)
    design = np.column_stack([np.ones(n), X])
    mapped = np.column_stack([np.ones(n), 3.0 * X - 7.0])
    assert _close(_r2(y, design), _r2(-2.5 * y + 4.0, mapped))


def test_d6_breaks_without_an_intercept(rng):
    n = 1110
    X = rng.standard_normal((n, 5))
    y = X @ rng.standard_normal(5) + rng.standard_normal(n)
    assert not _close(_r2(y, X), _r2(y + 50.0, X))


# D7 ---------------------------------------------------------------------------------------------


@pytest.mark.parametrize("rho", [0.05, 0.3, 0.5, 0.9])
def test_d7_calibration_control_has_exact_r2(rng, rho):
    n = 1110
    B = np.column_stack([np.ones(n), rng.standard_normal((n, 8))])
    h_hat = B @ rng.standard_normal(9)
    noise = rng.standard_normal(n)
    beta, *_ = np.linalg.lstsq(B, noise, rcond=None)
    n_perp = noise - B @ beta
    a, b = np.sqrt(rho), np.sqrt(1.0 - rho)
    assert abs(_r2(a * _z(h_hat) + b * _z(n_perp), B) - rho) < ATOL


def test_d7_breaks_when_the_noise_is_not_residualised(rng):
    n = 1110
    B = np.column_stack([np.ones(n), rng.standard_normal((n, 8))])
    h_hat = B @ rng.standard_normal(9)
    noise = rng.standard_normal(n) + B[:, 1]
    a, b = np.sqrt(0.3), np.sqrt(0.7)
    assert abs(_r2(a * _z(h_hat) + b * _z(noise), B) - 0.3) > 1e-3


# D8 ---------------------------------------------------------------------------------------------


def _exceed_probability(n, r):
    """Exact P(a value exchangeable with n null values exceeds the r-th smallest null)."""
    hits = total = 0
    for perm in itertools.permutations(range(n + 1)):
        candidate, nulls = perm[0], sorted(perm[1:])
        hits += candidate > nulls[r - 1]
        total += 1
    return Fraction(hits, total)


def test_d8_tail_formula_by_exhaustive_enumeration():
    for n in range(1, 7):
        for r in range(1, n + 1):
            assert _exceed_probability(n, r) == Fraction(n + 1 - r, n + 1)


def test_d8_instance_used_by_k6():
    per_candidate = Fraction(1000 + 1 - 989, 1001)
    assert per_candidate == Fraction(12, 1001)
    assert 4 * per_candidate <= Fraction(1, 20)


def test_d8_breaks_at_the_988th_value():
    assert 4 * Fraction(1000 + 1 - 988, 1001) > Fraction(1, 20)


# D9 ---------------------------------------------------------------------------------------------

M = 1109


def _overlap_moments(m, k=15):
    pmf = {j: Fraction(math.comb(k, j) * math.comb(m - k, k - j), math.comb(m, k)) for j in range(k + 1)}
    mean = sum(j * p for j, p in pmf.items())
    var = sum(j * j * p for j, p in pmf.items()) - mean**2
    return sum(pmf.values()), mean, var


def test_d9_overlap_count_moments_exactly():
    total, mean, var = _overlap_moments(M)
    p = Fraction(15, M)
    assert total == 1
    assert mean == Fraction(225, M)
    assert var == 15 * p * (1 - p) * Fraction(M - 15, M - 1)
    assert abs(float(mean) - 0.20289) < 1e-5
    assert abs(float(var) - 0.19762) < 1e-5


def test_d9_breaks_if_the_fraction_is_read_as_the_count():
    _, mean, _ = _overlap_moments(M)
    assert mean != Fraction(15, M)


# D10 --------------------------------------------------------------------------------------------


def test_d10_random_axis_is_orthogonal_to_q(rng):
    for _ in range(TRIALS):
        q = _unit(rng.standard_normal(D))
        u = _unit(_perp(rng.standard_normal(D), q))
        assert abs(np.dot(u, q)) < ATOL


def test_d10_q_sits_at_zero_in_its_own_perspective_exactly(rng):
    for _ in range(TRIALS):
        q = _unit(rng.standard_normal(D))
        frame = PolarProjector().prepare(q, rng.standard_normal(D), rng.standard_normal(D))
        _, lam, d_esc = PolarProjector().evaluate(q, frame, 0)
        assert lam == 0.0
        assert d_esc == 0.0


def test_d10_breaks_for_a_direction_parallel_to_q(rng):
    q = _unit(rng.standard_normal(D))
    assert np.linalg.norm(_perp(5.0 * q, q)) < ATOL


# Z (D17, D19-D21, D23-D26), through tools/experiments/zoom_three_point.py -----------------------

G = 1.0 / (2.0 * math.sqrt(2.0))
TUBE = 4.0 * math.sqrt(2.0)
FD_STEP = 1e-5
FD_TOL = 1e-8  # central differences: truncation ≈ FD_STEP² ≈ 1e-10, rounding ≈ 1e-16 / FD_STEP ≈ 1e-11
R64 = zoom.gauss_legendre(64)
R_INTEGRAL = zoom.gauss_legendre(256)  # stands for the integral: √(1 + Var) is analytic on a leg
Z7 = np.zeros(7)


def _axis(k):
    x = np.zeros(8)
    x[k] = 1.0
    return x


def _central(fn, x, step=FD_STEP):
    out = np.empty(len(x))
    for k in range(len(x)):
        e = np.zeros(len(x))
        e[k] = step
        out[k] = (fn(x + e) - fn(x - e)) / (2.0 * step)
    return out


def _tau_from(p, rule):
    return lambda q: zoom.tau_seg(p, q, rule)


def _tau_to(q, rule):
    return lambda p: zoom.tau_seg(p, q, rule)


def _route_s(a, m, b, rule):
    return zoom.tau_seg(a, m, rule) + zoom.tau_seg(m, b, rule)


def _affine_friction(c0, slope, axis):
    grad = slope * _axis(axis)
    return zoom.Friction(
        root=lambda x: c0 + slope * x[:, axis], root_grad=lambda x: np.tile(grad, (len(x), 1))
    )


def _random_line(rng):
    a = rng.uniform(-0.5, 0.5, 8)
    return zoom.make_line(a, a + rng.uniform(0.3, 1.0) * _unit(rng.standard_normal(8)))


def _random_offset(rng, line, low=0.0, high=0.5):
    return rng.uniform(low, high) * zoom.h_max(line.d) * _unit(rng.standard_normal(7))


def _radial(p, u, rule):
    return lambda r: zoom.tau_seg(p, p + r[0] * u, rule)


def _g(line, rule):
    def g(z):
        _, m = zoom.mid(line, z, rule)
        return _route_s(line.a, m, line.b, rule)

    return g


def _xi(line, rule):
    return lambda z: zoom.mid(line, z, rule)[0]


# D17 --------------------------------------------------------------------------------------------


def test_d17_variance_gradient_is_a_quarter_of_the_centred_coordinates(rng):
    for _ in range(TRIALS):
        c = rng.uniform(-1.0, 1.0, 8)
        grad = zoom.variance_gradient(c[None, :])[0]
        assert np.allclose(grad, 0.25 * (c - c.mean()), rtol=RTOL, atol=ATOL)
        assert np.allclose(grad, _central(np.var, c), rtol=0.0, atol=FD_TOL)
    for n in (3, 20):
        c = rng.standard_normal(n)
        assert np.allclose((2.0 / n) * (c - c.mean()), _central(np.var, c), rtol=0.0, atol=FD_TOL)


def test_d17_breaks_without_the_mean_term(rng):
    c = rng.uniform(0.2, 1.0, 8)
    assert not np.allclose(0.25 * c, _central(np.var, c), rtol=0.0, atol=FD_TOL)


# D19 --------------------------------------------------------------------------------------------


def _tau_curve(pos, speed, root, t, breaks=(0.25, 0.5)):
    """∫₀ᵗ √f(Pos(s))‖Pos'(s)‖ ds, 256 Gauss–Legendre nodes on each piece between breaks."""
    x, w = np.polynomial.legendre.leggauss(256)
    edges = [0.0, *[c for c in breaks if c < t], t]
    total = 0.0
    for lo, hi in itertools.pairwise(edges):
        s = lo + (hi - lo) * (x + 1.0) / 2.0
        total += (hi - lo) / 2.0 * float(w @ (root(pos(s)) * speed(s)))
    return total


def _curve(kind, a, b, m):
    mid = (a + b) / 2.0
    if kind == "segment":
        return (lambda s: a + s[:, None] * (b - a)), (lambda s: np.full(len(s), np.linalg.norm(b - a)))
    if kind == "two-legs":

        def pos(s):
            first = a + 2.0 * s[:, None] * (m - a)
            return np.where(s[:, None] <= 0.5, first, m + (2.0 * s[:, None] - 1.0) * (b - m))

        return pos, lambda s: np.where(s <= 0.5, 2.0 * np.linalg.norm(m - a), 2.0 * np.linalg.norm(b - m))
    bend = m - mid

    def velocity(s):
        return (b - a) + (4.0 - 8.0 * s[:, None]) * bend

    return (
        lambda s: a + s[:, None] * (b - a) + 4.0 * (s * (1.0 - s))[:, None] * bend,
        lambda s: np.linalg.norm(velocity(s), axis=1),
    )


@pytest.mark.parametrize("kind", ["segment", "parabola", "parabola-turning", "two-legs"])
def test_d19_friction_time_is_strictly_increasing_with_a_unique_half_time(rng, kind):
    a, b, m = rng.uniform(-1.0, 1.0, (3, 8))
    if kind == "parabola-turning":
        m = a.copy()  # Pos'(1/4) = 0: the curve turns back once
    pos, speed = _curve(kind.removesuffix("-turning"), a, b, m)
    root = zoom.VAR_FRICTION.root
    taus = np.array([_tau_curve(pos, speed, root, t) for t in np.linspace(0.0, 1.0, 201)])
    assert np.all(np.diff(taus) > 0.0)
    half = taus[-1] / 2.0
    t_star, _, _ = zoom.bisect(lambda t: _tau_curve(pos, speed, root, t) - half, 1.0)
    assert _close(_tau_curve(pos, speed, root, t_star), half)
    assert np.count_nonzero(np.diff(taus > half)) == 1


def test_d19_breaks_where_the_friction_vanishes_on_a_stretch():
    a, b = np.zeros(8), _axis(0)
    pos, speed = _curve("segment", a, b, a)

    def root(x):
        return ((x[:, 0] < 0.25) | (x[:, 0] > 0.75)).astype(float)

    grid = np.linspace(0.0, 1.0, 201)
    taus = np.array([_tau_curve(pos, speed, root, t, breaks=(0.25, 0.75)) for t in grid])
    assert not np.all(np.diff(taus) > 0.0)
    assert np.count_nonzero(np.abs(taus - taus[-1] / 2.0) <= ATOL) > 1


# D20 --------------------------------------------------------------------------------------------


def test_d20_node_sum_gradients_match_finite_differences_of_the_64_node_tau(rng):
    for _ in range(TRIALS):
        p, q = rng.uniform(-1.0, 1.0, (2, 8))
        grad_q, grad_p = zoom.tau_seg_grad(p, q, R64)
        assert np.allclose(grad_q, _central(_tau_from(p, R64), q), rtol=0.0, atol=FD_TOL)
        assert np.allclose(grad_p, _central(_tau_to(q, R64), p), rtol=0.0, atol=FD_TOL)


def test_d20_breaks_with_the_node_weights_of_the_two_ends_swapped(rng):
    p, q = rng.uniform(-1.0, 1.0, (2, 8))
    diff = q - p
    length = np.linalg.norm(diff)
    points = p + R64.nodes[:, None] * diff
    root, grad = zoom.VAR_FRICTION.root(points), zoom.VAR_FRICTION.root_grad(points)
    swapped = diff / length * (R64.weights @ root) + length * ((R64.weights * (1.0 - R64.nodes)) @ grad)
    assert not np.allclose(swapped, _central(_tau_from(p, R64), q), rtol=0.0, atol=FD_TOL)


def test_d20_reversal_holds_for_the_symmetric_rule(rng):
    for _ in range(TRIALS):
        p, q = rng.uniform(-1.0, 1.0, (2, 8))
        assert _close(zoom.tau_seg(p, q, R64), zoom.tau_seg(q, p, R64))


def test_d20_reversal_breaks_for_a_rule_that_is_not_symmetric(rng):
    n = 64
    right = zoom.Rule(np.arange(1, n + 1) / n, np.full(n, 1.0 / n), zoom.VAR_FRICTION)
    p, q = rng.uniform(-1.0, 1.0, (2, 8))
    assert not _close(zoom.tau_seg(p, q, right), zoom.tau_seg(q, p, right))


def test_d20_additivity_and_radial_rate_of_the_integral(rng):
    for _ in range(TRIALS):
        p, q = rng.uniform(-1.0, 1.0, (2, 8))
        split = p + rng.uniform(0.0, 1.0) * (q - p)
        whole = zoom.tau_seg(p, q, R_INTEGRAL)
        assert _close(whole, zoom.tau_seg(p, split, R_INTEGRAL) + zoom.tau_seg(split, q, R_INTEGRAL))
        u, r = _unit(q - p), rng.uniform(0.1, 1.0)
        rate = _central(_radial(p, u, R_INTEGRAL), np.array([r]))[0]
        root = zoom.VAR_FRICTION.root((p + r * u)[None, :])[0]
        assert abs(rate - root) <= FD_TOL
        assert root >= 1.0


def test_d20_additivity_breaks_off_the_segment_and_the_rate_off_a_unit_direction(rng):
    p, q = rng.uniform(-1.0, 1.0, (2, 8))
    u = _unit(q - p)
    split = p + 0.4 * (q - p) + 0.3 * _unit(_perp(rng.standard_normal(8), u))
    whole = zoom.tau_seg(p, q, R_INTEGRAL)
    assert not _close(whole, zoom.tau_seg(p, split, R_INTEGRAL) + zoom.tau_seg(split, q, R_INTEGRAL))
    rate = _central(_radial(p, 2.0 * u, R_INTEGRAL), np.array([0.5]))[0]
    assert abs(rate - zoom.VAR_FRICTION.root((p + u)[None, :])[0]) > 0.5


# D21 --------------------------------------------------------------------------------------------


def _touching_case(offset=0.0):
    """√f = 2 + 0.3·x₂, A = −e₁, B = e₁: E = 0 on x₁ = 0 by symmetry; S there is least at x₂ = t*."""
    c0, slope = 2.0, 0.3
    rule = zoom.gauss_legendre(64, _affine_friction(c0, slope, 1))
    t_star = -slope / (c0 + math.sqrt(c0**2 - 2.0 * slope**2))
    return rule, -_axis(0), _axis(0), (t_star + offset) * _axis(1)


def _lagrange(rule, a, b, m):
    grad_a, _ = zoom.tau_seg_grad(a, m, rule)
    _, grad_b = zoom.tau_seg_grad(m, b, rule)
    u = _unit(b - a)
    grad_s, grad_e = grad_a + grad_b, grad_a - grad_b
    mu = float(grad_s @ u) / float(grad_e @ u)
    return grad_a, grad_b, grad_s - mu * grad_e, mu


def test_d21_equal_friction_time_hyperspheres_touch_at_the_known_point():
    rule, a, b, m = _touching_case()
    assert abs(zoom.route_e(a, m, b, rule)) <= ATOL
    grad_a, grad_b, residual, mu = _lagrange(rule, a, b, m)
    assert np.allclose(residual, 0.0, atol=ATOL)
    assert abs(mu) < 1.0
    assert np.allclose((1.0 - mu) * grad_a, -(1.0 + mu) * grad_b, atol=ATOL)
    root = rule.friction.root(m[None, :])[0]
    assert root >= 1.0
    assert _close(float(grad_a @ _unit(m - a)), root)
    assert _close(float(grad_b @ _unit(m - b)), root)
    on_segment = a + 0.3 * (b - a)
    slope = _chord_slope(a, on_segment, b, rule)
    assert _close(slope, 2.0 * rule.friction.root(on_segment[None, :])[0])


def test_d21_breaks_at_another_point_of_the_constraint():
    rule, a, b, m = _touching_case(offset=0.05)
    assert abs(zoom.route_e(a, m, b, rule)) <= ATOL
    _, _, residual, _ = _lagrange(rule, a, b, m)
    assert np.linalg.norm(residual) > 1e-3


# D23 --------------------------------------------------------------------------------------------


def _phi(xi, d, h):
    r_a, r_b = math.hypot(xi, h), math.hypot(d - xi, h)
    return xi / r_a + (d - xi) / r_b - (G / 2.0) * (r_a + r_b)


def _chord_slope(a, m, b, rule):
    return float((zoom.tau_seg_grad(a, m, rule)[0] - zoom.tau_seg_grad(m, b, rule)[1]) @ _unit(b - a))


@pytest.mark.parametrize("rule", [R_INTEGRAL, R64], ids=["integral", "64-node"])
def test_d23_slope_along_the_chord_exceeds_phi_on_parallels_inside_the_tube(rng, rule):
    for _ in range(TRIALS):
        a, d = rng.uniform(-1.0, 1.0, 8), rng.uniform(0.05, TUBE - 0.05)
        u = _unit(rng.standard_normal(8))
        y = rng.uniform(0.0, 1.0) * zoom.h_max(d) * _unit(_perp(rng.standard_normal(8), u))
        xi = rng.uniform(0.0, d)
        phi = _phi(xi, d, float(np.linalg.norm(y)))
        assert phi >= -1e-12
        assert _chord_slope(a, a + xi * u + y, a + d * u, rule) > phi


def test_d23_h_max_is_its_closed_form_and_the_zero_of_phi_at_the_ends():
    for d in np.linspace(0.01, TUBE - 0.01, 60):
        w = 8.0 * math.sqrt(2.0) / d - 1.0
        h = zoom.h_max(d)
        assert _close(h, d * (w - 1.0) / (2.0 * math.sqrt(w)))
        assert _close(h, (TUBE - d) * math.sqrt(d / (2.0 * TUBE - d)))
        assert abs(_phi(0.0, d, h)) <= ATOL
        assert _phi(0.0, d, 0.99 * h) > 0.0 > _phi(0.0, d, 1.01 * h)


def _bump_friction(centre, height, width):
    def bump(x):
        return height * np.exp(-((x - centre) ** 2).sum(axis=1) / width**2)

    return zoom.Friction(
        root=lambda x: 1.0 + bump(x),
        root_grad=lambda x: (-2.0 / width**2) * bump(x)[:, None] * (x - centre),
    )


def test_d23_breaks_with_a_friction_steeper_than_its_bound():
    centre = 0.1 * _axis(0) + 0.15 * _axis(1)
    rule = zoom.gauss_legendre(256, _bump_friction(centre, 50.0, 0.03))
    a, b, y = np.zeros(8), _axis(0), 0.3 * _axis(1)
    assert np.linalg.norm(y) <= zoom.h_max(1.0)
    slopes = [_chord_slope(a, a + xi * _axis(0) + y, b, rule) for xi in np.linspace(0.0, 1.0, 101)]
    assert min(slopes) < 0.0


# D24 --------------------------------------------------------------------------------------------


def test_d24_gradients_of_g_and_of_xi_match_finite_differences_through_the_bisection(rng):
    for _ in range(10):
        line = _random_line(rng)
        z = _random_offset(rng, line)
        point = zoom.evaluate(line, z, R64)
        assert np.allclose(point.grad, _central(_g(line, R64), z), rtol=0.0, atol=FD_TOL)
        grad_xi = -line.zn.T @ point.grad_e / point.slope
        assert np.allclose(grad_xi, _central(_xi(line, R64), z), rtol=0.0, atol=FD_TOL)


def test_d24_breaks_without_the_multiplier_term(rng):
    line = _random_line(rng)
    z = _random_offset(rng, line)
    point = zoom.evaluate(line, z, R64)
    assert abs(point.mu_hat) > 1e-3
    assert not np.allclose(line.zn.T @ point.grad_s, _central(_g(line, R64), z), rtol=0.0, atol=FD_TOL)


def test_d24_moving_along_the_chord_off_the_constraint_changes_s_by_minus_mu_e_to_first_order(rng):
    line = _random_line(rng)
    point = zoom.evaluate(line, _random_offset(rng, line), R64)
    residuals = []
    for delta in (1e-2, 1e-3):
        m = point.m + delta * line.u
        e = zoom.route_e(line.a, m, line.b, R64)
        residuals.append(abs(point.s - _route_s(line.a, m, line.b, R64) + point.mu_hat * e))
    assert residuals[1] <= residuals[0] / 50.0


# D25 --------------------------------------------------------------------------------------------


def _index_ranks(n_u):
    """Ranks under which every note's 384-d order is the other notes in index order."""
    ranks = np.empty((n_u, n_u), dtype=np.intp)
    for j in range(n_u):
        others = [i for i in range(n_u) if i != j]
        ranks[j, others] = np.arange(1, n_u)
        ranks[j, j] = n_u
    return ranks


def _order_in(ranks, j, view):
    return np.array(sorted((i for i in view if i != j), key=lambda i: ranks[j, i]), dtype=np.intp)


def test_d25_a_every_neighbourhood_kept_scores_one_and_a_view_smaller_than_k_plus_1_cannot(rng):
    n_u = 12
    x = rng.standard_normal((n_u, 5))
    ranks = zoom.hyp_ranks(x @ x.T)
    view = np.arange(n_u)
    r = zoom.score_orders([_order_in(ranks, j, view) for j in view], view, ranks, n_u)
    assert np.all(r == 1.0)
    assert zoom.auc(r) == 1.0
    small = np.array([2, 5, 7])
    r_small = zoom.score_orders([_order_in(ranks, j, small) for j in small], small, ranks, n_u)
    k = np.arange(1, n_u - 1)
    assert np.all(r_small <= 1.0)
    assert np.all(r_small[:, k >= len(small)] < 1.0)
    weights = 1.0 / k
    assert _close(zoom.auc(r_small), float(np.mean(r_small @ weights / weights.sum())))


def _null_moments(n_u, n_m, n_c):
    """Exact mean and variance of R_j(K) at every K over every arrangement of N_M − 1 others."""
    ranks = _index_ranks(n_u)
    others = range(1, n_u)
    arrangements = list(itertools.permutations(others, n_m - 1))
    moments = []
    for k in range(1, n_u - 1):
        k_prime = min(k, n_m - 1)
        values = []
        for arrangement in arrangements:
            o = int(zoom.overlaps(ranks[0], np.array(arrangement, dtype=np.intp), n_u)[k - 1])
            values.append(
                (Fraction(o, k) - Fraction(k_prime, n_c)) / (1 - Fraction(k_prime, n_c))
            )
        mean = sum(values, Fraction(0)) / len(values)
        var = sum(((v - mean) ** 2 for v in values), Fraction(0)) / len(values)
        moments.append((k, k_prime, mean, var))
    return moments


@pytest.mark.parametrize(("n_u", "n_m"), [(5, 3), (6, 4), (6, 6), (7, 3)])
def test_d25_b_no_information_has_mean_zero_and_the_stated_variance_exactly(n_u, n_m):
    n_c = n_u - 1
    for k, k_prime, mean, var in _null_moments(n_u, n_m, n_c):
        assert mean == 0
        assert var == Fraction(k_prime * (n_c - k), k * (n_c - k_prime) * (n_c - 1))
        assert var <= Fraction(1, n_u - 2)


def test_d25_b_r_values_are_the_exact_formula_at_every_scale():
    n_u, n_m = 7, 4
    ranks = _index_ranks(n_u)
    n_c = n_u - 1
    for arrangement in itertools.permutations(range(1, n_u), n_m - 1):
        o = zoom.overlaps(ranks[0], np.array(arrangement, dtype=np.intp), n_u)
        r = zoom.r_values(o[None, :], n_m, n_u)[0]
        for k in range(1, n_u - 1):
            k_prime = min(k, n_m - 1)
            exact = (Fraction(int(o[k - 1]), k) - Fraction(k_prime, n_c)) / (1 - Fraction(k_prime, n_c))
            assert _close(r[k - 1], float(exact))


def test_d25_b_breaks_with_the_candidates_counted_as_n_u():
    assert any(mean != 0 for _, _, mean, _ in _null_moments(6, 4, 6))


def test_d25_c_r_nx_at_15_is_the_mean_overlap_against_225_over_n_c(rng):
    n_u = 40
    x = rng.standard_normal((n_u, 6))
    ranks = zoom.hyp_ranks(x @ x.T)
    view = np.arange(n_u)
    orders = [np.delete(view, j)[rng.permutation(n_u - 1)] for j in view]
    r = zoom.score_orders(orders, view, ranks, n_u)
    n_c = n_u - 1
    overlap = np.mean([len(set(_order_in(ranks, j, view)[:15]) & set(orders[j][:15])) for j in view])
    assert _close(r[:, 14].mean(), (overlap - 225.0 / n_c) / (15.0 - 225.0 / n_c))
    assert not _close(r[:, 14].mean(), (overlap - 15.0 / n_c) / (15.0 - 15.0 / n_c))


# D26 --------------------------------------------------------------------------------------------


def _diagonal_chord(rng):
    a = rng.uniform(-0.5, 0.5) * np.ones(8)
    w = rng.standard_normal(8)
    return a, a + rng.uniform(0.1, 1.0) * _unit(w - w.mean())


def test_d26_no_route_through_any_point_beats_the_segment_and_m0_is_the_only_answer(rng):
    for _ in range(20):
        a, b = _diagonal_chord(rng)
        tau_ab = zoom.tau_seg(a, b, R_INTEGRAL)
        for m in a + rng.uniform(-1.0, 1.0, (5, 8)):
            assert _route_s(a, m, b, R_INTEGRAL) >= tau_ab - ATOL
        line = zoom.make_line(a, b)
        _, m0 = zoom.mid(line, Z7, R_INTEGRAL)
        assert _close(_route_s(a, m0, b, R_INTEGRAL), tau_ab)
        _, m = zoom.mid(line, _random_offset(rng, line, low=0.1), R_INTEGRAL)
        assert _route_s(a, m, b, R_INTEGRAL) > tau_ab + ATOL


def test_d26_quadrature_form_g_is_even_and_the_projection_gap_holds_node_by_node(rng):
    for _ in range(20):
        a, b = _diagonal_chord(rng)
        line = zoom.make_line(a, b)
        z = _random_offset(rng, line)
        g = _g(line, R64)
        assert _close(g(z), g(-z))
        assert np.linalg.norm(zoom.evaluate(line, Z7, R64).grad) <= 1e-12
        for t in rng.uniform(0.0, 1.0, 5):
            xi = t * line.d
            proj = a + xi * line.u
            m = proj + _perp(rng.uniform(-0.5, 0.5, 8), line.u)
            h2 = float((m - proj) @ (m - proj))
            gap = _route_s(a, m, b, R64) - _route_s(a, proj, b, R64)
            bound = h2 / (np.linalg.norm(m - a) + xi) + h2 / (np.linalg.norm(b - m) + line.d - xi)
            assert gap >= bound - ATOL


def test_d26_breaks_off_the_diagonal(rng):
    a = rng.uniform(-0.5, 0.5, 8)
    w = rng.standard_normal(8)
    line = zoom.make_line(a, a + 0.8 * _unit(w - w.mean()))
    point = zoom.evaluate(line, Z7, R64)
    assert np.linalg.norm(point.grad) > 1e-3
    z = -1e-3 * point.grad
    g = _g(line, R64)
    assert g(z) < point.s
    assert not _close(g(z), g(-z))
