"""TG — tension gate on cross-label relations.

Implements docs/methodology/instrument-audit/TG.md (instrument audit record, revision 3) against
docs/methodology/instrument-audit/contracts.md (section 0 data layer, section 5 TG) and
docs/methodology/instrument-audit/derivations.md (D27, D28, D29).

For every pair of frozen-corpus (FIT) notes with different labels, measures the tension of their
joint neighbourhood, without the two ends, along the notes' own direction, against 1,000 blind
directions; a pair passes the cut iff its own tension is strictly below the 12th smallest blind
one, and is vetoed if a tunnel between the notes crosses a foreign note that kept its neighbours
apart from the bridge. What the gate keeps is compared, for the union and the open-borders
variant, against the variant with no gate and against a blind draw of the same size, by how many
turns separate an EVAL note from its real neighbours.

Refuses to run unless the three pinned modules match their sha256, resolve_epsilon_edge() returns
0.8, and the three input digests match; never runs on anything else.

Usage:
    python3 tools/experiments/tension_gate.py [--out PATH]
"""

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_var] = "1"

import argparse
import hashlib
import json
import math
import platform
import sys
from collections import deque
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, cast

import numpy as np
from numpy.typing import NDArray

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.experiments import k6_colour_predictability as k6
from tools.experiments import relational_graph_exploration as rge
from traianus.config import resolve_epsilon_edge
from traianus.geometry import observables as observables_module

Array = NDArray[np.float64]
Edge = tuple[int, int, float]
Pair = tuple[int, int]

EMBEDDINGS = REPO_ROOT / ".data" / "spinoza_frozen" / "embeddings.npy"
LABELS = REPO_ROOT / ".data" / "spinoza_frozen" / "labels.json"
AXES = REPO_ROOT / "tests" / "fixtures" / "nsm_axes_8.json"
RESULT = REPO_ROOT / "data" / "refapp" / "TG_result.json"
EXPECTED_DIGESTS = {
    EMBEDDINGS: "eafb0e97172830f2404e96fa08d74bf6cccc0b6cbe84d47b790a476603e7d8d1",
    LABELS: "1d60699353d810f089730c6203ee28f9c416e3004b60781bc965cec284097f4f",
    AXES: "b14e5d6700d1a7478a357ca26f0f38f5240f97a42daad45722d21f1c3f964e35",
}

K6_FILE = Path(k6.__file__)
K6_SHA256 = "6289c596792154f6bb799606265c68719c6b8c7ae8b69084116dfb23c77876d2"
RGE_FILE = Path(rge.__file__)
RGE_SHA256 = "627aa8e95a844b0aec290a41c48b9a0bf6890db25b5240b5730c366a56d2e7dc"
OBSERVABLES_FILE = Path(observables_module.__file__)
OBSERVABLES_SHA256 = "54385042f771fc6b2a383e52e312287b2b82030f378212f7e06bd19f16f94c0f"

SEED = 20260918
N_AXES = 8
K_NEIGH = 15
N_BLIND = 1000
CUT_INDEX = 11
N_BOOT = 10_000
GRID = (1, 2, 5, 10, 20, 50)
MIN_BLOCKS = 20
INTERVAL_RANKS = (249, 9749)
MC_RANKS = (233, 265, 9733, 9765)
MC_Z = 4.0
EPSILON = 0.8
BETA_DENOMINATOR = 2221.0  # TG.md: beta = 2|E| / 2221, the frozen corpus's row count, fixed
THREAD_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")
VARIANTS = ("union", "open_borders")
CONTROL_IDENTIFIERS = ("exchangeable_direction", "ceiling", "connectivity", "equal_budget")


# Pins, epsilon and environment -----------------------------------------------------------------


def check_pins(k6_file: Path, rge_file: Path, observables_file: Path) -> None:
    """Each pinned module file's sha256 by hashlib, not through the module's own check_digests."""
    for path, digest in (
        (Path(k6_file), K6_SHA256),
        (Path(rge_file), RGE_SHA256),
        (Path(observables_file), OBSERVABLES_SHA256),
    ):
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != digest:
            raise k6.IntegrityError(f"sha256 mismatch for {path}: expected {digest}, got {actual}")


def check_epsilon(value: float) -> None:
    if value != EPSILON:
        raise ValueError(f"epsilon must be {EPSILON!r}, got {value!r}")


