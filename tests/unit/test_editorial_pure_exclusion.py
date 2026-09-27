"""Unit tests of tools/experiments/editorial_pure_exclusion.py.

Specification: the delegation contract editorial-pure-exclusion-check (B1-B8). Synthetic inputs only: CI has
no .data/, and the real frozen corpus is never touched here. The three heavy run() functions (k6, r4, zoom)
are monkeypatched by small fakes; only data/spinoza/editorial_marks.json, a committed and versioned file, is
read for real, as a guard on the 11 pure labels.
"""

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from tools.experiments import editorial_pure_exclusion as eq
from tools.experiments import k6_colour_predictability as k6
from tools.experiments import r4_perspective_recall as r4
from tools.experiments import zoom_three_point as zoom

# T1: pure_labels ----------------------------------------------------------------------------------


def test_t1_pure_labels_returns_only_pure_true_sorted():
    marks = {
        "marked": {
            "b": {"pure": True, "coverage": 1.0},
            "a": {"pure": True, "coverage": 1.0},
            "c": {"pure": False, "coverage": 0.5},
        },
    }
    assert eq.pure_labels(marks) == ["a", "b"]


def test_t1_the_committed_editorial_marks_have_exactly_11_pure_labels_none_mixed():
    marks = json.loads((eq.REPO_ROOT / "data" / "spinoza" / "editorial_marks.json").read_text(encoding="utf-8"))
    pures = eq.pure_labels(marks)
    assert len(pures) == 11
    assert pures == sorted(pures)
    mixed = {label for label, info in marks["marked"].items() if info.get("pure") is False}
    assert not (set(pures) & mixed)


def test_x1_pure_labels_excludes_a_label_with_pure_absent_or_null():
    marks = {"marked": {"a": {"pure": True}, "b": {}, "c": {"pure": None}}}
    assert eq.pure_labels(marks) == ["a"]


# T2, T3: filter_corpus ------------------------------------------------------------------------------


def _small_corpus(n=6, d=8, seed=20260927):
    rng = np.random.default_rng(seed)
    v = rng.standard_normal((n, d)).astype("<f4")
    labels = [{"label": f"L{i}", "part": "P"} for i in range(n)]
    return v, labels


def test_t2_filter_corpus_drops_named_rows_keeps_order_and_bytes_unchanged():
    v, labels = _small_corpus()
    kept_v, kept_labels = eq.filter_corpus(v, labels, ["L1", "L4"])
    assert [item["label"] for item in kept_labels] == ["L0", "L2", "L3", "L5"]
    assert kept_v.dtype == np.dtype("<f4")
    assert kept_v.flags["C_CONTIGUOUS"]
    for row, orig_i in zip(kept_v, (0, 2, 3, 5), strict=True):
        assert row.tobytes() == v[orig_i].tobytes()
    assert kept_labels == [labels[0], labels[2], labels[3], labels[5]]
    assert all(kept is labels[orig_i] for kept, orig_i in zip(kept_labels, (0, 2, 3, 5), strict=True))


def test_t2_filter_corpus_with_an_empty_drop_list_returns_everything_unchanged():
    v, labels = _small_corpus(4)
    kept_v, kept_labels = eq.filter_corpus(v, labels, [])
    assert np.array_equal(kept_v, v) and kept_labels == labels


def test_t3_filter_corpus_raises_naming_the_label_when_absent_or_duplicated():
    v, labels = _small_corpus(4)
    with pytest.raises(ValueError, match="L9"):
        eq.filter_corpus(v, labels, ["L9"])
    dup_labels = [*labels, {"label": "L1", "part": "P"}]
    dup_v = np.vstack([v, v[1:2]])
    with pytest.raises(ValueError, match="L1"):
        eq.filter_corpus(dup_v, dup_labels, ["L1"])


def test_t3_filter_corpus_raises_when_row_and_label_counts_differ():
    v, labels = _small_corpus(4)
    with pytest.raises(ValueError, match="row count"):
        eq.filter_corpus(v, labels[:-1], ["L0"])


# T6: write_filtered_inputs ---------------------------------------------------------------------------


def _unit_corpus(n=5, d=k6.D, seed=1):
    rng = np.random.default_rng(seed)
    raw = rng.standard_normal((n, d))
    v = (raw / np.linalg.norm(raw, axis=1, keepdims=True)).astype("<f4")
    labels = [{"label": f"U{i}", "part": "P"} for i in range(n)]
    return v, labels


