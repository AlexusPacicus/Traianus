"""Unit tests of tools/experiments/k6_colour_predictability.py.

Specification: frontend/audits/K6.md (revision 6), frontend/audits/contracts.md §0 and §1,
frontend/audits/derivations.md (D2, D4, D6, D7, D8, D11). Synthetic inputs only: CI has no
.data/, and the measurement is never run on the real artefact here.
"""

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pytest

from tools.experiments import k6_colour_predictability as k6
from traianus.geometry.polar_projector import PolarProjector

D = 384

# First component of g_1, g_2, g_3 (deciding null, Generator(PCG64(20260918)), numpy 2.4.1).
# Pins the stream (NEP 19 does not guarantee it across numpy versions).
RECORDED_G_FIRST = (-1.4765772923017222, 0.21292362335480605, -0.5764113739053777)


def _unit_rows(rng, n, d=D):
    x = rng.standard_normal((n, d))
    return x / np.linalg.norm(x, axis=1, keepdims=True)


def _unit_rows_f32(rng, n, d=D):
    x = rng.standard_normal((n, d)).astype(np.float32)
    return x / np.linalg.norm(x, axis=1, keepdims=True).astype(np.float32)


def _labels(n):
    return [{"label": f"L{i}", "part": "P1"} for i in range(n)]


def _axis_ids():
    return [f"AXIS_{k}" for k in range(1, 9)]


def _flip_bit_f32(v32, row, col, bit):
    out = v32.copy()
    out.view(np.uint32)[row, col] ^= np.uint32(1 << bit)
    return out


@pytest.fixture
def rng():
    return np.random.default_rng(12345)


# Threshold, split, rng --------------------------------------------------------------------------


def test_threshold_returns_the_989th_smallest_value():
    values = np.arange(1, 1001, dtype=np.float64)
    assert k6.threshold(values) == 989.0
    assert k6.threshold(values[::-1].copy()) == 989.0


def test_threshold_admits_12_of_1001_ranks():
    # D8: a value exchangeable with the 1,000 nulls exceeds the 989th with probability 12/1001.
    nulls = np.arange(1, 1001, dtype=np.float64)
    tau = k6.threshold(nulls)
    exceeding = sum(1 for rank in range(1, 1002) if rank - 0.5 > tau)
    assert exceeding == 12


def test_fit_and_eval_are_even_and_odd_indices_and_disjoint():
    fit, ev = k6.split_fit_eval(2221)
    assert np.array_equal(fit, np.arange(0, 2221, 2))
    assert np.array_equal(ev, np.arange(1, 2221, 2))
    assert len(fit) == 1111 and len(ev) == 1110
    assert not set(fit.tolist()) & set(ev.tolist())
    assert sorted(fit.tolist() + ev.tolist()) == list(range(2221))


def test_first_three_deciding_null_draws_match_recorded_values():
    g = k6.draw_deciding_null(k6.make_rng(), k6.N_NULL, D)
    assert g.shape == (1000, D)
    assert (g[0, 0], g[1, 0], g[2, 0]) == pytest.approx(RECORDED_G_FIRST, rel=1e-12, abs=0.0)


def test_deciding_null_is_drawn_first_and_sigma_null_after(rng, monkeypatch):
    fresh = k6.make_rng().bit_generator.state
    seen = {}
    real_deciding, real_sigma = k6.draw_deciding_null, k6.draw_sigma_null

    def spy_deciding(r, n, d):
        seen["deciding"] = r.bit_generator.state
        return real_deciding(r, n, d)

    def spy_sigma(r, xc, n):
        seen["sigma"] = r.bit_generator.state
        return real_sigma(r, xc, n)

    monkeypatch.setattr(k6, "draw_deciding_null", spy_deciding)
    monkeypatch.setattr(k6, "draw_sigma_null", spy_sigma)
    v = _unit_rows(rng, 60)
    a_hat = _unit_rows(rng, 8)
    k6.measure(v, a_hat, _axis_ids(), k6.make_rng(), PolarProjector())

    advanced = k6.make_rng()
    for _ in range(k6.N_NULL):
        advanced.standard_normal(D)
    assert seen["deciding"] == fresh
    assert seen["sigma"] == advanced.bit_generator.state


def test_null_directions_are_unit_and_orthogonal_to_the_anchor(rng):
    c1 = _unit_rows(rng, 1)[0]
    g = rng.standard_normal((5, D))
    w = k6.null_directions(g, c1)
    assert np.allclose(np.linalg.norm(w, axis=1), 1.0, atol=1e-12)
    assert np.allclose(w @ c1, 0.0, atol=1e-12)


