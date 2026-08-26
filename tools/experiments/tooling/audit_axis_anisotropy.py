#!/usr/bin/env python
"""Q-axis anisotropy audit with empirical permutation null.

Dominance of an axis is never compared against a fixed quota: the observed
co-activation mass share of Q_1 is contrasted against a null distribution
built by permuting axis columns independently for each bridge endpoint
(preserves per-vector marginals, destroys cross-endpoint alignment).

Read-only audit: SQLite opened mode=ro, never mutates state (AGENTS 4.3).
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.analyze_bridges import find_bridges, load_current_nodes

DEFAULT_DB = Path(__file__).resolve().parents[3] / ".data" / "spinoza_full.db"
AXES = 8


def _matrix(projections_list):
    keys = [f"AXIS_{k + 1}" for k in range(AXES)]
    return np.array([[p[k] for k in keys] for p in projections_list],
                    dtype=np.float64)


def mass_shares(argmax, weights):
    """Co-activation mass share per axis from argmax assignment + weights."""
    totals = np.zeros(AXES, dtype=np.float64)
    np.add.at(totals, argmax, weights)
    total = totals.sum()
    if total <= 0:
        raise ValueError("no co-activation mass")
    return totals / total


def observed_statistic(q_a, q_b, weights):
    """Per-bridge argmax resonance axis and weighted mass shares."""
    products = np.abs(q_a * q_b)
    argmax = products.argmax(axis=1)
    return argmax, mass_shares(argmax, weights)


def permutation_pvalue(q_a, q_b, weights, replicas, seed):
    """Empirical p-value of Q_1 share under per-endpoint axis permutations."""
    argmax_obs, shares_obs = observed_statistic(q_a, q_b, weights)
    obs_share = float(shares_obs[0])
    rng = np.random.default_rng(seed)
    n = q_a.shape[0]
    exceed = 0
    for _ in range(replicas):
        pa = np.argsort(rng.random((n, AXES)), axis=1)
        pb = np.argsort(rng.random((n, AXES)), axis=1)
        products = np.abs(
            np.take_along_axis(q_a, pa, axis=1)
            * np.take_along_axis(q_b, pb, axis=1))
        shares = mass_shares(products.argmax(axis=1), weights)
        if shares[0] >= obs_share:
            exceed += 1
    return {
        "observed_share_q1": obs_share,
        "shares": shares_obs.tolist(),
        "argmax": argmax_obs.tolist(),
        "p_value": (1 + exceed) / (replicas + 1),
        "replicas": replicas,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Q-axis anisotropy with permutation-null significance.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB,
                        help=f"SQLite database path (default: {DEFAULT_DB})")
    parser.add_argument("--epsilon", type=float, required=True,
                        help="E_n threshold (pass the knee epsilon* reported "
                             "by epsilon_knee_audit)")
    parser.add_argument("--exclude", default="",
                        help="comma-separated node ids to drop before analysis")
    parser.add_argument("--replicas", type=int, default=1000,
                        help="permutation replicas for the empirical null")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--label", default="manifold")
    parser.add_argument("--json-out", type=Path, default=None,
                        help="optional path for the full JSON report")
    args = parser.parse_args()

    if not Path(args.db).exists():
        print(f"error: database not found: {args.db}")
        sys.exit(2)

    nodes = load_current_nodes(args.db)
    excluded = {t.strip() for t in args.exclude.split(",") if t.strip()}
    if excluded:
        nodes = [n for n in nodes if n["id"] not in excluded]
    bridges = find_bridges(nodes, args.epsilon)
    if not bridges:
        print(f"notice: no bridges at epsilon={args.epsilon}; "
              "nothing to audit.")
        return
    proj_by_id = {n["id"]: n["projections"] for n in nodes}
    q_a = _matrix([proj_by_id[b["source"]] for b in bridges])
    q_b = _matrix([proj_by_id[b["target"]] for b in bridges])
    weights = np.array([b["coactivation"] for b in bridges])
    result = permutation_pvalue(q_a, q_b, weights, args.replicas, args.seed)
    result.pop("argmax", None)
    result.update({
        "db": str(args.db),
        "epsilon": args.epsilon,
        "excluded_ids": sorted(excluded),
        "bridges": len(bridges),
        "label": args.label,
    })
    shares = result["shares"]
    top = int(np.argmax(shares))
    print(f"[{args.label}] bridges={len(bridges)} "
          f"epsilon={args.epsilon:.4f} excluded={len(excluded)}")
    print(f"dominant=AXIS_{top + 1} share={shares[top]:.4f} "
          f"Q1_share={shares[0]:.4f} p_value={result['p_value']:.4f} "
          f"({args.replicas} permutations)")
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(result, indent=2))
        print(f"report written: {args.json_out}")


if __name__ == "__main__":
    main()
