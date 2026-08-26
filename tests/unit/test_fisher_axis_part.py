"""Unit tests for tools/experiments/tooling/fisher_axis_part_test.py."""
import numpy as np
import pytest

from tools.experiments.tooling.fisher_axis_part_test import (
    AXES,
    PARTS,
    adjusted_residuals,
    chi2_stat,
    contingency_table,
    cramer_v_corrected,
    holm_bonferroni,
    jackknife_v,
    monte_carlo_pvalue,
    normalized_weights,
)


def test_normalized_weights_scale_invariance():
    w = [0.001, 0.002, 0.004, 0.003]
    a = normalized_weights(w)
    b = normalized_weights([x * 1000.0 for x in w])
    assert np.allclose(a, b)
    assert len(a) == pytest.approx(len(w))
    assert np.mean(a) == pytest.approx(1.0)


def test_weighted_chi2_invariant_under_weight_rescaling():
    from tools.experiments.tooling.fisher_axis_part_test import (
        weighted_contingency_table)

    units = [(i % AXES, i % len(PARTS)) for i in range(200)]
    weights = [0.001 * (1 + (i % 5)) for i in range(200)]
    t_small = weighted_contingency_table(units, weights)
    t_big = weighted_contingency_table(units, [w * 500.0 for w in weights])
    assert np.allclose(t_small, t_big)
    assert chi2_stat(t_small) > 0.0


def _units_from_table(table, seed=0):
    """Expand a count table into (axis_index, part_index) unit tuples."""
    rng = np.random.default_rng(seed)
    units = []
    for i in range(table.shape[0]):
        for j in range(table.shape[1]):
            units.extend([(i, j)] * int(table[i, j]))
    rng.shuffle(units)
    return units


def test_contingency_table_shape_and_totals():
    units = [(0, 0), (0, 1), (3, 2), (7, 4)]
    table = contingency_table(units)
    assert table.shape == (AXES, len(PARTS))
    assert table.sum() == 4
    assert table[0, 0] == 1 and table[7, 4] == 1


def test_chi2_zero_under_independence():
    table = np.full((AXES, len(PARTS)), 10.0)
    assert chi2_stat(table) == pytest.approx(0.0, abs=1e-9)


def test_chi2_large_under_perfect_association():
    table = np.zeros((AXES, len(PARTS)))
    for j in range(len(PARTS)):
        table[j % AXES, j] = 50
    assert chi2_stat(table) > 500


def test_cramer_v_corrected_in_unit_interval():
    table = np.full((AXES, len(PARTS)), 5.0)
    n = table.sum()
    chi2 = chi2_stat(table)
    v = cramer_v_corrected(chi2, n, *table.shape)
    assert v == pytest.approx(0.0, abs=1e-9)
    assoc = np.zeros((AXES, len(PARTS)))
    for j in range(len(PARTS)):
        assoc[j, j] = 100
    v_assoc = cramer_v_corrected(chi2_stat(assoc), assoc.sum(), *assoc.shape)
    assert 0.0 < v_assoc <= 1.0


def test_adjusted_residuals_flag_driving_cells():
    table = np.full((AXES, len(PARTS)), 10.0)
    table[0, 0] = 40
    residuals = adjusted_residuals(table)
    assert residuals[0, 0] > 2.5
    # Boosting one cell shrinks every other cell's expectation (n grows,
    # their margins stay fixed): all other residuals stay far below.
    others = np.delete(residuals.ravel(), 0)
    assert others.max() < residuals[0, 0]
    uniform = np.full((AXES, len(PARTS)), 10.0)
    assert np.allclose(adjusted_residuals(uniform), 0.0)


def _separable_units():
    table = np.zeros((AXES, len(PARTS)))
    for j in range(len(PARTS)):
        table[j, j] = 60
    return _units_from_table(table, seed=1)


def _homogeneous_units():
    return _units_from_table(np.full((AXES, len(PARTS)), 12), seed=1)


def test_monte_carlo_detects_separable_parts():
    result = monte_carlo_pvalue(_separable_units(), replicas=200, seed=0)
    assert result["p_value"] <= 0.01
    assert result["chi2"] > 500


def test_monte_carlo_homogeneous_not_significant():
    result = monte_carlo_pvalue(_homogeneous_units(), replicas=200, seed=0)
    assert result["p_value"] >= 0.20


def test_monte_carlo_deterministic_given_seed():
    a = monte_carlo_pvalue(_separable_units(), replicas=50, seed=7)
    b = monte_carlo_pvalue(_separable_units(), replicas=50, seed=7)
    assert a == b


def test_holm_bonferroni_orders_and_adjusts():
    pvals = [0.001, 0.01, 0.03, 0.5]
    adjusted = holm_bonferroni(pvals)
    assert adjusted == pytest.approx([0.004, 0.03, 0.06, 0.5])
    assert all(a <= b for a, b in zip(adjusted, adjusted[1:]))


def test_jackknife_v_deterministic_and_stable():
    units = _homogeneous_units()
    a = jackknife_v(units, blocks=5)
    b = jackknife_v(units, blocks=5)
    assert a == b
    assert set(a) == {"v_scores", "mean", "std"}
    assert len(a["v_scores"]) == 5
    assert all(v >= 0.0 for v in a["v_scores"])


def test_main_missing_db_clean_exit(monkeypatch, capsys):
    from tools.experiments.tooling.fisher_axis_part_test import main

    monkeypatch.setattr(
        "sys.argv",
        ["fisher_axis_part_test", "--db", "/nonexistent/fisher_target.db"],
    )
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 2
    assert "not found" in capsys.readouterr().out


def test_main_rejects_unknown_unit(monkeypatch):
    from tools.experiments.tooling.fisher_axis_part_test import main

    monkeypatch.setattr(
        "sys.argv",
        ["fisher_axis_part_test", "--db", ".data/spinoza_full.db",
         "--unit", "bogus"],
    )
    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 2
