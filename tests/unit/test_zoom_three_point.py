"""Unit tests of tools/experiments/zoom_three_point.py.

Specification: docs/methodology/instrument-audit/Z.md (revision 9), docs/methodology/instrument-audit/contracts.md
sections 0 and 4, docs/methodology/instrument-audit/derivations.md (D5, D17, D19-D21, D23-D26). Synthetic inputs
only: CI has no .data/, and the measurement is never run on the real artefact here.
"""

import dataclasses
import hashlib
import itertools
import json
import math
from pathlib import Path

import numpy as np
import pytest

from tools.experiments import k6_colour_predictability as k6
from tools.experiments import zoom_three_point as zoom

R64 = zoom.gauss_legendre(64)
Z0 = np.zeros(7)


def _e(k, n=8):
    x = np.zeros(n)
    x[k] = 1.0
    return x


def _affine_friction(c0, slope, axis):
    """√f = c0 + slope·x_axis: affine, so the 64-node τ of any straight leg is exact."""
    grad = slope * _e(axis)
    return zoom.Friction(
        root=lambda x: c0 + slope * x[:, axis], root_grad=lambda x: np.tile(grad, (len(x), 1))
    )


def _off_diagonal_line():
    a = np.array([0.30, -0.20, 0.10, 0.45, -0.35, 0.05, 0.20, -0.10])
    b = np.array([-0.25, 0.40, -0.30, 0.10, 0.25, -0.45, 0.35, 0.15])
    return zoom.make_line(a, b)


# Search (Z.md, Routes; unit tests (i)-(vi)) --------------------------------------------------------


def test_i_a_search_that_works_ends_at_2_below_the_benchmark_off_the_diagonal():
    line = _off_diagonal_line()
    start = zoom.evaluate(line, Z0, R64)
    assert np.linalg.norm(start.grad) > 1e6 * start.nu_g
    found = zoom.search(line, R64)
    assert (found.stop, found.condition) == ("converged", None)
    assert found.iterations > 0
    assert found.point.s < start.s - 2 * max(start.nu_g, found.point.nu_g)


def test_ii_the_search_ends_at_2_with_the_known_touching_point_in_its_uncertainty_sphere():
    c0, slope, a = 2.0, 0.3, 1.0
    rule = zoom.gauss_legendre(64, _affine_friction(c0, slope, 1))
    line = zoom.make_line(-a * _e(0), a * _e(0))
    t_star = -slope * a**2 / (c0 + math.sqrt(c0**2 - 2 * slope**2 * a**2))
    m_star = t_star * _e(1)
    found = zoom.search(line, rule)
    assert (found.stop, found.condition) == ("converged", None)
    rho3 = zoom.rho_3(found, line)
    assert np.linalg.norm(found.m - m_star) <= rho3
    assert np.linalg.norm(found.first.m - m_star) > 1e4 * rho3


@pytest.mark.parametrize(
    ("a", "b"),
    [
        pytest.param(0.1 * np.ones(8), 0.35 * np.ones(8), id="on-the-diagonal"),
        pytest.param(
            0.1 * np.ones(8),
            0.1 * np.ones(8) + 0.2 * np.array([1.0, -1.0, 0.5, -0.5, 0.0, 0.0, 0.2, -0.2]),
            id="orthogonal-to-the-diagonal",
        ),
    ],
)
def test_iii_known_answers_are_returned_with_no_step_and_both_middles_bit_for_bit(a, b):
    line = zoom.make_line(a, b)
    found = zoom.search(line, R64)
    assert (found.stop, found.condition, found.iterations) == ("converged", None, 0)
    assert not found.point.z.any()
    _, m0 = zoom.mid(line, Z0, R64)
    assert found.m.tobytes() == m0.tobytes()


def test_iv_search_code_fires_when_the_computed_direction_is_replaced_by_its_opposite(monkeypatch):
    original = zoom.direction
    monkeypatch.setattr(zoom, "direction", lambda grad, newton: -original(grad, newton))
    found = zoom.search(_off_diagonal_line(), R64)
    assert (found.condition, found.stop) == ("search_code", "ascent_direction")


def test_iv_search_code_fires_on_a_slope_along_the_chord_that_is_not_positive(monkeypatch):
    original = zoom.tau_seg_grad
    monkeypatch.setattr(
        zoom, "tau_seg_grad", lambda p, q, rule: tuple(-g for g in original(p, q, rule))
    )
    found = zoom.search(_off_diagonal_line(), R64)
    assert (found.condition, found.stop) == ("search_code", "slope_not_positive")


def test_v_mid_0_is_the_tau_midpoint_of_the_segment_in_closed_form():
    rule = zoom.gauss_legendre(64, _affine_friction(1.0, 0.2, 0))
    line = zoom.make_line(np.zeros(8), 2.0 * _e(0))
    xi, m0 = zoom.mid(line, Z0, rule)
    xi_star = 2.4 / (1.0 + math.sqrt(1.48))
    assert abs(xi - xi_star) <= zoom.rho_2(zoom.evaluate(line, Z0, rule), line)
    assert np.array_equal(m0, line.point(Z0, xi))


def test_v_mid_0_halves_the_64_node_tau_of_the_segment_up_to_the_rules_error():
    line = _off_diagonal_line()
    _, m0 = zoom.mid(line, Z0, R64)
    total = zoom.tau_seg(line.a, line.b, R64)
    assert abs(zoom.tau_seg(line.a, m0, R64) - total / 2) <= 1e-12 * total
    assert abs(zoom.route_e(line.a, m0, line.b, R64)) <= 1e-12 * total


@pytest.mark.parametrize(
    "sign",
    [
        pytest.param(lambda xi: xi - 0.3, id="monotone"),
        pytest.param(lambda xi: math.sin(40.0 * xi - 0.5), id="not-monotone"),
    ],
)
def test_v_the_bisection_keeps_its_invariant_and_stops_at_eps_d(sign):
    d = 1.0
    assert sign(0.0) < 0.0 <= sign(d)
    xi, lo, hi = zoom.bisect(sign, d)
    assert sign(lo) < 0.0 <= sign(hi)
    assert 0.0 < hi - lo <= zoom.EPS * d
    assert lo <= xi <= hi


