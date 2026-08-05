"""Pure decision kernel (SPEC-REFACTOR-v0.2 §3.2, decision A-a).

Deterministic dual-key gate C1 for v0.1/v0.2. This module is the single
authority for the state transition decision; it has NO SQLite/FastAPI
dependencies (pure Python + math only). The HTTP layer and the spectral
processor compute the projection spectrum and the dynamic threshold and
delegate the decision here.
"""


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
