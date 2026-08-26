"""Unit tests for tools/experiments/tooling/epsilon_knee_audit.py."""
import numpy as np
import pytest

from tools.experiments.tooling.epsilon_knee_audit import (
    bootstrap_epsilon_stability,
    otsu_threshold,
    sweep_bridges,
)


def _bimodal_distances(n_per_mode=500):
    rng = np.random.default_rng(7)
    intra = rng.normal(0.35, 0.05, n_per_mode)
    bulk = rng.normal(1.30, 0.08, n_per_mode)
    return np.clip(np.concatenate([intra, bulk]), 0.0, None)


def test_otsu_splits_bimodal_mixture_between_modes():
    d = _bimodal_distances()
    eps = otsu_threshold(d)
    assert 0.5 < eps < 1.15


def test_otsu_constant_input_returns_value():
    assert otsu_threshold(np.full(10, 0.7)) == pytest.approx(0.7)


def test_sweep_bridges_monotonicity():
    rng = np.random.default_rng(7)
    all_d = rng.random(500)
    cont_d = np.array([0.05, 0.06, 0.07])
    grid = np.linspace(0.5, 10.0, 20)
    rows = sweep_bridges(all_d, cont_d, grid)
    eps = [r["epsilon"] for r in rows]
    bridges = [r["bridges"] for r in rows]
    assert all(a <= b for a, b in zip(eps, eps[1:]))
    assert all(a <= b for a, b in zip(bridges, bridges[1:]))
    mid = rows[len(rows) // 2]
    expected_edges = int((all_d < mid["epsilon"]).sum())
    expected_contig = int((cont_d < mid["epsilon"]).sum())
    assert mid["edges"] == expected_edges
    assert mid["bridges"] == expected_edges - expected_contig


def test_bootstrap_stability_deterministic_given_seed():
    d = _bimodal_distances()
    kwargs = dict(replicas=10, pairs_per_replica=300, seed=11)
    a = bootstrap_epsilon_stability(d, **kwargs)
    b = bootstrap_epsilon_stability(d, **kwargs)
    assert a == b
    assert set(a) == {"epsilons", "mean", "std"}
    assert len(a["epsilons"]) == 10


def test_bootstrap_stability_concentrates_between_modes():
    d = _bimodal_distances()
    result = bootstrap_epsilon_stability(d, replicas=20,
                                         pairs_per_replica=400, seed=11)
    assert 0.5 < result["mean"] < 1.15
    assert result["std"] < 0.25


def test_main_missing_db_clean_exit(monkeypatch, capsys):
    from tools.experiments.tooling.epsilon_knee_audit import main

    monkeypatch.setattr(
        "sys.argv",
        ["epsilon_knee_audit", "--db", "/nonexistent/knee_target.db"],
    )
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 2
    assert "not found" in capsys.readouterr().out
