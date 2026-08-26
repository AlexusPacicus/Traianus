#!/usr/bin/env python
"""Inter-part epsilon-edge matrix normalized as enrichment ratios.

observed(block_a<->block_b) / expected under size-proportional homogeneity:
expected = M * n_a * n_b / C(N,2) (off-diagonal) or M * C(n_a,2) / C(N,2)
(diagonal). No fixed analytic thresholds: pass the epsilon* reported by
epsilon_knee_audit. Reports tracemalloc peak for the O(N^2)-scale pass.

Read-only audit: SQLite opened mode=ro, never mutates state (AGENTS 4.3).
"""
import argparse
import json
import sys
import tracemalloc
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.analyze_bridges import load_current_nodes
from tools.experiments.tooling._common import load_labels
from traianus.geometry.observables import compute_epsilon_edges

DEFAULT_DB = Path(__file__).resolve().parents[3] / ".data" / "spinoza_full.db"
DEFAULT_LABELS = (Path(__file__).resolve().parents[3] / ".data"
                  / "spinoza_full_labels.json")
PART_BY_PREFIX = {"PART1": "P1_GOD", "PART2": "P2_MIND", "PART3": "P3_AFFECTS",
                  "PART4": "P4_BONDAGE", "PART5": "P5_POWER"}


def part_of(label: str) -> str:
    return PART_BY_PREFIX[label[:5]]


def enrichment_matrix(observed, sizes):
    """Enrichment ratio per block pair from edge counts + block sizes."""
    keys = sorted(sizes)
    n = sum(sizes.values())
    total_pairs = n * (n - 1) / 2.0
    m = sum(observed.values())
    result = {}
    for i, a in enumerate(keys):
        for b in keys[i:]:
            pairs = (sizes[a] * (sizes[a] - 1) / 2.0 if a == b
                     else sizes[a] * sizes[b])
            key = a if a == b else " <-> ".join((a, b))
            expected = m * pairs / total_pairs
            result[key] = {
                "observed": observed.get(key, 0),
                "expected": round(expected, 2),
                "enrichment": (round(observed.get(key, 0) / expected, 4)
                               if expected else None),
            }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inter-part epsilon-edge enrichment matrix.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB,
                        help=f"SQLite database path (default: {DEFAULT_DB})")
    parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS,
                        help=f"node labels JSON (default: {DEFAULT_LABELS})")
    parser.add_argument("--epsilon", type=float, required=True,
                        help="E_n threshold (pass the Otsu epsilon*)")
    parser.add_argument("--json-out", type=Path, default=None,
                        help="optional path for the full JSON report")
    args = parser.parse_args()

    if not Path(args.db).exists():
        print(f"error: database not found: {args.db}")
        sys.exit(2)
    if not Path(args.labels).exists():
        print(f"error: labels file not found: {args.labels}")
        sys.exit(2)

    labels = load_labels(args.labels)
    tracemalloc.start()
    nodes = load_current_nodes(args.db)
    vectors = {n["id"]: n["vector"] for n in nodes}
    edges = compute_epsilon_edges(vectors, args.epsilon)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    node_part = {nid: part_of(labels[nid]) for nid in vectors}
    sizes = {p: sum(1 for v in node_part.values() if v == p)
             for p in PART_BY_PREFIX.values()}
    observed = {}
    for e in edges:
        pa, pb = node_part[e["source"]], node_part[e["target"]]
        key = pa if pa == pb else " <-> ".join(sorted((pa, pb)))
        observed[key] = observed.get(key, 0) + 1

    matrix = enrichment_matrix(observed, sizes)
    peak_mb = round(peak / 1024 / 1024, 1)
    print(f"epsilon={args.epsilon:.4f} edges={len(edges)} "
          f"peak_memory_mb={peak_mb}")
    for k in sorted(matrix):
        cell = matrix[k]
        print(f"{k}: obs={cell['observed']} exp={cell['expected']} "
              f"enrichment={cell['enrichment']}")
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps({
            "epsilon": args.epsilon, "total_edges": len(edges),
            "nodes": len(vectors), "block_sizes": sizes,
            "peak_memory_mb": peak_mb, "matrix": matrix}, indent=2))
        print(f"report written: {args.json_out}")


if __name__ == "__main__":
    main()
