"""Relational graph exploration: degrees, components and relational distances of the engine's relations.

Implements the delegation contract relational-graph-exploration (B1-B8) against
docs/methodology/instrument-audit/contracts.md section 0. The relations are the engine's automatic
epsilon-relations, computed by traianus.geometry.observables.compute_epsilon_edges with
epsilon = traianus.config.resolve_epsilon_edge(); the relational distance of two notes is the length of
the shortest path between them along those relations, each relation counted by its unrounded L2 length.
With --relations mst (delegation contract relational-graph-mst) the relations are instead the minimum spanning
tree of the complete graph over the same binary64 L2 distances, and its longest edge is reported as the
connectivity threshold, the smallest epsilon at which the epsilon-relations join every note.
With --relations union (delegation contract relational-graph-union) the relations are the epsilon-relations
joined with that tree, so the tree adds only the links that keep every note reachable.
With --relations cells (delegation contract relational-graph-cells) each note lies in the cell of its dominant
axis, as in the Z script; each cell has its own threshold epsilon_c, the longest edge of the minimum spanning tree
of its notes, and the relations are the pairs of one cell within its epsilon_c joined with the edges of the global
tree between different cells.
With --relations cells_median (delegation contract relational-graph-cells-median) each cell's threshold median_c is
the median of its own tree's edge weights, and the within-cell relations are joined with every edge of the global
tree; each note's nearest neighbour is reported as well, with its axis cell.
With --relations cells_open (delegation contract relational-graph-cells-open) each cell's threshold t_c is the median
of the global tree's edge weights with an end in the cell, two notes in any cells are related within the smaller
threshold of their cells, the relations are joined with every edge of the global tree, and the cross-cell pairs
cells_median drops though both its cells' median_c admit them are counted.
Descriptive: it tests no hypothesis and decides nothing.

Refuses to run, writing nothing, unless every input digest (two files, three in the cells modes with the axes)
matches the Z script's pins.

Usage:
    python3 tools/experiments/relational_graph_exploration.py
        [--relations {epsilon,mst,union,cells,cells_median,cells_open}] [--out PATH]
"""

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_var] = "1"

import argparse
import io
import json
import math
import platform
import sys
from collections.abc import Callable, Mapping, Sequence
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.experiments import k6_colour_predictability as k6
from traianus.config import resolve_epsilon_edge
from traianus.geometry.observables import compute_epsilon_edges

Array = NDArray[np.float64]
Edge = tuple[int, int, float]

