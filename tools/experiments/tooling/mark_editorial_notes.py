#!/usr/bin/env python
"""Mark manifest chunks that come from Gutenberg footnote blocks, from the
source, without rebuilding the corpus.

build_spinoza_corpus.extract_part removes footnote reference markers
(re.sub(r'\\[\\d+\\]', '', body)) before splitting the source into blocks, so
its own GUTENBERG_FOOTNOTE filter (^\\[\\d+\\]\\s) never sees a marker and
every footnote block of PG#3800 entered the frozen manifests as if it were
Spinoza's own text. This tool reads the committed source and the five
manifests -- it never rebuilds them -- and reports, for every manifest
label, whether its chunk comes from a footnote block.

Rule: a footnote block is a source paragraph block (blank-line separated,
whitespace-normalised, within a part's builder boundaries, markers intact)
whose raw text starts with '[N] '. Its sentences, obtained by stripping the
marker and calling the builder's own split_sentences, are matched as
substrings, in reading order, against the part's frozen manifest chunks (a
forward-only cursor -- also advanced by every ordinary block in between --
prevents matching an earlier occurrence of the same text). Blocks that
immediately follow a footnote block, up to the next block that is a
section header, an inline marker (DEFINITION/AXIOM/LEMMA/POSTULATE/PROP./
Proof.--/Corollary.--/Note.--), a roman-numbered list item (the
DEFINITIONS/AXIOMS/POSTULATES bare "I. ..." form) or another footnote
marker, are reported as continuation candidates and are never marked.

Offline: reads local files, no network primitives.
"""

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from tools.experiments.tooling.build_spinoza_corpus import (
    GUTENBERG_FOOTNOTE,
    INLINE_MARKERS,
    PART_CONFIG,
    ROMAN_ITEM,
    SECTION_HEADERS,
    split_sentences,
)

# data/spinoza/PROVENANCE.md declares this snapshot's hash (abbreviated
# there as "647f0227..."); the full value is the one committed in
# tests/unit/test_builder_reproducibility.py::test_source_snapshot_intact.
SOURCE_SHA256 = ("647f0227f3700b5d221a004fc545568c879f6f204e952f1cf"
                  "0c24672676c2a60")

RULE = (
    "A footnote block is a source paragraph block (blank-line separated, "
    "whitespace-normalised, within a part's builder boundaries, markers "
    "intact) whose raw text starts with '[N] '. Its sentences, obtained by "
    "stripping the marker and calling the builder's split_sentences, are "
    "matched as substrings, in reading order, against the part's frozen "
    "manifest chunks (a forward-only cursor, also advanced by every "
    "ordinary block in between, prevents matching an earlier occurrence of "
    "the same text). Blocks that immediately follow a footnote block, up "
    "to the next block that is a section header, an inline marker "
    "(DEFINITION/AXIOM/LEMMA/POSTULATE/PROP./Proof.--/Corollary.--/"
    "Note.--), a roman-numbered list item, or another footnote marker, "
    "are reported as continuation candidates and are never marked."
)

DEFAULT_SOURCE = REPO_ROOT / "data" / "spinoza" / "source" / "pg3800.txt"
DEFAULT_OUT = REPO_ROOT / "data" / "spinoza" / "editorial_marks.json"
DEFAULT_DATA_DIR = REPO_ROOT / "data" / "spinoza"


@dataclass
class PartMarks:
    footnote_blocks: list = field(default_factory=list)
    marked: dict = field(default_factory=dict)
    unmatched: list = field(default_factory=list)
    continuation_candidates: dict = field(default_factory=dict)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _blank_separated_blocks(body: str) -> list[str]:
    """Whitespace-normalised paragraph blocks; markers left untouched."""
    blocks: list[str] = []
    current: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if stripped:
            current.append(stripped)
            continue
        if current:
            blocks.append(_normalize(" ".join(current)))
            current = []
    if current:
        blocks.append(_normalize(" ".join(current)))
    return [b for b in blocks if b]


def part_raw_blocks(raw: str, cfg: dict) -> list[str]:
    """Blank-line-separated blocks of one Ethics part, markers intact.

    Mirrors build_spinoza_corpus.extract_part's blocking exactly, minus its
    marker-stripping re.sub: extract_part does not expose that step
    separately, so it is reproduced here rather than changing the builder.
    """
    start = cfg["start"].search(raw)
    end = cfg["end"].search(raw)
    if not start or not end or start.end() > end.start():
        raise SystemExit("ERR: part boundaries not found in source text")
    return _blank_separated_blocks(raw[start.end():end.start()])


