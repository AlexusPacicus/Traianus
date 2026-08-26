#!/usr/bin/env python
"""Axis x Part (8x5) independence battery on the Ethics manifold.

Four complementary units of analysis, no fixed analytic thresholds:
  all      - every vertex, dominant axis = argmax|q_k|; chi-square + seeded
             Monte-Carlo conditional p-value + bias-corrected Cramer's V.
  active   - vertices with sigma^2 >= theta_dyn (kinetic loads, dynamic).
  weighted - all vertices weighted by sigma^2 (asymptotic weighted chi2).
  edges    - epsilon bridges labeled by source-node part (dependent-sample
             reference; flagged inflated).
Sensitivity without stochasticity: deterministic leave-one-block-out
jackknife of Cramer's V over reading-order blocks.

Read-only audit: SQLite opened mode=ro, never mutates state (AGENTS 4.3).
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from tools.analyze_bridges import find_bridges, load_current_nodes
from tools.experiments.tooling._common import load_labels

DEFAULT_DB = Path(__file__).resolve().parents[3] / ".data" / "spinoza_full.db"
DEFAULT_LABELS = (Path(__file__).resolve().parents[3] / ".data"
                  / "spinoza_full_labels.json")
DEFAULT_TELEMETRY = (Path(__file__).resolve().parents[3] / ".data"
                     / "spinoza_full_telemetry.json")
AXES = 8
PARTS = ["P1_GOD", "P2_MIND", "P3_AFFECTS", "P4_BONDAGE", "P5_POWER"]
PART_BY_PREFIX = {"PART1": PARTS[0], "PART2": PARTS[1], "PART3": PARTS[2],
                  "PART4": PARTS[3], "PART5": PARTS[4]}
UNITS = ("all", "active", "weighted")


def part_of(label: str) -> str:
    return PART_BY_PREFIX[label[:5]]


def contingency_table(units):
    """Counts 8x5 from (axis_index, part_index) unit tuples."""
    table = np.zeros((AXES, len(PARTS)), dtype=np.float64)
    for axis, part in units:
        table[axis, part] += 1.0
    return table


def normalized_weights(weights):
    """Weights rescaled to mean 1: chi2 becomes invariant under uniform
    weight scaling and comparable with the unweighted table."""
    weights = np.asarray(weights, dtype=np.float64)
    if weights.size == 0 or float(weights.mean()) <= 0.0:
        raise ValueError("weights must be non-empty with positive mean")
    return weights / weights.mean()


def weighted_contingency_table(units, weights):
    """8x5 table accumulating mean-1-normalized weights per cell."""
    w = normalized_weights(weights)
    table = np.zeros((AXES, len(PARTS)), dtype=np.float64)
    np.add.at(table, (tuple(u[0] for u in units),
                      tuple(u[1] for u in units)), w)
    return table


def chi2_stat(table):
    """Pearson chi-square; valid for float (weighted) tables."""
    table = np.asarray(table, dtype=np.float64)
    n = table.sum()
    if n <= 0:
        raise ValueError("empty table")
    expected = np.outer(table.sum(axis=1), table.sum(axis=0)) / n
    mask = expected > 0
    return float(((table[mask] - expected[mask]) ** 2 / expected[mask]).sum())


def cramer_v_corrected(chi2, n, rows, cols):
    """Bias-corrected Cramer's V (Likert correction)."""
    if n <= 1:
        return 0.0
    phi2 = chi2 / n
    r = rows - (rows - 1) ** 2 / (n - 1)
    c = cols - (cols - 1) ** 2 / (n - 1)
    phi2_corr = max(0.0, phi2 - (rows - 1) * (cols - 1) / (n - 1))
    k = min(r, c)
    return float(np.sqrt(phi2_corr / max(k - 1, 1e-12))) if k > 1 else 0.0


def adjusted_residuals(table):
    """Adjusted standardized (Haberman) residuals per cell."""
    table = np.asarray(table, dtype=np.float64)
    n = table.sum()
    expected = np.outer(table.sum(axis=1), table.sum(axis=0)) / n
    with np.errstate(divide="ignore", invalid="ignore"):
        denom = np.sqrt(expected * (1 - table.sum(axis=1, keepdims=True) / n)
                        * (1 - table.sum(axis=0, keepdims=True) / n))
    return np.where(denom > 0, (table - expected) / denom, 0.0)


