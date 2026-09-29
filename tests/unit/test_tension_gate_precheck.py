"""Unit tests of tools/experiments/tension_gate_precheck.py.

A labelled exploration (docs/methodology/METHODOLOGY.md, Explore), not a registry entry: the tests specify
the delegation contract tg-precheck (behaviours B1..B12). Synthetic inputs only: CI has no .data/, and the
script is never run on the real artefact here.
"""

import hashlib
import itertools
import json
from pathlib import Path

import numpy as np
import pytest

from tools.experiments import tension_gate as tg
from tools.experiments import tension_gate_precheck as pre

D = 384
N_AXES = 8


def _axes_matrix():
    a = np.zeros((N_AXES, D))
    for k in range(N_AXES):
        a[k, k] = 1.0
    return a


def _corpus(n, seed=7, scale=0.2):
    v = np.zeros((n, D))
    rng = np.random.default_rng(seed)
    v[:, :N_AXES] = 0.3 + scale * rng.normal(size=(n, N_AXES))
    v[:, N_AXES:] = rng.normal(0.0, 0.01, size=(n, D - N_AXES))
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def _inputs(n=240):
    items = [{"label": f"L{i}", "part": "P1"} for i in range(n)]
    return _corpus(n), _axes_matrix(), items


def _measure(**kwargs):
    v, a, items = _inputs()
    return pre.measure(v, a, items, tg.EPSILON, **kwargs)


