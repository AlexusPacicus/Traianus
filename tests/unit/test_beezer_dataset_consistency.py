"""The frozen Beezer artifacts under data/math/ equal a rebuild from the pinned snapshot."""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "experiments" / "tooling"))

from build_beezer_corpus import ARTIFACTS, main

DATA = REPO_ROOT / "data" / "math"
MACROS = DATA / "macro_words.json"


def _frozen(key):
    return json.loads((DATA / ARTIFACTS[key]).read_text(encoding="utf-8"))


def test_rebuild_reproduces_frozen_artifacts_byte_for_byte(tmp_path):
    macros_before = MACROS.read_bytes()
    assert main(["--out", str(tmp_path)]) == 0
    for name in ARTIFACTS.values():
        assert (tmp_path / name).read_bytes() == (DATA / name).read_bytes(), name
    assert MACROS.read_bytes() == macros_before


def test_label_keyed_files_share_keys_and_order():
    labels = list(_frozen("manifest"))
    assert len(labels) == 342
    assert list(_frozen("marked")) == labels
    assert list(_frozen("formulas")) == labels


def test_citation_endpoints_are_labels():
    labels = set(_frozen("manifest"))
    citations = _frozen("citations")
    assert citations
    for source, target in citations:
        assert source in labels and target in labels