def test_t6_write_filtered_inputs_round_trips_matches_digests_and_passes_k6_validation(tmp_path):
    v, labels = _unit_corpus()
    embeddings_path, labels_path, digests = eq.write_filtered_inputs(tmp_path, v, labels)
    assert embeddings_path == tmp_path / "embeddings.npy"
    assert labels_path == tmp_path / "labels.json"
    assert hashlib.sha256(embeddings_path.read_bytes()).hexdigest() == digests[embeddings_path]
    assert hashlib.sha256(labels_path.read_bytes()).hexdigest() == digests[labels_path]

    loaded_v = np.load(embeddings_path, allow_pickle=False)
    assert loaded_v.dtype == np.dtype("<f4")
    assert np.array_equal(loaded_v, v)
    loaded_labels = json.loads(labels_path.read_text(encoding="utf-8"))
    assert loaded_labels == labels

    axis_ids = [f"ax{i}" for i in range(k6.N_AXES)]
    axes = np.eye(k6.N_AXES, k6.D)
    k6.validate_inputs(loaded_v, loaded_labels, axis_ids, axes)


# T4: compare_k6 --------------------------------------------------------------------------------------


def _k6_result(valid=True, selected=("a_8", "l"), **extra):
    base = {
        "valid": valid, "selected": list(selected), "n_fit": 10, "n_eval": 9,
        "ranking_fit": ["ax1", "ax2"], "means_fit": {"ax1": 0.1, "ax2": 0.2},
        "failed_conditions": [], "positive_control": {"margin": 0.05},
    }
    base.update(extra)
    return base


def test_t4_compare_k6_unchanged_for_equal_valid_and_selected_reported_diffs_do_not_decide():
    committed = _k6_result()
    filtered = _k6_result(n_fit=999, means_fit={"ax1": 9.9})
    result = eq.compare_k6(committed, filtered)
    assert result["unchanged"] is True and result["reason"] is None
    assert result["reported"]["n_fit"] == {"committed": 10, "filtered": 999}


@pytest.mark.parametrize(
    "other_selected", [("a_8", "h"), ("l", "a_8")], ids=["different-content", "different-order"],
)
def test_t4_compare_k6_changed_when_selected_differs_in_content_or_only_order(other_selected):
    committed = _k6_result(selected=("a_8", "l"))
    result = eq.compare_k6(committed, _k6_result(selected=other_selected))
    assert result["unchanged"] is False


def test_t4_compare_k6_changed_when_filtered_is_invalid_while_committed_is_valid():
    committed = _k6_result(valid=True)
    filtered = _k6_result(valid=False, failed_conditions=["dipole_1_fallback"])
    result = eq.compare_k6(committed, filtered)
    assert result["unchanged"] is False
    assert "failed_conditions" in result["reason"]


def test_t4_compare_k6_missing_key_is_a_difference_not_an_exception():
    committed = _k6_result()
    filtered = _k6_result()
    del filtered["selected"]
    result = eq.compare_k6(committed, filtered)
    assert result["unchanged"] is False
    assert result["deciding"]["selected"]["filtered"] == "<missing>"


# T5: compare_r4 and compare_z -------------------------------------------------------------------------


def _r4_result(valid=True, r4_holds=True, **extra):
    base = {
        "valid": valid, "r4_holds": r4_holds, "margin": -0.01, "n": 100,
        "reported": {"l_gt": {"value": 15, "interval": {"hi": -0.02}}},
        "failed_conditions": [],
    }
    base.update(extra)
    return base


def test_t5_compare_r4_changed_on_holds_flip_or_invalid_unchanged_when_equal():
    committed = _r4_result(r4_holds=True)
    assert eq.compare_r4(committed, _r4_result(r4_holds=False))["unchanged"] is False
    assert eq.compare_r4(committed, _r4_result(valid=False, r4_holds=None))["unchanged"] is False
    assert eq.compare_r4(committed, _r4_result())["unchanged"] is True