# Basis and regression ---------------------------------------------------------------------------


def _z(u):
    return (u - u.mean()) / u.std()


HEAD = ["1", "z(x)", "z(y)", "z(x)^2", "z(y)^2", "z(x)z(y)"]


def test_basis_has_exactly_the_listed_columns_in_order_standardised(rng):
    x, y = 3.0 + 0.01 * rng.standard_normal(50), -2.0 + 5.0 * rng.standard_normal(50)
    c1, c2 = rng.standard_normal(50), 1e-3 * rng.standard_normal(50)
    xt, yt = _z(x), _z(y)
    for selected, names in (
        ([], []),
        ([("lambda_2", c1)], ["z(c_1:lambda_2)"]),
        ([("lambda_2", c1), ("a_8", c2)], ["z(c_1:lambda_2)", "z(c_2:a_8)"]),
    ):
        b, cols = k6.design_basis(x, y, selected)
        expected = [np.ones(50), xt, yt, xt**2, yt**2, xt * yt] + [_z(c) for _, c in selected]
        assert cols == HEAD + names
        assert b.shape == (50, 6 + len(selected))
        for j, col in enumerate(expected):
            assert np.allclose(b[:, j], col, rtol=0.0, atol=1e-12)
        for j in [1, 2, *range(6, b.shape[1])]:
            assert abs(b[:, j].mean()) < 1e-12
            assert b[:, j].std() == pytest.approx(1.0, abs=1e-12)


def test_standardised_basis_gives_the_raw_basis_r_squared(rng):
    # D6: standardising x, y and c_j maps span(B_s) onto the raw span; R² is unchanged.
    n = 300
    x, y, c = rng.uniform(-1, 1, n), rng.uniform(-1, 1, n), rng.standard_normal(n)
    u = x - 0.5 * y**2 + 0.3 * c + rng.standard_normal(n)
    raw = np.column_stack([np.ones(n), x, y, x**2, y**2, x * y, c])
    assert np.linalg.cond(raw) < 1e3
    b, _ = k6.design_basis(x, y, [("c", c)])
    assert k6.r_squared(u, b)[0] == pytest.approx(k6.r_squared(u, raw)[0], abs=1e-12)


def test_r_squared_is_centred_and_adjusted(rng):
    n = 200
    x = rng.standard_normal(n)
    b = np.column_stack([np.ones(n), x])
    u = 3.0 + 2.0 * x + rng.standard_normal(n)
    r2, adj = k6.r_squared(u, b)
    beta, *_ = np.linalg.lstsq(b, u, rcond=None)
    res = u - b @ beta
    expected = 1.0 - (res @ res) / ((u - u.mean()) @ (u - u.mean()))
    assert r2 == pytest.approx(expected, abs=1e-12)
    assert adj == pytest.approx(1.0 - (1.0 - expected) * (n - 1) / (n - 2), abs=1e-12)
    # D6: affine maps of the response leave R² unchanged.
    assert k6.r_squared(-4.0 * u + 7.0, b)[0] == pytest.approx(r2, abs=1e-12)


def test_r_squared_refuses_a_constant_response():
    b = np.column_stack([np.ones(10), np.arange(10.0)])
    with pytest.raises(ValueError, match="constant"):
        k6.r_squared(np.full(10, 2.0), b)


def test_r_squared_refuses_a_non_finite_result():
    b = np.column_stack([np.ones(10), np.arange(10.0)])
    u = np.arange(10.0) ** 2
    u[3] = np.nan
    with pytest.raises(ValueError, match="non-finite R"):
        k6.r_squared(u, b)


def test_calibration_control_hits_rho_exactly_and_detects_a_wrong_basis(rng):
    n = 300
    x, y = rng.uniform(-1, 1, n), rng.uniform(-1, 1, n)
    b, _ = k6.design_basis(x, y, [])
    h = np.tanh(np.sqrt(np.abs(1.0 - y**2 - 0.5 * x**2)))
    n1 = rng.standard_normal(n)
    for rho in (0.0, 0.01, 0.5, 0.99):
        m = k6.calibration_control(h, n1, b, rho)
        assert abs(k6.r_squared(m, b)[0] - rho) <= k6.CONTROL_TOL
    m = k6.calibration_control(h, n1, b, 0.5)
    assert abs(k6.r_squared(m, np.delete(b, 4, axis=1))[0] - 0.5) > k6.CONTROL_TOL


# Sequential selection with planted channels -----------------------------------------------------


