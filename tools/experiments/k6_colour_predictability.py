"""K6 — colour channel predictability.

Implements frontend/audits/K6.md (instrument audit record, revision 5) against
frontend/audits/contracts.md (§0 data layer, §1 K6) and frontend/audits/derivations.md.
For each colour candidate, the centred R² of an OLS fit on B_s = (1, x, y, x², y², xy,
c_1 … c_{s−1}) over the EVAL half is compared with the 989th smallest R² of 1,000 null
directions uniform in ĉ₁⊥; candidates are selected sequentially, with a positive control and
exact-R² calibration controls at every step.

Refuses to run unless the three input digests match; never runs on anything else.

Usage:
    python3 tools/experiments/k6_colour_predictability.py
"""

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_var] = "1"

import hashlib  # noqa: E402
import json  # noqa: E402
import math  # noqa: E402
import platform  # noqa: E402
from collections.abc import Mapping, Sequence  # noqa: E402
from pathlib import Path  # noqa: E402
from typing import Any  # noqa: E402

import numpy as np  # noqa: E402
from numpy.typing import NDArray  # noqa: E402

from traianus.geometry.polar_projector import PolarProjector  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
EMBEDDINGS = REPO_ROOT / ".data" / "spinoza_frozen" / "embeddings.npy"
LABELS = REPO_ROOT / ".data" / "spinoza_frozen" / "labels.json"
AXES = REPO_ROOT / "tests" / "fixtures" / "nsm_axes_8.json"
RESULT = REPO_ROOT / "data" / "refapp" / "K6_result.json"
EXPECTED_DIGESTS = {
    EMBEDDINGS: "eafb0e97172830f2404e96fa08d74bf6cccc0b6cbe84d47b790a476603e7d8d1",
    LABELS: "1d60699353d810f089730c6203ee28f9c416e3004b60781bc965cec284097f4f",
    AXES: "b14e5d6700d1a7478a357ca26f0f38f5240f97a42daad45722d21f1c3f964e35",
}

SEED = 20260918
D = 384
N_AXES = 8
N_NULL = 1000
TAU_INDEX = 988
NORM_TOL = 3e-5
COND_MAX = 1e5
CONTROL_TOL = 1e-9
N_STEPS = 3
THREAD_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")

Array = NDArray[np.float64]


class IntegrityError(ValueError):
    """An input artefact does not match its recorded sha256."""


# Integrity ----------------------------------------------------------------------------------------


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_digests(expected: Mapping[Path, str]) -> None:
    for path, digest in expected.items():
        actual = sha256_file(path)
        if actual != digest:
            raise IntegrityError(f"sha256 mismatch for {path}: expected {digest}, got {actual}")


def load_inputs(
    embeddings: Path, labels: Path, axes: Path
) -> tuple[NDArray[np.float32], list[Any], list[str], Array]:
    v32 = np.load(embeddings, allow_pickle=False)
    label_list = json.loads(Path(labels).read_text(encoding="utf-8"))
    axis_list = json.loads(Path(axes).read_text(encoding="utf-8"))
    axis_ids = [a["id"] for a in axis_list]
    a = np.array([a["vector"] for a in axis_list], dtype=np.float64)
    return v32, label_list, axis_ids, a


def validate_inputs(v32: NDArray[Any], labels: list[Any], axis_ids: list[str], a: Array) -> None:
    """Null elimination (contracts.md §0); raises ValueError naming the row or key."""
    v = np.asarray(v32, dtype=np.float64)
    if v.ndim != 2 or v.shape[1] != D:
        raise ValueError(f"embeddings must have shape (n, {D}), got {v.shape}")
    for i, row in enumerate(v):
        if not np.all(np.isfinite(row)):
            raise ValueError(f"row {i}: non-finite value")
        norm = math.sqrt(float(row @ row))
        if abs(norm - 1.0) > NORM_TOL:
            raise ValueError(f"row {i}: norm {norm!r} outside 1 ± {NORM_TOL}")
    if len(labels) != v.shape[0]:
        raise ValueError(f"label count {len(labels)} != row count {v.shape[0]}")
    seen: dict[str, int] = {}
    for i, item in enumerate(labels):
        if not isinstance(item, dict):
            raise ValueError(f"label {i}: not an object")
        for key in ("label", "part"):
            value = item.get(key)
            if not isinstance(value, str) or value == "":
                raise ValueError(f"label {i}: {key} is null or empty")
        if item["label"] in seen:
            raise ValueError(f"label {i}: duplicate of label {seen[item['label']]}")
        seen[item["label"]] = i
    a = np.asarray(a, dtype=np.float64)
    if len(axis_ids) != N_AXES or a.ndim != 2 or a.shape[0] != N_AXES:
        raise ValueError(f"expected {N_AXES} axes, got {len(axis_ids)} ids and shape {a.shape}")
    if a.shape[1] != D:
        raise ValueError(f"each axis must have {D} values, got {a.shape[1]}")
    for axis_id, row in zip(axis_ids, a):
        if not np.all(np.isfinite(row)):
            raise ValueError(f"axis {axis_id}: non-finite value")
        if not float(row @ row) > 0.0:
            raise ValueError(f"axis {axis_id}: zero norm")


