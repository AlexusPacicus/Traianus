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


def _write_inputs(tmp_path, corrupt=None):
    v, labels = _world()
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