def test_vi_a_trial_outside_the_tube_or_on_a_line_without_a_sign_change_is_rejected(monkeypatch):
    line = _off_diagonal_line()
    hmax = zoom.h_max(line.d)
    outside = np.full(7, 1.01 * hmax / math.sqrt(7))
    assert zoom.objective(line, outside, hmax, R64) is None
    inside = 0.5 * outside
    assert zoom.objective(line, inside, hmax, R64) is not None
    monkeypatch.setattr(zoom, "route_e", lambda a, m, b, rule: -1.0)
    assert zoom.objective(line, inside, hmax, R64) is None


def test_vi_the_line_search_halves_past_a_trial_outside_the_tube(monkeypatch):
    line = _off_diagonal_line()
    hmax = zoom.h_max(line.d)
    point = zoom.evaluate(line, Z0, R64)
    p = -3.0 * hmax * point.grad / np.linalg.norm(point.grad)
    seen = []
    original = zoom.objective

    def spy(line, z, hmax, rule):
        value = original(line, z, hmax, rule)
        seen.append((float(np.linalg.norm(z)), value))
        return value

    monkeypatch.setattr(zoom, "objective", spy)
    z = zoom.line_search(line, point, p, float(point.grad @ p), hmax, R64)
    assert seen[0][0] > hmax and seen[0][1] is None
    assert np.linalg.norm(z) <= hmax and seen[-1][1] is not None


def test_vi_a_search_forced_against_the_tube_edge_fails_search_converged(monkeypatch):
    line = _off_diagonal_line()
    radius = 0.3 * float(np.linalg.norm(zoom.search(line, R64).point.z))
    monkeypatch.setattr(zoom, "h_max", lambda d: radius)
    found = zoom.search(line, R64)
    assert (found.condition, found.stop) == ("search_converged", "edge")


def test_vi_a_floor_stop_fails_search_converged(monkeypatch):
    original = zoom.direction
    monkeypatch.setattr(zoom, "direction", lambda grad, newton: 1e-30 * original(grad, newton))
    found = zoom.search(_off_diagonal_line(), R64)
    assert (found.condition, found.stop) == ("search_converged", "floor")


def test_vi_a_critical_point_whose_hessian_is_not_positive_definite_fails_search_converged():
    kappa = 12.0

    def root(x):
        return 1.0 - kappa * (x[:, 1:] ** 2).sum(axis=1)

    def root_grad(x):
        grad = -2.0 * kappa * x
        grad[:, 0] = 0.0
        return grad

    rule = zoom.gauss_legendre(64, zoom.Friction(root, root_grad))
    line = zoom.make_line(np.zeros(8), _e(0))
    assert not zoom.evaluate(line, Z0, rule).grad.any()
    found = zoom.search(line, rule)
    assert (found.condition, found.stop) == ("search_converged", "critical_point")


def test_the_iteration_cap_fails_search_converged(monkeypatch):
    monkeypatch.setattr(zoom, "MAX_ITERATIONS", 1)
    found = zoom.search(_off_diagonal_line(), R64)
    assert (found.condition, found.stop, found.iterations) == ("search_converged", "cap", 1)


def test_a_step_that_falls_back_to_minus_the_gradient_is_counted(monkeypatch):
    original = zoom.newton_step
    calls = []

    def first_not_positive_definite(grad, h):
        calls.append(1)
        return (None, None) if len(calls) == 1 else original(grad, h)

    monkeypatch.setattr(zoom, "newton_step", first_not_positive_definite)
    found = zoom.search(_off_diagonal_line(), R64)
    assert (found.stop, found.fallback_steps) == ("converged", 1)


# States, Voronoi levels and frames (Z.md, States; Notes in view; Frame) -------------------------


def _corpus(fit, ev, extra=None):
    """A corpus whose axis coordinates are the given rows: â_k = o_k, notes padded to 384-d."""
    rows = np.empty((len(fit) + len(ev), 8))
    rows[0::2], rows[1::2] = fit, ev
    v = np.zeros((len(rows), 384))
    v[:, :8] = rows
    if extra is not None:
        v[:, 8:] = extra
    return zoom.make_corpus(v, np.eye(8, 384))


def _random_corpus(rng, n=40):
    v = rng.standard_normal((n, 384))
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    a = rng.standard_normal((8, 384))
    return zoom.make_corpus(v, a / np.linalg.norm(a, axis=1, keepdims=True))


def test_the_first_assignment_takes_the_largest_projection_and_ties_go_to_the_lower_site():
    x = np.zeros((5, 8))
    x[:, :2] = [[3.0, 0.0], [-3.0, 0.0], [0.0, 1.0], [0.0, -1.0], [0.0, 0.0]]
    assert zoom.first_assignment(x, np.zeros(8)).tolist() == [0, 1, 2, 3, 0]


@pytest.mark.parametrize("sign", [1.0, -1.0], ids=["tied-cell-first", "tied-cell-second"])
def test_lloyd_keeps_a_tied_note_in_its_current_cell_and_stops_when_no_note_moves(sign):
    x = np.zeros((5, 8))
    x[:, 0] = sign * np.array([-4.0, -2.0, 1.0, 5.0, 9.0])
    found = zoom.lloyd(x, np.zeros(8))
    groups = {frozenset(np.flatnonzero(found.labels == c).tolist()) for c in range(len(found.means))}
    assert groups == {frozenset({0, 1}), frozenset({2, 3, 4})}
    assert (found.iterations, found.converged, len(found.means)) == (1, True, 2)


def test_lloyd_drops_empty_cells_and_reaching_the_cap_fails_lloyd_converged(monkeypatch):
    x = np.zeros((6, 8))
    x[:, 0] = [-4.0, -2.0, -1.0, 1.0, 5.0, 9.0]
    assert len(zoom.lloyd(x, np.zeros(8)).means) == 2
    monkeypatch.setattr(zoom, "LLOYD_CAP", 0)
    assert not zoom.lloyd(x, np.zeros(8)).converged


def test_eval_notes_of_the_end_cell_go_to_the_nearest_mean_with_ties_to_the_lower_mean():
    fit, ev = np.zeros((4, 8)), np.zeros((4, 8))
    fit[:, 0] = [0.125, 0.375, 0.625, 0.875]
    ev[:, 0] = [0.25, 0.375, 0.1, 0.75]
    corpus = _corpus(fit, ev)
    state, found = zoom.level2(corpus, corpus.ev[0])
    assert found is not None and found.converged and len(found.means) == 2
    dist = ((corpus.ev[:, None, :] - found.means[None, :, :]) ** 2).sum(axis=2)
    assert dist[1, 0] == dist[1, 1]
    nearest = np.argmin(dist, axis=1)
    assert state.view.tolist() == np.flatnonzero(nearest == nearest[0]).tolist()


