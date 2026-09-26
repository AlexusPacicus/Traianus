"""Unit tests of tools/experiments/relational_graph_exploration.py.

Specification: the delegation contract relational-graph-exploration (B1-B8) and
docs/methodology/instrument-audit/contracts.md section 0. Synthetic inputs only: CI has no .data/, and the
exploration is never run on the real artefact here.
"""

import hashlib
import json
import math

import numpy as np
import pytest

from tools.experiments import k6_colour_predictability as k6
from tools.experiments import relational_graph_exploration as reg
from tools.experiments import zoom_three_point as zoom
from traianus.config import resolve_epsilon_edge
from traianus.geometry.observables import compute_epsilon_edges

D = 384


def _on_circle(plane, angle):
    x = np.zeros(D)
    x[plane] = math.cos(angle)
    x[plane + 1] = math.sin(angle)
    return x


def _world():
    """Rows A, B, D, C, E, F. Plane (0, 1) at angles 0, 0.5, 1.0 holds A-B-C (A-C at 2 sin 0.5 > 0.8);
    plane (2, 3) at angles 0, 0.3 holds D-E; F = e_4 is isolated. Edges (rows): 0-1, 1-3, 2-4."""
    v = np.array([
        _on_circle(0, 0.0), _on_circle(0, 0.5), _on_circle(2, 0.0),
        _on_circle(0, 1.0), _on_circle(2, 0.3), _on_circle(4, 0.0),
    ])
    labels = [
        {"label": name, "part": part}
        for name, part in zip(("n6", "n5", "n4", "n3", "n2", "n1"), ("I", "I", "I", "II", "II", "II"))
    ]
    return v, labels


def _chord(angle):
    return 2.0 * math.sin(angle / 2.0)


# T1: degrees, isolated notes and components on a known graph ------------------------------------


def test_t1_degrees_isolated_notes_and_components_of_a_known_graph():
    v, labels = _world()
    result = reg.explore(v, labels, 0.8)
    assert result["relations"]["n_edges"] == 3
    degrees = result["degrees"]
    assert degrees["isolated"] == 1
    assert (degrees["min"], degrees["max"], degrees["mean"]) == (0, 2, 1.0)
    assert (degrees["0.25"], degrees["0.5"], degrees["0.75"]) == (1.0, 1.0, 1.0)
    components = result["components"]
    assert components["count"] == 3
    assert components["sizes"] == [3, 2, 1]
    assert components["largest"] == {"size": 3, "share": 0.5}


def test_t1_components_are_the_row_sets_ordered_by_size():
    assert reg.components(6, [(0, 1, 0.5), (1, 3, 0.5), (2, 4, 0.3)]) == [[0, 1, 3], [2, 4], [5]]


# T2: relational distance is the shortest weighted path ------------------------------------------


def test_t2_the_shortest_path_is_the_two_relation_detour_and_a_disconnected_pair_stays_infinite():
    edges = [(0, 1, 1.0), (0, 2, 0.3), (1, 2, 0.4), (1, 3, 0.5)]
    w, hops = reg.relational_distances(5, edges)
    assert w[0, 1] == pytest.approx(0.7, abs=1e-15)
    assert w[0, 3] == pytest.approx(1.2, abs=1e-15)
    assert w[2, 3] == pytest.approx(0.9, abs=1e-15)
    assert np.array_equal(w, w.T)
    assert np.all(np.diag(w) == 0.0)
    assert np.all(np.isinf(w[4, :4])) and np.all(np.isinf(w[:4, 4]))
    assert hops[0, 1] == 1 and hops[0, 3] == 2 and np.isinf(hops[0, 4])


def test_t2_relational_figures_count_only_connected_pairs():
    v, labels = _world()
    ab, bc, ac = _chord(0.5), _chord(0.5), _chord(1.0)
    rel = reg.explore(v, labels, 0.8)["relational_distances"]
    assert rel["connected_pairs"] == 4
    assert rel["distance"]["count"] == 4
    assert rel["distance"]["1"] == pytest.approx(ab + bc, abs=1e-12)
    assert rel["distance"]["0"] == pytest.approx(_chord(0.3), abs=1e-12)
    assert rel["largest_component_diameter"] == pytest.approx(ab + bc, abs=1e-12)
    assert rel["hops"]["1"] == 2 and rel["hops"]["0"] == 1
    assert rel["ratio_to_direct"]["1"] == pytest.approx((ab + bc) / ac, abs=1e-12)
    assert rel["ratio_to_direct"]["0"] == pytest.approx(1.0, abs=1e-12)
    assert rel["ratio_undefined_pairs"] == 0
    assert rel["eccentricity"]["count"] == 5
    assert rel["eccentricity"]["1"] == pytest.approx(ab + bc, abs=1e-12)
    assert rel["reachable"]["count"] == 6
    assert (rel["reachable"]["0"], rel["reachable"]["1"]) == (0, 2)


# T3: parity with the engine's compute_epsilon_edges -----------------------------------------------


def test_t3_relations_equal_compute_epsilon_edges_on_random_unit_vectors():
    rng = np.random.default_rng(20260926)
    centres = rng.standard_normal((4, D))
    rows = [c + s * rng.standard_normal(D) for c in centres / np.linalg.norm(centres, axis=1, keepdims=True)
            for s in rng.uniform(0.02, 0.04, 10)]
    v = np.array([r / np.linalg.norm(r) for r in rows])
    labels = [f"L{int(k)}" for k in rng.permutation(len(v))]
    expected = compute_epsilon_edges({lab: row for lab, row in zip(labels, v)}, 0.8)
    assert 0 < len(expected) < len(v) * (len(v) - 1) // 2
    got = []
    for i, j, w in reg.relations(labels, v, 0.8):
        source, target = sorted((labels[i], labels[j]))
        got.append({"source": source, "target": target, "distance": round(w, 6)})
    assert sorted(got, key=lambda e: (e["source"], e["target"])) == expected


# T4: inputs refused on a single bit flip, nothing written -----------------------------------------


