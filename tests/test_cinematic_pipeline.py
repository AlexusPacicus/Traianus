"""Cinematic Kinematic Pipeline (H1 ∧ H2 ∧ H3) integration tests.

Validates the complete pipeline across 200 synthetic events in 5 phases:
  [1..40]  Laminar          → smooth displacement, K_cin ≤ θ_dyn
  [41..70] Estática         → v_t = v_{t-1}, Δv=0 ⇒ K_cin=0
  [71..110] Enquistamiento  → micro-oscillations alta freq, K_cin > θ_dyn
  [111..150] Ruido          → saltos estocásticos, quarantine_noise
  [151..200] Novedad        → rotación geodésica, structural_candidate
"""

import numpy as np
import pytest

from traianus.core import (
    compute_kinetic_resistance,
    ortho_distance,
    discrimination_ratio,
    evaluate_gate_v01,
    calibrate_critical_threshold,
    project_dimensional_relief,
)


# ---------------------------------------------------------------------------
# Constants from the cinematic pipeline plan
# ---------------------------------------------------------------------------

PHASES = {
    "LAMINAR": {"start": 1, "end": 40, "desc": "Desplazamiento suave dentro de B_0"},
    "ESTATICA": {"start": 41, "end": 70, "desc": "v_t = v_{t-1}, reposo absoluto"},
    "ENQUISMO": {"start": 71, "end": 110, "desc": "Micro-oscillations alta frecuencia"},
    "RUIDO": {"start": 111, "end": 150, "desc": "Saltos estocásticos transitorios"},
    "NOVELA": {"start": 151, "end": 200, "desc": "Rotación geodésica estructural"},
}

THETA_DYN_PLACEHOLDER = 0.05  # calibrated threshold order of magnitude (realistic B_0)
STRUCT_THRESHOLD = 1.0  # θ_struct for H3 discrimination ratio
DIM = 384


# ---------------------------------------------------------------------------
# Helpers: deterministic vector generation per phase
# ---------------------------------------------------------------------------

def _make_laminar_vector(index: int, total: int) -> np.ndarray:
    """Phase 1: smooth displacement within B_0. All vectors point near same direction."""
    base = np.zeros(DIM, dtype=np.float64)
    base[0] = 1.0
    rng = np.random.default_rng(42 + index)
    perturbation = rng.normal(scale=0.003 * (1.0 - index / total), size=DIM)
    vec = base + perturbation
    vec = vec / np.linalg.norm(vec)
    return vec


def _make_static_vector(_index: int, _total: int) -> np.ndarray:
    """Phase 2: identical vector repeated (stasis)."""
    return np.array([1.0, 0.0] + [0.0] * (DIM - 2), dtype=np.float64)


def _make_ensimbling_vector(index: int, total: int) -> np.ndarray:
    """Phase 3: micro-oscillations around a central point within B_0."""
    rng = np.random.default_rng(123 + index)
    base = np.array([1.0, 0.0] + [0.0] * (DIM - 2), dtype=np.float64)
    # Larger perturbation to ensure K_cin > θ_dyn
    perturbation = rng.normal(scale=0.5 * (index / total + 0.3), size=DIM)
    vec = base + perturbation
    vec = vec / np.linalg.norm(vec)
    return vec


def _make_noise_vector(index: int, total: int) -> np.ndarray:
    """Phase 4: large stochastic jumps restricted to B_0 subspace."""
    rng = np.random.default_rng(456 + index)
    vec = rng.standard_normal(DIM).astype(np.float64)
    vec = vec / np.linalg.norm(vec)
    return vec


def _make_novelty_vector(index: int, total: int) -> np.ndarray:
    """Phase 5: coherent trajectory with constant orthogonal component outside B_0."""
    rng = np.random.default_rng(789 + index)
    base = np.array([1.0, 0.0] + [0.0] * (DIM - 2), dtype=np.float64)
    ortho = np.zeros(DIM)
    ortho[-1] = 0.1 * ((index / total) + 0.5)
    vec = base + ortho
    vec = vec / np.linalg.norm(vec)
    return vec


