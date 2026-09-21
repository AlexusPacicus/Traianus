"""Unit tests of tools/experiments/r4_perspective_recall.py.

Specification: frontend/audits/R4.md (revision 5), frontend/audits/contracts.md section 0 and 2,
frontend/audits/derivations.md (D2, D5, D6, D9, D10). Synthetic inputs only: CI has no .data/,
and the measurement is never run on the real artefact here.
"""

import hashlib
import json
import os
from pathlib import Path

import numpy as np
import pytest

from tools.experiments import k6_colour_predictability as k6
from tools.experiments import r4_perspective_recall as r4
from traianus.geometry.perspective import observe as real_observe

D = 384
GRID = (1, 2, 5, 10, 20, 50)

# The first three rows e_1..e_3 of rng.standard_normal((200, 384)), Generator(PCG64(20260918)),
# numpy 2.4.1. Component 0 is K6's recorded g_1..g_3 (same seed, same stream); component 383
# pins the row-major layout. Pins the stream (NEP 19 does not guarantee it across versions).
RECORDED_E_FIRST = (-1.4765772923017222, 0.21292362335480605, -0.5764113739053777)
RECORDED_E_LAST = (0.36627402697443834, -1.2203019637924908, 0.19564922038438043)


def _unit_rows(rng, n, d=D):
    x = rng.standard_normal((n, d))
    return x / np.linalg.norm(x, axis=1, keepdims=True)


def _unit_rows_f32(rng, n, d=D):
    x = rng.standard_normal((n, d)).astype(np.float32)
    return x / np.linalg.norm(x, axis=1, keepdims=True).astype(np.float32)


def _labels(n):
    return [{'label': f'L{i}', 'part': 'P1'} for i in range(n)]


def _axis_ids():
    return [f'AXIS_{k}' for k in range(1, 9)]


def _axes_json(a):
    return [
        {'id': i, 'simbolo': 's', 'tag': 't', 'vector': row.tolist()}
        for i, row in zip(_axis_ids(), a)
    ]


@pytest.fixture
def rng():
    return np.random.default_rng(12345)


# Constants, digests, grid, interval -------------------------------------------------------------


def test_constants_are_the_records():
    assert (r4.K, r4.KS) == (15, (5, 15, 50))
    assert (r4.N_DIRECTIONS, r4.N_RESAMPLES) == (200, 10_000)
    assert r4.GRID == GRID and r4.MIN_BLOCKS == 20
    assert r4.TIE_TOL == 1e-12 and r4.NEAR_DUPLICATE_TOL == 1e-12
    assert r4.PERMUTATION_BAND == (0.149, 0.257)
    assert r4.SEED == 20260918


def test_expected_digests_are_k6s_three_and_the_pinned_k6_result():
    assert r4.EXPECTED_DIGESTS == {
        r4.EMBEDDINGS: 'eafb0e97172830f2404e96fa08d74bf6cccc0b6cbe84d47b790a476603e7d8d1',
        r4.LABELS: '1d60699353d810f089730c6203ee28f9c416e3004b60781bc965cec284097f4f',
        r4.AXES: 'b14e5d6700d1a7478a357ca26f0f38f5240f97a42daad45722d21f1c3f964e35',
        r4.K6_RESULT: 'a95ec2a01a14f9638c9fc01d1bc9f198f5c53e580636858a7690baf9539cac58',
    }
    assert r4.K6_RESULT.name == 'K6_result.json' and r4.RESULT.name == 'R4_result.json'


def test_grid_block_counts_leave_at_least_twenty_blocks_up_to_50():
    counts = {length: r4.n_blocks(1110, length) for length in r4.GRID}
    assert counts == {1: 1110, 2: 555, 5: 222, 10: 111, 20: 56, 50: 23}
    assert min(counts.values()) >= r4.MIN_BLOCKS
    assert r4.n_blocks(1110, 100) == 12 < r4.MIN_BLOCKS


def test_blocks_are_contiguous_in_index_order_and_the_last_may_be_shorter():
    starts = r4.block_starts(1110, 50)
    assert len(starts) == 23 and starts[0] == 0 and starts[-1] == 1100
    assert np.diff(np.append(starts, 1110)).tolist() == [50] * 22 + [10]
    assert r4.block_starts(6, 3).tolist() == [0, 3]


def test_interval_takes_sorted_positions_249_and_9749_with_their_monte_carlo_neighbours(rng):
    out = r4.interval(rng.permutation(10_000).astype(np.float64))
    assert (out['lo'], out['hi']) == (249.0, 9749.0)
    assert out['lo_neighbours'] == [233.0, 265.0]
    assert out['hi_neighbours'] == [9733.0, 9765.0]


def test_decision_needs_every_upper_bound_below_zero():
    per = {'1': {'hi': -0.5}, '2': {'hi': -0.1}}
    assert r4.decide(per) == (True, -0.1)
    per['5'] = {'hi': 0.0}
    assert r4.decide(per) == (False, 0.0)
    per['5'] = {'hi': 0.2}
    assert r4.decide(per) == (False, 0.2)


# Random streams ---------------------------------------------------------------------------------


def test_first_three_e_j_match_recorded_values():
    e = r4.draw_directions(k6.make_rng(), r4.N_DIRECTIONS, D)
    assert e.shape == (200, D)
    assert tuple(e[:3, 0]) == pytest.approx(RECORDED_E_FIRST, rel=1e-12, abs=0.0)
    assert tuple(e[:3, -1]) == pytest.approx(RECORDED_E_LAST, rel=1e-12, abs=0.0)
    assert np.array_equal(e[:3], k6.draw_deciding_null(k6.make_rng(), 3, D))


