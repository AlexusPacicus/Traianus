"""TG shortcut check -- does low tension beat a pure graph-shortcut order on J?

A labelled exploration (docs/methodology/METHODOLOGY.md, Explore), not an instrument audit record and not a
registry entry. One question: among the relations a variant already has between two notes of different
labels (J), does keeping the low-effort half (tension_gate_precheck's low arm) bring the B notes' neighbours
closer than keeping the pure graph-shortcut half, the relations whose ends are farthest apart by the rest of
the variant, an order that looks at neither tension, distance nor text? Three arms keep the same number of
the same relations: low effort, shortcut, random. Same notes and split as the pre-check: the FIT notes split
in two halves, A (corpus rows 0 mod 4) judges, B (2 mod 4) is the ground truth; EVAL rows (odd) are dropped
before any computation. The decision rule, RULE, is fixed in this file before any result exists.

Imports tension_gate_precheck as a module and reuses its functions; refuses to run unless the three modules
pinned by tension_gate, tension_gate.py, tension_gate_precheck.py and the three input digests match, and
resolve_epsilon_edge() returns 0.8. Never runs on anything else.

Usage:
    python3 tools/experiments/tension_gate_shortcut.py [--out PATH]
"""

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_var] = "1"

import argparse
import hashlib
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.experiments import k6_colour_predictability as k6
from tools.experiments import relational_graph_exploration as rge
from tools.experiments import tension_gate as tg
from tools.experiments import tension_gate_precheck as pc

Pair = pc.Pair

TG_FILE = pc.TG_FILE
PC_FILE = Path(pc.__file__)
PC_SHA256 = "2ae4c7c5fb06c9afab7c8e983c1b9889096de774c54b6b29f1442034a02a8a75"
K6_FILE = tg.K6_FILE
RGE_FILE = tg.RGE_FILE
OBSERVABLES_FILE = tg.OBSERVABLES_FILE
EMBEDDINGS = tg.EMBEDDINGS
LABELS = tg.LABELS
AXES = tg.AXES
EXPECTED_DIGESTS = tg.EXPECTED_DIGESTS
RESULT = REPO_ROOT / "data" / "refapp" / "TG_shortcut_result.json"

VARIANTS = pc.VARIANTS
ARMS = ("low", "shortcut", "random")
STATISTIC_ARMS = {
    "low_over_shortcut": ("low", "shortcut"),
    "shortcut_over_random": ("shortcut", "random"),
    "low_over_random": ("low", "random"),
}
STATISTICS = tuple(STATISTIC_ARMS)
STATEMENT = "labelled exploration, not a registry entry"
RULE = (
    "J per variant, the pair table, the A/B split, the low arm (effort rank, ties by smaller share, then "
    "(i, j)), the random arm, the turn sums, the block bootstrap and the verdicts are those of "
    "tension_gate_precheck. Each arm keeps k = floor(|J| / 2) relations of J and every other relation of the "
    "variant stays. The shortcut arm keeps the k relations of J with the largest h, ties by (i, j), where "
    "h(i, j) is the number of breadth-first turns between i and j in the variant without any relation of J "
    "(the minimum spanning tree intact); it uses no tension, no distance, no label and no text. Statistics "
    "in order: low_over_shortcut, shortcut_over_random, low_over_random, each D_X_over_Y(q) = S_Y(q) - "
    "S_X(q) over the B notes. Invalid, with a null decision, if a graph is disconnected, the three arms' "
    "edge counts differ, the ceiling control fails or |J| < 2 in a variant. Decision: tension_informative "
    "iff low_over_shortcut is above in both variants, otherwise archive. shortcut_over_random and "
    "low_over_random are reported and never decide."
)


# Pins ---------------------------------------------------------------------------------------------------


def check_precheck(pc_file: Path) -> None:
    """tension_gate_precheck.py's own sha256, by hashlib on the file on disk."""
    actual = hashlib.sha256(Path(pc_file).read_bytes()).hexdigest()
    if actual != PC_SHA256:
        raise k6.IntegrityError(f"sha256 mismatch for {pc_file}: expected {PC_SHA256}, got {actual}")


# The shortcut arm -----------------------------------------------------------------------------------------


def shortcut_turns(n: int, variant_pairs: set[Pair], j_pairs: set[Pair]) -> dict[Pair, int]:
    """h(i, j): breadth-first turns between the ends in the variant without any relation of J."""
    base = tg.build_graph(n, variant_pairs, j_pairs, set())
    from_end: dict[int, Any] = {}
    turns: dict[Pair, int] = {}
    for i, j in sorted(j_pairs):
        if i not in from_end:
            from_end[i] = tg.bfs(base, i)
        turns[(i, j)] = int(from_end[i][j])
    return turns