EMBEDDINGS = REPO_ROOT / ".data" / "spinoza_frozen" / "embeddings.npy"
LABELS = REPO_ROOT / ".data" / "spinoza_frozen" / "labels.json"
RESULT = REPO_ROOT / "data" / "refapp" / "relational_graph_exploration.json"
RESULT_MST = REPO_ROOT / "data" / "refapp" / "relational_graph_exploration_mst.json"
RESULT_UNION = REPO_ROOT / "data" / "refapp" / "relational_graph_exploration_union.json"
RESULT_CELLS = REPO_ROOT / "data" / "refapp" / "relational_graph_exploration_cells.json"
RESULT_CELLS_MEDIAN = REPO_ROOT / "data" / "refapp" / "relational_graph_exploration_cells_median.json"
RESULT_CELLS_OPEN = REPO_ROOT / "data" / "refapp" / "relational_graph_exploration_cells_open.json"
AXES = REPO_ROOT / "tests" / "fixtures" / "nsm_axes_8.json"
CELL_MODES = ("cells", "cells_median", "cells_open")
MODES = ("epsilon", "mst", "union", *CELL_MODES)
EXPECTED_DIGESTS = {
    EMBEDDINGS: "eafb0e97172830f2404e96fa08d74bf6cccc0b6cbe84d47b790a476603e7d8d1",
    LABELS: "1d60699353d810f089730c6203ee28f9c416e3004b60781bc965cec284097f4f",
}
AXES_DIGEST = "b14e5d6700d1a7478a357ca26f0f38f5240f97a42daad45722d21f1c3f964e35"
NEAR_EPSILON = 1e-6
QUANTILES = (0.0, 0.25, 0.5, 0.75, 1.0)
PAIRWISE_QUANTILES = (0.01, 0.05, 0.25, 0.5)
THREAD_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")
STATEMENT = "Descriptive exploration of the relation graph: it tests no hypothesis and decides nothing."
MANUAL_RELATIONS = "absent: manual relations exist only in an engine database, not in the frozen artefact"
EPSILON_SOURCE = "traianus.geometry.observables.compute_epsilon_edges"
MST_SOURCE = (
    "minimum spanning tree (Prim, from row 0, ties to the lower row index) of the complete graph over the "
    "binary64 L2 distances of pairwise_distances"
)
UNION_SOURCE = (
    f"union, on unordered row pairs, of {EPSILON_SOURCE} at epsilon and the {MST_SOURCE}; a pair in both "
    "appears once, weighted by its binary64 L2 distance of pairwise_distances"
)
CELLS_SOURCE = (
    "union, on unordered row pairs, of the within-cell relations (the pairs of one axis cell whose binary64 L2 "
    "distance of pairwise_distances is <= that cell's epsilon_c, the longest edge of the minimum spanning tree of "
    f"the cell's rows) and the edges of the {MST_SOURCE} whose ends lie in different cells; a pair appears once, "
    "weighted by its distance of pairwise_distances"
)
CELLS_MEDIAN_SOURCE = (
    "union, on unordered row pairs, of the within-cell relations (the pairs of one axis cell whose binary64 L2 "
    "distance of pairwise_distances is <= that cell's median_c, numpy.median of the edge weights of the minimum "
    f"spanning tree of the cell's rows) and every edge of the {MST_SOURCE}; a pair appears once, weighted by its "
    "distance of pairwise_distances"
)
CELLS_OPEN_SOURCE = (
    "union, on unordered row pairs, of the open relations (the pairs, in one axis cell or in two, whose binary64 L2 "
    "distance of pairwise_distances is <= min(t_c) of their cells, t_c numpy.median of the weights of the edges of "
    f"the {MST_SOURCE} with an end in the cell, an edge between two cells counted once for each; a null t_c admits no "
    "pair) and every edge of that tree; a pair appears once, weighted by its distance of pairwise_distances"
)
LOSS_DEFINITION = (
    "the cross-cell pairs cells_median drops: pairs of rows in different axis cells whose distance of "
    "pairwise_distances is <= min(median_c) of their cells (a null median_c admits no pair) and which are not edges "
    "of the minimum spanning tree; dropped.share is their share of all cross-cell pairs; notes_with_dropped counts "
    "the rows with at least one"
)
AXIS_CELLS = (
    "axis cells: each row in the cell of argmax_k <v, a_hat_k>, a_hat_k = a_k / ||a_k|| in binary64, ties to the "
    "lower axis index (the Z script's attractor)"
)
NEAREST_DEFINITION = (
    "nearest neighbour: the other row at the smallest distance of pairwise_distances, ties to the lower row index; "
    "with distinct distances the edge to it is an edge of the minimum spanning tree, and outside_tree counts the "
    "notes whose nearest-neighbour edge is not"
)
NEAR_STATEMENT = (
    "pairs whose binary64 L2 distance lies within the tolerance of epsilon (compute_epsilon_edges reports "
    "distances to 6 decimals); the engine normalises in binary32 (contracts.md section 0, Engine path) and "
    "could decide these pairs otherwise"
)
DEFINITION = (
    "relational distance: shortest path along the relations, each weighted by its unrounded L2 distance; "
    "defined only within a connected component (infinite, never written, between components); "
    "hops: fewest relations on a path, reported as context only"
)


# Inputs (contracts.md section 0) -----------------------------------------------------------------


def load_inputs(embeddings: bytes, labels: bytes) -> tuple[NDArray[np.float32], list[Any]]:
    v32 = np.load(io.BytesIO(embeddings), allow_pickle=False)
    label_list: list[Any] = json.loads(labels.decode("utf-8"))
    return v32, label_list


def validate_inputs(v32: NDArray[Any], labels: list[Any]) -> None:
    """Null elimination (contracts.md section 0) for the two files used; raises ValueError naming the row or label."""
    v = np.asarray(v32, dtype=np.float64)
    if v.ndim != 2 or v.shape[1] != k6.D:
        raise ValueError(f"embeddings must have shape (n, {k6.D}), got {v.shape}")
    for i, row in enumerate(v):
        if not np.all(np.isfinite(row)):
            raise ValueError(f"row {i}: non-finite value")
        norm = math.sqrt(float(row @ row))
        if abs(norm - 1.0) > k6.NORM_TOL:
            raise ValueError(f"row {i}: norm {norm!r} outside 1 ± {k6.NORM_TOL}")
    if len(labels) != v.shape[0]:
        raise ValueError(f"label count {len(labels)} != row count {v.shape[0]}")
    seen: dict[str, int] = {}
    for i, item in enumerate(labels):
        if not isinstance(item, dict):
            raise ValueError(f"label {i}: not an object")  # noqa: TRY004
        for key in ("label", "part"):
            value = item.get(key)
            if not isinstance(value, str) or value == "":
                raise ValueError(f"label {i}: {key} is null or empty")
        if item["label"] in seen:
            raise ValueError(f"label {i}: duplicate of label {seen[item['label']]}")
        seen[item["label"]] = i


