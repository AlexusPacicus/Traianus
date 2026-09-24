"""K8 — predictability of the orthogonalised second dipole.

Implements docs/methodology/instrument-audit/K8.md (instrument audit record, revision 3) against
docs/methodology/instrument-audit/contracts.md (§0 data layer, §3 K8) and
docs/methodology/instrument-audit/derivations.md (D13-D16).

The second colour dipole w_2 is orthogonalised against S = span{c1_hat, w_1, w_3, p_8} (the four
directions the map already shows); the remaining direction u, normalised, is the candidate z. Its
centred R^2 on K6's step-3 basis is compared with 1,000 null directions uniform in S-perp; z is
admissible iff it is no more predictable than the 951st smallest of those null R^2 values.

Refuses to run unless the four data digests and the two pinned code digests match, and unless
validate_inputs accepts the artefacts.

Usage:
    python3 tools/experiments/k8_orthogonal_dipole.py [--out PATH]
"""

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_var] = "1"

import argparse
import json
import platform
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
from numpy.typing import NDArray

from tools.experiments.k6_colour_predictability import (
    build_frame,
    calibration_control,
    channels_along,
    check_digests,
    design_basis,
    draw_deciding_null,
    draw_sigma_null,
    eval_channels,
    load_inputs,
    make_rng,
    ols_fit,
    r_squared,
    rank_axes,
    split_fit_eval,
    validate_inputs,
    z_score,
)
from traianus.geometry.polar_projector import PolarProjector

REPO_ROOT = Path(__file__).resolve().parents[2]
EMBEDDINGS = REPO_ROOT / ".data" / "spinoza_frozen" / "embeddings.npy"
LABELS = REPO_ROOT / ".data" / "spinoza_frozen" / "labels.json"
AXES = REPO_ROOT / "tests" / "fixtures" / "nsm_axes_8.json"
K6_RESULT = REPO_ROOT / "data" / "refapp" / "K6_result.json"
K6_SCRIPT = REPO_ROOT / "tools" / "experiments" / "k6_colour_predictability.py"
POLAR_PROJECTOR = REPO_ROOT / "traianus" / "geometry" / "polar_projector.py"
RESULT = REPO_ROOT / "data" / "refapp" / "K8_result.json"

EXPECTED_DIGESTS = {
    EMBEDDINGS: "eafb0e97172830f2404e96fa08d74bf6cccc0b6cbe84d47b790a476603e7d8d1",
    LABELS: "1d60699353d810f089730c6203ee28f9c416e3004b60781bc965cec284097f4f",
    AXES: "b14e5d6700d1a7478a357ca26f0f38f5240f97a42daad45722d21f1c3f964e35",
    K6_RESULT: "a95ec2a01a14f9638c9fc01d1bc9f198f5c53e580636858a7690baf9539cac58",
    K6_SCRIPT: "6289c596792154f6bb799606265c68719c6b8c7ae8b69084116dfb23c77876d2",
    POLAR_PROJECTOR: "2049291a522e217855a902fff71fa099619a207acc1a827accfd414f180952b6",
}

SEED = 20260924
D = 384
N_NULL = 1000
TAU_INDEX = 950
RANK_SURVIVAL_TOL = 1e-6
ORTHOGONALITY_TOL = 1e-12
COND_MAX = 1e5
CONTROL_TOL = 1e-9
THREAD_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS")
EPS = float(np.finfo(np.float64).eps)
GAMMA_384 = D * (EPS / 2.0) / (1.0 - D * (EPS / 2.0))
REQUIRED_K6_SELECTION = ["lambda_3", "a_8", "none"]

STOP_IDENTIFIERS = (
    "k6_result_valid", "k6_selected_channels", "ranking_reproduced",
    "fallback_flags_agree", "fallback_none", "rank", "survival",
    "u_from_w2", "u_orthogonal", "nulls_orthogonal", "spread",
)
POST_SPREAD_IDENTIFIERS = (
    "cond_B", "d16_identity", "positive_control",
    "control_in_exact", "control_in_side", "control_out_exact", "control_out_side",
)
# Every figure contracts.md §3 Output lists under "when not stopped"; null on a stopped run.
NULL_FIGURE_KEYS = (
    "sigma_min_M", "sigma_max_M", "survival", "eta", "u_from_w2_deviation",
    "u_orthogonality_max", "u_norm_deviation", "nulls_orthogonality_max",
    "nulls_norm_deviation_max", "sd_z", "spread_bound", "cond_B", "basis_columns",
    "tau", "tau_sigma_reference", "r2_z", "adjusted_r2_z", "margin", "admissible",
    "fragility", "fragile", "positive_control", "control_in", "control_out",
    "d16_max_deviation", "descriptive",
)

Array = NDArray[np.float64]


