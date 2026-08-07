import sqlite3

import numpy as np

from traianus.core import calibrate_critical_threshold, evaluate_gate_v01

DB_PATH = "traianus.db"


def load_geodesic_axes(db_path: str = DB_PATH):
    """Lee los BLOBs reales de geodesic_axes (solo lectura, sin mutación).

    Respeta el contrato de época (SPEC v0.2 §3.3): si la tabla tiene
    epoch_provenance, carga el conjunto activo; en bases heredadas sin la
    columna (PK = id) carga el conjunto completo ordenado por id.
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
    print(" Base geodésica: BLOBs REALES de geodesic_axes (sin np.random/Gram-Schmidt)")
    print("=" * 80)

    # ==========================================
    # PASO 0: Lectura de la base geodésica real
    # ==========================================
    axes = load_geodesic_axes()
    k = len(axes)
    d = axes[0][3].shape[0]
    print(f"\n[+] Base geodésica real: {k} ejes en R^{d}")
    for axis_id, simbolo, tag, v in axes:
        print(f"      - {axis_id} {simbolo} {tag} (dim={v.shape[0]}, ||.||_2={np.linalg.norm(v):.6f})")

    # ==========================================
    # PASO 1: Ingesta y Normalización L2 Estricta
    # ==========================================
    print("\n" + "-" * 50)
    print(" PASO 1: Ingesta y Normalización L2 Estricta")
    print("-" * 50)

    # Vector de prueba: mezcla convexa de dos primitivas reales (T1+T2).
    # Simula una ingesta alineada con dos ejes del tejido (fricción alta).
    v_raw = axes[0][3] + axes[1][3]
    norm_l2 = np.linalg.norm(v_raw)
    if norm_l2 == 0 or not np.isfinite(norm_l2):
        print(" [ERR] Compuerta Zero-Trust: Norma inválida. Abortando.")
        return

    v_d = v_raw / norm_l2
    print(f" [OK] Normalización L2 completada:")
    print(f"      - v_d shape: {v_d.shape}")
    print(f"      - Invariante L2 (||v_d||_2): {np.linalg.norm(v_d):.6f} (Debe ser exactamente 1.0)")

    # ==========================================
    # PASO 2: Espectro de Proyección sobre los k Ejes Reales
    # ==========================================
    print("\n" + "-" * 50)
    print(" PASO 2: Espectro de Proyección sobre los k Ejes Reales")
    print("-" * 50)

    axis_vectors = [axes[i][3] for i in range(k)]
    projections = [float(np.dot(v_d, axis_vectors[i])) for i in range(k)]
    for i, p_i in enumerate(projections):
        print(f"      - Proyección p_{i+1} (<v_d, e_{i+1}>): {p_i:+.6f}")

    mean_p = np.mean(projections)
    var_p = np.var(projections)
    print(f"      => Media Espectral (p_bar): {mean_p:+.6f}")
    print(f"      => Fricción / Varianza Espectral (sigma^2): {var_p:.6f}")

    # ==========================================
    # PASO 3: Umbral dinámico real y Compuerta Dual
    # ==========================================
    print("\n" + "-" * 50)
    print(" PASO 3: Umbral Dinámico (densidad del tejido) y Compuerta Dual")
    print("-" * 50)

    # Densidad del tejido = varianza de las proyecciones CRUZADAS de la base
    # real (calibrate_critical_threshold excluye auto-proyección i == j, audit
    # C1). Con la base real ya NO es 0.0 sino ~0.004.
    theta_dyn = calibrate_critical_threshold(axis_vectors)
    print(f"      - Densidad del Tejido (theta_dyn): {theta_dyn:.6f}")

    ethical_key = True
    gate = evaluate_gate_v01(projections, ethical_key, theta_dyn)
    print(f"      - Condición (sigma^2 >= theta_dyn): {var_p >= theta_dyn} ({var_p:.6f} >= {theta_dyn:.6f})")
    print(f"      - Ethical Key (HITL): {ethical_key}")
    print(f"      => Estado de Consolidación: {gate['state'].upper()}")

    # ==========================================
    # PASO 4: Válvula Dimensional Ortogonal (d -> d+1, k -> k+1)
    # ==========================================
    print("\n" + "-" * 50)
    print(" PASO 4: Válvula Dimensional Ortogonal (384D -> 385D)")
    print("-" * 50)
    print("      [i] Fricción (sigma^2) >= densidad (theta_dyn): se inyecta el eje d+1.")

    # 1. Zero-padding de la entidad: v_d_plus1 = [v_d; 0.0]
    v_d_plus1 = np.append(v_d, 0.0)
    print(f"      - Zero-padding de la entidad: v_d+1 shape = {v_d_plus1.shape}")

    # 2. Re-padding de los k ejes reales previos
    axes_padded = [np.append(axes[i][3], 0.0) for i in range(k)]
    print(f"      - Re-padding de los {k} ejes reales completado.")

    # 3. Inyección del eje canónico e_{k+1} = [0, ..., 0, 1.0]
    e_new = np.zeros(d + 1, dtype=np.float64)
    e_new[-1] = 1.0
    axes_padded.append(e_new)
    print(f"      - Eje canónico e_{k+1} inyectado (ortogonalidad absoluta).")

    # 4. Recálculo del espectro en la nueva época (k + 1 ejes)
    new_projections = [float(np.dot(v_d_plus1, axes_padded[i])) for i in range(k + 1)]
    print("\n      [i] Espectro re-calculado en R^385:")
    for i, p_i in enumerate(new_projections):
        suffix = " (NUEVO EJE)" if i == k else ""
        print(f"          - Proyección p_{i+1}: {p_i:+.6f}{suffix}")

    new_var_p = np.var(new_projections)
    print(f"      => Nueva Varianza Espectral (sigma^2): {new_var_p:.6f}")

    # ==========================================
    # PASO 5: Verificación de Invariantes Físicas
    # ==========================================
    print("\n" + "-" * 50)
    print(" PASO 5: Verificación de Invariantes Físicas")
    print("-" * 50)

    inv_norm = np.isclose(np.linalg.norm(v_d_plus1), 1.0)
    inv_dim = (e_new.shape[0] == d + 1)
    inv_axes_count = (len(axes_padded) == k + 1)
    ortho = max(float(np.abs(np.dot(e_new, old))) for old in axes_padded[:-1])
    inv_ortho = np.isclose(ortho, 0.0)
    inv_valve_ortho = np.isclose(np.dot(v_d_plus1, e_new), 0.0)

    print(f"      - Invariante 1 (||v_{d+1}||_2 == 1.0): {inv_norm} ({np.linalg.norm(v_d_plus1):.6f})")
    print(f"      - Invariante 2 (dim(e_{k+1}) == {d+1}): {inv_dim}")
    print(f"      - Invariante 3 (|B_n+1| == {k+1}): {inv_axes_count}")
    print(f"      - Invariante 4 (max|<e_viejo, e_nuevo>| == 0): {inv_ortho} ({ortho:.2e})")
    print(f"      - Invariante 5 (<v_d+1, e_nuevo> == 0): {inv_valve_ortho} ({np.dot(v_d_plus1, e_new):.2e})")

    success = inv_norm and inv_dim and inv_axes_count and inv_ortho and inv_valve_ortho
    print(f"\n      >>> RESULTADO DE LA PRUEBA: {'PASÓ (VERDE)' if success else 'FALLÓ (ROJO)'} <<<")
    print("=" * 80)


if __name__ == "__main__":
    run_simulation()
