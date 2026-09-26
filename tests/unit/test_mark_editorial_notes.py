"""Tests for the editorial-footnote marker (tools/experiments/tooling/
mark_editorial_notes.py).

Guarantees under test:
1. A footnote block is recognised from the raw (marker-intact) source, not
   from build_spinoza_corpus's own marker-stripped body -- the leak the
   builder produces by removing '[N]' before blocking.
2. A body sentence that merely mentions '[N]' inline is never mistaken for
   a footnote block (the block must *start* with the marker).
3. A footnote sentence is matched to its true (later) manifest label, never
   to an earlier body occurrence of the same sentence text.
4. A block that continues a footnote (no marker of its own) is reported as
   a continuation candidate, never marked.
5. On the committed PG#3800 source: the two chunks named in the problem
   statement are marked with their footnote numbers, and the Latin-verse
   continuation is a candidate, not marked.
6. Refusal on a source whose SHA-256 does not match, with no output write.
"""
import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLING = REPO_ROOT / "tools" / "experiments" / "tooling"
sys.path.insert(0, str(TOOLING))

import mark_editorial_notes as men
from build_spinoza_corpus import PART_CONFIG

SOURCE = REPO_ROOT / "data" / "spinoza" / "source" / "pg3800.txt"
DATA = REPO_ROOT / "data" / "spinoza"


def _manifest(part: int) -> dict:
    cfg = PART_CONFIG[part]
    return json.loads((DATA / cfg["manifest_name"]).read_text(encoding="utf-8"))


# --- T1: synthetic source and manifest ------------------------------------

def test_footnote_block_recognized_without_prestripped_marker():
    blocks = [
        "Some real sentence one.",
        "Another real sentence two.",
        "[3] Editorial note text.",
        "Real sentence three follows.",
    ]
    manifest = {
        "L1": "Some real sentence one.",
        "L2": "Another real sentence two.",
        "L3": "Editorial note text.",
        "L4": "Real sentence three follows.",
    }
    result = men.mark_part(blocks, manifest, "TESTPART")
    assert result.marked == {"L3": {"footnote": "3", "part": "TESTPART"}}
    assert [fb["footnote"] for fb in result.footnote_blocks] == ["3"]
    assert result.footnote_blocks[0]["labels"] == ["L3"]


def test_inline_bracket_number_in_body_not_marked():
    block = "A body sentence that mentions [5] inline wrongly."
    manifest = {"L1": block}
    result = men.mark_part([block], manifest, "TESTPART")
    assert result.footnote_blocks == []
    assert result.marked == {}


def test_duplicate_sentence_matched_to_true_label_not_earlier_duplicate():
    blocks = [
        "Repeated text appears here.",
        "[9] Repeated text appears here.",
    ]
    manifest = {
        "L1": "Repeated text appears here.",
        "L2": "Repeated text appears here.",
    }
    result = men.mark_part(blocks, manifest, "TESTPART")
    assert result.marked == {"L2": {"footnote": "9", "part": "TESTPART"}}
    assert "L1" not in result.marked


def test_continuation_block_reported_as_candidate_not_marked():
    blocks = [
        "[2] Footnote text here.",
        "Continuation verse line one.",
        "Continuation verse line two.",
        "Note.--Real annotation resumes normal flow.",
    ]
    manifest = {
        "F1": "Footnote text here.",
        "C1": "Continuation verse line one.",
        "C2": "Continuation verse line two.",
        "N1": "Real annotation resumes normal flow.",
    }
    result = men.mark_part(blocks, manifest, "TESTPART")
    assert result.marked == {"F1": {"footnote": "2", "part": "TESTPART"}}
    assert result.continuation_candidates == {
        "C1": {"after_footnote": "2", "part": "TESTPART",
               "text": "Continuation verse line one."},
        "C2": {"after_footnote": "2", "part": "TESTPART",
               "text": "Continuation verse line two."},
    }
    assert "N1" not in result.marked
    assert "N1" not in result.continuation_candidates


# --- T2: the committed PG#3800 source and manifests -----------------------

def test_known_leak_part3_van_vloten_marked():
    raw = SOURCE.read_text(encoding="utf-8")
    blocks = men.part_raw_blocks(raw, PART_CONFIG[3])
    result = men.mark_part(blocks, _manifest(3), "PART3_AFFECTS")
    assert result.marked["PART3_AFFECTS_P30_ESC_01_C04"] == {
        "footnote": "7", "part": "PART3_AFFECTS",
    }


def test_known_leak_part2_baconian_phrase_marked():
    raw = SOURCE.read_text(encoding="utf-8")
    blocks = men.part_raw_blocks(raw, PART_CONFIG[2])
    result = men.mark_part(blocks, _manifest(2), "PART2_MIND")
    assert result.marked["PART2_MIND_P40_DEMO_01_C19"] == {
        "footnote": "4", "part": "PART2_MIND",
    }


def test_footnote9_latin_verse_continuation_is_candidate_not_marked():
    raw = SOURCE.read_text(encoding="utf-8")
    blocks = men.part_raw_blocks(raw, PART_CONFIG[3])
    result = men.mark_part(blocks, _manifest(3), "PART3_AFFECTS")
    label = "PART3_AFFECTS_P31_COR_01_C03"
    assert label in result.continuation_candidates
    assert result.continuation_candidates[label]["after_footnote"] == "9"
    assert label not in result.marked


def test_total_footnote_blocks_across_five_parts_is_17():
    raw = SOURCE.read_text(encoding="utf-8")
    total = 0
    for part in sorted(PART_CONFIG):
        blocks = men.part_raw_blocks(raw, PART_CONFIG[part])
        result = men.mark_part(blocks, _manifest(part), PART_CONFIG[part]["prefix"])
        total += len(result.footnote_blocks)
        assert result.unmatched == []
    assert total == 17


# --- T3: refusal + determinism ---------------------------------------------

def test_refuses_on_sha256_mismatch_and_writes_nothing(tmp_path):
    tampered = tmp_path / "pg3800_tampered.txt"
    tampered.write_text(
        SOURCE.read_text(encoding="utf-8") + "\ntampered\n", encoding="utf-8"
    )
    out_path = tmp_path / "editorial_marks.json"
    exit_code = men.main(["--source", str(tampered), "--out", str(out_path)])
    assert exit_code != 0
    assert not out_path.exists()


def test_accepted_source_hash_matches_provenance():
    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert digest == men.SOURCE_SHA256


def test_output_is_sorted_finite_json(tmp_path):
    out_path = tmp_path / "editorial_marks.json"
    exit_code = men.main(["--source", str(SOURCE), "--out", str(out_path)])
    assert exit_code == 0
    text = out_path.read_text(encoding="utf-8")
    assert text.endswith("\n") and not text.endswith("\n\n")
    parsed = json.loads(text)
    assert json.dumps(parsed, sort_keys=True, allow_nan=False) is not None
    reserialized = json.dumps(parsed, sort_keys=True, indent=2,
                               allow_nan=False, ensure_ascii=False) + "\n"
    assert reserialized == text