def environment(epsilon: float) -> dict[str, Any]:
    return {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "numpy_config": np.show_config(mode="dicts"),
        "threads": {var: os.environ.get(var) for var in THREAD_VARS},
        "epsilon": epsilon,
    }


# Axis coordinates, labels and zones (contracts.md section 5, Function) --------------------------


def axis_coordinates(v: Array, a: Array) -> Array:
    a_hat = np.array([a_k / np.sqrt(a_k @ a_k) for a_k in a])
    return v @ a_hat.T


def zone_membership(c: Array) -> NDArray[np.bool_]:
    """i in Z_k iff c[i, k] > mean(c[i]) (strict); all-equal components leave a row in no zone."""
    return c > c.mean(axis=1, keepdims=True)


def zone_trees(
    d: Array, fit: Sequence[int], in_zone: NDArray[np.bool_], n_axes: int = N_AXES,
) -> tuple[list[int], list[float | None]]:
    """Per axis, in order: the FIT zone's minimum spanning tree edge count and its median threshold
    (None, 0 edges for a zone with fewer than 2 FIT notes)."""
    tree_edge_counts: list[int] = []
    thetas: list[float | None] = []
    for k in range(n_axes):
        rows = np.array([i for i in fit if in_zone[i, k]], dtype=np.intp)
        if len(rows) >= 2:
            local = rge.minimum_spanning_tree(d[np.ix_(rows, rows)])
            thetas.append(rge.median_threshold([w for _, _, w in local]))
            tree_edge_counts.append(len(local))
        else:
            thetas.append(None)
            tree_edge_counts.append(0)
    return tree_edge_counts, thetas


# Real neighbours ---------------------------------------------------------------------------------


def real_neighbours(
    d: Array, pool: Sequence[int], targets: Sequence[int], k: int = K_NEIGH,
) -> dict[int, list[int]]:
    """For each row in targets, the k rows of pool nearest by d, excluding itself, ties to the
    lower row."""
    pool_list = [int(r) for r in pool]
    out: dict[int, list[int]] = {}
    for raw_i in targets:
        i = int(raw_i)
        candidates = [r for r in pool_list if r != i]
        candidates.sort(key=lambda r: (d[i, r], r))
        out[i] = candidates[:k]
    return out


# Cone membership (tunnel, TG.md) -------------------------------------------------------------------


def cone_membership(
    vx: Array, vi: Array, vj: Array, rho_i: float, rho_j: float,
) -> tuple[bool, float]:
    """sigma and whether x is inside the tunnel between i and j (TG.md, Tunnel)."""
    vij = vj - vi
    sigma = float(np.dot(vx - vi, vij)) / float(vij @ vij)
    if not (0.0 <= sigma <= 1.0):
        return False, sigma
    radius = (1.0 - sigma) * rho_i + sigma * rho_j
    axis_point = vi + sigma * vij
    inside = float(np.linalg.norm(vx - axis_point)) <= radius
    return inside, sigma


# Tension, effort and the cut (D29, D27) -----------------------------------------------------------


def tension_matrix(points: Array) -> tuple[Array, Array]:
    """p_bar, T = 1/2 sum (c_x - p_bar)(c_x - p_bar)^T for the given sphere points (D29)."""
    p_bar = points.mean(axis=0)
    diffs = points - p_bar
    return p_bar, 0.5 * diffs.T @ diffs


def effort(t: Array, u: Array) -> float:
    """The tension of a sphere along a unit direction (D29): u^T T u."""
    return float(u @ t @ u)


def cut_and_pass(t: Array, b: Array, u_blind: Array) -> tuple[float, float, bool]:
    """The pair's own effort, the 12th smallest blind effort (index 11), and whether it passes
    the cut, strictly (D27)."""
    e = effort(t, b)
    blind = np.array([effort(t, u) for u in u_blind])
    kappa = float(np.sort(blind)[CUT_INDEX])
    return e, kappa, e < kappa


def sphere_without_ends(i: int, j: int, neighbours: Mapping[int, list[int]]) -> list[int]:
    members = (set(neighbours[i]) | set(neighbours[j])) - {i, j}
    return sorted(members)


