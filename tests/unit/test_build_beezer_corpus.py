"""Beezer corpus builder: spans, formulas apart, lossless, macro words, citations.

T1 and T2 pin the committed snapshot and macro table. The rest specify
tools/experiments/tooling/build_beezer_corpus.py on synthetic trees and on the
real snapshot, whose oracle here shares no code with the builder.
"""
import html
import json
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLING = REPO_ROOT / "tools" / "experiments" / "tooling"
DATA = REPO_ROOT / "data" / "math"
SRC = DATA / "source" / "src"
MACROS = DATA / "macro_words.json"
ARTIFACTS = (
    "beezer_manifest.json",
    "beezer_marked.json",
    "beezer_formulas.json",
    "beezer_citations.json",
)
MARKER = re.compile(r"⟦F(\d+)⟧")
ORACLE = re.compile(
    r'<xi:include href="\./([^"]+)"'
    r'|<definition acro="([^"]+)"[^>]*>(.*?)</definition>'
    r'|<theorem acro="([^"]+)"[^>]*>(.*?</statement>)',
    re.DOTALL,
)


@pytest.fixture(scope="module")
def bc():
    sys.path.insert(0, str(TOOLING))
    import build_beezer_corpus

    return build_beezer_corpus


@pytest.fixture(scope="module")
def real(bc):
    return bc.build_corpus(SRC, json.loads(MACROS.read_text(encoding="utf-8")))


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def _book(src, includes):
    body = "".join(f'<xi:include href="./{name}" />\n' for name in includes)
    _write(
        src / "fcla.xml",
        f'<book xmlns:xi="http://www.w3.org/2001/XInclude">\n{body}</book>\n',
    )


def _one(tmp_path, body):
    src = tmp_path / "src"
    _book(src, ["section-S.xml"])
    _write(src / "section-S.xml", f"<section>\n{body}\n</section>\n")
    return src


def _definition(acro, inner):
    return (
        f'<definition acro="{acro}" index="i"><title>T</title>'
        f"<p>{inner}</p></definition>"
    )


def _oracle(name="fcla.xml"):
    text = (SRC / name).read_bytes().decode("utf-8")
    for m in ORACLE.finditer(text):
        if m[1]:
            yield from _oracle(m[1])
        elif m[2]:
            yield f"MATH_BEEZER_DEF_{m[2]}", m[3]
        else:
            yield f"MATH_BEEZER_THM_{m[4]}", m[5]


def _rebuild(marked, formulas):
    return MARKER.sub(lambda m: formulas[int(m[1]) - 1], marked)


def test_snapshot_structure_guard():
    files = sorted(SRC.glob("*.xml"))
    raw = [f.read_bytes() for f in files]
    text = "".join(b.decode("utf-8") for b in raw)
    defs = re.findall(r'<definition acro="([^"]*)"', text)
    thms = re.findall(r'<theorem acro="([^"]*)"', text)
    assert len(files) == 53
    assert (len(defs), len(thms)) == (114, 228)
    assert len(set(defs)) == 114 and len(set(thms)) == 228
    assert set(defs) & set(thms) == {"CCM", "DIM", "DM", "ME", "SS"}
    assert not any(b"\r" in b for b in raw)
    assert "⟦" not in text and "⟧" not in text
    fcla = (SRC / "fcla.xml").read_text(encoding="utf-8")
    first = re.findall(r'<xi:include href="\./([^"]+)\.xml"', fcla)[:4]
    assert first == ["bookinfo", "macros", "chapter-SLE", "chapter-V"]


def test_macro_table_guard():
    table = json.loads(MACROS.read_text(encoding="utf-8"))
    nulls = [k for k, v in table.items() if v is None]
    assert len(table) == 96 and len(nulls) == 27
    assert all(v is None or isinstance(v, str) for v in table.values())
    assert all(table[k] is None for k in ("vect", "complex", "real", "lt"))
    assert table["csp"] == "column space" and table["detbars"] == "determinant"


