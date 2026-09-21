"""R4 — neighbourhood kept in a 5D perspective.

Implements frontend/audits/R4.md (instrument audit record, revision 5) against
frontend/audits/contracts.md (§0 data layer, §2 R4) and frontend/audits/derivations.md. For each
note q of K6's EVAL half, the 15 nearest notes in 384-d are compared with the 15 nearest in the
observed space of the perspective at q (traianus/geometry/perspective.py): the operator's
horizontal axis against a bank of random axes orthogonal to q, by block bootstrap over q and over
directions at every block length of the grid.

Refuses to run unless the three input digests and the digest of K6's committed result match, and
unless that result is valid; never runs on anything else. A run that fails a validity condition
(y-only control, permutation control) is written with valid = false and exits non-zero: no result
from it is used.

Usage:
    python3 tools/experiments/r4_perspective_recall.py [--out PATH]
"""

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_var] = "1"

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.experiments import k6_colour_predictability as k6
from traianus.geometry.perspective import observe, perspective_frame
from traianus.geometry.polar_projector import PolarProjector

EMBEDDINGS, LABELS, AXES, K6_RESULT = k6.EMBEDDINGS, k6.LABELS, k6.AXES, k6.RESULT
RESULT = REPO_ROOT / "data" / "refapp" / "R4_result.json"
EXPECTED_DIGESTS = {
    **k6.EXPECTED_DIGESTS,
    K6_RESULT: "a95ec2a01a14f9638c9fc01d1bc9f198f5c53e580636858a7690baf9539cac58",
}

SEED = k6.SEED
K = 15
KS = (5, K, 50)
K_INDEX = KS.index(K)
N_DIRECTIONS = 200
N_RESAMPLES = 10_000
GRID = (1, 2, 5, 10, 20, 50)
MIN_BLOCKS = 20
MC_OFFSET = 16
TIE_TOL = 1e-12
NEAR_DUPLICATE_TOL = 1e-12
PERMUTATION_BAND = (0.149, 0.257)
L_GT_MAX = 100
FAR_GAP = 100
OVERLAP_FACTOR = 2
CHANNELS = ("lambda_2", "lambda_3", "a_8", "l")
MAX_CHANNELS = 3
SPACES = ("full", "2d")
CHUNK = 500

IntegrityError = k6.IntegrityError
Array = NDArray[np.float64]


class K6ResultError(ValueError):
    """K6's committed result cannot be used by R4."""


# K6 dependency ------------------------------------------------------------------------------------


def read_k6_result(
    raw: bytes, axis_ids: Sequence[str], data_digests: Mapping[str, str]
) -> dict[str, Any]:
    """K6's result: valid, computed on these data digests, with a usable ranking and selection."""
    prior: dict[str, Any] = json.loads(raw.decode("utf-8"))
    for key in ("valid", "digests", "ranking_fit", "selected"):
        if key not in prior:
            raise K6ResultError(f"K6 result: key {key} missing")
    if prior["valid"] is not True:
        raise K6ResultError(f"K6 result: valid = {prior['valid']!r}, R4 does not run")
    if prior["digests"] != dict(data_digests):
        raise K6ResultError("K6 result: digests differ from the input digests verified in this run")
    if sorted(prior["ranking_fit"]) != sorted(axis_ids):
        raise K6ResultError("K6 result: ranking_fit is not a permutation of the axis ids")
    selected = prior["selected"]
    if (
        len(selected) > MAX_CHANNELS
        or len(set(selected)) != len(selected)
        or not set(selected) <= set(CHANNELS)
    ):
        raise K6ResultError(f"K6 result: selected {selected!r} is not distinct channels of {CHANNELS}")
    return prior


def colour_columns(
    v: Array, a_hat: Array, axis_ids: Sequence[str], prior: Mapping[str, Any]
) -> Array | None:
    """K6's selected channels, in K6's per-epoch frame from its FIT ranking, one column each."""
    if not prior["selected"]:
        return None
    order = [list(axis_ids).index(axis_id) for axis_id in prior["ranking_fit"]]
    projector = PolarProjector()
    channels = k6.eval_channels(v, a_hat, k6.build_frame(a_hat, order, projector), projector)
    return np.column_stack([channels[name] for name in prior["selected"]])


