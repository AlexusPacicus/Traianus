"""TG pre-check -- does the tension of a relation order cross-label relations better than distance?

A labelled exploration (docs/methodology/METHODOLOGY.md, Explore), not an instrument audit record and not a
registry entry. One question: among the relations a variant already has between two notes of different
labels (J), does the tension of each end's own neighbourhood, taken along the bridge and ranked against the
1,000 blind directions of tools/experiments/tension_gate.py, order them better than their 384-D distance,
at the same budget, with no cut and no veto? Four arms keep the same number of the same relations: lowest
effort, highest effort, shortest distance, random. The FIT notes split in two halves: A (corpus rows 0 mod 4)
judges, B (2 mod 4) is the ground truth. EVAL rows (odd) are dropped before any computation. The decision
rule, RULE, is fixed in this file before any result exists.

Imports tension_gate as a module and reuses its functions; refuses to run unless the three modules pinned
by tension_gate, tension_gate.py itself and the three input digests match, and resolve_epsilon_edge()
returns 0.8. Never runs on anything else.

Usage:
    python3 tools/experiments/tension_gate_precheck.py [--out PATH]
"""

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_var] = "1"

import argparse
import hashlib
import sys
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.experiments import k6_colour_predictability as k6
from tools.experiments import relational_graph_exploration as rge
from tools.experiments import tension_gate as tg

Array = NDArray[np.float64]
Pair = tuple[int, int]
Adjacency = list[set[int]]

TG_FILE = Path(tg.__file__)
TG_SHA256 = "4c195d483e926590007625c258a2352bd3a6639ba6bd857434bc04286db887e5"
K6_FILE = tg.K6_FILE
RGE_FILE = tg.RGE_FILE
OBSERVABLES_FILE = tg.OBSERVABLES_FILE
EMBEDDINGS = tg.EMBEDDINGS
LABELS = tg.LABELS
AXES = tg.AXES
EXPECTED_DIGESTS = tg.EXPECTED_DIGESTS
RESULT = REPO_ROOT / "data" / "refapp" / "TG_precheck_result.json"

VARIANTS = ("union", "open_borders")
ARMS = ("low", "high", "distance", "random")
STATISTIC_ARMS = {
    "low_over_distance": ("low", "distance"),
    "high_over_distance": ("high", "distance"),
    "distance_over_random": ("distance", "random"),
    "low_over_random": ("low", "random"),
    "high_over_random": ("high", "random"),
}
STATISTICS = tuple(STATISTIC_ARMS)
STATEMENT = "labelled exploration, not a registry entry"
RULE = (
    "J per variant: the relations (i, j) the variant has, both ends in A, of different labels, not in the "
    "minimum spanning tree of the FIT sub-corpus. Each arm keeps k = floor(|J| / 2) relations of J and "
    "every other relation of the variant stays. Effort of a pair: each end's 15 nearest A notes (both "
    "ends excluded), tension matrices of the two neighbourhoods around their own barycentres, summed; "
    "rank r = number of the 1,000 blind directions of tension_gate strictly below the tension along the "
    "bridge, share = that tension over the trace. low keeps the smallest r (ties: smaller share, then "
    "(i, j)); high the largest r (ties: larger share, then (i, j)); distance the shortest 384-D distance "
    "(ties: (i, j)); random a draw without replacement. For every B note q, S_arm(q) is the sum of the "
    "breadth-first turns from q to its 15 nearest B notes in the arm's graph, and D_X_over_Y(q) = "
    "S_Y(q) - S_X(q). Block bootstrap of the mean over B, 10,000 resamples, interval between ranks 249 "
    "and 9749, for every block length of 1, 2, 5, 10, 20, 50 with at least 20 blocks. Verdict of a "
    "statistic in a variant: above iff the interval's lower bound is above 0 at every valid length, "
    "below iff its upper bound is below 0 at every valid length, pending if no length is valid, "
    "otherwise inconclusive. Invalid, with a null decision, if a graph is disconnected, the four arms' "
    "edge counts differ, the ceiling control fails or |J| < 2 in a variant. Decision: no_resolution "
    "unless distance_over_random is above in both variants; otherwise a sense (low, high) beats "
    "distance iff its statistic over distance is above in both variants: only high gives sign_high, "
    "only low sign_low, neither archive, both sign_unresolved. low_over_random and high_over_random "
    "are reported and never decide."
)


