"""Spatial observables in one frame per epoch — pure, observational.

The frame (axis ranking by mean projection, ties by axis id) is fitted once on the nodes
present, frozen with the per-channel mean and sd, and shared by every node: the overview is one
map, not each node in its own coordinates (frontend/POC.md, "the overview has no shared frame").
Channels are the ones K6 measured and admitted (docs/methodology/instrument-audit/K6.md, data/refapp/K6_result.json):
  x = λ₁, y = ⟨v, ĉ₁⟩ → standardised, clipped to [-1, 1];  z = 0 (pending K8);
  l constant (author's choice); h from λ₃ and c from a₈ → [0, 1].
"""
import numpy as np
import pytest

from tools.experiments import k6_colour_predictability as k6
from traianus.geometry.polar_projector import PolarProjector
from traianus.geometry.spatial_observables import (
    CHANNELS,
    EPOCH_PROVENANCE,
    L_CONSTANT,
    derive_spatial_observables,
    fit_epoch_frame,
    rank_axes,
    raw_channels,
)

D = 384


def _basis(rng, k=8, d=D):
    return {f"AXIS_{i + 1}": rng.standard_normal(d) * (1.0 + i) for i in range(k)}


def _unit_rows(rng, n, d=D):
    x = rng.standard_normal((n, d))
    return x / np.linalg.norm(x, axis=1, keepdims=True)


@pytest.fixture
def rng():
    return np.random.default_rng(20260919)


def _k6_frame(vectors, basis):
    ids = sorted(basis)
    a = np.vstack([basis[i] for i in ids])
    a_hat = a / np.linalg.norm(a, axis=1, keepdims=True)
    order, _ = k6.rank_axes(vectors, a_hat, ids)
    projector = PolarProjector()
    return [ids[i] for i in order], k6.eval_channels(
        vectors, a_hat, k6.build_frame(a_hat, order, projector), projector
    )


class TestRanking:
    def test_ranking_matches_k6(self, rng):
        basis, v = _basis(rng), _unit_rows(rng, 300)
        assert list(rank_axes(v, basis)) == _k6_frame(v, basis)[0]

    def test_ties_break_by_axis_id(self):
        e = np.eye(D)
        basis = {"AXIS_2": e[0], "AXIS_1": e[1], "AXIS_3": e[2], "AXIS_4": e[3],
                 "AXIS_5": e[4], "AXIS_6": e[5], "AXIS_7": e[6], "AXIS_8": e[7]}
        v = (e[0] + e[1]) / np.sqrt(2.0)
        assert rank_axes(v[None, :], basis)[:2] == ("AXIS_1", "AXIS_2")


class TestRawChannels:
    def test_channels_are_the_ones_k6_measured(self, rng):
        basis, v = _basis(rng), _unit_rows(rng, 300)
        ranking = rank_axes(v, basis)
        ours = raw_channels(v, basis, ranking)
        theirs = _k6_frame(v, basis)[1]
        for name in CHANNELS:
            np.testing.assert_allclose(ours[name], theirs[name], rtol=1e-12, atol=1e-15)

    def test_one_frame_for_every_vector(self, rng):
        """Regression: the frame used to be chosen per node, from each vector's own top axes."""
        basis, v = _basis(rng), _unit_rows(rng, 50)
        ranking = rank_axes(v, basis)
        together = raw_channels(v, basis, ranking)
        for i in (0, 17, 49):
            alone = raw_channels(v[i], basis, ranking)
            for name in CHANNELS:
                assert alone[name] == pytest.approx(float(together[name][i]), rel=1e-12, abs=1e-15)

    def test_channels_are_unclipped(self):
        """Close poles give a short dipole, so |λ₁| exceeds 1; clipping is a rendering step."""
        e = np.eye(D)
        basis = {f"AXIS_{i + 1}": e[i] for i in range(8)}
        basis["AXIS_3"] = e[1] + 0.3 * e[2]
        ranking = tuple(sorted(basis))
        v = (e[1] - e[2]) / np.sqrt(2.0)
        w = e[1] - basis["AXIS_3"] / np.linalg.norm(basis["AXIS_3"])
        x = raw_channels(v, basis, ranking)["x"]
        assert x > 1.0
        assert x == pytest.approx(float(v @ w / (w @ w)), rel=1e-12)


class TestFrame:
    def test_fit_freezes_ranking_mean_and_population_sd(self, rng):
        basis, v = _basis(rng), _unit_rows(rng, 200)
        frame = fit_epoch_frame(v, basis, EPOCH_PROVENANCE)
        assert frame.epoch_provenance == EPOCH_PROVENANCE
        assert frame.ranking == rank_axes(v, basis)
        raw = raw_channels(v, basis, frame.ranking)
        for j, name in enumerate(CHANNELS):
            assert frame.mu[j] == pytest.approx(float(np.mean(raw[name])), rel=1e-12)
            assert frame.sigma[j] == pytest.approx(float(np.std(raw[name], ddof=0)), rel=1e-12)

    def test_fit_refuses_an_empty_population(self, rng):
        with pytest.raises(ValueError, match="empty"):
            fit_epoch_frame(np.empty((0, D)), _basis(rng), EPOCH_PROVENANCE)

    def test_fit_refuses_fewer_than_eight_axes(self, rng):
        with pytest.raises(ValueError, match="8 axes"):
            fit_epoch_frame(_unit_rows(rng, 10), _basis(rng, k=7), EPOCH_PROVENANCE)

    @pytest.mark.parametrize("pair", [(1, 2), (5, 6)])
    def test_fit_refuses_a_used_dipole_on_the_fallback(self, pair):
        """Dipole 1 (x) and dipole 3 (λ₃) must be contrasts; the operator's fallback is not one."""
        e = np.eye(D)
        axes = [3.0 * e[0], 2.0 * e[1], 1.9 * e[2], 1.5 * e[3], 1.4 * e[4], 1.2 * e[5],
                1.1 * e[6], 1.0 * e[7]]
        axes[pair[1]] = axes[pair[0]] * 0.999
        basis = {f"AXIS_{i + 1}": a for i, a in enumerate(axes)}
        v = np.ones(D) / np.sqrt(D)
        with pytest.raises(ValueError, match="fallback"):
            fit_epoch_frame(np.vstack([v, v]), basis, EPOCH_PROVENANCE)