def select_shortcut(turns: Mapping[Pair, int], k: int) -> set[Pair]:
    return set(sorted(turns, key=lambda p: (-turns[p], p))[:k])


# Decision ---------------------------------------------------------------------------------------------------


def decide(valid: bool, verdicts: Mapping[str, Mapping[str, str]]) -> str | None:
    if not valid:
        return None
    if all(verdicts[name]["low_over_shortcut"] == "above" for name in VARIANTS):
        return "tension_informative"
    return "archive"


def _mean(values: Sequence[float]) -> float | None:
    return float(sum(values)) / len(values) if values else None


# Measurement ------------------------------------------------------------------------------------------------


def measure(
    v: pc.Array, a: pc.Array, label_items: Sequence[Mapping[str, str]], epsilon: float,
    _on_draw: Callable[[str, str, int], None] | None = None,
) -> dict[str, Any]:
    fit, a_notes, b_notes = pc.split_notes(len(v))
    n_fit = len(fit)
    position = {corpus: local for local, corpus in enumerate(fit)}
    a_local = [position[i] for i in a_notes]
    b_local = [position[i] for i in b_notes]
    v_fit = v[fit]
    d = rge.pairwise_distances(v_fit)
    lab = rge.axis_cells(v_fit, a)
    c = tg.axis_coordinates(v_fit, a)
    variants = tg.build_variants(v_fit, d, [label_items[i] for i in fit], lab, epsilon)
    a_set = set(a_local)
    j_by_variant = {
        name: pc.judged_pairs(variants[name], variants["m_pairs"], a_set, lab) for name in VARIANTS
    }
    nearest = tg.real_neighbours(d, a_local, a_local, tg.K_NEIGH + 1)
    r_b = pc.evaluation_neighbours(d, b_local)

    rng = np.random.Generator(np.random.PCG64(tg.SEED))
    u_blind = pc.blind_directions(rng)
    info: dict[Pair, dict[str, Any]] = {}
    for i, j in sorted(set().union(*j_by_variant.values())):
        n_i, n_j = pc.neighbourhoods(nearest, i, j)
        rank, share = pc.pair_effort(c, i, j, n_i, n_j, u_blind)
        info[(i, j)] = {"rank": rank, "share": share, "distance": float(d[i, j])}

    j_sorted_by_variant = {name: sorted(j_by_variant[name]) for name in VARIANTS}
    turns_by_variant = {
        name: shortcut_turns(n_fit, variants[name], j_by_variant[name]) for name in VARIANTS
    }
    arms_by_variant: dict[str, dict[str, set[Pair]]] = {}
    for name in VARIANTS:
        j_sorted = j_sorted_by_variant[name]
        k = pc.arm_size(len(j_sorted))
        arms = {
            "low": pc.select_arm("low", {p: info[p] for p in j_sorted}, k),
            "shortcut": select_shortcut(turns_by_variant[name], k),
        }
        arms["random"] = pc.random_arm(rng, j_sorted, k)
        arms_by_variant[name] = arms

    graphs_by_variant = {
        name: pc.build_arm_graphs(n_fit, variants[name], j_by_variant[name], arms_by_variant[name])
        for name in VARIANTS
    }
    edge_counts = {
        name: {graph: tg.count_edges(adj) for graph, adj in graphs_by_variant[name].items()}
        for name in VARIANTS
    }
    connected = {
        name: {graph: tg.is_connected(adj) for graph, adj in graphs_by_variant[name].items()}
        for name in VARIANTS
    }
    equal_edges = {name: len({edge_counts[name][arm] for arm in ARMS}) == 1 for name in VARIANTS}
    ceiling_ok = tg.ceiling_control(b_local, r_b, n_fit)
    sums = {
        name: {arm: pc.turn_sums(graphs_by_variant[name][arm], b_local, r_b) for arm in ARMS}
        for name in VARIANTS
    }

    failed_conditions = [
        condition for condition, ok in (
            ("connectivity", all(all(per.values()) for per in connected.values())),
            ("equal_budget", all(equal_edges.values())),
            ("ceiling", ceiling_ok),
            ("j_size", all(len(j) >= 2 for j in j_by_variant.values())),
        ) if not ok
    ]
    valid = not failed_conditions

    lengths = pc.valid_lengths(len(b_local))
    variants_out: dict[str, Any] = {}
    verdicts: dict[str, dict[str, str]] = {}
    for name in VARIANTS:
        statistics: dict[str, Any] = {}
        for statistic, (arm_x, arm_y) in STATISTIC_ARMS.items():
            values = pc.differences(sums[name][arm_x], sums[name][arm_y], b_local)
            per_l: dict[str, Any] = {}
            for length in tg.GRID:
                n_blocks = tg.n_blocks_for(len(b_local), length)
                if length in lengths:
                    if _on_draw is not None:
                        _on_draw(name, statistic, length)
                    record = tg.interval_record(tg.bootstrap_means(rng, values, length))
                    per_l[str(length)] = {"valid": True, "n_blocks": n_blocks, **record}
                else:
                    per_l[str(length)] = {
                        "valid": False, "n_blocks": n_blocks, "interval": None, "ranks": None,
                    }
            statistics[statistic] = {
                "mean": float(values.mean()), "per_l": per_l, "verdict": pc.verdict(list(per_l.values())),
            }
        verdicts[name] = {statistic: statistics[statistic]["verdict"] for statistic in STATISTICS}

        kept = arms_by_variant[name]
        j_sorted = j_sorted_by_variant[name]
        turns = turns_by_variant[name]
        variants_out[name] = {
            "j_count": len(j_sorted),
            "k": pc.arm_size(len(j_sorted)),
            "g0": {
                "relations": edge_counts[name]["g0"], "beta": 2 * edge_counts[name]["g0"] / n_fit,
            },
            "arms": {
                arm: {
                    "relations": edge_counts[name][arm],
                    "beta": 2 * edge_counts[name][arm] / n_fit,
                    "kept": sorted([fit[i], fit[j]] for i, j in kept[arm]),
                }
                for arm in ARMS
            },
            "overlaps": {
                "low_shortcut": len(kept["low"] & kept["shortcut"]),
                "low_random": len(kept["low"] & kept["random"]),
                "shortcut_random": len(kept["shortcut"] & kept["random"]),
            },
            "mean_h": {
                "j": _mean([turns[p] for p in j_sorted]),
                **{arm: _mean([turns[p] for p in sorted(kept[arm])]) for arm in ARMS},
            },
            "pairs_sharing_h": pc.shared_rank_count([turns[p] for p in j_sorted]),
            "connected": connected[name],
            "equal_edges": equal_edges[name],
            "pairs": [
                {
                    "i": fit[i], "j": fit[j], "rank": info[(i, j)]["rank"],
                    "share": info[(i, j)]["share"], "distance": info[(i, j)]["distance"],
                    "h": turns[(i, j)],
                }
                for i, j in j_sorted
            ],
            "statistics": statistics,
        }

    return {
        "statement": STATEMENT,
        "rule": RULE,
        "valid": valid,
        "failed_conditions": failed_conditions,
        "decision": decide(valid, verdicts),
        "a_count": len(a_notes),
        "b_count": len(b_notes),
        "variants": variants_out,
    }


