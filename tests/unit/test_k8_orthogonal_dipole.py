"""Unit tests of tools/experiments/k8_orthogonal_dipole.py.

Specification: docs/methodology/instrument-audit/K8.md (revision 3),
docs/methodology/instrument-audit/contracts.md (§0 and §3),
docs/methodology/instrument-audit/derivations.md (D13-D16). Synthetic inputs only: CI has no
.data/, and the measurement is never run on the real artefact here.
"""

import hashlib
import json

import numpy as np
import pytest

from tools.experiments import k6_colour_predictability as k6
from tools.experiments import k8_orthogonal_dipole as k8

D = k8.D


def _axis_ids():
    return [f"AXIS_{k}" for k in range(1, 9)]


def _random_independent_columns(rng, m=4, d=20):
    return [rng.standard_normal(d) for _ in range(m)]


def _modified_gram_schmidt_project(w, vectors):
    basis = []
    for v in vectors:
        u = v.astype(float).copy()
        for b in basis:
            u = u - np.dot(u, b) * b
        basis.append(u / np.linalg.norm(u))
    out = w.copy()
    for b in basis:
        out = out - np.dot(out, b) * b
    return out


@pytest.fixture
def rng():
    return np.random.default_rng(424242)


# Threshold ---------------------------------------------------------------------------------------


def test_threshold_returns_the_951st_smallest_value():
    values = np.arange(1, 1001, dtype=np.float64)
    assert k8.threshold(values) == 951.0
    assert k8.threshold(values[::-1].copy()) == 951.0


# RNG stream pin ------------------------------------------------------------------------------------

# First component of g_1, g_2, g_3 (deciding null, Generator(PCG64(20260924)), numpy 2.4.1).
# Recorded before the script uses them; pins the stream (NEP 19 does not guarantee it across
# numpy versions).
RECORDED_G_FIRST = (0.8980620122737165, 0.6240239817116178, -0.4869091106929845)


def test_first_three_deciding_null_draws_match_recorded_values():
    g = k8.draw_deciding_null(k8.make_rng(k8.SEED), 3, D)
    assert (g[0, 0], g[1, 0], g[2, 0]) == pytest.approx(RECORDED_G_FIRST, rel=1e-12, abs=0.0)


def test_deciding_null_is_drawn_first_and_sigma_null_after():
    rng = k8.make_rng(k8.SEED)
    g_deciding = k8.draw_deciding_null(rng, k8.N_NULL, D)
    assert g_deciding.shape == (k8.N_NULL, D)
    advanced = k8.make_rng(k8.SEED)
    for _ in range(k8.N_NULL):
        advanced.standard_normal(D)
    assert rng.bit_generator.state == advanced.bit_generator.state


# Direction in S-perp: pure-function tests on a random small basis (D14, D15) ----------------------


def test_build_direction_u_is_orthogonal_to_m_and_unit(rng):
    checked = 0
    for _ in range(30):
        m = np.column_stack(_random_independent_columns(rng))
        w2 = rng.standard_normal(m.shape[0])
        direction = k8.build_direction(m, w2)
        u = direction["u"]
        assert direction["u_orthogonality_max"] < 1e-9
        assert direction["u_norm_deviation"] < 1e-9
        assert float(np.max(np.abs(m.T @ u))) < 1e-9
        assert abs(float(np.linalg.norm(u)) - 1.0) < 1e-9
        checked += 1
    assert checked == 30


def test_project_off_equals_gram_schmidt_in_two_orders(rng):
    for _ in range(20):
        cols = _random_independent_columns(rng)
        w = rng.standard_normal(len(cols[0]))
        order1 = _modified_gram_schmidt_project(w, cols)
        order2 = _modified_gram_schmidt_project(w, list(reversed(cols)))
        q, _ = np.linalg.qr(np.column_stack(cols))
        qr_result = k8.project_off(q, w)
        assert np.allclose(order1, order2, rtol=0.0, atol=1e-9)
        assert np.allclose(order1, qr_result, rtol=0.0, atol=1e-9)


