#!/usr/bin/env python3
"""EAS-01 Fase 1 — Sparse logographic probe over the 111-note control corpus."""
import argparse
import json
import os
import random
import re
import sys
import numpy as np


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)


from tools.experiments.shared._wp1_corpus import ALL_CATEGORIES, validate_corpus
from traianus.core import calibrate_critical_threshold


LOGOGRAMS: dict[str, tuple[str, ...]] = {
    "ContinuoSomatico": (
        "continuous", "continuum", "somatic", "indivisible", "organism", "embodied",
    ),
    "Metrica": (
        "metric", "distance", "norm", "l2", "normalized", "cosine", "epsilon",
    ),
    "Ortogonalidad": (
        "orthogonal", "orthogonality", "independent", "basis", "axis", "axes", "geodetic",
    ),
    "DespliegueDimensional": (
        "dimension", "dimensional", "expand", "expansion", "canonical", "hyperspace", "384d",
    ),
    "DobleLlave": (
        "consolidation", "consolidated", "consolidate", "dual-key", "ethical", "topological", "threshold",
    ),
    "AppendOnly": (
        "append-only", "immutable", "revision", "seq", "history", "insert", "overwrite",
    ),
    "FronteraDual": (
        "boundary", "perimeter", "ingress", "zero-trust", "reject", "token", "cors",
    ),
    "DispersionEspectral": (
        "variance", "dispersion", "spectral", "projection", "projections", "sigma", "spread",
    ),
    "SustratoDeterminista": (
        "deterministic", "determinism", "substrate", "reproducible", "algebraic", "vector", "vectors",
    ),
    "TopologiaManifold": (
        "manifold", "topology", "topological", "simplicial", "adjacency", "node", "nodes", "edges",
    ),
}


AXIS_NAMES: list[str] = list(LOGOGRAMS)
K = len(AXIS_NAMES)
TOKEN_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*")


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def build_sparse_basis(k: int = K) -> list[np.ndarray]:
    return [np.eye(k)[i] for i in range(k)]


def project_sparse(
    text: str,
    table: dict[str, tuple[str, ...]] | None = None,
) -> np.ndarray:
    table = table if table is not None else LOGOGRAMS
    names = list(table)
    lookup: dict[str, int] = {}
    for idx, name in enumerate(names):
        for form in table[name]:
            lookup[form] = idx
    alpha = np.zeros(len(names), dtype=np.float64)
    for tok in tokenize(text):
        idx = lookup.get(tok)
        if idx is not None:
            alpha[idx] += 1.0
    total = alpha.sum()
    return alpha / total if total > 0.0 else alpha


def charge(alpha: np.ndarray) -> float:
    return float(np.sum(np.abs(alpha)))


def spectral_variance(alpha: np.ndarray) -> float:
    return float(np.var(alpha))


def mannwhitney_u_p(x: list[float], y: list[float]) -> tuple[float, float]:
    nx, ny = len(x), len(y)
    if nx == 0 or ny == 0:
        return 0.5, 1.0
    combined = np.concatenate([np.asarray(x, float), np.asarray(y, float)])
    order = combined.argsort(kind="mergesort")
    ranks = np.empty(len(combined), dtype=np.float64)
    i = 0
    tie_term = 0.0
    while i < len(combined):
        j = i
        while j + 1 < len(combined) and combined[order[j + 1]] == combined[order[i]]:
            j += 1
        avg = 0.5 * (i + j) + 1.0
        for t in range(i, j + 1):
            ranks[order[t]] = avg
        run = j - i + 1
        tie_term += run**3 - run
        i = j + 1
    r1 = ranks[:nx].sum()
    u1 = r1 - nx * (nx + 1) / 2.0
    auc = u1 / (nx * ny)
    mu = nx * ny / 2.0
    n = nx + ny
    sigma_sq = (nx * ny / 12.0) * ((n + 1) - tie_term / (n * (n - 1))) if n > 1 else 0.0
    if sigma_sq <= 0.0:
        return auc, 1.0
    z = (u1 - mu) / np.sqrt(sigma_sq)
    p = 2.0 * (1.0 - _norm_cdf(abs(z)))
    return auc, float(min(1.0, max(0.0, p)))


def _norm_cdf(z: float) -> float:
    import math
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def cohens_d(x: list[float], y: list[float]) -> float:
    ax, ay = np.asarray(x, float), np.asarray(y, float)
    if len(ax) < 2 or len(ay) < 2:
        return 0.0
    pooled = np.sqrt((ax.var(ddof=1) + ay.var(ddof=1)) / 2.0)
    return float((ax.mean() - ay.mean()) / pooled) if pooled > 0 else 0.0


