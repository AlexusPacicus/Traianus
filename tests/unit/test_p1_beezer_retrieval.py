"""Unit tests of tools/experiments/p1_beezer_retrieval.py.

Specification: docs/methodology/instrument-audit/P1.md (revision 6), contracts.md (section 6) and
derivations.md (D5, D30-D34; the derivation tests are in test_audit_derivations.py). Synthetic
inputs and stub providers only: CI has no .data/, and the measurement is never run on the real
files here. The one test that loads the real model is in the model partition.
"""

import hashlib
import itertools
import json
import math
import re
import struct
import zlib
from fractions import Fraction

import numpy as np
import pytest

from tools.experiments import p1_beezer_retrieval as p1

DIM = 384
PREFIX = "MATH_BEEZER_"
CHUNKS = {
    "DEF_A": "common alphaw",
    "DEF_B": "betaw",
    "DEF_C": "common gammaw",
    "DEF_D": "common deltaw",
    "THM_E": "common epsw",
    "THM_F": "common zetaw",
    "THM_G": "common etaw",
    "THM_H": "common thetaw",
    "THM_I": "common thetaw",
}
LABEL_OF = {"A": "DEF_A", "B": "DEF_B", "C": "DEF_C", "D": "DEF_D", "E": "THM_E"}
ITEMS = [
    (1, "alphaw", ["A"]),
    (2, "common", ["B"]),
    (3, "gammaw", ["C"]),
    (4, "deltaw epsw", ["D", "E"]),
    (5, "thetaw", []),
    (6, "alphaw again", ["A"]),
]
CITATIONS = [
    [PREFIX + "THM_H", PREFIX + "THM_I"],
    [PREFIX + "DEF_A", PREFIX + "DEF_B"],
    [PREFIX + "DEF_B", PREFIX + "DEF_C"],
]
NAMES = {
    "manifest": "beezer_manifest.json",
    "test_set": "pilot1_test_set.json",
    "citations": "beezer_citations.json",
}
DIGESTS = {name: "0" * 64 for name in NAMES.values()}
ENV = {"device": "cpu"}
KEYS = [
    "valid",
    "first_failed",
    "failed",
    "digests",
    "environment",
    "vectors_sha256",
    "alignment_vectors_sha256",
    "counts",
    "alignment",
    "k5",
    "k1",
    "holds",
    "holds_limit",
    "shuffle",
    "bm25_check",
    "group_sensitivity",
    "report_only",
]
FIRST_QUERY_ROW = len(CHUNKS)


def _vec(text):
    seed = zlib.crc32(text.encode("utf-8"))
    return np.random.default_rng(seed).standard_normal(DIM).astype(np.float32)


def _unit(u):
    u = u.astype(np.float64)
    return u / np.linalg.norm(u)


def _chunk(suffix):
    return _vec(CHUNKS[suffix])


def _query_vectors():
    """Queries whose engine outcome is fixed: a hit is the target's own vector, a miss its negative."""
    both = (_unit(_chunk("DEF_D")) + _unit(_chunk("THM_E"))).astype(np.float32)
    return {
        "alphaw": _chunk("DEF_A"),
        "common": _chunk("DEF_B"),
        "gammaw": -_chunk("DEF_C"),
        "deltaw epsw": both,
        "thetaw": _chunk("THM_H"),
        "alphaw again": _chunk("DEF_A"),
    }


class Stub:
    """Provider recording its inputs in call order; ``hook(index, text, u)`` may alter an output."""

    def __init__(self, vectors=None, hook=None):
        self.vectors = vectors or {}
        self.hook = hook
        self.calls = []

    def encode(self, text):
        index = len(self.calls)
        self.calls.append(text)
        u = self.vectors.get(text, _vec(text))
        return u if self.hook is None else self.hook(index, text, u)

    def encode_batch(self, texts):
        raise AssertionError("encode_batch must not be called")


class Model:
    max_seq_length = 1

    def __init__(self, device="cpu"):
        self.device = device

    def tokenizer(self, text):
        return {"input_ids": text.split()}

    def to(self, device):
        return self


def _raw(manifest=None, items=None, citations=None):
    if manifest is None:
        manifest = {PREFIX + key: text for key, text in CHUNKS.items()}
    if items is None:
        items = [
            {"id": i, "name": "n", "prose_es": "es", "prose_en": q, "expected": e}
            for i, q, e in reversed(ITEMS)
        ]
    if citations is None:
        citations = CITATIONS
    return {
        "manifest": json.dumps(manifest).encode("utf-8"),
        "test_set": json.dumps({"pilot": "synthetic", "items": items}).encode("utf-8"),
        "citations": json.dumps(citations).encode("utf-8"),
    }


def _files(directory, raw):
    paths = {}
    for key, data in raw.items():
        paths[key] = directory / NAMES[key]
        paths[key].write_bytes(data)
    return paths, {key: hashlib.sha256(data).hexdigest() for key, data in raw.items()}


def _resolver(epsilon):
    """The resolver run() takes: ``epsilon`` is a value to return, or already a callable."""
    return epsilon if callable(epsilon) else lambda: epsilon


def _unparsable():
    raise ValueError("could not convert string to float: 'not-a-number'")


def _run(directory, raw=None, *, digests=None, epsilon=0.8, build=Model, provider=None):
    paths, own = _files(directory, raw or _raw())
    out = directory / "P1_result.json"
    provider = provider or Stub(_query_vectors())
    return p1.run(out, paths, digests or own, _resolver(epsilon), build, provider), out