def _write_inputs(tmp_path, corrupt=None, world=_world):
    v, labels = world()
    v32 = v.astype(np.float32)
    if corrupt is not None:
        corrupt(v32, labels)
    paths = (tmp_path / "embeddings.npy", tmp_path / "labels.json")
    np.save(paths[0], v32)
    paths[1].write_text(json.dumps(labels), encoding="utf-8")
    return paths, {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def _flip_file_bit(path, pos, bit):
    data = bytearray(path.read_bytes())
    data[pos] ^= 1 << bit
    path.write_bytes(bytes(data))


def test_t4_a_single_bit_flip_in_either_input_file_is_refused_and_nothing_is_written(tmp_path):
    paths, expected = _write_inputs(tmp_path)
    reg.run(*paths, expected, tmp_path / "intact.json")
    assert (tmp_path / "intact.json").exists()
    out = tmp_path / "out" / "relational_graph_exploration.json"
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
                reg.run(*paths, expected, out)
            path.write_bytes(original)
    assert not out.parent.exists()


def test_x1_the_pinned_digests_are_the_z_scripts_for_the_same_two_files():
    assert reg.EXPECTED_DIGESTS == {zoom.EMBEDDINGS: zoom.EXPECTED_DIGESTS[zoom.EMBEDDINGS],
                                    zoom.LABELS: zoom.EXPECTED_DIGESTS[zoom.LABELS]}


@pytest.mark.parametrize(
    ("corrupt", "message"),
    [
        pytest.param(lambda v, lab: v.__setitem__((2, 5), np.nan), "row 2: non-finite", id="nan"),
        pytest.param(lambda v, lab: v.__setitem__((3, 7), 0.5), "row 3: norm", id="norm"),
        pytest.param(lambda v, lab: lab[4].__setitem__("part", ""), "label 4: part", id="empty-part"),
        pytest.param(lambda v, lab: lab[1].__setitem__("label", "n6"), "label 1: duplicate", id="duplicate"),
        pytest.param(lambda v, lab: lab.pop(), "label count 5 != row count 6", id="count"),
    ],
)
def test_x2_null_elimination_refuses_with_the_row_or_label_named_and_writes_nothing(tmp_path, corrupt, message):
    paths, expected = _write_inputs(tmp_path, corrupt)
    out = tmp_path / "out" / "relational_graph_exploration.json"
    with pytest.raises(ValueError, match=message):
        reg.run(*paths, expected, out)
    assert not out.parent.exists()


# T5: output format ------------------------------------------------------------------------------

FIGURES = {
    "relations": ("n_edges", "near_epsilon"),
    "degrees": ("isolated", "min", "0.25", "0.5", "0.75", "mean", "max"),
    "components": ("count", "sizes", "largest"),
    "relational_distances": (
        "connected_pairs", "distance", "eccentricity", "reachable", "largest_component_diameter",
        "hops", "ratio_to_direct", "ratio_undefined_pairs",
    ),
    "pairwise_distances": ("pairs", "quantiles", "share_within_epsilon"),
    "reading_order": ("consecutive_row_edges", "cross_part_edges"),
}


@pytest.mark.parametrize("epsilon", ["0.8", "0.1"], ids=["with-relations", "no-relation"])
def test_t5_the_output_is_sorted_finite_utf8_lf_json_with_every_figure(tmp_path, monkeypatch, epsilon):
    monkeypatch.setenv("TRAIANUS_EPSILON_EDGE", epsilon)
    paths, expected = _write_inputs(tmp_path)
    out = tmp_path / "out" / "relational_graph_exploration.json"
    returned = reg.run(*paths, expected, out)
    raw = out.read_bytes()
    text = raw.decode("utf-8")
    loaded = json.loads(text)
    assert loaded == returned
    assert text == json.dumps(loaded, sort_keys=True, indent=2, allow_nan=False) + "\n"
    assert b"\r" not in raw and "NaN" not in text and "Infinity" not in text
    assert loaded["kind"] == "exploration"
    assert "no hypothesis" in loaded["statement"] and "decides nothing" in loaded["statement"]
    assert loaded["digests"] == {"embeddings.npy": expected[paths[0]], "labels.json": expected[paths[1]]}
    assert loaded["epsilon"] == float(epsilon)
    assert loaded["n"] == 6
    for section, keys in FIGURES.items():
        assert set(keys) <= set(loaded[section]), section
    assert set(loaded["pairwise_distances"]["quantiles"]) == {"0.01", "0.05", "0.25", "0.5"}
    assert loaded["pairwise_distances"]["pairs"] == 15
    for key in ("distance", "eccentricity", "reachable", "hops", "ratio_to_direct"):
        assert set(loaded["relational_distances"][key]) == {"count", "0", "0.25", "0.5", "0.75", "1"}
    if epsilon == "0.1":
        rel = loaded["relational_distances"]
        assert loaded["relations"]["n_edges"] == 0 and rel["connected_pairs"] == 0
        assert rel["largest_component_diameter"] is None and rel["distance"]["0.5"] is None
        assert loaded["pairwise_distances"]["share_within_epsilon"] == 0.0


def test_t5_near_epsilon_counts_the_pairs_within_1e_6_of_epsilon():
    v, labels = _world()
    near = reg.explore(v, labels, _chord(0.5) + 5e-7)["relations"]["near_epsilon"]
    assert near["tolerance"] == 1e-6
    assert (near["pairs"], near["edges"]) == (2, 2)
    far = reg.explore(v, labels, _chord(0.5) + 2e-6)["relations"]["near_epsilon"]
    assert (far["pairs"], far["edges"]) == (0, 0)


# T6: reading order and parts ---------------------------------------------------------------------


def test_t6_consecutive_row_and_cross_part_edges_on_hand_built_labels():
    v, labels = _world()
    reading = reg.explore(v, labels, 0.8)["reading_order"]
    assert reading == {"consecutive_row_edges": 1, "cross_part_edges": 2}


# Minimum spanning tree mode (delegation contract relational-graph-mst) ----------------------------


def _arc():
    """Rows at angles 0, 0.3, 0.7, 1.5 on plane (0, 1): the tree is the path 0-1-2-3."""
    v = np.array([_on_circle(0, angle) for angle in (0.0, 0.3, 0.7, 1.5)])
    labels = [{"label": f"a{i}", "part": part} for i, part in enumerate(("I", "I", "II", "II"))]
    return v, labels


def _dyadic_world():
    """Rows with coordinates in {0, 0.25, -0.25}: each distance is the correctly rounded root of an exact sum,
    so the written bytes are the same on every platform. Rows 0-3 (sign flips {}, {0}, {0, 1}, {0, 1, 2, 3}
    on dims 0-15) are joined at 0.8 by 0-1, 0-2, 1-2, 2-3; rows 4-5 (flips 8-12, 8-13) by 4-5; row 6
    (dims 16-31) is isolated."""

    def row(start, flips):
        x = np.zeros(D)
        x[start:start + 16] = 0.25
        x[list(flips)] = -0.25
        return x

    v = np.array([row(0, ()), row(0, (0,)), row(0, (0, 1)), row(0, (0, 1, 2, 3)),
                  row(0, range(8, 13)), row(0, range(8, 14)), row(16, ())])
    parts = ("I", "I", "II", "II", "II", "III", "III")
    return v, [{"label": f"q{i}", "part": part} for i, part in enumerate(parts)]


def _main(tmp_path, monkeypatch, world, *argv):
    tmp_path.mkdir(parents=True, exist_ok=True)
    paths, expected = _write_inputs(tmp_path, world=world)
    monkeypatch.setattr(reg, "EMBEDDINGS", paths[0])
    monkeypatch.setattr(reg, "LABELS", paths[1])
    monkeypatch.setattr(reg, "EXPECTED_DIGESTS", expected)
    out = tmp_path / "out" / "result.json"
    reg.main([*argv, "--out", str(out)])
    return out


def test_mst_t1_prim_gives_the_known_tree_with_a_tie_to_the_lower_index_and_no_edge_for_one_note():
    square = np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0], [1.0, 1.0], [3.0, 0.0]])
    tree = reg.minimum_spanning_tree(reg.pairwise_distances(square))
    assert tree == [(0, 1, 1.0), (0, 2, 1.0), (1, 3, 1.0), (1, 4, 2.0)]
    assert sum(w for _, _, w in tree) == 5.0
    assert reg.minimum_spanning_tree(np.zeros((1, 1))) == []


def test_x3_the_tree_is_kruskals_on_random_points_without_ties():
    n = 30
    d = reg.pairwise_distances(np.random.default_rng(7).standard_normal((n, 5)))
    root = list(range(n))

    def find(x):
        while root[x] != x:
            x = root[x]
        return x

    expected = []
    for w, i, j in sorted((d[a, b], a, b) for a in range(n) for b in range(a + 1, n)):
        if find(i) != find(j):
            root[find(i)] = find(j)
            expected.append((i, j, float(w)))
    assert reg.minimum_spanning_tree(d) == sorted(expected)


def test_mst_t2_the_connectivity_threshold_is_the_smallest_epsilon_joining_every_note():
    rng = np.random.default_rng(20260926)
    v = rng.standard_normal((40, D))
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    names = [f"L{i}" for i in range(len(v))]
    threshold = reg.explore(v, [{"label": name, "part": "I"} for name in names], None)["mst"]["connectivity_epsilon"]
    assert len(reg.components(len(v), reg.relations(names, v, threshold))) == 1
    below = float(np.nextafter(threshold, 0.0))
    assert len(reg.components(len(v), reg.relations(names, v, below))) > 1


def test_mst_t3_the_printed_threshold_round_trips_through_traianus_epsilon_edge(tmp_path, monkeypatch, capsys):
    out = _main(tmp_path, monkeypatch, _world, "--relations", "mst")
    reported = json.loads(out.read_text(encoding="utf-8"))["mst"]["connectivity_epsilon"]
    line = capsys.readouterr().out
    assert "relations=mst " in line
    printed = line.split("connectivity_epsilon=")[1].split()[0]
    assert printed == repr(reported)
    monkeypatch.setenv("TRAIANUS_EPSILON_EDGE", printed)
    assert resolve_epsilon_edge() == reported