def test_notes_in_view_are_eval_notes_and_fitting_uses_fit_notes_only(monkeypatch):
    rng = np.random.default_rng(7)
    corpus = _random_corpus(rng, n=60)
    fit_rows = {row.tobytes() for row in corpus.fit}
    eval_rows = {row.tobytes() for row in corpus.ev}
    assert not fit_rows & eval_rows
    fitted, shown = [], []
    original_frame, original_lloyd, original_display = zoom.frame, zoom.lloyd, zoom.display

    def frame(p, points):
        fitted.append(points)
        return original_frame(p, points)

    def lloyd(x, p):
        fitted.append(x)
        return original_lloyd(x, p)

    def display(p, basis, points):
        shown.append(points)
        return original_display(p, basis, points)

    monkeypatch.setattr(zoom, "frame", frame)
    monkeypatch.setattr(zoom, "lloyd", lloyd)
    monkeypatch.setattr(zoom, "display", display)
    a = corpus.fit.mean(axis=0)
    for q in range(len(corpus.ev)):
        zoom.level0(corpus, a)
        zoom.level1(corpus, (a + corpus.ev[q]) / 2.0)
        zoom.level2(corpus, corpus.ev[q])
    assert fitted and shown
    assert all(row.tobytes() in fit_rows for points in fitted for row in points)
    assert all(row.tobytes() in eval_rows for points in shown for row in points)


def test_a_degenerate_state_has_no_display_is_not_scored_and_is_written_as_null():
    fit = np.zeros((4, 8))
    fit[:, 0] = [0.9, 0.2, 0.2, 0.2]
    fit[:, 1] = [0.1, 0.8, 0.6, 0.4]
    ev = np.zeros((4, 8))
    ev[:, 0] = [0.95, 0.9, 0.3, 0.2]
    ev[:, 1] = [0.1, 0.2, 0.7, 0.6]
    corpus = _corpus(fit, ev)
    lonely = zoom.level1(corpus, corpus.ev[0])
    assert len(lonely.fit_view) == 1 and len(lonely.view) == 2
    collinear = zoom.level1(corpus, np.array([0.2, 0.5, 0, 0, 0, 0, 0, 0.0]))
    assert len(collinear.fit_view) == 3
    for state in (lonely, collinear):
        assert state.degenerate and state.display is None and state.eigen_gap is None
        assert zoom.score_state(state, corpus.ranks) is None
        record = zoom.state_record(state, None)
        assert record == {"n_m": len(state.view), "degenerate": True, "eigen_gap": None, "auc": None}
        json.dumps(record, allow_nan=False)


def test_a_state_with_a_frame_displays_its_eval_notes_on_the_two_leading_eigenvectors():
    rng = np.random.default_rng(11)
    corpus = _random_corpus(rng, n=60)
    p = corpus.fit.mean(axis=0)
    state = zoom.level0(corpus, p)
    x = corpus.fit - p
    omega, vectors = np.linalg.eigh(0.5 * x.T @ x)
    basis = vectors[:, ::-1][:, :2]
    assert np.allclose(np.abs(state.display), np.abs((corpus.ev - p) @ basis), rtol=0.0, atol=1e-12)
    assert zoom.state_record(state, 0.25)["eigen_gap"] == pytest.approx((omega[-2] - omega[-3]) / omega[-1])


# Score (D25; Z.md, Z1's score) --------------------------------------------------------------------


def _direct_r(gamma, display, view, n_u):
    """R_j(K) by a direct count of the two neighbour sets, ties to the lower index."""
    n_c = n_u - 1
    rows = []
    for pos, j in enumerate(view):
        hyp = sorted((i for i in range(n_u) if i != j), key=lambda i: (-gamma[j, i], i))
        dist = {
            int(view[t]): math.dist(display[t], display[pos]) for t in range(len(view)) if t != pos
        }
        shown = sorted(dist, key=lambda i: (dist[i], i))
        row = []
        for k in range(1, n_u - 1):
            k_prime = min(k, len(view) - 1)
            overlap = len(set(hyp[:k]) & set(shown[:k_prime]))
            row.append((overlap / k - k_prime / n_c) / (1 - k_prime / n_c))
        rows.append(row)
    return np.array(rows)


def test_the_score_is_its_definition_by_a_direct_count_with_ties_and_a_view_smaller_than_k_plus_1():
    n_u = 7
    index = np.arange(n_u)
    gamma = -np.abs(index[:, None] - index[None, :]).astype(float)
    ranks = zoom.hyp_ranks(gamma)
    view = np.array([0, 2, 3, 5, 6])
    display = np.array([[0.0, 0.0], [1.0, 0.0], [-1.0, 0.0], [0.0, 1.0], [2.0, 0.0]])
    r = zoom.score_orders(zoom.display_orders(display, view), view, ranks, n_u)
    expected = _direct_r(gamma, display, view, n_u)
    assert np.allclose(r, expected, rtol=0.0, atol=1e-12)
    state = zoom.State(np.zeros(8), np.arange(3), view, display, 0.5)
    auc, r_nx = zoom.score_state(state, ranks)
    weights = 1.0 / np.arange(1, n_u - 1)
    assert np.allclose(r_nx, expected.mean(axis=0), rtol=0.0, atol=1e-12)
    assert auc == pytest.approx(float(expected.mean(axis=0) @ weights / weights.sum()), abs=1e-12)


def test_a_note_never_appears_in_its_own_neighbour_lists():
    display = np.zeros((4, 2))
    for pos in range(4):
        order = zoom.shown_order(display, pos)
        assert pos not in order.tolist() and sorted(order.tolist()) == [p for p in range(4) if p != pos]
    ranks = zoom.hyp_ranks(np.ones((5, 5)))
    for j in range(5):
        assert ranks[j, j] == 5 and sorted(ranks[j].tolist()) == [1, 2, 3, 4, 5]
    view = np.array([1, 3, 4])
    for pos, order in enumerate(zoom.display_orders(np.zeros((3, 2)), view)):
        assert view[pos] not in order.tolist()