def test_sigma_bank_is_the_centred_eval_matrix_transposed_times_f_over_root_n(rng):
    v = _unit_rows(rng, 30)
    f = r4.draw_sigma_weights(k6.make_rng(), 5, 30)
    assert f.shape == (5, 30)
    g = r4.sigma_bank(f, v)
    x_c = v - v.mean(axis=0)
    assert g.shape == (5, D)
    for j in range(5):
        assert np.allclose(g[j], x_c.T @ f[j] / np.sqrt(30), rtol=0, atol=1e-12)


def test_random_directions_are_unit_and_orthogonal_to_q(rng):
    q_hat = _unit_rows(rng, 1)[0]
    bank = rng.standard_normal((6, D))
    u = r4.random_directions(bank, q_hat)
    assert np.allclose(np.linalg.norm(u, axis=1), 1.0, rtol=0, atol=1e-12)
    assert np.allclose(u @ q_hat, 0.0, rtol=0, atol=1e-12)
    p = bank[2] - (bank[2] @ q_hat) * q_hat
    assert np.allclose(u[2], p / np.linalg.norm(p), rtol=0, atol=1e-12)


# Neighbour lists and recall ---------------------------------------------------------------------


def test_ground_truth_neighbours_exclude_q_take_the_largest_and_break_ties_by_lower_index():
    g = np.array([0.5, 1.0, 0.9, 0.9, 0.7, 0.9, 0.1])
    assert r4.ground_truth_neighbours(g, 1, 6).tolist() == [2, 3, 5, 4, 0, 6]
    assert r4.ground_truth_neighbours(g, 1, 3).tolist() == [2, 3, 5]
    assert r4.ground_truth_neighbours(g, 6, 3).tolist() == [1, 2, 3]


