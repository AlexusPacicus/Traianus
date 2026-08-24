"""Central runtime configuration resolvers.

Single source of truth for environment-overridable operational constants,
so tooling can never silently diverge from the running server (audit N4).
"""
import os

DEFAULT_EPSILON_EDGE = 0.8


def resolve_epsilon_edge() -> float:
    """Resolves the E_n adjacency threshold (ADR-023/H5).

    Reads TRAIANUS_EPSILON_EDGE (server-boot override); defaults to
    DEFAULT_EPSILON_EDGE. Every consumer (HTTP layer, bridge auditor,
    experiments) resolves through here so an audited adjacency can never
    silently diverge from the persisted one.
    """
    return float(os.environ.get("TRAIANUS_EPSILON_EDGE", DEFAULT_EPSILON_EDGE))
