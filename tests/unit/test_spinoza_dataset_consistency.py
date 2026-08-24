"""Drift guard: the frozen corpus .md and its manifest must never diverge."""
import json
from pathlib import Path

DATA = Path(__file__).resolve().parents[2] / "data" / "spinoza"


def _assert_md_matches_manifest(md_name: str, manifest_name: str):
    manifest = json.loads((DATA / manifest_name).read_text(encoding="utf-8"))
    md_lines = [
        line for line in (DATA / md_name).read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("## ")
    ]
    assert list(manifest.values()) == md_lines
    assert all(label.startswith(("PART1_GOD_", "PART2_MIND_"))
               for label in manifest)


def test_part1_god_md_matches_manifest():
    _assert_md_matches_manifest("part1_god.md", "part1_god_manifest.json")


def test_part2_mind_md_matches_manifest():
    _assert_md_matches_manifest("part2_mind.md", "part2_mind_manifest.json")
