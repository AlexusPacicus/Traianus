"""Unit tests of tools/experiments/tension_gate.py.

Specification: docs/methodology/instrument-audit/TG.md (revision 3), docs/methodology/instrument-audit/
contracts.md (sections 0 and 5), docs/methodology/instrument-audit/derivations.md (D27, D28, D29).
Synthetic inputs only: CI has no .data/, and the measurement is never run on the real artefact here.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from tools.experiments import tension_gate as tg

D = 384
N_AXES = 8


def _axes_matrix():
    a = np.zeros((N_AXES, D))
    for k in range(N_AXES):
        a[k, k] = 1.0
    return a


def _corpus(n, equal_row=None):
    """n rows, dominant axis 0 for the first half and axis 1 for the second; unit-norm.

    The remaining 376 components carry small deterministic noise so raw 384-d distances are
    non-degenerate; the noise never touches the first 8 (axis) components' relative order.
    """
    rng = np.random.default_rng(12345)
    v = rng.normal(0.0, 0.05, size=(n, D))
    for i in range(n):
        dominant = 0 if i < n // 2 else 1
        v[i, :N_AXES] = rng.uniform(-0.02, 0.02, size=N_AXES)
        v[i, dominant] = 0.9
    if equal_row is not None:
        v[equal_row, :N_AXES] = 0.3
    v = v / np.linalg.norm(v, axis=1, keepdims=True)
    return v


def _measure_inputs(n=44, equal_row=None):
    v = _corpus(n, equal_row=equal_row)
    a = _axes_matrix()
    axis_ids = [f"AXIS_{k}" for k in range(N_AXES)]
    label_items = [{"label": f"L{i}", "part": "P1"} for i in range(n)]
    return v, a, axis_ids, label_items


def _write_inputs(tmp_path, n=44, equal_row=None, corrupt=None):
    v = _corpus(n, equal_row=equal_row)
    v32 = v.astype(np.float32)
    labels = [{"label": f"L{i}", "part": "P1"} for i in range(n)]
    axes = [
        {"id": f"AXIS_{k}", "simbolo": "s", "tag": "t", "vector": row.tolist()}
        for k, row in enumerate(_axes_matrix())
    ]
    if corrupt is not None:
        corrupt(v32, labels, axes)
    paths = (tmp_path / "embeddings.npy", tmp_path / "labels.json", tmp_path / "nsm_axes_8.json")
    np.save(paths[0], v32)
    paths[1].write_text(json.dumps(labels), encoding="utf-8")
    paths[2].write_text(json.dumps(axes), encoding="utf-8")
    return paths, {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def _pin_copies(tmp_path):
    copies = {
        "K6_FILE": tmp_path / "k6_colour_predictability.py",
        "RGE_FILE": tmp_path / "relational_graph_exploration.py",
        "OBSERVABLES_FILE": tmp_path / "observables.py",
    }
    copies["K6_FILE"].write_bytes(tg.K6_FILE.read_bytes())
    copies["RGE_FILE"].write_bytes(tg.RGE_FILE.read_bytes())
    copies["OBSERVABLES_FILE"].write_bytes(tg.OBSERVABLES_FILE.read_bytes())
    return copies


def _flip_bit(path, pos=0, bit=0):
    data = bytearray(path.read_bytes())
    data[pos] ^= 1 << bit
    path.write_bytes(bytes(data))


def _run(paths, expected, out_path, **modules):
    return tg.run(
        modules.get("k6_file", tg.K6_FILE),
        modules.get("rge_file", tg.RGE_FILE),
        modules.get("observables_file", tg.OBSERVABLES_FILE),
        *paths, expected, out_path,
    )


# Constants, pins and thread variables -------------------------------------------------------------


def test_constants_seed_pins_and_paths_are_the_record():
    assert tg.SEED == 20260918
    assert tg.N_AXES == 8
    assert tg.K_NEIGH == 15
    assert tg.N_BLIND == 1000
    assert tg.CUT_INDEX == 11
    assert tg.N_BOOT == 10_000
    assert tg.GRID == (1, 2, 5, 10, 20, 50)
    assert tg.MIN_BLOCKS == 20
    assert tg.INTERVAL_RANKS == (249, 9749)
    assert tg.MC_RANKS == (233, 265, 9733, 9765)
    assert tg.EPSILON == 0.8
    assert tg.K6_SHA256 == "6289c596792154f6bb799606265c68719c6b8c7ae8b69084116dfb23c77876d2"
    assert tg.RGE_SHA256 == "627aa8e95a844b0aec290a41c48b9a0bf6890db25b5240b5730c366a56d2e7dc"
    assert tg.OBSERVABLES_SHA256 == "54385042f771fc6b2a383e52e312287b2b82030f378212f7e06bd19f16f94c0f"
    assert tg.EXPECTED_DIGESTS == {
        tg.EMBEDDINGS: "eafb0e97172830f2404e96fa08d74bf6cccc0b6cbe84d47b790a476603e7d8d1",
        tg.LABELS: "1d60699353d810f089730c6203ee28f9c416e3004b60781bc965cec284097f4f",
        tg.AXES: "b14e5d6700d1a7478a357ca26f0f38f5240f97a42daad45722d21f1c3f964e35",
    }
    assert tg.RESULT == tg.REPO_ROOT / "data" / "refapp" / "TG_result.json"
    assert tg.K6_FILE == Path(tg.k6.__file__)
    assert tg.RGE_FILE == Path(tg.rge.__file__)
    assert tg.OBSERVABLES_FILE == Path(tg.observables_module.__file__)
    assert tg.CONTROL_IDENTIFIERS == (
        "exchangeable_direction", "ceiling", "connectivity", "equal_budget",
    )


def test_the_script_sets_the_thread_variables_before_its_first_numpy_import():
    source = Path(tg.__file__).read_text(encoding="utf-8")
    assert source.index('os.environ[_var] = "1"') < source.index("import numpy")
    assert '("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")' in source


@pytest.mark.parametrize("attr", ["K6_FILE", "RGE_FILE", "OBSERVABLES_FILE"])
def test_a_single_bit_flip_in_each_pinned_module_is_refused_before_any_data_is_read(tmp_path, attr):
    copies = _pin_copies(tmp_path)
    _flip_bit(copies[attr])
    paths, expected = _write_inputs(tmp_path)
    out = tmp_path / "out" / "TG_result.json"
    with pytest.raises(tg.k6.IntegrityError):
        tg.run(copies["K6_FILE"], copies["RGE_FILE"], copies["OBSERVABLES_FILE"], *paths, expected, out)
    assert not out.parent.exists()


# Artefact integrity ---------------------------------------------------------------------------------


@pytest.mark.parametrize("index", [0, 1, 2])
def test_a_single_bit_flip_in_each_artefact_is_refused_and_nothing_is_written(tmp_path, index):
    paths, expected = _write_inputs(tmp_path)
    out = tmp_path / "out" / "TG_result.json"
    _flip_bit(paths[index])
    with pytest.raises(tg.k6.IntegrityError):
        _run(paths, expected, out)
    assert not out.parent.exists()


def test_a_nan_row_is_refused_through_validate_inputs_and_nothing_is_written(tmp_path):
    paths, expected = _write_inputs(tmp_path, corrupt=lambda v, lab, ax: v.__setitem__((2, 100), np.nan))
    out = tmp_path / "out" / "TG_result.json"
    with pytest.raises(ValueError, match="row 2: non-finite"):
        _run(paths, expected, out)
    assert not out.parent.exists()


def test_epsilon_other_than_0_8_is_refused_and_nothing_is_written(tmp_path, monkeypatch):
    monkeypatch.setattr(tg, "resolve_epsilon_edge", lambda: 0.5)
    paths, expected = _write_inputs(tmp_path)
    out = tmp_path / "out" / "TG_result.json"
    with pytest.raises(ValueError, match="epsilon"):
        _run(paths, expected, out)
    assert not out.parent.exists()


# Zones, labels and real neighbours -------------------------------------------------------------------


def test_zone_membership_is_strict_and_a_note_with_equal_affinities_has_no_zone():
    c = np.array([
        [1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        [0.0] * 8,
        [5.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
    ])
    zones = tg.zone_membership(c)
    assert zones[0].tolist() == [True, True, False, False, False, False, False, False]
    assert zones[1].tolist() == [False] * 8
    assert zones[2].tolist() == [True, False, False, False, False, False, False, False]


def test_label_ties_go_to_the_lower_axis():
    c = np.array([[1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]])
    lab = tg.rge.axis_cells(c, np.eye(8))
    assert lab[0] == 0


def test_real_neighbours_exclude_self_and_break_ties_by_row():
    d = np.array([
        [0.0, 1.0, 1.0, 2.0],
        [1.0, 0.0, 1.0, 2.0],
        [1.0, 1.0, 0.0, 2.0],
        [2.0, 2.0, 2.0, 0.0],
    ])
    out = tg.real_neighbours(d, pool=[0, 1, 2, 3], targets=[0], k=2)
    assert out[0] == [1, 2]
    out_full = tg.real_neighbours(d, pool=[0, 1, 2, 3], targets=[0, 1, 2, 3], k=3)
    assert 0 not in out_full[0] and len(out_full[0]) == 3


# Cone membership -------------------------------------------------------------------------------------


def test_cone_membership_inside_on_surface_and_beyond_each_end():
    vi = np.array([0.0, 0.0])
    vj = np.array([10.0, 0.0])
    rho_i = rho_j = 2.0
    inside, sigma = tg.cone_membership(np.array([5.0, 1.0]), vi, vj, rho_i, rho_j)
    assert inside and sigma == pytest.approx(0.5)
    inside, _ = tg.cone_membership(np.array([5.0, 2.0]), vi, vj, rho_i, rho_j)
    assert inside
    inside, _ = tg.cone_membership(np.array([5.0, 2.0001]), vi, vj, rho_i, rho_j)
    assert not inside
    inside, sigma = tg.cone_membership(np.array([-1.0, 0.0]), vi, vj, rho_i, rho_j)
    assert not inside and sigma < 0.0
    inside, sigma = tg.cone_membership(np.array([11.0, 0.0]), vi, vj, rho_i, rho_j)
    assert not inside and sigma > 1.0


# Effort, the cut and the ends -------------------------------------------------------------------------


def test_cut_is_strict_at_exactly_the_12th_smallest():
    t = np.zeros((8, 8))
    t[0, 0] = 5.0
    u_blind = np.zeros((1000, 8))
    u_blind[:11, 1] = 1.0
    u_blind[11:, 0] = 1.0
    b_at_cut = np.array([1.0, 0, 0, 0, 0, 0, 0, 0])
    e, kappa, passes = tg.cut_and_pass(t, b_at_cut, u_blind)
    assert e == 5.0 and kappa == 5.0 and passes is False
    b_below = np.array([0.0, 1.0, 0, 0, 0, 0, 0, 0])
    e2, kappa2, passes2 = tg.cut_and_pass(t, b_below, u_blind)
    assert e2 < kappa2 and passes2 is True


def test_effort_excluding_the_ends_can_flip_the_pass_fail_outcome():
    interior = np.array([
        [1.0, 0.3, 0, 0, 0, 0, 0, 0],
        [1.0, -0.3, 0, 0, 0, 0, 0, 0],
        [1.0, 0.1, 0, 0, 0, 0, 0, 0],
        [1.0, -0.1, 0, 0, 0, 0, 0, 0],
        [1.0, 0.0, 0, 0, 0, 0, 0, 0],
    ])
    c_i = np.zeros(8)
    c_j = np.array([20.0, 0, 0, 0, 0, 0, 0, 0])
    b = np.array([1.0, 0, 0, 0, 0, 0, 0, 0])
    u_blind = np.zeros((1000, 8))
    u_blind[:5, 0] = 1.0
    u_blind[5:, 1] = 1.0
    _, t_without = tg.tension_matrix(interior)
    _, t_with = tg.tension_matrix(np.vstack([interior, c_i, c_j]))
    _, _, passes_without = tg.cut_and_pass(t_without, b, u_blind)
    _, _, passes_with = tg.cut_and_pass(t_with, b, u_blind)
    assert passes_without is True
    assert passes_with is False


# The three graphs ------------------------------------------------------------------------------------


def test_the_three_graphs_share_every_relation_outside_j_and_may_differ_within_it():
    n = 6
    variant = {(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)}
    j_pairs = {(1, 2), (2, 3), (3, 4)}
    kept = {(1, 2), (3, 4)}
    kept_blind = {(2, 3)}
    g0_adj = tg.build_graph(n, variant, set(), set())
    g_plus_adj = tg.build_graph(n, variant, j_pairs, kept)
    g_blind_adj = tg.build_graph(n, variant, j_pairs, kept_blind)

    def edges(adj):
        return {(i, j) for i in range(len(adj)) for j in adj[i] if i < j}

    assert edges(g0_adj) == variant
    assert edges(g_plus_adj) == (variant - j_pairs) | kept
    assert edges(g_blind_adj) == (variant - j_pairs) | kept_blind
    assert edges(g_plus_adj) != edges(g_blind_adj)
    outside = variant - j_pairs
    assert (edges(g0_adj) & outside) == (edges(g_plus_adj) & outside) == (edges(g_blind_adj) & outside) == outside


# Draw order and the blind reference -------------------------------------------------------------------


def test_the_first_components_of_g_from_seed_20260918_are_pinned():
    rng = np.random.Generator(np.random.PCG64(tg.SEED))
    g = rng.standard_normal((tg.N_BLIND, tg.N_AXES))
    assert g[0, :3] == pytest.approx(
        [-1.4765772923017222, 1.076562824432065, -0.2169697213652934]
    )


def test_the_blind_reference_is_drawn_before_any_other_random_call_in_measure():
    source = Path(tg.__file__).read_text(encoding="utf-8")
    measure_start = source.index("def measure(")
    next_def = source.index("\ndef ", measure_start + 1)
    body = source[measure_start:next_def]
    first_g = body.index("standard_normal((N_BLIND, N_AXES))")
    later_calls = [
        body.index(needle) for needle in ("exchangeable_control(rng", "rng.choice(", "bootstrap_means(rng")
    ]
    assert all(first_g < pos for pos in later_calls)


def test_bootstrap_draws_follow_the_records_order_variant_then_statistic_then_scope_then_length():
    """Draws: for union then open borders, for D-bar then D-bar-prime, for global then the zones in
    axis order, for each valid L ascending. A scope-before-statistic bug (or the reverse) produces
    calls out of step with this nesting, which the monotone check below catches."""
    v, a, axis_ids, label_items = _measure_inputs(n=100)
    calls = []
    tg.measure(
        v, a, axis_ids, label_items, tg.EPSILON,
        _on_draw=lambda variant, stat, scope, length: calls.append((variant, stat, scope, length)),
    )
    expected_scopes = ["global", *axis_ids]
    expected = [
        (variant, stat, scope, length)
        for variant in tg.VARIANTS
        for stat in ("d_bar", "d_bar_prime")
        for scope in expected_scopes
        for length in tg.GRID
    ]
    expected_index = {tag: idx for idx, tag in enumerate(expected)}
    positions = [expected_index[c] for c in calls]
    assert len(calls) > 0
    assert positions == sorted(positions)
    # the corpus is built so at least two scopes (global and one zone) have a valid L, so a
    # scope-before-statistic bug and a statistic-before-scope order are actually distinguishable.
    scopes_drawn = {tag[2] for tag in calls}
    assert len(scopes_drawn) >= 2


# Controls ----------------------------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["ceiling", "connectivity", "equal_budget", "exchangeable_direction"])
def test_each_control_fails_on_an_injected_fault_and_invalidates_every_decision(tmp_path, monkeypatch, name):
    if name == "ceiling":
        monkeypatch.setattr(tg, "ceiling_control", lambda *a, **k: False)
    elif name == "connectivity":
        monkeypatch.setattr(tg, "is_connected", lambda adj: False)
    elif name == "equal_budget":
        monkeypatch.setattr(tg, "check_equal_budget", lambda *a, **k: False)
    else:
        monkeypatch.setattr(
            tg, "exchangeable_control",
            lambda *a, **k: {"n_j": 0, "fraction": 0.0, "band": [0.0, 0.0], "passed": False},
        )
    paths, expected = _write_inputs(tmp_path)
    out = tmp_path / "out" / "TG_result.json"
    result = _run(paths, expected, out)
    assert result["valid"] is False
    assert name in result["failed_conditions"]
    assert result["controls"][name]["passed"] is False
    assert all(v is None for v in result["decision"].values())
    for variant_block in result["variants"].values():
        for scope in variant_block["scopes"]:
            assert scope["rule_1"] is None
            assert scope["rule_2"] is None
            assert scope["rule_3"] is None
            assert scope["decision"] is None


def test_equal_budget_control_fails_when_the_blind_graph_itself_is_built_wrong(tmp_path, monkeypatch):
    """|G^b| = |G+| must be checked on the built graphs, not by re-deriving relation counts from K
    and K^b: a bug in build_graph (not in the blind draw) must still be caught."""
    original_build_graph = tg.build_graph
    calls = {"n": 0}

    def fake_build_graph(n, base, j_pairs, kept_pairs):
        calls["n"] += 1
        adj = original_build_graph(n, base, j_pairs, kept_pairs)
        if calls["n"] % 3 == 0:  # g0, g_plus, g_blind in order: the third call is g_blind
            free = next(x for x in range(n) if x not in adj[0] and x != 0)
            adj[0].add(free)
            adj[free].add(0)
        return adj

    monkeypatch.setattr(tg, "build_graph", fake_build_graph)
    paths, expected = _write_inputs(tmp_path)
    out = tmp_path / "out" / "TG_result.json"
    result = _run(paths, expected, out)
    assert result["controls"]["equal_budget"]["passed"] is False
    assert "equal_budget" in result["failed_conditions"]


# A note with no zone is never an end of a judged pair ----------------------------------------------------


def test_a_note_with_eight_equal_affinities_is_never_an_end_of_a_pair_in_j(tmp_path):
    paths, expected = _write_inputs(tmp_path, equal_row=0)
    out = tmp_path / "out" / "TG_result.json"
    result = _run(paths, expected, out)
    for pair in result["pairs"]:
        assert pair["i"] != 0 and pair["j"] != 0


def test_variant_j_excludes_a_bridge_with_an_unzoned_end_even_if_already_a_relation():
    """TG.md, Zones: such a note is never an end of a pair in J -- neither a relation the variant
    has nor a candidate. variant_j's 'already a relation' arm must filter on zoned too, not just
    bridges()'s candidate arm."""
    fit_set = {0, 1, 2, 3}
    lab = np.array([0, 1, 0, 1])
    zoned = np.array([True, True, False, True])  # note 2 has no zone
    m_pairs: set = set()
    variant_pairs = {(0, 1), (2, 3)}  # (2, 3) is an existing cross-label FIT-FIT relation, not in M
    candidate_pairs: set = set()
    j = tg.variant_j(variant_pairs, m_pairs, candidate_pairs, fit_set, lab, zoned)
    assert (2, 3) not in j
    assert (0, 1) in j