def _measure(provider=None, raw=None):
    inp = p1.parse_inputs(raw or _raw())
    provider = provider or Stub(_query_vectors())
    return p1.measure(inp, p1.resolve_acros(inp), provider, Model(), ENV, DIGESTS)


def _tail(ps, h):
    """P(sum of independent Bernoulli(p) >= h), by enumeration of the outcomes."""
    total = Fraction(0)
    for outcome in itertools.product((0, 1), repeat=len(ps)):
        if sum(outcome) >= h:
            weight = Fraction(1)
            for o, p in zip(outcome, ps, strict=True):
                weight *= p if o else 1 - p
            total += weight
    return total


# BM25 (P1.md, BM25 score) -----------------------------------------------------------------------

EXAMPLE = ["cat cat dog", "dog bird", "fish fish fish fish"]
# N = 3, avgdl = 3, idf(cat) = ln(8/3), idf(dog) = ln(8/5); the query adds frog, in no document.
# d1 = 1.375 idf(cat) + idf(dog), d2 = idf(dog) * 2.2 / 1.9, d3 holds no query term.
HAND = [1.818643852136859129, 0.544214728600325378, 0.0]


def test_tokens_are_runs_of_ascii_lowercase_letters_and_digits():
    assert p1.tokens("It's a x-ray: 3D, ÉTÉ") == ["it", "s", "a", "x", "ray", "3d", "t"]


def test_bm25_matches_the_hand_scores_to_twelve_digits():
    index = p1.bm25_index(EXAMPLE)
    scores = p1.bm25_scores(index, "Cat cat dog, FROG")
    assert [abs(s - h) < 1e-12 for s, h in zip(scores, HAND, strict=True)] == [True] * 3
    assert scores[2] == 0.0


def test_bm25_counts_a_repeated_query_term_once_and_an_absent_term_adds_nothing():
    index = p1.bm25_index(EXAMPLE)
    assert p1.bm25_scores(index, "Cat cat dog, FROG") == p1.bm25_scores(index, "cat dog")


def test_bm25_check_passes_on_the_example_and_fails_with_two_rows_swapped():
    texts = [*EXAMPLE, "dog"]
    index = p1.bm25_index(texts)

    def rows(query):
        return p1.bm25_scores(index, query)

    def swapped(query):
        scores = rows(query)
        scores[0], scores[1] = scores[1], scores[0]
        return scores

    assert p1.bm25_check(texts, rows) == {"chunks_with_unique_token": 3, "passed": 3}
    assert p1.bm25_check(texts, swapped) == {"chunks_with_unique_token": 3, "passed": 1}


# Draws, ties, hits ------------------------------------------------------------------------------

SEED = 20261002
KEY_0 = [99, 171, 188, 243, 90, 117]
KEY_1 = [18, 194, 211, 88, 123, 323]


def test_draw_pins_the_numpy_stream_and_the_order_of_draws():
    keys, shuffles = p1.draw(342, 28, 18)
    assert p1.SEED == SEED
    assert keys[0][:6].tolist() == KEY_0
    assert keys[1][:6].tolist() == KEY_1
    rng = np.random.default_rng(SEED)
    assert len(keys) == 28 and len(shuffles) == 1000
    assert all(np.array_equal(k, rng.permutation(342)) for k in keys)
    assert shuffles == [rng.permutation(18).tolist() for _ in range(1000)]
    assert shuffles[0] != np.random.default_rng(SEED).permutation(18).tolist()
    assert np.array_equal(keys[0], np.random.Generator(np.random.PCG64(SEED)).permutation(342))


def test_ranking_orders_by_score_descending_then_key_ascending():
    assert p1.ranking([0.5, 0.9, 0.5, 0.9, 0.1], [4, 3, 2, 1, 0]) == [3, 1, 2, 0, 4]
    assert p1.ranking([-0.5, -0.1], [0, 1]) == [1, 0]


def test_hit_at_the_k_boundary_for_one_and_for_two_expected_labels():
    order = [7, 3, 5, 1, 0, 2, 4, 6]
    assert p1.is_hit(order, {1}, 4) and not p1.is_hit(order, {1}, 3)
    assert p1.is_hit(order, {1, 6}, 4) and not p1.is_hit(order, {1, 6}, 3)
    assert p1.is_hit(order, {2, 6}, 6) and not p1.is_hit(order, {2, 6}, 5)
    assert p1.is_hit(order, {4, 6}, 7) and not p1.is_hit(order, {4, 6}, 6)
    assert [p1.best_position(order, t) for t in ({1}, {1, 6}, {4, 6}, {7})] == [4, 4, 7, 1]


def test_distinct_acros_count_a_shared_target_once_and_either_label_of_m_2():
    expected = [["X"], ["X", "Y"], ["Z", "W"]]
    acro_index = {"X": 10, "Y": 11, "Z": 12, "W": 13}
    assert p1.acros_recovered(expected, acro_index, [[10, 5], [10, 3], [13, 5]]) == 2
    assert p1.acros_recovered(expected, acro_index, [[10], [11, 10], [12, 13]]) == 4
    assert p1.acros_recovered(expected, acro_index, [[1], [2], [3]]) == 0