def test_null_directions_are_orthogonal_to_m_and_unit_for_both_shapes(rng):
    cols = _random_independent_columns(rng)
    m = np.column_stack(cols)
    q, _ = np.linalg.qr(m)
    for n_rows in (50, 1000):
        g = rng.standard_normal((n_rows, len(cols[0])))
        w0 = k8.null_directions_in_complement(q, g)
        orth_max, norm_dev_max = k8.null_orthogonality(m, w0)
        assert orth_max < 1e-9
        assert norm_dev_max < 1e-9


def test_null_projected_off_c1_only_fails_nulls_orthogonal(rng):
    cols = _random_independent_columns(rng)
    m = np.column_stack(cols)
    c1_only = cols[0][:, np.newaxis]
    q1, _ = np.linalg.qr(c1_only)
    g = rng.standard_normal((50, len(cols[0])))
    w0 = k8.null_directions_in_complement(q1, g)
    orth_max, _ = k8.null_orthogonality(m, w0)
    assert orth_max > 1e-6


def test_u_built_from_w1_instead_of_w2_fails_u_from_w2(rng):
    cols = _random_independent_columns(rng)
    m = np.column_stack(cols)
    w1_like = cols[1]
    w2_like = rng.standard_normal(m.shape[0])
    wrong = k8.build_direction(m, w1_like)
    deviation_against_true_w2 = abs(float(wrong["u"] @ w2_like) - wrong["norm_pw2"])
    assert deviation_against_true_w2 > 1e-6


# assess_post_spread --------------------------------------------------------------------------------


def _all_flags(**overrides):
    flags = dict.fromkeys(k8.POST_SPREAD_IDENTIFIERS, True)
    flags.update(overrides)
    return flags


def test_assess_post_spread_all_true_is_valid():
    assert k8.assess_post_spread(_all_flags()) == (True, None, [])


@pytest.mark.parametrize("identifier", k8.POST_SPREAD_IDENTIFIERS)
def test_assess_post_spread_reports_a_single_failure_alone(identifier):
    valid, first, failed = k8.assess_post_spread(_all_flags(**{identifier: False}))
    assert (valid, first, failed) == (False, identifier, [identifier])


def test_assess_post_spread_lists_failures_in_check_order():
    flags = _all_flags(control_in_side=False, cond_B=False, positive_control=False)
    valid, first, failed = k8.assess_post_spread(flags)
    assert not valid
    assert first == "cond_B"
    assert failed == ["cond_B", "positive_control", "control_in_side"]


# Full-scenario fixtures ------------------------------------------------------------------------

WEIGHTS = np.array([20.0, 10.0, 9.0, 8.0, 7.0, 6.0, 5.0, 1.0])


def _clean_axes(rng):
    q, _ = np.linalg.qr(rng.standard_normal((D, 8)))
    return q.T.copy()


def _clean_v(rng, a_hat, n_per_half):
    n = 2 * n_per_half
    v = WEIGHTS @ a_hat + 0.02 * rng.standard_normal((n, D))
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def _labels(n):
    return [{"label": f"L{i}", "part": "P1"} for i in range(n)]


def _axes_json(a_hat, axis_ids):
    return [
        {"id": axis_id, "simbolo": "s", "tag": "t", "vector": row.tolist()}
        for axis_id, row in zip(axis_ids, a_hat)
    ]


def _k6_payload(*, valid=True, ranking_fit, rankings_match=True, fallback=None,
                selected=("lambda_3", "a_8", "none")):
    fallback = fallback if fallback is not None else {
        "dipole_1": False, "dipole_2": False, "dipole_3": False,
    }
    return {
        "valid": valid,
        "ranking_fit": list(ranking_fit),
        "rankings_match": rankings_match,
        "fallback": fallback,
        "steps": [{"step": s, "selected": sel} for s, sel in enumerate(selected, start=1)],
    }


def _clean_scenario(rng, n_per_half=100):
    a_hat = _clean_axes(rng)
    v = _clean_v(rng, a_hat, n_per_half)
    axis_ids = _axis_ids()
    k6_payload = _k6_payload(ranking_fit=axis_ids)
    return v.astype(np.float32), a_hat, axis_ids, k6_payload


