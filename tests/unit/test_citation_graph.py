"""Unit tests of tools/experiments/citation_graph.py.

Specification: the delegation contract citation-graph (B1-B8). Synthetic inputs only: the real frozen manifests are
never analysed here and nothing is written under data/.
"""

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from tools.experiments import citation_graph as cg
from tools.experiments.citation_graph import Unit

DEMO1 = "PART1_GOD_P20_DEMO_01"
DEMO3 = "PART3_AFFECTS_P20_DEMO_01"
DEMO4 = "PART4_BONDAGE_P37_DEMO_01"


def _units(text: str, citing: str = DEMO3, last_axiom: tuple[int, int] | None = None) -> list[Unit]:
    parse = cg.parse_span(text, citing, last_axiom)
    assert parse.error is None, parse.error
    return list(parse.units)


# T1: absolute forms ---------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "citing", "expected"),
    [
        ("III. xi. note", DEMO3, [Unit(3, "ESC", 11, 1)]),
        ("II. xi. Coroll.", DEMO3, [Unit(2, "COR", 11, 1)]),
        ("II. xvi. Coroll. ii.", DEMO3, [Unit(2, "COR", 16, 2)]),
        ("III. Def. ii.", DEMO3, [Unit(3, "DEF", 2)]),
        ("I. Ax. vi.", DEMO3, [Unit(1, "AX", 6)]),
        ("III. Post. i.", DEMO4, [Unit(3, "POST", 1)]),
        ("Part i., Prop. x.", DEMO3, [Unit(1, "PROP", 10)]),
        ("by Prop. xi.", DEMO4, [Unit(4, "PROP", 11)]),
        ("Def. of the Emotions, i.", DEMO4, [Unit(3, "DEFEMO", 1)]),
        ("II. Lemma iii.", DEMO3, [Unit(2, "LEMMA", 3)]),
        ("Ax. iv.", DEMO1, [Unit(1, "AX", 4)]),
        ("by Def. vi.", DEMO4, [Unit(4, "DEF", 6)]),
        ("II. xl. note. ii.", DEMO3, [Unit(2, "ESC", 40, 2)]),
        ("II., Def. i.", DEMO3, [Unit(2, "DEF", 1)]),
        ("what is the same thing, by Prop. xvi., Part i.", DEMO3, [Unit(1, "PROP", 16)]),
        ("II. xi. Schol.", DEMO3, [Unit(2, "ESC", 11, 1)]),
    ],
)
def test_t1_absolute_forms_resolve_to_exactly_the_expected_unit(text: str, citing: str, expected: list[Unit]) -> None:
    assert _units(text, citing) == expected


@pytest.mark.parametrize(
    ("text", "mode"),
    [
        ("by Prop. xi.", "explicit"),
        ("from II. xi. Coroll.", "explicit"),
        ("what is the same thing, by Prop. xvi.", "explicit"),
        ("III. xi. note", "explicit"),
        ("see Ax. iv.", "see"),
        ("cf. III. xi. note", "cf"),
    ],
)
def test_t1_prefix_is_kept_as_the_mode(text: str, mode: str) -> None:
    assert cg.parse_span(text, DEMO3).mode == mode


# T2: lists and additions ----------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "citing", "expected"),
    [
        ("II. xi., xiii.", DEMO3, [Unit(2, "PROP", 11), Unit(2, "PROP", 13)]),
        ("II. xix. and xxiii.", DEMO3, [Unit(2, "PROP", 19), Unit(2, "PROP", 23)]),
        ("IV. xxvi. xxvii.", DEMO3, [Unit(4, "PROP", 26), Unit(4, "PROP", 27)]),
        ("Deff. iii. and vi.", DEMO1, [Unit(1, "DEF", 3), Unit(1, "DEF", 6)]),
        ("Def. of the Emotions, vi. vii.", DEMO4, [Unit(3, "DEFEMO", 6), Unit(3, "DEFEMO", 7)]),
        ("III. xi. and note", DEMO3, [Unit(3, "PROP", 11), Unit(3, "ESC", 11, 1)]),
        ("II. xvii. and Coroll.", DEMO3, [Unit(2, "PROP", 17), Unit(2, "COR", 17, 1)]),
        ("see Axiom. i. and Prop. vii.", DEMO1, [Unit(1, "AX", 1), Unit(1, "PROP", 7)]),
        ("III. xxx. note, and III. xxvii. note", DEMO3, [Unit(3, "ESC", 30, 1), Unit(3, "ESC", 27, 1)]),
    ],
)
def test_t2_lists_and_additions_yield_every_unit_inheriting_part_and_kind(
    text: str, citing: str, expected: list[Unit]
) -> None:
    assert _units(text, citing) == expected