# Graph -------------------------------------------------------------------------------------------


def relations(labels: Sequence[str], v: Array, epsilon: float) -> list[Edge]:
    """The engine's epsilon-relations as (row i, row j, unrounded L2 distance), i < j, sorted.

    The distance is recomputed with compute_epsilon_edges' own expression, which it reports rounded."""
    row = {label: i for i, label in enumerate(labels)}
    edges = []
    for edge in compute_epsilon_edges({label: v[i] for i, label in enumerate(labels)}, epsilon):
        s, t = row[edge["source"]], row[edge["target"]]
        edges.append((min(s, t), max(s, t), float(np.linalg.norm(v[s] - v[t]))))
    return sorted(edges)


def pairwise_distances(v: Array) -> Array:
    """All L2 distances, pair by pair with compute_epsilon_edges' expression, so a pair's distance here
    and the engine's decision on it come from the same binary64 value."""
    n = len(v)
    d = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            d[i, j] = d[j, i] = float(np.linalg.norm(v[i] - v[j]))
    return d


def minimum_spanning_tree(d: Array) -> list[Edge]:
    """Prim's algorithm from row 0 over the complete graph weighted by d, in O(n^2). Ties go to the lower row
    index, both for the next row joined and for the tree row it joins through. Edges (i, j, weight), i < j,
    sorted; none for a single row."""
    n = len(d)
    joined = np.zeros(n, dtype=bool)
    joined[0] = True
    best = d[0].copy()
    parent = np.zeros(n, dtype=np.intp)
    edges = []
    for _ in range(n - 1):
        j = int(np.argmin(np.where(joined, np.inf, best)))
        joined[j] = True
        i = int(parent[j])
        edges.append((min(i, j), max(i, j), float(best[j])))
        closer = ~joined & ((d[j] < best) | ((d[j] == best) & (j < parent)))
        best[closer] = d[j][closer]
        parent[closer] = j
    return sorted(edges)


def union_edges(first: Sequence[Edge], second: Sequence[Edge], d: Array) -> list[Edge]:
    """The row pairs of either edge list, each once, weighted by its distance in d; (i, j, weight), i < j, sorted."""
    pairs = {(min(i, j), max(i, j)) for i, j, _ in (*first, *second)}
    return [(i, j, float(d[i, j])) for i, j in sorted(pairs)]


def axis_cells(v: Array, a: Array) -> NDArray[np.intp]:
    """Each row's axis cell: argmax_k <v, a_hat_k>, a_hat_k = a_k / ||a_k|| in binary64, ties to the lower axis
    index, as the Z script computes it (contracts.md section 0, Conversions)."""
    a_hat = np.array([a_k / np.sqrt(a_k @ a_k) for a_k in a])
    return np.argmax(v @ a_hat.T, axis=1)


def median_threshold(weights: Sequence[float]) -> float:
    return float(np.median(weights))


def cell_graph(
    d: Array, cells: NDArray[np.intp], n_cells: int, threshold: Callable[[Sequence[float]], float] = max,
) -> tuple[list[list[Edge]], list[Edge], list[Edge]]:
    """Per cell, in axis order, the minimum spanning tree of its rows in global rows (none below two rows); the
    within-cell relations, the pairs of one cell at distance <= its threshold of that tree's edge weights (epsilon_c,
    the longest edge, by default); and the edges of the minimum spanning tree over all rows whose ends lie in
    different cells. Edges (i, j, weight), i < j, sorted."""
    trees: list[list[Edge]] = []
    within: list[Edge] = []
    for k in range(n_cells):
        rows = np.flatnonzero(cells == k)
        local = minimum_spanning_tree(d[np.ix_(rows, rows)]) if len(rows) > 1 else []
        trees.append([(int(rows[i]), int(rows[j]), w) for i, j, w in local])
        if local:
            epsilon_c = threshold([w for _, _, w in local])
            within.extend(
                (int(i), int(j), float(d[i, j])) for i, j in combinations(rows, 2) if d[i, j] <= epsilon_c
            )
    cross = [(i, j, w) for i, j, w in minimum_spanning_tree(d) if cells[i] != cells[j]]
    return trees, sorted(within), cross


