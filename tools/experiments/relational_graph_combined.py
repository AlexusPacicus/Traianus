"""Relational graph combined: the union and open-borders graphs joined, described side by side.

Descriptive exploration (docs/methodology/METHODOLOGY.md, Explore): it tests no hypothesis and decides nothing.
Implements the delegation contract relational-graph-combined (B1-B8) against
docs/methodology/instrument-audit/contracts.md section 0. On the whole frozen corpus it builds the union (the
engine's epsilon-relations joined with the minimum spanning tree), the open borders (the cells_open relations joined
with the tree) and their combination (every pair of either), gives the three the figures
relational_graph_exploration gave its variants, and adds their overlap and the size of each spiral turn. Union and
open borders are also checked against the committed files of that exploration, field by field.

Imports relational_graph_exploration as a module and reuses its functions, which are pinned by sha256 in
tension_gate*.py and so are never edited; refuses to run, writing nothing, unless both modules, the three input
digests, the two reference files and epsilon = 0.8 match.

Usage:
    python3 tools/experiments/relational_graph_combined.py [--out PATH]
"""

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_var] = "1"

import argparse
import hashlib
import json
import sys
from collections.abc import Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any, NamedTuple

import numpy as np
from numpy.typing import NDArray

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.experiments import k6_colour_predictability as k6
from tools.experiments import relational_graph_exploration as rge
from traianus.config import resolve_epsilon_edge

Array = rge.Array
Edge = rge.Edge

RGE_FILE = Path(rge.__file__)
RGE_SHA256 = "627aa8e95a844b0aec290a41c48b9a0bf6890db25b5240b5730c366a56d2e7dc"
K6_FILE = Path(k6.__file__)
K6_SHA256 = "6289c596792154f6bb799606265c68719c6b8c7ae8b69084116dfb23c77876d2"
EPSILON = 0.8
EMBEDDINGS = rge.EMBEDDINGS
LABELS = rge.LABELS
AXES = rge.AXES
EXPECTED = {**rge.EXPECTED_DIGESTS, rge.AXES: rge.AXES_DIGEST}
REFERENCES = {
    "union": (rge.RESULT_UNION, "300f929d3cc9bb920203c7d050ed41b22570cba1cf8b391f8af47ed224ba04d5"),
    "open_borders": (rge.RESULT_CELLS_OPEN, "546d75fa31735adc5952929dad2674bbf6959219d89ca284b44f6bd77f489360"),
}
RESULT = REPO_ROOT / "data" / "refapp" / "relational_graph_combined.json"

GENERIC = ("relations", "degrees", "components", "relational_distances", "reading_order")
STATEMENT = (
    "Descriptive exploration of the union and open-borders relation graphs and their combination: it tests no "
    "hypothesis and decides nothing."
)
TURNS_DEFINITION = (
    "spiral turn k: for each note, the number of notes at exactly k hops (relations on the shortest path), k from 1 "
    "to the largest finite hop count of the graph; half_reach: per note the smallest k at which at least half of "
    "the other notes (n - 1 over 2) lie within k hops, a note that never reaches half counted in undefined and "
    "left out of the summary; quantiles are numpy.quantile's default over notes"
)


# Graphs -----------------------------------------------------------------------------------------------


class Graphs(NamedTuple):
    d: Array
    cells: NDArray[np.intp]
    tree: list[Edge]
    epsilon_edges: list[Edge]
    related: list[Edge]
    union: list[Edge]
    open_borders: list[Edge]
    combined: list[Edge]


def build_graphs(names: Sequence[str], v: Array, a: Array) -> Graphs:
    """The three graphs on the whole corpus, as rge.explore builds its union and cells_open variants."""
    d = rge.pairwise_distances(v)
    tree = rge.minimum_spanning_tree(d)
    epsilon_edges = rge.relations(names, v, EPSILON)
    cells = rge.axis_cells(v, a)
    touching = rge.touching_tree_weights(tree, cells, len(a))
    thresholds = [rge.median_threshold(weights) if weights else None for weights in touching]
    related = rge.open_relations(d, cells, thresholds)
    union = rge.union_edges(epsilon_edges, tree, d)
    open_borders = rge.union_edges(related, tree, d)
    return Graphs(
        d, cells, tree, epsilon_edges, related, union, open_borders, rge.union_edges(union, open_borders, d)
    )


# Figures ----------------------------------------------------------------------------------------------