def test_t2_a_comma_before_a_subunit_replaces_the_proposition_and_only_and_adds_it() -> None:
    assert _units("by Prop. xiv., Coroll. i.", DEMO3) == [Unit(3, "COR", 14, 1)]


def test_t2_a_bare_subunit_followed_by_a_separated_number_starts_a_new_proposition() -> None:
    assert _units("from II. Prop. xvii. Coroll., and xviii.", DEMO3) == [Unit(2, "COR", 17, 1), Unit(2, "PROP", 18)]


def test_t2_numbers_after_a_numbered_subunit_are_more_subunits() -> None:
    assert _units("cf. IV. xxxvii. Coroll. i. ii.", DEMO3) == [Unit(4, "COR", 37, 1), Unit(4, "COR", 37, 2)]


def test_t2_a_repeated_unit_in_one_span_is_kept_once() -> None:
    assert _units("II. xi., xi.", DEMO3) == [Unit(2, "PROP", 11)]


# T3: relative forms ---------------------------------------------------------------------------------------


@pytest.mark.parametrize("word", ["last", "foregoing", "preceding"])
def test_t3_the_last_prop_in_a_demo_is_the_previous_proposition_and_in_a_scholium_or_corollary_the_same(
    word: str,
) -> None:
    text = f"by the {word} Prop."
    assert _units(text, "PART1_GOD_P12_DEMO_01_C01") == [Unit(1, "PROP", 11)]
    assert _units(text, "PART1_GOD_P12_ESC_01_C02") == [Unit(1, "PROP", 12)]
    assert _units(text, "PART1_GOD_P12_COR_01") == [Unit(1, "PROP", 12)]


def test_t3_a_relative_span_records_its_form_and_resolution() -> None:
    parse = cg.parse_span("by the last Prop.", "PART2_MIND_P12_DEMO_01")
    assert parse.relative == (("last", Unit(2, "PROP", 11)),)


@pytest.mark.parametrize("citing", ["PART1_GOD_P01_DEMO_01", "PART1_GOD_P12_PROP", "PART1_GOD_AX_01", "not-a-label"])
def test_t3_a_relative_form_that_has_no_proposition_to_point_at_is_unresolved(citing: str) -> None:
    parse = cg.parse_span("by the last Prop.", citing)
    assert parse.error is not None
    assert parse.units == ()


def test_t3_the_same_axiom_is_the_last_axiom_cited_earlier() -> None:
    assert _units("by the same Axiom", DEMO1, last_axiom=(1, 4)) == [Unit(1, "AX", 4)]


def test_t3_the_same_axiom_with_no_earlier_axiom_is_unresolved() -> None:
    parse = cg.parse_span("by the same Axiom", DEMO1, None)
    assert parse.error is not None
    assert parse.units == ()


def test_t3_the_same_axiom_reads_only_earlier_spans_of_the_same_chunk() -> None:
    chunks = {
        "PART1_GOD_AX_04": "Axiom.",
        "PART1_GOD_P05_DEMO_01": "Shown (Ax. iv.) and (by the same Axiom).",
        "PART1_GOD_P06_DEMO_01": "Shown (by the same Axiom).",
    }
    result = cg.analyse(chunks, pure=(), mixed=())
    assert [(e["citing"], e["cited"]) for e in result["edge_list"]] == [
        ("PART1_GOD_P05_DEMO_01", "PART1_GOD_AX_04"),
        ("PART1_GOD_P05_DEMO_01", "PART1_GOD_AX_04"),
    ]
    assert [u["label"] for u in result["unresolved"]] == ["PART1_GOD_P06_DEMO_01"]


