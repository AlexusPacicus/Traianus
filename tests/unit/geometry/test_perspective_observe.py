"""observe: the coordinates of every vector in the perspective at q (frontend/audits/R4.md, "Observed space").

Columns [x?, y, colours...]: x = <v, horizontal> if a horizontal is given, y = <v, q_hat> with q the
vector at anchor_index, then the colours as given. Each column is z-scored with the mean and the
population sd over the N - 1 rows other than the anchor; the anchor row takes the same transform.
The reference is computed with math.fsum on plain floats, independently of the module.
"""

import math

import numpy as np
import pytest

from traianus.geometry.perspective import observe

D = 384
N = 40
ANCHOR = 7
ATOL = 1e-10


def _data(n=N):
    rng = np.random.default_rng(20260920)
    vectors = rng.standard_normal((n, D))
    vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
    colours = rng.random((n, 3)) * [1.0, 25.0, 0.01] + [0.0, 3.0, -1.0]
    return vectors, rng.standard_normal(D), colours


def _dot(a, b):
    return math.fsum(float(x) * float(y) for x, y in zip(a, b))


def _zscore(column, anchor):
    """Mean and population sd over the rows other than `anchor`, applied to every row."""
    others = [float(x) for i, x in enumerate(column) if i != anchor]
    mu = math.fsum(others) / len(others)
    sd = math.sqrt(math.fsum((x - mu) ** 2 for x in others) / len(others))
    return [(float(x) - mu) / sd for x in column]


def _reference(vectors, anchor, horizontal=None, colours=None):
    norm = math.sqrt(_dot(vectors[anchor], vectors[anchor]))
    q_hat = [float(x) / norm for x in vectors[anchor]]
    columns = []
    if horizontal is not None:
        columns.append([_dot(v, horizontal) for v in vectors])
    columns.append([_dot(v, q_hat) for v in vectors])
    if colours is not None:
        columns.extend(colours.T.tolist())
    return np.column_stack([_zscore(c, anchor) for c in columns])


def test_columns_are_z_scored_over_the_other_rows_and_the_anchor_takes_the_same_transform():
    vectors, horizontal, colours = _data()

    result = observe(vectors, ANCHOR, horizontal, colours)

    assert result.dtype == np.float64
    assert result.shape == (N, 5)
    expected = _reference(vectors, ANCHOR, horizontal, colours)
    np.testing.assert_allclose(result, expected, rtol=0, atol=ATOL)
    others = np.delete(result, ANCHOR, axis=0)
    np.testing.assert_allclose(others.mean(axis=0), 0.0, rtol=0, atol=ATOL)
    np.testing.assert_allclose(others.std(axis=0), 1.0, rtol=0, atol=ATOL)


def test_output_rows_follow_the_row_order_of_the_input():
    vectors, horizontal, colours = _data()
    perm = np.random.default_rng(5).permutation(N)
    new_anchor = int(np.flatnonzero(perm == ANCHOR)[0])
    assert new_anchor != ANCHOR

    result = observe(vectors, ANCHOR, horizontal, colours)
    permuted = observe(vectors[perm], new_anchor, horizontal, colours[perm])

    np.testing.assert_allclose(permuted, result[perm], rtol=0, atol=ATOL)


def test_calls_are_deterministic_and_inputs_are_never_mutated():
    vectors, horizontal, colours = _data()
    before = (vectors.copy(), horizontal.copy(), colours.copy())

    first = observe(vectors, ANCHOR, horizontal, colours)
    second = observe(vectors, ANCHOR, horizontal, colours)
    np.testing.assert_array_equal(first, second)
    first[:] = 0.0

    for after, kept in zip((vectors, horizontal, colours), before):
        np.testing.assert_array_equal(after, kept)


@pytest.mark.parametrize("m", [0, 1, 3])
@pytest.mark.parametrize("with_horizontal", [False, True])
def test_columns_are_x_then_y_then_the_colours(with_horizontal, m):
    vectors, horizontal, colours = _data()
    h = horizontal if with_horizontal else None
    c = colours[:, :m] if m else None

    result = observe(vectors, ANCHOR, h, c)

    assert result.shape == (N, 1 + with_horizontal + m)
    np.testing.assert_allclose(result, _reference(vectors, ANCHOR, h, c), rtol=0, atol=ATOL)


def test_result_is_float64_whatever_the_dtype_of_the_inputs():
    vectors, horizontal, colours = _data()

    result = observe(
        vectors.astype(np.float32), ANCHOR, horizontal.astype(np.float32), colours.astype(np.float32)
    )

    assert result.dtype == np.float64


