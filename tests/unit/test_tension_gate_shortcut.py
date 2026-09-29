"""Unit tests of tools/experiments/tension_gate_shortcut.py.

A labelled exploration (docs/methodology/METHODOLOGY.md, Explore), not a registry entry: the tests specify
the delegation contract tg-shortcut (behaviours B1..B8). Synthetic inputs only: CI has no .data/, and the
script is never run on the real artefact here.
"""

import hashlib
import itertools
import json
from collections import deque
from pathlib import Path

import numpy as np
import pytest

from tools.experiments import relational_graph_exploration as rge
from tools.experiments import tension_gate as tg
from tools.experiments import tension_gate_precheck as pc
from tools.experiments import tension_gate_shortcut as sh

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
    return sh.measure(v, a, items, tg.EPSILON, **kwargs)


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
    return sh.run(
        modules.get("k6_file", tg.K6_FILE),
        modules.get("rge_file", tg.RGE_FILE),
        modules.get("observables_file", tg.OBSERVABLES_FILE),
        modules.get("tg_file", sh.TG_FILE),
        modules.get("pc_file", sh.PC_FILE),
        *paths, expected, out_path,
    )


def _turns(n, edges, start):
    adj = [[] for _ in range(n)]
    for i, j in edges:
        adj[i].append(j)
        adj[j].append(i)
    dist = {start: 0}
    queue = deque([start])
    while queue:
        u = queue.popleft()
        for w in adj[u]:
            if w not in dist:
                dist[w] = dist[u] + 1
                queue.append(w)
    return dist


def _variant_and_j(name):
    """The variant, J and the FIT corpus indices of the synthetic corpus, rebuilt as the module does."""
    v, a, items = _inputs()
    fit, a_notes, _ = pc.split_notes(len(v))
    position = {corpus: local for local, corpus in enumerate(fit)}
    v_fit = v[fit]
    d = rge.pairwise_distances(v_fit)
    lab = rge.axis_cells(v_fit, a)
    variants = tg.build_variants(v_fit, d, [items[i] for i in fit], lab, tg.EPSILON)
    j = pc.judged_pairs(variants[name], variants["m_pairs"], {position[i] for i in a_notes}, lab)
    return fit, variants[name], j


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
    assert sh.pc is pc and sh.tg is tg
    assert sh.PC_SHA256 == "2ae4c7c5fb06c9afab7c8e983c1b9889096de774c54b6b29f1442034a02a8a75"
    assert hashlib.sha256(Path(pc.__file__).read_bytes()).hexdigest() == sh.PC_SHA256
    assert sh.PC_FILE == Path(pc.__file__) and sh.TG_FILE == Path(tg.__file__)
    assert sh.RESULT == sh.REPO_ROOT / "data" / "refapp" / "TG_shortcut_result.json"
    assert sh.VARIANTS == ("union", "open_borders")
    assert sh.ARMS == ("low", "shortcut", "random")
    assert sh.STATISTICS == ("low_over_shortcut", "shortcut_over_random", "low_over_random")
    assert sh.STATEMENT == "labelled exploration, not a registry entry"
    assert isinstance(sh.RULE, str) and sh.RULE


def test_the_script_sets_the_thread_variables_before_its_first_numpy_import():
    source = Path(sh.__file__).read_text(encoding="utf-8")
    assert source.index('os.environ[_var] = "1"') < source.index("import numpy")
    assert '("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")' in source


# T1 ---------------------------------------------------------------------------------------------------------


def test_turns_are_measured_without_any_of_j_and_with_the_rest_of_the_variant_intact():
    path = {(i, i + 1) for i in range(5)}
    j = {(0, 4), (1, 5)}
    turns = sh.shortcut_turns(6, path | j, j)
    assert turns == {(0, 4): 4, (1, 5): 4}


def test_a_relation_kept_outside_j_shortens_the_turns_of_j():
    path = {(i, i + 1) for i in range(6)}
    j = {(0, 5)}
    assert sh.shortcut_turns(7, path | j, j) == {(0, 5): 5}
    assert sh.shortcut_turns(7, path | j | {(0, 4)}, j) == {(0, 5): 2}


def test_the_shortcut_arm_ignores_tension_effort_and_axis_coordinates(monkeypatch, baseline):
    reference, _ = baseline
    real = tg.axis_coordinates
    monkeypatch.setattr(pc, "pair_effort", lambda *args, **kwargs: (0, 0.0))
    monkeypatch.setattr(tg, "axis_coordinates", lambda v, a: real(v, a)[:, ::-1] * 3.0)
    result = _measure()
    changed = False
    for name in sh.VARIANTS:
        ours, theirs = result["variants"][name], reference["variants"][name]
        assert ours["arms"]["shortcut"]["kept"] == theirs["arms"]["shortcut"]["kept"]
        assert [p["h"] for p in ours["pairs"]] == [p["h"] for p in theirs["pairs"]]
        changed = changed or ours["arms"]["low"]["kept"] != theirs["arms"]["low"]["kept"]
    assert changed