# T4: nothing is dropped silently --------------------------------------------------------------------------


def test_t4_a_span_the_grammar_cannot_read_is_unresolved_with_label_offset_and_text() -> None:
    text = "Shown (which see after Lemma iii. Prop. xiii., Part II.) here."
    chunks = {"PART2_MIND_P14_DEMO_01": text}
    result = cg.analyse(chunks, pure=(), mixed=())
    inner = "which see after Lemma iii. Prop. xiii., Part II."
    assert len(result["unresolved"]) == 1
    entry = result["unresolved"][0]
    assert (entry["label"], entry["offset"], entry["text"]) == ("PART2_MIND_P14_DEMO_01", text.index(inner), inner)
    assert entry["span"] == f"PART2_MIND_P14_DEMO_01@{text.index(inner)}"
    assert result["edge_list"] == []
    assert result["spans"]["unresolved"] == 1


def test_t4_a_citation_to_a_unit_absent_from_the_manifests_is_dangling_with_its_text() -> None:
    text = "Shown (I. ix.) here."
    result = cg.analyse({"PART1_GOD_P01_DEMO_01": text}, pure=(), mixed=())
    assert result["dangling"] == [
        {
            "label": "PART1_GOD_P01_DEMO_01",
            "offset": text.index("I. ix."),
            "span": f"PART1_GOD_P01_DEMO_01@{text.index('I. ix.')}",
            "text": "I. ix.",
            "unit": "1.PROP.9",
        }
    ]
    assert result["edge_list"] == []
    assert result["dangling_units"] == 1
    assert result["spans"]["with_dangling"] == 1
    assert result["spans"]["unresolved"] == 0


def test_t4_a_parenthesis_with_no_citation_token_is_not_a_span() -> None:
    assert cg.find_spans("A remark (see below) and (a remark that holds) and (in 1662).") == []


@pytest.mark.parametrize(
    "text",
    [
        "which by III. ix. note, come to the same thing",
        "by the general Def. of the Emotions",
        "cf. also III. xiii. note",
        "i. 25. Coroll.",
        "IV. xxxvii. notes. i. ii.",
        "Prop.",
        "Prop. Part i.",
        "Coroll. i.",
        "Ax. vi. of the third kind",
        "in Prop. xvi.",
    ],
)
def test_t4_forms_outside_the_grammar_are_unresolved_never_partly_read(text: str) -> None:
    parse = cg.parse_span(text, DEMO3)
    assert parse.error is not None
    assert parse.units == ()


def test_t4_span_finding_covers_parentheses_and_by_clauses_with_exact_offsets() -> None:
    text = "It follows by Prop. xi. that (III. xi. note) holds (by Def. vi.) and by Ax. i., Post. ii. so."
    spans = cg.find_spans(text)
    assert [(s.source, s.text) for s in spans] == [
        ("b", "by Prop. xi."),
        ("a", "III. xi. note"),
        ("a", "by Def. vi."),
        ("b", "by Ax. i., Post. ii."),
    ]
    assert all(text[s.offset : s.offset + len(s.text)] == s.text for s in spans)
    assert [s.offset for s in spans] == sorted(s.offset for s in spans)


def test_t4_an_ill_formed_numeral_is_unresolved() -> None:
    assert cg.parse_span("II. ivi.", DEMO3).error is not None


def test_t4_a_by_clause_inside_parentheses_is_one_span_not_two() -> None:
    assert [(s.source, s.text) for s in cg.find_spans("x (by Prop. xi.) y")] == [("a", "by Prop. xi.")]


def test_t4_a_by_clause_that_names_a_unit_but_leaves_the_vocabulary_is_still_a_span() -> None:
    spans = cg.find_spans("so by the Corollary and note to Prop. viii. of this part, then")
    assert [(s.source, s.text) for s in spans] == [("b", "by the Corollary and note to Prop. viii. of this part")]
    assert cg.parse_span(spans[0].text, DEMO3).error is not None


