"""Pure decision and geometry kernel.

Deterministic, side-effect-free algorithms: the dual-key gate C1 and the
ε-adjacency / projection-variance geometry. This module has NO SQLite/FastAPI
dependencies (pure Python + numpy + math only). The persistence layer
(`traianus/storage.py`) and the HTTP layer (`traianus/app.py`) delegate the
mathematical computations here.
"""

import numpy as np


def evaluate_gate_v01(spectrum: list[float], ethical_key: bool, threshold: float) -> dict:
    """Evaluates the dual gate C1 for v0.1.

    The Topological Key acts as a provisional informational geometric score.
    The dual gate is preserved: consolidation requires BOTH keys
    simultaneously (Topological Key AND Ethical Key / HITL). Neither acts
    alone.
    """
    mean = sum(spectrum) / len(spectrum) if spectrum else 0.0
    variance = sum((x - mean) ** 2 for x in spectrum) / len(spectrum) if spectrum else 0.0

    topological_passed = variance >= threshold
    is_consolidated = topological_passed and ethical_key  # dual-key (AND)

    return {
        "state": "consolidated" if is_consolidated else "incubating",
        "topological_key": {
            "status": "PROVISIONAL_INFORMATIONAL_SCORE",
            "variance": variance,
            "threshold": threshold,
            "passed": topological_passed,
        },
        "ethical_key": ethical_key,
    }


def calibrate_critical_threshold(vectors: list[np.ndarray]) -> float:
    """Critical variance threshold on S^{d-1}, self-projections excluded.

    Cross projections only (j != i). Self-projection (dot == 1.0 for an
    L2-normalized axis) inflated the baseline to an unreachable scale for
    inputs, forcing the Topological Key to a 0% approval rate on real
    corpora (audit finding C1).
    """
    base_variances = []
    for i, axis_vector in enumerate(vectors):
        projections = [
            float(np.dot(axis_vector, other))
            for j, other in enumerate(vectors) if j != i
        ]
        base_variances.append(np.var(projections))
    return float(np.mean(base_variances))


def compute_epsilon_edges(nodes: dict[str, np.ndarray], epsilon: float) -> list[dict]:
    """Pure ε-adjacency computation (ADR-023/H5, RE-08): no DB access.

    (v_i, v_j) ∈ E_n iff ||v_i − v_j||₂ ≤ epsilon. Deterministic: nodes are
    processed in sorted id order and edges are sorted by (source, target).
    """
    ids = sorted(nodes)
    edges: list[dict] = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            dist = float(np.linalg.norm(nodes[ids[i]] - nodes[ids[j]]))
            if dist <= epsilon:
                edges.append({
                    "source": ids[i],
                    "target": ids[j],
                    "distance": round(dist, 6),
                })
    edges.sort(key=lambda e: (e["source"], e["target"]))
    return edges