# Pins ---------------------------------------------------------------------------------------------------


def check_tension_gate(tg_file: Path) -> None:
    """tension_gate.py's own sha256, by hashlib on the file on disk."""
    actual = hashlib.sha256(Path(tg_file).read_bytes()).hexdigest()
    if actual != TG_SHA256:
        raise k6.IntegrityError(f"sha256 mismatch for {tg_file}: expected {TG_SHA256}, got {actual}")


# Notes and J ----------------------------------------------------------------------------------------------


def split_notes(n: int) -> tuple[list[int], list[int], list[int]]:
    """FIT (even corpus rows), A (0 mod 4, judges) and B (2 mod 4, ground truth), as corpus indices."""
    fit = [int(i) for i in k6.split_fit_eval(n)[0]]
    return fit, [i for i in fit if i % 4 == 0], [i for i in fit if i % 4 == 2]


def judged_pairs(
    variant_pairs: set[Pair], m_pairs: set[Pair], a_set: set[int], lab: NDArray[np.intp],
) -> set[Pair]:
    return {
        (i, j) for i, j in variant_pairs
        if i in a_set and j in a_set and lab[i] != lab[j] and (i, j) not in m_pairs
    }


def build_arm_graphs(
    n: int, base: set[Pair], j_pairs: set[Pair], arms: Mapping[str, set[Pair]],
) -> dict[str, Adjacency]:
    """G0 (the variant as it is) and, per arm, (variant minus J) plus the arm's kept relations."""
    graphs = {"g0": tg.build_graph(n, base, set(), set())}
    for name, kept in arms.items():
        graphs[name] = tg.build_graph(n, base, j_pairs, kept)
    return graphs


# Effort (each end's own neighbourhood, D29) -------------------------------------------------------------


def neighbourhoods(
    nearest: Mapping[int, list[int]], i: int, j: int,
) -> tuple[list[int], list[int]]:
    """The 15 A notes nearest each end, both ends excluded, from the 16 nearest of each."""
    return (
        [t for t in nearest[i] if t != j][: tg.K_NEIGH],
        [t for t in nearest[j] if t != i][: tg.K_NEIGH],
    )


def neighbourhood_tension(c: Array, n_i: Sequence[int], n_j: Sequence[int]) -> Array:
    """T(N_i) + T(N_j), each around its own barycentre; a note in both counts in both."""
    return tg.tension_matrix(c[list(n_i)])[1] + tg.tension_matrix(c[list(n_j)])[1]


def blind_directions(rng: np.random.Generator) -> Array:
    g = rng.standard_normal((tg.N_BLIND, tg.N_AXES))
    return g / np.linalg.norm(g, axis=1, keepdims=True)


def rank_and_share(w: Array, b: Array, u_blind: Array) -> tuple[int, float]:
    """Blind directions strictly below the tension along b, and that tension over the trace of w."""
    e = tg.effort(w, b)
    blind = np.array([tg.effort(w, u) for u in u_blind])
    return int(np.count_nonzero(blind < e)), e / float(np.trace(w))


def pair_effort(
    c: Array, i: int, j: int, n_i: Sequence[int], n_j: Sequence[int], u_blind: Array,
) -> tuple[int, float]:
    b = c[j] - c[i]
    return rank_and_share(neighbourhood_tension(c, n_i, n_j), b / np.linalg.norm(b), u_blind)


# Arms -----------------------------------------------------------------------------------------------------