def _planted(rng, n=400):
    x, y = rng.uniform(-1, 1, n), rng.uniform(-1, 1, n)
    b1, _ = k6.design_basis(x, y, [])
    raw = rng.standard_normal(n)
    indep = raw - k6.ols_fit(raw, b1)
    quad = 1.0 + x**2 - 2.0 * x * y
    nulls = rng.standard_normal((k6.N_NULL, n))
    sigma = rng.standard_normal((k6.N_NULL, n))
    h = x**2 + y**2
    return x, y, indep, quad, nulls, sigma, h


def test_selection_discards_predictable_selects_independent_and_logs_empty_step(rng):
    x, y, indep, quad, nulls, sigma, h = _planted(rng)
    cands = [("quad", quad), ("indep", indep), ("copy", indep.copy())]
    out = k6.run_selection(x, y, cands, nulls, sigma, h)

    s1, s2, s3 = out["steps"]
    assert [(c["name"], c["outcome"]) for c in s1["candidates"]] == [
        ("quad", "discarded"),
        ("indep", "selected"),
        ("copy", "not_reached"),
    ]
    assert s1["candidates"][0]["r2"] > s1["tau"]
    assert s1["candidates"][1]["r2"] <= s1["tau"]
    assert "r2" not in s1["candidates"][2]
    assert s1["selected"] == "indep"

    assert [(c["name"], c["outcome"]) for c in s2["candidates"]] == [("copy", "discarded")]
    assert s2["candidates"][0]["r2"] == pytest.approx(1.0, abs=1e-9)
    assert s2["selected"] == "none"

    assert s3 == {"step": 3, "ran": False, "reason": "no remaining candidate", "selected": "none"}
    assert out["selected"] == ["indep"]
    assert out["constant_channels"] == 2


def test_selection_admits_a_candidate_equal_to_the_threshold(rng):
    x, y, _, _, nulls, sigma, h = _planted(rng)
    b1, _ = k6.design_basis(x, y, [])
    r2 = np.array([k6.r_squared(u, b1)[0] for u in nulls])
    order = np.argsort(r2, kind="stable")
    at_tau, above_tau = nulls[order[988]].copy(), nulls[order[989]].copy()
    assert r2[order[989]] > r2[order[988]]
    out = k6.run_selection(x, y, [("above", above_tau), ("at", at_tau)], nulls, sigma, h)
    s1 = out["steps"][0]
    assert s1["tau"] == r2[order[988]]
    assert [(c["name"], c["outcome"]) for c in s1["candidates"]] == [
        ("above", "discarded"),
        ("at", "selected"),
    ]
    assert s1["candidates"][1]["margin"] == 0.0


def test_basis_at_each_step_is_augmented_by_the_selected_channels_in_order(rng, monkeypatch):
    x, y, indep, quad, nulls, sigma, h = _planted(rng)
    other = rng.standard_normal(len(x))
    calls = []
    real = k6.design_basis

    def spy(xx, yy, selected):
        b, cols = real(xx, yy, selected)
        calls.append((cols, b))
        return b, cols

    monkeypatch.setattr(k6, "design_basis", spy)
    out = k6.run_selection(x, y, [("indep", indep), ("other", other)], nulls, sigma, h)
    assert out["selected"][0] == "indep"
    assert calls[0][0] == HEAD
    assert calls[1][0] == [*HEAD, "z(c_1:indep)"]
    assert np.allclose(calls[1][1][:, 6], _z(indep), rtol=0.0, atol=1e-12)
    assert out["steps"][1]["basis_columns"] == calls[1][0]
    assert out["steps"][1]["cond"] == np.linalg.cond(calls[1][1])


def test_candidates_nulls_and_controls_share_one_regression_function(rng, monkeypatch):
    x, y, indep, quad, nulls, sigma, h = _planted(rng)
    cands = [("quad", quad), ("indep", indep), ("copy", indep.copy())]
    responses = []
    real = k6.r_squared

    def spy(u, b):
        responses.append(np.array(u, copy=True))
        return real(u, b)

    monkeypatch.setattr(k6, "r_squared", spy)
    out = k6.run_selection(x, y, cands, nulls, sigma, h)
    # step 1: 1000 + 1000 nulls, 2 candidates, positive control, 2 controls; step 2: 2000 + 1 + 2.
    assert len(responses) == 2005 + 2003
    assert any(np.array_equal(r, quad) for r in responses)
    assert any(np.array_equal(r, h) for r in responses)
    assert sum(np.array_equal(r, nulls[0]) for r in responses) == 2
    assert sum(np.array_equal(r, sigma[-1]) for r in responses) == 2
    for step in out["steps"][:2]:
        for side in ("in", "out"):
            assert step["controls"][side]["deviation"] <= k6.CONTROL_TOL


