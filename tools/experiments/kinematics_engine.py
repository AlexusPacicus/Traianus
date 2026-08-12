"""
Kinematics Engine — Módulo Core para Traianus

Funciones puras de álgebra lineal y dinámica de campos sobre R^d.
Todo está tipado y no tiene efectos secundarios (pure functions).
Diseñado para ser importado por runners modulares (H1, H2, H3).
"""

import numpy as np
from typing import Tuple, Optional


def compute_dismorphism(
    v: np.ndarray,
    B_0: np.ndarray,
) -> float:
    """
    Compute the local dismorphism (distortion) measure.

    Variance of the projection of vector v onto the orthogonal base B_0.

    Parameters
    ----------
    v : np.ndarray of shape (d,)
        Single data vector.
    B_0 : np.ndarray of shape (k, d)
        Orthogonal base matrix (k ≤ d), typically k = d (full rank).

    Returns
    -------
    float
        Variance of ||v · B_0^T|| across the projection space.
        Higher → more shearing/deformation from orthogonality.
    """
    projected = v @ B_0.T  # (k,)
    norms = np.linalg.norm(projected)  # single scalar if k=1, or array if k>1
    if norms.ndim == 0:
        # If B_0 has k rows and we get a scalar projection magnitude:
        # For unit vector v and full-rank B_0 = I, this should be 1.0
        return float(np.var(norms) if norms.ndim > 0 else 0.0)
    # norms is array of shape (k,) when v is (d,) and B_0 is (k, d)
    return float(np.var(norms))


def compute_k_cin(
    v_t: np.ndarray,
    v_prev: np.ndarray,
    B_0: np.ndarray,
) -> float:
    """
    Compute the kinetic resistance metric K_cin.

    K_cin = 0.5 * ||v_t - v_prev||^2 * (1 + dismorphism)

    Parameters
    ----------
    v_t : np.ndarray of shape (d,)
        Current vector in the trajectory.
    v_prev : np.ndarray of shape (d,)
        Previous vector in the trajectory.
    B_0 : np.ndarray of shape (k, d)
        Orthogonal base matrix.

    Returns
    -------
    float
        Scalar K_cin value measuring frictional work to re-assimilate the vortex.
    """
    delta_v = v_t - v_prev
    norm_sq = float(np.sum(delta_v ** 2))  # ||Δv||^2 (scalar for single pair)
    diss = compute_dismorphism(v_t, B_0)  # per-vector dismorphism
    return 0.5 * norm_sq * (1.0 + diss)


def apply_dimensional_relief(
    v: np.ndarray,
    k_cin: float,
) -> np.ndarray:
    """
    Apply dimensional relief mapping d → d+1.

    Maps v ∈ R^d to v̂ ∈ R^{d+1} by appending K_cin as the (d+1)-th coordinate:

    v̂ = (v_1, v_2, ..., v_d, K_cin)

    The (d+1)-th coordinate absorbs the solenoidal/kinetic energy,
    "unrolling" what was a vortex in d dimensions into a smooth
    orthogonal trajectory in d+1 dimensions.

    Parameters
    ----------
    v : np.ndarray of shape (d,)
        Input vector in d-dimensional space.
    k_cin : float
        Kinetic resistance metric computed via compute_k_cin.

    Returns
    -------
    np.ndarray of shape (d+1,)
        Augmented vector in (d+1)-dimensional space.
    """
    d = v.shape[0]
    result = np.empty(d + 1, dtype=np.float64)
    result[:d] = v.astype(np.float64, copy=False)
    result[d] = float(k_cin)
    return result


def compute_finite_difference(
    vectors: np.ndarray,
) -> np.ndarray:
    """
    Compute finite differences Δv_t = v_t - v_{t-1}.

    Parameters
    ----------
    vectors : np.ndarray of shape (n, d)
        Trajectory of n vectors in R^d.

    Returns
    -------
    np.ndarray of shape (n-1, d)
        Consecutive differences, excluding the first vector.
    """
    return np.diff(vectors, axis=0)


def compute_orthogonality_loss(
    V: np.ndarray,
    B_0: np.ndarray,
) -> float:
    """
    Measure the orthogonality loss of a set of vectors V relative to base B_0.

    Computes the variance of the projection norms ||v · B_0^T|| across all
    vectors in V. High variance → vectors are not well-aligned with the
    orthogonal structure → high dismorphism/energy dissipation.

    Parameters
    ----------
    V : np.ndarray of shape (n, d)
        Set of n vectors in R^d.
    B_0 : np.ndarray of shape (k, d)
        Orthogonal base matrix.

    Returns
    -------
    float
        Variance of projection magnitudes. Higher = more "disorthogonal".
    """
    # Project all vectors onto B_0: shape (n, k)
    projected = V @ B_0.T
    # Compute norm of each projection: shape (n,)
    norms = np.linalg.norm(projected, axis=1)
    return float(np.var(norms))


def measure_laminarity(
    V: np.ndarray,
) -> float:
    """
    Compute a laminarity proxy from a trajectory matrix.

    Average squared norm of consecutive differences:
    (1/(n-1)) * Σ ||v_t - v_{t-1}||^2

    Lower values → smoother trajectory, more laminar flow.

    Parameters
    ----------
    V : np.ndarray of shape (n, d)
        Trajectory of n vectors.

    Returns
    -------
    float
        Mean squared finite-difference magnitude.
    """
    diffs = np.diff(V, axis=0)
    sq_norms = np.sum(diffs ** 2, axis=1)
    return float(np.mean(sq_norms))


def generate_laminar_flow(
    n_points: int = 100,
    dim: int = 384,
    seed: int = 42,
) -> np.ndarray:
    """
    Generate a smooth laminar flow trajectory.

    In the laminar region, consecutive vectors vary slowly,
    producing low Δv and low K_cin.
    """
    rng = np.random.default_rng(seed)
    # Start with random unit vectors
    vectors = rng.normal(size=(n_points, dim))
    vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)

    # Apply smooth temporal coupling: each vector is a slight
    # perturbation of the previous one
    for t in range(1, n_points):
        vectors[t] = 0.9 * vectors[t - 1] + 0.1 * vectors[t]
        vectors[t] = vectors[t] / np.linalg.norm(vectors[t])

    return vectors


def generate_compressed_region(
    n_points: int = 100,
    dim: int = 384,
    compression: float = 3.0,
    seed: int = 42,
) -> np.ndarray:
    """
    Generate a high-compression/density region.

    High compression means consecutive vectors change rapidly,
    producing large Δv and high K_cin.
    """
    rng = np.random.default_rng(seed + 1000)
    # Start with random vectors
    vectors = rng.normal(size=(n_points, dim))

    # Apply strong high-frequency perturbations → large differences
    for t in range(1, n_points):
        perturbation = rng.normal(scale=compression, size=dim)
        vectors[t] = vectors[t - 1] + perturbation

    # Normalize to unit sphere (preserves directionality)
    vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors
    diffs = np.diff(V, axis=0)
    sq_norms = np.sum(diffs ** 2, axis=1)
    return float(np.mean(sq_norms))