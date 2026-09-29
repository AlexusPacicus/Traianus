"""Ethics citation graph: a labelled descriptive exploration (docs/methodology/METHODOLOGY.md "Explore").

It tests no hypothesis and decides nothing. It reads only text, the five frozen manifests {label -> chunk} of
data/spinoza/ and editorial_marks.json, and lists what Spinoza cites in the Ethics: propositions, definitions,
axioms, postulates, lemmas, corollaries and scholia. Every citation span found is resolved to the labels of the
cited unit or listed, with its label, offset and text, as unresolved (the grammar cannot read it) or dangling (the
unit has no label). No embeddings, no axes, no graph of relations; the EVAL/FIT split plays no role.

Refuses to run, writing nothing, unless the sha256 of the five manifests and of editorial_marks.json equal the
frozen pins below. Standard library only. Deterministic: the same input writes the same bytes.

Usage:
    python3 tools/experiments/citation_graph.py [--out PATH]
"""

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from collections.abc import Collection, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NamedTuple

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA = REPO_ROOT / "data" / "spinoza"
MANIFESTS = [
    DATA / "part1_god_manifest.json",
    DATA / "part2_mind_manifest.json",
    DATA / "part3_affects_manifest.json",
    DATA / "part4_bondage_manifest.json",
    DATA / "part5_power_manifest.json",
]
MARKS = DATA / "editorial_marks.json"
EXPECTED = {
    MANIFESTS[0]: "848c2ad98645c79820354b861532cb22e8acbf030d4d53d961b8eebc9f2696fe",
    MANIFESTS[1]: "0aa584037d237318f8a0f343403e1a0fb9c7ce90bb9cd9096607404c7523ccdf",
    MANIFESTS[2]: "7ef2f0aa66b383c80872bf35ab2e17b5d6bcee42b08113688b5db8d1b4ec4e06",
    MANIFESTS[3]: "8aa3e2d7159f1d105ad7a0f2ba95ebd23f466bdde02e10e5ac34cc0c23daf501",
    MANIFESTS[4]: "29b937dfb7fdea6e6efbd1fafc5fb7d7d604ace2d833dea75047e24babafdd70",
    MARKS: "99a80f5e327b431c4b13c9f00043c9f668d3799f425b6750bee4f67fc1e299d2",
}
DEFAULT_OUT = REPO_ROOT / "data" / "refapp" / "citation_graph.json"

STATEMENT = (
    "Descriptive extraction of the Ethics' internal citation graph from the frozen manifests: text only, no "
    "embeddings, no axes, no graph of relations. Spans are resolved to labels, unresolved or dangling; tests no "
    "hypothesis and decides nothing."
)
TOP_CITED = 20
MODES = ("cf", "explicit", "see")


class IntegrityError(Exception):
    """An input file is unpinned or its sha256 differs from its pin."""


class Unit(NamedTuple):
    """A citable unit: kind is PROP, COR, ESC, DEF, AX, POST, LEMMA or DEFEMO; sub numbers COR and ESC."""

    part: int
    kind: str
    num: int
    sub: int | None = None


class Span(NamedTuple):
    """offset is where text starts in the chunk; source is "a" (parenthesised) or "b" (a 'by' clause)."""

    offset: int
    text: str
    source: str


@dataclass(frozen=True)
class Parse:
    """mode: explicit, see or cf. relative: (form, resolved unit or None) for every relative form met."""

    mode: str
    units: tuple[Unit, ...]
    relative: tuple[tuple[str, Unit | None], ...]
    error: str | None


