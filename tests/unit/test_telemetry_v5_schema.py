"""Structural guard for the frozen telemetry v5 dynamic_epsilon_audit section.

No new dependencies: plain assertions over the committed artifact prevent
schema drift of the versioned dataset (LEDGER seq 40).
"""
import json
import math
from pathlib import Path

import pytest

V5_PATH = (Path(__file__).resolve().parents[2] / "data" / "spinoza"
           / "telemetry" / "v5.json")

PARTS = ["P1_GOD", "P2_MIND", "P3_AFFECTS", "P4_BONDAGE", "P5_POWER"]


@pytest.fixture(scope="module")
def v5():
    return json.loads(V5_PATH.read_text(encoding="utf-8"))


def test_file_exists_and_has_dynamic_section(v5):
    assert "dynamic_epsilon_audit" in v5


def test_runs_section_intact(v5):
    runs = v5["runs"]
    assert set(runs) == {"part1_isolated", "part2_isolated", "part3_isolated",
                         "part4_isolated", "part5_isolated",
                         "accumulated_12345"}
    for name, run in runs.items():
        assert isinstance(run["n_nodes"], int) and run["n_nodes"] > 0
        assert 0.0 <= run["chromatic"]["collision_rescue_rate"] <= 1.0


def _assert_knee(report):
    assert {"nodes", "null_pairs", "epsilon_star", "kept_mass_fraction",
            "edges_at_epsilon_star", "bridges_at_epsilon_star",
            "bootstrap_stability", "grid", "sweep"} <= set(report)
    stability = report["bootstrap_stability"]
    assert stability["std"] >= 0.0 and len(stability["epsilons"]) > 0
    assert 0.0 < report["kept_mass_fraction"] <= 1.0
    assert 0.0 < report["epsilon_star"] < math.sqrt(2.0) + 0.1
    assert all(isinstance(r["bridges"], int) for r in report["sweep"])


def _assert_anisotropy(report):
    assert len(report["shares"]) == 8
    assert abs(sum(report["shares"]) - 1.0) < 1e-9
    assert 0.0 <= report["p_value"] <= 1.0
    assert report["replicas"] > 0


def _assert_enrichment(report):
    assert set(report["block_sizes"]) == set(PARTS)
    assert sum(report["block_sizes"].values()) == report["nodes"] == 2221
    matrix = report["matrix"]
    assert len(matrix) == 15
    for key, cell in matrix.items():
        assert cell["observed"] >= 0 and cell["enrichment"] is not None
    assert report["peak_memory_mb"] > 0.0


def _assert_fisher(result, expect_unit):
    assert result["unit"].startswith(expect_unit)
    assert result["chi2"] >= 0.0
    assert 0.0 <= result["cramers_v_corrected"] <= 1.0
    if expect_unit != "weighted":
        assert 0.0 <= result["p_value"] <= 1.0
    else:
        assert result["effective_n"] > 0.0


def test_otsu_sweep_report_structure(v5):
    _assert_knee(v5["dynamic_epsilon_audit"]["knee_audit_v5"])


def test_anisotropy_report_structure(v5):
    _assert_anisotropy(
        v5["dynamic_epsilon_audit"]["anisotropy_accumulated"])


def test_inter_part_enrichment_structure(v5):
    _assert_enrichment(
        v5["dynamic_epsilon_audit"]["inter_part_enrichment_v5"])


def test_fisher_battery_structure(v5):
    audit = v5["dynamic_epsilon_audit"]
    for stem, unit in [("fisher_all", "all"), ("fisher_active", "active"),
                       ("fisher_weighted", "weighted")]:
        payload = audit[stem]
        key = next(k for k in payload if not k.startswith("edges_eps"))
        _assert_fisher(payload[key], unit)
    edges = audit["fisher_edges"]
    assert set(edges) == {"all", "edges_eps_0.8", "edges_eps_1.2032"}
    for key in ("edges_eps_0.8", "edges_eps_1.2032"):
        assert "warning" in edges[key]
