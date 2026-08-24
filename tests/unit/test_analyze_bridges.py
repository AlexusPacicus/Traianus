"""Unit tests for tools/analyze_bridges.py — non-sequential E_n bridge audit."""
import numpy as np

from tools.analyze_bridges import (
    adaptive_epsilon,
    apply_exclusions,
    bridge_set_overlap,
    find_bridges,
    pairwise_distances,
    resonance_axis,
)

EPSILON = 0.8
RNG = np.random.default_rng(42)


def _unit(v):
    return np.asarray(v, dtype=np.float64) / np.linalg.norm(v)


def _far(*others):
    w = RNG.standard_normal(384)
    for o in others:
        w = w - np.dot(w, o) * o
    return _unit(w)


def _proj(values):
    return {f"AXIS_{k + 1}": float(x) for k, x in enumerate(values)}


V1 = _unit(RNG.standard_normal(384))
V4 = _unit(V1 + RNG.normal(scale=0.01, size=384))
V2 = _unit(RNG.standard_normal(384))
V3 = _unit(V2 + RNG.normal(scale=0.01, size=384))
V5 = _far(V1, V2, V3)
V6 = _far(V2, V3, V5)

NODES = [
    {"id": "NODE_1", "text": "first proposition", "vector": V1,
     "projections": _proj([0.10, 0.40, 0.20, 0.05, 0.00, 0.10, 0.30, 0.25])},
    {"id": "NODE_2", "text": "second proposition", "vector": V2,
     "projections": _proj([0.05, 0.15, 0.35, 0.20, 0.10, 0.00, 0.25, 0.45])},
    {"id": "NODE_3", "text": "third proposition", "vector": V3,
     "projections": _proj([0.12, 0.22, 0.02, 0.40, 0.18, 0.08, 0.28, 0.36])},
    {"id": "NODE_4", "text": "fourth proposition", "vector": V4,
     "projections": _proj([0.30, 0.401, 0.22, 0.07, 0.02, 0.12, 0.32, 0.27])},
    {"id": "NODE_5", "text": "fifth proposition", "vector": V5,
     "projections": _proj([0.50, 0.05, 0.44, 0.11, 0.33, 0.21, 0.09, 0.17])},
    {"id": "NODE_6", "text": "sixth proposition", "vector": V6,
     "projections": _proj([0.03, 0.48, 0.19, 0.31, 0.07, 0.41, 0.14, 0.26])},
]


def _bridge_pairs(bridges):
    return {(b["source"], b["target"]) for b in bridges}


def test_bridge_non_contiguous_detected():
    assert ("NODE_1", "NODE_4") in _bridge_pairs(find_bridges(NODES, EPSILON))


def test_contiguous_pair_excluded():
    assert ("NODE_2", "NODE_3") not in _bridge_pairs(find_bridges(NODES, EPSILON))


def test_only_true_bridges_reported():
    bridges = find_bridges(NODES, EPSILON)
    assert _bridge_pairs(bridges) == {("NODE_1", "NODE_4")}
    assert all(b["distance"] <= EPSILON for b in bridges)


def test_resonance_axis_prefers_co_activation_over_min_delta():
    a = {"AXIS_1": 0.90, "AXIS_2": 0.10}
    b = {"AXIS_1": 0.88, "AXIS_2": 0.101}
    axis, score = resonance_axis(a, b)
    assert axis == "AXIS_1"
    assert abs(score - 0.90 * 0.88) < 1e-12


def test_find_bridges_reports_co_activation_winner():
    bridge = next(b for b in find_bridges(NODES, EPSILON) if b["source"] == "NODE_1")
    assert bridge["axis"] == "AXIS_2"
    assert bridge["coactivation"] == 0.40 * 0.401


def test_sorted_by_distance_ascending():
    distances = [b["distance"] for b in find_bridges(NODES, EPSILON)]
    assert distances == sorted(distances)


def test_no_bridges_when_all_contiguous():
    close_pair = [NODES[0], NODES[3]]
    assert np.linalg.norm(close_pair[0]["vector"] - close_pair[1]["vector"]) <= EPSILON
    assert find_bridges(close_pair, EPSILON) == []


def test_pairwise_distances_known_values():
    vectors = {
        "B": np.array([0.0, 1.0]),
        "A": np.array([1.0, 0.0]),
        "C": np.array([1.0, 1.0]),
    }
    dists = pairwise_distances(vectors)
    assert np.allclose(sorted(dists), [1.0, 1.0, np.sqrt(2)])


def test_adaptive_epsilon_keeps_closest_top_percent():
    dists = np.linspace(0.1, 0.9, 9)
    assert abs(adaptive_epsilon(dists, 98) - np.percentile(dists, 2)) < 1e-12
    assert adaptive_epsilon(dists, 90) <= adaptive_epsilon(dists, 10)
    assert abs(adaptive_epsilon(dists, 50) - 0.5) < 1e-12


def test_bridge_set_overlap_jaccard():
    a = [{"source": "a", "target": "c", "distance": 0.5},
         {"source": "d", "target": "f", "distance": 0.6},
         {"source": "g", "target": "h", "distance": 0.7}]
    b = [{"source": "a", "target": "c", "distance": 0.55},
         {"source": "g", "target": "h", "distance": 0.72},
         {"source": "x", "target": "y", "distance": 0.65}]
    overlap = bridge_set_overlap(a, b)
    assert overlap["intersection"] == 2
    assert abs(overlap["jaccard"] - 2 / 4) < 1e-12
    assert overlap["top_common"] == [("a", "c"), ("g", "h")]


def test_exclusion_collapses_contiguity():
    filtered = apply_exclusions(NODES, {"NODE_2", "NODE_3"})
    assert [n["id"] for n in filtered] == ["NODE_1", "NODE_4", "NODE_5", "NODE_6"]
    assert find_bridges(filtered, EPSILON) == []
