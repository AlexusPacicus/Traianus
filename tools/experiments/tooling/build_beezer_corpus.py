"""Derive the Beezer corpus of pilot 1 from the pinned FCLA snapshot, offline.

One definition or theorem statement is one chunk. Every formula is replaced by
a marker and kept in a table, so the raw statement is rebuilt byte for byte;
the model text carries the words of each formula's macros instead
(data/math/PROVENANCE.md, "Derivation rules"). The source is read as raw text,
not parsed: inline math holds a bare "<" inside CDATA.

Writes beezer_manifest.json, beezer_marked.json, beezer_formulas.json and
beezer_citations.json. Standard library only; computes no vector.
"""
import argparse
import json
import re
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any, NamedTuple

REPO_ROOT = Path(__file__).resolve().parents[3]
MARK_OPEN, MARK_CLOSE = "⟦", "⟧"
ARTIFACTS = {
    "manifest": "beezer_manifest.json",
    "marked": "beezer_marked.json",
    "formulas": "beezer_formulas.json",
    "citations": "beezer_citations.json",
}
KINDS = {"definition": "DEF", "theorem": "THM"}
ENTITIES = {"amp": "&", "lt": "<", "gt": ">", "quot": '"', "apos": "'"}

INCLUDE = re.compile(r'<xi:include\s+href="([^"]+)"\s*/>')
STATEMENT_OPEN = re.compile(r"<(definition|theorem)\b([^>]*)>")
ACRO = re.compile(r'\bacro="([^"]+)"')
ACROREF = re.compile(r"<acroref\b([^>]*)>")
ATTRIBUTE = re.compile(r'(\w+)="([^"]*)"')
FORMULA = re.compile(
    r"<equation>.*?</equation>|<alignmath>.*?</alignmath>|\$.*?\$", re.DOTALL
)
MARKER = re.compile(f"{MARK_OPEN}F(\\d+){MARK_CLOSE}")
MACRO = re.compile(r"\\([A-Za-z]+)")
DROPPED = re.compile(
    r"<notation\b[^>]*>.*?</notation>|<(?:indexlocation|subject)\b[^>]*/>", re.DOTALL
)
BLOCK_TAG = re.compile(
    r"</?(?:p|li|ol|title|statement|propertylist|property|content)\b[^>]*>"
    r"|<(?:acroref|ie|mdash|ellipsis)\b[^>]*/>"
)
INLINE_TAG = re.compile(r"</?(?:define|em|q)\b[^>]*>")
UNKNOWN_ENTITY = re.compile(r"&(?!(?:amp|lt|gt|quot|apos);)[^;\s<]*;?")
ENTITY = re.compile(r"&(amp|lt|gt|quot|apos);")


class _Statement(NamedTuple):
    label: str
    raw: str
    element: str


def _read(path: Path) -> str:
    return path.read_bytes().decode("utf-8")


def _segments(path: Path, seen: set[Path]) -> Iterator[tuple[str, str]]:
    """Text of `path` with every xi:include expanded in place, depth first."""
    resolved = path.resolve()
    if resolved in seen:
        raise ValueError(f"{path.name}: included twice")
    seen.add(resolved)
    text = _read(path)
    if text.count("<xi:include") != len(INCLUDE.findall(text)):
        raise ValueError(f"{path.name}: xi:include not of the form href=\"...\"")
    pos = 0
    for match in INCLUDE.finditer(text):
        yield path.name, text[pos:match.start()]
        yield from _segments(path.parent / match[1], seen)
        pos = match.end()
    yield path.name, text[pos:]


def _statements(name: str, text: str) -> Iterator[_Statement]:
    pos = 0
    while (opening := STATEMENT_OPEN.search(text, pos)) is not None:
        kind, attributes = opening.groups()
        acro = ACRO.search(attributes)
        if acro is None:
            raise ValueError(f"{name}: <{kind}> without acro")
        label = f"MATH_BEEZER_{KINDS[kind]}_{acro[1]}"
        closing = f"</{kind}>"
        end = text.find(closing, opening.end())
        if end < 0:
            raise ValueError(f"{label}: no {closing} in {name}")
        raw_end = end
        if kind == "theorem":
            statement = text.find("</statement>", opening.end(), end)
            if statement < 0:
                raise ValueError(f"{label}: no </statement> in {name}")
            raw_end = statement + len("</statement>")
        pos = end + len(closing)
        yield _Statement(label, text[opening.end():raw_end], text[opening.start():pos])