@pytest.mark.parametrize(
    ("diff", "expected"),
    [
        ([1.0, 2.0, -1.0, 0.0, -3.0, 4.0, 0.0, 0.0, 5.0, -2.0], [3, 6, 10]),
        ([0.0, 0.0, -1.0, -2.0], []),
        ([0.0, 1.0, 0.0, -1.0], [4]),
        ([-1.0, 1.0, -1.0], [2, 3]),
    ],
)
def test_crossings_are_the_scales_where_the_sign_of_the_difference_changes(diff, expected):
    assert zoom.crossings(np.array(diff)) == expected


# Constants, pins, grid, bootstrap and decision rules ---------------------------------------------

# The first three entries of rng.permutation(N_c), numpy.random.default_rng(seed), numpy 2.4.1:
# N_c = 1,109 for the real run (20260924), 167 for the known world (20260925). Pins the streams
# (NEP 19 does not guarantee them across numpy versions).
RECORDED_FIRST_PERMUTATION = {20260924: (948, 430, 156), 20260925: (152, 126, 30)}


def test_constants_seeds_pins_and_paths_are_the_records():
    assert (zoom.SEED, zoom.KNOWN_SEED) == (20260924, 20260925)
    assert (zoom.GRID, zoom.MIN_BLOCKS, zoom.N_BOOT) == ((1, 2, 5, 10, 20, 50), 20, 10_000)
    assert (zoom.INTERVAL_RANKS, zoom.MC_RANKS) == ((249, 9749), (233, 265, 9733, 9765))
    assert (zoom.N_NODES, zoom.N_NODES_CONTROL, zoom.C_ARM) == (64, 128, 1e-4)
    assert (zoom.MAX_ITERATIONS, zoom.LLOYD_CAP, zoom.TIE_TOL) == (100, 1000, 1e-12)
    assert (zoom.N_FRAMES, zoom.N_WARMUP, zoom.N_TIMER, zoom.READY_LIMIT_NS) == (60, 10, 1000, 10**8)
    assert zoom.K6_SHA256 == "6289c596792154f6bb799606265c68719c6b8c7ae8b69084116dfb23c77876d2"
    assert zoom.EXPECTED_DIGESTS == {
        zoom.EMBEDDINGS: "eafb0e97172830f2404e96fa08d74bf6cccc0b6cbe84d47b790a476603e7d8d1",
        zoom.LABELS: "1d60699353d810f089730c6203ee28f9c416e3004b60781bc965cec284097f4f",
        zoom.AXES: "b14e5d6700d1a7478a357ca26f0f38f5240f97a42daad45722d21f1c3f964e35",
    }
    assert zoom.RESULT == zoom.REPO_ROOT / "data" / "refapp" / "Z_result.json"
    assert zoom.CONDITIONS == (
        "null_world", "tube_defined", "search_converged", "search_code", "lloyd_converged",
        "n_scored", "arms_share_start_end", "identity", "permutation", "quadrature",
        "search_reproduced",
    )
    assert 4.0 / math.sqrt(1110 * 1108) == pytest.approx(0.003607, abs=5e-7)
    assert 4.0 / math.sqrt(168 * 166) == pytest.approx(0.0240, abs=5e-5)


def test_the_k6_module_file_imported_is_the_pinned_one():
    assert zoom.K6_FILE == Path(k6.__file__)
    assert hashlib.sha256(zoom.K6_FILE.read_bytes()).hexdigest() == zoom.K6_SHA256


def test_the_script_sets_the_thread_variables_before_its_first_numpy_import():
    source = Path(zoom.__file__).read_text(encoding="utf-8")
    assert source.index('os.environ[_var] = "1"') < source.index("import numpy")
    assert '("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")' in source


def test_the_first_permutation_from_each_seed_matches_recorded_values():
    first = {
        seed: tuple(np.random.default_rng(seed).permutation(n_c)[:3].tolist())
        for seed, n_c in ((20260924, 1109), (20260925, 167))
    }
    assert first == RECORDED_FIRST_PERMUTATION


@pytest.mark.parametrize(
    ("n", "used"),
    [(1110, [1, 2, 5, 10, 20, 50]), (168, [1, 2, 5]), (40, [1, 2]), (20, [1]), (19, [])],
)
def test_block_counts_and_the_filter_of_block_lengths_by_n(n, used):
    assert [zoom.n_blocks(1110, length) for length in zoom.GRID] == [1110, 555, 222, 111, 56, 23]
    assert zoom.lengths_used(n) == used


@pytest.mark.parametrize("length", [1, 5])
def test_the_block_bootstrap_resamples_contiguous_blocks_with_multiplicity(length):
    values = np.arange(23, dtype=float) ** 1.5
    draws = zoom.bootstrap(np.random.default_rng(1), values, length, np.mean)
    rng = np.random.default_rng(1)
    n_blk = zoom.n_blocks(23, length)
    blocks = [values[s : s + length] for s in range(0, 23, length)]
    naive = [
        np.mean(np.concatenate([blocks[i] for i in rng.integers(0, n_blk, n_blk)]))
        for _ in range(zoom.N_BOOT)
    ]
    assert np.allclose(draws, naive, rtol=0.0, atol=1e-12)


def test_the_interval_takes_sorted_ranks_249_and_9749_and_reports_the_monte_carlo_ranks():
    record = zoom.interval_record(np.arange(10_000.0)[::-1])
    assert record["interval"] == [249.0, 9749.0]
    assert record["ranks"] == {"233": 233.0, "265": 265.0, "9733": 9733.0, "9765": 9765.0}


def _z1(*bounds):
    return {str(length): {"interval": list(b)} for length, b in zip(zoom.GRID, bounds)}


@pytest.mark.parametrize(
    ("per_l", "decision"),
    [
        (_z1((-2.0, -1.0), (-3.0, -0.5)), "refuted"),
        (_z1((0.5, 1.0), (0.1, 2.0)), "keeps_more"),
        (_z1((-2.0, -1.0), (-3.0, 0.0)), "inconclusive"),
        (_z1((0.0, 1.0), (0.1, 2.0)), "inconclusive"),
        (_z1((0.0, 0.0), (0.0, 0.0)), "inconclusive"),
        ({}, None),
    ],
)
def test_z1_is_refuted_or_keeps_more_only_at_every_block_length(per_l, decision):
    assert zoom.z1_decision(per_l) == decision