def test_spans_labels_and_reading_order(bc, tmp_path):
    src = tmp_path / "src"
    _book(src, ["chapter-B.xml", "chapter-A.xml"])
    _write(
        src / "chapter-B.xml",
        '<chapter>\n<xi:include href="./section-Z.xml" />\n'
        '<xi:include href="./section-Y.xml" />\n</chapter>\n',
    )
    _write(
        src / "chapter-A.xml",
        '<chapter>\n<xi:include href="./section-X.xml" />\n</chapter>\n',
    )
    _write(
        src / "section-Z.xml",
        '<section>\n<p>Prose out.</p>\n'
        '<definition acro="ZD" index="z"><title>Zed</title><p>Zed text.</p></definition>\n'
        '<example acro="EX"><title>Ex</title><p>Example out.</p></example>\n'
        '<theorem acro="ZT" index="z"><title>Zed theorem</title>'
        '<statement><p>Zed statement.</p></statement>'
        '<proof><p>Proof out.</p></proof></theorem>\n</section>\n',
    )
    _write(
        src / "section-Y.xml",
        '<section>\n<theorem acro="ZD" index="y"><title>Shared</title>'
        '<statement><p>Shared statement.</p></statement>'
        '<proof><p>Shared proof.</p></proof></theorem>\n</section>\n',
    )
    _write(
        src / "section-X.xml",
        '<section>\n<definition acro="XD" index="x"><title>Ex def</title>'
        '<p>X text.</p><notation><usage>Notation out</usage></notation></definition>\n'
        '<exercise acro="XE"><problem>Exercise out.</problem></exercise>\n</section>\n',
    )
    out = bc.build_corpus(src, {})
    assert list(out["manifest"]) == [
        "MATH_BEEZER_DEF_ZD",
        "MATH_BEEZER_THM_ZT",
        "MATH_BEEZER_THM_ZD",
        "MATH_BEEZER_DEF_XD",
    ]
    assert list(out["marked"]) == list(out["formulas"]) == list(out["manifest"])
    stored = " ".join(out["manifest"].values()) + " ".join(out["marked"].values())
    for outside in ("Prose out", "Example out", "Proof out", "Shared proof", "Exercise out"):
        assert outside not in stored
    assert "Notation out" not in " ".join(out["manifest"].values())
    assert out["manifest"]["MATH_BEEZER_DEF_ZD"] == "Zed. Zed text."
    assert out["manifest"]["MATH_BEEZER_THM_ZD"] == "Shared. Shared statement."
    assert out["marked"]["MATH_BEEZER_THM_ZT"].endswith("</statement>")


def test_statement_outside_include_expansion_is_an_error(bc, tmp_path):
    src = _one(tmp_path, _definition("IN", "x"))
    _write(src / "orphan.xml", _definition("OUT", "y"))
    with pytest.raises(ValueError, match="orphan.xml"):
        bc.build_corpus(src, {})


def test_x1_file_included_twice_is_an_error(bc, tmp_path):
    src = _one(tmp_path, _definition("IN", "x"))
    _book(src, ["section-S.xml", "section-S.xml"])
    with pytest.raises(ValueError, match="section-S.xml"):
        bc.build_corpus(src, {})


ALL_TAGS_DEFINITION = (
    '<definition acro="TD" index="t">\n'
    "<title>Title &amp; More</title>\n"
    '<indexlocation index="t" />\n'
    '<subject key="a.b" />\n'
    "<p>First <define>term</define> with <em>emphasis</em> and <q>quoted</q> here<ie />, "
    'then<mdash />dash and<ellipsis />dots, see <acroref type="section" acro="S" /> now.</p>\n'
    "<p>Second &lt; &gt; &quot;a&quot; &apos;b&apos; paragraph.</p>\n"
    "<propertylist>\n"
    '<property acro="P1" index="p"><title>Prop One</title><content>Content one.</content></property>\n'
    '<property acro="P2" index="p"><title>Prop Two</title><content>Content two.</content></property>\n'
    "</propertylist>\n"
    "<notation><title>Hidden</title><usage>$H$</usage></notation>\n"
    "</definition>"
)
THEOREM = (
    '<theorem acro="TT" index="t">\n<title>Theorem Title</title>\n'
    "<statement>\n<p>Stated.</p>\n</statement>\n\n"
    "<proof>\n<p>Proved.</p>\n</proof>\n</theorem>"
)


def test_model_text_rule(bc, tmp_path):
    out = bc.build_corpus(_one(tmp_path, ALL_TAGS_DEFINITION + "\n" + THEOREM), {})
    assert out["manifest"]["MATH_BEEZER_DEF_TD"] == (
        "Title & More. First term with emphasis and quoted here , then dash and dots, "
        "see now. Second < > \"a\" 'b' paragraph. "
        "Prop One. Content one. Prop Two. Content two."
    )
    assert out["manifest"]["MATH_BEEZER_THM_TT"] == "Theorem Title. Stated."