# Blocks, intervals, decision ----------------------------------------------------------------------


def block_starts(n: int, length: int) -> NDArray[np.intp]:
    return np.arange(0, n, length)


def n_blocks(n: int, length: int) -> int:
    return len(block_starts(n, length))


def interval(means: Array) -> dict[str, Any]:
    """[sorted[B/40 - 1], sorted[B - B/40 - 1]] and the Monte Carlo neighbours of both bounds."""
    s = np.sort(means)
    lo = len(s) // 40 - 1
    hi = len(s) - len(s) // 40 - 1
    return {
        "lo": float(s[lo]),
        "hi": float(s[hi]),
        "lo_neighbours": [float(s[lo - MC_OFFSET]), float(s[lo + MC_OFFSET])],
        "hi_neighbours": [float(s[hi - MC_OFFSET]), float(s[hi + MC_OFFSET])],
    }


def decide(per_block: Mapping[str, Mapping[str, Any]]) -> tuple[bool, float]:
    """R4 holds iff hi < 0 at every block length; the margin is the largest hi."""
    upper = [p["hi"] for p in per_block.values()]
    return all(h < 0 for h in upper), max(upper)


def _in_band(mean: float) -> bool:
    return PERMUTATION_BAND[0] <= mean <= PERMUTATION_BAND[1]


def assess_validity(
    y_only: Mapping[str, Any], permutation_mean: float
) -> tuple[bool, str | None, list[str]]:
    failed = [] if y_only["passes"] else ["y_only_control"]
    if not _in_band(permutation_mean):
        failed.append("permutation_control")
    return not failed, (failed[0] if failed else None), failed


# Random streams -----------------------------------------------------------------------------------


def draw_directions(rng: np.random.Generator, n_directions: int, d: int) -> Array:
    return rng.standard_normal((n_directions, d))


def draw_sigma_weights(rng: np.random.Generator, n_directions: int, n: int) -> Array:
    return rng.standard_normal((n_directions, n))


def sigma_bank(f: Array, v: Array) -> Array:
    """Rows g_j = X_cᵀ f_j / √N, X_c the centred EVAL matrix."""
    x_c = v - v.mean(axis=0)
    bank: Array = f @ x_c / np.sqrt(len(v))
    return bank


def random_directions(bank: Array, q_hat: Array) -> Array:
    """u_j = P_q⊥ e_j / ‖P_q⊥ e_j‖, P_q⊥ x = x − ⟨x, q̂⟩q̂ (D10)."""
    p = bank - np.multiply.outer(bank @ q_hat, q_hat)
    u: Array = p / np.linalg.norm(p, axis=1, keepdims=True)
    return u


# Neighbour lists and recall -----------------------------------------------------------------------


def ground_truth_neighbours(g_row: Array, q: int, k: int) -> NDArray[np.intp]:
    """The k notes j ≠ q with the largest G[q, j]; ties: lower index."""
    order = -np.asarray(g_row, dtype=np.float64)
    order[q] = np.inf
    return np.argsort(order, kind="stable")[:k]


def observed_neighbours(obs: Array, q: int, k: int) -> NDArray[np.intp]:
    """The k notes j ≠ q nearest to q in the observed space (Euclidean); ties: lower index."""
    dist = np.sqrt(((obs - obs[q]) ** 2).sum(axis=1))
    dist[q] = np.inf
    return np.argsort(dist, kind="stable")[:k]


def permutation_neighbours(perm: NDArray[np.intp], q: int, k: int) -> NDArray[np.intp]:
    """The first k entries of a permutation of the N − 1 notes other than q, in index order."""
    others: NDArray[np.intp] = np.delete(np.arange(len(perm) + 1), q)
    return others[perm[:k]]


def truth_masks(truth: NDArray[np.intp], n: int) -> NDArray[np.bool_]:
    masks = np.zeros((len(KS), n), dtype=bool)
    for row, k in zip(masks, KS):
        row[truth[:k]] = True
    return masks


def recall(mask: NDArray[np.bool_], found: NDArray[np.intp]) -> int:
    return int(mask[found].sum())