def _is_header(block: str) -> bool:
    return any(pattern.match(block) for pattern in SECTION_HEADERS.values())


def _is_inline_marker(block: str) -> bool:
    return (any(pattern.match(block) for _, pattern in INLINE_MARKERS)
            or ROMAN_ITEM.match(block) is not None)


def _footnote_number(block: str) -> str:
    match = re.match(r"^\[(\d+)\]", block)
    assert match is not None
    return match.group(1)


# A bare roman/arabic list-item marker ("I.", "III.", "(2.)"). The builder
# strips these before calling split_sentences (ROMAN_ITEM/child numbering);
# fed whole, split_sentences' own abbreviation guard cannot protect a
# marker with nothing before it (its 16-char lookback window is empty at
# the start of a block), so it surfaces as a spurious one-token "sentence"
# that -- being short and generic -- can match anywhere by containment.
_LIST_MARKER = re.compile(
    r"^\(?[IVXLCDMivxlcdm]{1,8}\.?\)?$|^\(?\d{1,3}\.?\)?$")


def _candidate_sentences(text: str) -> list[str]:
    return [s for s in split_sentences(text) if not _LIST_MARKER.match(s)]


def _strip_known_prefix(block: str) -> str:
    """Best-effort mirror of build_manifest's own marker stripping (the
    part it does expose, via INLINE_MARKERS/ROMAN_ITEM), so an ordinary
    block's text tracks the manifest closely enough to keep the cursor in
    sync. Not a re-implementation of the builder's label state machine
    (child/sub-context absorption is not reproduced): a best-effort cursor
    aid, not a source of matches or marks."""
    for _, pattern in INLINE_MARKERS:
        match = pattern.match(block)
        if match:
            return block[match.end():].strip()
    item = ROMAN_ITEM.match(block)
    if item:
        return item.group(2)
    return block


def _footnote_text(block: str) -> str:
    return _normalize(re.sub(r"^\[\d+\]\s*", "", block))


def _coverage(chunk: str, sentences: list[str]) -> float:
    """Share of chunk's non-whitespace characters covered by the union of
    the matched footnote sentences' occurrences in the chunk."""
    covered = bytearray(len(chunk))
    for sentence in sentences:
        start = chunk.find(sentence)
        assert start != -1, "matched sentence not found in its own chunk"
        for i in range(start, start + len(sentence)):
            covered[i] = 1
    total = sum(1 for ch in chunk if not ch.isspace())
    if total == 0:
        return 0.0
    hit = sum(1 for i, ch in enumerate(chunk) if covered[i] and not ch.isspace())
    return hit / total


def mark_part(blocks: list[str], manifest: dict, part_prefix: str) -> PartMarks:
    """Identify footnote-derived and continuation-candidate manifest labels.

    blocks: the part's paragraph blocks with markers intact (part_raw_blocks).
    manifest: the frozen {label -> chunk} map, in reading order.
    """
    result = PartMarks()
    labels = list(manifest.items())
    cursor = 0
    label_sentences: dict[str, list[str]] = {}

    def find_from(start: int, needle: str) -> int | None:
        for idx in range(start, len(labels)):
            if needle in labels[idx][1]:
                return idx
        return None

    def advance(idx: int, sentence: str) -> int:
        # A label fully consumed by an exact match is closed (cursor moves
        # past it); a label only partially matched (the sentence is a
        # strict substring, e.g. a footnote fused into a longer chunk, cf.
        # data/spinoza/part2_mind_manifest.json PART2_MIND_P13_ESC_01_C05)
        # stays open for a later match -- the footnote's own sentence, or
        # the real content that follows it in the same fused chunk.
        return idx + 1 if sentence == labels[idx][1] else idx

    i = 0
    n_blocks = len(blocks)
    while i < n_blocks:
        block = blocks[i]
        if not GUTENBERG_FOOTNOTE.match(block):
            for sentence in _candidate_sentences(_strip_known_prefix(block)):
                idx = find_from(cursor, sentence)
                if idx is not None:
                    cursor = advance(idx, sentence)
            i += 1
            continue

        n = _footnote_number(block)
        matched_labels = []
        for sentence in _candidate_sentences(_footnote_text(block)):
            idx = find_from(cursor, sentence)
            if idx is None:
                result.unmatched.append(
                    {"part": part_prefix, "footnote": n, "text": sentence})
                continue
            label, _ = labels[idx]
            matched_labels.append(label)
            result.marked[label] = {"footnote": n, "part": part_prefix}
            label_sentences.setdefault(label, []).append(sentence)
            cursor = advance(idx, sentence)
        result.footnote_blocks.append({
            "part": part_prefix, "footnote": n, "text": block,
            "labels": matched_labels,
        })

        j = i + 1
        while j < n_blocks:
            candidate = blocks[j]
            if (GUTENBERG_FOOTNOTE.match(candidate) or _is_header(candidate)
                    or _is_inline_marker(candidate)):
                break
            for sentence in _candidate_sentences(candidate):
                idx = find_from(cursor, sentence)
                if idx is None:
                    continue
                label, text = labels[idx]
                if label in result.marked:
                    cursor = advance(idx, sentence)
                    continue
                result.continuation_candidates[label] = {
                    "after_footnote": n, "part": part_prefix, "text": text,
                }
                cursor = advance(idx, sentence)
            j += 1
        i = j

    chunk_by_label = dict(labels)
    for label, info in result.marked.items():
        coverage = _coverage(chunk_by_label[label], label_sentences[label])
        info["coverage"] = coverage
        info["pure"] = coverage == 1.0
    return result