def arm_size(j_count: int) -> int:
    return j_count // 2


def select_arm(arm: str, info: Mapping[Pair, Mapping[str, Any]], k: int) -> set[Pair]:
    if arm == "low":
        ordered = sorted(info, key=lambda p: (info[p]["rank"], info[p]["share"], p))
    elif arm == "high":
        ordered = sorted(info, key=lambda p: (-info[p]["rank"], -info[p]["share"], p))
    else:
        ordered = sorted(info, key=lambda p: (info[p]["distance"], p))
    return set(ordered[:k])


def random_arm(rng: np.random.Generator, j_sorted: Sequence[Pair], k: int) -> set[Pair]:
    return {j_sorted[int(idx)] for idx in rng.choice(len(j_sorted), k, replace=False)}


def shared_rank_count(ranks: Sequence[int]) -> int:
    return sum(count for count in Counter(ranks).values() if count > 1)


# Turns and differences (D28) --------------------------------------------------------------------------------


def evaluation_neighbours(d: Array, b_notes: Sequence[int]) -> dict[int, list[int]]:
    """R(q): the 15 B notes nearest q, q excluded, ties to the lower index."""
    return tg.real_neighbours(d, b_notes, b_notes)


def turn_sums(adj: Adjacency, b_notes: Sequence[int], r: Mapping[int, list[int]]) -> dict[int, int]:
    sums: dict[int, int] = {}
    for q in b_notes:
        dist = tg.bfs(adj, q)
        sums[q] = int(sum(int(dist[t]) for t in r[q]))
    return sums


def differences(s_x: Mapping[int, int], s_y: Mapping[int, int], b_notes: Sequence[int]) -> Array:
    """D_X_over_Y(q) = S_Y(q) - S_X(q): positive when X brings q's neighbours closer."""
    return np.array([s_y[q] - s_x[q] for q in b_notes], dtype=np.float64)


# Interval, verdict and decision -------------------------------------------------------------------------------


def valid_lengths(n: int) -> list[int]:
    return [length for length in tg.GRID if tg.n_blocks_for(n, length) >= tg.MIN_BLOCKS]


def verdict(records: Sequence[Mapping[str, Any]]) -> str:
    intervals = [record["interval"] for record in records if record["valid"]]
    if not intervals:
        return "pending"
    if all(lower > 0.0 for lower, _ in intervals):
        return "above"
    if all(upper < 0.0 for _, upper in intervals):
        return "below"
    return "inconclusive"


def decide(valid: bool, verdicts: Mapping[str, Mapping[str, str]]) -> str | None:
    if not valid:
        return None
    if any(verdicts[name]["distance_over_random"] != "above" for name in VARIANTS):
        return "no_resolution"
    beats = {
        sense: all(verdicts[name][f"{sense}_over_distance"] == "above" for name in VARIANTS)
        for sense in ("low", "high")
    }
    if beats["low"] and beats["high"]:
        return "sign_unresolved"
    if beats["high"]:
        return "sign_high"
    if beats["low"]:
        return "sign_low"
    return "archive"


# Measurement ------------------------------------------------------------------------------------------------------