# Run and command line ---------------------------------------------------------------------------------------------


def run(
    k6_file: Path, rge_file: Path, observables_file: Path, tg_file: Path, pc_file: Path,
    embeddings: Path, labels: Path, axes: Path,
    expected: Mapping[Path, str], out_path: Path,
) -> dict[str, Any]:
    """Pin checks, then epsilon, then the artefacts, as tension_gate_precheck.run orders them."""
    tg.check_pins(Path(k6_file), Path(rge_file), Path(observables_file))
    pc.check_tension_gate(Path(tg_file))
    check_precheck(Path(pc_file))
    epsilon = tg.resolve_epsilon_edge()
    tg.check_epsilon(epsilon)
    raw = k6.check_digests(expected)
    v32, label_list, axis_ids, a = k6.load_inputs(
        raw[Path(embeddings)], raw[Path(labels)], raw[Path(axes)]
    )
    k6.validate_inputs(v32, label_list, axis_ids, a)
    v64 = v32.astype("<f8")
    v = np.array([row / np.sqrt(row @ row) for row in v64])
    result = measure(v, a, label_list, epsilon)
    result["digests"] = {
        Path(k6_file).name: tg.K6_SHA256,
        Path(rge_file).name: tg.RGE_SHA256,
        Path(observables_file).name: tg.OBSERVABLES_SHA256,
        Path(tg_file).name: pc.TG_SHA256,
        Path(pc_file).name: PC_SHA256,
        **{Path(p).name: digest for p, digest in expected.items()},
    }
    result["environment"] = tg.environment(epsilon)
    return tg._write(result, out_path)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="TG shortcut check: tension order against shortcut order.")
    parser.add_argument("--out", type=Path, default=RESULT, help=f"result path (default: {RESULT})")
    out_path: Path = parser.parse_args(argv).out
    result = run(
        K6_FILE, RGE_FILE, OBSERVABLES_FILE, TG_FILE, PC_FILE, EMBEDDINGS, LABELS, AXES,
        EXPECTED_DIGESTS, out_path,
    )
    print(f"TG shortcut: valid={result['valid']} decision={result['decision']} -> {out_path}")
    if not result["valid"]:
        raise SystemExit(f"TG shortcut invalid: {result['failed_conditions']}")


if __name__ == "__main__":
    main()