def test_t4_a_by_clause_that_names_no_unit_is_not_a_span() -> None:
    assert cg.find_spans("we are moved by nature and by reason, not by chance.") == []


def test_t4_the_part_numeral_and_part_word_are_citation_tokens() -> None:
    assert [s.text for s in cg.find_spans("a (IV. xi.) b (Part i.) c (I have) d (V. of it)")] == ["IV. xi.", "Part i."]


def test_t4_nested_parentheses_give_one_outer_span_and_an_unclosed_one_runs_to_the_end() -> None:
    text = "x (see (II. xi. note) here) y"
    assert [s.text for s in cg.find_spans(text)] == ["see (II. xi. note) here"]
    assert [s.text for s in cg.find_spans("x (II. xi. note")] == ["II. xi. note"]
    assert [s.text for s in cg.find_spans("x) (II. xi. note)")] == ["II. xi. note"]


# T5: unit expansion ---------------------------------------------------------------------------------------


SCHOLIUM = {
    "PART3_AFFECTS_P11_PROP": "Proposition.",
    "PART3_AFFECTS_P11_DEMO_01": "Demonstration.",
    "PART3_AFFECTS_P11_ESC_01_C01": "First (III. xi. note) sentence.",
    "PART3_AFFECTS_P11_ESC_01_C02": "Second sentence.",
    "PART3_AFFECTS_P20_DEMO_01": "(III. xi. note) and (III. xi.)",
}


def test_t5_a_scholium_yields_edges_to_all_its_chunks_and_a_proposition_only_its_own_label() -> None:
    result = cg.analyse(SCHOLIUM, pure=(), mixed=())
    text = SCHOLIUM["PART3_AFFECTS_P20_DEMO_01"]
    first, second = "PART3_AFFECTS_P20_DEMO_01@1", f"PART3_AFFECTS_P20_DEMO_01@{text.index('III. xi.)')}"
    assert [(e["citing"], e["cited"], e["span"]) for e in result["edge_list"]] == [
        ("PART3_AFFECTS_P11_ESC_01_C01", "PART3_AFFECTS_P11_ESC_01_C02", "PART3_AFFECTS_P11_ESC_01_C01@7"),
        ("PART3_AFFECTS_P20_DEMO_01", "PART3_AFFECTS_P11_ESC_01_C01", first),
        ("PART3_AFFECTS_P20_DEMO_01", "PART3_AFFECTS_P11_ESC_01_C02", first),
        ("PART3_AFFECTS_P20_DEMO_01", "PART3_AFFECTS_P11_PROP", second),
    ]


def test_t5_a_self_citation_is_dropped_and_counted() -> None:
    result = cg.analyse(SCHOLIUM, pure=(), mixed=())
    assert result["edges"]["self_citations_dropped"] == 1
    assert result["edges"]["total"] == 4
    assert all(e["citing"] != e["cited"] for e in result["edge_list"])


def test_t5_a_proposition_split_in_chunks_yields_every_chunk_label_of_that_proposition() -> None:
    chunks = {
        "PART1_GOD_P03_PROP_C01": "One.",
        "PART1_GOD_P03_PROP_C02": "Two.",
        "PART1_GOD_P03_DEMO_01": "Shown.",
        "PART1_GOD_P04_DEMO_01": "Shown (by the last Prop.).",
    }
    result = cg.analyse(chunks, pure=(), mixed=())
    assert [e["cited"] for e in result["edge_list"]] == ["PART1_GOD_P03_PROP_C01", "PART1_GOD_P03_PROP_C02"]


