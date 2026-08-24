"""Builder reproducibility + structural-count guards for the frozen corpus.

The committed source snapshot (data/spinoza/source/pg3800.txt, SHA-256
647f0227...) is the single derivation input: rebuilding any part MUST
reproduce the frozen manifest byte-for-byte (json equality), and each part
MUST contain its documented proposition count (PROVENANCE.md).
"""
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools" / "experiments" / "tooling"))

from build_spinoza_corpus import PART_CONFIG, build_manifest  # noqa: E402

SOURCE = REPO_ROOT / "data" / "spinoza" / "source" / "pg3800.txt"
DATA = REPO_ROOT / "data" / "spinoza"

EXPECTED_PROPOSITIONS = {1: 36, 2: 49, 3: 59, 4: 73, 5: 42}


def _frozen(part: int) -> dict:
    cfg = PART_CONFIG[part]
    return json.loads((DATA / cfg["manifest_name"]).read_text(encoding="utf-8"))


@pytest.mark.parametrize("part", [1, 2, 3, 4, 5])
def test_builder_reproduces_frozen_manifest(part):
    assert build_manifest(SOURCE, part) == _frozen(part)


@pytest.mark.parametrize("part", [1, 2, 3, 4, 5])
def test_documented_proposition_count(part):
    manifest = _frozen(part)
    prefix = PART_CONFIG[part]["prefix"]
    props = {int(k.replace(f"{prefix}_P", "").split("_")[0])
             for k in manifest if k.startswith(f"{prefix}_P")
             and "_PROP" in k}
    assert len(props) == EXPECTED_PROPOSITIONS[part]


def test_part3_emotion_definitions_complete():
    manifest = _frozen(3)
    defemo = {int(k.split("_DEFEMO")[1].lstrip("_").split("_")[0])
              for k in manifest if "DEFEMO" in k}
    assert defemo == set(range(1, 49))


def test_part4_appendix_present():
    # Chunk count is consolidation-dependent (tokenizer merges); this is a
    # presence/scale floor, not an exact count.
    manifest = _frozen(4)
    appendix_chunks = [k for k in manifest if "_APPENDIX" in k]
    assert len(appendix_chunks) >= 20


def test_source_snapshot_intact():
    import hashlib
    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert digest == ("647f0227f3700b5d221a004fc545568c879f6f204e952f1cf"
                      "0c24672676c2a60")