def touching_tree_weights(tree: Sequence[Edge], cells: NDArray[np.intp], n_cells: int) -> list[list[float]]:
    """Per cell, in axis order, the weights of the tree edges with an end in the cell; an edge between two cells
    counts once for each, an edge inside a cell once."""
    weights: list[list[float]] = [[] for _ in range(n_cells)]
    for i, j, w in tree:
        for k in sorted({int(cells[i]), int(cells[j])}):
            weights[k].append(w)
    return weights


def _pair_thresholds(cells: NDArray[np.intp], thresholds: Sequence[float | None]) -> Array:
    """The smaller threshold of the two rows' cells, for every row pair; -inf where either is null."""
    t = np.array([-np.inf if c is None else c for c in thresholds])[cells]
    pairs: Array = np.minimum.outer(t, t)
    return pairs


def open_relations(d: Array, cells: NDArray[np.intp], thresholds: Sequence[float | None]) -> list[Edge]:
    """Every pair, in one cell or in two, at distance <= the smaller threshold of its cells (a null threshold admits
    none). Edges (i, j, weight), i < j, sorted."""
    rows, cols = np.nonzero(np.triu(d <= _pair_thresholds(cells, thresholds), 1))
    return [(int(i), int(j), float(d[i, j])) for i, j in zip(rows, cols, strict=True)]


def components(n: int, edges: Sequence[Edge]) -> list[list[int]]:
    """Connected components as ascending row lists, largest first, ties by first row."""
    adjacency: list[list[int]] = [[] for _ in range(n)]
    for i, j, _ in edges:
        adjacency[i].append(j)
        adjacency[j].append(i)
    seen = [False] * n
    found = []
    for start in range(n):
        if seen[start]:
            continue
        seen[start] = True
        stack, members = [start], []
        while stack:
            node = stack.pop()
            members.append(node)
            for other in adjacency[node]:
                if not seen[other]:
                    seen[other] = True
                    stack.append(other)
        found.append(sorted(members))
    return sorted(found, key=lambda c: (-len(c), c[0]))


def nearest_neighbours(d: Array) -> tuple[NDArray[np.intp], Array]:
    """Each row's nearest other row by d, ties to the lower row index, and the distance to it; none for one row."""
    others = d.copy()
    np.fill_diagonal(others, np.inf)
    nearest = np.argmin(others, axis=1) if len(d) > 1 else np.zeros(0, dtype=np.intp)
    return nearest, others[np.arange(len(nearest)), nearest]


def _floyd_warshall(d: Array) -> Array:
    d = d.copy()
    step = np.empty_like(d)
    for k in range(len(d)):
        np.add(d[:, k, None], d[k, None, :], out=step)
        np.minimum(d, step, out=d)
    return d


def relational_distances(n: int, edges: Sequence[Edge]) -> tuple[Array, Array]:
    """Exact all-pairs shortest paths within each component: weighted by the relations' L2 distances,
    and in hops (every relation 1, the unweighted BFS distance); infinite between components."""
    w = np.full((n, n), np.inf)
    hops = np.full((n, n), np.inf)
    np.fill_diagonal(w, 0.0)
    np.fill_diagonal(hops, 0.0)
    for i, j, dist in edges:
        w[i, j] = w[j, i] = dist
        hops[i, j] = hops[j, i] = 1.0
    for component in components(n, edges):
        if len(component) > 1:
            block = np.ix_(component, component)
            w[block] = _floyd_warshall(w[block])
            hops[block] = _floyd_warshall(hops[block])
    return w, hops


# Figures -----------------------------------------------------------------------------------------


def _quantiles(values: NDArray[Any], qs: Sequence[float]) -> dict[str, float | None]:
    return {f"{q:g}": float(np.quantile(values, q)) if len(values) else None for q in qs}


def _summary(values: NDArray[Any]) -> dict[str, Any]:
    return {"count": len(values), **_quantiles(values, QUANTILES)}