def test_t5_definitions_axioms_postulates_lemmas_and_emotions_resolve_to_their_chunks() -> None:
    chunks = {
        "PART1_GOD_DEF_02_C01": "a",
        "PART1_GOD_DEF_02_C02": "b",
        "PART1_GOD_AX_04": "c",
        "PART2_MIND_POST_01": "d",
        "PART2_MIND_LEMMA_03_C01": "e",
        "PART3_AFFECTS_DEFEMO_01_C01": "f",
        "PART3_AFFECTS_P01_DEMO_01": (
            "(I. Def. ii.) (I. Ax. iv.) (II. Post. i.) (II. Lemma iii.) (Def. of the Emotions, i.)"
        ),
    }
    result = cg.analyse(chunks, pure=(), mixed=())
    assert [e["cited"] for e in result["edge_list"]] == [
        "PART1_GOD_DEF_02_C01",
        "PART1_GOD_DEF_02_C02",
        "PART1_GOD_AX_04",
        "PART2_MIND_POST_01",
        "PART2_MIND_LEMMA_03_C01",
        "PART3_AFFECTS_DEFEMO_01_C01",
    ]


@pytest.mark.parametrize(
    ("label", "unit"),
    [
        ("PART1_GOD_DEF_02_C01", Unit(1, "DEF", 2)),
        ("PART1_GOD_DEF_02", Unit(1, "DEF", 2)),
        ("PART2_MIND_P11_COR_01", Unit(2, "COR", 11, 1)),
        ("PART3_AFFECTS_P13_ESC_01_C02", Unit(3, "ESC", 13, 1)),
        ("PART3_AFFECTS_DEFEMO_01", Unit(3, "DEFEMO", 1)),
        ("PART2_MIND_LEMMA_03", Unit(2, "LEMMA", 3)),
        ("PART1_GOD_AX_04", Unit(1, "AX", 4)),
        ("PART2_MIND_POST_01", Unit(2, "POST", 1)),
        ("PART4_BONDAGE_P37_DEMO_01", Unit(4, "DEMO", 37, 1)),
        ("PART4_BONDAGE_P37_PROP", Unit(4, "PROP", 37)),
        ("PART4_BONDAGE_P37_PROP_C02", Unit(4, "PROP", 37)),
        ("PART3_AFFECTS_GENDEF_C01", Unit(3, "GENDEF", 0)),
        ("PART1_GOD_APPENDIX_C05", Unit(1, "APPENDIX", 0)),
    ],
)
def test_t5_label_shapes_map_to_their_unit(label: str, unit: Unit) -> None:
    assert cg.parse_label(label) == unit


def test_t5_a_label_of_no_known_shape_maps_to_nothing() -> None:
    assert cg.parse_label("SOMETHING_ELSE") is None


# T6: editorial text ---------------------------------------------------------------------------------------


EDITORIAL = {
    "PART1_GOD_P01_PROP": "First.",
    "PART1_GOD_P02_ESC_01_C01": "Footnote (I. i.) editorial.",
    "PART1_GOD_P02_ESC_01_C02": "Mixed (I. i.) text.",
    "PART1_GOD_P02_DEMO_01": "(I. i.)",
}


def test_t6_spans_in_a_pure_editorial_label_land_only_in_the_editorial_block() -> None:
    result = cg.analyse(EDITORIAL, pure=("PART1_GOD_P02_ESC_01_C01",), mixed=())
    assert [(s["label"], s["text"]) for s in result["editorial"]["spans"]] == [("PART1_GOD_P02_ESC_01_C01", "I. i.")]
    assert result["editorial"]["labels"] == ["PART1_GOD_P02_ESC_01_C01"]
    assert "PART1_GOD_P02_ESC_01_C01" not in {e["citing"] for e in result["edge_list"]}
    assert result["spans"]["found"] == 2
    assert result["unresolved"] == [] and result["dangling"] == []


def test_t6_a_mixed_labels_edges_carry_the_flag_and_are_counted_apart() -> None:
    result = cg.analyse(EDITORIAL, pure=("PART1_GOD_P02_ESC_01_C01",), mixed=("PART1_GOD_P02_ESC_01_C02",))
    assert [(e["citing"], e["mixed"]) for e in result["edge_list"]] == [
        ("PART1_GOD_P02_ESC_01_C02", True),
        ("PART1_GOD_P02_DEMO_01", False),
    ]
    assert result["mixed"] == {"labels_with_spans": 1, "spans": 1, "edges": 1}


# T7: descriptives -----------------------------------------------------------------------------------------

