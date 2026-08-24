"""Pure observational geometry (issue #48).

Observables over S^{d-1}: kinematic resistance K_cin, orthogonal residual
distance, discrimination ratio (H3), dimensional relief (H2), ε-adjacency
E_n (ADR-023/H5) and critical-threshold calibration (C1). All functions are
pure (numpy only, no side effects).
"""

import numpy as np


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
            for j, other in enumerate(vectors) if j != i
        ]
        if projections:
            base_variances.append(np.var(projections))
    return float(np.mean(base_variances)) if base_variances else 0.0


def compute_epsilon_edges(nodes: dict[str, np.ndarray], epsilon: float) -> list[dict]:
    """Pure ε-adjacency computation (ADR-023/H5, RE-08): no DB access.

    (v_i, v_j) ∈ E_n iff ||v_i − v_j||₂ ≤ epsilon. Deterministic: nodes are
    processed in sorted id order and edges are sorted by (source, target).
    """
    ids = sorted(nodes)
    edges: list[dict] = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            dist = float(np.linalg.norm(nodes[ids[i]] - nodes[ids[j]]))
            if dist <= epsilon:
                edges.append({
                    "source": ids[i],
                    "target": ids[j],
                    "distance": round(dist, 6),
                })
    edges.sort(key=lambda e: (e["source"], e["target"]))
    return edges


def project_dimensional_relief(v: np.ndarray, k_cin: float) -> np.ndarray:
    """Pure operator: map v ∈ R^d → v̂ ∈ R^{d+1} via dimensional relief.

    The K_cin scalar absorbs solenoidal/kinetic energy into the new coordinate,
    allowing the spectral variance to relaminate and the node to be evaluated
    with lower distortion on the augmented base B_0 ∈ R^{k × (d+1)}.

    Parameters
    ----------
    v : np.ndarray
        Input vector v ∈ R^d (first d coordinates).
    k_cin : float
        Kinematic resistance K_cin ∈ R (non-negative, typically K_cin ≥ 0).

    Returns
    -------
    np.ndarray
        Augmented vector v̂ ∈ R^{d+1} = (v_1, ..., v_d, K_cin).
    """
    v_hat = np.empty(v.shape[0] + 1, dtype=v.dtype)
    v_hat[:-1] = v
    v_hat[-1] = float(k_cin)
    return v_hat


def compute_kinetic_resistance(v_t: np.ndarray, v_prev: np.ndarray, B_0: np.ndarray) -> float:
    """Pure computation of kinematic resistance K_cin.

    K_cin(v_t, v_{t-1}, B_0) = 0.5 ||v_t - v_{t-1}||^2 ⋅ (1 + Var(v_t B_0^T)).

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

    Parameters
    ----------
    v : np.ndarray of shape (d,)
        Input vector in R^d.
    B_0 : np.ndarray of shape (k, d)
        Reduced base matrix (k < d), rows are orthogonal axes of the
        geodetic piscina.

    Returns
    -------
    float
        Squared norm ||v - v B_0^T B_0||^2.  Higher = more "outside".
    """
    # Project v onto B_0: coords = v @ B_0.T  (shape (k,))
    projected_coords = np.dot(v, B_0.T)  # shape (k,)
    # Reconstruct from projection: v_proj = B_0.T @ projected_coords  (shape (d,))
    # Since B_0 is (k, d), B_0.T is (d, k), so B_0.T @ projected_coords = (d,)
    v_proj = np.dot(B_0.T, projected_coords)  # shape (d,)
    # Residual (orthogonal component)
    residual = v - v_proj
    return float(np.linalg.norm(residual) ** 2)


def discrimination_ratio(
    v_t: np.ndarray,
    v_prev: np.ndarray,
    B_0: np.ndarray,
    epsilon: float = 1e-12,
) -> float:
    """Pure operator: discrimination ratio for H3 novelty classification.

    ortho_distance / K_cin.  High ratio  → structural novelty (smooth
    rotation outside B_0, low kinetic resistance).  Low ratio    → transitory
    noise (high kinetic energy but within the known sub‑space).

    Parameters
    ----------
    v_t : np.ndarray of shape (d,)
        Current vector in the trajectory.
    v_prev : np.ndarray of shape (d,)
        Preceding vector.
    B_0 : np.ndarray of shape (k, d)
        Reduced geodetic base.
    epsilon : float, optional
        Small value to avoid division‑zero when K_cin ≈ 0.

    Returns
    -------
    float
        Discrimination ratio = ortho_distance / K_cin.
        +inf if K_cin == 0.
    """
    k_cin = compute_kinetic_resistance(v_t, v_prev, B_0)
    od = ortho_distance(v_t, B_0)
    if k_cin < epsilon:
        return float(od / epsilon)  # avoid div‑0; very high ratio
    return float(od / k_cin)
