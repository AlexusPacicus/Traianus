"""Unit tests for freeze_telemetry dynamic-report embedding."""
import json

import pytest

from tools.experiments.tooling.freeze_telemetry import merge_extra_reports


def _write_report(tmp_path, stem, body):
    path = tmp_path / f"{stem}.json"
    path.write_text(json.dumps(body), encoding="utf-8")
    return path


def test_merge_extra_reports_embeds_payloads_by_stem(tmp_path):
    payload = {"runs": {}}
    knee = _write_report(tmp_path, "knee_audit_v5", {"epsilon_star": 1.2})
    aniso = _write_report(tmp_path, "anisotropy_full", {"p_value": 0.0025})
    merged = merge_extra_reports(payload, [knee, aniso])
    assert merged["dynamic_epsilon_audit"]["knee_audit_v5"] == {
        "epsilon_star": 1.2}
    assert merged["dynamic_epsilon_audit"]["anisotropy_full"] == {
        "p_value": 0.0025}
    assert merged["runs"] == {}


def test_merge_extra_reports_absent_flag_keeps_payload_intact():
    payload = {"runs": {"a": 1}}
    assert merge_extra_reports(payload, []) == {"runs": {"a": 1}}


def test_merge_extra_reports_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        merge_extra_reports({}, [tmp_path / "nonexistent.json"])
