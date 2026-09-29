"""Unit tests of tools/experiments/relational_graph_combined.py.

Specification: the delegation contract relational-graph-combined (B1-B8) and
docs/methodology/instrument-audit/contracts.md section 0. Synthetic inputs only: CI has no .data/, and the
exploration is never run on the real artefact here.
"""

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pytest

from tools.experiments import k6_colour_predictability as k6
from tools.experiments import relational_graph_combined as rgc
from tools.experiments import relational_graph_exploration as rge

D = 384
GENERIC = ("relations", "degrees", "components", "relational_distances", "reading_order")
QUANTILE_KEYS = ("0", "0.25", "0.5", "0.75", "1")


def _line_world():
    """Nine rows on the x axis, axes +x, +y, -x, -y (every distance is a dyadic gap, so exact). Rows 0-5 at
    x = 1, 2, 3, 8, 13, 18 (cell 0), rows 6-8 at x = -20, -20.25, -20.5 (cell 2). Global tree: the path 0-1-...-5
    (1, 1, 5, 5, 5), 6-7-8 (0.25, 0.25) and the cross edge 0-6 (21). Thresholds: cell 0 touches 1, 1, 5, 5, 5, 21
    (t 5), cell 2 touches 0.25, 0.25, 21 (t 0.25). Open relations add 0-2 (2) to the tree; the epsilon-relations at
    0.8 are 6-7, 7-8 and 6-8 (0.5), so the union adds 6-8."""
    v = np.array([[x, 0.0] for x in (1, 2, 3, 8, 13, 18, -20, -20.25, -20.5)])
    a = np.array([[1, 0], [0, 1], [-1, 0], [0, -1]], dtype=float)
    names = [f"r{i}" for i in range(9)]
    parts = ["I"] * 6 + ["II"] * 3
    return names, parts, v, a


TREE = [(0, 1), (0, 6), (1, 2), (2, 3), (3, 4), (4, 5), (6, 7), (7, 8)]
UNION = sorted([*TREE, (6, 8)])
OPEN = sorted([*TREE, (0, 2)])
COMBINED = sorted([*TREE, (0, 2), (6, 8)])


def _pairs(edges):
    return [(i, j) for i, j, _ in edges]


def _edges(pairs):
    return [(i, j, 1.0) for i, j in pairs]


# T1: the combined graph -----------------------------------------------------------------------------


def test_t1_the_combined_graph_is_the_union_of_both_pair_sets_each_pair_once_with_its_distance():
    names, _, v, a = _line_world()
    g = rgc.build_graphs(names, v, a)
    assert g.cells.tolist() == [0, 0, 0, 0, 0, 0, 2, 2, 2]
    assert _pairs(g.tree) == TREE
    assert _pairs(g.epsilon_edges) == [(6, 7), (6, 8), (7, 8)]
    assert _pairs(g.related) == [(0, 1), (0, 2), (1, 2), (2, 3), (3, 4), (4, 5), (6, 7), (7, 8)]
    assert _pairs(g.union) == UNION
    assert _pairs(g.open_borders) == OPEN
    assert _pairs(g.combined) == COMBINED
    assert set(_pairs(g.combined)) == set(_pairs(g.union)) | set(_pairs(g.open_borders))
    assert len(g.combined) == len(set(_pairs(g.combined))) == 10
    assert set(TREE) <= set(_pairs(g.combined))
    for i, j, w in g.combined:
        assert w == float(g.d[i, j])
    assert [w for i, j, w in g.combined if (i, j) in {(0, 1), (0, 6)}] == [1.0, 21.0]


# T2: the figures are rge.explore's ---------------------------------------------------------------------


def _generic(figures):
    return {key: figures[key] for key in GENERIC}