_LABEL = re.compile(
    r"PART(\d)_[A-Z]+_(?:P(\d+)_(PROP|DEMO|ESC|COR)(?:_(\d+))?|(DEF|AX|POST|LEMMA|DEFEMO)_(\d+)|(GENDEF|APPENDIX))"
    r"(?:_C\d+)?"
)
_TOKEN = re.compile(
    r"""
    (?P<defemo>Def\.\s+of\s+the\s+Emotions)
   |(?P<rel>the\s+(?:last|foregoing|preceding)\s+Prop\b\.?)
   |(?P<same>the\s+same\s+Ax(?:iom)?\b\.?)
   |(?P<part>Part\s+[ivxIVX]+\b\.?)
   |(?P<partnum>(?:IV|V|I{1,3})\.)
   |(?P<def>Deff?\b\.?)
   |(?P<ax>Ax(?:iom)?\b\.?)
   |(?P<post>Post\b\.?)
   |(?P<lemma>Lemma\b)
   |(?P<prop>Prop\b\.?)
   |(?P<cor>Coroll\b\.?)
   |(?P<esc>(?:note|Schol)\b\.?)
   |(?P<num>[ivxl]+\b\.?)
   |(?P<sep>,|;|and\b)
   |(?P<unk>[^\s,;]+)
    """,
    re.VERBOSE,
)
_MODE = re.compile(r"\s*(?:(what\s+is\s+the\s+same\s+thing,\s+by|by|from)|(see)|(cf\.))\s+", re.IGNORECASE)
_CITES = re.compile(
    r"\b(?:Prop|Def|Ax|Post|Lemma|Coroll|Schol)|\bnote\b|\b(?:IV|V|I{1,3})\.\s*[ivxl]+\b|\bPart\s+[ivxIVX]+\b"
)
_NAMES = re.compile(r"\b(?:Prop|Def|Ax|Post|Lemma)")
_KIND = {"def": "DEF", "ax": "AX", "post": "POST", "lemma": "LEMMA", "prop": "PROP"}
_START = frozenset({"rel", "same", "defemo", "part", "partnum", *_KIND})
_PART_OF = re.compile(r"PART(\d+)_")


def _roman(text: str) -> int | None:
    """Value of a lower-case roman numeral in i, v, x, l, or None when it is not a well-formed one."""
    value = {"i": 1, "v": 5, "x": 10, "l": 50}
    if not text or any(c not in value for c in text):
        return None
    total = sum(-value[c] if i + 1 < len(text) and value[c] < value[text[i + 1]] else value[c] for i, c in enumerate(text))
    return total if _to_roman(total) == text else None


