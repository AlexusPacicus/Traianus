#!/usr/bin/env python
"""Build the frozen Spinoza Ethics Part II ("De Mente") corpus + manifest.

Input: Project Gutenberg eBook #3800 plain text (Elwes translation,
public domain) previously downloaded by the operator. Offline: reads a
local file, no network primitives.

Granularity: ONE SENTENCE = ONE CHUNK (vectorial unit v ∈ R^d). Every
sentence of Part II becomes exactly one manifest entry, in reading order.

Outputs (frozen research datasets under data/spinoza/):
- part2_mind.md           continuous text, one chunk per line, reading order.
- part2_mind_manifest.json immutable {label -> chunk} map, insertion order
  == reading order. Labels are neutral metadata (never embedded): the
  chunk text itself is exactly what enters the representation pipeline.

Label scheme (prefix PART2_MIND_ for Part II, PART1_GOD_ for Part I;
_NN sequential within the unit):
  PART2_MIND_PREFACE_NN        preface
  PART2_MIND_DEF_NN[_Ckk]      definitions (Explanation absorbed)
  PART2_MIND_AX_NN             axioms (both groups, document order)
  PART2_MIND_LEMMA_NN          lemmata (their proofs absorbed)
  PART2_MIND_POST_NN           postulates
  PART2_MIND_PNN_PROP[_Ckk]    proposition statement
  PART2_MIND_PNN_DEMO_KK[_Ckk] proof(s)
  PART2_MIND_PNN_COR_KK[_Ckk]  corollaries
  PART2_MIND_PNN_ESC_KK[_Ckk]  notes / scholia

Elwes' editorial "N.B." notes are excluded from the corpus.
"""

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

SECTION_HEADERS = {
    "preface": re.compile(r"^PREFACE\.?\s*$"),
    "definitions": re.compile(r"^DEFINITIONS\.?\s*$"),
    "axioms": re.compile(r"^AXIOMS?\.?\s*$"),
    "propositions": re.compile(r"^PROPOSITIONS\.?\s*$"),
    "postulates": re.compile(r"^POSTULATES\.?\s*$"),
    "appendix": re.compile(r"^APPENDAGE\.?\s*$|^APPENDIX[:.]?\s*$"),
    "definitions_of_emotions": re.compile(
        r"^DEFINITIONS OF THE EMOTIONS\.?\s*$"),
    "general_definition": re.compile(
        r"^GENERAL DEFINITION OF THE EMOTIONS\.?\s*$"),
}

# Sections whose units are roman-numbered items ("I. ...") rather than
# inline markers, mapped to their label codes.
ROMAN_ITEM_SECTIONS = {
    "definitions": ("definition", "DEF"),
    "axioms": ("axiom", "AX"),
    "postulates": ("postulate", "POST"),
    "definitions_of_emotions": ("emotion_definition", "DEFEMO"),
}

PART_CONFIG = {
    1: {
        "start": re.compile(r"^PART I\..*$", re.M),
        "end": re.compile(r"^Part II\.\s*$", re.M),
        "prefix": "PART1_GOD",
        "md_name": "part1_god.md",
        "manifest_name": "part1_god_manifest.json",
        "md_title": "## **Part 1\\. Concerning God**",
        # Part I lists definitions as roman items under DEFINITIONS.;
        # Part II uses inline DEFINITION N. markers.
        "roman_sections": ["definitions", "axioms", "postulates"],
    },
    2: {
        "start": re.compile(r"^Part II\.\s*$", re.M),
        "end": re.compile(r"^PART III\.\s*$", re.M),
        "prefix": "PART2_MIND",
        "md_name": "part2_mind.md",
        "manifest_name": "part2_mind_manifest.json",
        "md_title": "## **Part 2\\. On the Nature and Origin of the Mind**",
        "roman_sections": ["axioms", "postulates"],
    },
    3: {
        "start": re.compile(r"^PART III\.\s*$", re.M),
        "end": re.compile(r"^PART IV:\s*$", re.M),
        "prefix": "PART3_AFFECTS",
        "md_name": "part3_affects.md",
        "manifest_name": "part3_affects_manifest.json",
        "md_title": "## **Part 3\\. On the Origin and Nature of the Emotions**",
        "roman_sections": ["definitions", "postulates",
                           "definitions_of_emotions"],
    },
    4: {
        "start": re.compile(r"^PART IV:\s*$", re.M),
        "end": re.compile(r"^PART V:\s*$", re.M),
        "prefix": "PART4_BONDAGE",
        "md_name": "part4_bondage.md",
        "manifest_name": "part4_bondage_manifest.json",
        "md_title": "## **Part 4\\. Of Human Bondage, or the Strength of the Emotions**",
        "roman_sections": ["definitions", "axioms"],
    },
}