def test_t2_the_generic_block_equals_what_explore_returns_for_union_and_cells_open():
    names, parts, v, a = _line_world()
    labels = [{"label": n, "part": p} for n, p in zip(names, parts, strict=True)]
    g = rgc.build_graphs(names, v, a)
    ids = ["x", "y", "-x", "-y"]
    explored = {
        "union": rge.explore(v, labels, rgc.EPSILON, union=True),
        "open_borders": rge.explore(v, labels, None, axes=(ids, a), open_cells=True),
    }
    edges = {"union": g.union, "open_borders": g.open_borders}
    for name, full in explored.items():
        block, _ = rgc.generic_block(g.d, edges[name], parts)
        want = {"relations": {"n_edges": full["relations"]["n_edges"]}, **{k: full[k] for k in GENERIC[1:]}}
        assert rge._plain(block) == rge._plain(want), name
        assert set(block) == set(GENERIC)


def test_t2_beta_cross_cell_relations_and_hand_values_of_the_combined_graph():
    names, parts, v, a = _line_world()
    g = rgc.build_graphs(names, v, a)
    figures, _ = rgc.describe(g.d, g.cells, g.combined, parts)
    assert set(figures) == {*GENERIC, "beta", "cross_cell_relations"}
    assert figures["beta"] == 2 * 10 / 9
    assert figures["cross_cell_relations"] == 1
    assert figures["relations"] == {"n_edges": 10}
    degrees = figures["degrees"]
    assert (degrees["isolated"], degrees["min"], degrees["max"], degrees["mean"]) == (0, 1, 3, 20 / 9)
    assert figures["components"] == {"count": 1, "sizes": [9], "largest": {"size": 9, "share": 1.0}}
    assert figures["reading_order"] == {"consecutive_row_edges": 7, "cross_part_edges": 1}
    assert figures["relational_distances"]["definition"] == rge.DEFINITION
    for name, edges in (("union", g.union), ("open_borders", g.open_borders)):
        assert rgc.describe(g.d, g.cells, edges, parts)[0]["cross_cell_relations"] == 1, name


# T3: the reproduction control --------------------------------------------------------------------------


def _reference_of(figures):
    """What a committed reference file holds: the generic block, more keys, in JSON form."""
    extra = {"relations": {**figures["relations"], "source": "s", "manual": "m", "near_epsilon": None}}
    return json.loads(json.dumps(rge._plain({**_generic(figures), **extra, "mst": {"edges": 1}})))


def _figures():
    names, parts, v, a = _line_world()
    g = rgc.build_graphs(names, v, a)
    return {
        "union": rgc.describe(g.d, g.cells, g.union, parts)[0],
        "open_borders": rgc.describe(g.d, g.cells, g.open_borders, parts)[0],
    }


def test_t3_equal_references_reproduce_and_an_altered_field_is_named():
    figures = _figures()
    references = {name: _reference_of(f) for name, f in figures.items()}
    assert rgc.reproduce(figures, references) == ({"union": True, "open_borders": True}, [])
    references["union"]["degrees"]["max"] += 1
    references["open_borders"]["relational_distances"]["hops"]["0.5"] += 0.5
    references["open_borders"]["components"]["sizes"] = [8, 1]
    del references["open_borders"]["reading_order"]
    reproduction, mismatches = rgc.reproduce(figures, references)
    assert reproduction == {"union": False, "open_borders": False}
    assert mismatches == [
        "union.degrees.max",
        "open_borders.components.sizes",
        "open_borders.reading_order",
        "open_borders.relational_distances.hops.0.5",
    ]


def test_t3_a_reference_that_differs_only_in_another_variants_field_leaves_this_one_true():
    figures = _figures()
    references = {name: _reference_of(f) for name, f in figures.items()}
    references["union"]["relations"]["n_edges"] += 1
    reproduction, mismatches = rgc.reproduce(figures, references)
    assert reproduction == {"union": False, "open_borders": True}
    assert mismatches == ["union.relations.n_edges"]


# T4: overlap -------------------------------------------------------------------------------------------


