#!/usr/bin/env python
"""Adaptive epsilon selection from the empirical pairwise-distance structure.

No fixed analytic thresholds: epsilon* is the Otsu two-class threshold over
the null-model pairwise distances — the cut that maximizes between-class
variance, separating the intra-cluster distance mode from the isotropic
bulk (random-unit reference sqrt(2)). A dense kept-percentile sweep is
reported as a descriptive multi-threshold table, and seed-stable bootstrap
dispersion quantifies the stability of epsilon*.

Read-only audit: SQLite opened mode=ro, never mutates state (AGENTS 4.3).
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

DEFAULT_DB = Path(__file__).resolve().parents[3] / ".data" / "spinoza_full.db"


def load_pairwise_distances(db_path):
    """Full null-model distances + contiguous-edge distances + node count."""
    import tools.analyze_bridges as ab

    nodes = ab.load_current_nodes(Path(db_path))
    vectors = {n["id"]: n["vector"] for n in nodes}
    all_d = ab.pairwise_distances(vectors)
    contiguous = np.sort(np.array([
        float(np.linalg.norm(nodes[i]["vector"] - nodes[i + 1]["vector"]))
        for i in range(len(nodes) - 1)
    ]))
    return all_d, contiguous, len(nodes)


def otsu_threshold(values, bins: int = 256) -> float:
    """Otsu threshold: cut maximizing between-class variance.

    All cuts inside the inter-mode valley tie for optimality; the reported
    threshold is the center of that optimal plateau, removing the
    left-edge arbitrariness that would otherwise inflate bootstrap
    dispersion.
    """
    values = np.asarray(values, dtype=np.float64)
    lo, hi = float(values.min()), float(values.max())
    if not hi > lo:
        return lo
    hist, edges = np.histogram(values, bins=bins, range=(lo, hi))
    probs = hist.astype(np.float64) / hist.sum()
    omega = np.cumsum(probs)
    centers = (edges[:-1] + edges[1:]) / 2.0
    mu = np.cumsum(probs * centers)
    mu_total = mu[-1]
    denom = omega * (1.0 - omega)
    safe_denom = np.where(denom > 0, denom, 1.0)
    between = np.where(denom > 0,
                       (mu_total * omega - mu) ** 2 / safe_denom,
                       -1.0)
    plateau = np.flatnonzero(between >= between.max() * (1.0 - 1e-9))
    return float(np.mean(edges[plateau + 1]))


def sweep_bridges(all_d, contiguous_d, p_grid):
    """For each kept-percentile P: epsilon, total edges, non-contiguous bridges.

    epsilon(P) = empirical quantile P of the null model, i.e. the threshold
    retaining the closest P% of all pairs. Exact and O(log n) per grid point
    via sorted-distance searchsorted.
    """
    all_sorted = np.sort(all_d)
    rows = []
    for p in p_grid:
        epsilon = float(np.percentile(all_d, p))
        total = int(np.searchsorted(all_sorted, epsilon, side="right"))
        contig = int(np.searchsorted(contiguous_d, epsilon, side="right"))
        rows.append({"percentile": round(float(p), 6), "epsilon": epsilon,
                     "edges": total, "bridges": total - contig})
    return rows


def bootstrap_epsilon_stability(all_d, replicas, pairs_per_replica, seed):
    """Nonparametric bootstrap over pairs -> dispersion of the Otsu epsilon*."""
    rng = np.random.default_rng(seed)
    n_draw = int(min(pairs_per_replica, all_d.size))
    epsilons = []
    for _ in range(replicas):
        sub = all_d[rng.integers(0, all_d.size, n_draw)]
        epsilons.append(round(otsu_threshold(sub), 6))
    return {
        "epsilons": epsilons,
        "mean": float(np.mean(epsilons)),
        "std": float(np.std(epsilons)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Adaptive epsilon selection via Otsu thresholding of "
                    "the E_n null-model distances.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB,
                        help=f"SQLite database path (default: {DEFAULT_DB})")
    parser.add_argument("--p-min", type=float, default=0.1,
                        help="lowest kept-percentile of the descriptive sweep")
    parser.add_argument("--p-max", type=float, default=20.0,
                        help="highest kept-percentile of the descriptive sweep")
    parser.add_argument("--p-step", type=float, default=0.1,
                        help="sweep resolution in kept-percentile points")
    parser.add_argument("--replicas", type=int, default=100,
                        help="bootstrap replicas for epsilon* stability")
    parser.add_argument("--pairs-per-replica", type=int, default=200000,
                        help="resampling budget per replica")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--json-out", type=Path, default=None,
                        help="optional path for the full JSON report")
    args = parser.parse_args()

    if not Path(args.db).exists():
        print(f"error: database not found: {args.db}")
        sys.exit(2)

    all_d, cont_d, n_nodes = load_pairwise_distances(args.db)
    if all_d.size == 0:
        print(f"notice: fewer than 2 manifold nodes in {args.db}; "
              "nothing to audit.")
        return

    epsilon_star = otsu_threshold(all_d)
    kept_mass = float((all_d < epsilon_star).mean())
    all_sorted = np.sort(all_d)
    edges_star = int(np.searchsorted(all_sorted, epsilon_star, side="right"))
    contig_star = int(np.searchsorted(cont_d, epsilon_star, side="right"))
    stability = bootstrap_epsilon_stability(
        all_d, args.replicas, args.pairs_per_replica, args.seed)

    grid = np.arange(args.p_min, args.p_max + args.p_step / 2, args.p_step)
    sweep = sweep_bridges(all_d, cont_d, grid)
    report = {
        "nodes": n_nodes,
        "null_pairs": int(all_d.size),
        "epsilon_star": epsilon_star,
        "kept_mass_fraction": kept_mass,
        "edges_at_epsilon_star": edges_star,
        "bridges_at_epsilon_star": edges_star - contig_star,
        "bootstrap_stability": {"replicas": args.replicas,
                                "pairs_per_replica":
                                    int(min(args.pairs_per_replica,
                                            all_d.size)),
                                "seed": args.seed,
                                **stability},
        "grid": {"p_min": args.p_min, "p_max": args.p_max,
                 "p_step": args.p_step},
        "sweep": sweep,
    }
    print(f"nodes={n_nodes} null_pairs={all_d.size}")
    print(f"epsilon*={epsilon_star:.4f} | kept mass={kept_mass * 100:.2f}% "
          f"| edges={edges_star} | non-contiguous bridges="
          f"{edges_star - contig_star}")
    print(f"bootstrap: mean={stability['mean']:.4f} "
          f"std={stability['std']:.4f} over {args.replicas} replicas "
          f"(seed={args.seed})")
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2))
        print(f"report written: {args.json_out}")


if __name__ == "__main__":
    main()
