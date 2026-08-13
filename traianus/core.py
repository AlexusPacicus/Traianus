"""Pure decision and geometry kernel.

Deterministic, side-effect-free algorithms: the dual-key gate C1 and the
ε-adjacency / projection-variance geometry. This module has NO SQLite/FastAPI
dependencies (pure Python + numpy + math only). The persistence layer
(`traianus/storage.py`) and the HTTP layer (`traianus/app.py`) delegate the
mathematical computations here.
"""


import numpy as np


def evaluate_gate_v01(spectrum: list[float], ethical_key: bool, threshold: float) -> dict:
    """Evaluates the dual gate C1 for v0.1.

    The Topological Key acts as a provisional informational geometric score.
    The dual gate is preserved: consolidation requires BOTH keys
    simultaneously (Topological Key AND Ethical Key / HITL). Neither acts
    alone.
    """
    mean = sum(spectrum) / len(spectrum) if spectrum else 0.0
    variance = sum((x - mean) ** 2 for x in spectrum) / len(spectrum) if spectrum else 0.0

    topological_passed = variance >= threshold
    is_consolidated = topological_passed and ethical_key  # dual-key (AND)

    return {
        "state": "consolidated" if is_consolidated else "incubating",
        "topological_key": {
            "status": "PROVISIONAL_INFORMATIONAL_SCORE",
            "variance": variance,
            "threshold": threshold,
            "passed": topological_passed,
        },
        "ethical_key": ethical_key,
    }


def calibrate_critical_threshold(vectors: list[np.ndarray]) -> float:
    """Critical variance threshold on S^{d-1}, self-projections excluded.

    Cross projections only (j != i). Self-projection (dot == 1.0 for an
    L2-normalized axis) inflated the baseline to an unreachable scale for
    inputs, forcing the Topological Key to a 0% approval rate on real
    corpora (audit finding C1).
    """
    base_variances = []
    for i, axis_vector in enumerate(vectors):
        projections = [
            float(np.dot(axis_vector, other))
            for j, other in enumerate(vectors)
            if i != j
        ]
        if projections:
            base_variances.append(sum((p - sum(projections) / len(projections)) ** 2 for p in projections) / len(projections))
    return sum(base_variances) / len(base_variances) if base_variances else 0.0


def project_dimensional_relief(v: np.ndarray, k_cin: float) -> np.ndarray:
    """Pure operator: map v in R^d to v_hat in R^{d+1} via dimensional relief.

    The K_cin scalar absorbs solenoidal/kinetic energy into the new coordinate,
    allowing the spectral variance to relaminate and the node to be evaluated
    with lower distortion on the augmented base B_0 in R^{k × (d+1)}.

    Parameters
    ----------
    v : np.ndarray
        Input vector v in R^d (first d coordinates).
    k_cin : float
        Kinematic resistance K_cin in R (non-negative, typically K_cin >= 0).

    Returns
    -------
    np.ndarray
        Augmented vector v_hat in R^{d+1} = (v_1, ..., v_d, K_cin).
    """
    v_hat = np.empty(v.shape[0] + 1, dtype=v.dtype)
    v_hat[:-1] = v
    v_hat[-1] = float(k_cin)
    return v_hat


def compute_kinetic_resistance(v_t: np.ndarray, v_prev: np.ndarray, B_0: np.ndarray) -> float:
    """Pure computation of kinematic resistance K_cin.

    K_cin(v_t, v_{t-1}, B_0) = 0.5 ||v_t - v_{t-1}||^2 * (1 + Var(v_t B_0^T)).

    Parameters are pure (no mutable state). B_0 is the geodetic basis matrix
    (k × d) where each row is an axis vector; v_t B_0^T yields projection
    coordinates per axis, and Var() computes their variance.

    Returns a scalar float representing kinematic resistance.
    """
    delta = v_t - v_prev
    norm_delta2 = float(np.linalg.norm(delta) ** 2)
    projections = np.dot(v_t, B_0.T)  # shape (k,)
    projection_var = float(np.var(projections))  # scalar variance
    return 0.5 * norm_delta2 * (1.0 + projection_var)


def ortho_distance(v: np.ndarray, B_0: np.ndarray) -> float:
    """Pure operator: orthogonal residual distance from vector v to base B_0.

    Computes the squared L2-norm of the component of v orthogonal to all
    rows of B_0 (k × d matrix).  This is the "projection distance outside
    the piscina B_0" used by H3 discrimination.
    """
    return float(np.linalg.norm(v - np.dot(v, B_0.T) @ B_0))


def discrimination_ratio(v_t: np.ndarray, v_prev: np.ndarray, B_0: np.ndarray, epsilon: float = 1e-8) -> float:
    """Pure operator: discrimination ratio K_cin / ortho_distance.

    Used by H3 to separate transient noise from structural base updates.
    """
    k_cin = compute_kinetic_resistance(v_t, v_prev, B_0)
    od = ortho_distance(v_t, B_0)
    if k_cin < epsilon:
        return float(od / epsilon)  # avoid div‑0; very high ratio
    return float(od / k_cin)


