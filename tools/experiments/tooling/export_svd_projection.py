#!/usr/bin/env python
"""Static SVD projection of the Spinoza Part II scratch manifold (Fase 3).

Reads the current-state nodes (MAX(seq)/id, telemetry_error excluded) from
the scratch DB built by ingest_spinoza_part2.py, reduces the 384-D cloud to
2-D/3-D principal coordinates with traianus.geometry.svd_reduce (sign-
canonicalized, stable across BLAS builds), and emits a frozen JSON for
logical-separation inspection before Ulpia ingestion.

Output (.data/spinoza_part2_svd.json):
- explained_variance_ratios: full spectrum of the centered cloud;
- points: [{node_id, label, x[, y][, z], r}] in reading order; labels come
  from .data/spinoza_part2_labels.json (neutral metadata, never embedded).

Read-only audit: opens SQLite in URI mode=ro, never mutates state.
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

sys.path.insert(0, str(REPO_ROOT))

DEFAULT_DB = REPO_ROOT / ".data" / "spinoza_part2.db"
DEFAULT_LABELS = REPO_ROOT / ".data" / "spinoza_part2_labels.json"
DEFAULT_OUT = REPO_ROOT / ".data" / "spinoza_part2_svd.json"


def explained_variance_ratios(X) -> list[float]:
    """Full PCA spectrum of the centered data matrix."""
    import numpy as np

    X_centered = X - np.mean(X, axis=0)
    S = np.linalg.svd(X_centered, compute_uv=False)
    total = float(np.sum(S**2))
    if total == 0.0:
        raise ValueError("degenerate cloud: zero variance")
    return [float(v / total) for v in S**2]


def assemble_points(node_ids: list[str], coords, residual,
                    labels: dict[str, str], k: int) -> list[dict]:
    """Reading-order points with neutral labels and coordinates."""
    points = []
    for i, nid in enumerate(node_ids):
        if nid not in labels:
            raise KeyError(f"label missing for {nid}")
        point = {"node_id": nid, "label": labels[nid],
                 "x": float(coords[i, 0]), "y": float(coords[i, 1])}
        if k >= 3:
            point["z"] = float(coords[i, 2])
        if residual.shape[1] > 0:
            point["r"] = float(residual[i, 0])
        points.append(point)
    return points


def load_nodes(db_path: Path) -> tuple[list[str], "np.ndarray"]:
    """Current manifold state from the scratch DB (read-only)."""
    import numpy as np

    sql = """
        SELECT id, vector_blob FROM manifold_nodes m
        WHERE m.lifecycle_state != 'telemetry_error'
          AND m.seq = (SELECT MAX(seq) FROM manifold_nodes m2 WHERE m2.id = m.id)
        ORDER BY CAST(SUBSTR(m.id, 6) AS INTEGER), m.id
    """
    conn = __import__("sqlite3").connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = conn.execute(sql).fetchall()
    finally:
        conn.close()
    if len(rows) < 2:
        raise SystemExit(f"ERR: need >= 2 nodes in {db_path}, got {len(rows)}")
    node_ids = [row[0] for row in rows]
    X = np.vstack([np.frombuffer(row[1], dtype=np.float64) for row in rows])
    return node_ids, X


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    import numpy as np

    from traianus.geometry.observables import svd_reduce

    node_ids, X = load_nodes(args.db)
    labels = json.loads(Path(args.labels).read_text(encoding="utf-8"))
    ratios = explained_variance_ratios(X)

    coords2, residual2 = svd_reduce(X, k=2)
    coords3, residual3 = svd_reduce(X, k=3)

    payload = {
        "n_points": len(node_ids),
        "explained_variance_ratios": ratios[:10],
        "points_2d": assemble_points(node_ids, coords2, residual2, labels, k=2),
        "points_3d": assemble_points(node_ids, coords3, residual3, labels, k=3),
    }
    Path(args.out).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")

    print(f"[+] nodes projected: {len(node_ids)}")
    print(f"[=] explained variance: PC1={ratios[0]:.4f} PC2={ratios[1]:.4f} "
          f"PC3={ratios[2]:.4f} | top-10 cum="
          f"{sum(ratios[:10]):.4f}")
    print(f"[+] output: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
