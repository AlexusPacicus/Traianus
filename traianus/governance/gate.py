"""Dual-key C1 gate (issue #48/#49).

Consolidation is a simultaneous AND: Consolidated ⟺ (σ² ≥ θ_dyn) ∧
(EthicalKey == True) (AGENTS.md §3.5, ADR-022). This module owns the pure
decision and the lifecycle-state transition; persistence and orchestration
live in the HTTP layer.
"""


def evaluate_gate(spectrum: list[float], ethical_key: bool, threshold: float) -> dict:
    """Evaluates the dual gate C1 (canonical name, issue #49).

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


evaluate_gate_v01 = evaluate_gate