# T2 ---------------------------------------------------------------------------------------------------------


def test_the_shortcut_arm_keeps_the_largest_turns_with_ties_to_the_smaller_pair():
    turns = {(0, 1): 2, (0, 2): 5, (0, 3): 5, (1, 2): 1, (1, 3): 5, (2, 3): 3}
    assert sh.select_shortcut(turns, 0) == set()
    assert sh.select_shortcut(turns, 1) == {(0, 2)}
    assert sh.select_shortcut(turns, 2) == {(0, 2), (0, 3)}
    assert sh.select_shortcut(turns, 3) == {(0, 2), (0, 3), (1, 3)}
    assert sh.select_shortcut(turns, 4) == {(0, 2), (0, 3), (1, 3), (2, 3)}


def test_the_shortcut_arm_of_a_hand_built_graph_takes_the_relations_far_apart_by_other_paths():
    path = {(i, i + 1) for i in range(7)}
    j = {(0, 2), (0, 7), (3, 6), (1, 4)}
    turns = sh.shortcut_turns(8, path | j, j)
    assert turns == {(0, 2): 2, (0, 7): 7, (3, 6): 3, (1, 4): 3}
    assert sh.select_shortcut(turns, 2) == {(0, 7), (1, 4)}


# T3 ---------------------------------------------------------------------------------------------------------


def test_the_low_and_random_arms_and_the_pair_table_equal_the_precheck(baseline):
    result, _ = baseline
    v, a, items = _inputs()
    precheck = pc.measure(v, a, items, tg.EPSILON)
    for name in sh.VARIANTS:
        ours, theirs = result["variants"][name], precheck["variants"][name]
        for arm in ("low", "random"):
            assert ours["arms"][arm]["kept"] == theirs["arms"][arm]["kept"]
        assert ours["j_count"] == theirs["j_count"] and ours["k"] == theirs["k"]
        assert ours["g0"] == theirs["g0"]
        for mine, base in zip(ours["pairs"], theirs["pairs"], strict=True):
            assert {key: mine[key] for key in ("i", "j", "rank", "share", "distance")} == base


# T4 ---------------------------------------------------------------------------------------------------------


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
        tg._write(sh.measure(rows, a, labels, tg.EPSILON), path)
        written[key] = path.read_bytes()
    assert written["eval"] == written["same"]
    assert written["fit"] != written["same"]


# T5 ---------------------------------------------------------------------------------------------------------


def _verdicts(**by_statistic):
    base = {s: ("inconclusive", "inconclusive") for s in sh.STATISTICS}
    base.update(by_statistic)
    return {name: {s: base[s][k] for s in sh.STATISTICS} for k, name in enumerate(sh.VARIANTS)}


def test_the_decision_is_null_when_invalid():
    assert sh.decide(False, _verdicts(low_over_shortcut=("above", "above"))) is None


@pytest.mark.parametrize(("low", "expected"), [
    (("above", "above"), "tension_informative"),
    (("above", "inconclusive"), "archive"),
    (("inconclusive", "above"), "archive"),
    (("inconclusive", "inconclusive"), "archive"),
    (("below", "below"), "archive"),
    (("above", "below"), "archive"),
    (("pending", "pending"), "archive"),
    (("above", "pending"), "archive"),
])
def test_the_decision_table(low, expected):
    assert sh.decide(True, _verdicts(low_over_shortcut=low)) == expected


def test_the_report_only_statistics_never_change_the_decision():
    for expected, low in (
        ("archive", ("above", "inconclusive")), ("tension_informative", ("above", "above")),
    ):
        outcomes = set()
        for report in itertools.product(("above", "below", "inconclusive", "pending"), repeat=2):
            verdicts = _verdicts(
                low_over_shortcut=low,
                shortcut_over_random=(report[0], report[1]), low_over_random=(report[1], report[0]),
            )
            outcomes.add(sh.decide(True, verdicts))
        assert outcomes == {expected}


# T6 ---------------------------------------------------------------------------------------------------------


def test_the_draws_follow_variant_then_statistic_then_length(baseline):
    _, calls = baseline
    lengths = pc.valid_lengths(60)
    expected = [
        (variant, statistic, length)
        for variant in sh.VARIANTS for statistic in sh.STATISTICS for length in lengths
    ]
    assert calls == expected
    assert all(length != 50 for _, _, length in calls)