def test_mst_t4_the_tree_mode_figures_on_a_known_tree():
    v, labels = _arc()
    result = reg.explore(v, labels, None)
    steps = [_chord(0.3), _chord(0.4), _chord(0.8)]
    paths = [steps[0], steps[0] + steps[1], sum(steps), steps[1], steps[1] + steps[2], steps[2]]
    relations = result["relations"]
    assert "minimum spanning tree" in relations["source"]
    assert relations["n_edges"] == 3 and relations["near_epsilon"] is None
    assert result["components"]["sizes"] == [4]
    degrees = result["degrees"]
    assert degrees["mean"] * 4 == 2 * 3
    assert (degrees["isolated"], degrees["min"], degrees["max"]) == (0, 1, 2)
    rel = result["relational_distances"]
    assert rel["connected_pairs"] == 6
    for q in ("0", "0.25", "0.5", "0.75", "1"):
        assert rel["distance"][q] == pytest.approx(float(np.quantile(paths, float(q))), abs=1e-12)
    assert rel["largest_component_diameter"] == pytest.approx(sum(steps), abs=1e-12)
    assert rel["hops"]["1"] == 3
    assert result["pairwise_distances"]["share_within_epsilon"] is None
    mst = result["mst"]
    tree = reg.minimum_spanning_tree(reg.pairwise_distances(v))
    assert mst["connectivity_epsilon"] == max(w for _, _, w in tree)
    assert mst["connectivity_epsilon"] == pytest.approx(steps[2], abs=1e-12)
    assert mst["total_weight"] == pytest.approx(sum(steps), abs=1e-12)
    for q in ("0", "0.25", "0.5", "0.75", "1"):
        assert mst["weights"][q] == pytest.approx(float(np.quantile(steps, float(q))), abs=1e-12)
    assert result["reading_order"] == {"consecutive_row_edges": 3, "cross_part_edges": 1}


def test_mst_t4_the_tree_mode_file_is_sorted_finite_json_with_every_figure(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAIANUS_EPSILON_EDGE", "0.1")
    paths, expected = _write_inputs(tmp_path)
    out = tmp_path / "out" / "relational_graph_exploration.json"
    returned = reg.run(*paths, expected, out, "mst")
    text = out.read_text(encoding="utf-8")
    loaded = json.loads(text)
    assert loaded == returned
    assert text == json.dumps(loaded, sort_keys=True, indent=2, allow_nan=False) + "\n"
    assert "NaN" not in text and "Infinity" not in text
    assert loaded["epsilon"] is None and loaded["pairwise_distances"]["share_within_epsilon"] is None
    assert loaded["relations"]["n_edges"] == 5 and loaded["components"]["sizes"] == [6]
    for section, keys in FIGURES.items():
        assert set(keys) <= set(loaded[section]), section
    assert set(loaded["mst"]) == {"connectivity_epsilon", "total_weight", "weights"}
    assert set(loaded["mst"]["weights"]) == {"count", "0", "0.25", "0.5", "0.75", "1"}
    assert loaded["mst"]["weights"]["count"] == 5


# sha256 of the file the code at base commit 620270f writes for _dyadic_world, environment fixed
BASE_COMMIT_OUTPUT_SHA256 = "de1e4970bad6f48d48dd0d88f9e8d8f9c84d85060e557456b580afdb4f94f356"


def test_mst_t5_the_default_output_is_byte_identical_to_the_base_commit(tmp_path, monkeypatch):
    monkeypatch.delenv("TRAIANUS_EPSILON_EDGE", raising=False)
    monkeypatch.setattr(reg, "environment", lambda: {"fixed": True})
    out = _main(tmp_path, monkeypatch, _dyadic_world)
    assert hashlib.sha256(out.read_bytes()).hexdigest() == BASE_COMMIT_OUTPUT_SHA256


def test_x4_relations_epsilon_writes_the_default_bytes_and_the_summary_names_the_mode(tmp_path, monkeypatch, capsys):
    monkeypatch.delenv("TRAIANUS_EPSILON_EDGE", raising=False)
    monkeypatch.setattr(reg, "environment", lambda: {"fixed": True})
    default = _main(tmp_path / "default", monkeypatch, _dyadic_world).read_bytes()
    explicit = _main(tmp_path / "explicit", monkeypatch, _dyadic_world, "--relations", "epsilon").read_bytes()
    assert explicit == default
    assert capsys.readouterr().out.count("relations=epsilon ") == 2


# sha256 of the file the code at base commit fd24696 writes for _dyadic_world in mst mode, environment fixed
BASE_COMMIT_MST_OUTPUT_SHA256 = "ed4c641f8fa3307b25447163eea5aa6d09d66a90189e6be0f04115848b561d63"


def test_x5_the_mst_mode_output_is_byte_identical_to_the_base_commit(tmp_path, monkeypatch):
    monkeypatch.delenv("TRAIANUS_EPSILON_EDGE", raising=False)
    monkeypatch.setattr(reg, "environment", lambda: {"fixed": True})
    out = _main(tmp_path, monkeypatch, _dyadic_world, "--relations", "mst")
    assert hashlib.sha256(out.read_bytes()).hexdigest() == BASE_COMMIT_MST_OUTPUT_SHA256


# Union mode (delegation contract relational-graph-union) ------------------------------------------

QUANTILE_KEYS = ("0", "0.25", "0.5", "0.75", "1")


def _union_world():
    """Rows at angles 0, 0.3, 0.7, 1.7, 2.05, 3.25 on plane (0, 1). At 0.8 the epsilon-relations are 0-1, 0-2, 1-2
    and 3-4 (components {0, 1, 2}, {3, 4} and the isolated row 5); the tree is the path 0-1-2-3-4-5, which shares
    0-1, 1-2 and 3-4 with them and adds 2-3 and 4-5."""
    v = np.array([_on_circle(0, angle) for angle in (0.0, 0.3, 0.7, 1.7, 2.05, 3.25)])
    labels = [{"label": f"u{i}", "part": part} for i, part in enumerate(("I", "I", "I", "II", "II", "III"))]
    return v, labels


def test_union_t1_the_union_keeps_every_epsilon_relation_and_adds_only_the_tree_links():
    v, labels = _union_world()
    d = reg.pairwise_distances(v)
    epsilon_edges = reg.relations([item["label"] for item in labels], v, 0.8)
    tree = reg.minimum_spanning_tree(d)
    assert [(i, j) for i, j, _ in epsilon_edges] == [(0, 1), (0, 2), (1, 2), (3, 4)]
    assert [(i, j) for i, j, _ in tree] == [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5)]
    pairs = [(0, 1), (0, 2), (1, 2), (2, 3), (3, 4), (4, 5)]
    assert reg.union_edges(epsilon_edges, tree, d) == [(i, j, float(d[i, j])) for i, j in pairs]
    result = reg.explore(v, labels, 0.8, union=True)
    assert "union" in result["relations"]["source"]
    assert result["relations"]["n_edges"] == 6
    assert result["components"]["sizes"] == [6]
    assert result["degrees"]["isolated"] == 0
    union = result["union"]
    assert (union["epsilon_relations"], union["tree_edges"], union["added_links"]) == (4, 5, 2)


def test_union_t2_the_union_block_figures_on_the_known_world():
    v, labels = _union_world()
    added = [_chord(1.0), _chord(1.2)]
    union = reg.explore(v, labels, 0.8, union=True)["union"]
    assert union["added_link_distances"]["count"] == 2
    for q in QUANTILE_KEYS:
        assert union["added_link_distances"][q] == pytest.approx(float(np.quantile(added, float(q))), abs=1e-12)
    assert union["isolated_reached_only_by_added_links"] == 1
    bare = reg.explore(v, labels, 0.1, union=True)["union"]
    assert (bare["epsilon_relations"], bare["tree_edges"], bare["added_links"]) == (0, 5, 5)
    assert bare["isolated_reached_only_by_added_links"] == 6