def judge_pair(
    i: int, j: int, c: Array, v: Array, neighbours: Mapping[int, list[int]], u_blind: Array,
) -> dict[str, Any]:
    """Sphere without ends, effort, cut, tunnel and veto for one bridge (TG.md, Bridge/Effort/Tunnel)."""
    s = sphere_without_ends(i, j, neighbours)
    _, t = tension_matrix(c[s])
    b = c[j] - c[i]
    b = b / np.linalg.norm(b)
    e, kappa, passes = cut_and_pass(t, b, u_blind)

    rho_i = float(np.linalg.norm(v[i] - v[neighbours[i][-1]]))
    rho_j = float(np.linalg.norm(v[j] - v[neighbours[j][-1]]))
    in_sphere_full = {i, j} | set(neighbours[i]) | set(neighbours[j])
    foreign = []
    for x in neighbours:
        if x in in_sphere_full:
            continue
        inside, _ = cone_membership(v[x], v[i], v[j], rho_i, rho_j)
        if inside:
            foreign.append(x)
    vetoed = any(i not in neighbours[x] and j not in neighbours[x] for x in foreign)
    return {
        "n_sphere_without_ends": len(s),
        "effort": e,
        "cut": kappa,
        "passes": bool(passes),
        "foreign": sorted(foreign),
        "vetoed": bool(vetoed),
        "T": t,
    }


# Candidacy (TG.md, Candidates and verdicts) --------------------------------------------------------


def candidacy(
    i: int, j: int, dist_ij: float, in_zone: NDArray[np.bool_], lab: NDArray[np.intp],
    thetas: Sequence[float | None],
) -> tuple[list[int], bool | None]:
    """candidate_zones (k in shared with dist <= theta_k), own_sphere (None when shared is not
    empty; else whether dist <= min of the two ends' own thresholds, False if either is missing)."""
    shared = sorted(k for k in range(N_AXES) if in_zone[i, k] and in_zone[j, k])
    if shared:
        candidate_zones = [
            k for k in shared if (theta_k := thetas[k]) is not None and dist_ij <= theta_k
        ]
        return candidate_zones, None
    theta_i, theta_j = thetas[int(lab[i])], thetas[int(lab[j])]
    if theta_i is None or theta_j is None:
        return [], False
    return [], bool(dist_ij <= min(theta_i, theta_j))


def bridges(fit: Sequence[int], lab: NDArray[np.intp], zoned: NDArray[np.bool_]) -> list[Pair]:
    """FIT pairs with different labels; a note in no zone is never an end (TG.md, Zones)."""
    eligible = sorted(int(i) for i in fit if zoned[i])
    return [
        (i, j) for idx, i in enumerate(eligible) for j in eligible[idx + 1:] if lab[i] != lab[j]
    ]


# Variants (TG.md, Variants) -------------------------------------------------------------------------


def build_variants(
    v: Array, d: Array, label_items: Sequence[Mapping[str, str]], lab: NDArray[np.intp], epsilon: float,
) -> dict[str, Any]:
    names = [item["label"] for item in label_items]
    m_edges = rge.minimum_spanning_tree(d)
    epsilon_edges = rge.relations(names, v, epsilon)
    union_list = rge.union_edges(epsilon_edges, m_edges, d)

    touching = rge.touching_tree_weights(m_edges, lab, N_AXES)
    open_thresholds = [rge.median_threshold(w) if w else None for w in touching]
    related = rge.open_relations(d, lab, open_thresholds)
    open_list = rge.union_edges(related, m_edges, d)

    _trees_dense, within_dense, cross_dense = rge.cell_graph(d, lab, N_AXES)
    dense_list = rge.union_edges(within_dense, cross_dense, d)

    def pairs(edges: Sequence[Edge]) -> set[Pair]:
        return {(i, j) for i, j, _ in edges}

    return {
        "m_pairs": pairs(m_edges),
        "union": pairs(union_list),
        "open_borders": pairs(open_list),
        "dense": pairs(dense_list),
    }


def variant_j(
    variant_pairs: set[Pair], m_pairs: set[Pair], candidate_pairs: set[Pair],
    fit_set: set[int], lab: NDArray[np.intp], zoned: NDArray[np.bool_],
) -> set[Pair]:
    """TG.md, Zones: a note in no zone is never an end of a pair in J -- neither a relation the
    variant has (excluded here) nor a candidate (bridges() already excludes it from candidacy)."""
    already = {
        (i, j) for (i, j) in variant_pairs
        if i in fit_set and j in fit_set and lab[i] != lab[j] and (i, j) not in m_pairs
        and zoned[i] and zoned[j]
    }
    added = candidate_pairs - variant_pairs
    return already | added