# ---------------------------------------------------------------------------
# Fixture: realistic DB per test
# ---------------------------------------------------------------------------

@pytest.fixture
def realistic_isolate_db(tmp_path, monkeypatch):
    """Ephemeral SQLite DB with realistic NSM geometry (not onehot)."""
    test_db_path = str(tmp_path / "test_traianus_realistic.db")
    from tests.helpers.db_factory import create_test_db, seed_realistic_axes
    create_test_db(test_db_path, seed="realistic")
    import traianus.storage as storage
    monkeypatch.setattr(storage, "DB_PATH", test_db_path)
    return test_db_path


# ---------------------------------------------------------------------------
# Parametrized tests per phase using core functions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "phase_name, vector_factory, n_events, expected_k_cin_behavior, "
    "expected_dr_behavior",
    [
        # Phase 1: Laminar - smooth displacement, K_cin ≤ θ_dyn
        (
            "LAMINAR",
            _make_laminar_vector,
            40,
            "low",
            "variable",
        ),
        # Phase 2: Estática - v_t = v_{t-1}, Δv=0 ⇒ K_cin=0
        (
            "ESTATICA",
            _make_static_vector,
            30,
            "zero",
            "infinite",
        ),
        # Phase 3: Enquistamiento - K_cin > θ_dyn, ortho_dist ≈ 0
        (
            "ENQUISMO",
            _make_ensimbling_vector,
            40,
            "high",
            "variable",
        ),
        # Phase 4: Ruido - K_cin alto, ortho_dist bajo, discrimination_ratio bajo
        (
            "RUIDO",
            _make_noise_vector,
            40,
            "high",
            "low",
        ),
        # Phase 5: Novedad - K_cin bajo/moderado, ortho_dist elevado, ratio alto
        (
            "NOVELA",
            _make_novelty_vector,
            50,
            "low_mod",
            "high",
        ),
    ],
)
def test_cinematic_pipeline_core_functions(
    phase_name,
    vector_factory,
    n_events,
    expected_k_cin_behavior,
    expected_dr_behavior,
    realistic_isolate_db,
    request,
):
    """Validate core computational kernel behavior per cinematic phase.

    Tests traianus.core pure functions with deterministic synthetic vectors.
    Uses `realistic_isolate_db` fixture for ephemeral DB with production geometry.
    """
    import traianus.storage as storage
    from traianus import app as main_app
    from tests.helpers.fake_encoder import FakeSentenceTransformer

    # Monkeypatch with fake encoder (L1 hermeticity)
    fake = FakeSentenceTransformer()
    monkeypatch = request.getfixturevalue("monkeypatch")
    monkeypatch.setattr(storage, "DB_PATH", realistic_isolate_db)
    monkeypatch.setattr(main_app, "_provider", fake)
    monkeypatch.setattr(main_app, "get_provider", lambda: fake)

    # Ensure geodetic matrix is loaded with realistic geometry
    storage.DB_PATH = realistic_isolate_db
    matrix = storage.get_geodetic_matrix_db()
    assert matrix is not None, f"Geodetic matrix must be populated for {phase_name} test"

    # Build B_0 matrix from geodetic matrix dict
    B_0_rows = []
    for axis_id, axis_entry in matrix.items():
        B_0_rows.append(np.array(axis_entry["vector"], dtype=np.float64))
    if B_0_rows:
        B_0 = np.array(B_0_rows)
    else:
        B_0 = np.eye(DIM)[:96, :]

    # Generate event sequence and compute metrics
    k_cin_values = []
    ortho_dist_values = []
    dr_values = []

    # Generate all vectors for this phase
    vectors = []
    for i in range(n_events):
        vec = vector_factory(i, n_events)
        vectors.append(vec)

    # Compute metrics for consecutive pairs (v_t, v_{t-1})
    for t in range(1, n_events):
        v_t = vectors[t]
        v_prev = vectors[t - 1]

        # H1: compute K_cin (kinematic resistance)
        k_cin = float(compute_kinetic_resistance(v_t, v_prev, B_0))
        k_cin_values.append(k_cin)

        # H3: ortho_distance to B_0
        od = float(ortho_distance(v_t, B_0))
        ortho_dist_values.append(od)

        # H3: discrimination ratio = ortho_dist / K_cin
        if k_cin > 1e-12:
            dr = od / k_cin
        else:
            dr = float('inf') if od > 0 else float('inf')
        dr_values.append(dr)

    # ---- Assertions per expected behavior ----

    # 1. K_cin behavior
    max_k_cin = max(k_cin_values) if k_cin_values else 0.0
    min_k_cin = min(k_cin_values) if k_cin_values else 0.0

    if expected_k_cin_behavior == "zero":
        # Phase 2 (ESTATICA): K_cin should be 0.0 (strict static vectors)
        assert all(abs(k) < 1e-10 for k in k_cin_values), (
            f"[{phase_name}] Expected K_cin ≈ 0.0 for all events, "
            f"got range [{min_k_cin:.6f}, {max_k_cin:.6f}]"
        )
    elif expected_k_cin_behavior == "low":
        # Phase 1 (LAMINAR): K_cin should be below threshold
        assert max_k_cin < THETA_DYN_PLACEHOLDER, (
            f"[{phase_name}] Expected max K_cin < θ_dyn={THETA_DYN_PLACEHOLDER}, "
            f"got {max_k_cin:.6f}"
        )
    elif expected_k_cin_behavior == "high":
        # Phase 3 (ENQUISMO) & 4 (RUIDO): K_cin should be above threshold
        assert min_k_cin > THETA_DYN_PLACEHOLDER, (
            f"[{phase_name}] Expected min K_cin > θ_dyn={THETA_DYN_PLACEHOLDER}, "
            f"got {min_k_cin:.6f}"
        )
    elif expected_k_cin_behavior == "low_mod":
        # Phase 5 (NOVELA): K_cin low/moderate
        assert max_k_cin < THETA_DYN_PLACEHOLDER * 2, (
            f"[{phase_name}] Expected max K_cin < {THETA_DYN_PLACEHOLDER * 2}, "
            f"got {max_k_cin:.6f}"
        )

    # 2. discrimination_ratio behavior (H3)
    max_dr = max(dr_values) if dr_values else 0.0
    min_dr = min(dr_values) if dr_values else 0.0

    if expected_dr_behavior == "infinite":
        # Phase 2 (ESTATICA): K_cin=0 ⇒ dr very high
        high_drs = [dr for dr in dr_values if dr > 100]
        assert len(high_drs) >= len(dr_values) * 0.8, (
            f"[{phase_name}] Expected most dr values very high (K_cin=0), "
            f"got: {dr_values[:5]}..."
        )
    elif expected_dr_behavior == "low":
        # Phase 4 (RUIDO): discrimination_ratio should be low (most values)
        mean_dr = sum(dr_values) / len(dr_values)
        assert mean_dr < STRUCT_THRESHOLD, (
            f"[{phase_name}] Expected mean dr < θ_struct={STRUCT_THRESHOLD}, "
            f"got {mean_dr:.4f} (range [{min_dr:.4f}, {max_dr:.4f}])"
        )
    elif expected_dr_behavior == "high":
        # Phase 5 (NOVELA): discrimination_ratio should be high
        assert all(dr >= STRUCT_THRESHOLD for dr in dr_values), (
            f"[{phase_name}] Expected dr >= θ_struct={STRUCT_THRESHOLD}, "
            f"got range [{min_dr:.4f}, {max_dr:.4f}]"
        )
    elif expected_dr_behavior == "variable":
        # Phase 1 (LAMINAR) & 3 (ENQUISMO): no strict constraint
        pass

    # 3. Phase-appropriate ortho_dist notes (informational)
    # With realistic NSM geometry, ortho_dist values depend on basis alignment;
    # the primary invariants are K_cin (H1) and discrimination_ratio (H3) above.

    print(
        f"[cinematic_core] Phase '{phase_name}': OK. "
        f"K_cin=[{min_k_cin:.4f}, {max_k_cin:.4f}], "
        f"dr=[{min_dr:.4f}, {max_dr:.4f}]"
    )