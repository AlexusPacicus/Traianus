"""Minimum spanning tree of the current nodes — pure, observational.

Prim over the ids in sorted order from the first id; ties go to the lower sorted position, and a key
is replaced only by a strictly smaller distance, so ties keep the earlier parent. Lengths are
computed and rounded exactly as compute_epsilon_edges does, so the two never disagree on a pair.
"""
import numpy as np
import pytest

from traianus.geometry.observables import compute_epsilon_edges
from traianus.geometry.spanning_tree import compute_minimum_spanning_tree

D = 16


def _nodes(seed: int, n: int) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    x = rng.standard_normal((n, D))
    x /= np.linalg.norm(x, axis=1, keepdims=True)
    return {f"N{i:03d}": x[i] for i in range(n)}


def _kruskal(nodes: dict[str, np.ndarray]) -> list[tuple[str, str]]:
    ids = sorted(nodes)
    pairs = sorted(
        (float(np.linalg.norm(nodes[a] - nodes[b])), a, b)
        for i, a in enumerate(ids)
        for b in ids[i + 1:]
    )
    root = {i: i for i in ids}

    def find(i: str) -> str:
        while root[i] != i:
            root[i] = root[root[i]]
            i = root[i]
        return i

    chosen = []
    for _, a, b in pairs:
        ra, rb = find(a), find(b)
        if ra != rb:
            root[ra] = rb
            chosen.append((a, b))
    return sorted(chosen)


def _length(nodes: dict[str, np.ndarray], edges: list[dict]) -> float:
    return sum(float(np.linalg.norm(nodes[e["source"]] - nodes[e["target"]])) for e in edges)


@pytest.mark.parametrize("n", [0, 1, 2, 3, 5, 12, 40])
def test_tree_matches_an_independent_kruskal(n):
    nodes = _nodes(20260929 + n, n)
    edges = compute_minimum_spanning_tree(nodes)
    expected = _kruskal(nodes)
    assert len(edges) == max(n - 1, 0)
    assert [(e["source"], e["target"]) for e in edges] == expected
    assert _length(nodes, edges) == pytest.approx(_length(nodes, [
        {"source": a, "target": b} for a, b in expected
    ]))


@pytest.mark.parametrize("n", [2, 5, 40])
def test_tree_connects_every_node(n):
    nodes = _nodes(7 + n, n)
    edges = compute_minimum_spanning_tree(nodes)
    reached = {min(nodes)}
    pending = list(edges)
    while pending:
        grown = [e for e in pending if (e["source"] in reached) != (e["target"] in reached)]
        assert grown
        for e in grown:
            reached |= {e["source"], e["target"]}
        pending = [e for e in pending if e not in grown]
    assert reached == set(nodes)


def test_edges_are_ordered_and_sorted():
    nodes = _nodes(3, 12)
    edges = compute_minimum_spanning_tree(dict(reversed(list(nodes.items()))))
    assert all(e["source"] < e["target"] for e in edges)
    assert edges == sorted(edges, key=lambda e: (e["source"], e["target"]))
    assert all(set(e) == {"source", "target", "distance"} for e in edges)


def test_ties_go_to_the_lower_sorted_position_and_keep_the_earlier_parent():
    square = {
        "D": np.array([1.0, 1.0]),
        "B": np.array([1.0, 0.0]),
        "C": np.array([0.0, 1.0]),
        "A": np.array([0.0, 0.0]),
    }
    assert compute_minimum_spanning_tree(square) == [
        {"source": "A", "target": "B", "distance": 1.0},
        {"source": "A", "target": "C", "distance": 1.0},
        {"source": "B", "target": "D", "distance": 1.0},
    ]


def test_tree_and_epsilon_edges_agree_on_every_shared_length():
    nodes = _nodes(11, 30)
    tree = compute_minimum_spanning_tree(nodes)
    adjacent = {
        (e["source"], e["target"]): e["distance"]
        for e in compute_epsilon_edges(nodes, 1.5)
    }
    shared = [e for e in tree if (e["source"], e["target"]) in adjacent]
    assert shared
    for e in shared:
        assert e["distance"] == adjacent[(e["source"], e["target"])]
    for e in tree:
        assert e["distance"] == round(float(np.linalg.norm(nodes[e["source"]] - nodes[e["target"]])), 6)