def build_graph(
    n: int, base_pairs: set[Pair], j_pairs: set[Pair], kept_pairs: set[Pair],
) -> list[set[int]]:
    """(base ∖ J) ∪ kept, as an adjacency list."""
    edges = (base_pairs - j_pairs) | kept_pairs
    adj: list[set[int]] = [set() for _ in range(n)]
    for i, j in edges:
        adj[i].add(j)
        adj[j].add(i)
    return adj


def count_edges(adj: list[set[int]]) -> int:
    """The graph's own relation count, from the adjacency it was actually built with."""
    return sum(len(neighbours) for neighbours in adj) // 2


def beta(edges_count: int) -> float:
    return 2.0 * edges_count / BETA_DENOMINATOR


# Breadth-first turns ------------------------------------------------------------------------------


def bfs(adj: list[set[int]], start: int) -> NDArray[np.int64]:
    n = len(adj)
    dist = np.full(n, -1, dtype=np.int64)
    dist[start] = 0
    queue: deque[int] = deque([start])
    while queue:
        u = queue.popleft()
        for w in adj[u]:
            if dist[w] == -1:
                dist[w] = dist[u] + 1
                queue.append(w)
    return dist


def is_connected(adj: list[set[int]]) -> bool:
    return bool(np.all(bfs(adj, 0) >= 0))


# Block bootstrap (contracts.md section 0/5, Dependence and interval) -------------------------------