def test_calibration_controls_land_on_their_sides_at_every_step(rng):
    x, y, indep, quad, nulls, sigma, h = _planted(rng)
    out = k6.run_selection(x, y, [("indep", indep), ("quad", quad)], nulls, sigma, h)
    for step in out["steps"]:
        if not step["ran"]:
            continue
        tau = step["tau"]
        cin, cout = step["controls"]["in"], step["controls"]["out"]
        assert cin["rho"] == tau / 2 and cout["rho"] == (1 + tau) / 2
        assert cin["r2"] <= tau and cin["side_ok"] and cin["exact"]
        assert cout["r2"] > tau and cout["side_ok"] and cout["exact"]
    assert out["positive_control"]["passes"]
    valid, first, _ = k6.assess_validity([False, False, False], out)
    assert valid and first is None


def test_unpredictable_positive_control_invalidates_the_instrument(rng):
    x, y, indep, _, nulls, sigma, _ = _planted(rng)
    h = rng.standard_normal(len(x))
    out = k6.run_selection(x, y, [("indep", indep)], nulls, sigma, h)
    assert not out["positive_control"]["passes"]
    valid, first, failed = k6.assess_validity([False, False, False], out)
    assert not valid and first == "positive_control" and failed[0] == "positive_control"


def test_tiny_raw_scale_no_longer_fails_the_conditioning_gate(rng):
    x, y, indep, _, nulls, sigma, h = _planted(rng)
    xs = 1e-3 * x
    raw = np.column_stack([np.ones(len(x)), xs, y, xs**2, y**2, xs * y])
    assert np.linalg.cond(raw) > k6.COND_MAX
    out = k6.run_selection(xs, y, [("indep", indep)], nulls, sigma, h)
    assert out["steps"][0]["cond"] < k6.COND_MAX
    assert "cond_standardised" not in out["steps"][0]
    valid, first, failed = k6.assess_validity([False, False, False], out)
    assert valid and first is None and failed == []


def test_collinear_standardised_columns_invalidate_the_instrument(rng):
    # A two-valued x makes z(x)² an affine function of z(x): the standardised basis is singular.
    x, y, indep, _, nulls, sigma, h = _planted(rng)
    out = k6.run_selection(np.where(x > 0, 1.0, -1.0), y, [("indep", indep)], nulls, sigma, h)
    assert out["steps"][0]["cond"] > k6.COND_MAX
    valid, first, _ = k6.assess_validity([False, False, False], out)
    assert not valid and first == "step_1_cond"


def test_a_nan_candidate_raises_instead_of_being_discarded(rng):
    x, y, indep, _, nulls, sigma, h = _planted(rng)
    bad = indep.copy()
    bad[7] = np.nan
    with pytest.raises(ValueError, match="non-finite R"):
        k6.run_selection(x, y, [("bad", bad), ("indep", indep)], nulls, sigma, h)


def test_all_candidates_failing_leaves_three_constant_channels(rng):
    x, y, _, quad, nulls, sigma, h = _planted(rng)
    out = k6.run_selection(x, y, [("quad", quad), ("q2", x * y)], nulls, sigma, h)
    assert out["selected"] == [] and out["constant_channels"] == 3
    assert [s["ran"] for s in out["steps"]] == [True, False, False]


# Frame, ranking, channels -----------------------------------------------------------------------


def test_ranking_is_descending_by_fit_mean_with_ties_by_axis_id(rng):
    a_hat = _unit_rows(rng, 8)
    a_hat[5] = a_hat[2]
    v = _unit_rows(rng, 40)
    order, means = k6.rank_axes(v, a_hat, _axis_ids())
    assert np.allclose(means, (v @ a_hat.T).mean(axis=0), rtol=0.0, atol=1e-15)
    ranked = [means[i] for i in order]
    assert ranked == sorted(ranked, reverse=True)
    assert order.index(2) + 1 == order.index(5)


def test_frame_poles_follow_rank_and_fallback_is_flagged_per_dipole(rng):
    a_hat = _unit_rows(rng, 8)
    a_hat[4] = a_hat[3]
    order = list(range(8))
    frame = k6.build_frame(a_hat, order, PolarProjector())
    c1 = a_hat[0]
    assert np.array_equal(frame["c1_hat"], c1 / np.linalg.norm(c1))
    w1 = k6.perp(a_hat[1], frame["c1_hat"]) - k6.perp(a_hat[2], frame["c1_hat"])
    assert np.allclose(frame["frames"][0].v_dipole, w1, atol=1e-15)
    assert frame["fallback"] == [False, True, False]
    assert np.allclose(frame["p8"], k6.perp(a_hat[7], frame["c1_hat"]), atol=1e-15)
    assert k6.candidate_names(frame["fallback"]) == ["lambda_3", "a_8", "l"]


