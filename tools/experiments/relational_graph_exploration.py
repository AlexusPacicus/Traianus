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
Descriptive: it tests no hypothesis and decides nothing.

Refuses to run, writing nothing, unless both input digests match the Z script's pins.

Usage:
    python3 tools/experiments/relational_graph_exploration.py [--relations {epsilon,mst,union}] [--out PATH]
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
from collections.abc import Mapping, Sequence
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
MODES = ("epsilon", "mst", "union")
EXPECTED_DIGESTS = {
    EMBEDDINGS: "eafb0e97172830f2404e96fa08d74bf6cccc0b6cbe84d47b790a476603e7d8d1",
    LABELS: "1d60699353d810f089730c6203ee28f9c416e3004b60781bc965cec284097f4f",
}
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


def _union_figures(epsilon_edges: Sequence[Edge], tree: Sequence[Edge]) -> dict[str, Any]:
    related = {(i, j) for i, j, _ in epsilon_edges}
    added = [(i, j, w) for i, j, w in tree if (i, j) not in related]
    touched = {k for i, j, _ in epsilon_edges for k in (i, j)}
    return {
        "epsilon_relations": len(epsilon_edges),
        "tree_edges": len(tree),
        "added_links": len(added),
        "added_link_distances": _summary(np.array([w for _, _, w in added])),
        "isolated_reached_only_by_added_links": len({k for i, j, _ in added for k in (i, j)} - touched),
    }


def _adjacency(n: int, edges: Sequence[Edge]) -> NDArray[np.bool_]:
    adjacent = np.zeros((n, n), dtype=bool)
    for i, j, _ in edges:
        adjacent[i, j] = adjacent[j, i] = True
    return adjacent


def explore(
    v: Array, labels: Sequence[Mapping[str, str]], epsilon: float | None, union: bool = False
) -> dict[str, Any]:
    """The figures of the relation graph: the epsilon-relations at epsilon, the minimum spanning tree when
    epsilon is None, or with union the union of both, whose near_epsilon counts the epsilon-relations only."""
    n = len(v)
    names = [item["label"] for item in labels]
    parts = [item["part"] for item in labels]
    d = pairwise_distances(v)
    epsilon_edges = [] if epsilon is None else relations(names, v, epsilon)
    tree = minimum_spanning_tree(d) if epsilon is None or union else []
    if union:
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
            "source": UNION_SOURCE if union else MST_SOURCE if epsilon is None else EPSILON_SOURCE,
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
    if epsilon is None or union:
        result["mst"] = _tree_figures(tree)
    if union:
        result["union"] = _union_figures(epsilon_edges, tree)
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
    embeddings: Path, labels: Path, expected: Mapping[Path, str], out_path: Path, mode: str = "epsilon"
) -> dict[str, Any]:
    """Digests, null elimination, then the figures of the mode's relations (MODES); any refusal raises before
    anything is written. In mst mode epsilon is null: TRAIANUS_EPSILON_EDGE is not read."""
    if mode not in MODES:
        raise ValueError(f"relations mode {mode!r} not in {MODES}")
    embeddings, labels = Path(embeddings), Path(labels)
    raw = k6.check_digests(expected)
    v32, label_list = load_inputs(raw[embeddings], raw[labels])
    validate_inputs(v32, label_list)
    v64 = v32.astype("<f8")
    v = np.array([row / np.sqrt(row @ row) for row in v64])
    epsilon = None if mode == "mst" else resolve_epsilon_edge()
    result = {
        "kind": "exploration",
        "statement": STATEMENT,
        "digests": {p.name: expected[p] for p in (embeddings, labels)},
        "epsilon": epsilon,
        "n": len(v),
        "environment": environment(),
        **explore(v, label_list, epsilon, union=mode == "union"),
    }
    return _write(result, out_path)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Relational graph exploration of the engine's relations.")
    parser.add_argument(
        "--relations", choices=MODES, default="epsilon",
        help=(
            "epsilon: the engine's epsilon-relations (default); mst: the minimum spanning tree of the L2 distances; "
            "union: the epsilon-relations joined with that tree"
        ),
    )
    parser.add_argument(
        "--out", type=Path, default=None,
        help=f"result path (default: {RESULT}, in mst mode {RESULT_MST}, in union mode {RESULT_UNION})",
    )
    args = parser.parse_args(argv)
    mode: str = args.relations
    out_path: Path = args.out or {"epsilon": RESULT, "mst": RESULT_MST, "union": RESULT_UNION}[mode]
    result = run(EMBEDDINGS, LABELS, EXPECTED_DIGESTS, out_path, mode)
    threshold = (
        f"connectivity_epsilon={result['mst']['connectivity_epsilon']!r}" if mode == "mst"
        else f"epsilon={result['epsilon']}"
    )
    added = f" added_links={result['union']['added_links']}" if mode == "union" else ""
    print(
        f"relational graph: n={result['n']} relations={mode} {threshold} "
        f"edges={result['relations']['n_edges']}{added} components={result['components']['count']} -> {out_path}"
    )


if __name__ == "__main__":
    main()