def _z_result(valid=True, z1_decision="inconclusive", z2_decision="confirmed", **extra):
    base = {
        "valid": valid,
        "z1": {"decision": z1_decision, "n": 40, "d_bar_cells_agree": 1e-6},
        "z2": {"decision": z2_decision, "median_delta_ns": -900000.0, "ready_p95_ns": 4.7e7, "per_l": {"1": 0.1}},
        "failed_conditions": [],
    }
    base.update(extra)
    return base


def test_t5_compare_z_unchanged_true_when_both_runs_equal_the_committed_decisions():
    committed = _z_result()
    result = eq.compare_z(committed, (_z_result(), _z_result()))
    assert result["unchanged"] is True
    assert result["usable"] is True
    assert result["z2_reproducible"] is True


@pytest.mark.parametrize(
    ("z1", "z2"), [("confirmed", "confirmed"), ("inconclusive", "rejected")], ids=["z1-differs", "z2-differs"],
)
def test_t5_compare_z_changed_when_z1_or_z2_decision_differs_from_committed(z1, z2):
    committed = _z_result(z1_decision="inconclusive", z2_decision="confirmed")
    run = _z_result(z1_decision=z1, z2_decision=z2)
    result = eq.compare_z(committed, (run, run))
    assert result["unchanged"] is False


def test_t5_compare_z_usable_false_when_the_two_runs_differ_outside_z2():
    committed = _z_result()
    run1 = _z_result()
    run2 = _z_result(z1_decision="confirmed")
    result = eq.compare_z(committed, (run1, run2))
    assert result["usable"] is False
    assert result["unchanged"] is False
    assert result["deciding"] == {}


def test_t5_compare_z_not_reproducible_when_the_two_runs_disagree_only_on_z2():
    committed = _z_result()
    run1 = _z_result(z2_decision="confirmed")
    run2 = _z_result(z2_decision="rejected")
    result = eq.compare_z(committed, (run1, run2))
    assert result["usable"] is True
    assert result["z2_reproducible"] is False
    assert result["deciding"]["z2.decision"]["filtered"] == "not reproducible"
    assert result["unchanged"] is False
    assert "not reproducible" in result["reason"]


# Orchestration (B6, B7, B8) --------------------------------------------------------------------------


def _write_json(payload, out_path):
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, sort_keys=True, indent=2, allow_nan=False) + "\n"
    out_path.write_text(text, encoding="utf-8", newline="\n")
    return json.loads(text)


def _write_corpus_files(directory, n=6, d=4, seed=20260927):
    directory.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    raw = rng.standard_normal((n, d))
    v = (raw / np.linalg.norm(raw, axis=1, keepdims=True)).astype("<f4")
    labels = [{"label": f"N{i}", "part": "P"} for i in range(n)]
    embeddings_path, labels_path = directory / "embeddings.npy", directory / "labels.json"
    np.save(embeddings_path, v)
    labels_path.write_text(json.dumps(labels), encoding="utf-8")
    digests = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (embeddings_path, labels_path)}
    return embeddings_path, labels_path, digests


def _fake_runs(calls, unfiltered_embeddings, results):
    """Fakes for k6.run, r4.run and zoom.run: they record a uniform tuple (kind, embeddings, labels, axes,
    extra, expected, out_path) and write a fixed payload, distinguishing control from filtered by whether
    `embeddings` is the unfiltered path; Z's two calls are told apart by their position in `calls`."""

    def fake_k6(embeddings, labels, axes, expected, out_path):
        embeddings = Path(embeddings)
        calls.append(("k6", embeddings, Path(labels), Path(axes), None, dict(expected), Path(out_path)))
        control = embeddings == unfiltered_embeddings
        return _write_json(results["k6_control" if control else "k6_filtered"], out_path)

    def fake_r4(embeddings, labels, axes, k6_result, expected, out_path):
        embeddings = Path(embeddings)
        calls.append(
            ("r4", embeddings, Path(labels), Path(axes), Path(k6_result), dict(expected), Path(out_path))
        )
        control = embeddings == unfiltered_embeddings
        return _write_json(results["r4_control" if control else "r4_filtered"], out_path)

    def fake_zoom(k6_file, embeddings, labels, axes, expected, out_path, clock=None):
        calls.append(
            ("zoom", Path(embeddings), Path(labels), Path(axes), Path(k6_file), dict(expected), Path(out_path))
        )
        run_index = sum(1 for c in calls if c[0] == "zoom")
        return _write_json(results[f"z_run{run_index}"], out_path)

    return fake_k6, fake_r4, fake_zoom