INLINE_MARKERS = [
    ("definition", re.compile(r"^DEFINITION\s+([IVXL]+)\.\s*")),
    ("axiom", re.compile(r"^AXIOM\s+([IVXL]+)\.\s*")),
    ("lemma", re.compile(r"^LEMMA\s+([IVXL]+)\.\s*")),
    ("postulate", re.compile(r"^POSTULATE\s+([IVXL]+)?\.?\s*")),
    ("prop", re.compile(r"^PROP\.\s+([IVXL]+)\.\s*")),
    ("proof", re.compile(r"^Proof\.--\s*")),
    ("corollary", re.compile(r"^Corollary\.--\s*")),
    ("note", re.compile(r"^Note\.--\s*")),
]

ROMAN_ITEM = re.compile(r"^([IVXL]+)\.\s+(.*)$")
EDITORIAL_NOTE = re.compile(r"^N\.B\.\s")
GUTENBERG_FOOTNOTE = re.compile(r"^\[\d+\]\s")

ROMAN = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7,
    "VIII": 8, "IX": 9, "X": 10, "XI": 11, "XII": 12, "XIII": 13,
    "XIV": 14, "XV": 15, "XVI": 16, "XVII": 17, "XVIII": 18, "XIX": 19,
    "XX": 20, "XXI": 21, "XXII": 22, "XXIII": 23, "XXIV": 24, "XXV": 25,
    "XXVI": 26, "XXVII": 27, "XXVIII": 28, "XXIX": 29, "XXX": 30,
    "XXXI": 31, "XXXII": 32, "XXXIII": 33, "XXXIV": 34, "XXXV": 35,
    "XXXVI": 36, "XXXVII": 37, "XXXVIII": 38, "XXXIX": 39, "XL": 40,
    "XLI": 41, "XLII": 42, "XLIII": 43, "XLIV": 44, "XLV": 45, "XLVI": 46,
    "XLVII": 47, "XLVIII": 48, "XLIX": 49, "L": 50, "LI": 51, "LII": 52,
    "LIII": 53, "LIV": 54, "LV": 55, "LVI": 56, "LVII": 57, "LVIII": 58,
    "LIX": 59, "LX": 60, "LXI": 61, "LXII": 62, "LXIII": 63, "LXIV": 64,
    "LXV": 65, "LXVI": 66, "LXVII": 67, "LXVIII": 68, "LXIX": 69,
    "LXX": 70, "LXXI": 71, "LXXII": 72, "LXXIII": 73, "LXXIV": 74,
    "LXXV": 75, "LXXVI": 76, "LXXVII": 77, "LXXVIII": 78, "LXXIX": 79,
    "LXXX": 80,
}

CHILD_CODES = {"proof": "DEMO", "corollary": "COR", "note": "ESC"}
CHILD_KINDS = set(CHILD_CODES)

SENTENCE_SPLIT = re.compile(r"(?<=[.;:!?])\s+")

# Citation/abbreviation tails that must NOT terminate a sentence
# ("Pt. i.", "II., Def. i.", "(I. xxviii.)", "Q.E.D.", "&c." ...).
NOT_BOUNDARY = re.compile(
    r"(?:\s|\()("
    r"Pt|Def|Prop|Cor|Ax|Lem|Post|Schol|Pref|App"
    r"|i\.e|e\.g|etc|&c|[ivxlIVXL]{1,5}|[A-Z]"
    r")\.$"
)


