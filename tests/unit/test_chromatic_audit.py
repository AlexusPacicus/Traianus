"""Unit tests for the chromatic audit tool (pure helpers, no SQLite/model)."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "experiments" / "tooling"))

from chromatic_audit import (
    effective_5d,
    find_collisions,
    sammon_stress,
    zone_channel_alignment,
)


def test_effective_5d_shape_and_rgb_range():
    rng = np.random.default_rng(3)
    X = rng.normal(size=(40, 16))
    out = effective_5d(X)
    assert out.shape == (40, 6)
    assert np.all(out[:, 2:5] >= -1e-12) and np.all(out[:, 2:5] <= 1 + 1e-12)


def test_find_collisions_separates_duplicates_from_real_collisions():
    # Genuine collision: (0,1) close in 2D, far in 384D. Stylistic duplicate:
    # (2,3) identical 384D vectors.
    pts2d = np.array([
        [0.0, 0.0],    # 0
        [0.01, 0.0],   # 1  close to 0 in 2D
        [5.0, 5.0],    # 2
        [5.02, 5.0],   # 3  duplicate of 2
        [9.0, 9.0],    # 4
        [0.0, 5.0],    # 5
    ])
    e = lambda k: np.eye(8)[k]
    pts8d = np.stack([e(0), -e(0), e(1), e(1), e(2), e(3)])
    collisions, duplicates = find_collisions(pts2d, pts8d)
    assert {(i, j) for i, j, _ in duplicates} == {(2, 3)}
    coll_pairs = {(i, j) for i, j, *_ in collisions}
    assert (0, 1) in coll_pairs
    assert all((i, j) not in coll_pairs for i, j, _ in duplicates)


def test_sammon_stress_zero_for_identical_distances():
    rng = np.random.default_rng(5)
    P = rng.normal(size=(20, 7))
    D = np.linalg.norm(P[:, None] - P[None, :], axis=2)
    assert sammon_stress(D, D.copy()) == pytest.approx(0.0, abs=1e-12)


def test_sammon_stress_increases_with_distortion():
    rng = np.random.default_rng(5)
    P = rng.normal(size=(30, 8))
    D = np.linalg.norm(P[:, None] - P[None, :], axis=2)
    noisy = D * (1 + rng.normal(scale=0.05, size=D.shape))
    worse = D * (1 + rng.normal(scale=0.50, size=D.shape))
    s_low = sammon_stress(D, noisy)
    s_high = sammon_stress(D, worse)
    assert s_low > 0 and s_high > s_low


def test_zone_alignment_detects_planted_correlation():
    labels = []
    for i in range(30):
        labels.append(f"PART2_MIND_P{24 + (i % 8):02d}_DEMO_01")   # soma
    for i in range(30):
        labels.append(f"PART2_MIND_DEF_{1 + (i % 7):02d}_C01")     # other
    rgb = np.zeros((60, 3))
    rgb[:30, 0] = 0.9   # R high exactly on soma
    rgb[30:, 0] = 0.1
    result = zone_channel_alignment(labels, rgb)
    soma = next(z for z in result["zones"] if z["zone"] == "soma")
    assert soma["r_red"] > 0.9
    assert soma["verdict"] == "confirmed"


def test_zone_alignment_refutes_when_anti_correlated():
    labels = ["PART2_MIND_P37_PROP"] * 10 + ["PART2_MIND_P01_PROP"] * 10
    rgb = np.zeros((20, 3))
    rgb[:10, 2] = 0.05   # potestas with LOW blue
    rgb[10:, 2] = 0.95
    result = zone_channel_alignment(labels, rgb)
    pot = next(z for z in result["zones"] if z["zone"] == "potestas")
    assert pot["b_blue"] < -0.9
    assert pot["verdict"] == "refuted"