class TestRoundingFloor:
    """A channel's population sd below the rounding bound of its own dot products is zero
    (regression: Linux CI, tests/unit/geometry/test_spatial_observables.py, 2026-09-23)."""

    def test_rows_differing_only_in_the_last_bits_are_zeroed(self, rng):
        basis = _basis(rng)
        base = _unit_rows(rng, 1)[0]
        v = np.tile(base, (5, 1))
        for i, idx in enumerate((0, 7, 100, 200, 383)):
            v[i, idx] = np.nextafter(v[i, idx], 1.0)
        frame = fit_epoch_frame(v, basis, EPOCH_PROVENANCE)
        assert frame.sigma == (0.0, 0.0, 0.0, 0.0)
        for row in v:
            obs = derive_spatial_observables(row, basis, frame)
            assert (obs["x"], obs["y"], obs["c"], obs["h"]) == (0.0, 0.0, 0.5, 0.5)

    def test_a_genuine_small_spread_is_not_zeroed(self, rng):
        basis = _basis(rng)
        base = _unit_rows(rng, 1)[0]
        direction = _unit_rows(rng, 1)[0]
        v = np.vstack([base + i * 1e-9 * direction for i in range(5)])
        frame = fit_epoch_frame(v, basis, EPOCH_PROVENANCE)
        raw = raw_channels(v, basis, frame.ranking)
        for j, name in enumerate(CHANNELS):
            assert frame.sigma[j] > 0.0
            assert frame.sigma[j] == pytest.approx(float(np.std(raw[name])), rel=1e-9)

    def test_non_degenerate_sigma_is_bit_identical_to_population_std(self, rng):
        basis, v = _basis(rng), _unit_rows(rng, 200)
        frame = fit_epoch_frame(v, basis, EPOCH_PROVENANCE)
        raw = raw_channels(v, basis, frame.ranking)
        for j, name in enumerate(CHANNELS):
            assert frame.sigma[j] == float(np.std(raw[name]))


class TestObservables:
    def test_mapping_of_every_channel(self, rng):
        basis, v = _basis(rng), _unit_rows(rng, 200)
        frame = fit_epoch_frame(v, basis, EPOCH_PROVENANCE)
        raw = raw_channels(v[3], basis, frame.ranking)
        obs = derive_spatial_observables(v[3], basis, frame)

        def s(name):
            j = CHANNELS.index(name)
            return float(np.clip((raw[name] - frame.mu[j]) / (frame.k_sigma * frame.sigma[j]), -1, 1))

        assert obs["x"] == pytest.approx(s("x"))
        assert obs["y"] == pytest.approx(s("y"))
        assert obs["z"] == 0.0
        assert obs["l"] == L_CONSTANT
        assert obs["h"] == pytest.approx((s("lambda_3") + 1.0) / 2.0)
        assert obs["c"] == pytest.approx((s("a_8") + 1.0) / 2.0)

    def test_ranges_and_finiteness(self, rng):
        basis, v = _basis(rng), _unit_rows(rng, 200)
        frame = fit_epoch_frame(v, basis, EPOCH_PROVENANCE)
        for row in _unit_rows(rng, 100):
            obs = derive_spatial_observables(row, basis, frame)
            assert all(isinstance(obs[k], float) and np.isfinite(obs[k]) for k in obs)
            assert -1.0 <= obs["x"] <= 1.0 and -1.0 <= obs["y"] <= 1.0
            assert 0.0 <= obs["c"] <= 1.0 and 0.0 <= obs["h"] <= 1.0

    def test_frozen_frame_does_not_move_a_node_when_others_arrive(self, rng):
        """R1: with the frame frozen, a node's observables depend on its vector alone."""
        basis, v = _basis(rng), _unit_rows(rng, 200)
        frame = fit_epoch_frame(v, basis, EPOCH_PROVENANCE)
        before = derive_spatial_observables(v[0], basis, frame)
        _ = [derive_spatial_observables(r, basis, frame) for r in _unit_rows(rng, 50)]
        assert derive_spatial_observables(v[0], basis, frame) == before

    def test_nodes_spread_over_the_viewport(self, rng):
        basis, v = _basis(rng), _unit_rows(rng, 500)
        frame = fit_epoch_frame(v, basis, EPOCH_PROVENANCE)
        xs = [derive_spatial_observables(r, basis, frame)["x"] for r in v]
        assert max(xs) - min(xs) > 1.0

    def test_degenerate_spread_maps_to_the_centre(self, rng):
        basis = _basis(rng)
        v = np.vstack([_unit_rows(rng, 1)] * 5)
        frame = fit_epoch_frame(v, basis, EPOCH_PROVENANCE)
        obs = derive_spatial_observables(v[0], basis, frame)
        assert (obs["x"], obs["y"], obs["c"], obs["h"]) == (0.0, 0.0, 0.5, 0.5)