FORMULA_DEFINITION = (
    '<definition acro="FD" index="f">\n'
    "<title>Formulas</title>\n"
    "<p>Inline $a+b$ then $<![CDATA[m<t]]>$ done.</p>\n"
    "<equation>\n<![CDATA[x<y]]>\n<![CDATA[z]]>\n</equation>\n"
    "<p>Then <alignmath>\n<![CDATA[a&=b]]>\n<![CDATA[c&=d]]>\n</alignmath></p>\n"
    "</definition>"
)


def test_formulas_apart_and_lossless(bc, tmp_path):
    plain = _definition("PD", "No formula here.")
    out = bc.build_corpus(_one(tmp_path, FORMULA_DEFINITION + "\n" + plain), {})
    formulas = out["formulas"]["MATH_BEEZER_DEF_FD"]
    assert formulas == [
        "$a+b$",
        "$<![CDATA[m<t]]>$",
        "<equation>\n<![CDATA[x<y]]>\n<![CDATA[z]]>\n</equation>",
        "<alignmath>\n<![CDATA[a&=b]]>\n<![CDATA[c&=d]]>\n</alignmath>",
    ]
    marked = out["marked"]["MATH_BEEZER_DEF_FD"]
    assert "Inline ⟦F1⟧ then ⟦F2⟧ done." in marked
    assert "\n⟦F3⟧\n" in marked
    assert "Then ⟦F4⟧</p>" in marked
    raw = FORMULA_DEFINITION.split(">", 1)[1].rsplit("</definition>", 1)[0]
    assert MARKER.sub(lambda m: formulas[int(m[1]) - 1], marked) == raw
    assert out["manifest"]["MATH_BEEZER_DEF_FD"] == "Formulas. Inline then done. Then"
    assert out["formulas"]["MATH_BEEZER_DEF_PD"] == []


SMALL_TABLE = {"alpha": "alpha word", "beta": "beta", "pair": "two words", "nul": None}


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        (r"A $\alpha\alpha\alpha$ B", "T. A alpha word B"),
        (r"A $\beta+\alpha+\beta$ B", "T. A beta alpha word B"),
        (r"A $\nul x$ B", "T. A B"),
        (r"A $\left(x\right)\ldots$ B", "T. A B"),
        (r"A $x+1$ B", "T. A B"),
        (r"A <equation><![CDATA[\pair{x}+\alpha]]></equation> B", "T. A two words alpha word B"),
        (r"A $\alpha$ and $\alpha$ B", "T. A alpha word and alpha word B"),
    ],
)
def test_macro_words(bc, tmp_path, body, expected):
    out = bc.build_corpus(_one(tmp_path, _definition("M", body)), SMALL_TABLE)
    assert out["manifest"]["MATH_BEEZER_DEF_M"] == expected


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Dimension of $x$", "Dimension of. Body."),
        (r"$\pair{x}$ tail", "two words tail. Body."),
        (r"Lead $\alpha$ tail", "Lead alpha word tail. Body."),
        ("\n  Spaced \n", "Spaced. Body."),
    ],
)
def test_title_separator_is_one_period_and_one_space(bc, tmp_path, title, expected):
    body = (
        f'<definition acro="TS" index="i"><title>{title}</title><p>Body.</p></definition>'
    )
    out = bc.build_corpus(_one(tmp_path, body), SMALL_TABLE)
    assert out["manifest"]["MATH_BEEZER_DEF_TS"] == expected


def test_property_titles_get_the_separator(bc, tmp_path):
    body = (
        '<definition acro="PL" index="i"><title>Chunk</title><p>Intro.</p><propertylist>'
        '<property acro="P1" index="p"><title>First</title><content>One.</content></property>'
        '<property acro="P2" index="p"><title>Second $x$</title><content>Two.</content></property>'
        "</propertylist></definition>"
    )
    out = bc.build_corpus(_one(tmp_path, body), {})
    assert out["manifest"]["MATH_BEEZER_DEF_PL"] == "Chunk. Intro. First. One. Second. Two."


def _citation_body():
    dropped = "".join(
        f'<acroref type="{t}" acro="X" />'
        for t in ("section", "chapter", "example", "archetype", "property", "exercise", "technique", "sage")
    )
    return "\n".join(
        [
            (
                '<definition acro="CA" index="a"><title>A</title><p>Uses '
                '<acroref type="theorem" acro="CB" /> and <acroref type="section" acro="S" /> '
                'and itself <acroref type="definition" acro="CA" />.</p></definition>'
            ),
            (
                '<theorem acro="CB" index="b"><title>B</title><statement><p>Plain.</p></statement>'
                '<proof><p>By <acroref type="definition" acro="CA" /> and '
                f'<acroref type="theorem" acro="CB" />, {dropped} again '
                '<acroref type="definition" acro="CA" />.</p></proof></theorem>'
            ),
            (
                '<definition acro="CC" index="c"><title>C</title><p>Uses '
                '<acroref type="theorem" acro="CA" /> <acroref type="definition" acro="CA" /> '
                '<acroref type="theorem" acro="CB" /> <acroref type="theorem" acro="CA" />.</p></definition>'
            ),
            (
                '<theorem acro="CA" index="a"><title>A thm</title><statement><p>Uses '
                '<acroref type="definition" acro="CA" />.</p></statement>'
                "<proof><p>Nothing.</p></proof></theorem>"
            ),
        ]
    )