def _patch_orchestration(monkeypatch, tmp_path, results):
    """Wires the corpus, marks and committed-result files, and the three run() fakes; returns the shared
    call log and the unfiltered embeddings path."""
    embeddings_path, labels_path, digests = _write_corpus_files(tmp_path / "frozen")
    axes_path = tmp_path / "axes.json"
    marks_path = tmp_path / "editorial_marks.json"
    marks_path.write_text(
        json.dumps({"marked": {"N1": {"pure": True}, "N4": {"pure": True}, "N2": {"pure": False}}}),
        encoding="utf-8",
    )
    monkeypatch.setattr(eq, "MARKS", marks_path)
    monkeypatch.setattr(k6, "EMBEDDINGS", embeddings_path)
    monkeypatch.setattr(k6, "LABELS", labels_path)
    monkeypatch.setattr(k6, "AXES", axes_path)
    monkeypatch.setattr(
        k6, "EXPECTED_DIGESTS",
        {embeddings_path: digests[embeddings_path], labels_path: digests[labels_path], axes_path: "axes-digest"},
    )

    _write_json(results["committed_k6"], tmp_path / "committed_k6.json")
    _write_json(results["committed_r4"], tmp_path / "committed_r4.json")
    _write_json(results["committed_z"], tmp_path / "committed_z.json")
    monkeypatch.setattr(k6, "RESULT", tmp_path / "committed_k6.json")
    monkeypatch.setattr(r4, "RESULT", tmp_path / "committed_r4.json")
    monkeypatch.setattr(zoom, "RESULT", tmp_path / "committed_z.json")

    calls: list[tuple] = []
    fake_k6, fake_r4, fake_zoom = _fake_runs(calls, embeddings_path, results)
    monkeypatch.setattr(k6, "run", fake_k6)
    monkeypatch.setattr(r4, "run", fake_r4)
    monkeypatch.setattr(zoom, "run", fake_zoom)
    return calls, embeddings_path


def _default_results():
    committed_k6 = {
        "valid": True, "selected": ["a_8"], "n_fit": 3, "n_eval": 3, "ranking_fit": ["ax0"],
        "means_fit": {"ax0": 0.1}, "failed_conditions": [], "positive_control": {"margin": 0.2},
        "environment": {"platform": "committed"},
    }
    committed_r4 = {
        "valid": True, "r4_holds": True, "margin": -0.01, "n": 50,
        "reported": {"l_gt": {"value": 15, "interval": {"hi": -0.02}}}, "failed_conditions": [],
        "environment": {"platform": "committed"},
    }
    committed_z = {
        "valid": True, "z1": {"decision": "inconclusive", "n": 40, "d_bar_cells_agree": 1e-6},
        "z2": {"decision": "confirmed", "median_delta_ns": -1.0, "ready_p95_ns": 2.0, "per_l": {"1": 0.1}},
        "failed_conditions": [], "environment": {"platform": "committed"},
    }
    return {
        "committed_k6": committed_k6, "committed_r4": committed_r4, "committed_z": committed_z,
        "k6_control": committed_k6, "k6_filtered": committed_k6,
        "r4_control": committed_r4, "r4_filtered": {**committed_r4, "r4_holds": False},
        "z_run1": committed_z, "z_run2": committed_z,
    }