def monte_carlo_pvalue(units, replicas, seed):
    """Conditional MC p-value: permute part labels under fixed margins."""
    rng = np.random.default_rng(seed)
    axes = np.array([u[0] for u in units])
    parts = np.array([u[1] for u in units])
    observed = contingency_table(units)
    chi2_obs = chi2_stat(observed)
    exceed = 0
    for _ in range(replicas):
        shuffled = rng.permutation(parts)
        table = np.zeros((AXES, len(PARTS)))
        np.add.at(table, (axes, shuffled), 1.0)
        if chi2_stat(table) >= chi2_obs:
            exceed += 1
    v = cramer_v_corrected(chi2_obs, len(units), AXES, len(PARTS))
    return {
        "chi2": round(chi2_obs, 4),
        "dof": (AXES - 1) * (len(PARTS) - 1),
        "n_units": len(units),
        "cramers_v_corrected": round(v, 6),
        "p_value": (1 + exceed) / (replicas + 1),
        "replicas": replicas,
        "seed": seed,
    }


def holm_bonferroni(pvals):
    """Holm step-down adjustment preserving input order."""
    m = len(pvals)
    order = np.argsort(pvals)
    adjusted_sorted = np.empty(m)
    running = 0.0
    for rank, idx in enumerate(order):
        running = max(running, (m - rank) * pvals[idx])
        adjusted_sorted[rank] = min(running, 1.0)
    adjusted = np.empty(m)
    adjusted[order] = adjusted_sorted
    return [round(float(a), 6) for a in adjusted]


def jackknife_v(units, blocks):
    """Deterministic leave-one-block-out dispersion of Cramer's V.

    Blocks are contiguous chunks of the unit list (reading order); no
    stochastic component.
    """
    n = len(units)
    if blocks < 2 or n < blocks:
        raise ValueError("need at least 2 blocks and n >= blocks")
    scores = []
    fold = n // blocks
    for b in range(blocks):
        lo = b * fold
        hi = n if b == blocks - 1 else lo + fold
        subset = units[:lo] + units[hi:]
        if not subset:
            continue
        table = contingency_table(subset)
        scores.append(round(cramer_v_corrected(chi2_stat(table), len(subset),
                                               AXES, len(PARTS)), 6))
    return {"v_scores": scores,
            "mean": round(float(np.mean(scores)), 6),
            "std": round(float(np.std(scores)), 6)}


def _load_variance_map(telemetry_path):
    data = json.loads(Path(telemetry_path).read_text(encoding="utf-8"))
    variance = {r["node_id"]: r["variance"] for r in data["rows"]}
    return variance, data["theta_dyn"]


def _vertex_units(nodes, labels, unit_mode, telemetry_path):
    variance_by_id, theta_dyn = _load_variance_map(telemetry_path)
    keys = [f"AXIS_{k + 1}" for k in range(AXES)]
    units, weights = [], []
    for node in nodes:
        if node["id"] not in variance_by_id:
            continue
        q = node["projections"]
        axis = int(np.argmax([abs(q[k]) for k in keys]))
        part = PARTS.index(part_of(labels[node["id"]]))
        var = variance_by_id[node["id"]]
        if unit_mode == "active" and var < theta_dyn:
            continue
        units.append((axis, part))
        weights.append(var)
    if unit_mode == "weighted":
        return units, weights, theta_dyn
    return units, None, theta_dyn


def _weighted_chi2(nodes, labels, telemetry_path):
    variance_by_id, theta_dyn = _load_variance_map(telemetry_path)
    keys = [f"AXIS_{k + 1}" for k in range(AXES)]
    units, weights = [], []
    for node in nodes:
        if node["id"] not in variance_by_id:
            continue
        q = node["projections"]
        axis = int(np.argmax([abs(q[k]) for k in keys]))
        part = PARTS.index(part_of(labels[node["id"]]))
        units.append((axis, part))
        weights.append(variance_by_id[node["id"]])
    table = weighted_contingency_table(units, weights)
    chi2 = chi2_stat(table)
    effective_n = float(table.sum())
    residuals = adjusted_residuals(table)
    top_cells = np.dstack(np.unravel_index(
        np.argsort(np.abs(residuals), axis=None)[::-1], residuals.shape))[0][:5]
    driving = [{"axis": f"AXIS_{int(i) + 1}", "part": PARTS[int(j)],
                "residual": round(float(residuals[i, j]), 4)}
               for i, j in top_cells]
    return {
        "unit": "weighted",
        "chi2": round(chi2, 4),
        "effective_n": round(effective_n, 2),        "cramers_v_corrected": round(
            cramer_v_corrected(chi2, effective_n, AXES, len(PARTS)), 6),
        "driving_cells": driving,
        "note": "asymptotic weighted chi2; MC permutation undefined for "
                "float weights",
    }


