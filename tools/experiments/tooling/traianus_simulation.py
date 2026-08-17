import sqlite3

import numpy as np

from traianus.core import calibrate_critical_threshold, evaluate_gate_v01

DB_PATH = ".data/traianus.db"


def load_geodesic_axes(db_path: str = DB_PATH):
    """Reads the real BLOBs from geodesic_axes (read-only, no mutation).

    Respects the epoch contract (SPEC v0.2 §3.3): when the table has
    epoch_provenance, loads the active set; in legacy bases without the
    column (PK = id) loads the full set ordered by id.
    """
    conn = sqlite3.connect(db_path)
    try:
        cols = [row[1] for row in conn.execute("PRAGMA table_info(geodesic_axes)").fetchall()]
        if "epoch_provenance" in cols:
            epoch = conn.execute(
                "SELECT epoch_provenance FROM geodesic_axes "
                "GROUP BY epoch_provenance ORDER BY MAX(created_at) DESC LIMIT 1"
            ).fetchone()[0]
            rows = conn.execute(
                "SELECT id, simbolo, tag, vector_blob FROM geodesic_axes "
                "WHERE epoch_provenance = ? ORDER BY id",
                (epoch,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, simbolo, tag, vector_blob FROM geodesic_axes ORDER BY id"
            ).fetchall()
    finally:
        conn.close()
    return [
        (axis_id, simbolo, tag, np.frombuffer(vector_blob, dtype=np.float64))
        for axis_id, simbolo, tag, vector_blob in rows
    ]


def run_simulation():
    print("=" * 80)
    print(" TRAIANUS CORE - KINETIC KERNEL SIMULATION (384D -> 385D)")
    print(" Geodesic basis: REAL BLOBs from geodesic_axes (no np.random/Gram-Schmidt)")
    print("=" * 80)

    # ==========================================
    # STEP 0: Read the real geodesic basis
    # ==========================================
    axes = load_geodesic_axes()
    k = len(axes)
    d = axes[0][3].shape[0]
    print(f"\n[+] Real geodesic basis: {k} axes in R^{d}")
    for axis_id, simbolo, tag, v in axes:
        print(f"      - {axis_id} {simbolo} {tag} (dim={v.shape[0]}, ||.||_2={np.linalg.norm(v):.6f})")

    # ==========================================
    # STEP 1: Ingest and strict L2 normalization
    # ==========================================
    print("\n" + "-" * 50)
    print(" STEP 1: Ingest and Strict L2 Normalization")
    print("-" * 50)

    # Test vector: convex combination of two real primitives (T1+T2).
    # Simulates an ingest aligned with two axes of the tissue (high friction).
    v_raw = axes[0][3] + axes[1][3]
    norm_l2 = np.linalg.norm(v_raw)
    if norm_l2 == 0 or not np.isfinite(norm_l2):
        print(" [ERR] Zero-Trust Gate: invalid norm. Aborting.")
        return

    v_d = v_raw / norm_l2
    print(f" [OK] L2 normalization completed:")
    print(f"      - v_d shape: {v_d.shape}")
    print(f"      - L2 invariant (||v_d||_2): {np.linalg.norm(v_d):.6f} (must be exactly 1.0)")

    # ==========================================
    # STEP 2: Projection spectrum over the k real axes
    # ==========================================
    print("\n" + "-" * 50)
    print(" STEP 2: Projection Spectrum over the k Real Axes")
    print("-" * 50)

    axis_vectors = [axes[i][3] for i in range(k)]
    projections = [float(np.dot(v_d, axis_vectors[i])) for i in range(k)]
    for i, p_i in enumerate(projections):
        print(f"      - Projection p_{i+1} (<v_d, e_{i+1}>): {p_i:+.6f}")

    mean_p = np.mean(projections)
    var_p = np.var(projections)
    print(f"      => Spectral Mean (p_bar): {mean_p:+.6f}")
    print(f"      => Friction / Spectral Variance (sigma^2): {var_p:.6f}")

    # ==========================================
    # STEP 3: Real dynamic threshold and Dual Gate
    # ==========================================
    print("\n" + "-" * 50)
    print(" STEP 3: Dynamic Threshold (tissue density) and Dual Gate")
    print("-" * 50)

    # Tissue density = variance of the CROSS projections of the real basis
    # (calibrate_critical_threshold excludes self-projection i == j, audit
    # C1). With the real basis it is no longer 0.0 but ~0.004.
    theta_dyn = calibrate_critical_threshold(axis_vectors)
    print(f"      - Tissue Density (theta_dyn): {theta_dyn:.6f}")

    ethical_key = True
    gate = evaluate_gate_v01(projections, ethical_key, theta_dyn)
    print(f"      - Condition (sigma^2 >= theta_dyn): {var_p >= theta_dyn} ({var_p:.6f} >= {theta_dyn:.6f})")
    print(f"      - Ethical Key (HITL): {ethical_key}")
    print(f"      => Consolidation State: {gate['state'].upper()}")

    # ==========================================
    # STEP 4: Orthogonal Dimensional Valve (d -> d+1, k -> k+1)
    # ==========================================
    print("\n" + "-" * 50)
    print(" STEP 4: Orthogonal Dimensional Valve (384D -> 385D)")
    print("-" * 50)
    print("      [i] Friction (sigma^2) >= density (theta_dyn): the d+1 axis is injected.")

    # 1. Zero-padding of the entity: v_d_plus1 = [v_d; 0.0]
    v_d_plus1 = np.append(v_d, 0.0)
    print(f"      - Zero-padding of the entity: v_d+1 shape = {v_d_plus1.shape}")

    # 2. Re-padding of the k previous real axes
    axes_padded = [np.append(axes[i][3], 0.0) for i in range(k)]
    print(f"      - Re-padding of the {k} real axes completed.")

    # 3. Injection of the canonical axis e_{k+1} = [0, ..., 0, 1.0]
    e_new = np.zeros(d + 1, dtype=np.float64)
    e_new[-1] = 1.0
    axes_padded.append(e_new)
    print(f"      - Canonical axis e_{k+1} injected (absolute orthogonality).")

    # 4. Spectrum recomputed in the new epoch (k + 1 axes)
    new_projections = [float(np.dot(v_d_plus1, axes_padded[i])) for i in range(k + 1)]
    print("\n      [i] Spectrum recomputed in R^385:")
    for i, p_i in enumerate(new_projections):
        suffix = " (NEW AXIS)" if i == k else ""
        print(f"          - Projection p_{i+1}: {p_i:+.6f}{suffix}")

    new_var_p = np.var(new_projections)
    print(f"      => New Spectral Variance (sigma^2): {new_var_p:.6f}")

    # ==========================================
    # STEP 5: Verification of physical invariants
    # ==========================================
    print("\n" + "-" * 50)
    print(" STEP 5: Verification of Physical Invariants")
    print("-" * 50)

    inv_norm = np.isclose(np.linalg.norm(v_d_plus1), 1.0)
    inv_dim = (e_new.shape[0] == d + 1)
    inv_axes_count = (len(axes_padded) == k + 1)
    ortho = max(float(np.abs(np.dot(e_new, old))) for old in axes_padded[:-1])
    inv_ortho = np.isclose(ortho, 0.0)
    inv_valve_ortho = np.isclose(np.dot(v_d_plus1, e_new), 0.0)

    print(f"      - Invariant 1 (||v_{d+1}||_2 == 1.0): {inv_norm} ({np.linalg.norm(v_d_plus1):.6f})")
    print(f"      - Invariant 2 (dim(e_{k+1}) == {d+1}): {inv_dim}")
    print(f"      - Invariant 3 (|B_n+1| == {k+1}): {inv_axes_count}")
    print(f"      - Invariant 4 (max|<e_old, e_new>| == 0): {inv_ortho} ({ortho:.2e})")
    print(f"      - Invariant 5 (<v_d+1, e_new> == 0): {inv_valve_ortho} ({np.dot(v_d_plus1, e_new):.2e})")

    success = inv_norm and inv_dim and inv_axes_count and inv_ortho and inv_valve_ortho
    print(f"\n      >>> TEST RESULT: {'PASSED (GREEN)' if success else 'FAILED (RED)'} <<<")
    print("=" * 80)


if __name__ == "__main__":
    run_simulation()