def recalls_in(obs: Array, q: int, masks: NDArray[np.bool_]) -> NDArray[np.int16]:
    """Recall at every k, in the full observed space and in its first two columns (x, y)."""
    out = np.empty((len(SPACES), len(KS)), dtype=np.int16)
    for s, space in enumerate((obs, obs[:, :2])):
        found = observed_neighbours(space, q, KS[-1])
        out[s] = [recall(masks[i], found[:k]) for i, k in enumerate(KS)]
    return out


def arm_recalls(
    v: Array, q: int, horizontal: Array, colours: Array | None, masks: NDArray[np.bool_]
) -> NDArray[np.int16]:
    return recalls_in(observe(v, q, horizontal, colours), q, masks)


def bank_recalls(
    v: Array, q: int, bank: Array, colours: Array | None, masks: NDArray[np.bool_]
) -> NDArray[np.int16]:
    q_hat = v[q] / np.linalg.norm(v[q])
    return np.stack(
        [arm_recalls(v, q, u, colours, masks) for u in random_directions(bank, q_hat)], axis=-1
    )


def operator_horizontal(q_vec: Array, basis: Mapping[str, Array]) -> tuple[Array, bool]:
    """v_dipole / ‖v_dipole‖² of the perspective frame at q, and its collinear-fallback flag."""
    frame = perspective_frame(q_vec, dict(basis))
    horizontal: Array = frame.frame.v_dipole / frame.frame.v_dipole_norm_sq
    return horizontal, bool(frame.fallback)


def y_only_verdict(truth: NDArray[np.intp], found: NDArray[np.intp], g_row: Array) -> tuple[int, bool]:
    """Swapped pairs between the two 15-lists, and whether all of them are ties (within TIE_TOL
    of the 15th-place similarity)."""
    missing, extra = np.setdiff1d(truth, found), np.setdiff1d(found, truth)
    if missing.size == 0:
        return 0, True
    swapped = np.concatenate([missing, extra])
    return int(missing.size), bool(np.all(np.abs(g_row[swapped] - g_row[truth[-1]]) <= TIE_TOL))


def perspective_r2(obs: Array, q: int) -> Array:
    """R² of each colour column on (1, x, y, x², y², xy) of the perspective, over the N − 1 others."""
    rows = np.delete(obs, q, axis=0)
    x, y = rows[:, 0], rows[:, 1]
    design = np.column_stack([np.ones(len(rows)), x, y, x * x, y * y, x * y])
    return np.array([k6.r_squared(rows[:, c], design)[0] for c in range(2, obs.shape[1])])


def overlap_block_length(nn: NDArray[np.intp]) -> int | None:
    """L_gt: the smallest g ≤ 100 with overlap(g) ≤ 2 × far, from the 384-d neighbour lists alone."""
    n = len(nn)
    if n <= FAR_GAP:
        return None
    member = np.zeros((n, int(nn.max()) + 1), dtype=np.float32)
    member[np.arange(n)[:, None], nn] = 1.0
    overlap = (member @ member.T).astype(np.float64) / K
    far = overlap[np.triu(np.ones((n, n), dtype=bool), FAR_GAP)].mean()
    for g in range(1, L_GT_MAX + 1):
        if np.diagonal(overlap, g).mean() <= OVERLAP_FACTOR * far:
            return g
    return None


# Bootstrap ----------------------------------------------------------------------------------------


def block_bootstrap(
    rng: np.random.Generator, op: Array, rand: Array, length: int, n_resamples: int
) -> Array:
    """D̄_b over blocks of `length` notes and directions, both drawn with multiplicity.

    Per resample, K_b = rng.integers(0, n_blocks, n_blocks) then J_b = rng.integers(0, J, J). With
    n_k, m_j the counts of each block and direction, D̄_b = (Σ n_k S_k − Σ_k n_k Σ_j m_j C_kj / J)
    / Σ n_k size_k, S_k and C_kj the block sums of op and of rand: the mean over the notes of Q_b of
    op(q) − mean over J_b of rand(q, j).
    """
    n, j = rand.shape
    starts = block_starts(n, length)
    n_blk = len(starts)
    size = np.diff(np.append(starts, n)).astype(np.float64)
    s_op = np.add.reduceat(np.asarray(op, dtype=np.float64), starts)
    c = np.add.reduceat(np.asarray(rand, dtype=np.float64), starts, axis=0)
    out = np.empty(n_resamples)
    for first in range(0, n_resamples, CHUNK):
        count = min(CHUNK, n_resamples - first)
        k_counts, j_counts = np.empty((count, n_blk)), np.empty((count, j))
        for row in range(count):
            k_counts[row] = np.bincount(rng.integers(0, n_blk, n_blk), minlength=n_blk)
            j_counts[row] = np.bincount(rng.integers(0, j, j), minlength=j)
        numerator = k_counts @ s_op - ((k_counts @ c) * j_counts).sum(axis=1) / j
        out[first : first + count] = numerator / (k_counts @ size)
    return out