def _load_manifest(part: int, data_dir: Path) -> dict:
    cfg = PART_CONFIG[part]
    path = data_dir / cfg["manifest_name"]
    return json.loads(path.read_text(encoding="utf-8"))


def analyze(raw: str, data_dir: Path = DEFAULT_DATA_DIR) -> dict:
    footnote_blocks: list = []
    marked: dict = {}
    unmatched: list = []
    continuation_candidates: dict = {}
    counts: dict = {}

    for part in sorted(PART_CONFIG):
        cfg = PART_CONFIG[part]
        blocks = part_raw_blocks(raw, cfg)
        manifest = _load_manifest(part, data_dir)
        result = mark_part(blocks, manifest, cfg["prefix"])

        footnote_blocks.extend(result.footnote_blocks)
        marked.update(result.marked)
        unmatched.extend(result.unmatched)
        continuation_candidates.update(result.continuation_candidates)
        part_pure = sum(1 for info in result.marked.values() if info["pure"])
        counts[cfg["prefix"]] = {
            "footnote_blocks": len(result.footnote_blocks),
            "marked": len(result.marked),
            "unmatched": len(result.unmatched),
            "continuation_candidates": len(result.continuation_candidates),
            "pure": part_pure,
            "mixed": len(result.marked) - part_pure,
        }

    total_pure = sum(1 for info in marked.values() if info["pure"])
    counts["total"] = {
        "footnote_blocks": len(footnote_blocks),
        "marked": len(marked),
        "unmatched": len(unmatched),
        "continuation_candidates": len(continuation_candidates),
        "pure": total_pure,
        "mixed": len(marked) - total_pure,
    }

    return {
        "source_sha256": SOURCE_SHA256,
        "rule": RULE,
        "footnote_blocks": footnote_blocks,
        "marked": marked,
        "unmatched": unmatched,
        "continuation_candidates": continuation_candidates,
        "counts": counts,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE,
                        help="PG#3800 source path (default: the committed "
                             "snapshot)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT,
                        help="output JSON path")
    args = parser.parse_args(argv)

    if not args.source.is_file():
        print(f"ERR: source not found: {args.source}", file=sys.stderr)
        return 2

    raw_bytes = args.source.read_bytes()
    digest = hashlib.sha256(raw_bytes).hexdigest()
    if digest != SOURCE_SHA256:
        print(f"ERR: source sha256 mismatch: expected {SOURCE_SHA256}, "
              f"got {digest} -- refusing to run", file=sys.stderr)
        return 2

    raw = raw_bytes.decode("utf-8")
    report = analyze(raw, data_dir=DEFAULT_DATA_DIR)

    payload = json.dumps(report, sort_keys=True, indent=2, allow_nan=False,
                         ensure_ascii=False) + "\n"
    args.out.write_text(payload, encoding="utf-8", newline="\n")

    total = report["counts"]["total"]
    print(f"[+] footnote blocks: {total['footnote_blocks']} | "
          f"marked labels: {total['marked']} | "
          f"continuation candidates: {total['continuation_candidates']} | "
          f"pure: {total['pure']} | mixed: {total['mixed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