def test_the_length_of_fifty_is_not_valid_for_555_notes():
    assert pc.valid_lengths(555) == [1, 2, 5, 10, 20]


def test_the_random_arm_is_drawn_after_the_blind_directions_union_before_open_borders(baseline):
    result, _ = baseline
    rng = np.random.Generator(np.random.PCG64(tg.SEED))
    rng.standard_normal((tg.N_BLIND, tg.N_AXES))
    for name in sh.VARIANTS:
        pairs = [(p["i"], p["j"]) for p in result["variants"][name]["pairs"]]
        chosen = rng.choice(len(pairs), len(pairs) // 2, replace=False)
        expected = sorted([pairs[idx][0], pairs[idx][1]] for idx in chosen)
        assert result["variants"][name]["arms"]["random"]["kept"] == expected


# Shape of the result ------------------------------------------------------------------------------------------


def test_the_baseline_is_valid_and_every_arm_keeps_k_pairs_at_one_budget(baseline):
    result, _ = baseline
    assert result["valid"] is True and result["failed_conditions"] == []
    assert result["decision"] in {"tension_informative", "archive"}
    assert result["a_count"] == 60 and result["b_count"] == 60
    for name in sh.VARIANTS:
        variant = result["variants"][name]
        assert variant["j_count"] >= 2 and variant["j_count"] == len(variant["pairs"])
        assert variant["k"] == variant["j_count"] // 2
        assert list(variant["arms"]) == list(sh.ARMS)
        assert len({arm["relations"] for arm in variant["arms"].values()}) == 1
        for arm in variant["arms"].values():
            assert len(arm["kept"]) == variant["k"]
            assert arm["beta"] == pytest.approx(2 * arm["relations"] / 120)
        assert variant["g0"]["beta"] == pytest.approx(2 * variant["g0"]["relations"] / 120)


def test_each_statistic_reports_its_mean_its_records_and_its_verdict(baseline):
    result, _ = baseline
    for name in sh.VARIANTS:
        statistics = result["variants"][name]["statistics"]
        assert list(statistics) == list(sh.STATISTICS)
        for statistic in statistics.values():
            assert set(statistic) == {"mean", "per_l", "verdict"}
            assert set(statistic["per_l"]) == {str(length) for length in tg.GRID}
            for length, record in statistic["per_l"].items():
                assert set(record) == {"valid", "n_blocks", "interval", "ranks"}
                assert record["valid"] == (int(length) in pc.valid_lengths(60))
                assert (record["interval"] is None) == (not record["valid"])


# T7 ---------------------------------------------------------------------------------------------------------


def _assert_invalid(result, condition):
    assert result["valid"] is False
    assert condition in result["failed_conditions"]
    assert result["decision"] is None
    for name in sh.VARIANTS:
        assert list(result["variants"][name]["statistics"]) == list(sh.STATISTICS)


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


# T8 ---------------------------------------------------------------------------------------------------------


def _flip_last_byte(path):
    data = bytearray(path.read_bytes())
    data[-1] ^= 0x01
    path.write_bytes(bytes(data))


@pytest.mark.parametrize("module", ["tg_file", "pc_file"])
def test_a_changed_tension_gate_or_precheck_file_is_refused_and_nothing_is_written(tmp_path, module):
    paths, expected = _write_inputs(tmp_path)
    copy = tmp_path / "module.py"
    copy.write_bytes((sh.TG_FILE if module == "tg_file" else sh.PC_FILE).read_bytes())
    _flip_last_byte(copy)
    out = tmp_path / "out" / "TG_shortcut_result.json"
    with pytest.raises(tg.k6.IntegrityError, match="sha256 mismatch"):
        _run(paths, expected, out, **{module: copy})
    assert not out.parent.exists()


@pytest.mark.parametrize("attr", ["K6_FILE", "RGE_FILE", "OBSERVABLES_FILE"])
def test_a_changed_pinned_module_is_refused_and_nothing_is_written(tmp_path, attr):
    paths, expected = _write_inputs(tmp_path)
    copy = tmp_path / "pinned.py"
    copy.write_bytes(getattr(tg, attr).read_bytes())
    _flip_last_byte(copy)
    out = tmp_path / "out" / "TG_shortcut_result.json"
    with pytest.raises(tg.k6.IntegrityError, match="sha256 mismatch"):
        _run(paths, expected, out, **{attr.lower(): copy})
    assert not out.parent.exists()


def test_an_epsilon_other_than_0_8_is_refused_and_nothing_is_written(tmp_path, monkeypatch):
    monkeypatch.setattr(tg, "resolve_epsilon_edge", lambda: 0.5)
    paths, expected = _write_inputs(tmp_path)
    out = tmp_path / "out" / "TG_shortcut_result.json"
    with pytest.raises(ValueError, match="epsilon"):
        _run(paths, expected, out)
    assert not out.parent.exists()


@pytest.mark.parametrize("index", [0, 1, 2])
def test_an_input_digest_mismatch_is_refused_and_nothing_is_written(tmp_path, index):
    paths, expected = _write_inputs(tmp_path)
    _flip_last_byte(paths[index])
    out = tmp_path / "out" / "TG_shortcut_result.json"
    with pytest.raises(tg.k6.IntegrityError, match="sha256 mismatch"):
        _run(paths, expected, out)
    assert not out.parent.exists()


# T9 ---------------------------------------------------------------------------------------------------------


def test_two_runs_write_the_same_bytes_and_the_result_carries_the_rule(tmp_path, fast_bootstrap):
    paths, expected = _write_inputs(tmp_path)
    first, second = tmp_path / "one" / "r.json", tmp_path / "two" / "r.json"
    result = _run(paths, expected, first)
    _run(paths, expected, second)
    assert first.read_bytes() == second.read_bytes()
    text = first.read_text(encoding="utf-8")
    assert text == json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n"
    assert result["rule"] == sh.RULE
    assert result["statement"] == sh.STATEMENT
    assert result["environment"]["epsilon"] == tg.EPSILON
    assert "timings" not in result
    assert result["digests"][sh.PC_FILE.name] == sh.PC_SHA256
    assert result["digests"][sh.TG_FILE.name] == pc.TG_SHA256
    assert {tg.K6_FILE.name, tg.RGE_FILE.name, tg.OBSERVABLES_FILE.name} <= set(result["digests"])
    assert {p.name for p in paths} <= set(result["digests"])


def test_h_overlaps_and_mean_h_recompute_from_the_reported_pairs_and_kept_sets(baseline):
    result, _ = baseline
    for name in sh.VARIANTS:
        fit, variant_pairs, j = _variant_and_j(name)
        base_edges = variant_pairs - j
        variant = result["variants"][name]
        table = {(p["i"], p["j"]): p for p in variant["pairs"]}
        assert set(table) == {(fit[i], fit[k]) for i, k in j}
        for (i, k), record in table.items():
            local = {corpus: idx for idx, corpus in enumerate(fit)}
            assert record["h"] == _turns(len(fit), base_edges, local[i])[local[k]]
        kept = {arm: {tuple(p) for p in variant["arms"][arm]["kept"]} for arm in sh.ARMS}
        assert kept["shortcut"] == {
            p for p in sorted(table, key=lambda q: (-table[q]["h"], q))[: variant["k"]]
        }
        assert variant["overlaps"] == {
            "low_shortcut": len(kept["low"] & kept["shortcut"]),
            "low_random": len(kept["low"] & kept["random"]),
            "shortcut_random": len(kept["shortcut"] & kept["random"]),
        }
        hs = [record["h"] for record in table.values()]
        assert variant["mean_h"]["j"] == pytest.approx(sum(hs) / len(hs))
        for arm in sh.ARMS:
            assert variant["mean_h"][arm] == pytest.approx(
                sum(table[p]["h"] for p in kept[arm]) / len(kept[arm])
            )
        assert variant["pairs_sharing_h"] == pc.shared_rank_count(hs)
        assert [(p["i"], p["j"]) for p in variant["pairs"]] == sorted(table)


def test_main_prints_one_line_and_exits_non_zero_when_the_result_is_invalid(tmp_path, monkeypatch, capsys, fast_bootstrap):
    paths, expected = _write_inputs(tmp_path)
    monkeypatch.setattr(sh, "EMBEDDINGS", paths[0])
    monkeypatch.setattr(sh, "LABELS", paths[1])
    monkeypatch.setattr(sh, "AXES", paths[2])
    monkeypatch.setattr(sh, "EXPECTED_DIGESTS", expected)
    out = tmp_path / "out.json"
    sh.main(["--out", str(out)])
    assert len(capsys.readouterr().out.strip().splitlines()) == 1
    assert json.loads(out.read_text(encoding="utf-8"))["valid"] is True
    monkeypatch.setattr(tg, "is_connected", lambda adj: False)
    with pytest.raises(SystemExit) as exit_info:
        sh.main(["--out", str(out)])
    assert "connectivity" in str(exit_info.value)
    assert len(capsys.readouterr().out.strip().splitlines()) == 1