def test_shuffle_gives_item_s_r_the_expected_set_of_item_s_pi_r():
    tops = [{10, 30}, {20}, {99}]
    targets = [{10}, {20}, {30}]
    assert p1.shuffled_h(tops, targets, [2, 0, 1]) == 1
    assert p1.shuffled_h(tops, targets, [1, 2, 0]) == 0
    assert p1.shuffled_h(tops, targets, [0, 1, 2]) == 2


# Group sensitivity (P1.md, Group sensitivity; D34) -----------------------------------------------

REAL_EXPECTED = {
    1: ["NV"],
    2: ["GSP"],
    6: ["NV"],
    7: ["IP"],
    11: ["NSM"],
    12: ["NSM", "KLT"],
    13: ["SUV"],
    14: ["OV"],
    15: ["GSP"],
    16: ["ROM", "ROLT"],
    17: ["MM"],
    18: ["LT"],
    21: ["D", "CV"],
    23: ["IP"],
    24: ["IP"],
    25: ["TM"],
    27: ["LCCV"],
    28: ["NV"],
}


def test_the_units_of_the_test_set_are_twelve_with_the_shared_targets_joined():
    assert p1.unit_ids(REAL_EXPECTED) == [
        [1, 6, 28],
        [2, 15],
        [7, 23, 24],
        [11, 12],
        [13],
        [14],
        [16],
        [17],
        [18],
        [21],
        [25],
        [27],
    ]


def test_a_chain_of_three_items_joined_through_a_two_acro_item_is_one_unit():
    assert p1.unit_ids({3: ["b"], 1: ["a"], 4: ["c"], 2: ["a", "b"]}) == [[1, 2, 3], [4]]


def test_unit_hit_and_both_unit_p_values_on_a_hand_computed_case():
    units = [[1, 2], [3], [4], [5], [6]]
    p_by_id = {1: Fraction(1, 2), 2: Fraction(1, 2)} | dict.fromkeys((3, 4, 5, 6), Fraction(1, 4))
    engine = {1: False, 2: True, 3: True, 4: True, 5: False, 6: False}
    bm25 = {1: False, 2: False, 3: False, 4: False, 5: True, 6: False}
    assert p1.unit_hits(units, engine) == [True, True, True, False, False]
    assert p1.unit_hits(units, bm25) == [False, False, False, True, False]
    q = p1.unit_probabilities(units, p_by_id)
    assert q == [Fraction(3, 4)] + [Fraction(1, 4)] * 4
    figures = p1.compare_arms(q, p1.unit_hits(units, engine), p1.unit_hits(units, bm25))
    assert figures["H_engine"] == 3 and figures["H_bm25"] == 1
    assert figures["p_chance"] == Fraction(107, 512)
    assert (figures["b"], figures["c"]) == (3, 1)
    assert figures["p_mcnemar"] == Fraction(5, 16)


# Decision (P1.md, Decision) ----------------------------------------------------------------------


def test_holds_is_the_conjunction_of_the_four_conditions():
    for flags in itertools.product((False, True), repeat=4):
        assert p1.holds(*flags) is all(flags)


def test_a_condition_passes_only_strictly_below_one_twentieth_on_the_fraction():
    below = Fraction(1, 20) - Fraction(1, 10**30)
    assert p1.passes(below)
    assert not p1.passes(Fraction(1, 20))
    assert not p1.passes(Fraction(1, 20) + Fraction(1, 10**30))
    assert float(below) == 0.05 and not float(below) < 0.05


def test_fractions_are_stored_as_numerator_denominator_and_float():
    assert p1.fraction_record(Fraction(6, 8)) == {"num": 3, "den": 4, "float": 0.75}


# Refusals (P1.md, Refusal) -----------------------------------------------------------------------


def test_the_unmodified_synthetic_world_runs_and_writes_the_result(tmp_path):
    code, out = _run(tmp_path)
    assert code == 0
    text = out.read_text(encoding="utf-8")
    data = json.loads(text)
    assert text.endswith("}\n") and list(data) == KEYS
    assert data["valid"] is True
    assert list(data["environment"]) == [
        "python",
        "numpy",
        "torch",
        "sentence_transformers",
        "platform",
        "device",
        "max_seq_length",
        "numpy_config",
        "torch_threads",
    ]
    assert data["environment"]["device"] == "cpu" and data["environment"]["max_seq_length"] == 1
    assert data["digests"] == {NAMES[k]: hashlib.sha256(v).hexdigest() for k, v in _raw().items()}


def _refused(directory, capsys, identifier, **kwargs):
    code, _ = _run(directory, **kwargs)
    assert code != 0
    assert capsys.readouterr().err.startswith(identifier)
    assert sorted(p.name for p in directory.glob("*.json")) == sorted(NAMES.values())


@pytest.mark.parametrize("name", list(NAMES))
@pytest.mark.parametrize("where", ["first", "last", "seeded"])
def test_rf1_one_flipped_bit_in_any_of_the_three_files_refuses(tmp_path, capsys, name, where):
    paths, digests = _files(tmp_path, _raw())
    data = bytearray(paths[name].read_bytes())
    seeded = int(np.random.default_rng(20261003).integers(len(data)))
    data[{"first": 0, "last": len(data) - 1, "seeded": seeded}[where]] ^= 0x01
    paths[name].write_bytes(bytes(data))
    out = tmp_path / "P1_result.json"
    code = p1.run(out, paths, digests, _resolver(0.8), Model, Stub(_query_vectors()))
    assert code != 0 and capsys.readouterr().err.startswith("RF1")
    assert not out.exists()