def test_citations(bc, tmp_path):
    out = bc.build_corpus(_one(tmp_path, _citation_body()), {})
    assert out["citations"] == [
        ["MATH_BEEZER_DEF_CA", "MATH_BEEZER_THM_CB"],
        ["MATH_BEEZER_THM_CB", "MATH_BEEZER_DEF_CA"],
        ["MATH_BEEZER_DEF_CC", "MATH_BEEZER_THM_CA"],
        ["MATH_BEEZER_DEF_CC", "MATH_BEEZER_DEF_CA"],
        ["MATH_BEEZER_DEF_CC", "MATH_BEEZER_THM_CB"],
        ["MATH_BEEZER_THM_CA", "MATH_BEEZER_DEF_CA"],
    ]


DECLARED_DROPPED = (
    "archetype", "chapter", "diagram", "example", "exercise", "property",
    "sage", "section", "solution", "subsection", "technique",
)


def test_dropped_citation_types_are_the_declared_eleven(bc):
    assert bc.DROPPED_CITATION_TYPES == frozenset(DECLARED_DROPPED)


@pytest.mark.parametrize("kind", DECLARED_DROPPED)
def test_declared_dropped_type_gives_no_edge(bc, tmp_path, kind):
    body = _definition("D1", f'<acroref type="{kind}" acro="D2" />') + _definition("D2", "x")
    assert bc.build_corpus(_one(tmp_path, body), {})["citations"] == []


def test_undeclared_citation_type_is_an_error(bc, tmp_path):
    body = _definition("U", '<acroref type="bogus" acro="X" />')
    with pytest.raises(ValueError, match="bogus") as caught:
        bc.build_corpus(_one(tmp_path, body), {})
    assert "MATH_BEEZER_DEF_U" in str(caught.value)


@pytest.mark.parametrize("reference", ['<acroref acro="X" />', '<acroref type="section" />'])
def test_acroref_without_type_or_acro_is_an_error(bc, tmp_path, reference):
    with pytest.raises(ValueError, match="without type or acro"):
        bc.build_corpus(_one(tmp_path, _definition("U", reference)), {})


def test_unresolvable_citation_is_an_error(bc, tmp_path):
    body = _definition("U", '<acroref type="theorem" acro="NOPE" />')
    with pytest.raises(ValueError, match="NOPE") as caught:
        bc.build_corpus(_one(tmp_path, body), {})
    assert "MATH_BEEZER_DEF_U" in str(caught.value)


def test_citation_resolves_by_type(bc, tmp_path):
    theorem_only = (
        '<theorem acro="TO" index="t"><title>T</title>'
        "<statement><p>S.</p></statement></theorem>"
    )
    body = theorem_only + _definition("U", '<acroref type="definition" acro="TO" />')
    with pytest.raises(ValueError, match="TO") as caught:
        bc.build_corpus(_one(tmp_path, body), {})
    assert "MATH_BEEZER_DEF_U" in str(caught.value)


@pytest.mark.parametrize(
    ("inner", "keyword"),
    [
        ("x <blink>y</blink>", "blink"),
        ("a&nbsp;b", "nbsp"),
        ("cost $5 here", "dollar"),
        ("x <![CDATA[y]]>", "CDATA"),
        ("x ⟦ y", "marker"),
    ],
)
def test_failure_is_loud_and_names_the_label(bc, tmp_path, inner, keyword):
    src = _one(tmp_path, _definition("BAD", inner))
    with pytest.raises(ValueError, match=keyword) as caught:
        bc.build_corpus(src, {})
    assert "MATH_BEEZER_DEF_BAD" in str(caught.value)


def test_duplicate_label_is_an_error(bc, tmp_path):
    body = _definition("BAD", "one") + "\n" + _definition("BAD", "two")
    with pytest.raises(ValueError, match="duplicate") as caught:
        bc.build_corpus(_one(tmp_path, body), {})
    assert "MATH_BEEZER_DEF_BAD" in str(caught.value)


