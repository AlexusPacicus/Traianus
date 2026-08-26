"""Unit tests for tools/experiments/tooling/inter_part_enrichment.py."""
import pytest

from tools.experiments.tooling.inter_part_enrichment import (
    enrichment_matrix,
    part_of,
)


SIZES = {"P1_GOD": 100, "P2_MIND": 100, "P5_POWER": 300}


def test_part_of_maps_prefix():
    assert part_of("PART3_AFFECTS_P08_PROP") == "P3_AFFECTS"
    with pytest.raises(KeyError):
        part_of("BOOTSTRAP_SEED")


def _observed_for(sizes, scale=1.0):
    keys = sorted(sizes)
    obs = {}
    for i, a in enumerate(keys):
        obs[a] = int(scale * sizes[a] * (sizes[a] - 1) / 2)
        for b in keys[i + 1:]:
            obs[" <-> ".join((a, b))] = int(scale * sizes[a] * sizes[b])
    return obs


def test_homogeneous_blocks_show_enrichment_one():
    result = enrichment_matrix(_observed_for(SIZES), SIZES)
    for key, cell in result.items():
        assert cell["enrichment"] == pytest.approx(1.0, abs=1e-3), key


def test_overconnected_pair_shows_highest_enrichment():
    obs = _observed_for(SIZES)
    x = obs["P1_GOD <-> P2_MIND"]
    m_original = sum(obs.values())
    obs["P1_GOD <-> P2_MIND"] *= 4
    result = enrichment_matrix(obs, SIZES)
    # Fixed-density null: inflating one cell raises M, attenuating its own
    # ratio to 4*m/(m + 3x) while every other cell drops below 1.
    expected_ratio = 4.0 * m_original / (m_original + 3 * x)
    assert result["P1_GOD <-> P2_MIND"]["enrichment"] == pytest.approx(
        expected_ratio, abs=1e-3)
    others = [c["enrichment"] for k, c in result.items()
              if k != "P1_GOD <-> P2_MIND"]
    assert all(o < 1.0 for o in others)


def test_missing_block_pair_reports_zero_observed():
    obs = _observed_for(SIZES)
    del obs["P1_GOD <-> P2_MIND"]
    result = enrichment_matrix(obs, SIZES)
    assert result["P1_GOD <-> P2_MIND"]["observed"] == 0
    assert result["P1_GOD <-> P2_MIND"]["enrichment"] == 0.0


def test_single_block_diagonal_only():
    sizes = {"P5_POWER": 10}
    result = enrichment_matrix({"P5_POWER": 45}, sizes)
    assert result["P5_POWER"]["enrichment"] == pytest.approx(1.0)