# K6 result -----------------------------------------------------------------------------------


def parse_k6_result(data: bytes) -> dict[str, Any]:
    """K8's own parsing of the consumed K6 result (load_inputs parses the other three artefacts)."""
    payload = json.loads(data.decode("utf-8"))
    return {
        "valid": bool(payload["valid"]),
        "ranking_fit": list(payload["ranking_fit"]),
        "rankings_match": bool(payload["rankings_match"]),
        "fallback": dict(payload["fallback"]),
        "selected": [step["selected"] for step in payload["steps"]],
    }


# Direction in S-perp ---------------------------------------------------------------------------


def project_off(q: Array, w: Array) -> Array:
    """P_S-perp applied twice: w' = w - Q(Q^T w), then w' - Q(Q^T w') (D14, "twice is enough")."""
    first = w - q @ (q.T @ w)
    return first - q @ (q.T @ first)


def build_direction(m: Array, w2: Array) -> dict[str, Any]:
    """Q from numpy.linalg.qr(M); u = P_S-perp(w2) normalised, with the construction figures."""
    q, _ = np.linalg.qr(m)
    singular_values = np.linalg.svd(m, compute_uv=False)
    sigma_min, sigma_max = float(singular_values[-1]), float(singular_values[0])
    pw2 = project_off(q, w2)
    norm_pw2 = float(np.linalg.norm(pw2))
    norm_w2 = float(np.linalg.norm(w2))
    survival = norm_pw2 / norm_w2
    u = pw2 / norm_pw2 if norm_pw2 > 0.0 else pw2
    u_from_w2_deviation = abs(float(u @ w2) - norm_pw2)
    u_orthogonality_max = float(np.max(np.abs(m.T @ u)))
    u_norm_deviation = abs(float(np.linalg.norm(u)) - 1.0)
    return {
        "q": q, "sigma_min": sigma_min, "sigma_max": sigma_max, "u": u,
        "norm_w2": norm_w2, "norm_pw2": norm_pw2, "survival": survival,
        "u_from_w2_deviation": u_from_w2_deviation,
        "u_orthogonality_max": u_orthogonality_max,
        "u_norm_deviation": u_norm_deviation,
    }


def null_directions_in_complement(q: Array, g: Array) -> Array:
    """w0_i = P_S-perp(g_i) / ||P_S-perp(g_i)|| for each row g_i (D15)."""
    projected = np.array([project_off(q, row) for row in g])
    norms = np.linalg.norm(projected, axis=1, keepdims=True)
    return projected / norms


def null_orthogonality(m: Array, w0: Array) -> tuple[float, float]:
    """Max |<w0_i, s>| over columns s of M and i, and max |1 - ||w0_i||| over i."""
    orth_max = float(np.max(np.abs(w0 @ m)))
    norm_dev_max = float(np.max(np.abs(np.linalg.norm(w0, axis=1) - 1.0)))
    return orth_max, norm_dev_max


def assess_post_spread(flags: Mapping[str, bool]) -> tuple[bool, str | None, list[str]]:
    """valid, first_failed_condition and failed_conditions among the seven post-spread checks."""
    failed = [name for name in POST_SPREAD_IDENTIFIERS if not flags[name]]
    return not failed, (failed[0] if failed else None), failed


def _clip_fraction(u: Array) -> float:
    return float(np.mean(np.abs(u) > 1.0))


def threshold(r2_values: Array) -> float:
    """The 951st smallest of 1,000 R^2 values (D13, N = 1,000, j = 951)."""
    return float(np.sort(np.asarray(r2_values, dtype=np.float64))[TAU_INDEX])


# Measurement -----------------------------------------------------------------------------------