def generic_block(d: Array, edges: Sequence[Edge], parts: Sequence[str]) -> tuple[dict[str, Any], Array]:
    """The figures rge.explore returns for any variant, and the hops matrix, computed as it computes them."""
    n = len(d)
    upper = np.triu_indices(n, 1)
    direct = d[upper]
    degree = rge._adjacency(n, edges).sum(axis=1)
    found = rge.components(n, edges)
    w, hops = rge.relational_distances(n, edges)
    connected = np.isfinite(w[upper])
    relational = w[upper][connected]
    direct_connected = direct[connected]
    defined = direct_connected > 0.0
    reachable = np.isfinite(w).sum(axis=1) - 1
    farthest = np.where(np.isfinite(w), w, -np.inf).max(axis=1)
    largest = found[0]
    block = {
        "relations": {"n_edges": len(edges)},
        "degrees": {
            "isolated": int(np.count_nonzero(degree == 0)),
            "min": int(degree.min()),
            **rge._quantiles(degree, (0.25, 0.5, 0.75)),
            "mean": float(degree.mean()),
            "max": int(degree.max()),
        },
        "components": {
            "count": len(found),
            "sizes": [len(c) for c in found],
            "largest": {"size": len(largest), "share": len(largest) / n},
        },
        "relational_distances": {
            "definition": rge.DEFINITION,
            "connected_pairs": int(np.count_nonzero(connected)),
            "distance": rge._summary(relational),
            "eccentricity": rge._summary(farthest[reachable > 0]),
            "reachable": rge._summary(reachable),
            "largest_component_diameter": (
                float(w[np.ix_(largest, largest)].max()) if len(largest) > 1 else None
            ),
            "hops": rge._summary(hops[upper][connected]),
            "ratio_to_direct": rge._summary(relational[defined] / direct_connected[defined]),
            "ratio_undefined_pairs": int(np.count_nonzero(~defined)),
        },
        "reading_order": {
            "consecutive_row_edges": sum(1 for i, j, _ in edges if j - i == 1),
            "cross_part_edges": sum(1 for i, j, _ in edges if parts[i] != parts[j]),
        },
    }
    return block, hops


def spiral_turns(hops: Array) -> dict[str, Any]:
    """Per turn k, the notes at exactly k hops, summarised over notes; per note, the turn reaching half the others."""
    n = len(hops)
    largest = int(hops[np.isfinite(hops)].max())
    at = np.array([(hops == k).sum(axis=1) for k in range(1, largest + 1)]).reshape(largest, n)
    enough = 2 * np.cumsum(at, axis=0) >= n - 1
    reaches = enough.any(axis=0)
    turn = enough.argmax(axis=0) + 1 if largest else np.zeros(n, dtype=np.intp)
    return {
        "largest_hops": largest,
        "per_turn": [{"k": k, **rge._summary(at[k - 1])} for k in range(1, largest + 1)],
        "half_reach": {"undefined": int(np.count_nonzero(~reaches)), **rge._summary(turn[reaches])},
    }


def describe(
    d: Array, cells: NDArray[np.intp], edges: Sequence[Edge], parts: Sequence[str]
) -> tuple[dict[str, Any], dict[str, Any]]:
    """One graph's figures (the generic block, beta = 2 |E| / n, the relations across axis cells) and turns."""
    block, hops = generic_block(d, edges, parts)
    figures = {
        **block,
        "beta": 2 * len(edges) / len(d),
        "cross_cell_relations": sum(1 for i, j, _ in edges if cells[i] != cells[j]),
    }
    return figures, spiral_turns(hops)


# Reproduction and overlap -----------------------------------------------------------------------------


def _differences(got: Any, want: Any, path: str) -> Iterator[str]:
    if not isinstance(got, dict):
        if got != want:
            yield path
    elif not isinstance(want, dict):
        yield path
    else:
        for key in sorted(got):
            if key in want:
                yield from _differences(got[key], want[key], f"{path}.{key}")
            else:
                yield f"{path}.{key}"


def reproduce(
    figures: Mapping[str, Mapping[str, Any]], references: Mapping[str, Any]
) -> tuple[dict[str, bool], list[str]]:
    """Per variant, whether every field of the generic block equals the reference file's; the unequal ones, named."""
    reproduction: dict[str, bool] = {}
    mismatches: list[str] = []
    for name, own in figures.items():
        got = json.loads(json.dumps(rge._plain({key: own[key] for key in GENERIC}), allow_nan=False))
        found = list(_differences(got, references[name], name))
        reproduction[name] = not found
        mismatches += found
    return reproduction, mismatches