def measure(table: dict[str, tuple[str, ...]] | None = None) -> dict:
    out: dict[str, dict[str, list[float]]] = {}
    for label, paragraphs in ALL_CATEGORIES.items():
        rhos, sigmas = [], []
        for text in paragraphs:
            alpha = project_sparse(text, table)
            rhos.append(charge(alpha))
            sigmas.append(spectral_variance(alpha))
        out[label] = {"rho": rhos, "sigma2": sigmas}
    return out


def run_experiment(tau: float = 1e-12) -> dict:
    validate_corpus()
    basis = build_sparse_basis()
    gram = np.stack(basis) @ np.stack(basis).T
    off_diagonal = gram[~np.eye(K, dtype=bool)]
    theta_dyn = calibrate_critical_threshold(basis)
    measured = measure()
    stats: dict[str, dict] = {}
    for label, vals in measured.items():
        rho = np.asarray(vals["rho"])
        sig = np.asarray(vals["sigma2"])
        passed = (sig >= theta_dyn) & (rho >= tau)
        stats[label] = {
            "count": len(rho),
            "rho_mean": float(rho.mean()),
            "rho_var": float(rho.var()),
            "rho_zero_count": int(np.sum(rho == 0.0)),
            "sigma2_mean": float(sig.mean()),
            "sigma2_var": float(sig.var()),
            "consolidated_count": int(passed.sum()),
            "consolidation_rate": float(passed.mean()),
        }
    comparisons = {}
    for name, (l1, l2) in {"A_vs_B": ("A", "B"), "A_vs_C": ("A", "C")}.items():
        for metric in ("rho", "sigma2"):
            auc, p = mannwhitney_u_p(measured[l1][metric], measured[l2][metric])
            comparisons[f"{name}__{metric}"] = {
                "auc": auc,
                "p_value": p,
                "cohens_d": cohens_d(measured[l1][metric], measured[l2][metric]),
            }
    return {
        "basis": {
            "k": K,
            "axis_names": AXIS_NAMES,
            "off_diagonal_max": float(np.max(np.abs(off_diagonal))),
            "orthonormal": bool(np.allclose(gram, np.eye(K))),
        },
        "theta_dyn": theta_dyn,
        "tau": tau,
        "category_statistics": stats,
        "comparisons": comparisons,
        "controls": run_controls(tau),
    }


def run_controls(tau: float) -> dict:
    ctrl: dict = {}
    basis = build_sparse_basis()
    ctrl["theta_dyn_on_orthonormal_basis"] = calibrate_critical_threshold(basis)
    all_forms = [f for forms in LOGOGRAMS.values() for f in forms]
    rng = random.Random(0)
    shuffled = all_forms[:]
    rng.shuffle(shuffled)
    per = len(shuffled) // K
    scrambled = {
        f"RANDOM_{i}": tuple(shuffled[i * per:(i + 1) * per]) for i in range(K)
    }
    scr = measure(scrambled)
    ctrl["axis_scramble"] = {
        label: {
            "rho_mean": float(np.mean(v["rho"])),
            "rho_zero_count": int(np.sum(np.asarray(v["rho"]) == 0.0)),
        }
        for label, v in scr.items()
    }
    b_tokens: dict[str, int] = {}
    for text in ALL_CATEGORIES["B"]:
        for tok in tokenize(text):
            if len(tok) > 3:
                b_tokens[tok] = b_tokens.get(tok, 0) + 1
    top_b = [t for t, _ in sorted(b_tokens.items(), key=lambda kv: -kv[1])[:K * 6]]
    b_table = {f"B_{i}": tuple(top_b[i * 6:(i + 1) * 6]) for i in range(K)}
    swap = measure(b_table)
    ctrl["domain_swap_basis_from_catB"] = {
        label: {
            "rho_mean": float(np.mean(v["rho"])),
            "consolidated": int(np.sum(
                (np.asarray(v["sigma2"]) >= 0.0) & (np.asarray(v["rho"]) >= tau)
            )),
            "count": len(v["rho"]),
        }
        for label, v in swap.items()
    }
    attacks = [
        "purple elephant dancing on the ceiling of a submarine sandwich factory vector",
        "xyzqwk mnbvc lkjhg fdsap oiuyt rewq zx cvb nm manifold",
        "the square root of yesterday is blue and tastes like variance on toast",
        "colorless green ideas sleep furiously inside an append-only refrigerator",
    ]
    ctrl["adversarial"] = []
    for text in attacks:
        alpha = project_sparse(text)
        r, s = charge(alpha), spectral_variance(alpha)
        ctrl["adversarial"].append({
            "text": text,
            "rho": r,
            "sigma2": s,
            "consolidates": bool(s >= 0.0 and r >= tau),
        })
    return ctrl


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", default=False)
    parser.add_argument("--tau", type=float, default=1e-12)
    args = parser.parse_args()
    res = run_experiment(tau=args.tau)
    if args.json:
        print(json.dumps(res, indent=2, ensure_ascii=False))
    else:
        print(f"EAS-01 Fase 1 Sparse Logographic Probe complete. theta_dyn={res['theta_dyn']}")