def _z2(*bounds):
    return {
        str(length): {"median_delta": {"interval": list(delta)}, "ready_p95": {"interval": list(ready)}}
        for length, (delta, ready) in zip(zoom.GRID, bounds)
    }


LIMIT = 10**8


@pytest.mark.parametrize(
    ("per_l", "decision"),
    [
        (_z2(((0.0, 5.0), (1.0, 2.0)), ((1.0, 5.0), (1.0, 2.0))), "refuted"),
        (_z2(((-5.0, -1.0), (LIMIT + 1, LIMIT + 9)), ((-5.0, -1.0), (LIMIT + 2, LIMIT + 9))), "refuted"),
        (_z2(((-5.0, -1.0), (1.0, LIMIT)), ((-5.0, -2.0), (1.0, 2.0))), "confirmed"),
        (_z2(((-5.0, -1.0), (1.0, LIMIT + 1)), ((-5.0, -2.0), (1.0, 2.0))), "inconclusive"),
        (_z2(((-5.0, 1.0), (1.0, 2.0)), ((-5.0, -2.0), (1.0, 2.0))), "inconclusive"),
        (_z2(((0.0, 5.0), (1.0, 2.0)), ((-1.0, 5.0), (1.0, 2.0))), "inconclusive"),
        ({}, None),
    ],
)
def test_z2_rule_refutes_confirms_or_stays_inconclusive_at_every_block_length(per_l, decision):
    assert zoom.z2_decision(per_l) == decision


# Controls: identity, permutation, arms_share_start_end, quadrature, tube_defined -----------------


def _structured_world():
    """The known world's construction with one offset per pair: 112 notes, 56 EVAL targets."""
    pairs = list(itertools.combinations(range(8), 2))
    golden = (math.sqrt(5.0) - 1.0) / 2.0
    v = np.zeros((4 * len(pairs), 384))
    for p, (k1, k2) in enumerate(pairs):
        x = (p + 1) * golden
        beta = 0.1 + 0.2 * (x - math.floor(x))
        for r, (first, second) in enumerate(((k1, k2), (k1, k2), (k2, k1), (k2, k1))):
            i = 4 * p + r
            c = np.full(8, 0.1)
            c[first] += beta
            c[second] -= beta
            v[i, :8] = c
            v[i, 8 + i] = math.sqrt(1.0 - c @ c)
    return v, np.eye(8, 384)


@pytest.fixture(scope="module")
def small():
    v, a = _structured_world()
    corpus = zoom.make_corpus(v, a)
    p0 = corpus.fit.mean(axis=0)
    return corpus, p0, zoom.run_targets(corpus, p0, zoom.RULE_64)


def _tie_corpus(delta):
    """EVAL notes e₀, (½, √¾, 0) and (½ + delta, 0, ·): notes 1 and 2 nearly tied for note 0."""
    ev = np.zeros((3, 384))
    ev[0, 0] = 1.0
    ev[1, :2] = [0.5, math.sqrt(0.75)]
    ev[2, [0, 2]] = [0.5 + delta, math.sqrt(1.0 - (0.5 + delta) ** 2)]
    v = np.zeros((6, 384))
    v[0::2, 4:12] = np.eye(3, 8)
    v[1::2] = ev
    return zoom.make_corpus(v, np.eye(8, 384))


def _swap_notes_1_and_2_for_note_0(original):
    def swapped(shown, pos):
        order = original(shown, pos)
        if pos == 0:
            order = order.copy()
            i, k = np.flatnonzero(order == 1)[0], np.flatnonzero(order == 2)[0]
            order[[i, k]] = order[[k, i]]
        return order

    return swapped


def test_identity_holds_on_unit_vectors_and_counts_a_swap_within_tolerance_as_ties(monkeypatch):
    assert zoom.identity_control(_random_corpus(np.random.default_rng(3), n=80)) == {
        "passed": True, "ties": 0,
    }
    assert zoom.identity_control(_tie_corpus(1e-13)) == {"passed": True, "ties": 0}
    monkeypatch.setattr(zoom, "shown_order", _swap_notes_1_and_2_for_note_0(zoom.shown_order))
    assert zoom.identity_control(_tie_corpus(1e-13)) == {"passed": True, "ties": 2}
    assert not zoom.identity_control(_tie_corpus(1e-9))["passed"]


def test_identity_fails_with_a_score_that_counts_j_among_its_own_neighbours(monkeypatch):
    def with_self(shown, pos):
        diff = shown - shown[pos]
        return np.argsort((diff * diff).sum(axis=1), kind="stable")

    monkeypatch.setattr(zoom, "shown_order", with_self)
    assert not zoom.identity_control(_random_corpus(np.random.default_rng(3), n=80))["passed"]


def test_permutation_holds_in_its_band_and_fails_with_the_chance_term_dropped(monkeypatch):
    ranks = _random_corpus(np.random.default_rng(5), n=120).ranks
    held = zoom.permutation_control(np.random.default_rng(zoom.SEED), ranks)
    assert held["passed"] and held["band"] == pytest.approx(4.0 / math.sqrt(60 * 58))
    assert abs(held["auc"]) <= held["band"]
    monkeypatch.setattr(zoom, "r_values", lambda o, n_m, n_u: o / np.arange(1, n_u - 1))
    dropped = zoom.permutation_control(np.random.default_rng(zoom.SEED), ranks)
    assert not dropped["passed"] and dropped["auc"] > 0.1


def test_arms_share_start_end_fails_with_an_arm_dependent_start(monkeypatch, small):
    corpus, a, targets = small
    assert zoom.arms_share_start_end(targets)
    original = zoom.arm_states
    calls = []

    def arm_dependent(corpus, a, middle, b):
        calls.append(1)
        states, found = original(corpus, a, middle, b)
        if len(calls) % 2 == 0:
            states["start"] = dataclasses.replace(states["start"], display=states["start"].display + 1e-12)
        return states, found

    monkeypatch.setattr(zoom, "arm_states", arm_dependent)
    moved = [zoom.run_target(corpus, a, pos, zoom.RULE_64, {}) for pos in range(2)]
    assert not zoom.arms_share_start_end(moved)