def _edge_reference(nodes, labels, epsilon, replicas, seed):
    proj_by_id = {n["id"]: n["projections"] for n in nodes}
    bridges = find_bridges(nodes, epsilon)
    keys = [f"AXIS_{k + 1}" for k in range(AXES)]
    units = []
    for bridge in bridges:
        qa, qb = proj_by_id[bridge["source"]], proj_by_id[bridge["target"]]
        products = [abs(qa[k] * qb[k]) for k in keys]
        axis = int(np.argmax(products))
        part = PARTS.index(part_of(labels[bridge["source"]]))
        units.append((axis, part))
    result = monte_carlo_pvalue(units, replicas, seed)
    result.update({
        "unit": "edges",
        "epsilon": epsilon,
        "warning": "bridges share endpoints; N is dependent-inflated; "
                   "reference only",
    })
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Axis x Part independence battery (8x5 tables).")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB,
                        help=f"SQLite database path (default: {DEFAULT_DB})")
    parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS,
                        help=f"node labels JSON (default: {DEFAULT_LABELS})")
    parser.add_argument("--telemetry", type=Path, default=DEFAULT_TELEMETRY,
                        help=f"telemetry JSON with variance/theta_dyn "
                             f"(default: {DEFAULT_TELEMETRY})")
    parser.add_argument("--unit", choices=UNITS, default="all")
    parser.add_argument("--replicas", type=int, default=1000,
                        help="Monte-Carlo conditional replicas")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--blocks", type=int, default=10,
                        help="jackknife blocks over reading order")
    parser.add_argument("--edges-epsilon", type=float, nargs="*", default=[],
                        help="extra edge-level reference runs at these "
                             "epsilon values")
    parser.add_argument("--json-out", type=Path, default=None,
                        help="optional path for the full JSON report")
    args = parser.parse_args()

    for path in (args.db, args.labels, args.telemetry):
        if not Path(path).exists():
            print(f"error: file not found: {path}")
            sys.exit(2)

    labels = load_labels(args.labels)
    nodes = load_current_nodes(args.db)

    report = {}
    if args.unit == "weighted":
        report["weighted"] = _weighted_chi2(nodes, labels, args.telemetry)
    else:
        units, _, theta_dyn = _vertex_units(nodes, labels, args.unit,
                                            args.telemetry)
        if not units:
            print(f"notice: no units after filtering ({args.unit}); "
                  "nothing to test.")
            return
        result = monte_carlo_pvalue(units, args.replicas, args.seed)
        result["unit"] = args.unit
        result["theta_dyn"] = theta_dyn
        result["jackknife_v"] = jackknife_v(units, args.blocks)
        table = contingency_table(units)
        residuals = adjusted_residuals(table)
        flat_idx = np.dstack(np.unravel_index(
            np.argsort(np.abs(residuals), axis=None)[::-1],
            residuals.shape))[0][:5]
        result["driving_cells"] = [
            {"axis": f"AXIS_{int(i) + 1}", "part": PARTS[int(j)],
             "residual": round(float(residuals[i, j]), 4)}
            for i, j in flat_idx]
        posthoc = []
        for j, part in enumerate(PARTS):
            sub = [(a, p) for a, p in units if p == j]
            rest = [(a, p) for a, p in units if p != j]
            pooled = sub + rest
            one_vs_rest = monte_carlo_pvalue(
                [(a, 0 if p == j else 1) for a, p in pooled],
                args.replicas, args.seed)
            posthoc.append({"part": part, "n": len(sub),
                            "chi2": one_vs_rest["chi2"],
                            "p_value_raw": one_vs_rest["p_value"]})
        posthoc_p = [p["p_value_raw"] for p in posthoc]
        adjusted = holm_bonferroni(posthoc_p)
        for entry, adj in zip(posthoc, adjusted):
            entry["p_value_holm"] = adj
        result["posthoc_part_vs_rest"] = posthoc
        report[args.unit] = result

    for epsilon in args.edges_epsilon:
        report[f"edges_eps_{epsilon:g}"] = _edge_reference(
            nodes, labels, epsilon, args.replicas, args.seed)

    print(json.dumps({k: {kk: vv for kk, vv in v.items()
                          if kk != "jackknife_v"}
                      for k, v in report.items()}, indent=2))
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2))
        print(f"report written: {args.json_out}")


if __name__ == "__main__":
    main()