def test_rank_8_axis_parallel_to_the_anchor_raises():
    # P⊥â_(8) = 0 exactly: e_0 − ⟨e_0, e_0⟩e_0; mirrors polar_projector.py:241-245.
    a_hat = np.eye(8, D)
    a_hat[7] = a_hat[0]
    with pytest.raises(ValueError, match="rank-8 axis"):
        k6.build_frame(a_hat, list(range(8)), PolarProjector())


def test_channels_are_unclipped_and_h_comes_from_the_operator(rng):
    a_hat = _unit_rows(rng, 8)
    a_hat[2] = 0.98 * a_hat[1] + 0.02 * a_hat[2]
    a_hat[2] /= np.linalg.norm(a_hat[2])
    frame = k6.build_frame(a_hat, list(range(8)), PolarProjector())
    w1 = frame["frames"][0].v_dipole
    v = np.vstack([_unit_rows(rng, 30), (w1 / np.linalg.norm(w1))[None, :]])
    ch = k6.eval_channels(v, a_hat, frame, PolarProjector())
    assert np.allclose(ch["x"], v @ w1 / (w1 @ w1), atol=1e-12)
    assert abs(ch["x"][-1]) > 1.0
    assert np.allclose(ch["y"], v @ frame["c1_hat"], atol=1e-15)
    p8 = frame["p8"]
    assert np.allclose(ch["a_8"], v @ p8 / (p8 @ p8), atol=1e-12)
    assert np.allclose(ch["l"], 1.0 / (1.0 + np.var(v @ a_hat.T, axis=1, ddof=0)), atol=1e-15)
    expected_h = [math.tanh(PolarProjector().evaluate(r, frame["frames"][0], 0)[2]) for r in v]
    assert np.allclose(ch["h"], expected_h, atol=0.0, rtol=0.0)


def test_dipole_one_on_the_fallback_stops_the_run(rng):
    a_hat = _unit_rows(rng, 8)
    a_hat[2] = a_hat[1]
    v = 3.0 * a_hat[0] + 2.0 * a_hat[1] + 0.05 * rng.standard_normal((60, D))
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    out = k6.measure(v, a_hat, _axis_ids(), k6.make_rng(), PolarProjector())
    assert out["ranking_fit"][:3] == ["AXIS_1", "AXIS_2", "AXIS_3"]
    assert out["fallback"]["dipole_1"] is True
    assert out["valid"] is False and out["first_failed_condition"] == "dipole_1_fallback"
    assert "steps" not in out


# Integrity: file layer --------------------------------------------------------------------------


def _write_inputs(tmp_path, v32, labels, axes):
    emb, lab, ax = tmp_path / "embeddings.npy", tmp_path / "labels.json", tmp_path / "axes.json"
    np.save(emb, v32)
    lab.write_text(json.dumps(labels), encoding="utf-8")
    ax.write_text(json.dumps(axes), encoding="utf-8")
    return emb, lab, ax


def _axes_json(a):
    return [
        {"id": i, "simbolo": "s", "tag": "t", "vector": row.tolist()}
        for i, row in zip(_axis_ids(), a)
    ]