def _pair_set(edges: Sequence[Edge]) -> set[tuple[int, int]]:
    return {(min(i, j), max(i, j)) for i, j, _ in edges}


def overlap(
    epsilon_edges: Sequence[Edge], related: Sequence[Edge], tree: Sequence[Edge], union: Sequence[Edge],
    open_borders: Sequence[Edge], combined: Sequence[Edge],
) -> dict[str, Any]:
    tree_pairs = _pair_set(tree)
    u, o, c = _pair_set(union), _pair_set(open_borders), _pair_set(combined)

    def count(pairs: set[tuple[int, int]]) -> dict[str, int]:
        return {"edges": len(pairs), "tree_edges": len(pairs & tree_pairs)}

    return {
        "union": count(u),
        "open_borders": count(o),
        "combined": count(c),
        "both": count(u & o),
        "union_only": count(u - o),
        "open_borders_only": count(o - u),
        "epsilon_not_in_open_borders": len(_pair_set(epsilon_edges) - o),
        "open_relations_not_in_union": len(_pair_set(related) - u),
    }


# Run and command line ---------------------------------------------------------------------------------


def _pinned(path: Path, digest: str) -> bytes:
    data = Path(path).read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != digest:
        raise k6.IntegrityError(f"sha256 mismatch for {path}: expected {digest}, got {actual}")
    return data


def run(
    k6_file: Path, rge_file: Path, embeddings: Path, labels: Path, axes: Path, expected: Mapping[Path, str],
    references: Mapping[str, tuple[Path, str]], out_path: Path,
) -> dict[str, Any]:
    """Pins, digests and null elimination, then the three graphs; any refusal raises before anything is written.
    A reference that is not reproduced makes valid false and is named; the figures are written either way."""
    _pinned(k6_file, K6_SHA256)
    _pinned(rge_file, RGE_SHA256)
    epsilon = resolve_epsilon_edge()
    if epsilon != EPSILON:
        raise k6.IntegrityError(f"epsilon {epsilon!r} is not {EPSILON}")
    raw = k6.check_digests(expected)
    reference = {name: json.loads(_pinned(path, digest)) for name, (path, digest) in references.items()}
    inputs = (Path(embeddings), Path(labels), Path(axes))
    v32, label_list, axis_ids, a = k6.load_inputs(*(raw[p] for p in inputs))
    k6.validate_inputs(v32, label_list, axis_ids, a)
    v64 = v32.astype("<f8")
    v = np.array([row / np.sqrt(row @ row) for row in v64])
    parts = [item["part"] for item in label_list]
    g = build_graphs([item["label"] for item in label_list], v, a)
    described = {
        name: describe(g.d, g.cells, edges, parts)
        for name, edges in (("union", g.union), ("open_borders", g.open_borders), ("combined", g.combined))
    }
    reproduction, mismatches = reproduce({name: described[name][0] for name in references}, reference)
    result = {
        "kind": "exploration",
        "statement": STATEMENT,
        "n": len(v),
        "epsilon": EPSILON,
        "digests": {
            **{p.name: expected[p] for p in inputs},
            Path(k6_file).name: K6_SHA256,
            Path(rge_file).name: RGE_SHA256,
            **{Path(path).name: digest for path, digest in references.values()},
        },
        "environment": rge.environment(),
        "valid": all(reproduction.values()),
        "reproduction": reproduction,
        "mismatches": mismatches,
        "turns_definition": TURNS_DEFINITION,
        "graphs": {name: {"figures": figures, "turns": turns} for name, (figures, turns) in described.items()},
        "overlap": overlap(g.epsilon_edges, g.related, g.tree, g.union, g.open_borders, g.combined),
    }
    return rge._write(result, Path(out_path))


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Relational graph: union and open borders combined.")
    parser.add_argument("--out", type=Path, default=RESULT, help=f"result path (default: {RESULT})")
    out_path: Path = parser.parse_args(argv).out
    result = run(K6_FILE, RGE_FILE, EMBEDDINGS, LABELS, AXES, EXPECTED, REFERENCES, out_path)
    edges = {name: result["overlap"][name]["edges"] for name in ("union", "open_borders", "combined")}
    print(
        f"relational graph combined: n={result['n']} union={edges['union']} open_borders={edges['open_borders']} "
        f"combined={edges['combined']} components={result['graphs']['combined']['figures']['components']['count']} "
        f"valid={result['valid']} -> {out_path}"
    )
    if not result["valid"]:
        raise SystemExit(f"reference not reproduced: {result['mismatches']}")


if __name__ == "__main__":
    main()