def test_rf1_a_missing_file_refuses(tmp_path, capsys):
    paths, digests = _files(tmp_path, _raw())
    paths["citations"].unlink()
    out = tmp_path / "P1_result.json"
    assert p1.run(out, paths, digests, _resolver(0.8), Model, Stub()) != 0
    assert capsys.readouterr().err.startswith("RF1") and not out.exists()


BAD_MANIFESTS = {
    "duplicate_key": b'{"MATH_BEEZER_DEF_A": "x", "MATH_BEEZER_DEF_A": "y"}',
    "nan": b'{"MATH_BEEZER_DEF_A": NaN}',
    "infinity": b'{"MATH_BEEZER_DEF_A": Infinity}',
    "empty_label": b'{"": "x"}',
    "empty_text": b'{"MATH_BEEZER_DEF_A": ""}',
    "non_string_text": b'{"MATH_BEEZER_DEF_A": 7}',
    "invalid_utf8": b'{"MATH_BEEZER_DEF_A": "\xff"}',
    "not_an_object": b'["MATH_BEEZER_DEF_A"]',
    "number_that_parses_to_infinity": b'{"MATH_BEEZER_DEF_A": "x", "MATH_BEEZER_DEF_B": 1e999}',
}
BAD_TEST_SETS = {
    "duplicate_key": b'{"items": [], "items": []}',
    "nan": b'{"items": [{"id": 1, "prose_en": NaN, "expected": []}]}',
    "infinity": b'{"items": [{"id": 1, "prose_en": "q", "expected": [], "x": -Infinity}]}',
    "empty_prose": b'{"items": [{"id": 1, "prose_en": "", "expected": []}]}',
    "non_string_prose": b'{"items": [{"id": 1, "prose_en": 3, "expected": []}]}',
    "missing_prose": b'{"items": [{"id": 1, "expected": []}]}',
    "number_that_parses_to_infinity": b'{"items": [{"id": 1, "prose_en": "q", "expected": [], "x": 1e999}]}',
    "not_an_object": b'[{"id": 1, "prose_en": "q", "expected": []}]',
    "no_items_key": b'{"pilot": "synthetic"}',
    "items_not_a_list": b'{"items": {"id": 1, "prose_en": "q", "expected": []}}',
    "item_not_an_object": b'{"items": [{"id": 1, "prose_en": "q", "expected": []}, 7]}',
    "missing_id": b'{"items": [{"prose_en": "q", "expected": []}]}',
    "string_id": b'{"items": [{"id": "1", "prose_en": "q", "expected": []}]}',
    "float_id": b'{"items": [{"id": 1.0, "prose_en": "q", "expected": []}]}',
    "boolean_id": b'{"items": [{"id": true, "prose_en": "q", "expected": []}]}',
    "repeated_id": b'{"items": [{"id": 1, "prose_en": "q", "expected": []}, '
    b'{"id": 1, "prose_en": "r", "expected": []}]}',
    "expected_missing": b'{"items": [{"id": 1, "prose_en": "q"}]}',
    "expected_a_string": b'{"items": [{"id": 1, "prose_en": "q", "expected": "A"}]}',
    "expected_with_a_non_string": b'{"items": [{"id": 1, "prose_en": "q", "expected": ["A", 3]}]}',
}
BAD_CITATIONS = {
    "number_that_parses_to_infinity": b'[["MATH_BEEZER_DEF_A", 1e999]]',
    "not_a_list": b'{"MATH_BEEZER_DEF_A": "MATH_BEEZER_DEF_B"}',
    "pair_not_a_list": b'[{"MATH_BEEZER_DEF_A": 1, "MATH_BEEZER_DEF_B": 2}]',
    "pair_of_one": b'[["MATH_BEEZER_DEF_A"]]',
    "pair_of_three": b'[["MATH_BEEZER_DEF_A", "MATH_BEEZER_DEF_B", "MATH_BEEZER_DEF_C"]]',
    "end_not_a_string": b'[["MATH_BEEZER_DEF_A", 3]]',
    "end_not_a_manifest_label": b'[["MATH_BEEZER_DEF_A", "MATH_BEEZER_DEF_Z"]]',
}


@pytest.mark.parametrize("name", list(BAD_MANIFESTS))
def test_rf2_the_parser_refuses_a_bad_manifest(name):
    raw = _raw(citations=[])
    raw["manifest"] = BAD_MANIFESTS[name]
    with pytest.raises(p1.Refusal) as caught:
        p1.parse_inputs(raw)
    assert caught.value.identifier == "RF2"


@pytest.mark.parametrize("name", list(BAD_TEST_SETS))
def test_rf2_the_parser_refuses_a_bad_test_set(name):
    raw = _raw()
    raw["test_set"] = BAD_TEST_SETS[name]
    with pytest.raises(p1.Refusal) as caught:
        p1.parse_inputs(raw)
    assert caught.value.identifier == "RF2"


@pytest.mark.parametrize("name", list(BAD_CITATIONS))
def test_rf2_the_parser_refuses_bad_citations(name):
    raw = _raw()
    raw["citations"] = BAD_CITATIONS[name]
    with pytest.raises(p1.Refusal) as caught:
        p1.parse_inputs(raw)
    assert caught.value.identifier == "RF2"


