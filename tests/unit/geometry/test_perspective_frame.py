"""perspective_frame: the frame of the perspective at q (frontend/audits/R4.md, "Perspective at q").

Poles from select_poles, unit axes as the poles' vectors, q as the anchor, PolarProjector.prepare
with its default parameters. Expected values are rebuilt here from the definitions.
"""

import numpy as np
import pytest

from traianus.geometry.perspective import PerspectiveFrame, perspective_frame
from traianus.geometry.polar_projector import PolarFrame

D = 384
FALLBACK_NORM = 0.2  # 2 * delta, delta = 0.1 (PolarProjector default)
ATOL = 1e-13


def _unit(x):
    return x / np.linalg.norm(x)


def _perp(x, q_hat):
    return x - (x @ q_hat) * q_hat


def _expected(q, basis):
    """Poles by decreasing <q, unit axis>, ties by id, and the dipole P_perp(a_A) - P_perp(a_B)."""
    q_hat = _unit(q)
    ranked = sorted(basis, key=lambda k: (-float(q @ _unit(basis[k])), k))
    a, b = (_unit(basis[k]) for k in ranked[:2])
    return (ranked[0], ranked[1]), _perp(a, q_hat) - _perp(b, q_hat)


def _coplanar_basis(q, gap, mirrored):
    """Two axes in the plane of q and a unit u orthogonal to it, of lengths 3 and 1/4.

    Normalised, their projections orthogonal to q differ by gap * u; mirrored gives the second
    axis the opposite cosine to q, so that the projections coincide when gap is 0.
    """
    q_hat = _unit(q)
    u = _unit(_perp(np.random.default_rng(7).standard_normal(D), q_hat))
    s_a, s_b = 0.6, 0.6 - gap
    c_a = np.sqrt(1.0 - s_a**2)
    c_b = np.sqrt(1.0 - s_b**2) * (-1.0 if mirrored else 1.0)
    return {"A": 3.0 * (c_a * q_hat + s_a * u), "B": 0.25 * (c_b * q_hat + s_b * u)}


def test_frame_is_built_from_the_unit_axes_of_the_poles_with_q_as_anchor():
    rng = np.random.default_rng(20260920)
    q = rng.standard_normal(D) * 3.7
    basis = {f"AXIS_{i + 1}": rng.standard_normal(D) * (1.0 + 4.0 * i) for i in range(8)}
    q_before, basis_before = q.copy(), {k: v.copy() for k, v in basis.items()}
    poles, dipole = _expected(q, basis)

    result = perspective_frame(q, basis)

    assert isinstance(result, PerspectiveFrame)
    assert isinstance(result.frame, PolarFrame)
    assert result.poles == poles
    assert result.fallback is False
    np.testing.assert_array_equal(result.frame.c_1, q)
    np.testing.assert_allclose(result.frame.c1_hat, q / np.linalg.norm(q), rtol=0, atol=ATOL)
    assert np.linalg.norm(result.frame.c1_hat) == pytest.approx(1.0, abs=ATOL)
    np.testing.assert_allclose(result.frame.v_dipole, dipole, rtol=0, atol=ATOL)
    assert abs(result.frame.v_dipole @ result.frame.c1_hat) < ATOL
    assert result.frame.v_dipole_norm_sq == pytest.approx(float(dipole @ dipole), rel=1e-12)
    np.testing.assert_array_equal(q, q_before)
    for axis_id, axis in basis.items():
        np.testing.assert_array_equal(axis, basis_before[axis_id])


@pytest.mark.parametrize(
    "gap, mirrored",
    [(0.0, False), (0.0, True), (5e-7, False)],
    ids=["same-direction", "mirrored-through-q", "just-inside-eps"],
)
def test_collinear_projections_flag_the_fallback_and_keep_the_canonical_dipole(gap, mirrored):
    q = np.random.default_rng(3).standard_normal(D) * 2.5
    basis = _coplanar_basis(q, gap, mirrored)
    q_hat = _unit(q)
    e_k = np.zeros(D)
    e_k[int(np.argmin(np.abs(q_hat)))] = 1.0
    u_perp = _unit(_perp(e_k, q_hat))

    result = perspective_frame(q, basis)

    assert result.fallback is True
    assert result.poles == _expected(q, basis)[0]
    np.testing.assert_allclose(result.frame.v_dipole, FALLBACK_NORM * u_perp, rtol=0, atol=ATOL)
    assert result.frame.v_dipole_norm_sq == pytest.approx(FALLBACK_NORM**2, rel=1e-12)
    assert abs(result.frame.v_dipole @ result.frame.c1_hat) < ATOL


def test_projections_just_outside_the_collinearity_threshold_keep_the_contrast_dipole():
    q = np.random.default_rng(3).standard_normal(D) * 2.5
    basis = _coplanar_basis(q, 2e-6, False)
    poles, dipole = _expected(q, basis)

    result = perspective_frame(q, basis)

    assert result.fallback is False
    assert result.poles == poles
    np.testing.assert_allclose(result.frame.v_dipole, dipole, rtol=0, atol=ATOL)
    assert np.linalg.norm(result.frame.v_dipole) == pytest.approx(2e-6, rel=1e-6)


def test_errors_of_select_poles_and_of_prepare_propagate():
    e = np.eye(D)
    with pytest.raises(ValueError):
        perspective_frame(np.zeros(D), {"A": e[0], "B": e[1]})
    with pytest.raises(ValueError):
        perspective_frame(e[0], {"A": e[0]})
    with pytest.raises(ValueError, match="d >= 2"):
        perspective_frame(np.array([1.0]), {"A": np.array([1.0]), "B": np.array([-1.0])})
