"""Governance layer: the dual-key C1 gate (issue #48).

Houses the state-transition decision: consolidation requires BOTH the
Topological Key (σ² ≥ θ_dyn) and the Ethical Key (HITL) simultaneously
(AGENTS.md §3.5, ADR-022). Pure computation, no persistence.
"""

from traianus.governance.gate import evaluate_gate, evaluate_gate_v01

__all__ = ["evaluate_gate", "evaluate_gate_v01"]
