"""Hermetic smoke suite for the Representation Independence experiment (#53).

Re-runs the 3.3 harness scenarios that need no neural model (B, C.1, C.2)
over a small six-note corpus and re-asserts the governance and fail-closed
rejection invariants. Scenario A (cached offline MiniLM) is exercised
manually via `exp_representation_independence.py --providers a`.
"""
from pathlib import Path

from tools.experiments.representation.exp_representation_independence import (
    DEFAULT_TOKEN,
    SyntheticHeteroProvider,
    assert_invariants,
    assert_rejection_invariants,
    run_governance_scenario,
    run_rejection_scenario,
)
from traianus.representation.mock_provider import MockRepresentationProvider

SMOKE_CORPUS = [
    ("A", "Substrate variance across the eight-axis geodetic baseline."),
    ("A", "Spectral projection onto the active epoch of the canonical basis."),
    ("B", "Dual-key consolidation requires variance above the dynamic threshold."),
    ("B", "An ethical-key denial must leave the node incubating unconditionally."),
    ("C", "Append-only node history keeps every revision sequence contiguous."),
    ("C", "Fail-closed ingress rejects non-plain text before any side effect."),
]


class TestRepresentationIndependenceSmoke:
    def test_governance_invariants_hold_under_mock_provider(self, tmp_path):
        metrics = run_governance_scenario(
            MockRepresentationProvider(), SMOKE_CORPUS, Path(tmp_path)
        )
        assert_invariants(metrics)
        assert metrics["ingested"] == 6
        assert metrics["nodes"] == 6

    def test_governance_invariants_hold_under_hetero_128_provider(self, tmp_path):
        metrics = run_governance_scenario(
            SyntheticHeteroProvider(128, seed=20260814), SMOKE_CORPUS, Path(tmp_path)
        )
        assert_invariants(metrics)
        assert metrics["ingested"] == 6
        assert metrics["nodes"] == 6

    def test_epsilon_edge_set_is_non_vacuous_under_mock_provider(self, tmp_path):
        metrics = run_governance_scenario(
            MockRepresentationProvider(), SMOKE_CORPUS, Path(tmp_path)
        )
        assert metrics["edge_count"] > 0, (
            "vacuous epsilon-edge set: edge_count=0 makes edges_deterministic "
            "and edge_jaccard vacuous (empty graph similarity)"
        )

    def test_rejection_invariants_hold_for_hetero_512(self, tmp_path):
        metrics = run_rejection_scenario(Path(tmp_path), token=DEFAULT_TOKEN)
        assert_rejection_invariants(metrics)
        assert metrics["vector_422"] == 422
        assert metrics["node_rows_written"] == 0
        assert metrics["telemetry_error_rows"] == 1