def split_sentences(text: str) -> list[str]:
    """One chunk per real sentence; abbreviation/citation dots protected."""
    sentences, start = [], 0
    for m in SENTENCE_SPLIT.finditer(text):
        tail = text[max(start, m.start() - 16):m.end()]
        nxt = text[m.end():m.end() + 1]
        if NOT_BOUNDARY.search(tail) or (nxt and not nxt.isupper()):
            continue  # keep current sentence open
        sentences.append(text[start:m.end()].strip())
        start = m.end()
    tail = text[start:].strip()
    if tail:
        sentences.append(tail)
    # Citation debris ("Coroll.).", "Nov.", "i., Prop.") merges backwards.
    cite_start = re.compile(
        r"^(?:[a-z]|\d|[ivxlIVXL]{1,5}\b"
        r"|(?:Pt|Def|Prop|Cor|Coroll|Dem|Ax|Lem|Lemma|Post|Schol"
        r"|Pref|App|Note|Nov|Org|i\.e|e\.g|etc|&c)\.)")
    merged: list[str] = []
    for sentence in sentences:
        if merged and (re.fullmatch(r"Q\.E\.D\.", sentence)
                       or cite_start.match(sentence)):
            merged[-1] += " " + sentence
        else:
            merged.append(sentence)
    return [s for s in merged if s]


def extract_part(raw: str, cfg: dict) -> list[str]:
    """Whitespace-normalized paragraph blocks of one Ethics part."""
    start = cfg["start"].search(raw)
    end = cfg["end"].search(raw)
    if not start or not end or start.end() > end.start():
        raise SystemExit("ERR: part boundaries not found in source text")
    body = raw[start.end():end.start()]
    body = re.sub(r"\[\d+\]", "", body)  # Gutenberg footnote reference markers
    blocks, current = [], []
    for line in body.splitlines():
        stripped = line.strip()
        if stripped:
            current.append(stripped)
            continue
        if current:
            blocks.append(re.sub(r"\s+", " ", " ".join(current)).strip())
            current = []
    if current:
        blocks.append(re.sub(r"\s+", " ", " ".join(current)).strip())
    return [b for b in blocks if b]