def _digests(*paths):
    return {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def _flip_file_bit(path, pos, bit):
    data = bytearray(path.read_bytes())
    data[pos] ^= 1 << bit
    path.write_bytes(bytes(data))


def test_digest_check_accepts_intact_files_and_refuses_any_single_bit_flip(tmp_path, rng):
    v32 = _unit_rows_f32(rng, 6)
    paths = _write_inputs(tmp_path, v32, _labels(6), _axes_json(_unit_rows(rng, 8)))
    expected = _digests(*paths)
    k6.check_digests(expected)

    emb = paths[0]
    raw = emb.read_bytes()
    data_start = 10 + int.from_bytes(raw[8:10], "little")
    for path in paths:
        size = path.stat().st_size
        positions = {0, size - 1, int(rng.integers(0, size))}
        if path == emb:
            positions |= {20, data_start}
        for pos in sorted(positions):
            original = path.read_bytes()
            _flip_file_bit(path, pos, int(rng.integers(0, 8)))
            with pytest.raises(k6.IntegrityError, match=path.name):
                k6.check_digests(expected)
            path.write_bytes(original)
    k6.check_digests(expected)


def test_run_refuses_a_mismatched_digest_before_writing(tmp_path, rng):
    v32 = _unit_rows_f32(rng, 6)
    paths = _write_inputs(tmp_path, v32, _labels(6), _axes_json(_unit_rows(rng, 8)))
    expected = _digests(*paths)
    expected[paths[1]] = "0" * 64
    out = tmp_path / "out" / "K6_result.json"
    with pytest.raises(k6.IntegrityError, match="labels.json"):
        k6.run(*paths, expected, out)
    assert not out.exists()


def test_run_parses_the_bytes_it_hashed(tmp_path, rng, monkeypatch):
    # Each input is swapped on disk right after its first read: a second read cannot pass.
    n = 40
    v32, a = _unit_rows_f32(rng, n), _unit_rows(rng, 8)
    paths = _write_inputs(tmp_path, v32, _labels(n), _axes_json(a))
    expected = _digests(*paths)
    (tmp_path / "alt").mkdir()
    alt_labels = [{"label": f"M{i}", "part": "P2"} for i in range(n)]
    alt_paths = _write_inputs(tmp_path / "alt", _unit_rows_f32(rng, n), alt_labels,
                              _axes_json(_unit_rows(rng, 8)))
    swap = {p: q.read_bytes() for p, q in zip(paths, alt_paths)}
    real_read = Path.read_bytes
    reads = []

    def spy(self):
        data = real_read(self)
        reads.append(Path(self))
        if Path(self) in swap:
            Path(self).write_bytes(swap[Path(self)])
        return data

    seen = {}

    def fake_measure(v, a_hat, axis_ids, rng_, projector):
        seen.update(v=v, a_hat=a_hat)
        return {}

    monkeypatch.setattr(Path, "read_bytes", spy)
    monkeypatch.setattr(k6, "measure", fake_measure)
    k6.run(*paths, expected, tmp_path / "out.json")
    v64 = v32.astype(np.float64)
    assert np.allclose(seen["v"], v64 / np.linalg.norm(v64, axis=1, keepdims=True), atol=1e-15)
    assert np.allclose(seen["a_hat"], a / np.linalg.norm(a, axis=1, keepdims=True), atol=1e-15)
    assert [reads.count(p) for p in paths] == [1, 1, 1]


# Integrity: null elimination and memory layer ---------------------------------------------------


def _valid_inputs(rng, n=6):
    return _unit_rows_f32(rng, n), _labels(n), _axis_ids(), _unit_rows(rng, 8)


def test_validation_accepts_clean_inputs(rng):
    k6.validate_inputs(*_valid_inputs(rng))


@pytest.mark.parametrize(
    "corrupt, match",
    [
        (lambda v, lab, ids, a: v.__setitem__((2, 5), np.nan), "row 2"),
        (lambda v, lab, ids, a: v.__setitem__((3, 0), np.inf), "row 3"),
        (lambda v, lab, ids, a: v.__setitem__((1, 7), v[1, 7] + np.float32(0.01)), "row 1"),
        (lambda v, lab, ids, a: lab[4].__setitem__("label", None), "label 4"),
        (lambda v, lab, ids, a: lab[0].__setitem__("label", ""), "label 0"),
        (lambda v, lab, ids, a: lab[5].__setitem__("label", "L1"), "label 5"),
        (lambda v, lab, ids, a: lab[2].__setitem__("part", None), "label 2"),
        (lambda v, lab, ids, a: lab[1].pop("part"), "label 1"),
        (lambda v, lab, ids, a: lab[3].__setitem__("part", ""), "label 3"),
        (lambda v, lab, ids, a: ids.__setitem__(3, "AXIS_2"), "axis AXIS_2: duplicate"),
        (lambda v, lab, ids, a: lab.pop(), "count"),
        (lambda v, lab, ids, a: a.__setitem__((6, 3), np.nan), "AXIS_7"),
        (lambda v, lab, ids, a: a.__setitem__(1, 0.0), "AXIS_2"),
    ],
)
def test_null_elimination_names_the_row_or_key(rng, corrupt, match):
    v, lab, ids, a = _valid_inputs(rng)
    corrupt(v, lab, ids, a)
    with pytest.raises(ValueError, match=match):
        k6.validate_inputs(v, lab, ids, a)


def test_null_elimination_requires_eight_axes_of_384(rng):
    v, lab, ids, a = _valid_inputs(rng)
    with pytest.raises(ValueError, match="8 axes"):
        k6.validate_inputs(v, lab, ids[:7], a[:7])
    with pytest.raises(ValueError, match="384"):
        k6.validate_inputs(v, lab, ids, a[:, :383])


def test_memory_flip_of_the_exponent_msb_is_caught(rng):
    v, lab, ids, a = _valid_inputs(rng)
    col = int(rng.integers(0, D))
    flipped = _flip_bit_f32(v, 2, col, 30)
    assert abs(flipped[2, col]) >= 2.0
    with pytest.raises(ValueError, match="row 2"):
        k6.validate_inputs(flipped, lab, ids, a)


def _lsb_threshold(factor):
    # ‖v‖² changes by (factor² − 1)·t²; caught iff ‖v‖ leaves 1 ± NORM_TOL.
    tol = k6.NORM_TOL
    if factor > 1:
        return math.sqrt(((1 + tol) ** 2 - 1) / (factor**2 - 1))
    return math.sqrt((1 - (1 - tol) ** 2) / (1 - factor**2))


def _row_with_component(rng, t, col=7):
    v = rng.standard_normal(D)
    v[col] = 0.0
    v *= math.sqrt(1.0 - t * t) / np.linalg.norm(v)
    v[col] = t
    return v.astype(np.float32)


def test_exponent_lsb_thresholds_are_derived():
    assert _lsb_threshold(2.0) == pytest.approx(4.4722e-3, rel=1e-3)
    assert _lsb_threshold(0.5) == pytest.approx(8.9441e-3, rel=1e-3)


@pytest.mark.parametrize("t", [0.01, 0.02, -0.03, 0.2])
def test_memory_flip_of_the_exponent_lsb_is_caught_above_the_derived_magnitude(rng, t):
    v, lab, ids, a = _valid_inputs(rng)
    v[3] = _row_with_component(rng, t)
    k6.validate_inputs(v, lab, ids, a)
    flipped = _flip_bit_f32(v, 3, 7, 23)
    factor = float(flipped[3, 7] / v[3, 7])
    assert factor in (2.0, 0.5)
    assert abs(t) > _lsb_threshold(factor)
    with pytest.raises(ValueError, match="row 3"):
        k6.validate_inputs(flipped, lab, ids, a)


@pytest.mark.parametrize("t", [0.002, -0.004])
def test_memory_flip_of_the_exponent_lsb_passes_below_the_derived_magnitude(rng, t):
    v, lab, ids, a = _valid_inputs(rng)
    v[3] = _row_with_component(rng, t)
    flipped = _flip_bit_f32(v, 3, 7, 23)
    factor = float(flipped[3, 7] / v[3, 7])
    assert abs(t) < _lsb_threshold(factor)
    k6.validate_inputs(flipped, lab, ids, a)


@pytest.mark.parametrize("t", [0.0, 2.0**-140])
def test_memory_flip_of_the_exponent_lsb_of_a_zero_or_subnormal_component_passes(rng, t):
    # Exponent field 0 → 1: the component becomes a small normal (≈ 2⁻¹²⁶), far below the bound.
    v, lab, ids, a = _valid_inputs(rng)
    v[3] = _row_with_component(rng, t)
    assert float(v[3, 7]) == t
    flipped = _flip_bit_f32(v, 3, 7, 23)
    assert 2.0**-126 <= float(flipped[3, 7]) < 2.0**-125
    k6.validate_inputs(flipped, lab, ids, a)


def _mantissa_bound(bit):
    # Bit k (1 ≤ k ≤ 22) changes |v_i| by a relative r ≤ 2^(k−23); ‖v‖² by at most v_i²(2r + r²).
    # From ‖v‖ = 1, detection needs |v_i| ≥ √((1 − (1 − tol)²) / (2r + r²)).
    r = 2.0 ** (bit - 23)
    return math.sqrt((1 - (1 - k6.NORM_TOL) ** 2) / (2 * r + r * r))


def test_mantissa_bounds_are_derived():
    assert _mantissa_bound(22) == pytest.approx(6.928e-3, rel=1e-3)
    assert _mantissa_bound(8) < 1.0 < _mantissa_bound(7)


@pytest.mark.parametrize("t", [0.005, -0.006])
def test_memory_flip_of_mantissa_bit_22_passes_below_the_derived_bound(rng, t):
    v, lab, ids, a = _valid_inputs(rng)
    v[3] = _row_with_component(rng, t)
    assert abs(t) < _mantissa_bound(22)
    k6.validate_inputs(_flip_bit_f32(v, 3, 7, 22), lab, ids, a)


@pytest.mark.parametrize("t", [0.03, -0.2])
def test_memory_flip_of_mantissa_bit_22_is_caught_well_above_the_bound(rng, t):
    # Bit 22 changes |v_i| by a relative r ∈ (1/4, 1/2]: ‖v‖² moves by ≥ 0.4375·t² > 6e-5.
    v, lab, ids, a = _valid_inputs(rng)
    v[3] = _row_with_component(rng, t)
    k6.validate_inputs(v, lab, ids, a)
    with pytest.raises(ValueError, match="row 3"):
        k6.validate_inputs(_flip_bit_f32(v, 3, 7, 22), lab, ids, a)


def test_memory_flip_of_the_sign_bit_is_a_declared_blind_spot(rng):
    # A sign flip preserves ‖v‖ exactly: no semantic check sees it, only the file digest.
    v, lab, ids, a = _valid_inputs(rng)
    col = int(rng.integers(0, D))
    flipped = _flip_bit_f32(v, 2, col, 31)
    assert flipped[2, col] == -v[2, col]
    k6.validate_inputs(flipped, lab, ids, a)


def test_memory_flip_of_the_low_mantissa_bit_is_a_declared_blind_spot(rng):
    v, lab, ids, a = _valid_inputs(rng)
    col = int(rng.integers(0, D))
    flipped = _flip_bit_f32(v, 2, col, 0)
    assert flipped[2, col] != v[2, col]
    assert abs(float(flipped[2, col]) - float(v[2, col])) < 1e-7
    k6.validate_inputs(flipped, lab, ids, a)


# End to end on synthetic files ------------------------------------------------------------------


def test_run_writes_the_result_json_as_the_contract_states(tmp_path, rng):
    n = 120
    v32 = _unit_rows_f32(rng, n)
    paths = _write_inputs(tmp_path, v32, _labels(n), _axes_json(_unit_rows(rng, 8)))
    expected = _digests(*paths)
    out = tmp_path / "data" / "refapp" / "K6_result.json"
    result = k6.run(*paths, expected, out)

    text = out.read_text(encoding="utf-8")
    assert "\r" not in text
    assert text == json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n"
    assert json.loads(text) == result
    assert result["digests"] == {p.name: d for p, d in expected.items()}
    for key in (
        "environment", "ranking_fit", "ranking_full", "rankings_match", "fallback", "steps",
        "positive_control", "clip_fractions", "valid", "first_failed_condition", "selected",
    ):
        assert key in result
    assert len(result["steps"]) == 3
    assert result["steps"][0]["ran"] is True
    for arm in ("x", "lambda_2", "lambda_3", "null_deciding", "null_sigma"):
        assert 0.0 <= result["clip_fractions"][arm] <= 1.0

    again = tmp_path / "again.json"
    k6.run(*paths, expected, again)
    assert again.read_bytes() == out.read_bytes()


def _validity_selection(**fail):
    def step(s):
        return {
            "step": s, "ran": True, "cond_ok": not fail.get(f"cond_{s}"),
            "controls": {side: {"exact": not fail.get(f"{side}_exact_{s}"),
                                "side_ok": not fail.get(f"{side}_side_{s}")}
                         for side in ("in", "out")},
        }
    return {"steps": [step(1), step(2), {"step": 3, "ran": False}],
            "positive_control": {"passes": not fail.get("positive")}}


def test_validity_lists_every_failed_condition_in_the_record_order():
    every = {f"{k}_{s}": True for s in (1, 2) for k in
             ("cond", "in_exact", "in_side", "out_exact", "out_side")}
    valid, first, failed = k6.assess_validity([True, False, False],
                                              _validity_selection(positive=True, **every))
    assert not valid and first == "dipole_1_fallback"
    assert failed == [
        "dipole_1_fallback",
        "step_1_cond", "positive_control",
        "step_1_control_in_exact", "step_1_control_in_side",
        "step_1_control_out_exact", "step_1_control_out_side",
        "step_2_cond",
        "step_2_control_in_exact", "step_2_control_in_side",
        "step_2_control_out_exact", "step_2_control_out_side",
    ]


@pytest.mark.parametrize(("flag", "expected"), [
    ("cond_2", "step_2_cond"),
    ("positive", "positive_control"),
    ("in_exact_1", "step_1_control_in_exact"),
    ("in_side_2", "step_2_control_in_side"),
    ("out_exact_2", "step_2_control_out_exact"),
    ("out_side_1", "step_1_control_out_side"),
])
def test_each_failed_condition_alone_is_reported_alone(flag, expected):
    valid, first, failed = k6.assess_validity([False, False, False],
                                              _validity_selection(**{flag: True}))
    assert (valid, first, failed) == (False, expected, [expected])


def test_all_conditions_holding_is_valid():
    assert k6.assess_validity([False, True, True], _validity_selection()) == (True, None, [])