def test_quadrature_holds_and_fails_with_a_changed_decision(monkeypatch, small):
    corpus, _, targets = small
    _, d_q = zoom.d_q_of(targets)
    rng = np.random.default_rng(zoom.SEED)
    state = rng.bit_generator.state
    levels = {length: zoom.z1_level(r) for length, r in zoom.z1_per_l(rng, d_q).items()}
    assert levels and "keeps_more" not in levels.values()
    held = zoom.quadrature_control(corpus, targets, state, levels, zoom.RULE_128)
    assert held["passed"]
    original = zoom.score_state

    def lowered(state, ranks):
        scored = original(state, ranks)
        return None if scored is None else (scored[0] - 0.5, scored[1])

    monkeypatch.setattr(zoom, "score_state", lowered)
    changed = zoom.quadrature_control(corpus, targets, state, levels, zoom.RULE_128)
    assert not changed["passed"]
    assert changed["changed"] == len(d_q)
    assert {d["128"] for d in changed["decisions"].values()} == {"keeps_more"}


def test_tube_defined_fails_for_a_target_at_d_of_at_least_4_root_2():
    fit = np.full((4, 8), 0.1)
    fit[:, 0] = [0.2, 0.3, 0.4, 0.5]
    ev = np.full((4, 8), 0.1)
    ev[:, 1] = [0.2, 0.3, 0.4, 0.5]
    ev[3] = 3.0 * np.array([1.0, -1.0, 1.0, -1.0, 1.0, -1.0, 1.0, -1.0])
    corpus = _corpus(fit, ev)
    targets = zoom.run_targets(corpus, corpus.fit.mean(axis=0), zoom.RULE_64)
    assert targets[3].d >= zoom.TUBE and targets[3].search is None
    assert all(t.d < zoom.TUBE for t in targets[:3])
    assert zoom.target_conditions(targets)["tube_defined"] is False


# The known world (Z.md, Controls, null_world; D26) ----------------------------------------------


def test_the_known_world_meets_d26s_conditions_with_84_distinct_offsets():
    v, a = zoom.known_world()
    assert v.shape == (336, 384) and np.array_equal(a, np.eye(8, 384))
    assert np.allclose(np.linalg.norm(v, axis=1), 1.0, rtol=0.0, atol=1e-15)
    assert np.array_equal(np.flatnonzero(v[:, 8:]) % 376, np.arange(336))
    c = v[:, :8]
    fit, ev = c[0::2], c[1::2]
    p0 = fit.mean(axis=0)
    assert np.allclose(p0, 0.1, rtol=0.0, atol=1e-12)
    for b in ev:
        assert abs(float((b - p0).sum())) <= 1e-12 and np.linalg.norm(b - p0) > 0.1
    betas = c[0::4].max(axis=1) - 0.1
    assert len(set(np.round(betas, 12).tolist())) == 84 and np.all((betas > 0.1) & (betas < 0.3))
    pairs = [tuple(sorted((int(np.argmax(row)), int(np.argmin(row))))) for row in c[0::4]]
    assert pairs == [p for p in itertools.combinations(range(8), 2) for _ in range(3)]
    for block in range(84):
        rows = c[4 * block : 4 * block + 4]
        assert np.array_equal(rows[0], rows[1]) and np.array_equal(rows[2], rows[3])
        assert np.array_equal(np.sort(rows[0]), np.sort(rows[2]))
    assert np.bincount(np.argmax(ev, axis=1), minlength=8).tolist() == [21] * 8


def test_no_pair_in_the_known_world_has_its_three_offsets_equally_spaced():
    v, _ = zoom.known_world()
    triples = (v[0::4, :8].max(axis=1) - 0.1).reshape(28, 3)
    spread = np.abs(2.0 * triples - np.roll(triples, 1, axis=1) - np.roll(triples, 2, axis=1))
    assert {p: float(row.min()) for p, row in enumerate(spread) if row.min() < 5.0e-3} == {}


@pytest.fixture(scope="module")
def known():
    return zoom.null_world()


def test_the_null_world_passes(known):
    assert known["passed"]
    assert known["all_d_q_zero"] and known["searches_without_step"] and known["middles_scored"]
    assert known["decisions"] == {"1": "inconclusive", "2": "inconclusive", "5": "inconclusive"}
    assert list(known["conditions"]) == list(zoom.CONDITIONS[1:-1])
    assert all(known["conditions"].values())
    gap = known["smallest_relative_display_gap"]
    assert isinstance(gap, float) and 0.0 < gap < 1.0
    json.dumps(known, allow_nan=False)


def test_the_null_world_fails_with_an_arm_dependent_search(monkeypatch):
    original = zoom.search

    def arm_dependent(line, rule):
        found = original(line, rule)
        return dataclasses.replace(found, point=zoom.evaluate(line, np.full(7, 1e-3), rule), iterations=1)

    monkeypatch.setattr(zoom, "search", arm_dependent)
    world = zoom.null_world()
    assert not world["passed"] and not world["searches_without_step"]


# Draws (Z.md, Draws) ------------------------------------------------------------------------------


class _Recorder:
    def __init__(self, seed):
        self.rng = np.random.default_rng(seed)
        self.log = []

    @property
    def bit_generator(self):
        return self.rng.bit_generator

    def permutation(self, n):
        self.log.append(("permutation", n))
        return self.rng.permutation(n)

    def integers(self, low, high, size):
        self.log.append(("integers", high, size))
        return self.rng.integers(low, high, size)


def test_draws_come_in_the_records_order():
    v, a = _structured_world()
    recorder = _Recorder(zoom.SEED)
    measured = zoom.measure(v, a, recorder)
    n_u, n = len(v) // 2, len(measured.d_q)
    expected = [("permutation", n_u - 1)] * n_u
    for length in zoom.lengths_used(n):
        expected += [("integers", zoom.n_blocks(n, length), zoom.n_blocks(n, length))] * zoom.N_BOOT
    assert recorder.log == expected
    recorder = _Recorder(zoom.SEED)
    zoom.z2_statistics(recorder, np.arange(40.0), np.arange(40.0))
    blocks = [zoom.n_blocks(40, length) for length in zoom.lengths_used(40)]
    assert recorder.log == [("integers", b, b) for b in blocks * 2 for _ in range(zoom.N_BOOT)]


# Z2 mechanics (no assertion on wall-clock values) ------------------------------------------------


class _Clock:
    """A clock that advances by `step` at every reading."""

    def __init__(self, step=10):
        self.now = 0
        self.step = step

    def __call__(self):
        self.now += self.step
        return self.now


