#!/usr/bin/env python
"""Audit non-sequential semantic bridges in the epsilon-adjacency E_n.

A bridge is an E_n edge (ADR-023/H5: ||v_i - v_j||_2 <= epsilon over the
384D float64 manifold) whose endpoints are non-contiguous in reading order
(|i - j| > 1 by ingestion sequence position): distant propositions that
resonate across pages.

v2 instrumentation:
- Null model: every-run histogram + percentiles of the full pairwise
  distance distribution, with the isotropic random-unit reference sqrt(2).
- Adaptive threshold: --percentile P derives epsilon from that null model;
  both modes run side by side and are compared (counts, Jaccard, shared
  top pairs).
- Resonance axis: co-activation argmax_k(|q_i,k * q_j,k|) over the R^8
  spectral projections — rewards axes where BOTH endpoints project strongly,
  replacing the min-delta heuristic that rewarded dormant axes.
- --exclude drops bootstrap/noise ids before contiguity (positions collapse);
  --top limits the printed ranking.

Read-only audit: opens SQLite in URI mode=ro, never mutates state
(AGENTS.md 4.3).
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from traianus.geometry.observables import compute_epsilon_edges

DEFAULT_DB = Path(__file__).resolve().parents[1] / "traianus.db"
EPSILON = 0.8

_CURRENT_NODES_SQL = """
    SELECT m.id, m.text, m.vector_blob, m.projections_json
    FROM manifold_nodes m
    WHERE m.lifecycle_state != 'telemetry_error'
      AND m.seq = (SELECT MAX(seq) FROM manifold_nodes m2 WHERE m2.id = m.id)
    ORDER BY CAST(SUBSTR(m.id, 6) AS INTEGER), m.id
"""


def load_current_nodes(db_path: Path) -> list[dict]:
    """Current manifold state (MAX(seq)/id, telemetry_error excluded)."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = conn.execute(_CURRENT_NODES_SQL).fetchall()
    finally:
        conn.close()
    return [
        {
            "id": nid,
            "text": text,
            "vector": np.frombuffer(blob, dtype=np.float64),
            "projections": json.loads(projections_json),
        }
        for nid, text, blob, projections_json in rows
    ]


def _axis_sorted(projections: dict) -> list[str]:
    return sorted(projections, key=lambda k: int(k.rsplit("_", 1)[1]))


def resonance_axis(proj_a: dict, proj_b: dict) -> tuple[str, float]:
    """Co-activation resonance: axis maximizing |q_a,k * q_b,k|."""
    keys = _axis_sorted(proj_a)
    q_a = np.array([proj_a[k] for k in keys], dtype=np.float64)
    q_b = np.array([proj_b[k] for k in keys], dtype=np.float64)
    products = np.abs(q_a * q_b)
    k = int(np.argmax(products))
    return f"AXIS_{k + 1}", float(products[k])


def find_bridges(nodes: list[dict], epsilon: float) -> list[dict]:
    """Non-contiguous E_n edges ordered by attraction strength (distance asc)."""
    position = {node["id"]: i for i, node in enumerate(nodes)}
    edges = compute_epsilon_edges(
        {node["id"]: node["vector"] for node in nodes}, epsilon)
    bridges = []
    for edge in edges:
        i, j = position[edge["source"]], position[edge["target"]]
        if abs(i - j) <= 1:
            continue
        axis, score = resonance_axis(
            nodes[i]["projections"], nodes[j]["projections"])
        bridges.append({
            "source": edge["source"],
            "target": edge["target"],
            "distance": edge["distance"],
            "axis": axis,
            "coactivation": score,
        })
    bridges.sort(key=lambda b: b["distance"])
    return bridges


def apply_exclusions(nodes: list[dict], excluded_ids: set) -> list[dict]:
    """Drop excluded ids preserving reading order (contiguity collapses)."""
    return [node for node in nodes if node["id"] not in excluded_ids]


def pairwise_distances(vectors: dict) -> np.ndarray:
    """Null model: L2 distances for every unordered pair, sorted-id order."""
    ids = sorted(vectors)
    if len(ids) < 2:
        return np.empty(0)
    stack = np.vstack([vectors[nid] for nid in ids])
    chunks = [
        np.linalg.norm(stack[i + 1:] - stack[i], axis=1)
        for i in range(len(ids) - 1)
    ]
    return np.concatenate(chunks)


def adaptive_epsilon(distances: np.ndarray, percentile: float) -> float:
    """Threshold keeping the closest `percentile`% of null-model pairs."""
    return float(np.percentile(distances, 100.0 - percentile))


