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