def _write_inputs(tmp_path, n=240):
    v32 = _corpus(n).astype(np.float32)
    labels = [{"label": f"L{i}", "part": "P1"} for i in range(n)]
    axes = [
        {"id": f"AXIS_{k}", "simbolo": "s", "tag": "t", "vector": row.tolist()}
        for k, row in enumerate(_axes_matrix())
    ]
    paths = (tmp_path / "embeddings.npy", tmp_path / "labels.json", tmp_path / "nsm_axes_8.json")
    np.save(paths[0], v32)
    paths[1].write_text(json.dumps(labels), encoding="utf-8")
    paths[2].write_text(json.dumps(axes), encoding="utf-8")
    return paths, {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def _run(paths, expected, out_path, **modules):
    return pre.run(
        modules.get("k6_file", tg.K6_FILE),
        modules.get("rge_file", tg.RGE_FILE),
        modules.get("observables_file", tg.OBSERVABLES_FILE),
        modules.get("tg_file", pre.TG_FILE),
        *paths, expected, out_path,
    )


@pytest.fixture
def fast_bootstrap(monkeypatch):
    monkeypatch.setattr(tg, "N_BOOT", 400)
    monkeypatch.setattr(tg, "INTERVAL_RANKS", (9, 389))
    monkeypatch.setattr(tg, "MC_RANKS", (8, 10, 388, 390))


@pytest.fixture(scope="module")
def baseline():
    calls = []
    result = _measure(_on_draw=lambda *args: calls.append(args))
    return result, calls


def test_constants_pins_and_paths_are_the_contract():
    assert pre.tg is tg
    assert pre.TG_SHA256 == "4c195d483e926590007625c258a2352bd3a6639ba6bd857434bc04286db887e5"
    assert hashlib.sha256(Path(tg.__file__).read_bytes()).hexdigest() == pre.TG_SHA256
    assert pre.TG_FILE == Path(tg.__file__)
    assert pre.RESULT == pre.REPO_ROOT / "data" / "refapp" / "TG_precheck_result.json"
    assert pre.VARIANTS == ("union", "open_borders")
    assert pre.STATISTICS == (
        "low_over_distance", "high_over_distance", "distance_over_random",
        "low_over_random", "high_over_random",
    )
    assert isinstance(pre.RULE, str) and pre.RULE


def test_the_script_sets_the_thread_variables_before_its_first_numpy_import():
    source = Path(pre.__file__).read_text(encoding="utf-8")
    assert source.index('os.environ[_var] = "1"') < source.index("import numpy")
    assert '("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")' in source


def test_the_split_gives_a_556_b_555_disjoint_and_together_the_fit_rows():
    fit, a, b = pre.split_notes(2221)
    assert fit == list(range(0, 2221, 2))
    assert len(fit) == 1111 and len(a) == 556 and len(b) == 555
    assert all(i % 4 == 0 for i in a) and all(i % 4 == 2 for i in b)
    assert not set(a) & set(b)
    assert sorted(set(a) | set(b)) == fit


def test_j_admits_only_a_a_cross_label_relations_outside_the_tree():
    lab = np.array([0, 1, 0, 1, 0, 1])
    a_set = {0, 1, 2, 4}
    variant = {(0, 1), (0, 2), (1, 2), (1, 3), (2, 5), (0, 4), (1, 4)}
    m_pairs = {(1, 2)}
    assert pre.judged_pairs(variant, m_pairs, a_set, lab) == {(0, 1), (1, 4)}


def test_every_relation_outside_j_is_in_all_four_arm_graphs_and_g0():
    base = {(0, 1), (0, 2), (1, 3), (2, 3), (3, 4), (4, 5), (1, 5)}
    j = {(0, 2), (1, 5), (2, 3)}
    arms = {"low": {(0, 2)}, "high": {(1, 5)}, "distance": {(2, 3)}, "random": {(0, 2)}}
    graphs = pre.build_arm_graphs(6, base, j, arms)

    def edges(adj):
        return {(i, k) for i in range(len(adj)) for k in adj[i] if i < k}

    assert set(graphs) == {"g0", "low", "high", "distance", "random"}
    assert edges(graphs["g0"]) == base
    for name, kept in arms.items():
        assert edges(graphs[name]) == (base - j) | kept
        assert (base - j) <= edges(graphs[name])


def test_neighbourhoods_exclude_both_ends_have_fifteen_notes_and_ties_go_to_the_lower_index():
    x = np.arange(20, dtype=np.float64)
    d = np.abs(x[:, None] - x[None, :])
    a_notes = list(range(20))
    nearest = tg.real_neighbours(d, a_notes, a_notes, tg.K_NEIGH + 1)
    for i, j in ((5, 6), (0, 19), (10, 3), (7, 9)):
        n_i, n_j = pre.neighbourhoods(nearest, i, j)
        for centre, got in ((i, n_i), (j, n_j)):
            expected = sorted(
                (t for t in a_notes if t not in (i, j)), key=lambda t, c=centre: (d[c, t], t),
            )[:15]
            assert got == expected
            assert len(got) == 15
            assert i not in got and j not in got


def test_the_effort_is_taken_within_each_neighbourhood_and_ignores_the_separation_between_them():
    rng = np.random.default_rng(1)
    c = rng.normal(size=(40, N_AXES))
    n_i, n_j = list(range(2, 17)), list(range(17, 32))
    u_blind = pre.blind_directions(np.random.Generator(np.random.PCG64(tg.SEED)))
    b_hat = (c[1] - c[0]) / np.linalg.norm(c[1] - c[0])
    shifted = c.copy()
    shifted[[0, *n_i]] -= 3.7 * b_hat
    shifted[[1, *n_j]] += 3.7 * b_hat

    assert pre.neighbourhood_tension(shifted, n_i, n_j) == pytest.approx(
        pre.neighbourhood_tension(c, n_i, n_j), abs=1e-9,
    )
    rank, share = pre.pair_effort(c, 0, 1, n_i, n_j, u_blind)
    rank_shifted, share_shifted = pre.pair_effort(shifted, 0, 1, n_i, n_j, u_blind)
    assert rank_shifted == rank
    assert share_shifted == pytest.approx(share, abs=1e-9)


def test_a_note_in_both_neighbourhoods_is_counted_in_both():
    rng = np.random.default_rng(2)
    c = rng.normal(size=(30, N_AXES))
    n_i, n_j = list(range(2, 17)), list(range(10, 25))
    w = np.zeros((N_AXES, N_AXES))
    for members in (n_i, n_j):
        for t in members:
            centred = c[t] - c[members].mean(axis=0)
            w += 0.5 * np.outer(centred, centred)
    assert pre.neighbourhood_tension(c, n_i, n_j) == pytest.approx(w, abs=1e-12)


def test_the_rank_is_strict_and_the_share_is_effort_over_trace():
    w = np.diag([1.0, 2.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    b = np.eye(N_AXES)[0]
    u_blind = np.array([
        np.eye(N_AXES)[0], np.eye(N_AXES)[0], np.eye(N_AXES)[1],
        [0.6, 0.8, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], np.eye(N_AXES)[2],
    ])
    assert pre.rank_and_share(w, b, u_blind) == (1, pytest.approx(1.0 / 3.0))


def test_the_blind_directions_are_the_first_draw_of_the_generator_as_tg_takes_them():
    rng = np.random.Generator(np.random.PCG64(20260918))
    g = rng.standard_normal((1000, 8))
    expected = g / np.linalg.norm(g, axis=1, keepdims=True)
    u_blind = pre.blind_directions(np.random.Generator(np.random.PCG64(tg.SEED)))
    assert u_blind.shape == (1000, 8)
    assert np.array_equal(u_blind, expected)


_INFO = {
    (0, 1): (2, 0.5, 3.0),
    (0, 2): (1, 0.4, 5.0),
    (0, 3): (1, 0.3, 2.0),
    (0, 4): (1, 0.3, 7.0),
    (1, 2): (3, 0.9, 2.0),
    (1, 3): (3, 0.9, 1.0),
    (1, 4): (3, 0.95, 8.0),
    (2, 3): (0, 0.1, 4.0),
}


def test_the_arm_budget_is_half_of_j_rounded_down():
    assert [pre.arm_size(m) for m in (0, 1, 2, 5, 6)] == [0, 0, 1, 2, 3]


def test_low_high_and_distance_keep_the_exact_pairs_with_their_tie_breaks():
    info = {p: {"rank": r, "share": s, "distance": dist} for p, (r, s, dist) in _INFO.items()}
    assert pre.select_arm("low", info, 1) == {(2, 3)}
    assert pre.select_arm("low", info, 3) == {(2, 3), (0, 3), (0, 4)}
    assert pre.select_arm("low", info, 4) == {(2, 3), (0, 3), (0, 4), (0, 2)}
    assert pre.select_arm("high", info, 2) == {(1, 4), (1, 2)}
    assert pre.select_arm("high", info, 3) == {(1, 4), (1, 2), (1, 3)}
    assert pre.select_arm("high", info, 4) == {(1, 4), (1, 2), (1, 3), (0, 1)}
    assert pre.select_arm("distance", info, 2) == {(1, 3), (0, 3)}
    assert pre.select_arm("distance", info, 3) == {(1, 3), (0, 3), (1, 2)}


def test_the_pairs_sharing_their_rank_with_another_pair_are_counted():
    assert pre.shared_rank_count([1, 1, 2, 3, 3, 3]) == 5
    assert pre.shared_rank_count([0, 1, 2]) == 0


def test_the_random_arm_is_reproducible_and_takes_k_pairs():
    j_sorted = [(0, 1), (0, 2), (1, 3), (2, 3), (2, 4), (3, 4)]
    first = pre.random_arm(np.random.Generator(np.random.PCG64(5)), j_sorted, 3)
    second = pre.random_arm(np.random.Generator(np.random.PCG64(5)), j_sorted, 3)
    assert first == second
    assert len(first) == 3 and first <= set(j_sorted)


def test_the_random_arm_is_drawn_after_the_blind_directions_union_before_open_borders(baseline):
    result, _ = baseline
    rng = np.random.Generator(np.random.PCG64(tg.SEED))
    rng.standard_normal((tg.N_BLIND, tg.N_AXES))
    for name in pre.VARIANTS:
        pairs = [(p["i"], p["j"]) for p in result["variants"][name]["pairs"]]
        chosen = rng.choice(len(pairs), len(pairs) // 2, replace=False)
        expected = sorted([pairs[idx][0], pairs[idx][1]] for idx in chosen)
        assert result["variants"][name]["arms"]["random"]["kept"] == expected


def test_the_evaluation_neighbours_come_from_b_only_with_ties_to_the_lower_index():
    x = np.arange(40, dtype=np.float64)
    d = np.abs(x[:, None] - x[None, :])
    b_notes = list(range(1, 40, 2))
    r = pre.evaluation_neighbours(d, b_notes)
    assert set(r) == set(b_notes)
    for q in b_notes:
        expected = sorted((t for t in b_notes if t != q), key=lambda t, c=q: (d[c, t], t))[:15]
        assert r[q] == expected
        assert all(t % 2 == 1 for t in r[q])


def test_a_shortcut_gives_a_positive_difference_for_the_arm_that_takes_it():
    path = {(0, 1), (1, 2), (2, 3), (3, 4)}
    adj_path = tg.build_graph(5, path, set(), set())
    adj_short = tg.build_graph(5, path | {(0, 3)}, set(), set())
    r = {0: [3, 4]}
    s_path = pre.turn_sums(adj_path, [0], r)
    s_short = pre.turn_sums(adj_short, [0], r)
    assert s_path == {0: 7}
    assert s_short == {0: 3}
    assert pre.differences(s_short, s_path, [0]).tolist() == [4.0]
    assert pre.differences(s_path, s_short, [0]).tolist() == [-4.0]


def _verdicts(**by_statistic):
    base = {s: ("inconclusive", "inconclusive") for s in pre.STATISTICS}
    base.update(by_statistic)
    return {name: {s: base[s][k] for s in pre.STATISTICS} for k, name in enumerate(pre.VARIANTS)}


def _l(lower, upper):
    return {"valid": True, "interval": [lower, upper]}


def test_a_verdict_needs_every_valid_l_and_ignores_the_invalid_ones():
    invalid = {"valid": False, "interval": None}
    assert pre.verdict([_l(0.1, 0.5), _l(0.2, 0.9), invalid]) == "above"
    assert pre.verdict([_l(-0.9, -0.1), _l(-0.5, -0.2), invalid]) == "below"
    assert pre.verdict([_l(0.1, 0.5), _l(0.0, 0.9)]) == "inconclusive"
    assert pre.verdict([_l(-0.9, -0.1), _l(-0.5, 0.0)]) == "inconclusive"
    assert pre.verdict([_l(0.1, 0.5), _l(-0.5, -0.1)]) == "inconclusive"
    assert pre.verdict([invalid, invalid]) == "pending"
    assert pre.verdict([]) == "pending"


def test_the_decision_is_null_when_invalid():
    verdicts = _verdicts(
        distance_over_random=("above", "above"), high_over_distance=("above", "above"),
    )
    assert pre.decide(False, verdicts) is None


@pytest.mark.parametrize("control", [("above", "inconclusive"), ("inconclusive", "above"), ("below", "above"),
                                     ("pending", "pending")])
def test_without_the_positive_control_in_both_variants_nothing_is_resolved(control):
    verdicts = _verdicts(
        distance_over_random=control, high_over_distance=("above", "above"),
        low_over_distance=("above", "above"),
    )
    assert pre.decide(True, verdicts) == "no_resolution"


@pytest.mark.parametrize(("low", "high", "expected"), [
    (("inconclusive", "inconclusive"), ("above", "above"), "sign_high"),
    (("above", "above"), ("inconclusive", "below"), "sign_low"),
    (("inconclusive", "inconclusive"), ("inconclusive", "inconclusive"), "archive"),
    (("above", "inconclusive"), ("above", "inconclusive"), "archive"),
    (("below", "below"), ("below", "below"), "archive"),
    (("above", "above"), ("above", "above"), "sign_unresolved"),
])
def test_the_decision_table(low, high, expected):
    verdicts = _verdicts(
        distance_over_random=("above", "above"), low_over_distance=low, high_over_distance=high,
    )
    assert pre.decide(True, verdicts) == expected


def test_the_report_only_statistics_never_change_the_decision():
    for expected, low, high in (
        ("archive", ("inconclusive",) * 2, ("inconclusive",) * 2),
        ("sign_high", ("inconclusive",) * 2, ("above",) * 2),
    ):
        outcomes = set()
        for report in itertools.product(("above", "below", "inconclusive", "pending"), repeat=2):
            verdicts = _verdicts(
                distance_over_random=("above", "above"), low_over_distance=low, high_over_distance=high,
                low_over_random=(report[0], report[1]), high_over_random=(report[1], report[0]),
            )
            outcomes.add(pre.decide(True, verdicts))
        assert outcomes == {expected}


def test_the_bootstrap_lengths_follow_the_block_rule():
    assert pre.valid_lengths(555) == [1, 2, 5, 10, 20]
    assert tg.n_blocks_for(555, 50) < tg.MIN_BLOCKS
    assert pre.valid_lengths(60) == [1, 2]
    assert pre.valid_lengths(10) == []


def test_the_draws_follow_variant_then_statistic_then_length(baseline):
    _, calls = baseline
    lengths = pre.valid_lengths(60)
    expected = [
        (variant, statistic, length)
        for variant in pre.VARIANTS for statistic in pre.STATISTICS for length in lengths
    ]
    assert calls == expected
    assert all(length != 50 for _, _, length in calls)


def test_the_baseline_run_is_valid_and_every_arm_keeps_k_pairs_at_one_budget(baseline):
    result, _ = baseline
    assert result["valid"] is True and result["failed_conditions"] == []
    assert result["decision"] in {"no_resolution", "sign_high", "sign_low", "archive", "sign_unresolved"}
    assert result["a_count"] == 60 and result["b_count"] == 60
    for name in pre.VARIANTS:
        variant = result["variants"][name]
        assert variant["j_count"] >= 2 and variant["j_count"] == len(variant["pairs"])
        assert variant["k"] == variant["j_count"] // 2
        counts = {arm["relations"] for arm in variant["arms"].values()}
        assert len(counts) == 1
        for arm in variant["arms"].values():
            assert len(arm["kept"]) == variant["k"]
            assert arm["beta"] == pytest.approx(2 * arm["relations"] / 120)
        assert variant["g0"]["beta"] == pytest.approx(2 * variant["g0"]["relations"] / 120)


def test_the_baseline_only_names_a_notes_and_the_arms_follow_the_reported_pair_table(baseline):
    result, _ = baseline
    for name in pre.VARIANTS:
        variant = result["variants"][name]
        pairs = variant["pairs"]
        assert [(p["i"], p["j"]) for p in pairs] == sorted((p["i"], p["j"]) for p in pairs)
        assert all(p["i"] % 4 == 0 and p["j"] % 4 == 0 for p in pairs)
        info = {(p["i"], p["j"]): p for p in pairs}
        for arm in ("low", "high", "distance"):
            expected = sorted(list(p) for p in pre.select_arm(arm, info, variant["k"]))
            assert variant["arms"][arm]["kept"] == expected
        kept = {arm: {tuple(p) for p in variant["arms"][arm]["kept"]} for arm in variant["arms"]}
        assert variant["overlaps"] == {
            "low_distance": len(kept["low"] & kept["distance"]),
            "high_distance": len(kept["high"] & kept["distance"]),
            "low_high": len(kept["low"] & kept["high"]),
            "random_distance": len(kept["random"] & kept["distance"]),
        }
        assert variant["pairs_sharing_rank"] == pre.shared_rank_count([p["rank"] for p in pairs])


def test_each_statistic_reports_its_mean_its_records_and_its_verdict(baseline):
    result, _ = baseline
    for name in pre.VARIANTS:
        statistics = result["variants"][name]["statistics"]
        assert list(statistics) == list(pre.STATISTICS)
        for statistic in statistics.values():
            assert set(statistic) == {"mean", "per_l", "verdict"}
            assert set(statistic["per_l"]) == {str(length) for length in tg.GRID}
            for length, record in statistic["per_l"].items():
                assert set(record) == {"valid", "n_blocks", "interval", "ranks"}
                assert record["valid"] == (int(length) in pre.valid_lengths(60))
                assert (record["interval"] is None) == (not record["valid"])


def test_eval_rows_and_their_labels_influence_nothing_while_a_fit_row_does(tmp_path, fast_bootstrap):
    v, a, items = _inputs()
    rng = np.random.default_rng(99)
    other = rng.normal(size=(len(v[1::2]), D))
    v_eval = v.copy()
    v_eval[1::2] = other / np.linalg.norm(other, axis=1, keepdims=True)
    items_eval = [item if i % 2 == 0 else {"label": f"E{i}", "part": "P9"} for i, item in enumerate(items)]
    v_fit = v.copy()
    v_fit[4] = v[8]

    written = {}
    for key, (rows, labels) in {
        "same": (v, items), "eval": (v_eval, items_eval), "fit": (v_fit, items),
    }.items():
        path = tmp_path / f"{key}.json"
        tg._write(pre.measure(rows, a, labels, tg.EPSILON), path)
        written[key] = path.read_bytes()
    assert written["eval"] == written["same"]
    assert written["fit"] != written["same"]


def _assert_invalid(result, condition):
    assert result["valid"] is False
    assert condition in result["failed_conditions"]
    assert result["decision"] is None
    for name in pre.VARIANTS:
        assert list(result["variants"][name]["statistics"]) == list(pre.STATISTICS)


def test_a_disconnected_graph_is_invalid(monkeypatch, fast_bootstrap):
    monkeypatch.setattr(tg, "is_connected", lambda adj: False)
    _assert_invalid(_measure(), "connectivity")


def test_unequal_arm_edge_counts_are_invalid(monkeypatch, fast_bootstrap):
    counter = itertools.count()
    monkeypatch.setattr(tg, "count_edges", lambda adj: next(counter))
    _assert_invalid(_measure(), "equal_budget")


def test_a_failed_ceiling_control_is_invalid(monkeypatch, fast_bootstrap):
    monkeypatch.setattr(tg, "ceiling_control", lambda *args, **kwargs: False)
    _assert_invalid(_measure(), "ceiling")


def test_fewer_than_two_judged_relations_is_invalid(monkeypatch, fast_bootstrap):
    real = tg.build_variants

    def only_the_tree(*args, **kwargs):
        variants = real(*args, **kwargs)
        tree = variants["m_pairs"]
        return {"m_pairs": tree, "union": set(tree), "open_borders": set(tree), "dense": set()}

    monkeypatch.setattr(tg, "build_variants", only_the_tree)
    result = _measure()
    _assert_invalid(result, "j_size")
    assert result["variants"]["union"]["j_count"] == 0


def _flip_last_byte(path):
    data = bytearray(path.read_bytes())
    data[-1] ^= 0x01
    path.write_bytes(bytes(data))


def test_a_changed_tension_gate_file_is_refused_and_nothing_is_written(tmp_path):
    paths, expected = _write_inputs(tmp_path)
    copy = tmp_path / "tension_gate.py"
    copy.write_bytes(pre.TG_FILE.read_bytes())
    _flip_last_byte(copy)
    out = tmp_path / "out" / "TG_precheck_result.json"
    with pytest.raises(tg.k6.IntegrityError, match="sha256 mismatch"):
        _run(paths, expected, out, tg_file=copy)
    assert not out.parent.exists()


@pytest.mark.parametrize("attr", ["K6_FILE", "RGE_FILE", "OBSERVABLES_FILE"])
def test_a_changed_pinned_module_is_refused_and_nothing_is_written(tmp_path, attr):
    paths, expected = _write_inputs(tmp_path)
    copy = tmp_path / "pinned.py"
    copy.write_bytes(getattr(tg, attr).read_bytes())
    _flip_last_byte(copy)
    out = tmp_path / "out" / "TG_precheck_result.json"
    with pytest.raises(tg.k6.IntegrityError, match="sha256 mismatch"):
        _run(paths, expected, out, **{attr.lower(): copy})
    assert not out.parent.exists()


def test_an_epsilon_other_than_0_8_is_refused_and_nothing_is_written(tmp_path, monkeypatch):
    monkeypatch.setattr(tg, "resolve_epsilon_edge", lambda: 0.5)
    paths, expected = _write_inputs(tmp_path)
    out = tmp_path / "out" / "TG_precheck_result.json"
    with pytest.raises(ValueError, match="epsilon"):
        _run(paths, expected, out)
    assert not out.parent.exists()


@pytest.mark.parametrize("index", [0, 1, 2])
def test_an_input_digest_mismatch_is_refused_and_nothing_is_written(tmp_path, index):
    paths, expected = _write_inputs(tmp_path)
    _flip_last_byte(paths[index])
    out = tmp_path / "out" / "TG_precheck_result.json"
    with pytest.raises(tg.k6.IntegrityError, match="sha256 mismatch"):
        _run(paths, expected, out)
    assert not out.parent.exists()


def test_two_runs_write_the_same_bytes_and_the_result_carries_the_rule(tmp_path, fast_bootstrap):
    paths, expected = _write_inputs(tmp_path)
    first, second = tmp_path / "one" / "r.json", tmp_path / "two" / "r.json"
    result = _run(paths, expected, first)
    _run(paths, expected, second)
    assert first.read_bytes() == second.read_bytes()
    text = first.read_text(encoding="utf-8")
    assert text == json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n"
    assert result["rule"] == pre.RULE
    assert result["statement"] == "labelled exploration, not a registry entry"
    assert result["environment"]["epsilon"] == tg.EPSILON
    assert "timings" not in result


def test_main_prints_one_line_and_exits_non_zero_when_the_result_is_invalid(tmp_path, monkeypatch, capsys, fast_bootstrap):
    paths, expected = _write_inputs(tmp_path)
    monkeypatch.setattr(pre, "EMBEDDINGS", paths[0])
    monkeypatch.setattr(pre, "LABELS", paths[1])
    monkeypatch.setattr(pre, "AXES", paths[2])
    monkeypatch.setattr(pre, "EXPECTED_DIGESTS", expected)
    out = tmp_path / "out.json"
    pre.main(["--out", str(out)])
    assert len(capsys.readouterr().out.strip().splitlines()) == 1
    assert json.loads(out.read_text(encoding="utf-8"))["valid"] is True
    monkeypatch.setattr(tg, "is_connected", lambda adj: False)
    with pytest.raises(SystemExit) as exit_info:
        pre.main(["--out", str(out)])
    assert "connectivity" in str(exit_info.value)
    assert len(capsys.readouterr().out.strip().splitlines()) == 1