def _write_all_inputs(tmp_path, v32, labels, axes, k6_payload,
                       k6_script_bytes=b"# k6 placeholder\n", polar_bytes=b"# polar placeholder\n"):
    emb, lab, ax = tmp_path / "embeddings.npy", tmp_path / "labels.json", tmp_path / "axes.json"
    k6res, k6script = tmp_path / "K6_result.json", tmp_path / "k6_script.py"
    polar = tmp_path / "polar_projector.py"
    np.save(emb, v32)
    lab.write_text(json.dumps(labels), encoding="utf-8")
    ax.write_text(json.dumps(axes), encoding="utf-8")
    k6res.write_text(json.dumps(k6_payload), encoding="utf-8")
    k6script.write_bytes(k6_script_bytes)
    polar.write_bytes(polar_bytes)
    return emb, lab, ax, k6res, k6script, polar


def _digests(*paths):
    return {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def _run_case(tmp_path, v32, a_hat, axis_ids, k6_payload, out_name="K8_result.json"):
    paths = _write_all_inputs(tmp_path, v32, _labels(v32.shape[0]), _axes_json(a_hat, axis_ids),
                               k6_payload)
    expected = _digests(*paths)
    out = tmp_path / "out" / out_name
    return k8.run(*paths, expected, out), out


# Stop conditions, end to end (T8) -------------------------------------------------------------


def test_stop_k6_result_valid(tmp_path, rng):
    v32, a_hat, axis_ids, k6_payload = _clean_scenario(rng)
    k6_payload["valid"] = False
    result, out = _run_case(tmp_path, v32, a_hat, axis_ids, k6_payload)
    assert result["stopped"] is True and result["valid"] is False
    assert result["first_failed_condition"] == "k6_result_valid"
    assert result["failed_conditions"] == ["k6_result_valid"]
    assert result["conditions_checked"] == ["k6_result_valid"]
    assert result["r2_z"] is None and result["tau"] is None
    assert out.exists()


def test_stop_k6_selected_channels(tmp_path, rng):
    v32, a_hat, axis_ids, k6_payload = _clean_scenario(rng)
    k6_payload["steps"][0]["selected"] = "lambda_2"
    result, _ = _run_case(tmp_path, v32, a_hat, axis_ids, k6_payload)
    assert result["first_failed_condition"] == "k6_selected_channels"
    assert result["conditions_checked"] == ["k6_result_valid", "k6_selected_channels"]
    assert result["tau"] is None


def test_stop_ranking_reproduced(tmp_path, rng):
    v32, a_hat, axis_ids, k6_payload = _clean_scenario(rng)
    k6_payload["ranking_fit"] = list(reversed(axis_ids))
    result, _ = _run_case(tmp_path, v32, a_hat, axis_ids, k6_payload)
    assert result["first_failed_condition"] == "ranking_reproduced"
    assert result["tau"] is None


def test_stop_fallback_flags_agree(tmp_path, rng):
    v32, a_hat, axis_ids, k6_payload = _clean_scenario(rng)
    k6_payload["fallback"] = {"dipole_1": False, "dipole_2": True, "dipole_3": False}
    result, _ = _run_case(tmp_path, v32, a_hat, axis_ids, k6_payload)
    assert result["first_failed_condition"] == "fallback_flags_agree"
    assert result["tau"] is None


def test_stop_fallback_none(tmp_path, rng):
    a_hat = _clean_axes(rng)
    a_hat[2] = a_hat[1]  # dipole 1's poles collinear -> real fallback[0] = True
    v = _clean_v(rng, a_hat, 100)
    axis_ids = _axis_ids()
    k6_payload = _k6_payload(
        ranking_fit=axis_ids, fallback={"dipole_1": True, "dipole_2": False, "dipole_3": False},
    )
    result, _ = _run_case(tmp_path, v.astype(np.float32), a_hat, axis_ids, k6_payload)
    assert result["first_failed_condition"] == "fallback_none"
    assert result["tau"] is None


def _patched_build_direction(monkeypatch, **overrides):
    real = k8.build_direction

    def fake(m, w2):
        d = dict(real(m, w2))
        d.update(overrides)
        return d

    monkeypatch.setattr(k8, "build_direction", fake)


def test_stop_rank(tmp_path, rng, monkeypatch):
    v32, a_hat, axis_ids, k6_payload = _clean_scenario(rng)
    _patched_build_direction(monkeypatch, sigma_min=1e-9)
    result, _ = _run_case(tmp_path, v32, a_hat, axis_ids, k6_payload)
    assert result["first_failed_condition"] == "rank"
    assert result["sigma_min_M"] == 1e-9
    assert result["survival"] is None
    assert result["tau"] is None


def test_stop_survival(tmp_path, rng, monkeypatch):
    v32, a_hat, axis_ids, k6_payload = _clean_scenario(rng)
    _patched_build_direction(monkeypatch, survival=1e-9)
    result, _ = _run_case(tmp_path, v32, a_hat, axis_ids, k6_payload)
    assert result["first_failed_condition"] == "survival"
    assert result["survival"] == 1e-9
    assert result["u_from_w2_deviation"] is None
    assert result["tau"] is None


def test_stop_u_from_w2(tmp_path, rng, monkeypatch):
    v32, a_hat, axis_ids, k6_payload = _clean_scenario(rng)
    _patched_build_direction(monkeypatch, u_from_w2_deviation=1.0)
    result, _ = _run_case(tmp_path, v32, a_hat, axis_ids, k6_payload)
    assert result["first_failed_condition"] == "u_from_w2"
    assert result["u_orthogonality_max"] is None
    assert result["tau"] is None


def test_stop_u_orthogonal(tmp_path, rng, monkeypatch):
    v32, a_hat, axis_ids, k6_payload = _clean_scenario(rng)
    _patched_build_direction(monkeypatch, u_orthogonality_max=1.0)
    result, _ = _run_case(tmp_path, v32, a_hat, axis_ids, k6_payload)
    assert result["first_failed_condition"] == "u_orthogonal"
    assert result["nulls_orthogonality_max"] is None
    assert result["tau"] is None


def test_stop_nulls_orthogonal(tmp_path, rng, monkeypatch):
    v32, a_hat, axis_ids, k6_payload = _clean_scenario(rng)
    monkeypatch.setattr(k8, "null_orthogonality", lambda m, w0: (1.0, 1.0))
    result, _ = _run_case(tmp_path, v32, a_hat, axis_ids, k6_payload)
    assert result["first_failed_condition"] == "nulls_orthogonal"
    assert result["nulls_orthogonality_max"] == {"deciding": 1.0, "sigma": 1.0}
    assert result["sd_z"] is None
    assert result["tau"] is None


def test_stop_spread(tmp_path, rng, monkeypatch):
    v32, a_hat, axis_ids, k6_payload = _clean_scenario(rng)
    monkeypatch.setattr(
        k8, "channels_along", lambda v, directions: np.zeros((directions.shape[0], v.shape[0]))
    )
    result, _ = _run_case(tmp_path, v32, a_hat, axis_ids, k6_payload)
    assert result["first_failed_condition"] == "spread"
    assert result["sd_z"] == 0.0
    assert result["cond_B"] is None
    assert result["tau"] is None


# Post-spread failures: valid = false, every figure still computed (T9) -------------------------


def test_post_spread_cond_b_failure_leaves_every_figure_computed(tmp_path, rng, monkeypatch):
    v32, a_hat, axis_ids, k6_payload = _clean_scenario(rng)
    real_design_basis = k8.design_basis

    def fake_design_basis(x, y, selected):
        b, cols = real_design_basis(x, y, selected)
        b = b.copy()
        b[:, 1] = b[:, 0] * (1.0 + 1e-13)  # near-duplicate of the constant column: cond(B) >> 1e5
        return b, cols

    monkeypatch.setattr(k8, "design_basis", fake_design_basis)
    result, _ = _run_case(tmp_path, v32, a_hat, axis_ids, k6_payload)
    assert result["stopped"] is False
    assert result["valid"] is False
    assert result["first_failed_condition"] == "cond_B"
    assert result["cond_B"] > k8.COND_MAX
    assert result["admissible"] is None
    assert result["r2_z"] is not None and result["tau"] is not None
    assert result["descriptive"] is not None


def test_post_spread_d16_identity_failure_leaves_every_figure_computed(tmp_path, rng, monkeypatch):
    v32, a_hat, axis_ids, k6_payload = _clean_scenario(rng)
    real_ols_fit = k8.ols_fit
    count = {"n": 0}

    def fake_ols_fit(u, b):
        count["n"] += 1
        fit = real_ols_fit(u, b)
        if count["n"] == 2:  # resid_z is call 1; resid_lam2 is call 2
            fit = fit + 1000.0
        return fit

    monkeypatch.setattr(k8, "ols_fit", fake_ols_fit)
    result, _ = _run_case(tmp_path, v32, a_hat, axis_ids, k6_payload)
    assert result["valid"] is False
    assert "d16_identity" in result["failed_conditions"]
    assert result["admissible"] is None
    assert result["d16_max_deviation"] > 1e-9 * result["sd_z"]
    assert result["r2_z"] is not None


def test_post_spread_positive_control_failure_leaves_every_figure_computed(tmp_path, rng, monkeypatch):
    v32, a_hat, axis_ids, k6_payload = _clean_scenario(rng)
    real_r_squared = k8.r_squared
    count = {"n": 0}

    def fake_r_squared(u, b):
        count["n"] += 1
        if count["n"] == 2002:  # 1 (z) + 1000 (deciding) + 1000 (sigma) + 1 = the h call
            _, adj = real_r_squared(u, b)
            return 0.0, adj
        return real_r_squared(u, b)

    monkeypatch.setattr(k8, "r_squared", fake_r_squared)
    result, _ = _run_case(tmp_path, v32, a_hat, axis_ids, k6_payload)
    assert result["valid"] is False
    assert "positive_control" in result["failed_conditions"]
    assert result["positive_control"]["r2"] == 0.0
    assert result["admissible"] is None
    assert result["r2_z"] is not None


def test_post_spread_control_failure_leaves_every_figure_computed(tmp_path, rng, monkeypatch):
    v32, a_hat, axis_ids, k6_payload = _clean_scenario(rng)
    real_cc = k8.calibration_control
    count = {"n": 0}

    def fake_cc(h, n1, b, rho):
        count["n"] += 1
        if count["n"] == 2:  # the rho_out call
            rho = rho / 2.0
        return real_cc(h, n1, b, rho)

    monkeypatch.setattr(k8, "calibration_control", fake_cc)
    result, _ = _run_case(tmp_path, v32, a_hat, axis_ids, k6_payload)
    assert result["valid"] is False
    assert "control_out_exact" in result["failed_conditions"]
    assert result["admissible"] is None
    assert result["control_out"]["deviation"] > 1e-9


# Regression shared by every arm (T7) ------------------------------------------------------------


def test_z_nulls_h_and_controls_share_one_regression_function(tmp_path, rng, monkeypatch):
    v32, a_hat, axis_ids, k6_payload = _clean_scenario(rng)
    real_r_squared = k8.r_squared
    calls = []

    def spy(u, b):
        calls.append(np.array(u, copy=True))
        return real_r_squared(u, b)

    monkeypatch.setattr(k8, "r_squared", spy)
    result, _ = _run_case(tmp_path, v32, a_hat, axis_ids, k6_payload)
    assert result["stopped"] is False
    # 1 (z) + 1000 (deciding nulls) + 1000 (sigma nulls) + 1 (h) + 1 (control_in) + 1 (control_out)
    assert len(calls) == 2004


# Integrity: digests and null elimination (T10, T11) ---------------------------------------------


def _flip_bit(path, pos, bit=0):
    data = bytearray(path.read_bytes())
    data[pos] ^= 1 << bit
    path.write_bytes(bytes(data))


def test_run_refuses_a_single_bit_flip_in_any_of_the_six_digested_files(tmp_path, rng):
    v32, a_hat, axis_ids, k6_payload = _clean_scenario(rng)
    paths = _write_all_inputs(tmp_path, v32, _labels(v32.shape[0]), _axes_json(a_hat, axis_ids),
                               k6_payload)
    expected = _digests(*paths)
    out = tmp_path / "out" / "K8_result.json"
    for path in paths:
        original = path.read_bytes()
        _flip_bit(path, 0)
        with pytest.raises(k6.IntegrityError, match=path.name):
            k8.run(*paths, expected, out)
        path.write_bytes(original)
        assert not out.exists()


def test_run_refuses_a_mismatched_digest_before_writing(tmp_path, rng):
    v32, a_hat, axis_ids, k6_payload = _clean_scenario(rng)
    paths = _write_all_inputs(tmp_path, v32, _labels(v32.shape[0]), _axes_json(a_hat, axis_ids),
                               k6_payload)
    expected = _digests(*paths)
    expected[paths[3]] = "0" * 64  # K6_result.json
    out = tmp_path / "out" / "K8_result.json"
    with pytest.raises(k6.IntegrityError, match="K6_result.json"):
        k8.run(*paths, expected, out)
    assert not out.exists()


def test_run_refuses_a_nan_row_before_writing(tmp_path, rng):
    v32, a_hat, axis_ids, k6_payload = _clean_scenario(rng)
    v32 = v32.copy()
    v32[3, 5] = np.float32(np.nan)
    paths = _write_all_inputs(tmp_path, v32, _labels(v32.shape[0]), _axes_json(a_hat, axis_ids),
                               k6_payload)
    expected = _digests(*paths)
    out = tmp_path / "out" / "K8_result.json"
    with pytest.raises(ValueError, match="row 3"):
        k8.run(*paths, expected, out)
    assert not out.exists()


# Result format (T12) ------------------------------------------------------------------------------


def test_run_writes_the_result_json_as_the_contract_states(tmp_path, rng):
    v32, a_hat, axis_ids, k6_payload = _clean_scenario(rng)
    paths = _write_all_inputs(tmp_path, v32, _labels(v32.shape[0]), _axes_json(a_hat, axis_ids),
                               k6_payload)
    expected = _digests(*paths)
    out = tmp_path / "out" / "K8_result.json"
    result = k8.run(*paths, expected, out)

    text = out.read_text(encoding="utf-8")
    assert "\r" not in text
    assert text == json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n"
    assert json.loads(text) == result

    assert result["stopped"] is False
    assert result["conditions_checked"] == list(k8.STOP_IDENTIFIERS) + list(k8.POST_SPREAD_IDENTIFIERS)
    for key in k8.NULL_FIGURE_KEYS:
        assert key in result
    for key in ("digests", "environment", "rankings_match", "first_failed_condition",
                "failed_conditions", "valid", "descriptive"):
        assert key in result
    assert set(result["digests"].keys()) == {
        "embeddings.npy", "labels.json", "axes.json", "K6_result.json",
        "k6_script.py", "polar_projector.py",
    }
    assert result["admissible"] in (True, False)
    assert set(result["positive_control"].keys()) == {"r2", "tau"}
    for side in ("control_in", "control_out"):
        assert set(result[side].keys()) == {"rho", "r2", "deviation"}
    assert set(result["descriptive"].keys()) == {
        "pearson_r", "sd_z_rank_among_null_sd", "clip_fractions",
    }
    assert set(result["descriptive"]["pearson_r"].keys()) == {"x", "y", "lambda_3", "a_8"}
    assert set(result["descriptive"]["clip_fractions"].keys()) == {"x", "lambda_3"}

    again = tmp_path / "out" / "again.json"
    k8.run(*paths, expected, again)
    assert again.read_bytes() == out.read_bytes()


def test_out_option_directs_the_result_and_the_default_is_unchanged(tmp_path, monkeypatch):
    calls = []

    def fake_run(embeddings, labels, axes, k6_result, k6_script, polar_projector, expected, out_path):
        calls.append(
            (embeddings, labels, axes, k6_result, k6_script, polar_projector, expected, out_path)
        )
        return {"valid": True, "admissible": None}

    monkeypatch.setattr(k8, "run", fake_run)
    target = tmp_path / "elsewhere" / "K8_B.json"
    k8.main(["--out", str(target)])
    k8.main([])
    assert calls[0] == (
        k8.EMBEDDINGS, k8.LABELS, k8.AXES, k8.K6_RESULT, k8.K6_SCRIPT, k8.POLAR_PROJECTOR,
        k8.EXPECTED_DIGESTS, target,
    )
    assert calls[1][7] == k8.RESULT == k8.REPO_ROOT / "data" / "refapp" / "K8_result.json"