def test_t4_overlap_counts_on_hand_built_edge_sets():
    tree = _edges([(0, 1), (1, 2), (2, 3)])
    eps = _edges([(0, 1), (0, 3), (1, 3)])
    related = _edges([(1, 2), (2, 3), (0, 2)])
    union = _edges([(0, 1), (0, 3), (1, 2), (1, 3), (2, 3)])
    open_borders = _edges([(0, 1), (0, 2), (1, 2), (2, 3)])
    combined = _edges([(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)])
    got = rgc.overlap(eps, related, tree, union, open_borders, combined)
    assert got == {
        "union": {"edges": 5, "tree_edges": 3},
        "open_borders": {"edges": 4, "tree_edges": 3},
        "combined": {"edges": 6, "tree_edges": 3},
        "both": {"edges": 3, "tree_edges": 3},
        "union_only": {"edges": 2, "tree_edges": 0},
        "open_borders_only": {"edges": 1, "tree_edges": 0},
        "epsilon_not_in_open_borders": 2,
        "open_relations_not_in_union": 1,
    }


def test_t4_overlap_of_the_line_world_matches_its_hand_sets():
    names, _, v, a = _line_world()
    g = rgc.build_graphs(names, v, a)
    got = rgc.overlap(g.epsilon_edges, g.related, g.tree, g.union, g.open_borders, g.combined)
    assert got["union"] == {"edges": 9, "tree_edges": 8}
    assert got["open_borders"] == {"edges": 9, "tree_edges": 8}
    assert got["combined"] == {"edges": 10, "tree_edges": 8}
    assert got["both"] == {"edges": 8, "tree_edges": 8}
    assert got["union_only"] == {"edges": 1, "tree_edges": 0}
    assert got["open_borders_only"] == {"edges": 1, "tree_edges": 0}
    assert (got["epsilon_not_in_open_borders"], got["open_relations_not_in_union"]) == (1, 1)


# T5: spiral turns --------------------------------------------------------------------------------------


def _hops(n, pairs):
    return rge.relational_distances(n, _edges(pairs))[1]


def _row(k, count, *quantiles):
    return {"k": k, "count": count, **dict(zip(QUANTILE_KEYS, quantiles, strict=True))}


def test_t5_path_turns_and_half_reach():
    turns = rgc.spiral_turns(_hops(4, [(0, 1), (1, 2), (2, 3)]))
    assert turns["largest_hops"] == 3
    assert turns["per_turn"] == [
        _row(1, 4, 1.0, 1.0, 1.5, 2.0, 2.0),
        _row(2, 4, 1.0, 1.0, 1.0, 1.0, 1.0),
        _row(3, 4, 0.0, 0.0, 0.5, 1.0, 1.0),
    ]
    assert turns["half_reach"] == {"undefined": 0, "count": 4, "0": 1.0, "0.25": 1.0, "0.5": 1.5, "0.75": 2.0, "1": 2.0}


def test_t5_star_turns_and_half_reach():
    turns = rgc.spiral_turns(_hops(4, [(0, 1), (0, 2), (0, 3)]))
    assert turns["largest_hops"] == 2
    assert turns["per_turn"] == [
        _row(1, 4, 1.0, 1.0, 1.0, 1.5, 3.0),
        _row(2, 4, 0.0, 1.5, 2.0, 2.0, 2.0),
    ]
    assert turns["half_reach"] == {"undefined": 0, "count": 4, "0": 1.0, "0.25": 1.75, "0.5": 2.0, "0.75": 2.0, "1": 2.0}


def test_t5_k_stops_at_the_largest_finite_hop_count_and_unreached_notes_are_counted():
    turns = rgc.spiral_turns(_hops(3, [(0, 1)]))
    assert turns["largest_hops"] == 1
    assert turns["per_turn"] == [_row(1, 3, 0.0, 0.5, 1.0, 1.0, 1.0)]
    assert turns["half_reach"] == {"undefined": 1, "count": 2, "0": 1.0, "0.25": 1.0, "0.5": 1.0, "0.75": 1.0, "1": 1.0}
    none = rgc.spiral_turns(_hops(2, []))
    assert none["largest_hops"] == 0 and none["per_turn"] == []
    assert none["half_reach"] == {"undefined": 2, "count": 0, **dict.fromkeys(QUANTILE_KEYS)}