def test_real_labels_order_and_counts(real):
    labels = [label for label, _ in _oracle()]
    assert list(real["manifest"]) == labels
    assert list(real["marked"]) == list(real["formulas"]) == labels
    assert len(labels) == 342
    assert sum(label.startswith("MATH_BEEZER_DEF_") for label in labels) == 114
    assert sum(label.startswith("MATH_BEEZER_THM_") for label in labels) == 228


def test_real_lossless_against_independent_spans(real):
    for label, raw in _oracle():
        formulas = real["formulas"][label]
        marked = real["marked"][label]
        assert _rebuild(marked, formulas) == raw, label
        numbers = [int(n) for n in MARKER.findall(marked)]
        assert numbers == list(range(1, len(formulas) + 1)), label


def test_real_model_text_is_clean(real):
    for label, text in real["manifest"].items():
        assert text, label
        assert not set(text) & set("<>&⟦⟧"), label
        assert " ".join(text.split()) == text, label


def test_snapshot_acroref_types_are_the_declared_thirteen(bc):
    text = "".join(f.read_text(encoding="utf-8") for f in sorted(SRC.glob("*.xml")))
    types = set(re.findall(r'<acroref\b[^>]*?\btype="([^"]*)"', text))
    assert types == {"definition", "theorem"} | bc.DROPPED_CITATION_TYPES
    assert len(types) == 13


def _titles(raw):
    raw = re.sub(r"<notation\b.*?</notation>", "", raw, flags=re.DOTALL)
    return re.findall(r"<title>(.*?)</title>", raw, re.DOTALL)


def test_snapshot_titles_do_not_end_in_punctuation():
    for label, raw in _oracle():
        titles = _titles(raw)
        assert titles, label
        for title in titles:
            assert not title.rstrip().endswith((".", "?", "!", ":", ";")), (label, title)


def test_real_chunk_title_is_followed_by_period_and_space(real):
    checked = 0
    for label, raw in _oracle():
        title = _titles(raw)[0]
        if "$" in title or "<equation" in title or "<alignmath" in title:
            continue
        words = " ".join(html.unescape(re.sub(r"<[^>]*>", "", title)).split())
        text = real["manifest"][label]
        assert text.startswith(words + ". "), label
        assert not text[len(words) + 2:].startswith((" ", ".")), label
        assert "  " not in text, label
        checked += 1
    assert checked > 0


def test_real_citation_endpoints_are_labels(real):
    labels = set(real["manifest"])
    assert real["citations"]
    for source, target in real["citations"]:
        assert source in labels and target in labels and source != target


def test_build_corpus_is_deterministic_and_writes_nothing(bc, tmp_path):
    src = _one(tmp_path, _definition("D1", r"x $\alpha$ y") + "\n" + THEOREM)
    before = sorted(str(p) for p in tmp_path.rglob("*"))
    first = bc.build_corpus(src, SMALL_TABLE)
    assert bc.build_corpus(src, SMALL_TABLE) == first
    assert sorted(str(p) for p in tmp_path.rglob("*")) == before


def test_main_writes_four_files_byte_identical_across_runs(bc, tmp_path):
    src = _one(tmp_path, _definition("D1", r"x $\alpha$ y") + "\n" + THEOREM)
    macros = tmp_path / "macros.json"
    _write(macros, json.dumps(SMALL_TABLE))
    stamps = {p: p.stat().st_mtime_ns for p in DATA.rglob("*") if p.is_file()}
    outs = [tmp_path / "out1", tmp_path / "out2"]
    for out in outs:
        args = ["--source", str(src), "--macros", str(macros), "--out", str(out)]
        assert bc.main(args) == 0
    for out in outs:
        assert sorted(p.name for p in out.iterdir()) == sorted(ARTIFACTS)
    for name in ARTIFACTS:
        first = (outs[0] / name).read_bytes()
        assert first == (outs[1] / name).read_bytes()
        assert first.endswith(b"\n")
    labels = ["MATH_BEEZER_DEF_D1", "MATH_BEEZER_THM_TT"]
    for name in ARTIFACTS[:3]:
        assert list(json.loads((outs[0] / name).read_text(encoding="utf-8"))) == labels
    assert json.loads((outs[0] / ARTIFACTS[0]).read_text(encoding="utf-8")) == {
        "MATH_BEEZER_DEF_D1": "T. x alpha word y",
        "MATH_BEEZER_THM_TT": "Theorem Title. Stated.",
    }
    assert stamps == {p: p.stat().st_mtime_ns for p in DATA.rglob("*") if p.is_file()}