HAND = {
    "PART1_GOD_AX_01": "An axiom.",
    "PART1_GOD_P01_PROP": "First.",
    "PART1_GOD_P01_DEMO_01": "Shown (see Ax. i.).",
    "PART1_GOD_P02_PROP": "Second.",
    "PART1_GOD_P02_DEMO_01": "Shown (Ax. i.) and (I. i.).",
    "PART2_MIND_P01_PROP": "Third.",
    "PART2_MIND_P01_DEMO_01": "Shown (I. ii.) and (by the last Prop.).",
    "PART2_MIND_P01_ESC_01_C01": "Note (by the last Prop.) and (I. ix.).",
    "PART2_MIND_P02_PROP": "Alone.",
}


def test_t7_span_counts_equal_hand_values() -> None:
    spans = cg.analyse(HAND, pure=(), mixed=())["spans"]
    assert spans == {
        "found": 7,
        "by_source": {"a": 7, "b": 0},
        "by_mode": {"cf": 0, "explicit": 6, "see": 1},
        "resolved": 6,
        "unresolved": 1,
        "relative": 2,
        "with_dangling": 1,
    }


def test_t7_edges_labels_and_parts_equal_hand_values() -> None:
    result = cg.analyse(HAND, pure=(), mixed=())
    assert [(e["citing"], e["cited"]) for e in result["edge_list"]] == [
        ("PART1_GOD_P01_DEMO_01", "PART1_GOD_AX_01"),
        ("PART1_GOD_P02_DEMO_01", "PART1_GOD_AX_01"),
        ("PART1_GOD_P02_DEMO_01", "PART1_GOD_P01_PROP"),
        ("PART2_MIND_P01_DEMO_01", "PART1_GOD_P02_PROP"),
        ("PART2_MIND_P01_ESC_01_C01", "PART2_MIND_P01_PROP"),
    ]
    assert result["edges"] == {
        "total": 5,
        "distinct_pairs": 5,
        "within_part": 4,
        "across_part": 1,
        "self_citations_dropped": 0,
    }
    assert result["labels"] == {
        "total": 9,
        "citing": 4,
        "cited": 4,
        "touched": 8,
        "share_touched": pytest.approx(8 / 9),
    }
    assert result["dangling_units"] == 1


def test_t7_degrees_most_cited_and_components_equal_hand_values() -> None:
    result = cg.analyse(HAND, pure=(), mixed=())
    quantiles = {"0": 0.0, "0.25": 0.0, "0.5": 0.0, "0.75": 1.0, "1": 2.0}
    assert result["degrees"]["in"] == quantiles
    assert result["degrees"]["out"] == quantiles
    assert result["most_cited_units"] == [
        {"unit": "1.AX.1", "citing_labels": 2},
        {"unit": "1.PROP.1", "citing_labels": 1},
        {"unit": "1.PROP.2", "citing_labels": 1},
        {"unit": "2.PROP.1", "citing_labels": 1},
    ]
    assert result["components"] == {"count": 3, "sizes": [4, 2, 2], "isolated_labels": 1}


def test_t7_the_relative_spans_are_listed_with_their_resolution() -> None:
    relative = cg.analyse(HAND, pure=(), mixed=())["relative"]
    text7, text8 = HAND["PART2_MIND_P01_DEMO_01"], HAND["PART2_MIND_P01_ESC_01_C01"]
    assert relative == [
        {
            "label": "PART2_MIND_P01_DEMO_01",
            "offset": text7.index("by the last"),
            "span": f"PART2_MIND_P01_DEMO_01@{text7.index('by the last')}",
            "text": "by the last Prop.",
            "form": "last",
            "resolved_to": None,
        },
        {
            "label": "PART2_MIND_P01_ESC_01_C01",
            "offset": text8.index("by the last"),
            "span": f"PART2_MIND_P01_ESC_01_C01@{text8.index('by the last')}",
            "text": "by the last Prop.",
            "form": "last",
            "resolved_to": "2.PROP.1",
        },
    ]