# Random streams -----------------------------------------------------------------------------------


def make_rng(seed: int = SEED) -> np.random.Generator:
    return np.random.Generator(np.random.PCG64(seed))


def draw_deciding_null(rng: np.random.Generator, n_null: int, d: int) -> Array:
    return np.array([rng.standard_normal(d) for _ in range(n_null)])


def draw_sigma_null(rng: np.random.Generator, x_c: Array, n_null: int) -> Array:
    n = x_c.shape[0]
    return np.array([x_c.T @ rng.standard_normal(n) / np.sqrt(n) for _ in range(n_null)])


# Geometry -----------------------------------------------------------------------------------------


def perp(x: Array, c1_hat: Array) -> Array:
    return x - np.multiply.outer(x @ c1_hat, c1_hat)


def null_directions(g: Array, c1_hat: Array) -> Array:
    p = perp(g, c1_hat)
    return p / np.linalg.norm(p, axis=1, keepdims=True)


def channels_along(v: Array, directions: Array) -> Array:
    return np.array([v @ w / (w @ w) for w in directions])


def split_fit_eval(n: int) -> tuple[NDArray[np.intp], NDArray[np.intp]]:
    return np.arange(0, n, 2), np.arange(1, n, 2)


def rank_axes(v: Array, a_hat: Array, axis_ids: Sequence[str]) -> tuple[list[int], Array]:
    means = np.array([float(np.mean(v @ a_k)) for a_k in a_hat])
    order = sorted(range(len(axis_ids)), key=lambda k: (-means[k], axis_ids[k]))
    return order, means


def build_frame(a_hat: Array, order: Sequence[int], projector: PolarProjector) -> dict[str, Any]:
    c1 = a_hat[order[0]]
    frames, fallback = [], []
    for j in range(3):
        c_a, c_b = a_hat[order[2 * j + 1]], a_hat[order[2 * j + 2]]
        frame = projector.prepare(c1, c_a, c_b)
        gap = np.linalg.norm(perp(c_a, frame.c1_hat) - perp(c_b, frame.c1_hat))
        fallback.append(bool(gap < projector.eps_collinear))
        frames.append(frame)
    c1_hat = frames[0].c1_hat
    return {
        "c1_hat": c1_hat,
        "frames": frames,
        "fallback": fallback,
        "p8": perp(a_hat[order[7]], c1_hat),
    }


def candidate_names(fallback: Sequence[bool]) -> list[str]:
    names = [name for name, fb in (("lambda_2", fallback[1]), ("lambda_3", fallback[2])) if not fb]
    return names + ["a_8", "l"]


def eval_channels(
    v: Array, a_hat: Array, frame: dict[str, Any], projector: PolarProjector
) -> dict[str, Array]:
    f1, f2, f3 = frame["frames"]
    p8 = frame["p8"]
    return {
        "x": v @ f1.v_dipole / f1.v_dipole_norm_sq,
        "y": v @ frame["c1_hat"],
        "lambda_2": v @ f2.v_dipole / f2.v_dipole_norm_sq,
        "lambda_3": v @ f3.v_dipole / f3.v_dipole_norm_sq,
        "a_8": v @ p8 / (p8 @ p8),
        "l": 1.0 / (1.0 + np.var(v @ a_hat.T, axis=1, ddof=0)),
        "h": np.array([math.tanh(projector.evaluate(row, f1, 0)[2]) for row in v]),
    }


# Regression ---------------------------------------------------------------------------------------


def threshold(r2_values: Array) -> float:
    return float(np.sort(np.asarray(r2_values, dtype=np.float64))[TAU_INDEX])


def _stack(x: Array, y: Array, selected: Sequence[tuple[str, Array]]) -> tuple[Array, list[str]]:
    cols = [np.ones_like(x), x, y, x**2, y**2, x * y] + [u for _, u in selected]
    names = ["1", "x", "y", "x^2", "y^2", "xy"]
    names += [f"c_{j}:{name}" for j, (name, _) in enumerate(selected, start=1)]
    return np.column_stack(cols), names