def _near_epsilon(direct: Array, adjacent: NDArray[np.bool_], epsilon: float) -> dict[str, Any]:
    near = np.abs(direct - epsilon) <= NEAR_EPSILON
    return {
        "tolerance": NEAR_EPSILON,
        "pairs": int(np.count_nonzero(near)),
        "edges": int(np.count_nonzero(near & adjacent)),
        "statement": NEAR_STATEMENT,
    }


def _tree_figures(edges: Sequence[Edge]) -> dict[str, Any]:
    weights = [w for _, _, w in edges]
    return {
        "connectivity_epsilon": max(weights) if weights else None,
        "total_weight": math.fsum(weights),
        "weights": _summary(np.array(weights)),
    }


def _added_links(relations: Sequence[Edge], tree: Sequence[Edge]) -> list[Edge]:
    related = {(i, j) for i, j, _ in relations}
    return [(i, j, w) for i, j, w in tree if (i, j) not in related]


def _union_figures(epsilon_edges: Sequence[Edge], tree: Sequence[Edge]) -> dict[str, Any]:
    added = _added_links(epsilon_edges, tree)
    touched = {k for i, j, _ in epsilon_edges for k in (i, j)}
    return {
        "epsilon_relations": len(epsilon_edges),
        "tree_edges": len(tree),
        "added_links": len(added),
        "added_link_distances": _summary(np.array([w for _, _, w in added])),
        "isolated_reached_only_by_added_links": len({k for i, j, _ in added for k in (i, j)} - touched),
    }


def _cell_figures(
    axis_ids: Sequence[str], cells: NDArray[np.intp], trees: Sequence[Sequence[Edge]], within: Sequence[Edge],
    threshold: Callable[[Sequence[float]], float], key: str,
) -> dict[str, Any]:
    within_cells = [int(cells[i]) for i, _, _ in within]
    return {
        "partition": f"{AXIS_CELLS}; {key} is null for a cell of fewer than two rows",
        "per_axis": [
            {
                "axis": axis_id,
                "size": int(np.count_nonzero(cells == k)),
                key: threshold([w for _, _, w in tree]) if tree else None,
                "tree_weights": _summary(np.array([w for _, _, w in tree])),
                "within_cell_relations": within_cells.count(k),
            }
            for k, (axis_id, tree) in enumerate(zip(axis_ids, trees, strict=True))
        ],
    }


def _share(flags: NDArray[np.bool_]) -> dict[str, Any]:
    count = int(np.count_nonzero(flags))
    return {"count": count, "share": count / len(flags) if len(flags) else None}


