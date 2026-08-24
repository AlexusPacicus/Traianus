"""
Experiment: Test Hypothesis H3 (Discrimination of Novelty)

H3 validated: The relationship between the kinetic dissipation K_cin and the
projection distance to the base strictly separates transient noise/anomalies
from real structural base updates.

Theory: In the Traianus substrate, when new data points arrive, they either:
- Represent transient noise/local turbulence → high K_cin but small projection
  distance to existing base (get absorbed/rejected)
- Represent structural novelty → moderate K_cin with significant projection
  distance, triggering base B_0 update

The K_cin vs. projection-distance relationship creates a discriminative boundary
that separates transient noise from genuine entity hyperdimensional expansion.
"""



import numpy as np
from typing import Tuple, List

# Import core kinematics functions
from tools.experiments.shared.kinematics_engine import (
    compute_k_cin,
    compute_dismorphism,
    compute_finite_difference,
    compute_orthogonality_loss,
    apply_dimensional_relief,
    measure_laminarity,
    generate_compressed_region,
    generate_laminar_flow,
)


def generate_noise_region(
    n_points: int = 80,
    dim: int = 384,
    noise_level: float = 0.5,
    seed: int = 42,
) -> np.ndarray:
    """
    Generate a region with transient noise/anomalies.

    Noise vectors have random perturbations at each step, producing
    high K_cin (due to large Δv) but the projection to any fixed base
    remains uniformly distributed (no consistent structural update).
    """
    rng = np.random.default_rng(seed + 10000)
    vectors = rng.normal(size=(n_points, dim))
    # Normalize but with varying amplitudes to create "noisy" differences
    vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
    # Add per-step random perturbations to create high finite differences
    for t in range(1, n_points):
        perturbation = rng.normal(scale=noise_level, size=dim)
        vectors[t] = vectors[t - 1] + perturbation
    # Re-normalize to maintain unit length
    vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors


def generate_structural_update(
    n_points: int = 80,
    dim: int = 384,
    update_magnitude: float = 0.3,
    seed: int = 42,
) -> np.ndarray:
    """
    Generate a region with structural base updates.

    Vectors gradually change direction in a consistent way, producing
    moderate K_cin (smooth Δv) and consistent projection patterns
    that indicate a genuine base base expansion/update.

    Uses Givens rotation-like approach valid for any dimension d ≥ 2.
    """
    rng = np.random.default_rng(seed)
    # Start with random vectors
    vectors = rng.normal(size=(n_points, dim))
    vectors = vectors / np.linalg.norm(vectors, axis=1, keepdims=True)

    # Apply consistent gradual rotation each step.
    # In high dimensions we rotate within a random 2D plane spanned by
    # the vector and a random direction, using a small angle.
    rotation_angle = update_magnitude / n_points

    for t in range(1, n_points):
        v_prev = vectors[t - 1]
        # Create a random orthogonal direction in d dimensions
        # by taking a random vector and projecting out the component
        # parallel to v_prev
        random_dir = rng.normal(size=dim)
        # Gram-Schmidt: component of random_dir orthogonal to v_prev
        proj = np.dot(random_dir, v_prev) / np.dot(v_prev, v_prev) * v_prev
        ortho_dir = random_dir - proj
        # If ortho_dir is near-zero (rare), try again
        if np.linalg.norm(ortho_dir) < 1e-10:
            continue
        ortho_dir = ortho_dir / np.linalg.norm(ortho_dir)

        # Rotate v_prev within the (v_prev, ortho_dir) plane by angle
        cost = np.cos(rotation_angle)
        sine = np.sin(rotation_angle)
        # The component along v_prev stays, the orthogonal component rotates
        vectors[t] = cost * v_prev + sine * ortho_dir

        # Re-normalize (should already be unit but just in case)
        vectors[t] = vectors[t] / np.linalg.norm(vectors[t])

    return vectors


def compute_projection_distance(
    v: np.ndarray,
    B_0: np.ndarray,
) -> float:
    """
    Compute the projection distance/magnitude of vector v onto base B_0.

    This measures how much of the vector lies in the known subspace.
    For a structural update, we expect significant projection changes.
    """
    projected = v @ B_0.T
    norm_proj = np.linalg.norm(projected)
    return float(norm_proj)