def test_a_numpy_integer_is_an_anchor_index():
    vectors, _, _ = _data()

    np.testing.assert_array_equal(observe(vectors, np.int64(ANCHOR)), observe(vectors, ANCHOR))


@pytest.mark.filterwarnings("error")
@pytest.mark.parametrize("value", [0.1, 0.3, 1 / 3, 1e-3, 7.0])
def test_a_column_constant_over_the_other_rows_maps_to_zero_everywhere(value):
    vectors, horizontal, colours = _data()
    expected = _reference(vectors, ANCHOR, horizontal, colours[:, 2:])
    colours[:, 0] = value
    colours[:, 1] = value
    colours[ANCHOR, 1] = value + 5.0

    result = observe(vectors, ANCHOR, horizontal, colours)

    assert np.all(result[:, 2:4] == 0.0)
    np.testing.assert_allclose(result[:, [0, 1, 4]], expected, rtol=0, atol=ATOL)


@pytest.mark.filterwarnings("error")
def test_a_zero_horizontal_maps_x_to_zero_everywhere():
    vectors, _, colours = _data()

    result = observe(vectors, ANCHOR, np.zeros(D), colours)

    assert np.all(result[:, 0] == 0.0)
    expected = _reference(vectors, ANCHOR, None, colours)
    np.testing.assert_allclose(result[:, 1:], expected, rtol=0, atol=ATOL)


@pytest.mark.filterwarnings("error")
def test_two_vectors_leave_one_other_row_so_every_column_has_zero_spread():
    vectors, horizontal, colours = _data(2)

    result = observe(vectors, 1, horizontal, colours)

    np.testing.assert_array_equal(result, np.zeros((2, 5)))


@pytest.mark.parametrize(
    "vectors",
    [np.ones(D), np.ones((1, D)), np.ones((0, D)), np.ones((3, 2, D))],
    ids=["1-d", "one-row", "no-rows", "3-d"],
)
def test_vectors_must_be_2d_with_at_least_two_rows(vectors):
    with pytest.raises(ValueError):
        observe(vectors, 0)


@pytest.mark.parametrize(
    "anchor_index",
    [-1, N, N + 5, np.int64(-1), 1.0, 1.5, "1", None, True],
    ids=["negative", "N", "beyond", "negative-numpy", "float-integral", "float", "str", "none", "bool"],
)
def test_anchor_index_must_be_an_integer_in_range(anchor_index):
    vectors, _, _ = _data()

    with pytest.raises(ValueError):
        observe(vectors, anchor_index)


@pytest.mark.parametrize("bad", [np.nan, np.inf, -np.inf])
@pytest.mark.parametrize("where", ["vectors-anchor", "vectors-other", "horizontal", "colours"])
def test_non_finite_values_are_rejected(where, bad):
    vectors, horizontal, colours = _data()
    array, index = {
        "vectors-anchor": (vectors, (ANCHOR, 3)),
        "vectors-other": (vectors, (0, 3)),
        "horizontal": (horizontal, 3),
        "colours": (colours, (5, 1)),
    }[where]
    array[index] = bad

    with pytest.raises(ValueError):
        observe(vectors, ANCHOR, horizontal, colours)


def test_a_zero_norm_anchor_row_is_rejected_but_a_zero_row_elsewhere_is_not():
    vectors, _, _ = _data()
    vectors[0] = 0.0

    assert np.all(np.isfinite(observe(vectors, ANCHOR)))

    vectors[ANCHOR] = 0.0
    with pytest.raises(ValueError):
        observe(vectors, ANCHOR)


@pytest.mark.parametrize(
    "shape", [(D - 1,), (D + 1,), (D, 1), (1, D), ()], ids=["short", "long", "column", "row", "scalar"]
)
def test_horizontal_must_have_shape_d(shape):
    vectors, _, _ = _data()

    with pytest.raises(ValueError):
        observe(vectors, ANCHOR, np.ones(shape))


@pytest.mark.parametrize(
    "shape",
    [(N,), (N - 1, 3), (N + 1, 3), (N, 0), (N, 3, 1)],
    ids=["1-d", "too-few-rows", "too-many-rows", "no-column", "3-d"],
)
def test_colours_must_be_2d_with_n_rows_and_a_column(shape):
    vectors, _, _ = _data()

    with pytest.raises(ValueError):
        observe(vectors, ANCHOR, colours=np.ones(shape))