def _decision_record(means: Array, point: float, n: int, length: int) -> dict[str, Any]:
    record = {"n_blocks": n_blocks(n, length), "mean_difference": point, **interval(means)}
    record.update(
        margin=record["hi"],
        holds=record["hi"] < 0,
        hi_neighbours_hold=all(h < 0 for h in record["hi_neighbours"]),
    )
    return record


# Reported figures ---------------------------------------------------------------------------------


def _figures(op: Array, rand: Array, k: int) -> dict[str, float]:
    mean_op, mean_rand = float(op.mean()), float(rand.mean())
    return {
        "operator": mean_op,
        "random": mean_rand,
        "difference": mean_op - mean_rand,
        "retention_operator": mean_op / k,
        "retention_random": mean_rand / k,
    }


def summarise(op: NDArray[Any], rand: NDArray[Any]) -> dict[str, Any]:
    """Recall per space and k (op: (space, k, q); rand: (space, k, q, j)) and the colour gain."""
    spaces = {
        space: {str(k): _figures(op[s, i], rand[s, i], k) for i, k in enumerate(KS)}
        for s, space in enumerate(SPACES)
    }
    gain = {
        str(k): {
            "operator": float(op[0, i].mean() - op[1, i].mean()),
            "random": float(rand[0, i].mean() - rand[1, i].mean()),
        }
        for i, k in enumerate(KS)
    }
    return {"spaces": spaces, "colour_gain": gain}


# Measurement --------------------------------------------------------------------------------------