def design_basis(
    x: Array, y: Array, selected: Sequence[tuple[str, Array]]
) -> tuple[Array, list[str]]:
    return _stack(x, y, selected)


def ols_fit(u: Array, b: Array) -> Array:
    beta, *_ = np.linalg.lstsq(b, u, rcond=None)
    fitted: Array = b @ beta
    return fitted


def r_squared(u: Array, b: Array) -> tuple[float, float]:
    """Centred R² and adjusted R² of the OLS fit of u on b (b includes the constant)."""
    u = np.asarray(u, dtype=np.float64)
    dev = u - u.mean()
    ss_tot = float(dev @ dev)
    if ss_tot == 0.0:
        raise ValueError("constant response: SS_tot = 0")
    res = u - ols_fit(u, b)
    r2 = 1.0 - float(res @ res) / ss_tot
    n, k = b.shape
    return r2, 1.0 - (1.0 - r2) * (n - 1) / (n - k)


def z_score(u: Array) -> Array:
    return (u - u.mean()) / u.std()


def calibration_control(h: Array, n1: Array, b: Array, rho: float) -> Array:
    """m_ρ = a·z(ĥ) + b·z(n⊥), a²/(a² + b²) = ρ; R²(m_ρ; b) = ρ exactly (D7)."""
    h_hat = ols_fit(z_score(h), b)
    n_perp = n1 - ols_fit(n1, b)
    return math.sqrt(rho) * z_score(h_hat) + math.sqrt(1.0 - rho) * z_score(n_perp)


# Selection ----------------------------------------------------------------------------------------


def run_selection(
    x: Array,
    y: Array,
    candidates: Sequence[tuple[str, Array]],
    null_deciding: Array,
    null_sigma: Array,
    h: Array,
) -> dict[str, Any]:
    remaining = list(candidates)
    selected: list[tuple[str, Array]] = []
    steps: list[dict[str, Any]] = []
    positive: dict[str, Any] | None = None
    for s in range(1, N_STEPS + 1):
        if not remaining:
            steps.append({"step": s, "ran": False, "reason": "no remaining candidate", "selected": "none"})
            continue
        b, cols = design_basis(x, y, selected)
        b_std, _ = _stack(z_score(x), z_score(y), selected)
        cond = float(np.linalg.cond(b))
        tau = threshold(np.array([r_squared(u, b)[0] for u in null_deciding]))
        tau_sigma = threshold(np.array([r_squared(u, b)[0] for u in null_sigma]))

        records: list[dict[str, Any]] = []
        chosen: tuple[str, Array] | None = None
        not_reached: list[tuple[str, Array]] = []
        for name, u in remaining:
            if chosen is not None:
                records.append({"name": name, "outcome": "not_reached"})
                not_reached.append((name, u))
                continue
            r2, adj = r_squared(u, b)
            admitted = r2 <= tau
            records.append({
                "name": name,
                "outcome": "selected" if admitted else "discarded",
                "r2": r2,
                "adj_r2": adj,
                "margin": r2 - tau,
            })
            if admitted:
                chosen = (name, u)
        remaining = not_reached

        if s == 1:
            r2_h, adj_h = r_squared(h, b)
            positive = {
                "r2": r2_h, "adj_r2": adj_h, "tau_1": tau, "margin": r2_h - tau, "passes": r2_h > tau,
            }

        controls = {}
        for side, rho, admissible in (("in", tau / 2, True), ("out", (1 + tau) / 2, False)):
            r2_m, _ = r_squared(calibration_control(h, null_deciding[0], b, rho), b)
            deviation = abs(r2_m - rho)
            controls[side] = {
                "rho": rho,
                "r2": r2_m,
                "deviation": deviation,
                "exact": deviation <= CONTROL_TOL,
                "expected_side": "admissible" if admissible else "not_admissible",
                "side_ok": (r2_m <= tau) if admissible else (r2_m > tau),
                "margin": r2_m - tau,
            }

        steps.append({
            "step": s,
            "ran": True,
            "basis_columns": cols,
            "cond": cond,
            "cond_standardised": float(np.linalg.cond(b_std)),
            "cond_ok": cond <= COND_MAX,
            "tau": tau,
            "tau_sigma_reference": tau_sigma,
            "candidates": records,
            "selected": chosen[0] if chosen else "none",
            "controls": controls,
        })
        if chosen is not None:
            selected.append(chosen)
    return {
        "steps": steps,
        "selected": [name for name, _ in selected],
        "constant_channels": N_STEPS - len(selected),
        "positive_control": positive,
    }