def test_t7_the_top_of_most_cited_units_is_cut_at_twenty() -> None:
    chunks: dict[str, str] = {f"PART1_GOD_P{n:02d}_PROP": "p" for n in range(1, 26)}
    numerals = "i. ii. iii. iv. v. vi. vii. viii. ix. x. xi. xii. xiii. xiv. xv. xvi. xvii. xviii. xix. xx."
    chunks["PART1_GOD_P30_DEMO_01"] = f"(I. {numerals} xxi. xxii. xxiii. xxiv. xxv.)"
    result = cg.analyse(chunks, pure=(), mixed=())
    assert len(result["most_cited_units"]) == 20
    assert result["most_cited_units"][0] == {"unit": "1.PROP.1", "citing_labels": 1}


def test_t7_repeated_pairs_count_once_in_degrees_and_components_but_every_span_is_an_edge() -> None:
    chunks = {"PART1_GOD_P01_PROP": "p", "PART1_GOD_P02_DEMO_01": "(I. i.) and (I. i.)"}
    result = cg.analyse(chunks, pure=(), mixed=())
    assert result["edges"]["total"] == 2
    assert result["edges"]["distinct_pairs"] == 1
    assert result["components"]["sizes"] == [2]
    assert result["degrees"]["in"]["1"] == 1.0


@pytest.mark.parametrize(
    ("values", "expected"),
    [
        ([0, 0, 0, 0, 0, 1, 1, 1, 2], [0.0, 0.0, 0.0, 1.0, 2.0]),
        ([4, 1, 3, 2], [1.0, 1.75, 2.5, 3.25, 4.0]),
        ([7], [7.0, 7.0, 7.0, 7.0, 7.0]),
    ],
)
def test_t7_quantiles_interpolate_linearly(values: list[int], expected: list[float]) -> None:
    assert list(cg.quantiles(values).values()) == expected
    assert list(cg.quantiles(values)) == ["0", "0.25", "0.5", "0.75", "1"]


# T8: pins and determinism ---------------------------------------------------------------------------------


def _write_world(tmp_path: Path) -> tuple[list[Path], Path, dict[Path, str]]:
    parts = [
        {k: v for k, v in HAND.items() if k.startswith("PART1")},
        {k: v for k, v in HAND.items() if k.startswith("PART2")},
    ]
    manifests = []
    for i, chunks in enumerate(parts, start=1):
        path = tmp_path / f"part{i}_manifest.json"
        path.write_text(json.dumps(chunks), encoding="utf-8")
        manifests.append(path)
    marks = tmp_path / "editorial_marks.json"
    marks.write_text(json.dumps({"marked": {"PART2_MIND_P01_ESC_01_C01": {"pure": False}}}), encoding="utf-8")
    expected = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in [*manifests, marks]}
    return manifests, marks, expected


def test_t8_run_writes_the_exploration_with_digests(tmp_path: Path) -> None:
    manifests, marks, expected = _write_world(tmp_path)
    out = tmp_path / "out" / "citation_graph.json"
    result = cg.run(manifests, marks, expected, out)
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written == result
    assert written["kind"] == "exploration"
    assert isinstance(written["statement"], str) and written["statement"]
    assert written["digests"] == {p.name: expected[p] for p in expected}
    assert written["spans"]["found"] == 7
    assert written["mixed"] == {"labels_with_spans": 1, "spans": 2, "edges": 1}
    assert out.read_text(encoding="utf-8").endswith("\n")


@pytest.mark.parametrize("which", [0, 1, 2])
def test_t8_any_digest_mismatch_refuses_and_writes_nothing(tmp_path: Path, which: int) -> None:
    manifests, marks, expected = _write_world(tmp_path)
    victim = [*manifests, marks][which]
    expected[victim] = "0" * 64
    out = tmp_path / "out" / "citation_graph.json"
    with pytest.raises(cg.IntegrityError):
        cg.run(manifests, marks, expected, out)
    assert not out.exists()
    assert not out.parent.exists()


def test_t8_a_file_with_no_pin_refuses(tmp_path: Path) -> None:
    manifests, marks, expected = _write_world(tmp_path)
    del expected[marks]
    out = tmp_path / "citation_graph.json"
    with pytest.raises(cg.IntegrityError):
        cg.run(manifests, marks, expected, out)
    assert not out.exists()