def nearest_neighbour_figures(
    d: Array, tree: Sequence[Edge], cells: NDArray[np.intp], axis_ids: Sequence[str],
    labels: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    """Each note's nearest neighbour, whether it lies in the note's axis cell and whether the edge to it is a tree
    edge; the notes listed by that distance, descending, ties by lower row."""
    nearest, distance = nearest_neighbours(d)
    rows = range(len(nearest))
    own = cells[: len(nearest)]
    other = own != cells[nearest]
    in_tree = {(i, j) for i, j, _ in tree}

    def note(i: int) -> dict[str, Any]:
        return {"row": i, "label": labels[i]["label"], "part": labels[i]["part"], "axis": axis_ids[int(cells[i])]}

    return {
        "definition": NEAREST_DEFINITION,
        "distance": _summary(distance),
        "other_cell": _share(other),
        "outside_tree": sum(1 for i in rows if (min(i, int(nearest[i])), max(i, int(nearest[i]))) not in in_tree),
        "per_axis": [
            {"axis": axis_id, "distance": _summary(distance[own == k]), "other_cell": _share(other[own == k])}
            for k, axis_id in enumerate(axis_ids)
        ],
        "notes": [
            {**note(i), "neighbour": note(int(nearest[i])), "distance": float(distance[i]), "same_cell": not other[i]}
            for i in sorted(rows, key=lambda i: (-distance[i], i))
        ],
    }


def _adjacency(n: int, edges: Sequence[Edge]) -> NDArray[np.bool_]:
    adjacent = np.zeros((n, n), dtype=bool)
    for i, j, _ in edges:
        adjacent[i, j] = adjacent[j, i] = True
    return adjacent


def _open_cell_figures(
    axis_ids: Sequence[str], cells: NDArray[np.intp], touching: Sequence[Sequence[float]],
    thresholds: Sequence[float | None], related: Sequence[Edge], tree: Sequence[Edge],
) -> dict[str, Any]:
    ends = np.array([(cells[i], cells[j]) for i, j, _ in related], dtype=np.intp).reshape(-1, 2)
    same = ends[:, 0] == ends[:, 1]
    added = _added_links(related, tree)
    return {
        "partition": f"{AXIS_CELLS}; t_c is null for a cell touched by no tree edge",
        "per_axis": [
            {
                "axis": axis_id,
                "size": int(np.count_nonzero(cells == k)),
                "t_c": t_c,
                "touching_tree_weights": _summary(np.array(weights)),
                "within_cell_relations": int(np.count_nonzero(same & (ends[:, 0] == k))),
                "cross_cell_relations": int(np.count_nonzero(~same & (ends == k).any(axis=1))),
            }
            for k, (axis_id, weights, t_c) in enumerate(zip(axis_ids, touching, thresholds, strict=True))
        ],
        "tree_edges": len(tree),
        "within_cell_relations": int(np.count_nonzero(same)),
        "cross_cell_relations": int(np.count_nonzero(~same)),
        "added_links": len(added),
        "added_link_distances": _summary(np.array([w for _, _, w in added])),
    }


def cells_median_loss(
    d: Array, cells: NDArray[np.intp], medians: Sequence[float | None], tree: Sequence[Edge],
) -> dict[str, Any]:
    """The cross-cell pairs within the smaller median_c of their cells that are not tree edges: the pairs cells_median
    drops though both its cells' thresholds admit them."""
    n = len(d)
    cross = np.triu(cells[:, None] != cells[None, :], 1)
    dropped = cross & (d <= _pair_thresholds(cells, medians)) & ~_adjacency(n, tree)
    rows, cols = np.nonzero(dropped)
    return {
        "definition": LOSS_DEFINITION,
        "cross_cell_pairs": int(np.count_nonzero(cross)),
        "dropped": _share(dropped[cross]),
        "dropped_distances": _summary(d[dropped]),
        "notes_with_dropped": len({*rows.tolist(), *cols.tolist()}),
    }


def explore(
    v: Array, labels: Sequence[Mapping[str, str]], epsilon: float | None, union: bool = False,
    axes: tuple[Sequence[str], Array] | None = None, median: bool = False, open_cells: bool = False,
) -> dict[str, Any]:
    """The figures of the relation graph: the epsilon-relations at epsilon, the minimum spanning tree when
    epsilon is None, or with union the union of both, whose near_epsilon counts the epsilon-relations only.
    With axes (ids, raw vectors) and epsilon None, the per-cell relations of cell_graph and a cells block; with
    median as well, each cell's threshold is median_c, its relations are joined with the whole tree, and a
    nearest_neighbours block is added. With open_cells instead of median, each cell's threshold is t_c, the open
    relations are joined with the whole tree, and nearest_neighbours and cells_median_loss blocks are added."""
    if axes is not None and (epsilon is not None or union):
        raise ValueError("cells relations take no epsilon and no union")
    if median and axes is None:
        raise ValueError("median relations are cells relations and need the axes")
    if open_cells and (axes is None or median):
        raise ValueError("open relations are cells relations, need the axes and exclude median")
    n = len(v)
    names = [item["label"] for item in labels]
    parts = [item["part"] for item in labels]
    d = pairwise_distances(v)
    epsilon_edges = [] if epsilon is None else relations(names, v, epsilon)
    tree_mode = epsilon is None and axes is None
    tree = minimum_spanning_tree(d) if tree_mode or union or median or open_cells else []
    threshold: Callable[[Sequence[float]], float] = median_threshold if median or open_cells else max
    key = "median_c" if median else "epsilon_c"
    if axes is not None:
        cells = axis_cells(v, axes[1])
        trees, within, cross = cell_graph(d, cells, len(axes[1]), threshold)
        if open_cells:
            touching = touching_tree_weights(tree, cells, len(axes[1]))
            thresholds = [median_threshold(weights) if weights else None for weights in touching]
            related = open_relations(d, cells, thresholds)
            edges = union_edges(related, tree, d)
        else:
            edges = union_edges(within, tree if median else cross, d)
    elif union:
        edges = union_edges(epsilon_edges, tree, d)
    else:
        edges = tree if epsilon is None else epsilon_edges
    adjacent = _adjacency(n, edges)
    upper = np.triu_indices(n, 1)
    direct = d[upper]
    degree = adjacent.sum(axis=1)
    found = components(n, edges)
    w, hops = relational_distances(n, edges)
    connected = np.isfinite(w[upper])
    relational = w[upper][connected]
    direct_connected = direct[connected]
    defined = direct_connected > 0.0
    reachable = np.isfinite(w).sum(axis=1) - 1
    farthest = np.where(np.isfinite(w), w, -np.inf).max(axis=1)
    largest = found[0]
    result = {
        "relations": {
            "source": (
                CELLS_OPEN_SOURCE if open_cells else CELLS_MEDIAN_SOURCE if median
                else CELLS_SOURCE if axes is not None else UNION_SOURCE if union
                else MST_SOURCE if epsilon is None else EPSILON_SOURCE
            ),
            "manual": MANUAL_RELATIONS,
            "n_edges": len(edges),
            "near_epsilon": (
                None if epsilon is None
                else _near_epsilon(direct, _adjacency(n, epsilon_edges)[upper], epsilon)
            ),
        },
        "degrees": {
            "isolated": int(np.count_nonzero(degree == 0)),
            "min": int(degree.min()),
            **_quantiles(degree, (0.25, 0.5, 0.75)),
            "mean": float(degree.mean()),
            "max": int(degree.max()),
        },
        "components": {
            "count": len(found),
            "sizes": [len(c) for c in found],
            "largest": {"size": len(largest), "share": len(largest) / n},
        },
        "relational_distances": {
            "definition": DEFINITION,
            "connected_pairs": int(np.count_nonzero(connected)),
            "distance": _summary(relational),
            "eccentricity": _summary(farthest[reachable > 0]),
            "reachable": _summary(reachable),
            "largest_component_diameter": (
                float(w[np.ix_(largest, largest)].max()) if len(largest) > 1 else None
            ),
            "hops": _summary(hops[upper][connected]),
            "ratio_to_direct": _summary(relational[defined] / direct_connected[defined]),
            "ratio_undefined_pairs": int(np.count_nonzero(~defined)),
        },
        "pairwise_distances": {
            "pairs": len(direct),
            "quantiles": _quantiles(direct, PAIRWISE_QUANTILES),
            "share_within_epsilon": (
                float(np.count_nonzero(direct <= epsilon)) / len(direct)
                if epsilon is not None and len(direct) else None
            ),
        },
        "reading_order": {
            "consecutive_row_edges": sum(1 for i, j, _ in edges if j - i == 1),
            "cross_part_edges": sum(1 for i, j, _ in edges if parts[i] != parts[j]),
        },
    }
    if tree_mode or union:
        result["mst"] = _tree_figures(tree)
    if union:
        result["union"] = _union_figures(epsilon_edges, tree)
    if axes is not None and open_cells:
        medians = [median_threshold([w for _, _, w in own]) if own else None for own in trees]
        result["cells"] = _open_cell_figures(axes[0], cells, touching, thresholds, related, tree)
        result["cells_median_loss"] = cells_median_loss(d, cells, medians, tree)
        result["nearest_neighbours"] = nearest_neighbour_figures(d, tree, cells, axes[0], labels)
    elif axes is not None:
        block = _cell_figures(axes[0], cells, trees, within, threshold, key)
        if median:
            added = _added_links(within, tree)
            block |= {
                "tree_edges": len(tree),
                "added_links": len(added),
                "added_link_distances": _summary(np.array([w for _, _, w in added])),
            }
            result["nearest_neighbours"] = nearest_neighbour_figures(d, tree, cells, axes[0], labels)
        else:
            block["cross_cell_links"] = _summary(np.array([w for _, _, w in cross]))
        result["cells"] = block
    return result


# Run ---------------------------------------------------------------------------------------------


def environment() -> dict[str, Any]:
    return {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "numpy_config": np.show_config(mode="dicts"),
        "threads": {var: os.environ.get(var) for var in THREAD_VARS},
    }


def _plain(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_plain(v) for v in obj]
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    return obj


def _write(result: Mapping[str, Any], out_path: Path) -> dict[str, Any]:
    text = json.dumps(_plain(result), sort_keys=True, indent=2, allow_nan=False) + "\n"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8", newline="\n")
    loaded: dict[str, Any] = json.loads(text)
    return loaded


def run(
    embeddings: Path, labels: Path, expected: Mapping[Path, str], out_path: Path, mode: str = "epsilon",
    axes: Path | None = None,
) -> dict[str, Any]:
    """Digests, null elimination, then the figures of the mode's relations (MODES); any refusal raises before
    anything is written. In mst and the cells modes epsilon is null: TRAIANUS_EPSILON_EDGE is not read. The cells
    modes need the axes file, pinned in expected, and check, parse and validate the three inputs as the Z script
    does; the other modes read only embeddings and labels."""
    if mode not in MODES:
        raise ValueError(f"relations mode {mode!r} not in {MODES}")
    axes_path = Path(axes) if mode in CELL_MODES and axes is not None else None
    if mode in CELL_MODES and (axes_path is None or axes_path not in expected):
        raise ValueError("cells mode needs the axes file and its pinned digest")
    embeddings, labels = Path(embeddings), Path(labels)
    raw = k6.check_digests(expected)
    cell_axes: tuple[list[str], Array] | None = None
    if axes_path is None:
        v32, label_list = load_inputs(raw[embeddings], raw[labels])
        validate_inputs(v32, label_list)
    else:
        v32, label_list, axis_ids, a = k6.load_inputs(raw[embeddings], raw[labels], raw[axes_path])
        k6.validate_inputs(v32, label_list, axis_ids, a)
        cell_axes = (axis_ids, a)
    v64 = v32.astype("<f8")
    v = np.array([row / np.sqrt(row @ row) for row in v64])
    epsilon = None if mode in ("mst", *CELL_MODES) else resolve_epsilon_edge()
    inputs = (embeddings, labels) if axes_path is None else (embeddings, labels, axes_path)
    result: dict[str, Any] = {
        "kind": "exploration",
        "statement": STATEMENT,
        "digests": {p.name: expected[p] for p in inputs},
        "epsilon": epsilon,
        "n": len(v),
        "environment": environment(),
        **explore(
            v, label_list, epsilon, union=mode == "union", axes=cell_axes, median=mode == "cells_median",
            open_cells=mode == "cells_open",
        ),
    }
    if axes_path is not None:
        result["cells"]["axes_digest"] = expected[axes_path]
    return _write(result, out_path)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Relational graph exploration of the engine's relations.")
    parser.add_argument(
        "--relations", choices=MODES, default="epsilon",
        help=(
            "epsilon: the engine's epsilon-relations (default); mst: the minimum spanning tree of the L2 distances; "
            "union: the epsilon-relations joined with that tree; cells: per axis cell the pairs within its own "
            "connectivity threshold, the cells joined by that tree; cells_median: per axis cell the pairs within the "
            "median edge of its own tree, joined with the whole tree; cells_open: every pair within the smaller of its "
            "cells' medians of the tree edges touching each cell, joined with the whole tree"
        ),
    )
    parser.add_argument(
        "--out", type=Path, default=None,
        help=(
            f"result path (default: {RESULT}, in mst mode {RESULT_MST}, in union mode {RESULT_UNION}, "
            f"in cells mode {RESULT_CELLS}, in cells_median mode {RESULT_CELLS_MEDIAN}, "
            f"in cells_open mode {RESULT_CELLS_OPEN})"
        ),
    )
    args = parser.parse_args(argv)
    mode: str = args.relations
    cells = mode in CELL_MODES
    out_path: Path = args.out or {
        "epsilon": RESULT, "mst": RESULT_MST, "union": RESULT_UNION, "cells": RESULT_CELLS,
        "cells_median": RESULT_CELLS_MEDIAN, "cells_open": RESULT_CELLS_OPEN,
    }[mode]
    expected = {**EXPECTED_DIGESTS, AXES: AXES_DIGEST} if cells else EXPECTED_DIGESTS
    result = run(EMBEDDINGS, LABELS, expected, out_path, mode, AXES if cells else None)
    if mode == "mst":
        threshold = f" connectivity_epsilon={result['mst']['connectivity_epsilon']!r}"
    elif cells:
        threshold = ""
    else:
        threshold = f" epsilon={result['epsilon']}"
    if mode == "union":
        added = f" added_links={result['union']['added_links']}"
    elif mode == "cells_median":
        added = f" added_links={result['cells']['added_links']}"
    elif mode == "cells_open":
        added = (
            f" cross_cell_relations={result['cells']['cross_cell_relations']}"
            f" added_links={result['cells']['added_links']}"
        )
    elif cells:
        added = f" cross_cell_links={result['cells']['cross_cell_links']['count']}"
    else:
        added = ""
    print(
        f"relational graph: n={result['n']} relations={mode}{threshold} "
        f"edges={result['relations']['n_edges']}{added} components={result['components']['count']} -> {out_path}"
    )


if __name__ == "__main__":
    main()