def distance_summary(distances: np.ndarray, bins: int = 12) -> str:
    """ASCII histogram + null-model stats (isotropic reference sqrt(2))."""
    hist, bin_edges = np.histogram(distances, bins=bins)
    peak = max(int(hist.max()), 1)
    lines = [
        f"null model: n_pairs={distances.size} | mean={distances.mean():.4f} "
        f"| p1={np.percentile(distances, 1):.4f} "
        f"| p5={np.percentile(distances, 5):.4f} "
        f"| p50={np.percentile(distances, 50):.4f} "
        f"| random-unit ref=sqrt(2)=1.4142"
    ]
    for count, lo, hi in zip(hist, bin_edges[:-1], bin_edges[1:]):
        bar = "#" * int(round(40 * count / peak))
        lines.append(f"{lo:.3f}-{hi:.3f} | {bar} {count}")
    return "\n".join(lines)


def bridge_set_overlap(a: list[dict], b: list[dict]) -> dict:
    """Pair-set intersection, Jaccard and strongest shared bridges."""
    pairs_a = {(e["source"], e["target"]) for e in a}
    pairs_b = {(e["source"], e["target"]) for e in b}
    intersection = pairs_a & pairs_b
    union = pairs_a | pairs_b
    best_distance = {}
    for edge in a + b:
        pair = (edge["source"], edge["target"])
        if pair not in best_distance or edge["distance"] < best_distance[pair]:
            best_distance[pair] = edge["distance"]
    return {
        "intersection": len(intersection),
        "jaccard": len(intersection) / len(union) if union else 1.0,
        "top_common": sorted(intersection, key=lambda p: best_distance[p])[:10],
    }


def _preview(text: str, limit: int = 80) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[:limit] + "..."


def print_report(nodes: list[dict], total_edges: int, bridges: list[dict],
                 epsilon: float, label: str = "fixed",
                 top: int | None = None) -> None:
    texts = {node["id"]: node["text"] for node in nodes}
    shown = bridges if top is None else bridges[:max(top, 0)]
    contiguous = total_edges - len(bridges)
    print(f"\n=== [{label}] NON-LINEAR BRIDGE AUDIT (epsilon={epsilon:.4f}) ===")
    print(f"nodes={len(nodes)} | E_n={total_edges} | contiguous={contiguous} "
          f"| bridges={len(bridges)} | showing={len(shown)}")
    for bridge in shown:
        print(f"\n[D={bridge['distance']:.4f} | resonance {bridge['axis']} "
              f"| coact={bridge['coactivation']:.4f}]")
        print(f"  |- {bridge['source']}: {_preview(texts[bridge['source']])}")
        print(f"  '- {bridge['target']}: {_preview(texts[bridge['target']])}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit non-sequential semantic bridges in the E_n adjacency.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB,
                        help=f"SQLite database path (default: {DEFAULT_DB})")
    parser.add_argument("--epsilon", type=float, default=EPSILON,
                        help=f"fixed E_n adjacency threshold (default: {EPSILON})")
    parser.add_argument("--percentile", type=float, default=None,
                        help="derive an adaptive epsilon keeping the closest "
                             "PERCENTILE%% of null-model pairs and compare modes")
    parser.add_argument("--exclude", default="",
                        help="comma-separated node ids to drop before analysis")
    parser.add_argument("--top", type=int, default=None,
                        help="limit printed bridges per mode (strongest first)")
    args = parser.parse_args()

    nodes = load_current_nodes(args.db)
    excluded = {token.strip() for token in args.exclude.split(",") if token.strip()}
    if excluded:
        nodes = apply_exclusions(nodes, excluded)
    vectors = {node["id"]: node["vector"] for node in nodes}

    distances = pairwise_distances(vectors)
    print(distance_summary(distances))

    runs = [("fixed", args.epsilon)]
    if args.percentile is not None:
        runs.append((f"adaptive-p{args.percentile:g}",
                     adaptive_epsilon(distances, args.percentile)))
    labeled = []
    for label, epsilon in runs:
        edges_all = compute_epsilon_edges(vectors, epsilon)
        labeled.append((label, epsilon, edges_all, find_bridges(nodes, epsilon)))

    if len(labeled) == 2:
        overlap = bridge_set_overlap(labeled[0][3], labeled[1][3])
        print("\n=== COMPARISON "
              f"fixed(e={labeled[0][1]:.4f}) vs adaptive(e={labeled[1][1]:.4f}) ===")
        print(f"bridges: fixed={len(labeled[0][3])} "
              f"adaptive={len(labeled[1][3])} | "
              f"intersection={overlap['intersection']} "
              f"| jaccard={overlap['jaccard']:.3f}")
        shared = ", ".join(f"{src}<->{dst}"
                           for src, dst in overlap["top_common"]) or "(none)"
        print(f"strongest shared: {shared}")

    for label, epsilon, edges_all, bridges in labeled:
        print_report(nodes, len(edges_all), bridges, epsilon,
                     label=label, top=args.top)


if __name__ == "__main__":
    main()