def test_t7_orchestration_call_order_receivers_and_deterministic_output(tmp_path, monkeypatch):
    results = _default_results()
    calls, unfiltered_embeddings = _patch_orchestration(monkeypatch, tmp_path, results)
    out_dir, work_dir = tmp_path / "out", tmp_path / "work"

    returned = eq.run(work_dir, out_dir)

    assert [c[0] for c in calls] == ["k6", "r4", "k6", "r4", "zoom", "zoom"]
    k6_control, r4_control, k6_filtered, r4_filtered, z1, z2 = calls

    assert k6_control[1] == unfiltered_embeddings and r4_control[1] == unfiltered_embeddings
    assert r4_control[4] == Path(k6.RESULT)
    assert k6_filtered[1] == work_dir / "embeddings.npy" and k6_filtered[1] != unfiltered_embeddings
    assert r4_filtered[1] == k6_filtered[1]
    assert r4_filtered[4] == out_dir / "k6.json"
    assert r4_filtered[5][out_dir / "k6.json"] == hashlib.sha256((out_dir / "k6.json").read_bytes()).hexdigest()
    assert z1[4] == zoom.K6_FILE and z2[4] == zoom.K6_FILE
    assert z1[1] == k6_filtered[1] and z2[1] == k6_filtered[1]

    for name in ("k6.json", "r4.json", "z_run1.json", "z_run2.json", "comparison.json"):
        assert (out_dir / name).exists()

    comparison = json.loads((out_dir / "comparison.json").read_text(encoding="utf-8"))
    assert comparison == returned
    assert set(comparison) == {"dropped", "n_before", "n_after", "digests", "control", "k6", "r4", "z", "changed"}
    assert comparison["dropped"] == ["N1", "N4"]
    assert comparison["n_before"] == 6 and comparison["n_after"] == 4
    assert comparison["k6"]["unchanged"] is True
    assert comparison["r4"]["unchanged"] is False
    assert comparison["z"]["unchanged"] is True
    assert comparison["changed"] == ["R4"]
    assert comparison["control"]["usable"] is True

    calls.clear()
    out_dir2 = tmp_path / "out2"
    eq.run(work_dir / "again", out_dir2)
    for name in ("k6.json", "r4.json", "z_run1.json", "z_run2.json", "comparison.json"):
        assert (out_dir / name).read_bytes() == (out_dir2 / name).read_bytes()


# T8: control and integrity ---------------------------------------------------------------------------


def test_t8_control_usable_true_when_equal_outside_environment_even_if_environment_differs(tmp_path, monkeypatch):
    results = _default_results()
    results["k6_control"] = {**results["committed_k6"], "environment": {"platform": "different"}}
    results["r4_control"] = {**results["committed_r4"], "environment": {"platform": "also different"}}
    _patch_orchestration(monkeypatch, tmp_path, results)
    returned = eq.run(tmp_path / "work", tmp_path / "out")
    assert returned["control"] == {"usable": True, "k6_equal": True, "r4_equal": True}


def test_t8_control_usable_false_on_a_differing_numeric_field_and_the_run_still_completes(tmp_path, monkeypatch):
    results = _default_results()
    results["k6_control"] = {**results["committed_k6"], "n_fit": 999}
    _patch_orchestration(monkeypatch, tmp_path, results)
    out_dir = tmp_path / "out"
    returned = eq.run(tmp_path / "work", out_dir)
    assert returned["control"] == {"usable": False, "k6_equal": False, "r4_equal": True}
    for name in ("k6.json", "r4.json", "z_run1.json", "z_run2.json", "comparison.json"):
        assert (out_dir / name).exists()


def test_t8_an_integrity_error_from_a_fake_check_stops_the_run_before_out_dir_and_exits_non_zero(
    tmp_path, monkeypatch,
):
    results = _default_results()
    _patch_orchestration(monkeypatch, tmp_path, results)

    def failing_k6(embeddings, labels, axes, expected, out_path):
        raise k6.IntegrityError("sha256 mismatch for embeddings.npy: expected AAA, got BBB")

    monkeypatch.setattr(k6, "run", failing_k6)
    out_dir, work_dir = tmp_path / "out", tmp_path / "work"

    with pytest.raises(SystemExit) as excinfo:
        eq.main(["--work-dir", str(work_dir), "--out-dir", str(out_dir)])
    assert excinfo.value.code != 0
    assert not out_dir.exists()


def test_x2_a_value_error_from_filter_corpus_also_stops_main_before_out_dir_naming_the_label(
    tmp_path, monkeypatch,
):
    results = _default_results()
    _patch_orchestration(monkeypatch, tmp_path, results)
    marks_path = tmp_path / "bad_marks.json"
    marks_path.write_text(json.dumps({"marked": {"NOT_A_LABEL": {"pure": True}}}), encoding="utf-8")
    monkeypatch.setattr(eq, "MARKS", marks_path)
    out_dir, work_dir = tmp_path / "out", tmp_path / "work"

    with pytest.raises(SystemExit) as excinfo:
        eq.main(["--work-dir", str(work_dir), "--out-dir", str(out_dir)])
    assert excinfo.value.code != 0
    assert not out_dir.exists()
