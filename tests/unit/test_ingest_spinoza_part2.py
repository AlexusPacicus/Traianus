"""Unit tests for the Spinoza Part II ingestion runner (pure helpers only:
no encoder / no SQLite side effects at import time)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "experiments" / "tooling"))

from ingest_spinoza_part2 import (
    load_manifest,
    node_id,
    scratch_db_path,
    telemetry_summary,
)


def test_load_manifest_preserves_reading_order(tmp_path):
    manifest = {"PART2_MIND_DEF_01": "a", "PART2_MIND_P01_PROP": "b"}
    path = tmp_path / "m.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    assert load_manifest(path) == [("PART2_MIND_DEF_01", "a"), ("PART2_MIND_P01_PROP", "b")]


def test_node_id_is_numeric_suffix_compatible_with_bridge_audit():
    assert node_id(1) == "NODE_1"
    assert node_id(472) == "NODE_472"


def test_scratch_db_path_anchored_to_repo_root():
    # CWD-independent: artifacts must land under <repo_root>/.data/.
    assert scratch_db_path().endswith("/.data/spinoza_part2.db")
    assert scratch_db_path().startswith(str(Path(__file__).resolve().parents[2]))


def test_telemetry_summary_percentiles_and_count():
    rows = [
        ("NODE_1", "L1", 0.010),
        ("NODE_2", "L2", 0.020),
        ("NODE_3", "L3", 0.030),
        ("NODE_4", "L4", 0.040),
    ]
    s = telemetry_summary(rows)
    assert s["count"] == 4
    assert s["variance_min"] == pytest.approx(0.010)
    assert s["variance_max"] == pytest.approx(0.040)
    assert s["variance_p50"] == pytest.approx(0.025)


def test_telemetry_summary_empty_raises():
    with pytest.raises(ValueError):
        telemetry_summary([])