def _mark(label: str, raw: str) -> tuple[str, list[str]]:
    if MARK_OPEN in raw or MARK_CLOSE in raw:
        raise ValueError(f"{label}: marker character in source")
    formulas: list[str] = []

    def replace(match: re.Match[str]) -> str:
        formulas.append(match[0])
        return f"{MARK_OPEN}F{len(formulas)}{MARK_CLOSE}"

    marked = FORMULA.sub(replace, raw)
    if "$" in marked:
        raise ValueError(f"{label}: odd number of dollar signs")
    if MARKER.sub(lambda m: formulas[int(m[1]) - 1], marked) != raw:
        raise ValueError(f"{label}: marked text and formulas do not rebuild the source")
    return marked, formulas


def _words(formula: str, macro_words: dict[str, str | None]) -> str:
    body = formula.replace("<![CDATA[", "").replace("]]>", "")
    names = dict.fromkeys(MACRO.findall(body))
    return " ".join(words for name in names if (words := macro_words.get(name)))


def _model_text(
    label: str, marked: str, formulas: list[str], macro_words: dict[str, str | None]
) -> str:
    text = DROPPED.sub("", marked)
    if "<![CDATA[" in text:
        raise ValueError(f"{label}: CDATA section outside a formula")
    text = INLINE_TAG.sub("", BLOCK_TAG.sub(" ", text))
    tag = re.search(r"<[^\s>]*", text)
    if tag is not None:
        raise ValueError(f"{label}: unknown tag {tag[0]}")
    entity = UNKNOWN_ENTITY.search(text)
    if entity is not None:
        raise ValueError(f"{label}: unknown entity {entity[0]}")
    text = MARKER.sub(lambda m: _words(formulas[int(m[1]) - 1], macro_words), text)
    text = ENTITY.sub(lambda m: ENTITIES[m[1]], text)
    return " ".join(text.split())


def _citations(statements: dict[str, _Statement]) -> list[list[str]]:
    edges: dict[tuple[str, str], None] = {}
    for label, statement in statements.items():
        for attributes in ACROREF.findall(statement.element):
            fields = dict(ATTRIBUTE.findall(attributes))
            if "type" not in fields or "acro" not in fields:
                raise ValueError(f"{label}: acroref without type or acro")
            kind = KINDS.get(fields["type"])
            if kind is None:
                continue
            target = f"MATH_BEEZER_{kind}_{fields['acro']}"
            if target not in statements:
                raise ValueError(
                    f"{label}: unresolvable citation {fields['type']} {fields['acro']}"
                )
            if target != label:
                edges.setdefault((label, target))
    return [list(edge) for edge in edges]


def build_corpus(
    source_dir: Path, macro_words: dict[str, str | None]
) -> dict[str, Any]:
    seen: set[Path] = set()
    statements: dict[str, _Statement] = {}
    for name, text in _segments(source_dir / "fcla.xml", seen):
        for statement in _statements(name, text):
            if statement.label in statements:
                raise ValueError(f"{statement.label}: duplicate label in {name}")
            statements[statement.label] = statement
    for path in sorted(source_dir.glob("*.xml")):
        if path.resolve() not in seen and STATEMENT_OPEN.search(_read(path)):
            raise ValueError(f"{path.name}: statement outside the include expansion")

    manifest: dict[str, str] = {}
    marked: dict[str, str] = {}
    formulas: dict[str, list[str]] = {}
    for label, statement in statements.items():
        marked[label], formulas[label] = _mark(label, statement.raw)
        manifest[label] = _model_text(label, marked[label], formulas[label], macro_words)
    return {
        "manifest": manifest,
        "marked": marked,
        "formulas": formulas,
        "citations": _citations(statements),
    }


def main(argv: list[str] | None = None) -> int:
    data = REPO_ROOT / "data" / "math"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=data / "source" / "src")
    parser.add_argument("--macros", type=Path, default=data / "macro_words.json")
    parser.add_argument("--out", type=Path, default=data)
    args = parser.parse_args(argv)

    macro_words = json.loads(args.macros.read_text(encoding="utf-8"))
    corpus = build_corpus(args.source, macro_words)
    args.out.mkdir(parents=True, exist_ok=True)
    for key, name in ARTIFACTS.items():
        text = json.dumps(corpus[key], indent=2, ensure_ascii=False) + "\n"
        (args.out / name).write_bytes(text.encode("utf-8"))

    labels = list(corpus["manifest"])
    definitions = sum(label.startswith("MATH_BEEZER_DEF_") for label in labels)
    formula_count = sum(len(items) for items in corpus["formulas"].values())
    print(
        f"[+] chunks: {len(labels)} (DEF {definitions}, THM {len(labels) - definitions})"
        f" | formulas: {formula_count} | citations: {len(corpus['citations'])}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