def test_observed_neighbours_are_euclidean_exclude_q_and_break_ties_by_lower_index():
    obs = np.array(
        [[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [-1.0, 0.0], [0.0, -1.0], [2.0, 0.0], [0.0, 0.0]]
    )
    assert r4.observed_neighbours(obs, 0, 6).tolist() == [6, 1, 2, 3, 4, 5]
    assert r4.observed_neighbours(obs, 0, 3).tolist() == [6, 1, 2]
    assert r4.observed_neighbours(obs[:, :1], 0, 6).tolist() == [2, 4, 6, 1, 3, 5]


def test_a_shorter_list_is_the_prefix_of_a_longer_one(rng):
    obs = np.round(rng.standard_normal((80, 3)), 1)
    longer = r4.observed_neighbours(obs, 9, 50)
    assert longer[:15].tolist() == r4.observed_neighbours(obs, 9, 15).tolist()
    assert longer[:5].tolist() == r4.observed_neighbours(obs, 9, 5).tolist()


def test_q_is_in_neither_list_even_when_it_is_the_nearest_and_the_most_similar(rng):
    v = _unit_rows(rng, 70)
    for q in range(70):
        assert q not in r4.ground_truth_neighbours(v @ v[q], q, 50)
        assert q not in r4.observed_neighbours(v, q, 50)
        assert q not in r4.observed_neighbours(v[:, :1], q, 50)


def test_permutation_neighbours_index_into_the_other_notes_in_index_order(rng):
    out = r4.permutation_neighbours(np.arange(19), 3, 15)
    assert out.tolist() == [0, 1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
    assert r4.permutation_neighbours(np.arange(19)[::-1], 3, 4).tolist() == [19, 18, 17, 16]
    for q in range(20):
        assert q not in r4.permutation_neighbours(rng.permutation(19), q, 15)


def test_truth_masks_and_recall_count_the_overlap():
    truth = np.arange(1, 51)
    masks = r4.truth_masks(truth, 60)
    assert masks.shape == (3, 60) and masks.dtype == np.bool_
    assert masks.sum(axis=1).tolist() == [5, 15, 50]
    found = np.array([1, 2, 3, 40, 41])
    assert r4.recall(masks[1], found) == 3
    assert r4.recall(masks[2], found) == 5
    assert r4.recall(masks[0], np.array([9, 10])) == 0


def _naive_recalls(v, q, extra, h):
    n = len(v)
    others = [j for j in range(n) if j != q]
    q_hat = v[q] / np.linalg.norm(v[q])
    raw = [v @ h, v @ q_hat, *extra]
    z = np.column_stack([(c - np.mean(c[others])) / np.std(c[others]) for c in raw])
    gram = v @ v[q]
    truth = sorted(others, key=lambda j: (-gram[j], j))
    out = []
    for dims in (z.shape[1], 2):
        near = sorted(others, key=lambda j: (float(np.linalg.norm(z[j, :dims] - z[q, :dims])), j))
        out.append([len(set(truth[:k]) & set(near[:k])) for k in r4.KS])
    return np.array(out)


@pytest.mark.parametrize('q', [0, 7, 63])
def test_arm_recalls_match_a_naive_recomputation_in_full_and_2d_at_every_k(rng, q):
    v = _unit_rows(rng, 64)
    y = v @ v[q]
    extra = [y + 0.02 * rng.standard_normal(64), y + 0.05 * rng.standard_normal(64)]
    h = rng.standard_normal(D) + 3.0 * v[q]
    masks = r4.truth_masks(r4.ground_truth_neighbours(y, q, r4.KS[-1]), 64)
    got = r4.arm_recalls(v, q, h, np.column_stack(extra), masks)
    assert got.shape == (2, 3)
    assert np.array_equal(got, _naive_recalls(v, q, extra, h))
    assert got.max() > 1


def test_two_d_columns_are_the_first_two_columns_of_the_full_observation(rng):
    v = _unit_rows(rng, 30)
    h = rng.standard_normal(D)
    full = real_observe(v, 4, h, rng.standard_normal((30, 2)))
    assert np.array_equal(full[:, :2], real_observe(v, 4, h))


# y-only control ---------------------------------------------------------------------------------


def _similarities():
    return 0.9 - 0.01 * np.arange(40)


def _swap(truth, out_index, in_index):
    found = truth.copy()
    found[found == out_index] = in_index
    return found


def test_y_only_verdict_is_exact_when_the_lists_agree_in_any_order():
    truth = np.arange(15)
    assert r4.y_only_verdict(truth, truth[::-1].copy(), _similarities()) == (0, True)


def test_y_only_verdict_accepts_swaps_within_tolerance_across_ranks_14_to_16():
    g, truth = _similarities(), np.arange(15)
    g[15] = g[14] - 5e-13
    assert r4.y_only_verdict(truth, _swap(truth, 14, 15), g) == (1, True)
    g[13] = g[14] + 5e-13
    assert r4.y_only_verdict(truth, _swap(truth, 13, 15), g) == (1, True)
    g[16] = g[14] - 4e-13
    two = _swap(_swap(truth, 13, 15), 14, 16)
    assert r4.y_only_verdict(truth, two, g) == (2, True)


def test_y_only_verdict_refuses_a_swap_beyond_tolerance_or_of_a_top_ranked_note():
    g, truth = _similarities(), np.arange(15)
    g[15] = g[14] - 2e-12
    assert r4.y_only_verdict(truth, _swap(truth, 14, 15), g) == (1, False)
    g[15] = g[14] - 5e-13
    assert r4.y_only_verdict(truth, _swap(truth, 0, 15), g) == (1, False)
    g[13] = g[14] + 2e-12
    assert r4.y_only_verdict(truth, _swap(truth, 13, 15), g) == (1, False)


# Validity ---------------------------------------------------------------------------------------


def test_validity_names_each_failed_condition_in_the_record_order():
    assert r4.assess_validity({'passes': True}, 0.2029) == (True, None, [])
    assert r4.assess_validity({'passes': False}, 0.2029) == (
        False, 'y_only_control', ['y_only_control'])
    assert r4.assess_validity({'passes': True}, 0.3) == (
        False, 'permutation_control', ['permutation_control'])
    assert r4.assess_validity({'passes': False}, 0.0) == (
        False, 'y_only_control', ['y_only_control', 'permutation_control'])


@pytest.mark.parametrize(('mean', 'ok'), [
    (0.149, True), (0.257, True), (0.2029, True),
    (0.1489, False), (0.2571, False), (0.0, False), (15.0, False),
])
def test_permutation_control_band_is_inclusive_and_fixed(mean, ok):
    assert r4.assess_validity({'passes': True}, mean)[0] is ok


# Block length from the ground truth alone -------------------------------------------------------


def _naive_l_gt(nn):
    n = len(nn)
    sets = [set(row.tolist()) for row in nn]

    def overlap(g):
        return np.mean([len(sets[i] & sets[i + g]) / 15 for i in range(n - g)])

    far = np.mean([len(sets[i] & sets[j]) / 15 for i in range(n) for j in range(i + 100, n)])
    for g in range(1, 101):
        if overlap(g) <= 2 * far:
            return g
    return None


def _grouped_lists(n, size):
    return np.array([(i // size) * 15 + np.arange(15) for i in range(n)])


def test_l_gt_is_the_smallest_g_whose_overlap_is_at_most_twice_the_far_overlap():
    nn = _grouped_lists(300, 10)
    assert r4.overlap_block_length(nn) == 10 == _naive_l_gt(nn)


def test_l_gt_beyond_100_is_reported_as_none():
    nn = _grouped_lists(600, 200)
    assert _naive_l_gt(nn) is None
    assert r4.overlap_block_length(nn) is None


def test_l_gt_matches_a_naive_recomputation_on_random_lists(rng):
    nn = np.array([rng.choice(250, 15, replace=False) for _ in range(250)])
    assert r4.overlap_block_length(nn) == _naive_l_gt(nn)


# Bootstrap --------------------------------------------------------------------------------------


def _naive_bootstrap(rng, op, rand, length, b):
    n, j = rand.shape
    blocks = [list(range(s, min(s + length, n))) for s in range(0, n, length)]
    out = []
    for _ in range(b):
        kb = rng.integers(0, len(blocks), len(blocks))
        jb = rng.integers(0, j, j)
        qs = [q for k in kb for q in blocks[k]]
        out.append(np.mean([op[q] - np.mean([rand[q, jj] for jj in jb]) for q in qs]))
    return np.array(out)


@pytest.mark.parametrize('length', [1, 5, 50])
def test_block_bootstrap_matches_a_naive_resampling_of_the_same_draws(rng, length):
    n, j, b = 23, 5, 1100
    op = rng.integers(0, 16, n).astype(np.float64)
    rand = rng.integers(0, 16, (n, j))
    got = r4.block_bootstrap(np.random.default_rng(7), op, rand, length, b)
    want = _naive_bootstrap(np.random.default_rng(7), op, rand, length, b)
    assert got.shape == (b,)
    assert np.allclose(got, want, rtol=0, atol=1e-12)


def test_block_bootstrap_of_identical_arms_is_zero_and_of_a_unit_gap_is_one(rng):
    op = rng.integers(0, 16, 40).astype(np.float64)
    same = np.repeat(op[:, None], 4, axis=1)
    assert np.all(r4.block_bootstrap(np.random.default_rng(1), op, same, 5, 600) == 0.0)
    gap = r4.block_bootstrap(np.random.default_rng(1), op, same - 1.0, 5, 600)
    assert np.allclose(gap, 1.0, rtol=0, atol=1e-12)


# Reported figures -------------------------------------------------------------------------------


def test_summarise_reports_means_retention_difference_and_the_colour_gain():
    op, rand = np.zeros((2, 3, 4)), np.zeros((2, 3, 4, 2))
    op[0, 1] = [3, 5, 7, 9]
    op[1, 1] = 2
    rand[0, 1] = 1
    rand[1, 1] = 0.5
    out = r4.summarise(op, rand)
    full = out['spaces']['full']['15']
    assert full == {
        'operator': 6.0, 'random': 1.0, 'difference': 5.0,
        'retention_operator': 6.0 / 15, 'retention_random': 1.0 / 15,
    }
    assert out['spaces']['2d']['15']['operator'] == 2.0
    assert out['colour_gain']['15'] == {'operator': 4.0, 'random': 0.5}
    assert set(out['spaces']['full']) == {'5', '15', '50'}


def test_perspective_r2_is_the_quadratic_fit_over_the_other_notes(rng):
    n, q = 200, 3
    x, y, noise = rng.standard_normal((3, n))
    exact = 1.0 + 2.0 * x - y + 0.5 * x * x + x * y
    obs = np.column_stack([x, y, exact, noise])
    r2 = r4.perspective_r2(obs, q)
    assert r2.shape == (2,) and r2[0] == pytest.approx(1.0, abs=1e-9)
    others = np.delete(np.arange(n), q)
    design = np.column_stack([np.ones(n), x, y, x * x, y * y, x * y])[others]
    u = noise[others]
    beta = np.linalg.solve(design.T @ design, design.T @ u)
    res = u - design @ beta
    assert r2[1] == pytest.approx(1.0 - (res @ res) / ((u - u.mean()) ** 2).sum(), abs=1e-9)
    moved = obs.copy()
    moved[q] = 1e6
    assert np.allclose(r4.perspective_r2(moved, q), r2, rtol=0, atol=1e-9)


# K6 result --------------------------------------------------------------------------------------

DIGESTS = {'embeddings.npy': 'a' * 64, 'labels.json': 'b' * 64, 'axes.json': 'c' * 64}


def _k6_bytes(**over):
    body = {
        'valid': True, 'ranking_fit': _axis_ids(), 'selected': ['lambda_3', 'a_8'],
        'digests': dict(DIGESTS),
    }
    body.update(over)
    return json.dumps(body).encode('utf-8')


def test_a_valid_k6_result_is_read_including_an_empty_selection():
    out = r4.read_k6_result(_k6_bytes(), _axis_ids(), DIGESTS)
    assert out['selected'] == ['lambda_3', 'a_8'] and out['ranking_fit'] == _axis_ids()
    assert r4.read_k6_result(_k6_bytes(selected=[]), _axis_ids(), DIGESTS)['selected'] == []


@pytest.mark.parametrize(('over', 'match'), [
    ({'valid': False}, 'valid'),
    ({'valid': 1}, 'valid'),
    ({'valid': 'true'}, 'valid'),
    ({'digests': {**DIGESTS, 'labels.json': 'd' * 64}}, 'digests'),
    ({'digests': {}}, 'digests'),
    ({'ranking_fit': _axis_ids()[:7]}, 'ranking_fit'),
    ({'ranking_fit': _axis_ids()[:7] + ['AXIS_1']}, 'ranking_fit'),
    ({'selected': ['lambda_3', 'nonsense']}, 'selected'),
    ({'selected': ['a_8', 'a_8']}, 'selected'),
    ({'selected': ['l', 'a_8', 'lambda_2', 'lambda_3']}, 'selected'),
])
def test_an_unusable_k6_result_is_refused_by_name(over, match):
    with pytest.raises(r4.K6ResultError, match=match):
        r4.read_k6_result(_k6_bytes(**over), _axis_ids(), DIGESTS)


@pytest.mark.parametrize('key', ['valid', 'digests', 'ranking_fit', 'selected'])
def test_a_k6_result_missing_a_key_is_refused_by_name(key):
    body = json.loads(_k6_bytes())
    del body[key]
    with pytest.raises(r4.K6ResultError, match=key):
        r4.read_k6_result(json.dumps(body).encode('utf-8'), _axis_ids(), DIGESTS)


# Measurement ------------------------------------------------------------------------------------


def _scene(rng, n=64):
    return _unit_rows(rng, n), _unit_rows(rng, 8), _axis_ids()


def _prior(selected=('lambda_3', 'a_8'), ranking=None):
    return {
        'valid': True, 'ranking_fit': list(ranking or _axis_ids()),
        'selected': list(selected), 'digests': {},
    }


def _measure(v, a_hat, ids, prior=None, j=3, b=1000):
    return r4.measure(v, a_hat, ids, prior or _prior(), k6.make_rng(), j, b)


@pytest.fixture
def wide_band(monkeypatch):
    monkeypatch.setattr(r4, 'PERMUTATION_BAND', (0.0, 15.0))


@pytest.fixture
def spies(monkeypatch):
    log = {'observe': [], 'observed': [], 'truth': [], 'permutation': []}
    real = {
        name: getattr(r4, name)
        for name in (
            'observe', 'observed_neighbours', 'ground_truth_neighbours', 'permutation_neighbours'
        )
    }

    def observe(vectors, anchor_index, horizontal=None, colours=None):
        out = real['observe'](vectors, anchor_index, horizontal, colours)
        log['observe'].append((vectors, anchor_index, horizontal, colours, out))
        return out

    def logged(key, name):
        def call(data, q, k):
            out = real[name](data, q, k)
            log[key].append((data, q, out))
            return out

        return call

    monkeypatch.setattr(r4, 'observe', observe)
    monkeypatch.setattr(r4, 'observed_neighbours', logged('observed', 'observed_neighbours'))
    monkeypatch.setattr(r4, 'ground_truth_neighbours', logged('truth', 'ground_truth_neighbours'))
    monkeypatch.setattr(
        r4, 'permutation_neighbours', logged('permutation', 'permutation_neighbours')
    )
    return log


def test_q_never_enters_any_list_used_in_a_measurement(rng, spies):
    v, a_hat, ids = _scene(rng)
    _measure(v, a_hat, ids)
    for key in ('truth', 'observed', 'permutation'):
        assert spies[key]
        for _, q, out in spies[key]:
            assert q not in out


def test_y_only_is_15_of_15_and_reaches_the_same_observe_and_neighbour_code(rng, spies):
    v, a_hat, ids = _scene(rng)
    out = _measure(v, a_hat, ids)
    ctl = out['y_only_control']
    assert ctl['exact'] == 64 and ctl['ties'] == 0 and ctl['failures'] == [] and ctl['passes']
    y_calls = [c for c in spies['observe'] if c[2] is None]
    assert len(y_calls) == 64 and all(c[3] is None and c[4].shape == (64, 1) for c in y_calls)
    seen = {id(obs) for obs, _, _ in spies['observed']}
    assert all(id(c[4]) in seen for c in spies['observe'])
    assert out['reported']['spaces']['full']['15']['operator'] < 15


def test_arms_share_notes_colours_and_q_and_differ_only_in_the_horizontal(rng, spies):
    v, a_hat, ids = _scene(rng)
    j = 3
    _measure(v, a_hat, ids, j=j)
    e = r4.draw_directions(k6.make_rng(), j, D)
    basis = dict(zip(ids, a_hat))
    for q in range(len(v)):
        calls = [c for c in spies['observe'] if c[1] == q]
        assert len(calls) == 2 + 2 * j
        assert all(c[0] is v for c in calls)
        with_h = [c for c in calls if c[2] is not None]
        colours = with_h[0][3]
        assert colours.shape == (len(v), 2) and all(c[3] is colours for c in with_h)
        q_hat = v[q] / np.linalg.norm(v[q])
        expected = [r4.operator_horizontal(v[q], basis)[0], *r4.random_directions(e, q_hat)]
        for h in expected:
            assert any(np.allclose(c[2], h, rtol=0, atol=1e-12) for c in with_h)
        assert all(abs(c[2] @ q_hat) < 1e-10 for c in with_h)


def test_operator_horizontal_is_the_dipole_over_its_squared_norm_with_poles_by_projection(rng):
    v, a_hat, ids = _scene(rng)
    basis = dict(zip(ids, a_hat))
    for q in (0, 5, 63):
        q_hat = v[q] / np.linalg.norm(v[q])
        proj = {i: q_hat @ a for i, a in basis.items()}
        c_a, c_b = sorted(proj, key=lambda i: (-proj[i], i))[:2]

        def perp(x):
            return x - (x @ q_hat) * q_hat

        w = perp(basis[c_a]) - perp(basis[c_b])
        h, fallback = r4.operator_horizontal(v[q], basis)
        assert fallback is False
        assert np.allclose(h, w / (w @ w), rtol=0, atol=1e-10)


def test_fallback_is_counted_per_q_and_the_frame_is_kept(rng, monkeypatch):
    real = r4.perspective_frame
    calls = []

    def flagged(q_vec, basis):
        frame = real(q_vec, basis)
        calls.append(frame)
        return frame._replace(fallback=len(calls) % 2 == 1)

    monkeypatch.setattr(r4, 'perspective_frame', flagged)
    v, a_hat, ids = _scene(rng)
    out = _measure(v, a_hat, ids)
    assert len(calls) == 64 and out['fallback_count'] == 32


# Draw order -------------------------------------------------------------------------------------


def _watch_draws(monkeypatch):
    events, states = [], {}
    real = {
        name: getattr(r4, name)
        for name in ('draw_directions', 'block_bootstrap', 'draw_sigma_weights')
    }

    def directions(gen, *args):
        events.append('directions')
        states['directions'] = gen.bit_generator.state
        return real['draw_directions'](gen, *args)

    def bootstrap(gen, op, rand, length, count):
        events.append(('bootstrap', length))
        states.setdefault('bootstrap', gen.bit_generator.state)
        return real['block_bootstrap'](gen, op, rand, length, count)

    def sigma(gen, *args):
        events.append('sigma')
        states['sigma'] = gen.bit_generator.state
        return real['draw_sigma_weights'](gen, *args)

    monkeypatch.setattr(r4, 'draw_directions', directions)
    monkeypatch.setattr(r4, 'block_bootstrap', bootstrap)
    monkeypatch.setattr(r4, 'draw_sigma_weights', sigma)
    return events, states


def test_draws_come_in_the_recorded_order(rng, monkeypatch):
    n, j, b = 60, 3, 1000
    v, a_hat, ids = _scene(rng, n)
    monkeypatch.setattr(r4, 'overlap_block_length', lambda nn: None)
    events, states = _watch_draws(monkeypatch)
    _measure(v, a_hat, ids, j=j, b=b)
    assert events == ['directions', *[('bootstrap', length) for length in GRID], 'sigma']
    assert states['directions'] == k6.make_rng().bit_generator.state
    replay = k6.make_rng()
    replay.standard_normal((j, D))
    for _ in range(n):
        replay.permutation(n - 1)
    assert states['bootstrap'] == replay.bit_generator.state
    for length in GRID:
        blocks = r4.n_blocks(n, length)
        for _ in range(b):
            replay.integers(0, blocks, blocks)
            replay.integers(0, j, j)
    assert states['sigma'] == replay.bit_generator.state


@pytest.mark.parametrize(('l_gt', 'extra'), [(None, []), (5, []), (7, [('bootstrap', 7)])])
def test_the_l_gt_interval_reuses_a_grid_length_and_is_drawn_last_otherwise(
    rng, monkeypatch, l_gt, extra
):
    v, a_hat, ids = _scene(rng, 60)
    monkeypatch.setattr(r4, 'overlap_block_length', lambda nn: l_gt)
    events, _ = _watch_draws(monkeypatch)
    out = _measure(v, a_hat, ids)
    assert events[1:] == [*[('bootstrap', length) for length in GRID], 'sigma', *extra]
    report = out['reported']['l_gt']
    assert report['value'] == l_gt
    if l_gt is None:
        assert report['interval'] is None
    else:
        assert report['interval']['lo'] <= report['interval']['hi']
    if l_gt == 5:
        assert report['interval']['hi'] == out['per_block_length']['5']['hi']


# Colour channels, R2, controls, decision --------------------------------------------------------


@pytest.mark.parametrize(
    'selected', [[], ['a_8'], ['lambda_2', 'lambda_3', 'a_8'], ['l', 'lambda_3']]
)
def test_dimension_is_two_plus_the_channels_k6_selected(rng, spies, selected):
    v, a_hat, ids = _scene(rng)
    out = _measure(v, a_hat, ids, _prior(selected))
    assert out['dimension'] == 2 + len(selected) and out['colour_channels'] == selected
    with_h = [c for c in spies['observe'] if c[2] is not None]
    assert {c[4].shape[1] for c in with_h} == {2 + len(selected)}
    assert all((c[3] is None) == (not selected) for c in with_h)
    assert set(out['reported']['r2_colour']) == set(selected)


def test_colour_columns_are_k6s_channels_from_the_ranking_read_from_its_result(rng, spies):
    v, a_hat, ids = _scene(rng)
    ranking = ['AXIS_5', 'AXIS_2', 'AXIS_8', 'AXIS_1', 'AXIS_7', 'AXIS_3', 'AXIS_6', 'AXIS_4']
    _measure(v, a_hat, ids, _prior(['l', 'a_8', 'lambda_3'], ranking))
    colours = next(c[3] for c in spies['observe'] if c[3] is not None)
    by_id = dict(zip(ids, a_hat))
    ordered = np.array([by_id[i] for i in ranking])
    c1 = ordered[0]

    def perp(x):
        return x - (x @ c1) * c1

    p8 = perp(ordered[7])
    w3 = perp(ordered[5]) - perp(ordered[6])
    expected = np.column_stack([
        1.0 / (1.0 + np.var(v @ a_hat.T, axis=1)),
        v @ p8 / (p8 @ p8),
        v @ w3 / (w3 @ w3),
    ])
    assert np.allclose(colours, expected, rtol=0, atol=1e-9)


def test_reported_r2_is_the_mean_over_q_of_the_operator_perspective_r2(rng, monkeypatch):
    real = r4.perspective_r2
    got = []

    def spy(obs, q):
        r2 = real(obs, q)
        got.append(r2)
        return r2

    monkeypatch.setattr(r4, 'perspective_r2', spy)
    v, a_hat, ids = _scene(rng)
    out = _measure(v, a_hat, ids)
    assert len(got) == 64
    reported = out['reported']['r2_colour']
    assert [reported['lambda_3'], reported['a_8']] == pytest.approx(
        np.mean(got, axis=0).tolist(), abs=1e-12
    )


def test_near_duplicates_are_counted_and_the_permutation_mean_is_on_the_d9_scale(rng):
    v, a_hat, ids = _scene(rng)
    v[10] = v[3]
    out = _measure(v, a_hat, ids)
    assert out['y_only_control']['near_duplicates'] == 2
    m = 63
    var = 15 * (15 / m) * (1 - 15 / m) * (m - 15) / (m - 1)
    assert abs(out['permutation_control']['mean'] - 225 / m) < 4 * np.sqrt(var / 64)


def test_a_failed_y_only_control_invalidates_the_run_and_withholds_the_decision(
    rng, monkeypatch, wide_band
):
    monkeypatch.setattr(r4, 'y_only_verdict', lambda truth, found, g_row: (1, False))
    v, a_hat, ids = _scene(rng)
    out = _measure(v, a_hat, ids)
    assert out['valid'] is False and out['failed_conditions'] == ['y_only_control']
    assert out['first_failed_condition'] == 'y_only_control' and out['r4_holds'] is None
    ctl = out['y_only_control']
    assert ctl['passes'] is False and ctl['failures'] == list(range(64))


def test_a_permutation_mean_outside_the_band_invalidates_the_run(rng):
    v, a_hat, ids = _scene(rng)
    out = _measure(v, a_hat, ids)
    assert out['valid'] is False and out['failed_conditions'] == ['permutation_control']
    assert out['permutation_control']['passes'] is False and out['r4_holds'] is None


def test_a_valid_run_decides_on_every_upper_bound_and_reports_the_margin(rng, wide_band):
    v, a_hat, ids = _scene(rng)
    out = _measure(v, a_hat, ids)
    assert out['valid'] is True and out['first_failed_condition'] is None
    per = out['per_block_length']
    assert list(per) == [str(length) for length in GRID]
    assert out['r4_holds'] is all(p['hi'] < 0 for p in per.values())
    assert out['margin'] == max(p['hi'] for p in per.values())
    for length, p in per.items():
        assert p['n_blocks'] == r4.n_blocks(64, int(length)) and p['holds'] is (p['hi'] < 0)
        assert p['lo'] <= p['hi'] and p['margin'] == p['hi']
        assert len(p['lo_neighbours']) == len(p['hi_neighbours']) == 2


def test_measure_reports_every_figure_the_contract_lists(rng, wide_band):
    v, a_hat, ids = _scene(rng)
    out = _measure(v, a_hat, ids)
    for key in (
        'n', 'k', 'n_directions', 'n_resamples', 'colour_channels', 'dimension', 'fallback_count',
        'per_block_length', 'y_only_control', 'permutation_control', 'reported', 'valid',
        'failed_conditions', 'first_failed_condition', 'r4_holds', 'margin',
    ):
        assert key in out
    assert set(out['y_only_control']) >= {
        'exact', 'ties', 'tie_pairs', 'near_duplicates', 'failures', 'passes'
    }
    report = out['reported']
    assert set(report) == {'spaces', 'colour_gain', 'sigma_reference', 'l_gt', 'r2_colour'}
    assert set(report['sigma_reference']['spaces']) == {'full', '2d'}


# End to end on synthetic files ------------------------------------------------------------------


def _write_run_inputs(tmp_path, rng, n=128, selected=('lambda_3', 'a_8'), **over):
    emb, lab, ax = tmp_path / 'embeddings.npy', tmp_path / 'labels.json', tmp_path / 'axes.json'
    np.save(emb, _unit_rows_f32(rng, n))
    lab.write_text(json.dumps(_labels(n)), encoding='utf-8')
    ax.write_text(json.dumps(_axes_json(_unit_rows(rng, 8))), encoding='utf-8')
    body = {
        'valid': True, 'ranking_fit': _axis_ids(), 'selected': list(selected),
        'digests': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (emb, lab, ax)},
    }
    body.update(over)
    res = tmp_path / 'K6_result.json'
    res.write_text(json.dumps(body), encoding='utf-8')
    paths = (emb, lab, ax, res)
    return paths, {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def _flip_file_bit(path, pos, bit):
    data = bytearray(path.read_bytes())
    data[pos] ^= 1 << bit
    path.write_bytes(bytes(data))


@pytest.fixture
def fake_measure(monkeypatch):
    seen = {}

    def measure(v, a_hat, axis_ids, prior, gen, n_directions, n_resamples):
        seen.update(
            v=v, a_hat=a_hat, axis_ids=axis_ids, prior=prior, state=gen.bit_generator.state,
            n_directions=n_directions, n_resamples=n_resamples,
        )
        return {'valid': True}

    monkeypatch.setattr(r4, 'measure', measure)
    return seen


def test_run_refuses_any_single_bit_flip_in_any_of_the_four_files(tmp_path, rng, fake_measure):
    paths, expected = _write_run_inputs(tmp_path, rng)
    out = tmp_path / 'out' / 'R4_result.json'
    r4.run(*paths, expected, tmp_path / 'intact.json')
    header = paths[0].read_bytes()
    data_start = 10 + int.from_bytes(header[8:10], 'little')
    for path in paths:
        size = path.stat().st_size
        positions = {0, size - 1, int(rng.integers(0, size))}
        if path == paths[0]:
            positions |= {20, data_start}
        for pos in sorted(positions):
            original = path.read_bytes()
            _flip_file_bit(path, pos, int(rng.integers(0, 8)))
            with pytest.raises(k6.IntegrityError, match=path.name):
                r4.run(*paths, expected, out)
            path.write_bytes(original)
    assert not out.exists()


def test_run_refuses_a_mismatched_digest_for_each_file_before_writing(tmp_path, rng, fake_measure):
    paths, expected = _write_run_inputs(tmp_path, rng)
    out = tmp_path / 'out' / 'R4_result.json'
    for path in paths:
        with pytest.raises(k6.IntegrityError, match=path.name):
            r4.run(*paths, {**expected, path: '0' * 64}, out)
    assert not out.exists() and fake_measure == {}


def test_run_refuses_an_invalid_k6_result_and_one_computed_on_other_data(
    tmp_path, rng, fake_measure
):
    out = tmp_path / 'out' / 'R4_result.json'
    paths, expected = _write_run_inputs(tmp_path, rng, valid=False)
    with pytest.raises(r4.K6ResultError, match='valid'):
        r4.run(*paths, expected, out)
    (tmp_path / 'other').mkdir()
    paths, expected = _write_run_inputs(
        tmp_path / 'other', rng, digests={'embeddings.npy': '0' * 64}
    )
    with pytest.raises(r4.K6ResultError, match='digests'):
        r4.run(*paths, expected, out)
    assert not out.exists() and fake_measure == {}


def test_run_hands_measure_the_eval_rows_renormalised_and_a_fresh_stream(
    tmp_path, rng, fake_measure
):
    paths, expected = _write_run_inputs(tmp_path, rng, n=128)
    r4.run(*paths, expected, tmp_path / 'out.json')
    v64 = np.load(paths[0]).astype(np.float64)
    want = (v64 / np.linalg.norm(v64, axis=1, keepdims=True))[1::2]
    assert fake_measure['v'].shape == (64, D)
    assert np.allclose(fake_measure['v'], want, rtol=0, atol=1e-15)
    assert fake_measure['state'] == k6.make_rng().bit_generator.state
    assert (fake_measure['n_directions'], fake_measure['n_resamples']) == (200, 10_000)
    assert fake_measure['prior']['selected'] == ['lambda_3', 'a_8']


def test_run_parses_the_bytes_it_hashed(tmp_path, rng, monkeypatch, fake_measure):
    paths, expected = _write_run_inputs(tmp_path, rng)
    (tmp_path / 'alt').mkdir()
    alt, _ = _write_run_inputs(tmp_path / 'alt', rng, selected=('l',))
    swap = {p: a.read_bytes() for p, a in zip(paths, alt)}
    real_read = Path.read_bytes
    reads = []

    def spy(self):
        data = real_read(self)
        reads.append(Path(self))
        if Path(self) in swap:
            Path(self).write_bytes(swap[Path(self)])
        return data

    monkeypatch.setattr(Path, 'read_bytes', spy)
    r4.run(*paths, expected, tmp_path / 'out.json')
    assert fake_measure['prior']['selected'] == ['lambda_3', 'a_8']
    assert [reads.count(p) for p in paths] == [1, 1, 1, 1]


def test_run_writes_the_result_json_as_the_contract_states(tmp_path, rng, monkeypatch):
    monkeypatch.setattr(r4, 'N_DIRECTIONS', 3)
    monkeypatch.setattr(r4, 'N_RESAMPLES', 1000)
    paths, expected = _write_run_inputs(tmp_path, rng)
    out = tmp_path / 'data' / 'refapp' / 'R4_result.json'
    result = r4.run(*paths, expected, out)
    text = out.read_text(encoding='utf-8')
    assert text.count(chr(13)) == 0
    assert text == json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + chr(10)
    assert result['digests'] == {p.name: d for p, d in expected.items()}
    assert set(result['environment']['threads'].values()) == {'1'}
    for key in ('environment', 'per_block_length', 'y_only_control', 'permutation_control', 'valid'):
        assert key in result
    again = tmp_path / 'again.json'
    r4.run(*paths, expected, again)
    assert again.read_bytes() == out.read_bytes()


def test_main_directs_the_result_and_exits_nonzero_on_an_invalid_run(tmp_path, monkeypatch):
    calls = []

    def fake_run(*args):
        calls.append(args)
        return {'valid': True, 'r4_holds': False, 'dimension': 4, 'failed_conditions': []}

    monkeypatch.setattr(r4, 'run', fake_run)
    target = tmp_path / 'elsewhere' / 'R4_B.json'
    r4.main(['--out', str(target)])
    r4.main([])
    args = (r4.EMBEDDINGS, r4.LABELS, r4.AXES, r4.K6_RESULT, r4.EXPECTED_DIGESTS)
    assert calls[0] == (*args, target)
    assert calls[1][5] == r4.RESULT == r4.REPO_ROOT / 'data' / 'refapp' / 'R4_result.json'
    invalid = {'valid': False, 'r4_holds': None, 'dimension': 4, 'failed_conditions': ['x']}
    monkeypatch.setattr(r4, 'run', lambda *args: invalid)
    with pytest.raises(SystemExit) as stopped:
        r4.main([])
    assert stopped.value.code not in (0, None)


def test_thread_variables_are_set_before_numpy_is_imported():
    text = Path(r4.__file__).read_text(encoding='utf-8')
    assert text.index('OMP_NUM_THREADS') < text.index('import numpy')
    assert {var: os.environ.get(var) for var in k6.THREAD_VARS} == dict.fromkeys(k6.THREAD_VARS, '1')


# Real shape -------------------------------------------------------------------------------------


def test_a_synthetic_run_at_the_real_shape_is_valid(rng):
    v, a_hat, ids = _scene(rng, 1110)
    out = _measure(v, a_hat, ids, j=2, b=1000)
    assert out['valid'] is True, out['failed_conditions']
    lo, hi = r4.PERMUTATION_BAND
    assert lo <= out['permutation_control']['mean'] <= hi
    assert out['y_only_control']['exact'] == 1110
    blocks = [p['n_blocks'] for p in out['per_block_length'].values()]
    assert blocks == [1110, 555, 222, 111, 56, 23]


@pytest.mark.skipif(not os.environ.get('R4_FULL_SHAPE'), reason='timing run: set R4_FULL_SHAPE=1')
def test_a_synthetic_run_at_the_real_shape_and_the_record_constants_completes(rng):
    v, a_hat, ids = _scene(rng, 1110)
    out = r4.measure(v, a_hat, ids, _prior(), k6.make_rng(), r4.N_DIRECTIONS, r4.N_RESAMPLES)
    assert out['valid'] is True and len(out['per_block_length']) == 6