def assess_validity(
    fallback: Sequence[bool], selection: dict[str, Any]
) -> tuple[bool, str | None, list[str]]:
    failed = ["dipole_1_fallback"] if fallback[0] else []
    for step in selection["steps"]:
        if not step["ran"]:
            continue
        s = step["step"]
        if not step["cond_ok"]:
            failed.append(f"step_{s}_cond")
        if s == 1 and not selection["positive_control"]["passes"]:
            failed.append("positive_control")
        for side in ("in", "out"):
            control = step["controls"][side]
            if not control["exact"]:
                failed.append(f"step_{s}_control_{side}_exact")
            if not control["side_ok"]:
                failed.append(f"step_{s}_control_{side}_side")
    return not failed, (failed[0] if failed else None), failed


# Measurement --------------------------------------------------------------------------------------


def _clip_fraction(u: Array) -> float:
    return float(np.mean(np.abs(u) > 1.0))


def measure(
    v: Array, a_hat: Array, axis_ids: Sequence[str], rng: np.random.Generator, projector: PolarProjector
) -> dict[str, Any]:
    g = draw_deciding_null(rng, N_NULL, v.shape[1])
    fit, ev = split_fit_eval(v.shape[0])
    order_fit, means_fit = rank_axes(v[fit], a_hat, axis_ids)
    order_full, means_full = rank_axes(v, a_hat, axis_ids)
    frame = build_frame(a_hat, order_fit, projector)
    out: dict[str, Any] = {
        "n_fit": int(len(fit)),
        "n_eval": int(len(ev)),
        "ranking_fit": [axis_ids[k] for k in order_fit],
        "ranking_full": [axis_ids[k] for k in order_full],
        "rankings_match": order_fit == order_full,
        "means_fit": {axis_ids[k]: float(means_fit[k]) for k in range(len(axis_ids))},
        "means_full": {axis_ids[k]: float(means_full[k]) for k in range(len(axis_ids))},
        "fallback": {f"dipole_{j + 1}": fb for j, fb in enumerate(frame["fallback"])},
    }
    if frame["fallback"][0]:
        out.update(valid=False, first_failed_condition="dipole_1_fallback",
                   failed_conditions=["dipole_1_fallback"])
        return out

    v_eval = v[ev]
    ch = eval_channels(v_eval, a_hat, frame, projector)
    null_deciding = channels_along(v_eval, null_directions(g, frame["c1_hat"]))
    x_c = v_eval - v_eval.mean(axis=0)
    null_sigma = channels_along(v_eval, null_directions(draw_sigma_null(rng, x_c, N_NULL), frame["c1_hat"]))
    candidates = [(name, ch[name]) for name in candidate_names(frame["fallback"])]
    selection = run_selection(ch["x"], ch["y"], candidates, null_deciding, null_sigma, ch["h"])
    valid, first, failed = assess_validity(frame["fallback"], selection)
    out.update(selection)
    out.update(
        valid=valid,
        first_failed_condition=first,
        failed_conditions=failed,
        clip_fractions={
            "x": _clip_fraction(ch["x"]),
            "lambda_2": _clip_fraction(ch["lambda_2"]),
            "lambda_3": _clip_fraction(ch["lambda_3"]),
            "null_deciding": _clip_fraction(null_deciding),
            "null_sigma": _clip_fraction(null_sigma),
        },
    )
    return out


def environment() -> dict[str, Any]:
    return {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "numpy_config": np.show_config(mode="dicts"),
        "threads": {var: os.environ.get(var) for var in THREAD_VARS},
    }


def _plain(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_plain(v) for v in obj]
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, np.integer):
        return int(obj)
    if isinstance(obj, np.floating):
        return float(obj)
    return obj


def run(
    embeddings: Path, labels: Path, axes: Path, expected: Mapping[Path, str], out_path: Path
) -> dict[str, Any]:
    check_digests(expected)
    v32, label_list, axis_ids, a = load_inputs(embeddings, labels, axes)
    validate_inputs(v32, label_list, axis_ids, a)
    v64 = v32.astype("<f8")
    v = np.array([row / np.sqrt(row @ row) for row in v64])
    a_hat = np.array([a_k / np.sqrt(a_k @ a_k) for a_k in a])
    result = measure(v, a_hat, axis_ids, make_rng(), PolarProjector())
    result["digests"] = {Path(p).name: d for p, d in expected.items()}
    result["environment"] = environment()
    text = json.dumps(_plain(result), sort_keys=True, indent=2, allow_nan=False) + "\n"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8", newline="\n")
    loaded: dict[str, Any] = json.loads(text)
    return loaded


def main() -> None:
    result = run(EMBEDDINGS, LABELS, AXES, EXPECTED_DIGESTS, RESULT)
    print(f"K6: valid={result['valid']} selected={result.get('selected')} -> {RESULT}")


if __name__ == "__main__":
    main()
