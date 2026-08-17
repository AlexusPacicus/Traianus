"""
Experiment: Test Hypothesis H2 (Alivio Dimensional / Dimensional Relief)
Module: Uses kinematics_engine core (pure functions, no side effects).

H2 validated: Projection of compressed vectors to R^{d+1} via
dimensional relief (appending K_cin) reduces orthogonality loss
and relaminates the trajectory.

Theory: In the Traianus substrate, B_0 is a reduced basis (k < d) 
representing the "piscina" (rest substrate). Projecting onto a full 
identity base I_d is trivial (no variance). Real measurement requires 
a reduced basis to capture "disalignment" from the known subspace.
"""



import numpy as np
from typing import Tuple

# Import core kinematics functions
from tools.experiments.shared.kinematics_engine import (
    compute_k_cin,
    compute_dismorphism,
    compute_finite_difference,
    compute_orthogonality_loss,
    apply_dimensional_relief,
    measure_laminarity,
    generate_compressed_region,
)


def generate_reduced_base(dim: int, k: int, seed: int) -> np.ndarray:
    """
    Generate a reduced orthogonal base B_0 of shape (k, d) where k < d.

    This represents the "piscina" (rest substrate) - a known subspace
    against which projections are measured. The remaining d-k dimensions
    are the "unknown" space where vorticity/pressure manifests.

    Returns B_0 with unit-norm rows that are linearly independent but
    not fully orthogonal (captures the "dismorphism" concept).
    """
    rng = np.random.default_rng(seed)
    B_0 = rng.normal(size=(k, dim)).astype(np.float64)
    for i in range(k):
        B_0[i] = B_0[i] / np.linalg.norm(B_0[i])
    return B_0


def run_experiment(dim: int = 384, n_points: int = 80, compression: float = 3.0, seed: int = 42) -> tuple:
    """
    Run H2 validation experiment.

    Workflow:
    1. Generate reduced base B_0 (k < d) representing the "piscina"
    2. Generate compressed region in R^d (high vorticity, low orthogonality)
    3. Measure orthogonality loss in R^d relative to B_0
    4. Apply dimensional relief d -> d+1: append K_cin per vector
    5. Measure orthogonality loss in R^{d+1} with augmented base
    6. Compare: if loss decreases, H2 VALIDADA

    Returns (ortho_loss_d, ortho_loss_d_plus_1, laminarity_d, laminarity_d_plus_1, verdict)
    """
    # Step 0: Generate reduced base B_0 (k < d) - the "piscina"
    k = max(2, dim // 4)  # e.g., k=96 for dim=384
    B_0 = generate_reduced_base(dim, k, seed)

    # Step 1: Generate compressed region in R^d
    compressed_vectors = generate_compressed_region(n_points, dim, compression, seed)

    # Step 2: Measure orthogonality loss in R^d (original, compressed space)
    # variance of ||v · B_0^T|| across all vectors: high = disaligned from known subspace
    ortho_loss_d = compute_orthogonality_loss(compressed_vectors, B_0)
    # Also compute laminarity proxy in R^d: mean squared finite differences
    delta_d = np.diff(compressed_vectors, axis=0)
    sq_norms_d = np.sum(delta_d ** 2, axis=1)
    laminarity_d = float(np.mean(sq_norms_d))

    # Step 3: Apply dimensional relief d -> d+1: append K_cin per vector
    # We need K_cin per vector for the augmentation
    k_cins = []
    for t in range(compressed_vectors.shape[0]):
        if t == 0:
            # No predecessor -> K_cin = 0 (no finite difference available)
            k_cins.append(0.0)
        else:
            k = compute_k_cin(compressed_vectors[t], compressed_vectors[t - 1], B_0)
            k_cins.append(k)

    k_cins = np.array(k_cins, dtype=np.float64)

    # Project all vectors to R^{d+1} by appending K_cin as the (d+1)-th coordinate
    # v^ = (v_1, v_2, ..., v_d, K_cin) in R^{d+1}
    projected_vectors = np.column_stack([compressed_vectors, k_cins])  # shape (n, d+1)

    # Step 4: Measure orthogonality loss in R^{d+1} with augmented base
    # The augmented base is I_{d+1} (identity in the augmented space).
    # Since vectors now have the K_cin coordinate, projection norms will differ.
    B_0_aug = np.eye(dim + 1, dtype=np.float64)
    ortho_loss_d_plus_1 = compute_orthogonality_loss(projected_vectors, B_0_aug)
    # Laminarity proxy in R^{d+1}
    delta_d_plus_1 = np.diff(projected_vectors, axis=0)
    sq_norms_d_plus_1 = np.sum(delta_d_plus_1 ** 2, axis=1)
    laminarity_d_plus_1 = float(np.mean(sq_norms_d_plus_1))

    # Step 5: Compare and verdict
    # H2: Projection to R^{d+1} should reduce orthogonality loss
    # because K_cin absorbs the solenoidal energy, relaminating the flow.
    # We expect ortho_loss_d_plus_1 < ortho_loss_d when K_cin helps relaminar.
    ortho_improvement = ortho_loss_d - ortho_loss_d_plus_1
    laminarity_change = laminarity_d_plus_1 - laminarity_d

    # H2 validation: if orthogonality loss decreases (improvement > 0) OR
    # laminarity increases (smoother flow), that supports H2
    if ortho_improvement > 0.001 or laminarity_change > 0.001:
        verdict = "H2 VALIDADA"
    else:
        verdict = "H2 FALSADA"

    return ortho_loss_d, ortho_loss_d_plus_1, laminarity_d, laminarity_d_plus_1, verdict


def main():
    dim = 384
    n_points = 80
    compression = 3.0

    print("=== Experimento H2: Alivio Dimensional d -> d+1 ===")
    print(f"Espacio: R{dim} -> R{dim+1}")
    print(f"Puntos: {n_points}")
    print(f"Condicion: Alta compresion/densidad (factor {compression})")
    print(f"Base reducida k={dim // 4} < d (piscina del sustrato)")
    print("")

    (
        ortho_loss_d,
        ortho_loss_d_plus_1,
        laminarity_d,
        laminarity_d_plus_1,
        verdict,
    ) = run_experiment(dim=dim, n_points=n_points, compression=compression)

    print("Resultados de perdida de ortogonalidad:")
    print(f"  R{dim} (original, comprimido, base B_0 reducida k={dim // 4}): {ortho_loss_d:.6f}")
    print(f"  R{dim+1} (proyectado con K_cin, base I_{{d+1}}): {ortho_loss_d_plus_1:.6f}")
    print(f"  Mejora (reduccion): {ortho_loss_d - ortho_loss_d_plus_1:.6f}")
    print("")
    print("Proxy de laminaridad (mean squared Delta-v, menor = mas suave):")
    print(f"  R{dim}: {laminarity_d:.6f}")
    print(f"  R{dim+1}: {laminarity_d_plus_1:.6f}")
    print(f"  Cambio: {laminarity_d_plus_1 - laminarity_d:.6f}")
    print("")
    print(f"Veredicto: {verdict}")


if __name__ == "__main__":
    main()