def measure(
    v: Array, a: Array, label_items: Sequence[Mapping[str, str]], epsilon: float,
    _on_draw: Callable[[str, str, int], None] | None = None,
) -> dict[str, Any]:
    fit, a_notes, b_notes = split_notes(len(v))
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
        name: judged_pairs(variants[name], variants["m_pairs"], a_set, lab) for name in VARIANTS
    }
    nearest = tg.real_neighbours(d, a_local, a_local, tg.K_NEIGH + 1)
    r_b = evaluation_neighbours(d, b_local)

    rng = np.random.Generator(np.random.PCG64(tg.SEED))
    u_blind = blind_directions(rng)
    info: dict[Pair, dict[str, Any]] = {}
    for i, j in sorted(set().union(*j_by_variant.values())):
        n_i, n_j = neighbourhoods(nearest, i, j)
        rank, share = pair_effort(c, i, j, n_i, n_j, u_blind)
        info[(i, j)] = {"rank": rank, "share": share, "distance": float(d[i, j])}

    j_sorted_by_variant = {name: sorted(j_by_variant[name]) for name in VARIANTS}
    arms_by_variant: dict[str, dict[str, set[Pair]]] = {}
    for name in VARIANTS:
        j_sorted = j_sorted_by_variant[name]
        k = arm_size(len(j_sorted))
        j_info = {p: info[p] for p in j_sorted}
        arms = {arm: select_arm(arm, j_info, k) for arm in ("low", "high", "distance")}
        arms["random"] = random_arm(rng, j_sorted, k)
        arms_by_variant[name] = arms

    graphs_by_variant = {
        name: build_arm_graphs(n_fit, variants[name], j_by_variant[name], arms_by_variant[name])
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
        name: {arm: turn_sums(graphs_by_variant[name][arm], b_local, r_b) for arm in ARMS}
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

    lengths = valid_lengths(len(b_local))
    variants_out: dict[str, Any] = {}
    verdicts: dict[str, dict[str, str]] = {}
    for name in VARIANTS:
        statistics: dict[str, Any] = {}
        for statistic, (arm_x, arm_y) in STATISTIC_ARMS.items():
            values = differences(sums[name][arm_x], sums[name][arm_y], b_local)
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
                "mean": float(values.mean()), "per_l": per_l, "verdict": verdict(list(per_l.values())),
            }
        verdicts[name] = {statistic: statistics[statistic]["verdict"] for statistic in STATISTICS}

        kept = {arm: arms_by_variant[name][arm] for arm in ARMS}
        j_sorted = j_sorted_by_variant[name]
        variants_out[name] = {
            "j_count": len(j_sorted),
            "k": arm_size(len(j_sorted)),
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
                "low_distance": len(kept["low"] & kept["distance"]),
                "high_distance": len(kept["high"] & kept["distance"]),
                "low_high": len(kept["low"] & kept["high"]),
                "random_distance": len(kept["random"] & kept["distance"]),
            },
            "pairs_sharing_rank": shared_rank_count([info[p]["rank"] for p in j_sorted]),
            "connected": connected[name],
            "equal_edges": equal_edges[name],
            "pairs": [
                {
                    "i": fit[i], "j": fit[j], "rank": info[(i, j)]["rank"],
                    "share": info[(i, j)]["share"], "distance": info[(i, j)]["distance"],
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
    k6_file: Path, rge_file: Path, observables_file: Path, tg_file: Path,
    embeddings: Path, labels: Path, axes: Path,
    expected: Mapping[Path, str], out_path: Path,
) -> dict[str, Any]:
    """Pin checks, then epsilon, then the artefacts, as tension_gate.run orders them."""
    tg.check_pins(Path(k6_file), Path(rge_file), Path(observables_file))
    check_tension_gate(Path(tg_file))
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
        Path(tg_file).name: TG_SHA256,
        **{Path(p).name: digest for p, digest in expected.items()},
    }
    result["environment"] = tg.environment(epsilon)
    return tg._write(result, out_path)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="TG pre-check: tension order against distance order.")
    parser.add_argument("--out", type=Path, default=RESULT, help=f"result path (default: {RESULT})")
    out_path: Path = parser.parse_args(argv).out
    result = run(
        K6_FILE, RGE_FILE, OBSERVABLES_FILE, TG_FILE, EMBEDDINGS, LABELS, AXES, EXPECTED_DIGESTS, out_path,
    )
    print(f"TG pre-check: valid={result['valid']} decision={result['decision']} -> {out_path}")
    if not result["valid"]:
        raise SystemExit(f"TG pre-check invalid: {result['failed_conditions']}")


if __name__ == "__main__":
    main()