def test_z2_subtracts_the_timer_overhead_from_every_timing(monkeypatch, small):
    corpus, a, targets = small
    monkeypatch.setattr(zoom, "N_WARMUP", 2)
    passed = zoom.z2_pass(corpus, a, targets[:4], zoom.RULE_64, _Clock())
    assert passed.overhead == 10
    assert passed.delta.tolist() == [10.0] * 4
    assert passed.ready.tolist() == [0.0] * 4
    assert passed.reproduced


def test_z2_interleaves_the_arms_keyframes_first_at_even_positions_of_eval_order(monkeypatch, small):
    corpus, a, targets = small
    monkeypatch.setattr(zoom, "N_WARMUP", 0)
    calls = []
    for name in ("keyframes_arm", "per_step_arm"):
        original = getattr(zoom, name)

        def recording(*args, _name=name, _original=original):
            calls.append(_name)
            return _original(*args)

        monkeypatch.setattr(zoom, name, recording)
    zoom.z2_pass(corpus, a, targets[:5], zoom.RULE_64, _Clock())
    expected = []
    for t in targets[:5]:
        pair = ["keyframes_arm", "per_step_arm"]
        expected += pair if t.pos % 2 == 0 else pair[::-1]
    assert calls == expected


def test_search_reproduced_fails_when_the_timed_search_finds_another_m(monkeypatch, small):
    corpus, a, targets = small
    monkeypatch.setattr(zoom, "N_WARMUP", 0)
    original = zoom.search
    monkeypatch.setattr(
        zoom,
        "search",
        lambda line, rule: dataclasses.replace(
            original(line, rule), point=zoom.evaluate(line, np.full(7, 1e-3), rule)
        ),
    )
    assert not zoom.z2_pass(corpus, a, targets[:3], zoom.RULE_64, _Clock()).reproduced


def test_keyframes_interpolate_in_view_notes_and_keep_a_note_shown_in_one_display_only():
    prev = (np.array([[0.0, 0.0], [2.0, 2.0], [0.0, 0.0]]), np.array([True, True, False]))
    nxt = (np.array([[4.0, 0.0], [0.0, 0.0], [1.0, 1.0]]), np.array([True, False, True]))
    notes, positions = zoom.interpolate(prev, nxt, 0.25)
    assert notes.tolist() == [0, 1, 2]
    assert positions.tolist() == [[1.0, 0.0], [2.0, 2.0], [1.0, 1.0]]
    times = zoom.frame_times()
    assert len(times) == 60 and times[0] == 0.0 and times[-1] == 1.0
    a, m, b = np.zeros(8), np.ones(8), 3.0 * np.ones(8)
    assert np.array_equal(zoom.route_point(a, m, b, 0.25), 0.5 * np.ones(8))
    assert np.array_equal(zoom.route_point(a, m, b, 0.75), 2.0 * np.ones(8))


# run(): order, refusals, result file (contracts.md §0 and §4) --------------------------------------


