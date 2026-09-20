"""select_poles: the two axes with the largest projection on the vector q.

Poles of the perspective at q (frontend/audits/R4.md, "Perspective at q"): the two axes a_k with
the largest <q, a_k>, ties by axis id ascending (str order), c_A the larger. The projection is
taken on the normalised axis in float64, q as given; the result is the pair of axis ids.
"""
from itertools import permutations

import numpy as np
import pytest

from traianus.geometry.perspective import select_poles

D = 384
E = np.eye(4)
AXES = {"C": E[0], "A": E[1], "D": E[2], "B": E[3]}
GOOD_Q = np.array([1.0, 1.0, 0.0, 0.0])
GOOD_BASIS = {"A": E[0], "B": E[1], "C": E[2]}


def _axis(angle, k, length):
    """Axis at `angle` from e_0 towards e_k: <e_0, a> = cos(angle), whatever the length."""
    a = np.zeros(D)
    a[0] = np.cos(angle)
    a[k] = np.sin(angle)
    return length * a


def _orders(basis):
    return [dict(order) for order in permutations(basis.items())]


def test_poles_follow_direction_not_length_and_c_a_is_the_larger():
    q = np.zeros(D)
    q[0] = 2.5
    basis = {
        "MID": _axis(0.5, 3, 5.0),
        "LONG_OFF": _axis(0.9, 1, 100.0),
        "SHORT_ON": _axis(0.1, 2, 0.01),
        "ORTHOGONAL": _axis(np.pi / 2, 4, 1.0),
    }
    assert select_poles(q, basis) == ("SHORT_ON", "MID")


def test_poles_match_an_independent_ranking_on_random_vectors():
    rng = np.random.default_rng(20260920)
    q = rng.standard_normal(D) * 3.0
    basis = {f"AXIS_{i + 1}": rng.standard_normal(D) * (1.0 + 4.0 * i) for i in range(8)}
    by_cosine = sorted(basis, key=lambda k: -float(q @ basis[k]) / float(np.linalg.norm(basis[k])))
    assert select_poles(q, basis) == (by_cosine[0], by_cosine[1])


@pytest.mark.parametrize("scale", [1.0, 7.0])
@pytest.mark.parametrize(
    "q, expected",
    [
        ((1, 1, 0, 0), ("A", "C")),
        ((3, 0, 1, 1), ("C", "B")),
        ((1, 1, 1, 0), ("A", "C")),
        ((1, 1, 1, 1), ("A", "B")),
    ],
    ids=["tie-rank-1", "tie-rank-2", "three-way", "four-way"],
)
def test_exact_ties_go_to_the_smaller_axis_id_in_every_insertion_order(q, expected, scale):
    for basis in _orders(AXES):
        assert select_poles(scale * np.array(q, dtype=float), basis) == expected


def test_axes_of_the_same_direction_tie_whatever_their_length():
    basis = {"Z_LONG": 4.0 * E[0], "M": E[1], "A_SHORT": E[0], "N": E[2]}
    for ordered in _orders(basis):
        assert select_poles(E[0], ordered) == ("A_SHORT", "Z_LONG")


def test_tie_order_is_str_order_not_natural_order():
    basis = {"AXIS_2": E[0], "AXIS_10": E[1], "AXIS_1": E[2]}
    assert select_poles(GOOD_Q, basis) == ("AXIS_10", "AXIS_2")


def test_result_is_independent_of_insertion_order_and_of_the_scale_of_q():
    rng = np.random.default_rng(20260920)
    q = rng.standard_normal(D)
    ids = [f"AXIS_{i + 1}" for i in range(8)]
    vectors = {i: rng.standard_normal(D) for i in ids}
    ascending = {i: vectors[i] for i in sorted(ids)}
    descending = {i: vectors[i] for i in sorted(ids, reverse=True)}
    expected = select_poles(q, ascending)
    assert select_poles(q, descending) == expected
    assert select_poles(7.0 * q, ascending) == expected
    assert select_poles(7.0 * q, descending) == expected


@pytest.mark.parametrize(
    "q, basis, message",
    [
        (np.zeros(4), GOOD_BASIS, "q has zero norm"),
        (np.array([1.0, np.nan, 0.0, 0.0]), GOOD_BASIS, "q must be finite"),
        (np.array([1.0, np.inf, 0.0, 0.0]), GOOD_BASIS, "q must be finite"),
        (np.ones((2, 4)), GOOD_BASIS, "q must be 1-D"),
        (np.float64(1.0), GOOD_BASIS, "q must be 1-D"),
        (np.ones(3), GOOD_BASIS, "dimension"),
        (GOOD_Q, {**GOOD_BASIS, "X": np.ones(3)}, "dimension"),
        (GOOD_Q, {"A": E[0]}, "at least 2 axes"),
        (GOOD_Q, {}, "at least 2 axes"),
        (GOOD_Q, {**GOOD_BASIS, "Z": np.zeros(4)}, "axis Z has zero norm"),
        (GOOD_Q, {"A": E[0], "Z": np.zeros(4)}, "axis Z has zero norm"),
    ],
    ids=[
        "zero-q",
        "nan-q",
        "inf-q",
        "2d-q",
        "0d-q",
        "q-dimension",
        "axis-dimension",
        "one-axis",
        "no-axis",
        "zero-axis",
        "zero-axis-of-two",
    ],
)
def test_invalid_input_raises_value_error(q, basis, message):
    with pytest.raises(ValueError, match=message):
        select_poles(q, basis)


@pytest.mark.parametrize("bad", [np.nan, np.inf])
def test_non_finite_axis_raises_value_error(bad):
    axis = np.array([bad, 0.0, 0.0, 0.0])
    with pytest.raises(ValueError, match="axis X must be finite"):
        select_poles(GOOD_Q, {**GOOD_BASIS, "X": axis})
