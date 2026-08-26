"""Unit tests for tools/experiments/tooling/audit_axis_anisotropy.py."""
import numpy as np
import pytest

from tools.experiments.tooling.audit_axis_anisotropy import (
    AXES,
    mass_shares,
    observed_statistic,
    permutation_pvalue,
)


def _random_projections(n, seed):
    rng = np.random.default_rng(seed)
    return rng.random((n, AXES))


def test_mass_shares_sum_to_one_and_match_manual():
    argmax = np.array([0, 0, 2])
    weights = np.array([1.0, 3.0, 4.0])
    shares = mass_shares(argmax, weights)
    assert shares.shape == (AXES,)
    assert shares.sum() == pytest.approx(1.0)
    assert shares[0] == pytest.approx(4.0 / 8.0)
    assert shares[2] == pytest.approx(4.0 / 8.0)


def test_mass_shares_rejects_empty_mass():
    with pytest.raises(ValueError):
        mass_shares(np.zeros(0, dtype=int), np.zeros(0))


def _two_axis_row(first, second):
    row = np.zeros(AXES)
    row[0], row[1] = first, second
    return row


def test_observed_statistic_argmax_matches_products():
    q_a = np.vstack([_two_axis_row(0.9, 0.1), _two_axis_row(0.2, 0.8)])
    q_b = np.vstack([_two_axis_row(0.8, 0.2), _two_axis_row(0.7, 0.6)])
    argmax, shares = observed_statistic(q_a, q_b, np.array([1.0, 1.0]))
    assert argmax.tolist() == [0, 1]
    assert shares[0] == pytest.approx(shares[1])


def test_permutation_pvalue_detects_true_dominance():
    n = 60
    base = _random_projections(n, seed=11)
    q_a = base.copy()
    q_b = base * np.array([1.0] + [0.05] * (AXES - 1)) + 0.01
    weights = np.ones(n)
    result = permutation_pvalue(q_a, q_b, weights, replicas=200, seed=0)
    assert result["p_value"] <= 0.05


def test_permutation_pvalue_isotropic_null_not_significant():
    n = 200
    rng = np.random.default_rng(5)
    q_a = rng.random((n, AXES))
    q_b = rng.random((n, AXES))
    weights = rng.random(n)
    result = permutation_pvalue(q_a, q_b, weights, replicas=200, seed=0)
    assert result["p_value"] >= 0.20


def test_permutation_pvalue_deterministic_given_seed():
    q_a = _random_projections(30, seed=1)
    q_b = _random_projections(30, seed=2)
    weights = np.ones(30)
    a = permutation_pvalue(q_a, q_b, weights, replicas=50, seed=9)
    b = permutation_pvalue(q_a, q_b, weights, replicas=50, seed=9)
    assert a == b


def test_main_missing_db_clean_exit(monkeypatch, capsys):
    from tools.experiments.tooling.audit_axis_anisotropy import main

    monkeypatch.setattr(
        "sys.argv",
        ["audit_axis_anisotropy", "--db", "/nonexistent/axis_target.db",
         "--epsilon", "0.8"],
    )
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 2
    assert "not found" in capsys.readouterr().out