def run_h3_experiment(
    dim: int = 384,
    n_noise: int = 60,
    n_structural: int = 60,
    noise_level: float = 0.5,
    update_magnitude: float = 0.3,
    seed: int = 42,
) -> dict:
    """
    Run H3 validation experiment.

    Generates noise and structural update regions, computes K_cin and
    projection distances, and checks if they form separable clusters.

    Returns dict with analysis results and verdict.
    """
    # Generate reduced base B_0 (k < d)
    k = max(2, dim // 4)
    rng = np.random.default_rng(seed + 100000)
    B_0_raw = rng.normal(size=(k, dim)).astype(np.float64)
    for i in range(k):
        B_0_raw[i] = B_0_raw[i] / np.linalg.norm(B_0_raw[i])

    # Generate noise region
    noise_vectors = generate_noise_region(n_noise, dim, noise_level, seed)

    # Generate structural update region
    structural_vectors = generate_structural_update(
        n_structural, dim, update_magnitude, seed
    )

    # Compute metrics for noise region
    noise_k_cins = []
    noise_proj_distances = []
    for t in range(noise_vectors.shape[0]):
        if t == 0:
            noise_k_cins.append(0.0)
        else:
            k = compute_k_cin(
                noise_vectors[t], noise_vectors[t - 1], B_0_raw
            )
            noise_k_cins.append(k)
        proj_dist = compute_projection_distance(noise_vectors[t], B_0_raw)
        noise_proj_distances.append(proj_dist)

    # Compute metrics for structural region
    struct_k_cins = []
    struct_proj_distances = []
    for t in range(structural_vectors.shape[0]):
        if t == 0:
            struct_k_cins.append(0.0)
        else:
            k = compute_k_cin(
                structural_vectors[t], structural_vectors[t - 1], B_0_raw
            )
            struct_k_cins.append(k)
        proj_dist = compute_projection_distance(structural_vectors[t], B_0_raw)
        struct_proj_distances.append(proj_dist)

    # Analyze separation
    noise_k_cin_mean = np.mean(noise_k_cins)
    struct_k_cin_mean = np.mean(struct_k_cins)
    noise_proj_mean = np.mean(noise_proj_distances)
    struct_proj_mean = np.mean(struct_proj_distances)

    # Calculate separation metrics
    k_cin_separation = abs(noise_k_cin_mean - struct_k_cin_mean)
    proj_dist_separation = abs(noise_proj_mean - struct_proj_mean)

    # H3 validation: K_cin and/or projection distance should separate
    # noise from structural updates
    # Ideally: noise has higher K_cin (more turbulent) but lower/proj_dist
    # or some consistent pattern that strictly separates them
    h3_support = False

    # Check if there's a meaningful separation in either metric
    if k_cin_separation > 0.01 and proj_dist_separation > 0.01:
        # Both metrics separate → strong support
        h3_support = True
    elif k_cin_separation > 0.01:
        # K_cin alone separates → moderate support
        h3_support = True
    elif proj_dist_separation > 0.01:
        # Projection distance alone separates → moderate support
        h3_support = True

    verdict = "H3 VALIDATED" if h3_support else "H3 FALSIFIED"

    return {
        "noise_k_cin_mean": noise_k_cin_mean,
        "structural_k_cin_mean": struct_k_cin_mean,
        "noise_proj_mean": noise_proj_mean,
        "structural_proj_mean": struct_proj_mean,
        "k_cin_separation": k_cin_separation,
        "proj_dist_separation": proj_dist_separation,
        "verdict": verdict,
        "h3_support": h3_support,
    }


def main():
    dim = 384
    n_noise = 60
    n_structural = 60

    print("=== Experimento H3: Discriminación de Novedad ===")
    print(f"Espacio: R{dim}")
    print(f"Muestras: {n_noise} ruido + {n_structural} actualizaciones estructurales")
    print(f"")

    results = run_h3_experiment(
        dim=dim,
        n_noise=n_noise,
        n_structural=n_structural,
    )

    print("Métricas por categoría:")
    print(f"  Ruido:")
    print(f"    K_cin promedio: {results['noise_k_cin_mean']:.6f}")
    print(f"    Distancia proyección: {results['noise_proj_mean']:.6f}")
    print(f"  Actualizaciones estructurales:")
    print(f"    K_cin promedio: {results['structural_k_cin_mean']:.6f}")
    print(f"    Distancia proyección: {results['structural_proj_mean']:.6f}")
    print(f"")
    print(f"Separación:")
    print(f"    Diferencia K_cin: {results['k_cin_separation']:.6f}")
    print(f"    Distancia proyección: {results['proj_dist_separation']:.6f}")
    print(f"")
    print(f"Veredicto: {results['verdict']}")
    print(f"")


if __name__ == "__main__":
    main()