def measure(
    v: Array, a_hat: Array, axis_ids: Sequence[str], k6_result: Mapping[str, Any]
) -> dict[str, Any]:
    fit, ev = split_fit_eval(v.shape[0])
    order, _ = rank_axes(v[fit], a_hat, axis_ids)
    ranking_fit = [axis_ids[k] for k in order]

    checked: list[str] = []
    result: dict[str, Any] = {"rankings_match": bool(k6_result["rankings_match"])}

    def stop(identifier: str) -> dict[str, Any]:
        checked.append(identifier)
        result.update(
            stopped=True, valid=False, first_failed_condition=identifier,
            failed_conditions=[identifier], conditions_checked=list(checked),
        )
        for key in NULL_FIGURE_KEYS:
            result.setdefault(key, None)
        return result

    if not k6_result["valid"]:
        return stop("k6_result_valid")
    checked.append("k6_result_valid")

    if list(k6_result["selected"]) != REQUIRED_K6_SELECTION:
        return stop("k6_selected_channels")
    checked.append("k6_selected_channels")

    if ranking_fit != k6_result["ranking_fit"]:
        return stop("ranking_reproduced")
    checked.append("ranking_reproduced")

    projector = PolarProjector()
    frame = build_frame(a_hat, order, projector)
    fallback = {f"dipole_{j + 1}": bool(frame["fallback"][j]) for j in range(3)}
    if fallback != k6_result["fallback"]:
        return stop("fallback_flags_agree")
    checked.append("fallback_flags_agree")

    if any(frame["fallback"]):
        return stop("fallback_none")
    checked.append("fallback_none")

    c1_hat = frame["c1_hat"]
    w1 = frame["frames"][0].v_dipole
    w2 = frame["frames"][1].v_dipole
    w3 = frame["frames"][2].v_dipole
    p8 = frame["p8"]
    m = np.column_stack(
        [c1_hat, w1 / np.linalg.norm(w1), w3 / np.linalg.norm(w3), p8 / np.linalg.norm(p8)]
    )

    direction = build_direction(m, w2)
    result["sigma_min_M"] = direction["sigma_min"]
    result["sigma_max_M"] = direction["sigma_max"]
    if direction["sigma_min"] < RANK_SURVIVAL_TOL:
        return stop("rank")
    checked.append("rank")

    result["survival"] = direction["survival"]
    if direction["survival"] < RANK_SURVIVAL_TOL:
        return stop("survival")
    checked.append("survival")

    result["u_from_w2_deviation"] = direction["u_from_w2_deviation"]
    if direction["u_from_w2_deviation"] > ORTHOGONALITY_TOL * direction["norm_w2"]:
        return stop("u_from_w2")
    checked.append("u_from_w2")

    result["u_orthogonality_max"] = direction["u_orthogonality_max"]
    result["u_norm_deviation"] = direction["u_norm_deviation"]
    if (
        direction["u_orthogonality_max"] > ORTHOGONALITY_TOL
        or direction["u_norm_deviation"] > ORTHOGONALITY_TOL
    ):
        return stop("u_orthogonal")
    checked.append("u_orthogonal")

    rng = make_rng(SEED)
    g_deciding = draw_deciding_null(rng, N_NULL, D)
    v_eval = v[ev]
    x_c = v_eval - v_eval.mean(axis=0)
    g_sigma = draw_sigma_null(rng, x_c, N_NULL)

    q = direction["q"]
    w0_deciding = null_directions_in_complement(q, g_deciding)
    w0_sigma = null_directions_in_complement(q, g_sigma)
    orth_deciding, norm_dev_deciding = null_orthogonality(m, w0_deciding)
    orth_sigma, norm_dev_sigma = null_orthogonality(m, w0_sigma)
    result["nulls_orthogonality_max"] = {"deciding": orth_deciding, "sigma": orth_sigma}
    result["nulls_norm_deviation_max"] = {"deciding": norm_dev_deciding, "sigma": norm_dev_sigma}
    if (
        max(orth_deciding, orth_sigma) > ORTHOGONALITY_TOL
        or max(norm_dev_deciding, norm_dev_sigma) > ORTHOGONALITY_TOL
    ):
        return stop("nulls_orthogonal")
    checked.append("nulls_orthogonal")

    u = direction["u"]
    z = channels_along(v_eval, u[np.newaxis, :])[0]
    sd_z = float(np.std(z))
    max_norm_v_eval = float(np.max(np.linalg.norm(v_eval, axis=1)))
    spread_bound = GAMMA_384 * max_norm_v_eval
    result["sd_z"] = sd_z
    result["spread_bound"] = spread_bound
    if not (sd_z > spread_bound):
        return stop("spread")
    checked.append("spread")

    # Past the eleven stop conditions: every remaining figure is computed, whatever it shows.
    ch = eval_channels(v_eval, a_hat, frame, projector)
    x, y, lam2, lam3, a8, h = ch["x"], ch["y"], ch["lambda_2"], ch["lambda_3"], ch["a_8"], ch["h"]

    null_deciding_channels = channels_along(v_eval, w0_deciding)
    null_sigma_channels = channels_along(v_eval, w0_sigma)

    b, basis_columns = design_basis(x, y, [("lambda_3", lam3), ("a_8", a8)])
    cond_b = float(np.linalg.cond(b))
    cond_b_ok = cond_b <= COND_MAX

    r2_z, adj_r2_z = r_squared(z, b)
    deciding_r2 = np.array([r_squared(row, b)[0] for row in null_deciding_channels])
    sigma_r2 = np.array([r_squared(row, b)[0] for row in null_sigma_channels])
    tau = threshold(deciding_r2)
    tau_sigma_reference = threshold(sigma_r2)
    admissible = r2_z <= tau
    margin = r2_z - tau

    resid_z = z - ols_fit(z, b)
    resid_lam2 = lam2 - ols_fit(lam2, b)
    scale = (direction["norm_w2"] ** 2) / direction["norm_pw2"]
    d16_max_deviation = float(np.max(np.abs(resid_z - scale * resid_lam2)))
    d16_ok = d16_max_deviation <= CONTROL_TOL * sd_z

    r2_h, _ = r_squared(h, b)
    positive_control_ok = r2_h > tau

    n1 = null_deciding_channels[0]
    rho_in, rho_out = tau / 2.0, (1.0 + tau) / 2.0
    r2_in, _ = r_squared(calibration_control(h, n1, b, rho_in), b)
    r2_out, _ = r_squared(calibration_control(h, n1, b, rho_out), b)
    deviation_in, deviation_out = abs(r2_in - rho_in), abs(r2_out - rho_out)
    control_in_exact, control_in_side = deviation_in <= CONTROL_TOL, r2_in <= tau
    control_out_exact, control_out_side = deviation_out <= CONTROL_TOL, r2_out > tau

    valid, first_failed_post, failed_post = assess_post_spread({
        "cond_B": cond_b_ok, "d16_identity": d16_ok, "positive_control": positive_control_ok,
        "control_in_exact": control_in_exact, "control_in_side": control_in_side,
        "control_out_exact": control_out_exact, "control_out_side": control_out_side,
    })
    checked.extend(POST_SPREAD_IDENTIFIERS)

    eta = EPS * direction["sigma_max"] / (direction["sigma_min"] * direction["survival"])
    fragility = 4.0 * eta / sd_z
    fragile = fragility >= abs(margin)

    pearson_r = {
        name: float(np.mean(z_score(z) * z_score(channel)))
        for name, channel in (("x", x), ("y", y), ("lambda_3", lam3), ("a_8", a8))
    }
    null_sds = np.std(null_deciding_channels, axis=1)
    sd_z_rank_among_null_sd = int(np.sum(null_sds < sd_z)) + 1
    clip_fractions = {"x": _clip_fraction(x), "lambda_3": _clip_fraction(lam3)}

    result.update(
        eta=eta,
        cond_B=cond_b,
        basis_columns=basis_columns,
        tau=tau,
        tau_sigma_reference=tau_sigma_reference,
        r2_z=r2_z,
        adjusted_r2_z=adj_r2_z,
        margin=margin,
        admissible=(bool(admissible) if valid else None),
        fragility=fragility,
        fragile=bool(fragile),
        positive_control={"r2": r2_h, "tau": tau},
        control_in={"rho": rho_in, "r2": r2_in, "deviation": deviation_in},
        control_out={"rho": rho_out, "r2": r2_out, "deviation": deviation_out},
        d16_max_deviation=d16_max_deviation,
        descriptive={
            "pearson_r": pearson_r,
            "sd_z_rank_among_null_sd": sd_z_rank_among_null_sd,
            "clip_fractions": clip_fractions,
        },
        stopped=False,
        valid=bool(valid),
        first_failed_condition=first_failed_post,
        failed_conditions=failed_post,
        conditions_checked=list(checked),
    )
    return result


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
    embeddings: Path, labels: Path, axes: Path, k6_result: Path, k6_script: Path,
    polar_projector: Path, expected: Mapping[Path, str], out_path: Path,
) -> dict[str, Any]:
    raw = check_digests(expected)
    v32, label_list, axis_ids, a = load_inputs(
        raw[Path(embeddings)], raw[Path(labels)], raw[Path(axes)]
    )
    validate_inputs(v32, label_list, axis_ids, a)
    k6_res = parse_k6_result(raw[Path(k6_result)])
    v64 = v32.astype("<f8")
    v = np.array([row / np.sqrt(row @ row) for row in v64])
    a_hat = np.array([a_k / np.sqrt(a_k @ a_k) for a_k in a])
    result = measure(v, a_hat, axis_ids, k6_res)
    result["digests"] = {Path(p).name: d for p, d in expected.items()}
    result["environment"] = environment()
    text = json.dumps(_plain(result), sort_keys=True, indent=2, allow_nan=False) + "\n"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8", newline="\n")
    loaded: dict[str, Any] = json.loads(text)
    return loaded


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="K8 orthogonalised second dipole.")
    parser.add_argument("--out", type=Path, default=RESULT, help=f"result path (default: {RESULT})")
    out_path: Path = parser.parse_args(argv).out
    result = run(
        EMBEDDINGS, LABELS, AXES, K6_RESULT, K6_SCRIPT, POLAR_PROJECTOR, EXPECTED_DIGESTS, out_path
    )
    print(f"K8: valid={result['valid']} admissible={result.get('admissible')} -> {out_path}")


if __name__ == "__main__":
    main()