def measure(
    v: Array,
    a_hat: Array,
    axis_ids: Sequence[str],
    prior: Mapping[str, Any],
    rng: np.random.Generator,
    n_directions: int,
    n_resamples: int,
) -> dict[str, Any]:
    n = v.shape[0]
    if n - 1 < KS[-1]:
        raise ValueError(f"{n} notes leave fewer than {KS[-1]} neighbours")
    basis = dict(zip(axis_ids, a_hat))
    selected = list(prior["selected"])
    colours = colour_columns(v, a_hat, axis_ids, prior)
    gram = v @ v.T
    bank = draw_directions(rng, n_directions, v.shape[1])

    op = np.empty((len(SPACES), len(KS), n), dtype=np.int16)
    rand = np.empty((len(SPACES), len(KS), n, n_directions), dtype=np.int16)
    neighbours = np.empty((n, K), dtype=np.intp)
    permutation = np.empty(n)
    r2: list[Array] = []
    exact, ties, tie_pairs, near_duplicates, fallbacks = 0, 0, 0, 0, 0
    failures: list[int] = []
    for q in range(n):
        truth = ground_truth_neighbours(gram[q], q, KS[-1])
        masks = truth_masks(truth, n)
        neighbours[q] = truth[:K]
        horizontal, fallback = operator_horizontal(v[q], basis)
        fallbacks += fallback
        obs = observe(v, q, horizontal, colours)
        op[:, :, q] = recalls_in(obs, q, masks)
        r2.append(perspective_r2(obs, q))
        rand[:, :, q, :] = bank_recalls(v, q, bank, colours, masks)

        pairs, is_tie = y_only_verdict(truth[:K], observed_neighbours(observe(v, q), q, K), gram[q])
        exact += pairs == 0
        ties += pairs > 0 and is_tie
        tie_pairs += pairs if is_tie else 0
        if not is_tie:
            failures.append(q)
        near_duplicates += int(np.count_nonzero(np.delete(gram[q], q) >= 1 - NEAR_DUPLICATE_TOL))
        permutation[q] = recall(masks[K_INDEX], permutation_neighbours(rng.permutation(n - 1), q, K))

    op_deciding, rand_deciding = op[0, K_INDEX], rand[0, K_INDEX]
    point = float(op_deciding.mean() - rand_deciding.mean())
    per_block = {
        str(length): _decision_record(
            block_bootstrap(rng, op_deciding, rand_deciding, length, n_resamples), point, n, length
        )
        for length in GRID
    }

    sigma = sigma_bank(draw_sigma_weights(rng, n_directions, n), v)
    sigma_rand = np.empty_like(rand)
    for q in range(n):
        masks = truth_masks(ground_truth_neighbours(gram[q], q, KS[-1]), n)
        sigma_rand[:, :, q, :] = bank_recalls(v, q, sigma, colours, masks)

    l_gt = overlap_block_length(neighbours)
    l_gt_record = None
    if l_gt is not None:
        l_gt_record = per_block.get(str(l_gt)) or _decision_record(
            block_bootstrap(rng, op_deciding, rand_deciding, l_gt, n_resamples), point, n, l_gt
        )

    y_only = {
        "exact": exact,
        "ties": ties,
        "tie_pairs": tie_pairs,
        "near_duplicates": near_duplicates,
        "failures": failures,
        "passes": not failures,
    }
    permutation_mean = float(permutation.mean())
    valid, first_failed, failed = assess_validity(y_only, permutation_mean)
    holds, margin = decide(per_block)
    return {
        "n": n,
        "k": K,
        "n_directions": n_directions,
        "n_resamples": n_resamples,
        "colour_channels": selected,
        "dimension": 2 + len(selected),
        "fallback_count": fallbacks,
        "per_block_length": per_block,
        "y_only_control": y_only,
        "permutation_control": {
            "mean": permutation_mean,
            "band": list(PERMUTATION_BAND),
            "passes": _in_band(permutation_mean),
        },
        "reported": {
            **summarise(op, rand),
            "sigma_reference": summarise(op, sigma_rand),
            "l_gt": {"value": l_gt, "interval": l_gt_record},
            "r2_colour": dict(zip(selected, np.mean(r2, axis=0).tolist())),
        },
        "valid": valid,
        "first_failed_condition": first_failed,
        "failed_conditions": failed,
        "r4_holds": holds if valid else None,
        "margin": margin,
    }


def run(
    embeddings: Path,
    labels: Path,
    axes: Path,
    k6_result: Path,
    expected: Mapping[Path, str],
    out_path: Path,
) -> dict[str, Any]:
    raw = k6.check_digests(expected)
    v32, label_list, axis_ids, a = k6.load_inputs(
        raw[Path(embeddings)], raw[Path(labels)], raw[Path(axes)]
    )
    k6.validate_inputs(v32, label_list, axis_ids, a)
    data_digests = {Path(p).name: expected[p] for p in (embeddings, labels, axes)}
    prior = read_k6_result(raw[Path(k6_result)], axis_ids, data_digests)
    v64 = v32.astype("<f8")
    v = np.array([row / np.sqrt(row @ row) for row in v64])
    a_hat = np.array([a_k / np.sqrt(a_k @ a_k) for a_k in a])
    _, ev = k6.split_fit_eval(len(v))
    result = measure(v[ev], a_hat, axis_ids, prior, k6.make_rng(), N_DIRECTIONS, N_RESAMPLES)
    result["digests"] = {Path(p).name: d for p, d in expected.items()}
    result["environment"] = k6.environment()
    text = json.dumps(k6._plain(result), sort_keys=True, indent=2, allow_nan=False) + "\n"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8", newline="\n")
    loaded: dict[str, Any] = json.loads(text)
    return loaded


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="R4 neighbourhood kept in a 5D perspective.")
    parser.add_argument("--out", type=Path, default=RESULT, help=f"result path (default: {RESULT})")
    out_path: Path = parser.parse_args(argv).out
    result = run(EMBEDDINGS, LABELS, AXES, K6_RESULT, EXPECTED_DIGESTS, out_path)
    print(
        f"R4: valid={result['valid']} holds={result['r4_holds']} "
        f"dimension={result['dimension']} -> {out_path}"
    )
    if not result["valid"]:
        raise SystemExit(f"R4 invalid, no result is used: {result['failed_conditions']}")


if __name__ == "__main__":
    main()
