"""Code verification of docs/methodology/instrument-audit/derivations.md (D1-D12).

Each derivation is checked by computation, not by reading: algebraic identities numerically in
float64 at d = 384 on seeded random inputs that satisfy the stated conditions, through the real
PolarProjector where the operator is involved; combinatorial ones exactly with Fraction. Every
derivation also has a negative case: violating its condition must break the equality, so no test
is vacuous.
"""

import itertools
import math
from fractions import Fraction

import numpy as np
import pytest

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


# D13 ---------------------------------------------------------------------------------------------


def test_d13_tail_formula_by_exhaustive_enumeration():
    for n in range(1, 7):
        for r in range(1, n + 1):
            assert _exceed_probability(n, r) == Fraction(n + 1 - r, n + 1)


def test_d13_instance_used_by_k8():
    per_candidate = Fraction(1000 + 1 - 951, 1001)
    assert per_candidate == Fraction(50, 1001)
    assert per_candidate <= Fraction(1, 20)


def test_d13_breaks_at_the_950th_value():
    below = Fraction(1000 + 1 - 950, 1001)
    assert below == Fraction(51, 1001)
    assert below > Fraction(1, 20)


# D14 ---------------------------------------------------------------------------------------------


def _modified_gram_schmidt_project(w, vectors):
    """Gram-Schmidt of `vectors` (in the given order), then subtract w's component on each."""
    basis = []
    for v in vectors:
        u = v.astype(float).copy()
        for b in basis:
            u = u - np.dot(u, b) * b
        basis.append(u / np.linalg.norm(u))
    out = w.copy()
    for b in basis:
        out = out - np.dot(out, b) * b
    return out


def test_d14_projection_is_independent_of_order_and_of_the_orthonormal_basis(rng):
    for _ in range(20):
        vectors = [rng.standard_normal(D) for _ in range(4)]
        w = rng.standard_normal(D)
        order1 = _modified_gram_schmidt_project(w, vectors)
        order2 = _modified_gram_schmidt_project(w, list(reversed(vectors)))
        q, _ = np.linalg.qr(np.column_stack(vectors))
        qr_projection = w - q @ (q.T @ w)
        assert np.allclose(order1, order2, rtol=0.0, atol=ATOL)
        assert np.allclose(order1, qr_projection, rtol=0.0, atol=ATOL)


def test_d14_breaks_with_linearly_dependent_columns(rng):
    v1, v2, v3 = (rng.standard_normal(D) for _ in range(3))
    vectors = [v1, v2, v3, v1 + v2]  # rank(s_1..s_4) = 3, not 4: D14's condition fails
    w = rng.standard_normal(D)
    with np.errstate(invalid="ignore", divide="ignore"):
        order1 = _modified_gram_schmidt_project(w, vectors)
        order2 = _modified_gram_schmidt_project(w, list(reversed(vectors)))
    assert np.any(np.isnan(order1)) or not np.allclose(order1, order2, rtol=0.0, atol=ATOL)


# D15 ---------------------------------------------------------------------------------------------


def _orthonormal_complement(s):
    """E: an orthonormal basis of S-perp, from the complete QR of S's columns."""
    m = s.shape[1]
    q_complete, _ = np.linalg.qr(s, mode="complete")
    return q_complete[:, m:]


def test_d15_projection_equals_e_e_transpose_g_and_norms_match(rng):
    for _ in range(20):
        s = np.column_stack([rng.standard_normal(D) for _ in range(4)])
        q, _ = np.linalg.qr(s)
        e = _orthonormal_complement(s)
        g = rng.standard_normal(D)
        p_perp_g = g - q @ (q.T @ g)
        assert np.allclose(p_perp_g, e @ (e.T @ g), rtol=0.0, atol=ATOL)
        assert np.isclose(np.linalg.norm(p_perp_g), np.linalg.norm(e.T @ g), rtol=0.0, atol=ATOL)


def test_d15_breaks_when_the_complement_basis_is_not_orthonormal(rng):
    s = np.column_stack([rng.standard_normal(D) for _ in range(4)])
    q, _ = np.linalg.qr(s)
    e = _orthonormal_complement(s)
    scaled = e * np.arange(1, e.shape[1] + 1)  # spans S-perp, but columns are not unit/orthogonal
    g = rng.standard_normal(D)
    p_perp_g = g - q @ (q.T @ g)
    assert not np.allclose(p_perp_g, scaled @ (scaled.T @ g), rtol=0.0, atol=ATOL)


# D16 ---------------------------------------------------------------------------------------------


def _resid(y, X):
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return y - X @ beta


def _d16_setup(rng, n=300):
    s1, s2, s3, s4 = (_unit(rng.standard_normal(D)) for _ in range(4))
    q, _ = np.linalg.qr(np.column_stack([s1, s2, s3, s4]))
    v = rng.standard_normal((n, D))
    x, y_, lam3, a8 = v @ s1, v @ s2, v @ s3, v @ s4
    b = np.column_stack(
        [np.ones(n), _z(x), _z(y_), _z(x) ** 2, _z(y_) ** 2, _z(x) * _z(y_), _z(lam3), _z(a8)]
    )
    return q, v, b


def test_d16_residual_identity_for_a_general_direction(rng):
    for _ in range(10):
        q, v, b = _d16_setup(rng)
        w = rng.standard_normal(D)
        pw = w - q @ (q.T @ w)
        pw = pw - q @ (q.T @ pw)  # twice (D14)
        assert np.allclose(_resid(v @ w, b), _resid(v @ pw, b), rtol=0.0, atol=1e-9)


def test_d16_in_particular_form_scales_the_lambda2_residual(rng):
    for _ in range(10):
        q, v, b = _d16_setup(rng)
        w2 = rng.standard_normal(D)
        pw2 = w2 - q @ (q.T @ w2)
        pw2 = pw2 - q @ (q.T @ pw2)
        u = pw2 / np.linalg.norm(pw2)
        z = v @ u
        lam2 = v @ w2 / (w2 @ w2)
        scale = (w2 @ w2) / np.linalg.norm(pw2)
        assert np.allclose(_resid(z, b), scale * _resid(lam2, b), rtol=0.0, atol=1e-9)


def test_d16_breaks_when_b_omits_one_of_the_spanning_functionals(rng):
    q, v, b = _d16_setup(rng)
    b_missing = b[:, :-1]  # drops z(a_8): B no longer contains every functional of S (condition)
    w = rng.standard_normal(D)
    pw = w - q @ (q.T @ w)
    pw = pw - q @ (q.T @ pw)
    assert not np.allclose(_resid(v @ w, b_missing), _resid(v @ pw, b_missing), rtol=0.0, atol=1e-9)