# Runs: inputs, references, refusals, determinism -----------------------------------------------------------


def _on_circle(plane, angle):
    x = np.zeros(D)
    x[plane] = math.cos(angle)
    x[plane + 1] = math.sin(angle)
    return x


def _world():
    v = np.array([
        _on_circle(0, 0.0), _on_circle(0, 0.5), _on_circle(2, 0.0),
        _on_circle(0, 1.0), _on_circle(2, 0.3), _on_circle(4, 0.0),
    ])
    labels = [
        {"label": name, "part": part}
        for name, part in zip(("n6", "n5", "n4", "n3", "n2", "n1"), ("I", "I", "I", "II", "II", "II"), strict=True)
    ]
    return v, labels


def _write_inputs(tmp_path):
    v, labels = _world()
    a = np.zeros((8, D))
    for k, s in enumerate((1.0, 0.5, 3.0, 2.0, 1.0, 1.0, 1.0, 1.0)):
        a[k, k] = s
    paths = (tmp_path / "embeddings.npy", tmp_path / "labels.json", tmp_path / "nsm_axes_8.json")
    np.save(paths[0], v.astype(np.float32))
    paths[1].write_text(json.dumps(labels), encoding="utf-8")
    paths[2].write_text(
        json.dumps([{"id": f"ax{k}", "vector": row.tolist()} for k, row in enumerate(a)]), encoding="utf-8"
    )
    return paths, {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def _references(tmp_path, paths, expected, alter=None):
    """The two reference files as rge.run writes them on the same inputs; alter(name, loaded) edits one."""
    refs = {}
    for name, mode in (("union", "union"), ("open_borders", "cells_open")):
        path = tmp_path / f"reference_{name}.json"
        loaded = rge.run(paths[0], paths[1], expected, path, mode, paths[2])
        if alter is not None:
            alter(name, loaded)
            path.write_text(json.dumps(loaded, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        refs[name] = (path, hashlib.sha256(path.read_bytes()).hexdigest())
    return refs


@pytest.fixture
def setup(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAIANUS_EPSILON_EDGE", "0.8")
    inputs = tmp_path / "in"
    inputs.mkdir()
    paths, expected = _write_inputs(inputs)
    return tmp_path, paths, expected, _references(tmp_path, paths, expected)


def _run(paths, expected, refs, out, k6_file=rgc.K6_FILE, rge_file=rgc.RGE_FILE):
    return rgc.run(k6_file, rge_file, *paths, expected, refs, out)


def test_the_run_writes_the_three_graphs_valid_with_every_section(setup):
    tmp_path, paths, expected, refs = setup
    out = tmp_path / "out" / "combined.json"
    returned = _run(paths, expected, refs, out)
    raw = out.read_bytes()
    text = raw.decode("utf-8")
    loaded = json.loads(text)
    assert loaded == returned
    assert text == json.dumps(loaded, sort_keys=True, indent=2, allow_nan=False) + "\n"
    assert b"\r" not in raw and "NaN" not in text and "Infinity" not in text
    assert set(loaded) == {
        "kind", "statement", "n", "epsilon", "digests", "environment", "valid", "reproduction", "mismatches",
        "graphs", "overlap", "turns_definition",
    }
    assert loaded["turns_definition"] == rgc.TURNS_DEFINITION
    assert loaded["kind"] == "exploration" and loaded["n"] == 6 and loaded["epsilon"] == 0.8
    assert loaded["valid"] is True and loaded["mismatches"] == []
    assert loaded["reproduction"] == {"union": True, "open_borders": True}
    assert loaded["environment"] == rge._plain(rge.environment())
    assert set(loaded["graphs"]) == {"union", "open_borders", "combined"}
    for graph in loaded["graphs"].values():
        assert set(graph) == {"figures", "turns"}
        assert set(graph["figures"]) == {*GENERIC, "beta", "cross_cell_relations"}
        assert set(graph["turns"]) == {"largest_hops", "per_turn", "half_reach"}
    assert set(loaded["overlap"]) == {
        "union", "open_borders", "combined", "both", "union_only", "open_borders_only",
        "epsilon_not_in_open_borders", "open_relations_not_in_union",
    }
    assert loaded["digests"] == {
        "embeddings.npy": expected[paths[0]], "labels.json": expected[paths[1]],
        "nsm_axes_8.json": expected[paths[2]],
        rgc.RGE_FILE.name: rgc.RGE_SHA256, rgc.K6_FILE.name: rgc.K6_SHA256,
        refs["union"][0].name: refs["union"][1], refs["open_borders"][0].name: refs["open_borders"][1],
    }


def test_t3_an_altered_reference_file_makes_valid_false_names_the_field_and_still_writes(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAIANUS_EPSILON_EDGE", "0.8")
    (tmp_path / "in").mkdir()
    paths, expected = _write_inputs(tmp_path / "in")

    def alter(name, loaded):
        if name == "union":
            loaded["degrees"]["max"] += 1

    refs = _references(tmp_path, paths, expected, alter)
    out = tmp_path / "out.json"
    result = _run(paths, expected, refs, out)
    assert out.exists()
    assert result["valid"] is False
    assert result["reproduction"] == {"union": False, "open_borders": True}
    assert result["mismatches"] == ["union.degrees.max"]
    assert set(result["graphs"]) == {"union", "open_borders", "combined"}


def _tampered(tmp_path, source):
    copy = tmp_path / f"tampered_{Path(source).name}"
    copy.write_bytes(Path(source).read_bytes() + b"#\n")
    return copy


def test_t6_unpinned_code_or_data_is_refused_and_nothing_is_written(setup, monkeypatch):
    tmp_path, paths, expected, refs = setup
    _run(paths, expected, refs, tmp_path / "intact.json")
    assert (tmp_path / "intact.json").exists()
    out = tmp_path / "out" / "combined.json"

    with pytest.raises(k6.IntegrityError, match="tampered_relational_graph_exploration"):
        _run(paths, expected, refs, out, rge_file=_tampered(tmp_path, rgc.RGE_FILE))
    with pytest.raises(k6.IntegrityError, match="tampered_k6_colour_predictability"):
        _run(paths, expected, refs, out, k6_file=_tampered(tmp_path, rgc.K6_FILE))

    for path in paths:
        original = path.read_bytes()
        flipped = bytearray(original)
        flipped[-1] ^= 1
        path.write_bytes(bytes(flipped))
        with pytest.raises(k6.IntegrityError, match=path.name):
            _run(paths, expected, refs, out)
        path.write_bytes(original)

    for name, (path, digest) in refs.items():
        original = path.read_bytes()
        path.write_bytes(original + b" ")
        with pytest.raises(k6.IntegrityError, match=path.name):
            _run(paths, expected, refs, out)
        path.write_bytes(original)
        wrong = {**refs, name: (path, "0" * 64)}
        with pytest.raises(k6.IntegrityError, match=path.name):
            _run(paths, expected, wrong, out)

    monkeypatch.setenv("TRAIANUS_EPSILON_EDGE", "0.7")
    with pytest.raises(k6.IntegrityError, match="epsilon"):
        _run(paths, expected, refs, out)
    assert not out.parent.exists()


def test_t7_two_runs_write_byte_identical_files(setup):
    tmp_path, paths, expected, refs = setup
    first, second = tmp_path / "a" / "one.json", tmp_path / "b" / "two.json"
    _run(paths, expected, refs, first)
    _run(paths, expected, refs, second)
    assert first.read_bytes() == second.read_bytes()


# Pins, paths and the command line ----------------------------------------------------------------------------


def test_x1_the_pins_and_paths_are_the_contracts():
    assert rgc.rge is rge and rgc.k6 is k6
    assert rgc.RGE_FILE == Path(rge.__file__) and rgc.K6_FILE == Path(k6.__file__)
    assert rgc.RGE_SHA256 == "627aa8e95a844b0aec290a41c48b9a0bf6890db25b5240b5730c366a56d2e7dc"
    assert rgc.K6_SHA256 == "6289c596792154f6bb799606265c68719c6b8c7ae8b69084116dfb23c77876d2"
    assert hashlib.sha256(rgc.RGE_FILE.read_bytes()).hexdigest() == rgc.RGE_SHA256
    assert hashlib.sha256(rgc.K6_FILE.read_bytes()).hexdigest() == rgc.K6_SHA256
    assert rgc.EPSILON == 0.8
    assert rgc.REFERENCES == {
        "union": (rge.RESULT_UNION, "300f929d3cc9bb920203c7d050ed41b22570cba1cf8b391f8af47ed224ba04d5"),
        "open_borders": (rge.RESULT_CELLS_OPEN, "546d75fa31735adc5952929dad2674bbf6959219d89ca284b44f6bd77f489360"),
    }
    assert rgc.RESULT == rgc.REPO_ROOT / "data" / "refapp" / "relational_graph_combined.json"
    assert rgc.EXPECTED == {**rge.EXPECTED_DIGESTS, rge.AXES: rge.AXES_DIGEST}


def _patch_main(monkeypatch, tmp_path, paths, expected, refs):
    monkeypatch.setattr(rgc, "EMBEDDINGS", paths[0])
    monkeypatch.setattr(rgc, "LABELS", paths[1])
    monkeypatch.setattr(rgc, "AXES", paths[2])
    monkeypatch.setattr(rgc, "EXPECTED", expected)
    monkeypatch.setattr(rgc, "REFERENCES", refs)
    default = tmp_path / "default" / "relational_graph_combined.json"
    monkeypatch.setattr(rgc, "RESULT", default)
    return default


def test_x2_main_prints_one_summary_line_and_honours_the_default_and_the_override(setup, monkeypatch, capsys):
    tmp_path, paths, expected, refs = setup
    default = _patch_main(monkeypatch, tmp_path, paths, expected, refs)
    rgc.main([])
    loaded = json.loads(default.read_text(encoding="utf-8"))
    counts = {name: loaded["overlap"][name]["edges"] for name in ("union", "open_borders", "combined")}
    assert capsys.readouterr().out == (
        f"relational graph combined: n=6 union={counts['union']} open_borders={counts['open_borders']} "
        f"combined={counts['combined']} components={loaded['graphs']['combined']['figures']['components']['count']} "
        f"valid=True -> {default}\n"
    )
    overridden = tmp_path / "override" / "result.json"
    rgc.main(["--out", str(overridden)])
    assert overridden.read_bytes() == default.read_bytes()


def test_x3_main_exits_non_zero_when_a_reference_is_not_reproduced_and_still_writes(tmp_path, monkeypatch):
    monkeypatch.setenv("TRAIANUS_EPSILON_EDGE", "0.8")
    (tmp_path / "in").mkdir()
    paths, expected = _write_inputs(tmp_path / "in")

    def alter(name, loaded):
        if name == "open_borders":
            loaded["components"]["count"] += 1

    refs = _references(tmp_path, paths, expected, alter)
    default = _patch_main(monkeypatch, tmp_path, paths, expected, refs)
    with pytest.raises(SystemExit) as raised:
        rgc.main([])
    assert raised.value.code not in (0, None)
    assert json.loads(default.read_text(encoding="utf-8"))["valid"] is False
