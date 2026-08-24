"""Shared helpers for Spinoza-corpus lab tooling.

Single owner of node loading and the PCA spectrum so the exporter and the
chromatic audit cannot drift apart. Read-only against any substrate DB;
callers should keep n modest (distance matrices are O(n^2) in memory,
comfortable up to a few thousand nodes).
"""

import json
import sqlite3
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]

CURRENT_NODES_SQL = """
    SELECT id, text, vector_blob FROM manifold_nodes m
    WHERE m.lifecycle_state != 'telemetry_error'
      AND m.seq = (SELECT MAX(seq) FROM manifold_nodes m2 WHERE m2.id = m.id)
    ORDER BY CAST(SUBSTR(m.id, 6) AS INTEGER), m.id
"""


def load_nodes(db_path: Path) -> tuple[list[str], list[str], np.ndarray]:
    """Current-state nodes (MAX(seq)/id, telemetry_error excluded), reading order."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        rows = conn.execute(CURRENT_NODES_SQL).fetchall()
    finally:
        conn.close()
    if len(rows) < 10:
        raise SystemExit(f"ERR: need >= 10 nodes in {db_path}, got {len(rows)}")
    node_ids = [r[0] for r in rows]
    texts = [" ".join(r[1].split()) for r in rows]
    X = np.vstack([np.frombuffer(r[2], dtype=np.float64) for r in rows])
    return node_ids, texts, X


def load_labels(path: Path) -> dict[str, str]:
    return json.loads(path.read_text(encoding="utf-8"))


def explained_variance_ratios(X: np.ndarray, top: int | None = None) -> list[float]:
    """Full PCA spectrum of the centered cloud; raises on degenerate input."""
    X_centered = X - np.mean(X, axis=0)
    S = np.linalg.svd(X_centered, compute_uv=False)
    total = float(np.sum(S**2))
    if total == 0.0:
        raise ValueError("degenerate cloud: zero variance")
    ratios = [float(v / total) for v in S**2]
    return ratios if top is None else ratios[:top]