def test_an_existing_relation_with_an_unzoned_end_is_excluded_from_j_in_both_variants(tmp_path, monkeypatch):
    paths, expected = _write_inputs(tmp_path, equal_row=0)
    original_build_variants = tg.build_variants
    forced: dict = {}

    def fake_build_variants(v, d, label_items, lab, epsilon):
        data = original_build_variants(v, d, label_items, lab, epsilon)
        other = next(i for i in range(len(lab)) if i % 2 == 0 and i != 0 and lab[i] != lab[0])
        pair = (0, other) if 0 < other else (other, 0)
        forced["pair"] = pair
        for name in ("union", "open_borders"):
            data[name] = data[name] | {pair}
        data["m_pairs"] = data["m_pairs"] - {pair}
        return data

    monkeypatch.setattr(tg, "build_variants", fake_build_variants)
    out = tmp_path / "out" / "TG_result.json"
    result = _run(paths, expected, out)
    judged_pairs = {(p["i"], p["j"]) for p in result["pairs"]}
    assert forced["pair"] not in judged_pairs


# A valid run writes every key of the output format -------------------------------------------------------


def test_a_valid_run_on_a_small_synthetic_corpus_writes_every_key_of_the_output_format(tmp_path):
    paths, expected = _write_inputs(tmp_path)
    out = tmp_path / "out" / "TG_result.json"
    result = _run(paths, expected, out)
    text = out.read_text(encoding="utf-8")
    assert text == json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n"
    assert set(result) == {
        "digests", "environment", "valid", "first_failed_condition", "failed_conditions",
        "conditions_checked", "zones", "pairs", "variants", "dense_reference", "decision",
        "controls", "reported",
    }
    assert result["conditions_checked"] == list(tg.CONTROL_IDENTIFIERS)
    assert result["valid"] is True
    assert result["failed_conditions"] == []

    zones = result["zones"]
    assert set(zones) == {"per_axis", "notes_in_no_zone", "zones_per_fit_note"}
    assert len(zones["per_axis"]) == 8
    for zone in zones["per_axis"]:
        assert set(zone) == {
            "axis", "n_fit", "n_eval", "tree_edges", "theta", "candidates", "kept", "marked", "vetoed",
        }

    for pair in result["pairs"]:
        assert set(pair) == {
            "i", "j", "lab_i", "lab_j", "dist", "n_sphere_without_ends", "effort", "cut", "passes",
            "foreign", "vetoed", "candidate_zones", "kept_zones", "own_sphere", "in_variants",
        }
        assert pair["i"] < pair["j"]

    assert set(result["variants"]) == {"union", "open_borders"}
    for variant in result["variants"].values():
        assert set(variant) == {"g0", "g_plus", "g_blind", "j_size", "k_size", "horizon", "scopes"}
        for graph in ("g0", "g_plus", "g_blind"):
            assert set(variant[graph]) == {"relations", "beta"}
        scope_names = [s["scope"] for s in variant["scopes"]]
        assert scope_names[0] == "global"
        assert len(scope_names) == 9
        for scope in variant["scopes"]:
            assert set(scope) == {
                "scope", "n", "d_bar", "d_bar_prime", "rule_1", "rule_2", "rule_3", "decision",
            }
            for stat_key in ("d_bar", "d_bar_prime"):
                stat = scope[stat_key]
                assert set(stat) == {"mean", "per_l"}
                assert set(stat["per_l"]) == {str(length) for length in tg.GRID}
                for per_l in stat["per_l"].values():
                    assert set(per_l) == {"valid", "n_blocks", "mean", "interval", "ranks"}
                    if per_l["valid"]:
                        assert per_l["interval"] is not None
                        assert set(per_l["ranks"]) == {str(r) for r in tg.MC_RANKS}
                    else:
                        assert per_l["interval"] is None and per_l["ranks"] is None

    assert set(result["dense_reference"]) == {"relations", "beta"}
    assert set(result["decision"]) == {"global", *[f"AXIS_{k}" for k in range(8)]}

    controls = result["controls"]
    assert set(controls) == {"exchangeable_direction", "ceiling", "connectivity", "equal_budget"}
    assert set(controls["exchangeable_direction"]) == {"n_j", "fraction", "band", "passed"}
    assert set(controls["ceiling"]) == {"passed"}
    assert set(controls["connectivity"]) == {"passed", "union", "open_borders"}
    for variant_name in ("union", "open_borders"):
        assert set(controls["connectivity"][variant_name]) == {"g0", "g_plus", "g_blind"}
    assert set(controls["equal_budget"]) == {"passed", "union", "open_borders"}

    assert set(result["reported"]) == {"kept_fraction", "foreign_note_counts"}
    assert set(result["reported"]["kept_fraction"]) == {"union", "open_borders"}