def test_rf2_the_parser_accepts_the_valid_inputs_and_sorts_the_items_by_id():
    inp = p1.parse_inputs(_raw())
    assert [item.id for item in inp.items] == [1, 2, 3, 4, 5, 6]
    assert [item.query for item in inp.items] == [q for _, q, _ in ITEMS]
    assert [list(item.acros) for item in inp.items] == [e for _, _, e in ITEMS]


def test_rf2_through_the_run_writes_nothing(tmp_path, capsys):
    raw = _raw()
    raw["manifest"] = BAD_MANIFESTS["duplicate_key"]
    _refused(tmp_path, capsys, "RF2", raw=raw)


def test_rf3_an_acro_with_no_label_or_with_two_labels_refuses(tmp_path, capsys):
    without = {PREFIX + k: v for k, v in CHUNKS.items() if k != "THM_E"}
    twice = {PREFIX + k: v for k, v in CHUNKS.items()} | {PREFIX + "DEF_E": "other text"}
    for manifest in (without, twice):
        inp = p1.parse_inputs(_raw(manifest=manifest))
        with pytest.raises(p1.Refusal) as caught:
            p1.resolve_acros(inp)
        assert caught.value.identifier == "RF3"
    sub = tmp_path / "a"
    sub.mkdir()
    _refused(sub, capsys, "RF3", raw=_raw(manifest=without))


def test_rf4_an_epsilon_other_than_0_8_refuses(tmp_path, capsys):
    _refused(tmp_path, capsys, "RF4", epsilon=0.81)


def test_rf4_the_resolver_is_called_within_the_checks_and_a_value_error_refuses(tmp_path, capsys):
    calls = []

    def resolver():
        calls.append(1)
        return _unparsable()

    _refused(tmp_path, capsys, "RF4", epsilon=resolver)
    assert calls == [1]


def test_rf4_a_resolver_returning_0_81_is_called_once_and_refuses(tmp_path, capsys):
    calls = []

    def resolver():
        calls.append(1)
        return 0.81

    _refused(tmp_path, capsys, "RF4", epsilon=resolver)
    assert calls == [1]