def n_blocks_for(n: int, length: int) -> int:
    return -(-n // length)


def block_sizes(n: int, length: int) -> list[int]:
    edges = list(range(0, n, length)) + [n]
    return [edges[k + 1] - edges[k] for k in range(len(edges) - 1)]


def bootstrap_means(rng: np.random.Generator, values: Array, length: int) -> Array:
    n = len(values)
    nb = n_blocks_for(n, length)
    sizes = block_sizes(n, length)
    out = np.empty(N_BOOT)
    for b in range(N_BOOT):
        counts = np.bincount(rng.integers(0, nb, nb), minlength=nb)
        out[b] = np.mean(np.repeat(values, np.repeat(counts, sizes)))
    return out


def interval_record(draws: Array) -> dict[str, Any]:
    ordered = np.sort(draws)
    lo, hi = INTERVAL_RANKS
    return {
        "interval": [float(ordered[lo]), float(ordered[hi])],
        "ranks": {str(r): float(ordered[r]) for r in MC_RANKS},
    }


# Controls (TG.md, Controls) -------------------------------------------------------------------------


def ceiling_control(eval_notes: Sequence[int], neighbours_eval: Mapping[int, list[int]], n: int) -> bool:
    """Every h_q(n) = 1 on the graph joining each EVAL q directly to its own R(q)."""
    adj: list[set[int]] = [set() for _ in range(n)]
    for q in eval_notes:
        for nb in neighbours_eval[q]:
            adj[q].add(nb)
            adj[nb].add(q)
    for q in eval_notes:
        dist = bfs(adj, q)
        total = sum(int(dist[nb]) for nb in neighbours_eval[q])
        if total != len(neighbours_eval[q]):
            return False
    return True


def check_equal_budget(g_plus_edges: int, g_blind_edges: int) -> bool:
    """|G^b| = |G+|, on the graphs as actually built (TG.md, Controls)."""
    return g_plus_edges == g_blind_edges


def exchangeable_control(
    rng: np.random.Generator, judged: Sequence[Pair], pair_info: Mapping[Pair, dict[str, Any]],
) -> dict[str, Any]:
    n_j = len(judged)
    if n_j == 0:
        w = rng.standard_normal((0, N_AXES))
        return {"n_j": 0, "fraction": None, "band": None, "passed": True}
    w = rng.standard_normal((n_j, N_AXES))
    w = w / np.linalg.norm(w, axis=1, keepdims=True)
    below = 0
    for idx, pair in enumerate(judged):
        info = pair_info[pair]
        if effort(info["T"], w[idx]) < info["cut"]:
            below += 1
    fraction = below / n_j
    expected = 12.0 / 1001.0
    tol = MC_Z * math.sqrt(expected * (989.0 / 1001.0) / n_j)
    band = [expected - tol, expected + tol]
    return {"n_j": n_j, "fraction": fraction, "band": band, "passed": bool(band[0] <= fraction <= band[1])}


# Measurement ----------------------------------------------------------------------------------------


def measure(
    v: Array, a: Array, axis_ids: Sequence[str], label_items: Sequence[Mapping[str, str]], epsilon: float,
    _on_draw: Callable[[str, str, str, int], None] | None = None,
) -> dict[str, Any]:
    n = len(v)
    fit_raw, ev_raw = k6.split_fit_eval(n)
    fit = [int(i) for i in fit_raw]
    ev = [int(i) for i in ev_raw]
    fit_set, eval_set = set(fit), set(ev)
    d = rge.pairwise_distances(v)
    lab = rge.axis_cells(v, a)
    c = axis_coordinates(v, a)
    in_zone = zone_membership(c)
    zoned = cast("NDArray[np.bool_]", in_zone.any(axis=1))
    tree_edge_counts, thetas = zone_trees(d, fit, in_zone)

    neighbours_fit = real_neighbours(d, fit, fit)
    neighbours_eval = real_neighbours(d, ev, ev)

    variants_data = build_variants(v, d, label_items, lab, epsilon)
    bridge_list = bridges(fit, lab, zoned)

    candidate_pairs: set[Pair] = set()
    candidacy_info: dict[Pair, tuple[list[int], bool | None]] = {}
    for i, j in bridge_list:
        cz, own = candidacy(i, j, float(d[i, j]), in_zone, lab, thetas)
        candidacy_info[(i, j)] = (cz, own)
        if cz or own is True:
            candidate_pairs.add((i, j))

    j_by_variant = {
        name: variant_j(
            variants_data[name], variants_data["m_pairs"], candidate_pairs, fit_set, lab, zoned,
        )
        for name in VARIANTS
    }
    judged = sorted(set().union(*j_by_variant.values()))

    rng = np.random.Generator(np.random.PCG64(SEED))
    g = rng.standard_normal((N_BLIND, N_AXES))
    u_blind = g / np.linalg.norm(g, axis=1, keepdims=True)

    pair_info: dict[Pair, dict[str, Any]] = {
        (i, j): judge_pair(i, j, c, v, neighbours_fit, u_blind) for i, j in judged
    }

    exchangeable = exchangeable_control(rng, judged, pair_info)

    kept_by_variant: dict[str, set[Pair]] = {}
    kb_by_variant: dict[str, set[Pair]] = {}
    for name in VARIANTS:
        j_pairs = j_by_variant[name]
        kept = {p for p in j_pairs if pair_info[p]["passes"] and not pair_info[p]["vetoed"]}
        kept_by_variant[name] = kept
        j_sorted = sorted(j_pairs)
        chosen = rng.choice(len(j_sorted), len(kept), replace=False)
        kb_by_variant[name] = {j_sorted[idx] for idx in chosen}

    graphs: dict[str, dict[str, list[set[int]]]] = {}
    edge_counts: dict[str, dict[str, int]] = {}
    for name in VARIANTS:
        base = variants_data[name]
        j_pairs = j_by_variant[name]
        kept = kept_by_variant[name]
        kb = kb_by_variant[name]
        g0_adj = build_graph(n, base, set(), set())
        g_plus_adj = build_graph(n, base, j_pairs, kept)
        g_blind_adj = build_graph(n, base, j_pairs, kb)
        graphs[name] = {"g0": g0_adj, "g_plus": g_plus_adj, "g_blind": g_blind_adj}
        edge_counts[name] = {
            "g0": count_edges(g0_adj),
            "g_plus": count_edges(g_plus_adj),
            "g_blind": count_edges(g_blind_adj),
        }

    connectivity = {
        name: {graph: is_connected(adj) for graph, adj in graphs[name].items()} for name in VARIANTS
    }
    equal_budget = {
        name: check_equal_budget(edge_counts[name]["g_plus"], edge_counts[name]["g_blind"])
        for name in VARIANTS
    }
    ceiling_ok = ceiling_control(sorted(eval_set), neighbours_eval, n)

    control_passed = {
        "exchangeable_direction": bool(exchangeable["passed"]),
        "ceiling": ceiling_ok,
        "connectivity": all(v2 for per_variant in connectivity.values() for v2 in per_variant.values()),
        "equal_budget": all(equal_budget.values()),
    }
    controls = {
        "exchangeable_direction": exchangeable,
        "ceiling": {"passed": ceiling_ok},
        "connectivity": {"passed": control_passed["connectivity"], **connectivity},
        "equal_budget": {"passed": control_passed["equal_budget"], **equal_budget},
    }
    failed_conditions = [name for name in CONTROL_IDENTIFIERS if not control_passed[name]]
    valid = not failed_conditions

    d_by_variant: dict[str, dict[int, int]] = {}
    dprime_by_variant: dict[str, dict[int, int]] = {}
    horizon_by_variant: dict[str, int] = {}
    for name in VARIANTS:
        h_sum: dict[str, dict[int, int]] = {"g0": {}, "g_plus": {}, "g_blind": {}}
        eccentricity_max = 0
        for graph_name, adj in graphs[name].items():
            for q in eval_set:
                dist = bfs(adj, q)
                h_sum[graph_name][q] = int(sum(int(dist[nb]) for nb in neighbours_eval[q]))
                eccentricity_max = max(eccentricity_max, int(dist.max()))
        horizon_by_variant[name] = eccentricity_max
        d_by_variant[name] = {q: h_sum["g0"][q] - h_sum["g_plus"][q] for q in eval_set}
        dprime_by_variant[name] = {q: h_sum["g_blind"][q] - h_sum["g_plus"][q] for q in eval_set}

    beta_dense = beta(len(variants_data["dense"]))

    scope_order: list[tuple[str, list[int]]] = [("global", sorted(eval_set))]
    for k in range(N_AXES):
        scope_order.append((axis_ids[k], sorted(q for q in eval_set if in_zone[q, k])))

    variants_out: dict[str, Any] = {}
    decision: dict[str, str | None] = {}
    for scope_name, _ in scope_order:
        decision[scope_name] = None

    for name in VARIANTS:
        beta_g0 = beta(edge_counts[name]["g0"])
        beta_plus = beta(edge_counts[name]["g_plus"])
        rule_2 = "refuted" if beta_plus >= beta_dense else "holds"

        # Precompute the scope value arrays and means (no draws): D28 makes A_q's dependence on
        # H disappear, so D_q/D'_q sums are already known before any bootstrap resampling.
        n_by_scope: dict[str, int] = {}
        values_by_stat_scope: dict[str, dict[str, Array]] = {"d_bar": {}, "d_bar_prime": {}}
        mean_by_stat_scope: dict[str, dict[str, float | None]] = {"d_bar": {}, "d_bar_prime": {}}
        for scope_name, notes in scope_order:
            n_scope = len(notes)
            n_by_scope[scope_name] = n_scope
            values_d = np.array([d_by_variant[name][q] for q in notes], dtype=np.float64)
            values_dp = np.array([dprime_by_variant[name][q] for q in notes], dtype=np.float64)
            values_by_stat_scope["d_bar"][scope_name] = values_d
            values_by_stat_scope["d_bar_prime"][scope_name] = values_dp
            mean_by_stat_scope["d_bar"][scope_name] = float(values_d.mean()) if n_scope else None
            mean_by_stat_scope["d_bar_prime"][scope_name] = float(values_dp.mean()) if n_scope else None

        # Draws (TG.md): for this variant, for D-bar then D-bar-prime, for global then the zones
        # in axis order, for each valid L ascending, b = 1..10,000.
        per_l_by_stat_scope: dict[str, dict[str, dict[str, Any]]] = {"d_bar": {}, "d_bar_prime": {}}
        for stat_name in ("d_bar", "d_bar_prime"):
            for scope_name, _notes in scope_order:
                n_scope = n_by_scope[scope_name]
                values = values_by_stat_scope[stat_name][scope_name]
                mean_value = mean_by_stat_scope[stat_name][scope_name]
                per_l: dict[str, Any] = {}
                for length in GRID:
                    nb_ = n_blocks_for(n_scope, length) if n_scope else 0
                    is_valid = n_scope > 0 and nb_ >= MIN_BLOCKS
                    if is_valid:
                        if _on_draw is not None:
                            _on_draw(name, stat_name, scope_name, length)
                        draws = bootstrap_means(rng, values, length)
                        rec = interval_record(draws)
                        per_l[str(length)] = {"valid": True, "n_blocks": nb_, "mean": mean_value, **rec}
                    else:
                        per_l[str(length)] = {
                            "valid": False, "n_blocks": nb_, "mean": mean_value,
                            "interval": None, "ranks": None,
                        }
                per_l_by_stat_scope[stat_name][scope_name] = per_l

        scopes_out = []
        for scope_name, notes in scope_order:
            n_scope = n_by_scope[scope_name]
            mean_d = mean_by_stat_scope["d_bar"][scope_name]
            mean_dp = mean_by_stat_scope["d_bar_prime"][scope_name]
            per_l_d = per_l_by_stat_scope["d_bar"][scope_name]
            per_l_dp = per_l_by_stat_scope["d_bar_prime"][scope_name]

            valid_d = [per_l_d[str(length)] for length in GRID if per_l_d[str(length)]["valid"]]
            valid_dp = [per_l_dp[str(length)] for length in GRID if per_l_dp[str(length)]["valid"]]

            if not valid_d:
                rule_1 = "pending"
            elif any(rec["interval"][0] <= 0.0 <= rec["interval"][1] for rec in valid_d):
                rule_1 = "inconclusive"
            elif all(rec["interval"][0] > 0.0 for rec in valid_d) and beta_plus <= beta_g0:
                rule_1 = "holds"
            else:
                rule_1 = "refuted"

            if not valid_dp:
                rule_3 = "pending"
            elif any(rec["interval"][0] <= 0.0 <= rec["interval"][1] for rec in valid_dp):
                rule_3 = "inconclusive"
            elif all(rec["interval"][0] > 0.0 for rec in valid_dp):
                rule_3 = "holds"
            else:
                rule_3 = "refuted"

            if rule_1 == "pending" or rule_3 == "pending":
                variant_scope_decision = "pending"
            elif "refuted" in (rule_1, rule_2, rule_3):
                variant_scope_decision = "refuted"
            elif rule_1 == rule_2 == rule_3 == "holds":
                variant_scope_decision = "holds"
            else:
                variant_scope_decision = "inconclusive"

            scopes_out.append({
                "scope": scope_name,
                "n": n_scope,
                "d_bar": {"mean": mean_d, "per_l": per_l_d},
                "d_bar_prime": {"mean": mean_dp, "per_l": per_l_dp},
                "rule_1": rule_1,
                "rule_2": rule_2,
                "rule_3": rule_3,
                "decision": variant_scope_decision,
            })

            previous = decision[scope_name]
            if previous is None:
                decision[scope_name] = variant_scope_decision
            elif "pending" in (previous, variant_scope_decision):
                decision[scope_name] = "pending"
            elif "refuted" in (previous, variant_scope_decision):
                decision[scope_name] = "refuted"
            elif previous == variant_scope_decision == "holds":
                decision[scope_name] = "holds"
            else:
                decision[scope_name] = "inconclusive"

        variants_out[name] = {
            "g0": {"relations": edge_counts[name]["g0"], "beta": beta_g0},
            "g_plus": {"relations": edge_counts[name]["g_plus"], "beta": beta_plus},
            "g_blind": {
                "relations": edge_counts[name]["g_blind"],
                "beta": beta(edge_counts[name]["g_blind"]),
            },
            "j_size": len(j_by_variant[name]),
            "k_size": len(kept_by_variant[name]),
            "horizon": horizon_by_variant[name],
            "scopes": scopes_out,
        }

    if not valid:
        decision = dict.fromkeys(decision)
        for variant_block in variants_out.values():
            for scope in variant_block["scopes"]:
                scope["rule_1"] = scope["rule_2"] = scope["rule_3"] = scope["decision"] = None

    zones_out = []
    for k in range(N_AXES):
        n_fit = int(np.count_nonzero(in_zone[fit, k]))
        n_eval = int(np.count_nonzero(in_zone[ev, k]))
        zone_candidates = zone_kept = zone_marked = zone_vetoed = 0
        for (i, j), (cz, _own) in candidacy_info.items():
            if k in cz:
                zone_candidates += 1
                info = pair_info[(i, j)]
                if info["passes"] and not info["vetoed"]:
                    zone_kept += 1
                if info["foreign"]:
                    zone_marked += 1
                if info["vetoed"]:
                    zone_vetoed += 1
        zones_out.append({
            "axis": axis_ids[k],
            "n_fit": n_fit,
            "n_eval": n_eval,
            "tree_edges": tree_edge_counts[k],
            "theta": thetas[k],
            "candidates": zone_candidates,
            "kept": zone_kept,
            "marked": zone_marked,
            "vetoed": zone_vetoed,
        })
    notes_in_no_zone = int(np.count_nonzero(~zoned[fit]))
    zone_counts = in_zone[fit].sum(axis=1)
    zones_per_fit_note = {str(count): int(np.count_nonzero(zone_counts == count)) for count in range(N_AXES + 1)}

    pairs_out = []
    for i, j in judged:
        info = pair_info[(i, j)]
        cz, own = candidacy_info.get((i, j), ([], None))
        kept_zones = cz if (info["passes"] and not info["vetoed"]) else []
        in_variants = [name for name in VARIANTS if (i, j) in j_by_variant[name]]
        pairs_out.append({
            "i": i,
            "j": j,
            "lab_i": axis_ids[int(lab[i])],
            "lab_j": axis_ids[int(lab[j])],
            "dist": float(d[i, j]),
            "n_sphere_without_ends": info["n_sphere_without_ends"],
            "effort": info["effort"],
            "cut": info["cut"],
            "passes": info["passes"],
            "foreign": info["foreign"],
            "vetoed": info["vetoed"],
            "candidate_zones": cz,
            "kept_zones": kept_zones,
            "own_sphere": own,
            "in_variants": in_variants,
        })

    foreign_counts = [len(pair_info[p]["foreign"]) for p in judged]
    reported = {
        "kept_fraction": {
            name: (len(kept_by_variant[name]) / len(j_by_variant[name]) if j_by_variant[name] else None)
            for name in VARIANTS
        },
        "foreign_note_counts": {
            "marked": int(sum(1 for c in foreign_counts if c > 0)),
            "max": max(foreign_counts) if foreign_counts else 0,
            "mean": (sum(foreign_counts) / len(foreign_counts)) if foreign_counts else None,
        },
    }

    return {
        "valid": valid,
        "first_failed_condition": failed_conditions[0] if failed_conditions else None,
        "failed_conditions": failed_conditions,
        "conditions_checked": list(CONTROL_IDENTIFIERS),
        "zones": {
            "per_axis": zones_out,
            "notes_in_no_zone": notes_in_no_zone,
            "zones_per_fit_note": zones_per_fit_note,
        },
        "pairs": pairs_out,
        "variants": variants_out,
        "dense_reference": {"relations": len(variants_data["dense"]), "beta": beta_dense},
        "decision": decision,
        "controls": controls,
        "reported": reported,
    }


# Writing, run and main --------------------------------------------------------------------------------


def _plain(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
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
    k6_file: Path, rge_file: Path, observables_file: Path,
    embeddings: Path, labels: Path, axes: Path,
    expected: Mapping[Path, str], out_path: Path,
) -> dict[str, Any]:
    """Pin checks, then epsilon, then the artefacts (contracts.md section 5, Order)."""
    check_pins(Path(k6_file), Path(rge_file), Path(observables_file))
    epsilon = resolve_epsilon_edge()
    check_epsilon(epsilon)
    raw = k6.check_digests(expected)
    v32, label_list, axis_ids, a = k6.load_inputs(
        raw[Path(embeddings)], raw[Path(labels)], raw[Path(axes)]
    )
    k6.validate_inputs(v32, label_list, axis_ids, a)
    v64 = v32.astype("<f8")
    v = np.array([row / np.sqrt(row @ row) for row in v64])
    result = measure(v, a, axis_ids, label_list, epsilon)
    result["digests"] = {
        Path(k6_file).name: K6_SHA256,
        Path(rge_file).name: RGE_SHA256,
        Path(observables_file).name: OBSERVABLES_SHA256,
        **{Path(p).name: d for p, d in expected.items()},
    }
    result["environment"] = environment(epsilon)
    return _write(result, out_path)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="TG tension gate on cross-label relations.")
    parser.add_argument("--out", type=Path, default=RESULT, help=f"result path (default: {RESULT})")
    out_path: Path = parser.parse_args(argv).out
    result = run(K6_FILE, RGE_FILE, OBSERVABLES_FILE, EMBEDDINGS, LABELS, AXES, EXPECTED_DIGESTS, out_path)
    print(f"TG: valid={result['valid']} -> {out_path}")
    if not result["valid"]:
        raise SystemExit(f"TG invalid: {result['failed_conditions']}")


if __name__ == "__main__":
    main()