def _write_inputs(tmp_path, corrupt=None):
    v, a = _structured_world()
    v32 = v.astype(np.float32)
    labels = [{"label": f"L{i}", "part": "P1"} for i in range(len(v))]
    axes = [{"id": f"AXIS_{k}", "simbolo": "s", "tag": "t", "vector": row.tolist()} for k, row in enumerate(a)]
    if corrupt is not None:
        corrupt(v32, labels, axes)
    paths = (tmp_path / "embeddings.npy", tmp_path / "labels.json", tmp_path / "nsm_axes_8.json")
    np.save(paths[0], v32)
    paths[1].write_text(json.dumps(labels), encoding="utf-8")
    paths[2].write_text(json.dumps(axes), encoding="utf-8")
    return paths, {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def _flip_file_bit(path, pos, bit):
    data = bytearray(path.read_bytes())
    data[pos] ^= 1 << bit
    path.write_bytes(bytes(data))


@pytest.fixture
def world_calls(monkeypatch):
    calls = []

    def passing():
        calls.append(1)
        return {"passed": True}

    monkeypatch.setattr(zoom, "null_world", passing)
    return calls


def _sections():
    return {
        "targets": [], "z1": {"decision": "inconclusive"}, "controls": {},
        "z2": {"decision": "confirmed"}, "counts": {}, "reported": {},
    }


@pytest.fixture
def fake_measure(monkeypatch):
    seen = {}

    def measure(v, a, rng, clock=None):
        seen.update(v=v, a=a, state=rng.bit_generator.state, clock=clock)
        conditions = {c: True for c in zoom.CONDITIONS[1:]}
        conditions.update(seen.get("failing", {}))
        return zoom.Measurement(_sections(), conditions, [], np.zeros(0), {})

    monkeypatch.setattr(zoom, "measure", measure)
    return seen


def test_a_single_bit_flip_in_the_k6_module_file_is_refused_before_the_known_world(
    tmp_path, world_calls, fake_measure
):
    copy = tmp_path / "k6_colour_predictability.py"
    copy.write_bytes(zoom.K6_FILE.read_bytes())
    paths, expected = _write_inputs(tmp_path)
    zoom.run(copy, *paths, expected, tmp_path / "intact.json")
    world_calls.clear()
    out = tmp_path / "out" / "Z_result.json"
    rng = np.random.default_rng(0)
    size = copy.stat().st_size
    for pos in sorted({0, size - 1, int(rng.integers(0, size))}):
        original = copy.read_bytes()
        _flip_file_bit(copy, pos, int(rng.integers(0, 8)))
        with pytest.raises(k6.IntegrityError, match=copy.name):
            zoom.run(copy, *paths, expected, out)
        copy.write_bytes(original)
    assert not out.parent.exists() and not world_calls


def test_a_single_bit_flip_in_any_data_file_is_refused_after_the_known_world(
    tmp_path, world_calls, fake_measure
):
    paths, expected = _write_inputs(tmp_path)
    out = tmp_path / "out" / "Z_result.json"
    rng = np.random.default_rng(1)
    header = paths[0].read_bytes()
    data_start = 10 + int.from_bytes(header[8:10], "little")
    for path in paths:
        size = path.stat().st_size
        positions = {0, size - 1, int(rng.integers(0, size))}
        if path == paths[0]:
            positions |= {20, data_start}
        for pos in sorted(positions):
            original = path.read_bytes()
            _flip_file_bit(path, pos, int(rng.integers(0, 8)))
            with pytest.raises(k6.IntegrityError, match=path.name):
                zoom.run(zoom.K6_FILE, *paths, expected, out)
            path.write_bytes(original)
    assert not out.parent.exists() and "v" not in fake_measure and world_calls


def test_main_refuses_a_nan_row_through_validate_inputs_and_writes_nothing(
    tmp_path, monkeypatch, world_calls, fake_measure
):
    paths, expected = _write_inputs(tmp_path, corrupt=lambda v, lab, ax: v.__setitem__((2, 5), np.nan))
    for name, path in zip(("EMBEDDINGS", "LABELS", "AXES"), paths):
        monkeypatch.setattr(zoom, name, path)
    monkeypatch.setattr(zoom, "EXPECTED_DIGESTS", expected)
    out = tmp_path / "out" / "Z_result.json"
    with pytest.raises(ValueError, match="row 2: non-finite"):
        zoom.main(["--out", str(out)])
    assert not out.parent.exists() and "v" not in fake_measure


def test_a_known_world_failure_writes_nulls_and_never_reads_the_artefacts(tmp_path, monkeypatch):
    failed = {"passed": False, "all_d_q_zero": False}
    monkeypatch.setattr(zoom, "null_world", lambda: failed)
    read = []
    original = k6.check_digests
    monkeypatch.setattr(k6, "check_digests", lambda expected: read.append(dict(expected)) or original(expected))
    paths, expected = _write_inputs(tmp_path)
    out = tmp_path / "Z_result.json"
    result = zoom.run(zoom.K6_FILE, *paths, expected, out)
    assert read == [{zoom.K6_FILE: zoom.K6_SHA256}]
    assert result["valid"] is False and result["first_failed_condition"] == "null_world"
    assert result["failed_conditions"] == result["conditions_checked"] == ["null_world"]
    assert result["null_world"] == failed
    assert result["digests"] == {
        zoom.K6_FILE.name: zoom.K6_SHA256, "embeddings.npy": None, "labels.json": None,
        "nsm_axes_8.json": None,
    }
    assert all(result[key] is None for key in ("targets", "z1", "controls", "z2", "counts", "reported"))


def test_any_other_failed_condition_writes_valid_false_and_withholds_both_decisions(
    tmp_path, world_calls, fake_measure
):
    fake_measure["failing"] = {"identity": False, "quadrature": False}
    paths, expected = _write_inputs(tmp_path)
    result = zoom.run(zoom.K6_FILE, *paths, expected, tmp_path / "Z_result.json")
    assert result["valid"] is False and result["first_failed_condition"] == "identity"
    assert result["failed_conditions"] == ["identity", "quadrature"]
    assert result["conditions_checked"] == list(zoom.CONDITIONS)
    assert result["z1"]["decision"] is None and result["z2"]["decision"] is None
    assert fake_measure["state"] == np.random.default_rng(zoom.SEED).bit_generator.state
    assert fake_measure["clock"] is not None


def test_a_valid_run_writes_every_key_of_the_contract_in_the_result_format(tmp_path, world_calls):
    paths, expected = _write_inputs(tmp_path)
    out = tmp_path / "out" / "Z_result.json"
    result = zoom.run(zoom.K6_FILE, *paths, expected, out)
    text = out.read_text(encoding="utf-8")
    assert text == json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n"
    assert set(result) == {
        "digests", "environment", "valid", "first_failed_condition", "failed_conditions",
        "conditions_checked", "null_world", "targets", "z1", "controls", "z2", "counts", "reported",
    }
    assert result["valid"] is True and result["failed_conditions"] == []
    assert result["conditions_checked"] == list(zoom.CONDITIONS)
    assert result["digests"] == {zoom.K6_FILE.name: zoom.K6_SHA256, **{p.name: expected[p] for p in paths}}
    assert result["environment"]["threads"] == dict.fromkeys(
        ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"), "1"
    )
    assert {"platform", "numpy", "numpy_config"} <= set(result["environment"])
    targets = result["targets"]
    assert [t["index"] for t in targets] == list(range(1, 112, 2))
    assert set(targets[0]) == {
        "index", "d", "excluded", "search", "arms", "tau_2", "tau_3", "m_minus_m0_norm", "crossings",
        "lloyd",
    }
    assert set(targets[0]["search"]) == {
        "stop", "iterations", "decrement", "theta", "nu_g", "mu_hat", "h_over_hmax", "slope", "abs_e",
        "xi", "rho_pt", "fallback_steps",
    }
    assert set(targets[0]["arms"]) == {"two_point", "three_point"}
    assert set(targets[0]["arms"]["three_point"]) == {
        "k_star", "argmax_margin", "rho", "n_m", "degenerate", "eigen_gap", "auc",
    }
    assert set(targets[0]["arms"]["two_point"]["auc"]) == {"start", "middle", "end"}
    assert set(targets[0]["lloyd"]) == {"iterations", "cells"}
    z1 = result["z1"]
    assert set(z1) == {"n", "per_l", "d_bar_cells_agree", "decision"} and z1["decision"] is not None
    assert set(z1["per_l"]) == {"1", "2"}
    assert set(z1["per_l"]["1"]) == {"n_blocks", "d_bar", "interval", "margins", "ranks"}
    controls = result["controls"]
    assert set(controls) == {"identity", "permutation", "arms_share_start_end", "quadrature"}
    assert set(controls["identity"]) == {"passed", "ties"}
    assert set(controls["permutation"]) == {"auc", "band", "passed"}
    assert set(controls["quadrature"]) == {"passed", "decisions", "changed", "abs_e_128", "grad_norm_128"}
    z2 = result["z2"]
    assert set(z2) == {"timer_overhead_ns", "n", "median_delta_ns", "ready_p95_ns", "per_l", "decision"}
    assert z2["n"] == 56 and z2["decision"] is not None
    assert set(z2["per_l"]["1"]) == {"n_blocks", "median_delta", "ready_p95"}
    assert set(z2["per_l"]["1"]["median_delta"]) == {"interval", "margins"}
    assert set(result["counts"]) == {
        "excluded", "degenerate", "not_scored", "near_zero_eigen_gap", "failed_searches",
        "fallback_steps", "mu_hat_ge_1", "margin_below_2rho",
    }
    assert set(result["reported"]) == {
        "score_mean", "middle_cells_differ", "crossings", "tau_ratio", "start_leading_direction",
        "axis_norms", "smallest_d",
    }
    assert result["reported"]["axis_norms"] == [1.0] * 8