def test_t8_two_runs_write_identical_bytes(tmp_path: Path) -> None:
    manifests, marks, expected = _write_world(tmp_path)
    cg.run(manifests, marks, expected, tmp_path / "a.json")
    cg.run(manifests, marks, expected, tmp_path / "b.json")
    assert (tmp_path / "a.json").read_bytes() == (tmp_path / "b.json").read_bytes()


def test_t8_the_pins_equal_the_committed_files() -> None:
    assert len(cg.EXPECTED) == 6
    for path, pin in cg.EXPECTED.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == pin
    assert [p.name for p in cg.MANIFESTS] == [
        "part1_god_manifest.json",
        "part2_mind_manifest.json",
        "part3_affects_manifest.json",
        "part4_bondage_manifest.json",
        "part5_power_manifest.json",
    ]
    assert cg.MARKS.name == "editorial_marks.json"


def test_t8_the_default_output_is_under_data_refapp() -> None:
    assert cg.DEFAULT_OUT == cg.REPO_ROOT / "data" / "refapp" / "citation_graph.json"


# X: additional guards -------------------------------------------------------------------------------------


def test_x1_a_marked_label_missing_from_the_manifests_is_an_error(tmp_path: Path) -> None:
    manifests, marks, _ = _write_world(tmp_path)
    marks.write_text(json.dumps({"marked": {"PART9_X_P01_PROP": {"pure": True}}}), encoding="utf-8")
    expected = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in [*manifests, marks]}
    with pytest.raises(ValueError, match="PART9_X_P01_PROP"):
        cg.run(manifests, marks, expected, tmp_path / "out.json")
    assert not (tmp_path / "out.json").exists()


def test_x2_a_label_in_two_manifests_is_an_error(tmp_path: Path) -> None:
    manifests, marks, _ = _write_world(tmp_path)
    manifests[1].write_text(json.dumps({"PART1_GOD_AX_01": "again"}), encoding="utf-8")
    expected = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in [*manifests, marks]}
    with pytest.raises(ValueError, match="PART1_GOD_AX_01"):
        cg.run(manifests, marks, expected, tmp_path / "out.json")


def test_x6_a_chunk_that_is_not_text_is_an_error(tmp_path: Path) -> None:
    manifests, marks, _ = _write_world(tmp_path)
    manifests[0].write_text(json.dumps({"PART1_GOD_AX_01": 3}), encoding="utf-8")
    expected = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in [*manifests, marks]}
    with pytest.raises(TypeError, match="PART1_GOD_AX_01"):
        cg.run(manifests, marks, expected, tmp_path / "out.json")


def test_x3_main_prints_one_line_and_writes_to_the_given_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    manifests, marks, expected = _write_world(tmp_path)
    monkeypatch.setattr(cg, "MANIFESTS", manifests)
    monkeypatch.setattr(cg, "MARKS", marks)
    monkeypatch.setattr(cg, "EXPECTED", expected)
    out = tmp_path / "result.json"
    assert cg.main(["--out", str(out)]) == 0
    assert capsys.readouterr().out == "spans=7 resolved=6 unresolved=1 edges=5 share_touched=0.8889\n"
    assert json.loads(out.read_text(encoding="utf-8"))["kind"] == "exploration"


def test_x4_main_refuses_with_a_message_and_writes_nothing_on_a_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    manifests, marks, expected = _write_world(tmp_path)
    expected[marks] = "0" * 64
    monkeypatch.setattr(cg, "MANIFESTS", manifests)
    monkeypatch.setattr(cg, "MARKS", marks)
    monkeypatch.setattr(cg, "EXPECTED", expected)
    out = tmp_path / "result.json"
    assert cg.main(["--out", str(out)]) == 2
    assert not out.exists()
    assert "refused" in capsys.readouterr().err


def test_x5_the_result_is_plain_json() -> None:
    result: dict[str, Any] = cg.analyse(HAND, pure=(), mixed=())
    assert json.loads(json.dumps(result, allow_nan=False)) == result