def _to_roman(number: int) -> str:
    out = "l" * (number // 50)
    number %= 50
    for numeral, size in (("xl", 40), ("x", 10), ("ix", 9), ("v", 5), ("iv", 4), ("i", 1)):
        out += numeral * (number // size)
        number %= size
    return out


def parse_label(label: str) -> Unit | None:
    """The unit a manifest label belongs to (chunk suffix _Cnn dropped), or None for a label of no known shape."""
    m = _LABEL.fullmatch(label)
    if m is None:
        return None
    part, prop_n, prop_kind, prop_sub, kind, num, whole = m.groups()
    if prop_kind:
        return Unit(int(part), prop_kind, int(prop_n), int(prop_sub) if prop_sub else None)
    if kind:
        return Unit(int(part), kind, int(num))
    return Unit(int(part), whole, 0)


def _name(unit: Unit) -> str:
    return f"{unit.part}.{unit.kind}.{unit.num}" + (f".{unit.sub}" if unit.sub is not None else "")


def _scan(text: str, pos: int = 0) -> Iterator[re.Match[str]]:
    while True:
        while pos < len(text) and text[pos].isspace():
            pos += 1
        m = _TOKEN.match(text, pos)
        if m is None:
            return
        yield m
        pos = m.end()


@dataclass
class _Sub:
    kind: str
    num: int | None


@dataclass
class _Item:
    part: int | None
    kind: str
    num: int
    base: bool = True
    subs: list[_Sub] = field(default_factory=list)


def parse_span(text: str, citing: str, last_axiom: tuple[int, int] | None = None) -> Parse:
    """Read one citation span cited from the label `citing`; the grammar, in full:

    - Mode: a leading 'by', 'from' or 'what is the same thing, by' is explicit, 'see' is see, 'cf.' is cf.
    - Part: an explicit numeral (I. to V., or 'Part i.' to 'Part v.', before or after the rest) or, if absent, the
      part of `citing`.
    - Kind: Prop by default, or Def / Deff, Ax / Axiom, Post, Lemma, or 'Def. of the Emotions' (DEFEMO, always
      part III).
    - Numbers: lower-case roman numerals, one or several ('II. xi., xiii.', 'IV. xxvi. xxvii.', 'Deff. iii. and
      vi.'), each inheriting the part and kind before it.
    - Sub-units: 'Coroll.' is COR and 'note' or 'Schol.' is ESC; 'Coroll. ii.' is COR_02, a bare one is _01, and a
      sub-unit replaces the proposition it follows ('II. xi. note'); 'and note' or 'and Coroll.' adds it to the
      proposition ('III. xi. and note'). After a numbered sub-unit further numbers are more sub-units; after a
      bare one a separated number is a new proposition.
    - Relative: 'the last', 'the foregoing' or 'the preceding' Prop. is proposition n - 1 when `citing` is a DEMO
      of proposition n and n when it is that proposition's ESC or COR; 'the same Axiom' is `last_axiom`, the last
      axiom cited earlier in the same chunk.

    Everything else is an error, never a partial reading: the whole span is unresolved.
    """
    m0 = _MODE.match(text)
    mode = "explicit"
    pos = 0
    if m0 is not None:
        mode = "see" if m0.group(2) else "cf" if m0.group(3) else "explicit"
        pos = m0.end()
    cited_from = parse_label(citing)
    items: list[_Item] = []
    relative: list[tuple[str, Unit | None]] = []
    part_ctx: int | None = None
    kind: str | None = None
    kind_open = False
    sub_item: _Item | None = None
    sub_state = ""
    last = ""
    last_sep = ""

    def fail(reason: str) -> Parse:
        return Parse(mode, (), tuple(relative), reason)

    for m in _scan(text, pos):
        tok = m.lastgroup
        raw = m.group()
        if tok == "unk":
            return fail(f"unread: {raw}")
        if tok == "sep":
            if sub_state == "bare" or raw == ";":
                sub_item, sub_state = None, ""
            last, last_sep = "sep", raw
            continue
        if tok == "num":
            number = _roman(raw.rstrip("."))
            if number is None:
                return fail(f"not a numeral: {raw}")
            if sub_item is not None and sub_state == "bare":
                sub_item.subs[-1].num = number
                sub_state = "numbered"
            elif sub_item is not None and sub_state == "numbered":
                sub_item.subs.append(_Sub(sub_item.subs[-1].kind, number))
            else:
                part = 3 if kind == "DEFEMO" else part_ctx
                items.append(_Item(part, kind or "PROP", number))
                kind_open = False
        elif tok in ("cor", "esc"):
            if kind_open or not items or items[-1].kind != "PROP":
                return fail(f"sub-unit without a proposition: {raw}")
            item = items[-1]
            if not item.subs:
                item.base = last == "sep" and last_sep == "and"
            item.subs.append(_Sub("COR" if tok == "cor" else "ESC", None))
            sub_item, sub_state = item, "bare"
        elif tok in ("part", "partnum"):
            number = _roman(raw.removeprefix("Part").strip().rstrip(".").lower())
            if kind_open or number is None:
                return fail(f"misplaced or unread part: {raw}")
            part_ctx, kind, sub_item, sub_state = number, None, None, ""
            for item in items:
                if item.part is None and item.kind != "DEFEMO":
                    item.part = number
        elif tok == "rel":
            form = raw.split()[1]
            unit = _relative(cited_from)
            relative.append((form, unit))
            if kind_open or unit is None:
                return fail(f"relative form without a proposition to point at: {raw}")
            items.append(_Item(unit.part, "PROP", unit.num))
            kind, sub_item, sub_state = None, None, ""
        elif tok == "same":
            relative.append(("same", None if last_axiom is None else Unit(last_axiom[0], "AX", last_axiom[1])))
            if kind_open or last_axiom is None:
                return fail("'the same Axiom' with no earlier axiom in the chunk")
            items.append(_Item(last_axiom[0], "AX", last_axiom[1]))
            kind, sub_item, sub_state = None, None, ""
        else:
            if kind_open or tok is None:
                return fail(f"kind without a number: {raw}")
            kind = "DEFEMO" if tok == "defemo" else _KIND[tok]
            kind_open = True
            sub_item, sub_state = None, ""
        last = tok or ""
    if kind_open:
        return fail("kind without a number")
    if not items:
        return fail("no unit")
    units: list[Unit] = []
    for item in items:
        part = item.part if item.part is not None else cited_from.part if cited_from is not None else None
        if part is None:
            return fail("the citing label has no part")
        if item.base:
            units.append(Unit(part, item.kind, item.num))
        units.extend(Unit(part, s.kind, item.num, 1 if s.num is None else s.num) for s in item.subs)
    return Parse(mode, tuple(dict.fromkeys(units)), tuple(relative), None)


def _relative(cited_from: Unit | None) -> Unit | None:
    if cited_from is None or cited_from.kind not in ("DEMO", "ESC", "COR"):
        return None
    number = cited_from.num - 1 if cited_from.kind == "DEMO" else cited_from.num
    return Unit(cited_from.part, "PROP", number) if number >= 1 else None


def _groups(text: str) -> list[tuple[int, int, int]]:
    """Outermost parenthesised groups as (index of '(', end of inner text, end of group); an unclosed one runs to
    the end of the text and a stray ')' is ignored."""
    out: list[tuple[int, int, int]] = []
    depth = 0
    start = 0
    for i, c in enumerate(text):
        if c == "(":
            if depth == 0:
                start = i
            depth += 1
        elif c == ")" and depth > 0:
            depth -= 1
            if depth == 0:
                out.append((start, i, i + 1))
    if depth > 0:
        out.append((start, len(text), len(text)))
    return out


def _by_clause_end(masked: str, start: int, after: int) -> int | None:
    """End of the 'by' clause starting at `start` that names a unit, or None. A clause that opens in the citation
    vocabulary runs to its last token; any other runs to the next , ; : or parenthesis, and counts only if it
    names Prop, Def, Ax, Post or Lemma (it will be unresolved)."""
    first = next(_scan(masked, after), None)
    if first is not None and first.lastgroup in _START:
        end = after
        for m in _scan(masked, after):
            if m.lastgroup == "unk":
                break
            if m.lastgroup != "sep":
                end = m.end()
        return end
    end = next((i for i in range(after, len(masked)) if masked[i] in ",;:\x00"), len(masked))
    if not _NAMES.search(masked[start:end]):
        return None
    while masked[end - 1].isspace():
        end -= 1
    return end


def find_spans(text: str) -> list[Span]:
    """The citation spans of one chunk, by offset: (a) the text of each outermost parenthesis that holds a citation
    token, and (b) each 'by' clause outside parentheses that names a unit."""
    spans: list[Span] = []
    masked = list(text)
    for start, inner_end, group_end in _groups(text):
        inner = text[start + 1 : inner_end]
        if _CITES.search(inner):
            spans.append(Span(start + 1, inner, "a"))
        masked[start:group_end] = "\x00" * (group_end - start)
    outside = "".join(masked)
    pos = 0
    for m in re.finditer(r"\b[Bb]y\b", outside):
        if m.start() < pos:
            continue
        end = _by_clause_end(outside, m.start(), m.end())
        if end is not None:
            spans.append(Span(m.start(), text[m.start() : end], "b"))
            pos = end
    return sorted(spans)


def quantiles(values: Sequence[int]) -> dict[str, float | None]:
    """min, quartiles and max by linear interpolation; None everywhere for no values."""
    keys = (("0", 0.0), ("0.25", 0.25), ("0.5", 0.5), ("0.75", 0.75), ("1", 1.0))
    if not values:
        return {key: None for key, _ in keys}
    ordered = sorted(values)
    out: dict[str, float | None] = {}
    for key, q in keys:
        pos = q * (len(ordered) - 1)
        lo = int(pos)
        hi = min(lo + 1, len(ordered) - 1)
        out[key] = ordered[lo] + (ordered[hi] - ordered[lo]) * (pos - lo)
    return out


def _components(pairs: Collection[tuple[str, str]]) -> list[int]:
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in pairs:
        parent[find(a)] = find(b)
    return sorted(Counter(find(x) for x in list(parent)).values(), reverse=True)


def analyse(chunks: Mapping[str, str], pure: Collection[str], mixed: Collection[str]) -> dict[str, Any]:
    """Spans, resolution, edges and descriptives of `chunks` {label -> text}. `pure` labels are editorial: their
    spans are kept apart and never enter the graph. `mixed` labels enter it, flagged."""
    absent = sorted((set(pure) | set(mixed)) - set(chunks))
    if absent:
        raise ValueError(f"marked labels absent from the manifests: {absent}")
    index: dict[Unit, list[str]] = {}
    for label in chunks:
        unit = parse_label(label)
        if unit is not None:
            index.setdefault(unit, []).append(label)
    by_source: Counter[str] = Counter()
    by_mode: Counter[str] = Counter()
    found = resolved = n_relative = with_dangling = self_dropped = 0
    unresolved: list[dict[str, Any]] = []
    dangling: list[dict[str, Any]] = []
    relative: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    editorial: list[dict[str, Any]] = []
    mixed_labels: set[str] = set()
    mixed_spans = 0
    for label, text in chunks.items():
        last_axiom: tuple[int, int] | None = None
        for span in find_spans(text):
            record = {"label": label, "offset": span.offset, "span": f"{label}@{span.offset}", "text": span.text}
            if label in pure:
                editorial.append({**record, "source": span.source})
                continue
            found += 1
            by_source[span.source] += 1
            if label in mixed:
                mixed_labels.add(label)
                mixed_spans += 1
            parse = parse_span(span.text, label, last_axiom)
            by_mode[parse.mode] += 1
            for form, unit in parse.relative:
                relative.append({**record, "form": form, "resolved_to": None if unit is None else _name(unit)})
            n_relative += bool(parse.relative)
            if parse.error is not None:
                unresolved.append({**record, "reason": parse.error})
                continue
            resolved += 1
            has_dangling = False
            for unit in parse.units:
                if unit.kind == "AX":
                    last_axiom = (unit.part, unit.num)
                targets = index.get(unit)
                if not targets:
                    has_dangling = True
                    dangling.append({**record, "unit": _name(unit)})
                    continue
                for target in targets:
                    if target == label:
                        self_dropped += 1
                    else:
                        edges.append({"citing": label, "cited": target, "span": record["span"], "mixed": label in mixed})
            with_dangling += has_dangling
    pairs = {(e["citing"], e["cited"]) for e in edges}
    out_degree = Counter(c for c, _ in pairs)
    in_degree = Counter(t for _, t in pairs)
    touched = out_degree.keys() | in_degree.keys()
    within = sum(_part(e["citing"]) == _part(e["cited"]) for e in edges)
    cited_by: dict[Unit, set[str]] = {}
    for e in edges:
        unit = parse_label(e["cited"])
        if unit is not None:
            cited_by.setdefault(unit, set()).add(e["citing"])
    top = sorted(cited_by.items(), key=lambda kv: (-len(kv[1]), kv[0].part, kv[0].kind, kv[0].num, kv[0].sub or 0))
    sizes = _components(pairs)
    return {
        "spans": {
            "found": found,
            "by_source": {"a": by_source["a"], "b": by_source["b"]},
            "by_mode": {mode: by_mode[mode] for mode in MODES},
            "resolved": resolved,
            "unresolved": len(unresolved),
            "relative": n_relative,
            "with_dangling": with_dangling,
        },
        "dangling_units": len(dangling),
        "edges": {
            "total": len(edges),
            "distinct_pairs": len(pairs),
            "within_part": within,
            "across_part": len(edges) - within,
            "self_citations_dropped": self_dropped,
        },
        "labels": {
            "total": len(chunks),
            "citing": len(out_degree),
            "cited": len(in_degree),
            "touched": len(touched),
            "share_touched": len(touched) / len(chunks) if chunks else 0.0,
        },
        "degrees": {
            "basis": "distinct citing-cited label pairs, over every label",
            "in": quantiles([in_degree[label] for label in chunks]),
            "out": quantiles([out_degree[label] for label in chunks]),
        },
        "most_cited_units": [{"unit": _name(u), "citing_labels": len(c)} for u, c in top[:TOP_CITED]],
        "components": {
            "count": len(sizes),
            "sizes": sizes,
            "isolated_labels": len(chunks) - len(touched),
        },
        "mixed": {
            "labels_with_spans": len(mixed_labels),
            "spans": mixed_spans,
            "edges": sum(e["mixed"] for e in edges),
        },
        "editorial": {"labels": sorted(pure), "spans": editorial},
        "unresolved": unresolved,
        "dangling": dangling,
        "relative": relative,
        "edge_list": edges,
    }


def _part(label: str) -> int | None:
    m = _PART_OF.match(label)
    return int(m.group(1)) if m else None


def _write(result: Mapping[str, Any], out_path: Path) -> dict[str, Any]:
    text = json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text, encoding="utf-8", newline="\n")
    loaded: dict[str, Any] = json.loads(text)
    return loaded


def run(manifests: Sequence[Path], marks: Path, expected: Mapping[Path, str], out_path: Path) -> dict[str, Any]:
    """Read each input once, refuse (IntegrityError, nothing written) on any missing or different sha256, then
    analyse and write. Raises, also before writing, ValueError for a label in two manifests or a marked label absent from the
    manifests, and TypeError for a chunk that is not text."""
    raw: dict[Path, bytes] = {}
    digests: dict[str, str] = {}
    for path in [*manifests, marks]:
        if path not in expected:
            raise IntegrityError(f"no pinned digest for {path.name}")
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != expected[path]:
            raise IntegrityError(f"{path.name}: sha256 {digest} != pinned {expected[path]}")
        raw[path] = data
        digests[path.name] = digest
    chunks: dict[str, str] = {}
    for path in manifests:
        for label, text in json.loads(raw[path].decode("utf-8")).items():
            if label in chunks:
                raise ValueError(f"label {label} is in two manifests")
            if not isinstance(text, str):
                raise TypeError(f"label {label}: chunk is not text")
            chunks[label] = text
    marked = json.loads(raw[marks].decode("utf-8"))["marked"]
    pure = [label for label, info in marked.items() if info.get("pure") is True]
    mixed = [label for label, info in marked.items() if info.get("pure") is False]
    body = analyse(chunks, pure, mixed)
    return _write({"kind": "exploration", "statement": STATEMENT, "digests": digests, **body}, out_path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Extract and describe the Ethics' internal citation graph.")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    try:
        result = run(MANIFESTS, MARKS, EXPECTED, args.out)
    except IntegrityError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    spans = result["spans"]
    print(
        f"spans={spans['found']} resolved={spans['resolved']} unresolved={spans['unresolved']} "
        f"edges={result['edges']['total']} share_touched={result['labels']['share_touched']:.4f}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