def build_manifest(source_path: Path, part: int) -> dict[str, str]:
    cfg = PART_CONFIG[part]
    prefix = cfg["prefix"]
    blocks = extract_part(source_path.read_text(encoding="utf-8"), cfg)

    manifest: dict[str, str] = {}
    counters = {"axiom": 0, "lemma": 0, "postulate": 0, "definition": 0,
                "emotion_definition": 0}
    child_seq: dict[str, int] = {}
    section = None
    state_label: str | None = None      # label absorbing unmarked blocks
    prop_open = False                   # children attach to open proposition
    sub_context = False                 # inside an inline axiom/lemma/postulate
    child_absorbed = False              # a proof/corollary/note was absorbed

    def emit(label: str | None, buf: list[str]):
        if not (label and buf):
            return
        text = " ".join(buf)
        sentences = split_sentences(text)
        if len(sentences) == 1:
            manifest[label] = sentences[0]
        else:
            for k, sentence in enumerate(sentences, 1):
                manifest[f"{label}_C{k:02d}"] = sentence

    def close(buf: list[str]):
        nonlocal state_label
        emit(state_label, buf)
        buf.clear()
        state_label = None

    buf: list[str] = []
    for block in blocks:
        if GUTENBERG_FOOTNOTE.match(block):
            continue
        header_kind = next(
            (k for k, pat in SECTION_HEADERS.items() if pat.match(block)), None)
        if header_kind:
            close(buf)
            section = header_kind
            sub_context = False
            if header_kind == "appendix":
                state_label = f"{prefix}_APPENDIX"
            elif header_kind == "general_definition":
                state_label = f"{prefix}_GENDEF"
            continue
        # Elwes' cross-reference notes appear under AXIOMS/POSTULATES;
        # elsewhere an "N.B." is Spinoza's own text and must be kept.
        if EDITORIAL_NOTE.match(block) and section in ("axioms", "postulates"):
            continue

        marker = None
        for kind, pattern in INLINE_MARKERS:
            matched = pattern.match(block)
            if matched:
                marker = (kind, matched)
                break

        roman_sections: tuple[str, ...] = tuple(cfg["roman_sections"])
        if section in roman_sections and not marker:
            item = ROMAN_ITEM.match(block)
            if item or counters[ROMAN_ITEM_SECTIONS[section][0]] == 0:
                close(buf)
                family, code = ROMAN_ITEM_SECTIONS[section]
                counters[family] += 1
                state_label = f"{prefix}_{code}_{counters[family]:02d}"
                buf.append(item.group(2) if item else block)
                continue
            if state_label is None:
                continue  # stray preamble before first numbered item
            buf.append(block)
            continue

        if marker is None:
            if state_label is None:
                continue  # preamble between title and first section
            if sub_context and child_absorbed and prop_open:
                # Digression prose after a lemma/axiom proof belongs to the
                # enclosing proposition's scholium, not to the sub-unit.
                close(buf)
                key = f"{prop_base}ESC"
                child_seq[key] = child_seq.get(key, 0) + 1
                state_label = f"{key}_{child_seq[key]:02d}"
                sub_context = False
            buf.append(block)
            continue

        kind, match = marker
        if kind in CHILD_KINDS and prop_open and not sub_context:
            close(buf)
            key = f"{prop_base}{CHILD_CODES[kind]}"
            child_seq[key] = child_seq.get(key, 0) + 1
            state_label = f"{key}_{child_seq[key]:02d}"
        elif kind in CHILD_KINDS:
            # proof/corollary/note of an inline axiom/lemma/postulate: absorbed
            buf.append(block)
            child_absorbed = True
            continue
        else:
            close(buf)
            sub_context = False
            if kind == "prop":
                nn = ROMAN.get(match.group(1).upper())
                if nn is None:
                    raise SystemExit(f"ERR: unknown roman {match.group(1)!r}")
                prop_base = f"{prefix}_P{nn:02d}_"
                state_label = f"{prop_base}PROP"
                child_seq = {}
                prop_open = True
            elif kind == "definition":
                nn = ROMAN.get(match.group(1).upper())
                state_label = f"{prefix}_DEF_{nn:02d}" if nn else None
            elif kind in ("axiom", "lemma", "postulate"):
                family = kind
                counters[family] += 1
                code = {"axiom": "AX", "lemma": "LEMMA", "postulate": "POST"}[kind]
                state_label = f"{prefix}_{code}_{counters[family]:02d}"
                sub_context = True
                child_absorbed = False
        rest = block[match.end():].strip()
        if rest:
            buf.append(rest)
    close(buf)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path,
                        help="path to Project Gutenberg #3800 plain text")
    parser.add_argument("--part", type=int, choices=sorted(PART_CONFIG),
                        default=2,
                        help="Ethics part to derive (default: 2)")
    args = parser.parse_args()

    if not args.source.is_file():
        print(f"ERR: source not found: {args.source}", file=sys.stderr)
        return 2

    cfg = PART_CONFIG[args.part]
    manifest = build_manifest(args.source, args.part)

    out_dir = REPO_ROOT / "data" / "spinoza"
    out_dir.mkdir(parents=True, exist_ok=True)

    md_lines = [cfg["md_title"], ""]
    for chunk in manifest.values():
        md_lines.append(chunk)
    (out_dir / cfg["md_name"]).write_text(
        "\n".join(md_lines).rstrip() + "\n", encoding="utf-8")

    (out_dir / cfg["manifest_name"]).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")

    words = [len(c.split()) for c in manifest.values()]
    print(f"[+] sentence-chunks: {len(manifest)} | words min={min(words)} "
          f"max={max(words)} mean={sum(words)/len(words):.1f}")
    kinds: dict[str, int] = {}
    for label in manifest:
        kind = re.sub(r"(_C\d+|_\d+)$", "", label)
        kinds[kind] = kinds.get(kind, 0) + 1
    for kind, count in sorted(kinds.items()):
        print(f"    {kind}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
