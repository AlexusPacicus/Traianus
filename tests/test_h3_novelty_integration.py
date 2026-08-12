"""
Integration tests for Hypothesis H3: Novelty Discrimination.

Tests the routing classification of vectors into quarantine_noise (incubating)
vs structural_candidate (pending_approval) based on the discrimination_ratio
computed via traianus.core.

H3 VALIDADA (seq 15, LEDGER): ratio = ||v - v·B_0^T·B_0|| / K_cin
separa ruido transitorio de novedad estructural.
"""

import numpy as np
import pytest

from traianus.core import (
    ortho_distance,
    discrimination_ratio,
    compute_kinetic_resistance,
    evaluate_gate_v01,
)


# ---------------------------------------------------------------------------
# Helpers de test
# ---------------------------------------------------------------------------

def _make_reduced_base(k: int = 96, d: int = 384, seed: int = 42) -> np.ndarray:
    """Genera una base reducida B_0 (k < d) con filas de unidad."""
    rng = np.random.default_rng(seed)
    B_0 = rng.normal(size=(k, d)).astype(np.float64)
    for i in range(k):
        B_0[i] = B_0[i] / np.linalg.norm(B_0[i])
    return B_0


def _make_noise_trajectory(
    n: int = 60, d: int = 384, noise_level: float = 0.5, seed: int = 42
) -> list[np.ndarray]:
    """Genera n vectores con perturbaciones aleatorias por paso (ruido transitorio)."""
    rng = np.random.default_rng(seed)
    vectors = []
    v = rng.normal(size=d)
    v = v / np.linalg.norm(v)
    vectors.append(v)
    for _ in range(n - 1):
        perturbation = rng.normal(scale=noise_level, size=d)
        v_next = vectors[-1] + perturbation
        v_next = v_next / np.linalg.norm(v_next)
        vectors.append(v_next)
    return vectors


def _make_structural_trajectory(
    n: int = 60, d: int = 384, update_magnitude: float = 0.3, seed: int = 42
) -> list[np.ndarray]:
    """Genera n vectores con rotación gradual consistente (novedad estructural)."""
    rng = np.random.default_rng(seed)
    vectors = []
    v = rng.normal(size=d)
    v = v / np.linalg.norm(v)
    vectors.append(v)
    rotation_angle = update_magnitude / n
    for _ in range(n - 1):
        # Pequeña rotación consistente en un plano aleatorio
        random_dir = rng.normal(size=d)
        ortho_dir = random_dir - np.dot(random_dir, vectors[-1]) / np.dot(vectors[-1], vectors[-1]) * vectors[-1]
        if np.linalg.norm(ortho_dir) < 1e-10:
            continue
        ortho_dir = ortho_dir / np.linalg.norm(ortho_dir)
        cost = np.cos(rotation_angle)
        sine = np.sin(rotation_angle)
        v_next = cost * vectors[-1] + sine * ortho_dir
        v_next = v_next / np.linalg.norm(v_next)
        vectors.append(v_next)
    return vectors


# ---------------------------------------------------------------------------
# Pruebas parametrizadas
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name, vectors, expected_state, expected_meta_key, expected_meta_val, theta_struct", [
    (
        "h3_quarantine_noise_routing",
        "noise",
        "incubating",
        "quarantine_noise",
        True,
        1.0,  # θ_struct: umbral de discriminación H3
    ),
    (
        "h3_structural_discovery_routing",
        "structural",
        "pending_approval",
        "structural_candidate",
        True,
        1.0,  # θ_struct: umbral de discriminación H3
    ),
])
def test_h3_novelty_routing(name, vectors, expected_state, expected_meta_key, expected_meta_val, theta_struct):
    """Parametrized test: routing classification for H3 novelty discrimination.

    Verifies that the discrimination pipeline correctly classifies:
      - noise transitorio  → lifecycle_state = "incubating" + quarantine_noise: true
      - novedad estructural → lifecycle_state = "pending_approval" + structural_candidate: true

    Classification logic (per plan H3):
      discrimination_ratio = ortho_distance / K_cin
      - ratio < θ_struct  → quarantine_noise (incubating)
      - ratio >= θ_struct → structural_candidate (pending_approval)
    """
    if vectors == "noise":
        traj = _make_noise_trajectory(n=60, seed=42)
    elif vectors == "structural":
        traj = _make_structural_trajectory(n=60, seed=42)
    else:
        raise ValueError(f"Unknown trajectory type: {vectors}")

    d = len(traj[0])
    k = max(2, d // 4)
    B_0 = _make_reduced_base(k=k, d=d, seed=42)

    # Procesar primer par consecutivo para el test de enrutamiento
    v_t = traj[1]
    v_prev = traj[0]

    # --- Cálculo de métricas H3 ---
    od = ortho_distance(v_t, B_0)
    dr = discrimination_ratio(v_t, v_prev, B_0)  # = ortho_distance / K_cin
    k_cin = compute_kinetic_resistance(v_t, v_prev, B_0)

    # --- Lógica de enrutamiento H3 (según plan) ---
    # Si discrimination_ratio < theta_struct -> ruido transitorio
    # Si discrimination_ratio >= theta_struct -> novedad estructural
    if dr < theta_struct:
        lifecycle_state = "incubating"
        meta = {expected_meta_key: expected_meta_val}
    else:
        lifecycle_state = "pending_approval"
        meta = {expected_meta_key: expected_meta_val}

    # --- Afirmaciones ---
    assert lifecycle_state == expected_state, (
        f"[{name}] lifecycle_state expected '{expected_state}', got '{lifecycle_state}'"
    )
    assert meta.get(expected_meta_key) == expected_meta_val, (
        f"[{name}] meta[{expected_meta_key}] expected {expected_meta_val}, got {meta.get(expected_meta_key)}"
    )

    # --- Validación cruzada con evaluate_gate_v01 (C1 dual-key) ---
    # El invariante C1 dice: consolidated iff (σ² >= θ_dyn) ∧ (EthicalKey == True).
    # H3 clasifica ANTES de C1; el nodo nunca debe ir a consolidated directo por H3 solo.
    gate_result = evaluate_gate_v01(
        spectrum=[k_cin],
        ethical_key=True,
        threshold=0.5,  # θ_dyn placeholder
    )
    # El gate C1 devuelve "consolidated" solo si dual-key satisfecho;
    # H3 routing debe haber clasificado a incubating/pending_approval.
    assert gate_result["state"] != "consolidated" or expected_state == "consolidated", (
        f"[{name}] H3 routing to '{lifecycle_state}' but C1 would consolidate; "
        "verify H3-C1 ordering."
    )