def test_rf4_the_real_resolver_with_an_unparsable_environment_value_refuses(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("TRAIANUS_EPSILON_EDGE", "not-a-number")
    _refused(tmp_path, capsys, "RF4", epsilon=p1.resolve_epsilon_edge)


def test_rf4_an_error_other_than_value_error_is_not_a_refusal(tmp_path):
    def resolver():
        raise RuntimeError("not a parse failure")

    with pytest.raises(RuntimeError):
        _run(tmp_path, epsilon=resolver)


def _cannot_load():
    raise OSError("offline cache miss")


def test_rf5_an_encoder_that_cannot_load_or_sits_off_the_cpu_refuses(tmp_path, capsys):
    first = tmp_path / "a"
    first.mkdir()
    _refused(first, capsys, "RF5", build=_cannot_load)
    second = tmp_path / "b"
    second.mkdir()
    _refused(second, capsys, "RF5", build=lambda: Model("cuda:0"))


def test_rf5_a_revision_other_than_the_pinned_one_refuses():
    with pytest.raises(p1.Refusal) as caught:
        p1.load_encoder(Model, "0" * 40)
    assert caught.value.identifier == "RF5"
    assert p1.PINNED_REVISION == "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"


def test_the_first_failure_ends_the_run_in_the_order_rf1_to_rf5(tmp_path, capsys):
    bad_json = _raw()
    bad_json["test_set"] = BAD_TEST_SETS["duplicate_key"]
    bad_acro = _raw(manifest={PREFIX + k: v for k, v in CHUNKS.items() if k != "THM_E"})
    cases = [
        ("RF1", bad_json, "f" * 64, _unparsable, _cannot_load),
        ("RF2", bad_json, None, _unparsable, _cannot_load),
        ("RF3", bad_acro, None, _unparsable, _cannot_load),
        ("RF4", _raw(), None, _unparsable, _cannot_load),
        ("RF5", _raw(), None, _resolver(0.8), _cannot_load),
    ]
    for number, (identifier, raw, digest, resolver, build) in enumerate(cases):
        directory = tmp_path / str(number)
        directory.mkdir()
        paths, own = _files(directory, raw)
        digests = own if digest is None else {**own, "manifest": digest}
        out = directory / "P1_result.json"
        assert p1.run(out, paths, digests, resolver, build, Stub()) != 0
        assert capsys.readouterr().err.startswith(identifier)
        assert not out.exists()


# Vectors (P1.md, Vectors) ------------------------------------------------------------------------


def _with_bits(u, index, bits):
    w = u.copy()
    w.view(np.uint32)[index] = bits
    return w


def _bad_outputs():
    u = _vec("x")
    return {
        "zero": np.zeros(DIM, np.float32),
        "inf": _with_bits(u, 3, 0x7F800000),
        "nan": _with_bits(u, 3, 0x7FC00000),
        "nan_payload": _with_bits(u, 3, 0xFF800001),
        "float64": u.astype(np.float64),
        "float16": u.astype(np.float16),
        "two_dimensional": u.reshape(2, DIM // 2),
        "short": u[: DIM - 1],
        "list": u.tolist(),
    }


@pytest.mark.parametrize("name", list(_bad_outputs()))
def test_a_provider_output_of_the_wrong_format_or_range_is_rejected(name):
    with pytest.raises(p1.InvalidVector):
        p1.unit_vector(_bad_outputs()[name])


def test_a_flip_of_the_lowest_mantissa_bit_is_accepted():
    u = _vec("x")
    w = u.copy()
    w.view(np.uint32)[0] ^= 1
    assert not np.array_equal(u, w)
    assert p1.unit_vector(w).shape == (DIM,)


@pytest.mark.parametrize(
    ("name", "mask"),
    [("sign", 0x80000000), ("lowest_exponent_bit", 1 << 23), ("middle_exponent_bit", 1 << 27)],
)
def test_a_flip_of_the_sign_or_of_an_exponent_bit_that_stays_finite_is_accepted_and_renormalised(name, mask):
    u = _vec("x")
    w = u.copy()
    w.view(np.uint32)[0] ^= mask
    assert np.isfinite(w[0]) and w[0] != 0.0 and w[0] != u[0]
    v = p1.unit_vector(w)
    assert abs(np.linalg.norm(v) - 1.0) <= 1e-12
    assert np.allclose(v, _unit(w), rtol=0.0, atol=1e-7)
    assert not np.allclose(v, _unit(u), rtol=0.0, atol=1e-7)


def test_the_docstrings_of_the_script_and_of_the_tests_name_only_revision_6():
    for module_doc in (p1.__doc__, __doc__):
        assert re.findall(r"revision \d+", module_doc) == ["revision 6"]


def test_unit_vector_normalises_in_binary64():
    u = _vec("x")
    v = p1.unit_vector(3.0 * u)
    assert v.dtype == np.float64 and v.shape == (DIM,)
    assert abs(np.linalg.norm(v) - 1.0) <= 1e-12
    assert np.allclose(v, _unit(u), rtol=0.0, atol=1e-7)


def test_distance_is_clamped_at_zero_for_a_score_above_one():
    assert p1.distance(1.0 + 2e-12) == 0.0
    assert p1.distance(0.0) == math.sqrt(2.0)
    assert p1.distance(-1.0) == 2.0


def test_matrix_hash_is_the_little_endian_c_order_float64_bytes():
    rows = [np.array([1.0, 0.0]), np.array([0.0, 0.5])]
    expected = hashlib.sha256(struct.pack("<4d", 1.0, 0.0, 0.0, 0.5)).hexdigest()
    assert p1.matrix_sha256(rows) == expected


def test_queries_follow_the_chunks_in_item_id_order_and_each_reads_its_own_prose():
    inp = p1.parse_inputs(_raw())
    prose = {i: q for i, q, _ in ITEMS}
    queries = [item.query for item in inp.items]
    stub = Stub()
    first, second = p1.encode_passes(stub, inp.texts, queries)
    n = len(inp.texts)
    assert stub.calls == inp.texts + queries + inp.texts
    assert len(first) == n + len(queries) and len(second) == n
    for item in inp.items:
        row = FIRST_QUERY_ROW + item.id - 1
        assert item.query == prose[item.id]
        assert np.array_equal(first[row], _unit(_vec(item.query)))
    assert all(np.array_equal(first[j], _unit(_vec(t))) for j, t in enumerate(inp.texts))


def test_labels_texts_and_index_come_from_one_enumeration():
    a, b, c = (PREFIX + s for s in ("DEF_A", "DEF_B", "DEF_C"))
    plain = {a: "one", b: "two", c: "three"}
    swapped = {b: "two", a: "one", c: "three"}
    seen = []
    for manifest in (plain, swapped):
        inp = p1.parse_inputs(_raw(manifest=manifest, citations=[]))
        assert inp.labels == list(manifest)
        assert inp.texts == [manifest[label] for label in inp.labels]
        assert all(inp.texts[inp.index[label]] == manifest[label] for label in manifest)
        assert inp.index == {label: j for j, label in enumerate(manifest)}
        seen.append((inp.index[a], inp.texts[0]))
    assert seen == [(0, "one"), (1, "two")]


# Alignment control (P1.md, Control) --------------------------------------------------------------

TWIN_TEXTS = ["a", "b", "c", "d", "d", "e"]


def _twin_rows():
    return np.array([_unit(_vec(t)) for t in TWIN_TEXTS])


def test_alignment_passes_on_the_same_vectors_and_accepts_an_identical_twin():
    rows = _twin_rows()
    assert p1.alignment_matched(rows, rows, TWIN_TEXTS) == 6


def test_alignment_fails_under_a_second_pass_shifted_by_one():
    rows = _twin_rows()
    assert p1.alignment_matched(np.roll(rows, -1, axis=0), rows, TWIN_TEXTS) == 1


def test_alignment_fails_under_a_reversed_score_direction():
    rows = _twin_rows()
    assert p1.alignment_matched(-rows, rows, TWIN_TEXTS) == 0


# The whole measurement on a synthetic world -------------------------------------------------------


def test_a_valid_synthetic_run_reports_every_figure_of_the_record():
    stub = Stub(_query_vectors())
    result = _measure(stub)
    texts = list(CHUNKS.values())
    queries = [q for _, q, _ in ITEMS]
    assert list(result) == KEYS
    assert (result["valid"], result["first_failed"], result["failed"]) == (True, None, [])
    assert stub.calls == texts + queries + texts
    assert result["digests"] == DIGESTS and result["environment"] == ENV
    assert result["counts"] == {
        "chunks": 9,
        "distinct_texts": 8,
        "items": 6,
        "positives": 5,
        "chunk_texts_over_max_seq_length": 8,
        "query_texts_over_max_seq_length": 2,
    }
    assert result["alignment"] == {"matched": 9, "required": 9, "bitwise_differences": 0}
    vectors = _query_vectors()
    rows = [_unit(vectors.get(t, _vec(t))) for t in texts + queries]
    assert result["vectors_sha256"] == p1.matrix_sha256(rows)
    assert result["alignment_vectors_sha256"] == p1.matrix_sha256(rows[:9])
    for k in (5, 1):
        block = result[f"k{k}"]
        ps = [1 - Fraction(math.comb(9 - m, k), math.comb(9, k)) for m in (1, 1, 1, 2, 1)]
        chance = _tail(ps, 4)
        assert (block["H_engine"], block["H_bm25"]) == (4, 4)
        assert block["chance"] == {
            "num": chance.numerator,
            "den": chance.denominator,
            "float": float(chance),
            "pass": chance < Fraction(1, 20),
        }
        assert block["mcnemar"] == {
            "b": 1,
            "c": 1,
            "n": 2,
            "num": 3,
            "den": 4,
            "float": 0.75,
            "pass": False,
        }
        assert block["k_pass"] is False
    assert result["holds"] is False
    assert isinstance(result["holds_limit"], str) and result["holds_limit"]
    assert result["bm25_check"] == {"chunks_with_unique_token": 7, "passed": 7}


def test_the_group_sensitivity_counts_each_shared_target_once_and_carries_no_pass_field():
    group = _measure()["group_sensitivity"]
    assert group["units"] == [[1, 6], [2], [3], [4]]
    for k in (5, 1):
        block = group[f"k{k}"]
        p = 1 - Fraction(math.comb(8, k), math.comb(9, k))
        p2 = 1 - Fraction(math.comb(7, k), math.comb(9, k))
        chance = _tail([1 - (1 - p) ** 2, p, p, p2], 3)
        assert (block["H_engine"], block["H_bm25"]) == (3, 3)
        assert block["chance"] == {
            "num": chance.numerator,
            "den": chance.denominator,
            "float": float(chance),
        }
        assert block["mcnemar"] == {"b": 1, "c": 1, "n": 2, "num": 3, "den": 4, "float": 0.75}


def test_the_label_shuffle_is_recomputed_from_the_reported_top_labels():
    result = _measure()
    items = {entry["id"]: entry for entry in result["report_only"]["items"]}
    positives = [1, 2, 3, 4, 6]
    expected = {i: e for i, _, e in ITEMS}
    targets = [{PREFIX + LABEL_OF[a] for a in expected[s]} for s in positives]
    rng = np.random.default_rng(SEED)
    for _ in range(6):
        rng.permutation(9)
    shuffles = [rng.permutation(5).tolist() for _ in range(1000)]
    for k in (5, 1):
        tops = [set(items[s]["engine"]["top5"][:k]) for s in positives]
        counts = sum(
            sum(bool(tops[r] & targets[pi[r]]) for r in range(5)) >= 4 for pi in shuffles
        )
        assert result["shuffle"][f"k{k}"] == {"count": counts, "total": 1000, "fraction": counts / 1000}


def test_the_report_only_figures():
    report = _measure()["report_only"]
    assert list(report) == [
        "items",
        "acros_recovered",
        "bm25_fewer_than_k_positive",
        "nearest_chunk_distance",
        "words_per_chunk",
        "truncation",
        "bitwise_second_pass_differences",
        "citation_fraction",
    ]
    items = {entry["id"]: entry for entry in report["items"]}
    assert sorted(items) == [1, 2, 3, 4, 5, 6]
    assert [items[i]["m"] for i in (1, 2, 3, 4, 5, 6)] == [1, 1, 1, 2, 0, 1]
    assert items[1]["engine"]["position"] == 1 and items[1]["bm25"]["position"] == 1
    assert items[3]["engine"]["position"] == 9 and items[3]["bm25"]["position"] == 1
    assert items[2]["engine"]["position"] == 1 and items[2]["bm25"]["position"] == 9
    assert items[4]["engine"]["position"] == 1 and items[4]["bm25"]["position"] == 1
    assert items[5]["engine"]["position"] is None and items[5]["bm25"]["k5"] is None
    assert items[1]["engine"]["k5"] is True and items[3]["engine"]["k1"] is False
    assert items[2]["bm25"]["k5"] is False and items[3]["bm25"]["k1"] is True
    assert len(items[1]["engine"]["top5"]) == 5
    assert all(label.startswith(PREFIX) for label in items[1]["bm25"]["top5"])
    assert [items[i]["bm25"]["positive_scores"] for i in (1, 2, 3, 4, 5, 6)] == [1, 8, 1, 2, 2, 1]
    assert report["bm25_fewer_than_k_positive"] == {"k5": 4, "k1": 0}
    assert report["acros_recovered"] == {
        "distinct_expected": 5,
        "engine": {"k5": 4, "k1": 3},
        "bm25": {"k5": 4, "k1": 3},
    }
    near = report["nearest_chunk_distance"]
    assert near["n0"]["values"] == [near["n0"]["min"]] and near["n0"]["max"] < 1e-6
    assert len(near["p"]["values"]) == 5 and near["p"]["min"] < 1e-6 and near["p"]["max"] > 1.0
    assert near["p"]["median"] == sorted(near["p"]["values"])[2]
    words = report["words_per_chunk"]
    assert (words["min"], words["median"], words["max"], words["at_most_10"]) == (1, 2.0, 2, 9)
    assert report["truncation"] == {"max_seq_length": 1, "chunk_texts": 8, "query_texts": 2}
    assert report["bitwise_second_pass_differences"] == 0
    assert report["citation_fraction"] == {
        "pairs": 3,
        "within": 1,
        "fraction": 1 / 3,
        "epsilon": 0.8,
    }


# Validity (P1.md, Validity) ----------------------------------------------------------------------

NQ = len(CHUNKS) + len(ITEMS)


def _flip_lowest_bit(u):
    w = u.copy()
    w.view(np.uint32)[0] ^= 1
    return w


def test_a_second_pass_that_differs_by_one_bit_is_counted_and_does_not_invalidate():
    base = _measure()
    stub = Stub(
        _query_vectors(),
        hook=lambda i, t, u: _flip_lowest_bit(u) if i == NQ + 3 else u,
    )
    result = _measure(stub)
    assert result["valid"] is True
    assert result["alignment"] == {"matched": 9, "required": 9, "bitwise_differences": 1}
    assert result["vectors_sha256"] == base["vectors_sha256"]
    assert result["alignment_vectors_sha256"] != base["alignment_vectors_sha256"]
    assert result["report_only"]["bitwise_second_pass_differences"] == 1


def test_a_second_pass_shifted_by_one_fails_v2_and_nulls_every_decision_only():
    texts = list(CHUNKS.values())
    stub = Stub(
        _query_vectors(),
        hook=lambda i, t, u: _vec(texts[(i - NQ + 1) % 9]) if i >= NQ else u,
    )
    result = _measure(stub)
    assert (result["valid"], result["first_failed"], result["failed"]) == (False, "V2", ["V2"])
    assert result["alignment"]["matched"] < 9 and result["alignment"]["required"] == 9
    assert result["holds"] is None
    for k in (5, 1):
        block = result[f"k{k}"]
        assert block["k_pass"] is None
        assert block["chance"]["pass"] is None and block["mcnemar"]["pass"] is None
        assert block["H_engine"] == 4 and block["chance"]["num"] > 0
    assert result["group_sensitivity"] is not None and result["shuffle"] is not None
    assert result["holds_limit"]
    json.dumps(result, allow_nan=False)


def test_an_invalid_vector_fails_v1_and_v2_and_nulls_every_vector_derived_figure():
    result = _measure(Stub(_query_vectors(), hook=lambda i, t, u: np.zeros(DIM, np.float32) if i == 1 else u))
    assert list(result) == KEYS
    assert (result["valid"], result["first_failed"], result["failed"]) == (False, "V1", ["V1", "V2"])
    assert result["holds"] is None and result["holds_limit"]
    assert result["vectors_sha256"] is None and result["alignment_vectors_sha256"] is None
    assert result["alignment"] == {"matched": None, "required": 9, "bitwise_differences": None}
    for k in (5, 1):
        assert result[f"k{k}"] == {
            "H_engine": None,
            "H_bm25": 4,
            "chance": None,
            "mcnemar": None,
            "k_pass": None,
        }
    assert result["shuffle"] is None and result["group_sensitivity"] is None
    report = result["report_only"]
    assert report["nearest_chunk_distance"] is None and report["citation_fraction"] is None
    assert report["bitwise_second_pass_differences"] is None
    assert report["acros_recovered"]["engine"] is None
    assert report["acros_recovered"]["bm25"] == {"k5": 4, "k1": 3}
    first = {entry["id"]: entry for entry in report["items"]}[1]
    assert first["engine"] == {"position": None, "top5": None, "k5": None, "k1": None}
    assert first["bm25"]["position"] == 1
    assert result["bm25_check"] == {"chunks_with_unique_token": 7, "passed": 7}
    json.dumps(result, allow_nan=False)


def test_the_writer_refuses_nan_and_infinity_and_writes_nothing(tmp_path):
    for bad in (float("nan"), float("inf"), float("-inf")):
        path = tmp_path / "bad.json"
        with pytest.raises(ValueError):
            p1.write_result({"x": [bad]}, path)
        assert not path.exists()


def test_the_writer_keeps_key_order_utf8_two_space_indent_and_a_final_newline(tmp_path):
    path = tmp_path / "out.json"
    p1.write_result({"b": 1, "a": "é", "c": {"d": [1, 2]}}, path)
    expected = '{\n  "b": 1,\n  "a": "é",\n  "c": {\n    "d": [\n      1,\n      2\n    ]\n  }\n}\n'
    assert path.read_bytes() == expected.encode("utf-8")


# The real provider (model partition) -------------------------------------------------------------


@pytest.mark.model
def test_the_real_encoder_sits_on_the_cpu_after_load_encoder():
    from traianus.representation.sentence_transformer import (
        MODEL_REVISION,
        SentenceTransformerProvider,
        build_encoder,
    )

    model = p1.load_encoder(build_encoder, MODEL_REVISION)
    assert str(model.device) == "cpu"
    assert model.max_seq_length > 0 and len(model.tokenizer("a statement")["input_ids"]) > 2
    assert p1.unit_vector(SentenceTransformerProvider().encode("a statement")).shape == (DIM,)
