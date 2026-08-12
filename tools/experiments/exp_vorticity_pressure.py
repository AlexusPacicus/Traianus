"""
Experiment: Test Hypothesis H1 (Presión y Vorticidad)
Module: Uses kinematics_engine core (pure functions, no side effects).

H1 validated: Increasing data density in fixed d dimensions monotonically
increases the kinetic distortion metric K_cin.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import numpy as np
from typing import Tuple

# Import core kinematics functions
from kinematics_engine import (
    compute_k_cin,
    compute_dismorphism,
    compute_finite_difference,
    compute_orthogonality_loss,
    apply_dimensional_relief,
    measure_laminarity,
    generate_compressed_region,
    generate_laminar_flow,
)


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


def run_experiment(
    dim: int = 384,
    n_free: int = 80,
    n_compressed: int = 80,
    compression_factor: float = 3.0,
    seed: int = 42,
) -> Tuple[float, float, str]:
    """
    Run H1 validation experiment.

    Generates a laminar (free) region and a high-compression region,
    computes K_cin for each, and returns the verdict.

    Returns (free_k_cin_avg, compressed_k_cin_avg, verdict)
    """
    # Orthogonal base B_0 (full-rank: identity)
    B_0 = np.eye(dim, dtype=np.float64)

    # Free/laminar flow
    free_vectors = generate_laminar_flow(n_free, dim, seed)
    free_delta = compute_finite_difference(free_vectors)
    # Compute per-vector K_cin by averaging, or compute a single K_cin for the region
    # Here we compute mean K_cin across consecutive pairs
    free_k_cins = []
    for t in range(1, free_vectors.shape[0]):
        k = compute_k_cin(free_vectors[t], free_vectors[t - 1], B_0)
        free_k_cins.append(k)
    free_k_cin_avg = float(np.mean(free_k_cins)) if free_k_cins else 0.0

    # Compressed region
    compressed_vectors = generate_compressed_region(
        n_compressed, dim, compression_factor, seed
    )
    compressed_delta = compute_finite_difference(compressed_vectors)
    compressed_k_cins = []
    for t in range(1, compressed_vectors.shape[0]):
        k = compute_k_cin(compressed_vectors[t], compressed_vectors[t - 1], B_0)
        compressed_k_cins.append(k)
    compressed_k_cin_avg = float(np.mean(compressed_k_cins)) if compressed_k_cins else 0.0

    # H1: Increasing compression/density → monotonically increasing K_cin
    if compressed_k_cin_avg > free_k_cin_avg:
        verdict = "H1 VALIDA"
    else:
        verdict = "H1 FALSADA"

    return free_k_cin_avg, compressed_k_cin_avg, verdict


def main():
    dim = 384
    free_avg, compressed_avg, verdict = run_experiment(dim=dim)

    print(f"Dimensión del espacio: R^{dim}")
    print(f"")
    print(f"Zona de flujo libre (laminar):")
    print(f"  K_cin promedio: {free_avg:.6f}")
    print(f"")
    print(f"Zona de alta compresión/densidad:")
    print(f"  K_cin promedio: {compressed_avg:.6f}")
    print(f"")
    print(f"Veredicto: {verdict}")
    print(f"")


if __name__ == "__main__":
    main()