def test_union_t2_near_epsilon_and_the_tree_block_are_those_of_the_other_modes():
    v, labels = _union_world()
    epsilon = _chord(1.0) - 5e-7
    result = reg.explore(v, labels, epsilon, union=True)
    near = result["relations"]["near_epsilon"]
    assert near == reg.explore(v, labels, epsilon)["relations"]["near_epsilon"]
    assert (near["pairs"], near["edges"]) == (1, 0)
    assert result["mst"] == reg.explore(v, labels, None)["mst"]
    assert result["pairwise_distances"]["share_within_epsilon"] == 4 / 15


def test_union_t2_the_union_mode_file_is_sorted_finite_json_with_every_section(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAIANUS_EPSILON_EDGE", "0.8")
    paths, expected = _write_inputs(tmp_path, world=_union_world)
    out = tmp_path / "out" / "relational_graph_exploration_union.json"
    returned = reg.run(*paths, expected, out, "union")
    raw = out.read_bytes()
    text = raw.decode("utf-8")
    loaded = json.loads(text)
    assert loaded == returned
    assert text == json.dumps(loaded, sort_keys=True, indent=2, allow_nan=False) + "\n"
    assert b"\r" not in raw and "NaN" not in text and "Infinity" not in text
    assert loaded["epsilon"] == resolve_epsilon_edge() == 0.8
    assert loaded["relations"]["n_edges"] == 6 and loaded["components"]["sizes"] == [6]
    for section, keys in FIGURES.items():
        assert set(keys) <= set(loaded[section]), section
    assert set(loaded["mst"]) == {"connectivity_epsilon", "total_weight", "weights"}
    assert set(loaded["union"]) == {
        "epsilon_relations", "tree_edges", "added_links", "added_link_distances",
        "isolated_reached_only_by_added_links",
    }
    assert set(loaded["union"]["added_link_distances"]) == {"count", *QUANTILE_KEYS}


def test_union_t4_the_summary_line_and_the_default_output_path(tmp_path, monkeypatch, capsys):
    assert reg.RESULT_UNION == reg.REPO_ROOT / "data" / "refapp" / "relational_graph_exploration_union.json"
    monkeypatch.setenv("TRAIANUS_EPSILON_EDGE", "0.8")
    paths, expected = _write_inputs(tmp_path, world=_union_world)
    monkeypatch.setattr(reg, "EMBEDDINGS", paths[0])
    monkeypatch.setattr(reg, "LABELS", paths[1])
    monkeypatch.setattr(reg, "EXPECTED_DIGESTS", expected)
    default = tmp_path / "default" / "relational_graph_exploration_union.json"
    monkeypatch.setattr(reg, "RESULT_UNION", default)
    reg.main(["--relations", "union"])
    assert json.loads(default.read_text(encoding="utf-8"))["union"]["added_links"] == 2
    line = capsys.readouterr().out
    assert line == f"relational graph: n=6 relations=union epsilon=0.8 edges=6 added_links=2 components=1 -> {default}\n"
    overridden = _main(tmp_path / "override", monkeypatch, _union_world, "--relations", "union")
    assert json.loads(overridden.read_text(encoding="utf-8"))["relations"]["n_edges"] == 6


# Cells mode (delegation contract relational-graph-cells) ------------------------------------------

CELL_KEYS = {"axis", "size", "epsilon_c", "tree_weights", "within_cell_relations"}


def _axes(scale=(1.0, 0.5, 3.0, 2.0, 1.0, 1.0, 1.0, 1.0)):
    """Axis k = scale_k e_k: eight axes of unequal norms whose normalised form is exactly e_k."""
    a = np.zeros((8, D))
    for k, s in enumerate(scale):
        a[k, k] = s
    return [f"ax{k}" for k in range(8)], a


def _cells_world():
    """Plane rows and the axes +x, +y, -x, -y. Cell 0 holds rows 0, 2, 4, 6 at (10, 0), (10, 1), (10, 3), (10, 7):
    its tree is 0-2, 2-4, 4-6 (1, 2, 4), and at epsilon_c = 4 its relations add 0-4 (3) but not 2-6 (6) or 0-6 (7).
    Cell 1 holds rows 1, 5 at (0, 20), (2, 20), epsilon_c 2; cell 2 holds row 3 at (-10, 0) alone; cell 3 is empty.
    The global tree joins the cells by 5-6 (sqrt 233) and 0-3 (20); the nearest pair of cells 1 and 2, 1-3
    (sqrt 500), is not a tree edge. Integer coordinates: every distance is a correctly rounded root."""
    v = np.array([[10, 0], [0, 20], [10, 1], [-10, 0], [10, 3], [2, 20], [10, 7]], dtype=float)
    a = np.array([[1, 0], [0, 1], [-1, 0], [0, -1]], dtype=float)
    labels = [{"label": f"c{i}", "part": part} for i, part in enumerate(("I", "I", "I", "II", "II", "II", "III"))]
    return v, (["x", "y", "-x", "-y"], a), labels


def _write_cells_inputs(tmp_path, corrupt_axes=None, world=_world):
    paths, expected = _write_inputs(tmp_path, world=world)
    ids, a = _axes()
    if corrupt_axes is not None:
        corrupt_axes(a)
    axes = tmp_path / "nsm_axes_8.json"
    axes.write_text(json.dumps([{"id": i, "vector": row.tolist()} for i, row in zip(ids, a)]), encoding="utf-8")
    return (*paths, axes), {**expected, axes: hashlib.sha256(axes.read_bytes()).hexdigest()}


def test_cells_t1_each_note_goes_to_its_normalised_dominant_axis_and_a_tie_to_the_lower_index():
    _, a = _axes((1.0, 0.5, 3.0, 10.0, 1.0, 1.0, 1.0, 2.0))
    s = math.sqrt(0.5)
    notes = np.zeros((5, D))
    notes[0, 0] = 1.0
    notes[1, [1, 2]] = s
    notes[2, [3, 4]] = (0.6, 0.8)
    notes[3, 7] = 1.0
    notes[4, [5, 6]] = s
    assert reg.axis_cells(notes, a).tolist() == [0, 1, 4, 7, 5]
    raw = np.argmax(notes @ a.T, axis=1).tolist()
    assert (raw[1], raw[2]) == (2, 3)


def test_x6_axis_cells_are_the_z_scripts_attractor_of_the_normalised_axes():
    rng = np.random.default_rng(20260926)
    v = rng.standard_normal((60, D))
    a = rng.standard_normal((8, D)) * rng.uniform(0.1, 10.0, (8, 1))
    a_hat = np.array([a_k / np.sqrt(a_k @ a_k) for a_k in a])
    assert np.array_equal(reg.axis_cells(v, a), zoom.attractor(v @ a_hat.T))


def test_x7_the_pinned_axes_file_and_digest_are_the_z_scripts():
    assert reg.AXES == zoom.AXES
    assert reg.AXES_DIGEST == zoom.EXPECTED_DIGESTS[zoom.AXES]


def test_cells_t2_per_cell_thresholds_within_cell_relations_and_cross_cell_tree_links_on_a_known_world():
    v, (ids, a), labels = _cells_world()
    d = reg.pairwise_distances(v)
    cells = reg.axis_cells(v, a)
    assert cells.tolist() == [0, 1, 0, 2, 0, 1, 0]
    trees, within, cross = reg.cell_graph(d, cells, len(a))
    assert trees == [[(0, 2, 1.0), (2, 4, 2.0), (4, 6, 4.0)], [(1, 5, 2.0)], [], []]
    assert within == [(0, 2, 1.0), (0, 4, 3.0), (1, 5, 2.0), (2, 4, 2.0), (4, 6, 4.0)]
    assert cross == [(0, 3, 20.0), (5, 6, math.sqrt(233.0))]
    result = reg.explore(v, labels, None, axes=(ids, a))
    relations = result["relations"]
    assert "cell" in relations["source"] and relations["near_epsilon"] is None
    assert relations["n_edges"] == 7
    assert result["components"]["sizes"] == [7] and result["degrees"]["isolated"] == 0
    assert result["pairwise_distances"]["share_within_epsilon"] is None
    block = result["cells"]
    per_axis = block["per_axis"]
    assert [c["axis"] for c in per_axis] == ids
    assert [c["size"] for c in per_axis] == [4, 2, 1, 0]
    assert [c["epsilon_c"] for c in per_axis] == [4.0, 2.0, None, None]
    assert [c["within_cell_relations"] for c in per_axis] == [4, 1, 0, 0]
    assert per_axis[0]["tree_weights"] == {"count": 3, "0": 1.0, "0.25": 1.5, "0.5": 2.0, "0.75": 3.0, "1": 4.0}
    assert per_axis[1]["tree_weights"] == {"count": 1, "0": 2.0, "0.25": 2.0, "0.5": 2.0, "0.75": 2.0, "1": 2.0}
    assert per_axis[2]["tree_weights"] == {"count": 0, **dict.fromkeys(QUANTILE_KEYS)}
    links = block["cross_cell_links"]
    assert links["count"] == 2
    assert (links["0"], links["1"]) == (math.sqrt(233.0), 20.0)


def test_cells_t3_a_single_bit_flip_in_the_axes_file_is_refused_and_nothing_is_written(tmp_path):
    (embeddings, labels, axes), expected = _write_cells_inputs(tmp_path)
    reg.run(embeddings, labels, expected, tmp_path / "intact.json", "cells", axes)
    assert (tmp_path / "intact.json").exists()
    out = tmp_path / "out" / "relational_graph_exploration_cells.json"
    rng = np.random.default_rng(3)
    size = axes.stat().st_size
    for pos in sorted({0, size - 1, int(rng.integers(0, size)), int(rng.integers(0, size))}):
        original = axes.read_bytes()
        _flip_file_bit(axes, pos, int(rng.integers(0, 8)))
        with pytest.raises(k6.IntegrityError, match=axes.name):
            reg.run(embeddings, labels, expected, out, "cells", axes)
        axes.write_bytes(original)
    assert not out.parent.exists()


@pytest.mark.parametrize(
    ("corrupt", "message"),
    [
        pytest.param(lambda a: a.__setitem__(3, 0.0), "axis ax3: zero norm", id="zero-norm"),
        pytest.param(lambda a: a.__setitem__((5, 9), np.inf), "axis ax5: non-finite", id="inf"),
    ],
)
def test_x8_cells_mode_refuses_null_axes_and_an_unpinned_axes_file_writing_nothing(tmp_path, corrupt, message):
    (embeddings, labels, axes), expected = _write_cells_inputs(tmp_path, corrupt)
    out = tmp_path / "out" / "relational_graph_exploration_cells.json"
    with pytest.raises(ValueError, match=message):
        reg.run(embeddings, labels, expected, out, "cells", axes)
    unpinned = {p: digest for p, digest in expected.items() if p != axes}
    with pytest.raises(ValueError, match="axes"):
        reg.run(embeddings, labels, unpinned, out, "cells", axes)
    with pytest.raises(ValueError, match="axes"):
        reg.run(embeddings, labels, expected, out, "cells")
    assert not out.parent.exists()


def test_cells_t4_the_cells_mode_file_is_sorted_finite_json_with_every_section(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAIANUS_EPSILON_EDGE", "0.8")
    (embeddings, labels, axes), expected = _write_cells_inputs(tmp_path)
    out = tmp_path / "out" / "relational_graph_exploration_cells.json"
    returned = reg.run(embeddings, labels, expected, out, "cells", axes)
    raw = out.read_bytes()
    text = raw.decode("utf-8")
    loaded = json.loads(text)
    assert loaded == returned
    assert text == json.dumps(loaded, sort_keys=True, indent=2, allow_nan=False) + "\n"
    assert b"\r" not in raw and "NaN" not in text and "Infinity" not in text
    assert loaded["kind"] == "exploration" and loaded["epsilon"] is None and loaded["n"] == 6
    assert loaded["digests"] == {
        "embeddings.npy": expected[embeddings], "labels.json": expected[labels], "nsm_axes_8.json": expected[axes],
    }
    for section, keys in FIGURES.items():
        assert set(keys) <= set(loaded[section]), section
    assert loaded["relations"]["near_epsilon"] is None and "cell" in loaded["relations"]["source"]
    assert loaded["pairwise_distances"]["share_within_epsilon"] is None
    assert loaded["components"]["sizes"] == [6]
    cells = loaded["cells"]
    assert set(cells) == {"partition", "axes_digest", "per_axis", "cross_cell_links"}
    assert cells["axes_digest"] == expected[axes]
    assert [c["axis"] for c in cells["per_axis"]] == [f"ax{k}" for k in range(8)]
    assert [c["size"] for c in cells["per_axis"]] == [2, 1, 2, 0, 1, 0, 0, 0]
    for cell in cells["per_axis"]:
        assert set(cell) == CELL_KEYS
        assert set(cell["tree_weights"]) == {"count", *QUANTILE_KEYS}
    assert set(cells["cross_cell_links"]) == {"count", *QUANTILE_KEYS}


def _main_cells(tmp_path, monkeypatch, *argv):
    tmp_path.mkdir(parents=True, exist_ok=True)
    (embeddings, labels, axes), expected = _write_cells_inputs(tmp_path)
    monkeypatch.setattr(reg, "EMBEDDINGS", embeddings)
    monkeypatch.setattr(reg, "LABELS", labels)
    monkeypatch.setattr(reg, "AXES", axes)
    monkeypatch.setattr(reg, "EXPECTED_DIGESTS", {p: expected[p] for p in (embeddings, labels)})
    monkeypatch.setattr(reg, "AXES_DIGEST", expected[axes])
    reg.main(["--relations", "cells", *argv])


def test_x9_the_cells_summary_line_the_default_output_path_and_its_override(tmp_path, monkeypatch, capsys):
    assert "cells" in reg.MODES
    assert reg.RESULT_CELLS == reg.REPO_ROOT / "data" / "refapp" / "relational_graph_exploration_cells.json"
    default = tmp_path / "default" / "relational_graph_exploration_cells.json"
    monkeypatch.setattr(reg, "RESULT_CELLS", default)
    _main_cells(tmp_path / "a", monkeypatch)
    assert json.loads(default.read_text(encoding="utf-8"))["cells"]["cross_cell_links"]["count"] == 3
    line = capsys.readouterr().out
    assert line == f"relational graph: n=6 relations=cells edges=5 cross_cell_links=3 components=1 -> {default}\n"
    overridden = tmp_path / "override" / "result.json"
    _main_cells(tmp_path / "b", monkeypatch, "--out", str(overridden))
    assert json.loads(overridden.read_text(encoding="utf-8"))["relations"]["n_edges"] == 5


# sha256 of the files the code at base commit d8c6f3c writes for _dyadic_world in union and cells modes, environment
# fixed
BASE_COMMIT_UNION_OUTPUT_SHA256 = "55a0361bf8a2a80c3a744d9c65744a6feb7b445322061e0d984b6efc40ba2834"
BASE_COMMIT_CELLS_OUTPUT_SHA256 = "becb5406ba93824da3a653bab99b808af7bc93ef18df4136c1a780d757a19436"


def test_x10_the_union_mode_output_is_byte_identical_to_the_base_commit(tmp_path, monkeypatch):
    monkeypatch.delenv("TRAIANUS_EPSILON_EDGE", raising=False)
    monkeypatch.setattr(reg, "environment", lambda: {"fixed": True})
    out = _main(tmp_path, monkeypatch, _dyadic_world, "--relations", "union")
    assert hashlib.sha256(out.read_bytes()).hexdigest() == BASE_COMMIT_UNION_OUTPUT_SHA256


def test_x11_the_cells_mode_output_is_byte_identical_to_the_base_commit(tmp_path, monkeypatch):
    monkeypatch.setattr(reg, "environment", lambda: {"fixed": True})
    (embeddings, labels, axes), expected = _write_cells_inputs(tmp_path, world=_dyadic_world)
    out = tmp_path / "out" / "result.json"
    reg.run(embeddings, labels, expected, out, "cells", axes)
    assert hashlib.sha256(out.read_bytes()).hexdigest() == BASE_COMMIT_CELLS_OUTPUT_SHA256


# Cells median mode (delegation contract relational-graph-cells-median) ----------------------------

MEDIAN_CELLS_KEYS = {"partition", "axes_digest", "per_axis", "tree_edges", "added_links", "added_link_distances"}
MEDIAN_CELL_KEYS = {"axis", "size", "median_c", "tree_weights", "within_cell_relations"}
NEAREST_KEYS = {"definition", "distance", "other_cell", "outside_tree", "per_axis", "notes"}


def _median_world():
    """Plane rows and the axes +x, +y, -x, -y. Cell 0 holds rows 0, 2, 4, 6, 7 at (20, y), y = 0, 1, 3, 7, 15: its
    tree is 0-2, 2-4, 4-6, 6-7 (1, 2, 4, 8), median_c = (2 + 4) / 2 = 3, and its relations are 0-2, 2-4 and 0-4 (3,
    at median_c) but not 4-6 (4). Cell 1 holds row 1 at (0, 30) alone; cell 2 holds rows 3, 5 at (-20, 0), (-20, 2),
    median_c 2; cell 3 is empty. The global tree is 0-2, 2-4, 4-6, 6-7, 3-5, 1-7 (25) and 1-5 (sqrt 1184), so 4-6,
    6-7, 1-7 and 1-5 are the added links. Integer coordinates: every distance is a correctly rounded root."""
    v = np.array([[20, 0], [0, 30], [20, 1], [-20, 0], [20, 3], [-20, 2], [20, 7], [20, 15]], dtype=float)
    a = np.array([[1, 0], [0, 1], [-1, 0], [0, -1]], dtype=float)
    parts = ("I", "I", "I", "II", "II", "II", "III", "III")
    return v, (["x", "y", "-x", "-y"], a), [{"label": f"m{i}", "part": part} for i, part in enumerate(parts)]


def test_cells_median_t1_per_cell_median_thresholds_and_the_union_with_the_global_tree_on_a_known_world():
    v, (ids, a), labels = _median_world()
    d = reg.pairwise_distances(v)
    cells = reg.axis_cells(v, a)
    assert cells.tolist() == [0, 1, 0, 2, 0, 2, 0, 0]
    assert reg.median_threshold([1.0, 2.0, 4.0, 8.0]) == 3.0
    trees, within, cross = reg.cell_graph(d, cells, len(a), reg.median_threshold)
    assert trees == [[(0, 2, 1.0), (2, 4, 2.0), (4, 6, 4.0), (6, 7, 8.0)], [], [(3, 5, 2.0)], []]
    assert within == [(0, 2, 1.0), (0, 4, 3.0), (2, 4, 2.0), (3, 5, 2.0)]
    assert cross == [(1, 5, math.sqrt(1184.0)), (1, 7, 25.0)]
    result = reg.explore(v, labels, None, axes=(ids, a), median=True)
    relations = result["relations"]
    assert "median" in relations["source"] and relations["near_epsilon"] is None
    assert relations["n_edges"] == 8
    assert result["components"]["sizes"] == [8]
    degrees = result["degrees"]
    assert (degrees["isolated"], degrees["min"], degrees["max"], degrees["mean"]) == (0, 1, 3, 2.0)
    assert result["reading_order"] == {"consecutive_row_edges": 1, "cross_part_edges": 5}
    assert result["pairwise_distances"]["share_within_epsilon"] is None
    assert "mst" not in result and "union" not in result
    block = result["cells"]
    assert set(block) == MEDIAN_CELLS_KEYS - {"axes_digest"}
    assert "median_c" in block["partition"]
    per_axis = block["per_axis"]
    assert [c["axis"] for c in per_axis] == ids
    assert [c["size"] for c in per_axis] == [5, 1, 2, 0]
    assert [c["median_c"] for c in per_axis] == [3.0, None, 2.0, None]
    assert [c["within_cell_relations"] for c in per_axis] == [3, 0, 1, 0]
    assert per_axis[0]["tree_weights"] == {"count": 4, "0": 1.0, "0.25": 1.75, "0.5": 3.0, "0.75": 5.0, "1": 8.0}
    assert per_axis[1]["tree_weights"] == {"count": 0, **dict.fromkeys(QUANTILE_KEYS)}
    for cell in per_axis:
        assert set(cell) == MEDIAN_CELL_KEYS
    assert (block["tree_edges"], block["added_links"]) == (7, 4)
    added = [4.0, 8.0, 25.0, math.sqrt(1184.0)]
    assert block["added_link_distances"]["count"] == 4
    for q in QUANTILE_KEYS:
        assert block["added_link_distances"][q] == pytest.approx(float(np.quantile(added, float(q))), abs=1e-12)
    assert reg.explore(v, labels, None, axes=(ids, a))["cells"]["per_axis"][0]["epsilon_c"] == 8.0


def test_cells_median_t2_nearest_neighbours_with_ties_cells_order_and_edges_outside_the_tree():
    d = np.array([[0.0, 3.0, 2.0, 1.0], [3.0, 0.0, 2.0, 2.0], [2.0, 2.0, 0.0, 2.0], [1.0, 2.0, 2.0, 0.0]])
    tree = reg.minimum_spanning_tree(d)
    assert tree == [(0, 2, 2.0), (0, 3, 1.0), (1, 3, 2.0)]
    nearest, distance = reg.nearest_neighbours(d)
    assert nearest.tolist() == [3, 2, 0, 0]
    assert distance.tolist() == [1.0, 2.0, 2.0, 1.0]
    labels = [{"label": f"t{i}", "part": part} for i, part in enumerate(("I", "I", "II", "II"))]
    block = reg.nearest_neighbour_figures(d, tree, np.array([0, 1, 0, 0]), ["a", "b", "c"], labels)
    assert set(block) == NEAREST_KEYS
    assert "minimum spanning tree" in block["definition"]
    assert block["outside_tree"] == 1
    assert block["other_cell"] == {"count": 1, "share": 0.25}
    assert block["distance"] == {"count": 4, "0": 1.0, "0.25": 1.0, "0.5": 1.5, "0.75": 2.0, "1": 2.0}
    per_axis = block["per_axis"]
    assert [c["axis"] for c in per_axis] == ["a", "b", "c"]
    assert [c["other_cell"] for c in per_axis] == [
        {"count": 0, "share": 0.0}, {"count": 1, "share": 1.0}, {"count": 0, "share": None},
    ]
    assert per_axis[0]["distance"] == {"count": 3, "0": 1.0, "0.25": 1.0, "0.5": 1.0, "0.75": 1.5, "1": 2.0}
    assert per_axis[2]["distance"] == {"count": 0, **dict.fromkeys(QUANTILE_KEYS)}
    notes = block["notes"]
    assert [(note["row"], note["neighbour"]["row"]) for note in notes] == [(1, 2), (2, 0), (0, 3), (3, 0)]
    assert [note["same_cell"] for note in notes] == [False, True, True, True]
    assert notes[0] == {
        "row": 1, "label": "t1", "part": "I", "axis": "b",
        "neighbour": {"row": 2, "label": "t2", "part": "II", "axis": "a"},
        "distance": 2.0, "same_cell": False,
    }
    assert reg.nearest_neighbours(np.zeros((1, 1)))[0].tolist() == []


def test_cells_median_t2_the_nearest_neighbours_of_a_known_world():
    v, (ids, a), labels = _median_world()
    block = reg.explore(v, labels, None, axes=(ids, a), median=True)["nearest_neighbours"]
    notes = block["notes"]
    assert [(note["row"], note["neighbour"]["row"]) for note in notes] == [
        (1, 7), (7, 6), (6, 4), (3, 5), (4, 2), (5, 3), (0, 2), (2, 0),
    ]
    assert [note["distance"] for note in notes] == [25.0, 8.0, 4.0, 2.0, 2.0, 2.0, 1.0, 1.0]
    assert notes[0]["axis"] == "y" and notes[0]["neighbour"]["axis"] == "x" and not notes[0]["same_cell"]
    assert all(note["same_cell"] for note in notes[1:])
    assert block["other_cell"] == {"count": 1, "share": 1 / 8}
    assert [c["other_cell"]["count"] for c in block["per_axis"]] == [0, 1, 0, 0]
    assert [c["distance"]["count"] for c in block["per_axis"]] == [5, 1, 2, 0]
    assert block["outside_tree"] == 0


def test_cells_median_t3_the_cells_median_file_is_sorted_finite_json_with_every_section(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAIANUS_EPSILON_EDGE", "0.8")
    (embeddings, labels, axes), expected = _write_cells_inputs(tmp_path)
    out = tmp_path / "out" / "relational_graph_exploration_cells_median.json"
    returned = reg.run(embeddings, labels, expected, out, "cells_median", axes)
    raw = out.read_bytes()
    text = raw.decode("utf-8")
    loaded = json.loads(text)
    assert loaded == returned
    assert text == json.dumps(loaded, sort_keys=True, indent=2, allow_nan=False) + "\n"
    assert b"\r" not in raw and "NaN" not in text and "Infinity" not in text
    assert loaded["kind"] == "exploration" and loaded["epsilon"] is None and loaded["n"] == 6
    assert loaded["digests"] == {
        "embeddings.npy": expected[embeddings], "labels.json": expected[labels], "nsm_axes_8.json": expected[axes],
    }
    for section, keys in FIGURES.items():
        assert set(keys) <= set(loaded[section]), section
    assert loaded["relations"]["near_epsilon"] is None and "median" in loaded["relations"]["source"]
    assert loaded["components"]["sizes"] == [6]
    cells = loaded["cells"]
    assert set(cells) == MEDIAN_CELLS_KEYS
    assert cells["axes_digest"] == expected[axes]
    assert [c["axis"] for c in cells["per_axis"]] == [f"ax{k}" for k in range(8)]
    for cell in cells["per_axis"]:
        assert set(cell) == MEDIAN_CELL_KEYS
        assert set(cell["tree_weights"]) == {"count", *QUANTILE_KEYS}
    assert cells["tree_edges"] == 5
    assert set(cells["added_link_distances"]) == {"count", *QUANTILE_KEYS}
    nearest = loaded["nearest_neighbours"]
    assert set(nearest) == NEAREST_KEYS
    assert set(nearest["distance"]) == {"count", *QUANTILE_KEYS} and nearest["distance"]["count"] == 6
    assert len(nearest["per_axis"]) == 8 and len(nearest["notes"]) == 6


def test_x12_the_cells_median_summary_line_the_default_output_path_and_its_override(tmp_path, monkeypatch, capsys):
    assert "cells_median" in reg.MODES
    assert reg.RESULT_CELLS_MEDIAN == reg.REPO_ROOT / "data" / "refapp" / "relational_graph_exploration_cells_median.json"
    default = tmp_path / "default" / "relational_graph_exploration_cells_median.json"
    monkeypatch.setattr(reg, "RESULT_CELLS_MEDIAN", default)
    monkeypatch.setattr(reg, "RESULT_CELLS", tmp_path / "cells" / "unused.json")
    tmp_path.joinpath("a").mkdir()
    (embeddings, labels, axes), expected = _write_cells_inputs(tmp_path / "a")
    monkeypatch.setattr(reg, "EMBEDDINGS", embeddings)
    monkeypatch.setattr(reg, "LABELS", labels)
    monkeypatch.setattr(reg, "AXES", axes)
    monkeypatch.setattr(reg, "EXPECTED_DIGESTS", {p: expected[p] for p in (embeddings, labels)})
    monkeypatch.setattr(reg, "AXES_DIGEST", expected[axes])
    reg.main(["--relations", "cells_median"])
    loaded = json.loads(default.read_text(encoding="utf-8"))
    assert loaded["epsilon"] is None and not (tmp_path / "cells").exists()
    line = capsys.readouterr().out
    assert line == (
        f"relational graph: n=6 relations=cells_median edges={loaded['relations']['n_edges']} "
        f"added_links={loaded['cells']['added_links']} components={loaded['components']['count']} -> {default}\n"
    )
    overridden = tmp_path / "override" / "result.json"
    reg.main(["--relations", "cells_median", "--out", str(overridden)])
    assert json.loads(overridden.read_text(encoding="utf-8")) == loaded


# sha256 of the file the code at base commit 08144b0 writes for _dyadic_world in cells_median mode, environment fixed
BASE_COMMIT_CELLS_MEDIAN_OUTPUT_SHA256 = "dc8c788e1a2a58afea2b1aab301b012c796efe916146f55ffc418dce57a18a5a"


def test_x13_the_cells_median_mode_output_is_byte_identical_to_the_base_commit(tmp_path, monkeypatch):
    monkeypatch.setattr(reg, "environment", lambda: {"fixed": True})
    (embeddings, labels, axes), expected = _write_cells_inputs(tmp_path, world=_dyadic_world)
    out = tmp_path / "out" / "result.json"
    reg.run(embeddings, labels, expected, out, "cells_median", axes)
    assert hashlib.sha256(out.read_bytes()).hexdigest() == BASE_COMMIT_CELLS_MEDIAN_OUTPUT_SHA256


# Cells open mode (delegation contract relational-graph-cells-open) --------------------------------

OPEN_CELLS_KEYS = {
    "partition", "axes_digest", "per_axis", "tree_edges", "within_cell_relations", "cross_cell_relations",
    "added_links", "added_link_distances",
}
OPEN_CELL_KEYS = {"axis", "size", "t_c", "touching_tree_weights", "within_cell_relations", "cross_cell_relations"}
LOSS_KEYS = {"definition", "cross_cell_pairs", "dropped", "dropped_distances", "notes_with_dropped"}


def _open_world():
    """Rows on the line y = 9.5 at x = 0, 5, 8, 9 (cell y) and 10, 11, 15, 22, 30 (cell x), axes +x, +y, -x, -y:
    every distance is the integer gap in x. The global tree is the path 0-1-...-8 (5, 3, 1, 1, 1, 4, 7, 8), whose
    edge 3-4 (1) crosses the cells. The tree edges touching cell y weigh 5, 3, 1, 1 (t_c 2), those touching cell x
    1, 1, 4, 7, 8 (t_c 4); cells -x and -y are empty. The cells' own trees weigh 5, 3, 1 (median_c 3) and 1, 4, 7, 8
    (median_c 5.5)."""
    v = np.array([[x, 9.5] for x in (0, 5, 8, 9, 10, 11, 15, 22, 30)], dtype=float)
    a = np.array([[1, 0], [0, 1], [-1, 0], [0, -1]], dtype=float)
    parts = ("I", "I", "I", "II", "II", "II", "III", "III", "III")
    return v, (["x", "y", "-x", "-y"], a), [{"label": f"o{i}", "part": part} for i, part in enumerate(parts)]


def test_cells_open_t1_each_threshold_is_the_median_of_the_global_tree_edges_touching_the_cell():
    v, (ids, a), labels = _open_world()
    d = reg.pairwise_distances(v)
    cells = reg.axis_cells(v, a)
    assert cells.tolist() == [1, 1, 1, 1, 0, 0, 0, 0, 0]
    tree = reg.minimum_spanning_tree(d)
    assert [w for _, _, w in tree] == [5.0, 3.0, 1.0, 1.0, 1.0, 4.0, 7.0, 8.0]
    touching = reg.touching_tree_weights(tree, cells, len(a))
    assert [sorted(w) for w in touching] == [[1.0, 1.0, 4.0, 7.0, 8.0], [1.0, 1.0, 3.0, 5.0], [], []]
    per_axis = reg.explore(v, labels, None, axes=(ids, a), open_cells=True)["cells"]["per_axis"]
    assert [c["axis"] for c in per_axis] == ids
    assert [c["size"] for c in per_axis] == [5, 4, 0, 0]
    assert [c["t_c"] for c in per_axis] == [4.0, 2.0, None, None]
    assert per_axis[0]["touching_tree_weights"] == {
        "count": 5, "0": 1.0, "0.25": 1.0, "0.5": 4.0, "0.75": 7.0, "1": 8.0,
    }
    assert per_axis[1]["touching_tree_weights"] == {
        "count": 4, "0": 1.0, "0.25": 1.0, "0.5": 2.0, "0.75": 3.5, "1": 5.0,
    }
    assert per_axis[2]["touching_tree_weights"] == {"count": 0, **dict.fromkeys(QUANTILE_KEYS)}
    for cell in per_axis:
        assert set(cell) == OPEN_CELL_KEYS
    median = reg.explore(v, labels, None, axes=(ids, a), median=True)["cells"]["per_axis"]
    assert [c["median_c"] for c in median] == [5.5, 3.0, None, None]


def test_cells_open_t2_pairs_within_the_smaller_threshold_of_their_cells_joined_with_the_global_tree():
    v, (ids, a), labels = _open_world()
    d = reg.pairwise_distances(v)
    cells = reg.axis_cells(v, a)
    related = reg.open_relations(d, cells, [4.0, 2.0, None, None])
    assert related == [(2, 3, 1.0), (2, 4, 2.0), (3, 4, 1.0), (3, 5, 2.0), (4, 5, 1.0), (5, 6, 4.0)]
    assert reg.open_relations(d, cells, [4.0, None, None, None]) == [(4, 5, 1.0), (5, 6, 4.0)]
    result = reg.explore(v, labels, None, axes=(ids, a), open_cells=True)
    relations = result["relations"]
    assert "t_c" in relations["source"] and relations["near_epsilon"] is None
    assert relations["n_edges"] == 10
    assert result["components"]["sizes"] == [9]
    degrees = result["degrees"]
    assert (degrees["isolated"], degrees["min"], degrees["max"], degrees["mean"]) == (0, 1, 3, 20 / 9)
    assert result["reading_order"] == {"consecutive_row_edges": 8, "cross_part_edges": 3}
    assert result["pairwise_distances"]["share_within_epsilon"] is None
    assert "mst" not in result and "union" not in result
    block = result["cells"]
    assert set(block) == OPEN_CELLS_KEYS - {"axes_digest"}
    assert "t_c" in block["partition"]
    assert [c["within_cell_relations"] for c in block["per_axis"]] == [2, 1, 0, 0]
    assert [c["cross_cell_relations"] for c in block["per_axis"]] == [3, 3, 0, 0]
    assert (block["within_cell_relations"], block["cross_cell_relations"]) == (3, 3)
    assert (block["tree_edges"], block["added_links"]) == (8, 4)
    assert block["added_link_distances"] == {"count": 4, "0": 3.0, "0.25": 4.5, "0.5": 6.0, "0.75": 7.25, "1": 8.0}


def test_cells_open_t3_the_cross_cell_pairs_cells_median_drops():
    v, (ids, a), labels = _open_world()
    d = reg.pairwise_distances(v)
    cells = reg.axis_cells(v, a)
    tree = reg.minimum_spanning_tree(d)
    loss = reg.cells_median_loss(d, cells, [5.5, 3.0, None, None], tree)
    assert set(loss) == LOSS_KEYS
    assert "median_c" in loss["definition"]
    assert loss["cross_cell_pairs"] == 20
    assert loss["dropped"] == {"count": 3, "share": 3 / 20}
    assert loss["dropped_distances"] == {"count": 3, "0": 2.0, "0.25": 2.0, "0.5": 2.0, "0.75": 2.5, "1": 3.0}
    assert loss["notes_with_dropped"] == 4
    assert reg.cells_median_loss(d, cells, [5.5, None, None, None], tree)["dropped"] == {"count": 0, "share": 0.0}
    assert reg.explore(v, labels, None, axes=(ids, a), open_cells=True)["cells_median_loss"] == loss


def test_cells_open_t4_the_cells_open_file_is_sorted_finite_json_with_every_section(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAIANUS_EPSILON_EDGE", "0.8")
    (embeddings, labels, axes), expected = _write_cells_inputs(tmp_path)
    out = tmp_path / "out" / "relational_graph_exploration_cells_open.json"
    returned = reg.run(embeddings, labels, expected, out, "cells_open", axes)
    raw = out.read_bytes()
    text = raw.decode("utf-8")
    loaded = json.loads(text)
    assert loaded == returned
    assert text == json.dumps(loaded, sort_keys=True, indent=2, allow_nan=False) + "\n"
    assert b"\r" not in raw and "NaN" not in text and "Infinity" not in text
    assert loaded["kind"] == "exploration" and loaded["epsilon"] is None and loaded["n"] == 6
    assert loaded["digests"] == {
        "embeddings.npy": expected[embeddings], "labels.json": expected[labels], "nsm_axes_8.json": expected[axes],
    }
    median = reg.run(embeddings, labels, expected, tmp_path / "median.json", "cells_median", axes)
    assert set(loaded) == set(median) | {"cells_median_loss"}
    for section, keys in FIGURES.items():
        assert set(keys) <= set(loaded[section]), section
    assert loaded["relations"]["near_epsilon"] is None and "t_c" in loaded["relations"]["source"]
    assert loaded["components"]["sizes"] == [6]
    cells = loaded["cells"]
    assert set(cells) == OPEN_CELLS_KEYS
    assert cells["axes_digest"] == expected[axes]
    assert [c["axis"] for c in cells["per_axis"]] == [f"ax{k}" for k in range(8)]
    for cell in cells["per_axis"]:
        assert set(cell) == OPEN_CELL_KEYS
        assert set(cell["touching_tree_weights"]) == {"count", *QUANTILE_KEYS}
    assert cells["tree_edges"] == 5
    assert set(cells["added_link_distances"]) == {"count", *QUANTILE_KEYS}
    nearest = loaded["nearest_neighbours"]
    assert set(nearest) == NEAREST_KEYS and len(nearest["notes"]) == 6
    loss = loaded["cells_median_loss"]
    assert set(loss) == LOSS_KEYS
    assert set(loss["dropped"]) == {"count", "share"}
    assert set(loss["dropped_distances"]) == {"count", *QUANTILE_KEYS}


def test_x14_the_cells_open_summary_line_the_default_output_path_and_its_override(tmp_path, monkeypatch, capsys):
    assert "cells_open" in reg.MODES
    assert reg.RESULT_CELLS_OPEN == reg.REPO_ROOT / "data" / "refapp" / "relational_graph_exploration_cells_open.json"
    default = tmp_path / "default" / "relational_graph_exploration_cells_open.json"
    monkeypatch.setattr(reg, "RESULT_CELLS_OPEN", default)
    monkeypatch.setattr(reg, "RESULT_CELLS_MEDIAN", tmp_path / "median" / "unused.json")
    tmp_path.joinpath("a").mkdir()
    (embeddings, labels, axes), expected = _write_cells_inputs(tmp_path / "a")
    monkeypatch.setattr(reg, "EMBEDDINGS", embeddings)
    monkeypatch.setattr(reg, "LABELS", labels)
    monkeypatch.setattr(reg, "AXES", axes)
    monkeypatch.setattr(reg, "EXPECTED_DIGESTS", {p: expected[p] for p in (embeddings, labels)})
    monkeypatch.setattr(reg, "AXES_DIGEST", expected[axes])
    reg.main(["--relations", "cells_open"])
    loaded = json.loads(default.read_text(encoding="utf-8"))
    assert loaded["epsilon"] is None and not (tmp_path / "median").exists()
    line = capsys.readouterr().out
    cells = loaded["cells"]
    assert line == (
        f"relational graph: n=6 relations=cells_open edges={loaded['relations']['n_edges']} "
        f"cross_cell_relations={cells['cross_cell_relations']} added_links={cells['added_links']} "
        f"components={loaded['components']['count']} -> {default}\n"
    )
    overridden = tmp_path / "override" / "result.json"
    reg.main(["--relations", "cells_open", "--out", str(overridden)])
    assert json.loads(overridden.read_text(encoding="utf-8")) == loaded
