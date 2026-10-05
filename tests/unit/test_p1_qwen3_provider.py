"""Unit tests of tools/experiments/p1_qwen3_provider.py.

Specification: docs/roadmap/NEXT_RESEARCH.md ("Línea base de proveedor: Qwen3-Embedding-0.6B", frozen at
8cfebc5). Synthetic inputs and fake encoders only: CI has no weights, and the measurement is never run on
the real files here. The real test set and the committed P1 result are read, never encoded.
"""

import hashlib
import itertools
import json
import math
import platform
import zlib
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from tools.experiments import p1_beezer_retrieval as p1
from tools.experiments import p1_qwen3_provider as q3

FULL = 1024
SMALL = 384
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
ITEMS = [
    (1, "alphaw", ["A"]),
    (2, "common", ["B"]),
    (3, "gammaw", ["C"]),
    (4, "deltaw epsw", ["D", "E"]),
    (5, "thetaw", []),
    (6, "alphaw again", ["A"]),
]
CITATIONS = [[PREFIX + "THM_H", PREFIX + "THM_I"], [PREFIX + "DEF_A", PREFIX + "DEF_B"]]
NAMES = {
    "manifest": "beezer_manifest.json",
    "test_set": "pilot1_test_set.json",
    "citations": "beezer_citations.json",
}
MINILM_NAME = "P1_result.json"
EMPTIED = (1, 2)
KEPT = (3, 4, 6)
POSITIVES = [1, 2, 3, 4, 6]
TEXTS = list(CHUNKS.values())
QUERIES = [query for _, query, _ in ITEMS]
INSTRUCTION = (
    "Instruct: Given a description of a mathematical concept, retrieve the definition or theorem that states it\nQuery:"
)
VERSIONS = {"1024": FULL, "384": SMALL}
P1_ENVIRONMENT_KEYS = [
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
REAL_DATA = Path(__file__).resolve().parents[2] / "data" / "math"


def _vec(text, size=FULL):
    return np.random.default_rng(zlib.crc32(text.encode("utf-8"))).standard_normal(size).astype(np.float32)


def _unit(u):
    u = u.astype(np.float64)
    return u / np.linalg.norm(u)


def _chunk(suffix):
    return _vec(CHUNKS[suffix])


def _query_vectors():
    """Instructed queries whose outcome is fixed; the plain query of item 1 points at another chunk."""
    both = (_unit(_chunk("DEF_D")) + _unit(_chunk("THM_E"))).astype(np.float32)
    return {
        INSTRUCTION + "alphaw": _chunk("DEF_A"),
        INSTRUCTION + "common": _chunk("DEF_B"),
        INSTRUCTION + "gammaw": -_chunk("DEF_C"),
        INSTRUCTION + "deltaw epsw": both,
        INSTRUCTION + "thetaw": _chunk("THM_H"),
        INSTRUCTION + "alphaw again": _chunk("DEF_A"),
        "alphaw": _chunk("DEF_C"),
    }


OUTPUTS = _query_vectors()


def _output(text):
    return OUTPUTS.get(text, _vec(text))


class FakeQwen:
    """Stands for the SentenceTransformer: records every encoder input; ``hook`` may alter an output."""

    max_seq_length = 1

    def __init__(self, dtypes=("torch.float32",), device="cpu", hook=None):
        self.dtypes, self.device, self.hook, self.calls = dtypes, device, hook, []

    def to(self, device):
        return self

    def parameters(self):
        return iter([SimpleNamespace(dtype=dtype) for dtype in self.dtypes])

    def __getitem__(self, index):
        config = SimpleNamespace(_attn_implementation="eager")
        return SimpleNamespace(auto_model=SimpleNamespace(config=config))

    def tokenizer(self, text):
        return {"input_ids": text.split()}

    def encode(self, text):
        index = len(self.calls)
        self.calls.append(text)
        u = _output(text)
        return u if self.hook is None else self.hook(index, text, u)


class MiniLmStub:
    def encode(self, text):
        return _vec(text, SMALL)


class Tick:
    """A clock that advances one millisecond per reading."""

    def __init__(self):
        self.now = 0

    def __call__(self):
        self.now += 1_000_000
        return self.now


class Uneven:
    """A clock whose k-th timed call lasts 1 + k % 10 milliseconds (two readings per call)."""

    def __init__(self):
        self.now, self.reads = 0, 0

    def __call__(self):
        self.reads += 1
        if self.reads % 2 == 0:
            self.now += 1_000_000 * (1 + (self.reads // 2) % 10)
        return self.now


def _raw():
    items = [
        {"id": i, "name": "n", "prose_es": "es", "prose_en": q, "expected": e} for i, q, e in reversed(ITEMS)
    ]
    return {
        "manifest": json.dumps({PREFIX + key: text for key, text in CHUNKS.items()}).encode("utf-8"),
        "test_set": json.dumps({"pilot": "synthetic", "items": items}).encode("utf-8"),
        "citations": json.dumps(CITATIONS).encode("utf-8"),
    }


def _minilm_doc():
    """What P1 writes for the synthetic world, from a 384-dimensional stub: the stored MiniLM arm."""
    inp = p1.parse_inputs(_raw())
    return p1.measure(inp, p1.resolve_acros(inp), MiniLmStub(), FakeQwen(), {"device": "cpu"}, {})


def _bytes(doc):
    return (json.dumps(doc, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _mutated(change):
    doc = _minilm_doc()
    change(doc)
    return _bytes(doc)


def _world(directory, minilm=None):
    raw = _raw()
    paths = {}
    for key, data in raw.items():
        paths[key] = directory / NAMES[key]
        paths[key].write_bytes(data)
    stored = _bytes(_minilm_doc()) if minilm is None else minilm
    (directory / MINILM_NAME).write_bytes(stored)
    digests = {key: hashlib.sha256(data).hexdigest() for key, data in raw.items()}
    return paths, digests, directory / MINILM_NAME, hashlib.sha256(stored).hexdigest()


def _run(
    directory, *, minilm=None, minilm_digest=None, qwen=None, emptied=EMPTIED, kept=KEPT, epsilon=0.8, clock=None
):
    paths, digests, minilm_path, own = _world(directory, minilm)
    qwen = FakeQwen() if qwen is None else qwen
    out, timing = directory / "P1_qwen3_result.json", directory / "P1_qwen3_timing.json"
    code = q3.run(
        out,
        timing,
        paths,
        digests,
        minilm_path,
        minilm_digest or own,
        lambda: epsilon,
        lambda: qwen,
        emptied=emptied,
        kept=kept,
        clock=clock or Tick(),
    )
    return code, out, timing, qwen


def _result(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _only_inputs(directory):
    return sorted(p.name for p in directory.glob("*.json")) == sorted([*NAMES.values(), MINILM_NAME])


@pytest.fixture
def ran(tmp_path):
    code, out, timing, qwen = _run(tmp_path)
    assert code == 0
    return _result(out), _minilm_doc(), qwen, out, timing


def _engine_positions(block):
    items = block["report_only"]["p1_measurement"]["report_only"]["items"]
    return {item["id"]: item["engine"]["position"] for item in items if item["m"]}


def _bm25_positions(block):
    items = block["report_only"]["p1_measurement"]["report_only"]["items"]
    return {item["id"]: item["bm25"]["position"] for item in items if item["m"]}


def _minilm_positions(doc):
    return {item["id"]: item["engine"]["position"] for item in doc["report_only"]["items"] if item["m"]}


# Wilcoxon (decision) ----------------------------------------------------------------------------


def _brute(d):
    """Midranks by their definition, and the p by enumeration of every sign assignment."""
    d = [x for x in d if x != 0]
    absolute = [abs(x) for x in d]
    ranks = [
        Fraction(sum(a < x for a in absolute)) + Fraction(sum(a == x for a in absolute) + 1, 2) for x in absolute
    ]
    observed = sum(r for r, x in zip(ranks, d, strict=True) if x > 0)
    count = sum(
        sum(r for r, s in zip(ranks, signs, strict=True) if s) >= observed
        for signs in itertools.product((False, True), repeat=len(d))
    )
    return Fraction(count, 2 ** len(d)), observed


def test_wilcoxon_all_positive_n_4_gives_one_sixteenth():
    w = q3.wilcoxon([1, 2, 3, 4])
    assert (w["n"], w["dropped_zeros"]) == (4, 0)
    assert (w["w_plus"], w["w_minus"], w["p"]) == (10, 0, Fraction(1, 16))


def test_wilcoxon_a_tie_among_the_absolute_values_takes_midranks():
    # |d| = 3, 3, 5, 1, 2 rank 3.5, 3.5, 5, 1, 2; W+ = 3.5 + 5 + 2; 8 of the 32 sign assignments reach it.
    w = q3.wilcoxon([3, -3, 5, -1, 2])
    assert (w["w_plus"], w["w_minus"], w["p"]) == (Fraction(21, 2), Fraction(9, 2), Fraction(1, 4))


def test_wilcoxon_drops_the_zeros_and_counts_them():
    w = q3.wilcoxon([0, 0, 1, 2, 3, 4])
    assert (w["n"], w["dropped_zeros"], w["p"]) == (4, 2, Fraction(1, 16))


@pytest.mark.parametrize("d", [[], [0, 0, 0]])
def test_wilcoxon_with_nothing_left_has_p_one_and_does_not_pass(d):
    w = q3.wilcoxon(d)
    assert (w["n"], w["w_plus"], w["w_minus"], w["p"]) == (0, 0, 0, 1)
    assert q3.wilcoxon_pass(w["p"], True) is False


def test_wilcoxon_passes_only_strictly_below_one_twentieth_and_only_when_valid():
    assert q3.wilcoxon_pass(q3.wilcoxon([1, 2, 3, 4, 5])["p"], True) is True
    assert q3.wilcoxon_pass(q3.wilcoxon([1, 2, 3, 4])["p"], True) is False
    assert q3.wilcoxon_pass(Fraction(1, 20) - Fraction(1, 10**30), True) is True
    assert q3.wilcoxon_pass(Fraction(1, 20), True) is False
    assert q3.wilcoxon_pass(Fraction(1, 32), False) is None


def test_wilcoxon_agrees_with_enumeration_on_seeded_small_inputs_with_ties_and_zeros():
    rng = np.random.default_rng(20261004)
    for _ in range(200):
        d = rng.integers(-5, 6, size=int(rng.integers(0, 9))).tolist()
        p, observed = _brute(d)
        w = q3.wilcoxon(d)
        assert (w["p"], w["w_plus"]) == (p, observed)
        assert w["n"] == len(d) - d.count(0) and w["dropped_zeros"] == d.count(0)
        assert w["w_plus"] + w["w_minus"] == Fraction(w["n"] * (w["n"] + 1), 2)


# Report-only figures ------------------------------------------------------------------------------


def test_mcnemar_against_minilm_counts_qwen3_only_hits_as_b():
    record = q3.mcnemar_against([True, True, False, False, True], [True, False, True, False, False])
    assert (record["b"], record["c"], record["n"]) == (2, 1, 3)
    assert (record["num"], record["den"], record["float"]) == (1, 2, 0.5)


def test_rank_metrics_on_a_hand_example():
    m = q3.rank_metrics([1, 2, 4, 12, 25])
    assert m["mrr"] == pytest.approx(281 / 750, abs=1e-12)
    assert (m["recall_10"], m["recall_20"], m["median_position"]) == (0.6, 0.8, 4)
    assert q3.rank_metrics([1, 3, 5, 9])["median_position"] == 4.0
    assert q3.rank_metrics([10, 20])["recall_10"] == 0.5 and q3.rank_metrics([10, 20])["recall_20"] == 1.0


def test_auc_counts_a_tie_as_one_half():
    assert q3.auc([1, 2, 3], [2, 4]) == Fraction(3, 4)
    assert q3.auc([1.0, 1.0], [1.0]) == Fraction(1, 2)
    assert q3.auc([1, 2], [3, 4]) == 1 and q3.auc([3, 4], [1, 2]) == 0


# Formula split (B8) -----------------------------------------------------------------------------


def test_the_frozen_split_ids():
    assert q3.EMPTIED == (1, 2, 6, 7, 13, 15, 18, 23, 24, 25, 28)
    assert q3.KEPT == (11, 12, 14, 16, 17, 21, 27)


def test_the_frozen_split_is_exactly_the_positive_items_of_the_real_test_set():
    items = json.loads((REAL_DATA / "pilot1_test_set.json").read_text(encoding="utf-8"))["items"]
    positives = [item["id"] for item in items if item["expected"]]
    q3.split_check(positives, q3.EMPTIED, q3.KEPT)
    assert sorted([*q3.EMPTIED, *q3.KEPT]) == sorted(positives)


@pytest.mark.parametrize(
    "emptied, kept",
    [((1, 2), (3, 4)), ((1, 2), (3, 4, 6, 7)), ((1, 2, 3), (3, 4, 6)), ((1, 2, 5), (3, 4, 6))],
)
def test_the_split_refuses_unless_its_disjoint_union_is_the_positive_ids(emptied, kept):
    with pytest.raises(p1.Refusal) as caught:
        q3.split_check(POSITIVES, emptied, kept)
    assert caught.value.identifier == "RF7"


def test_the_split_accepts_the_disjoint_union():
    q3.split_check(POSITIVES, EMPTIED, KEPT)


# Provider (RF5) ---------------------------------------------------------------------------------


def test_the_pinned_provider_and_the_query_instruction_are_byte_exact():
    assert q3.MODEL_ID == "Qwen/Qwen3-Embedding-0.6B"
    assert q3.QWEN_REVISION == "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3"
    assert q3.INSTRUCTION == INSTRUCTION
    assert q3.INSTRUCTION.endswith("states it\nQuery:") and q3.INSTRUCTION.count("\n") == 1


def test_the_loader_accepts_the_pinned_float32_cpu_encoder():
    model = FakeQwen()
    assert q3.load_qwen3(lambda: model, q3.QWEN_REVISION) is model


@pytest.mark.parametrize(
    "kwargs",
    [
        {"dtypes": ("torch.bfloat16",)},
        {"dtypes": ("torch.float32", "torch.bfloat16")},
        {"dtypes": ("torch.float16",)},
        {"device": "mps"},
    ],
)
def test_rf5_an_encoder_with_a_non_float32_parameter_or_off_the_cpu_is_refused(kwargs):
    with pytest.raises(p1.Refusal) as caught:
        q3.load_qwen3(lambda: FakeQwen(**kwargs), q3.QWEN_REVISION)
    assert caught.value.identifier == "RF5"


def test_rf5_another_revision_is_refused_and_an_encoder_that_does_not_load_offline_is_refused():
    with pytest.raises(p1.Refusal) as caught:
        q3.load_qwen3(lambda: FakeQwen(), p1.PINNED_REVISION)
    assert caught.value.identifier == "RF5"

    def not_cached():
        raise OSError("not in the local cache")

    with pytest.raises(p1.Refusal) as caught:
        q3.load_qwen3(not_cached, q3.QWEN_REVISION)
    assert caught.value.identifier == "RF5"


def test_the_builder_loads_offline_on_the_cpu_in_float32_with_eager_attention(monkeypatch):
    import sentence_transformers
    import torch

    calls = []

    def fake(*args, **kwargs):
        calls.append((args, kwargs))
        return "model"

    monkeypatch.setattr(sentence_transformers, "SentenceTransformer", fake)
    assert q3.build_qwen3() == "model"
    assert calls == [
        (
            ("Qwen/Qwen3-Embedding-0.6B",),
            {
                "revision": "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3",
                "local_files_only": True,
                "device": "cpu",
                "model_kwargs": {"dtype": torch.float32, "attn_implementation": "eager"},
            },
        )
    ]


# Guard: P1 does not change (T12) ------------------------------------------------------------------


def test_p1_keeps_its_constants_and_its_default_behaviour():
    assert p1.DIM == 384 and p1.PINNED_REVISION == "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
    assert p1.RESULT.name == MINILM_NAME and p1.RESULT.parent.name == "math"
    assert p1.unit_vector(_vec("x", SMALL)).shape == (SMALL,)
    with pytest.raises(p1.InvalidVector):
        p1.unit_vector(_vec("x", FULL))


def test_the_pinned_minilm_digest_is_that_of_the_committed_p1_result():
    assert q3.MINILM_SHA256 == hashlib.sha256((REAL_DATA / MINILM_NAME).read_bytes()).hexdigest()


def test_the_output_paths_default_to_data_math():
    assert q3.RESULT == REAL_DATA / "P1_qwen3_result.json"
    assert q3.TIMING == REAL_DATA / "P1_qwen3_timing.json"


# Refusals before any encoding (B1) ----------------------------------------------------------------


def _refused(directory, capsys, identifier, **kwargs):
    code, _, _, qwen = _run(directory, **kwargs)
    assert code == 1 and capsys.readouterr().err.startswith(identifier)
    assert _only_inputs(directory)
    return qwen


BAD_MINILM = {
    "not_json": lambda: b"{not json",
    "not_an_object": lambda: b"[]",
    "duplicate_key": lambda: b'{"valid": true, "valid": true}',
    "nan": lambda: b'{"valid": true, "x": NaN}',
    "invalid": lambda: _mutated(lambda d: d.update(valid=False)),
    "valid_missing": lambda: _mutated(lambda d: d.pop("valid")),
    "valid_not_true": lambda: _mutated(lambda d: d.update(valid=1)),
    "no_report": lambda: _mutated(lambda d: d.pop("report_only")),
    "item_missing": lambda: _mutated(lambda d: d["report_only"]["items"].pop()),
    "no_distances": lambda: _mutated(lambda d: d["report_only"].pop("nearest_chunk_distance")),
}


@pytest.mark.parametrize("name", list(BAD_MINILM))
def test_rf6_a_minilm_arm_that_does_not_parse_or_is_not_valid_refuses(tmp_path, capsys, name):
    _refused(tmp_path, capsys, "RF6", minilm=BAD_MINILM[name]())


def test_rf6_a_wrong_minilm_digest_refuses_and_writes_nothing(tmp_path, capsys):
    qwen = _refused(tmp_path, capsys, "RF6", minilm_digest="0" * 64)
    assert qwen.calls == []


def test_rf6_one_flipped_bit_in_the_minilm_file_refuses(tmp_path, capsys):
    paths, digests, minilm_path, own = _world(tmp_path)
    data = bytearray(minilm_path.read_bytes())
    data[len(data) // 2] ^= 0x01
    minilm_path.write_bytes(bytes(data))
    out, timing = tmp_path / "r.json", tmp_path / "t.json"
    code = q3.run(out, timing, paths, digests, minilm_path, own, lambda: 0.8, FakeQwen, emptied=EMPTIED, kept=KEPT)
    assert code == 1 and capsys.readouterr().err.startswith("RF6") and not out.exists() and not timing.exists()


def test_rf7_the_split_not_covering_the_positive_items_refuses(tmp_path, capsys):
    _refused(tmp_path, capsys, "RF7", kept=(3, 4))


def test_rf1_a_wrong_input_digest_and_rf4_a_wrong_epsilon_refuse(tmp_path, capsys):
    paths, digests, minilm_path, own = _world(tmp_path)
    digests["manifest"] = "0" * 64
    args = (tmp_path / "r.json", tmp_path / "t.json", paths, digests, minilm_path, own)
    assert q3.run(*args, lambda: 0.8, FakeQwen, emptied=EMPTIED, kept=KEPT) == 1
    assert capsys.readouterr().err.startswith("RF1")
    digests["manifest"] = hashlib.sha256(paths["manifest"].read_bytes()).hexdigest()
    assert q3.run(*args, lambda: 0.5, FakeQwen, emptied=EMPTIED, kept=KEPT) == 1
    assert capsys.readouterr().err.startswith("RF4")
    assert _only_inputs(tmp_path)


def test_rf5_an_encoder_not_in_float32_refuses_through_run(tmp_path, capsys):
    qwen = _refused(tmp_path, capsys, "RF5", qwen=FakeQwen(dtypes=("torch.bfloat16",)))
    assert qwen.calls == []


# The run: instruction, versions, V3 (B2, B3, B10) ---------------------------------------------------


def test_the_instruction_goes_on_the_queries_only_and_every_call_is_one_text(ran):
    result, _, qwen, _, _ = ran
    assert qwen.calls == [*TEXTS, *[INSTRUCTION + q for q in QUERIES], *TEXTS, *QUERIES]
    assert result["valid"] is True and result["failed"] == []


def test_bm25_sees_the_query_without_the_instruction(ran):
    result, doc, _, _, _ = ran
    assert result["bm25_vs_minilm_result"] == {"items": 6, "mismatched_ids": []}
    stored = [item["bm25"] for item in doc["report_only"]["items"]]
    for block in result["versions"].values():
        ours = [item["bm25"] for item in block["report_only"]["p1_measurement"]["report_only"]["items"]]
        assert ours == stored


def test_the_result_keys_in_order(ran):
    result = ran[0]
    assert list(result) == [
        "valid",
        "first_failed",
        "failed",
        "decides",
        "digests",
        "environment",
        "bm25_vs_minilm_result",
        "versions",
        "report_only",
    ]
    assert list(result["versions"]) == ["1024", "384"]
    for block in result["versions"].values():
        assert list(block) == ["dimension", "valid", "first_failed", "failed", "wilcoxon", "report_only"]
        assert list(block["report_only"]) == [
            "p1_measurement",
            "mcnemar_vs_minilm",
            "rank_metrics",
            "no_instruction",
            "auc",
            "split",
        ]


def test_the_environment_adds_the_provider_fields_to_p1s(ran):
    result, doc, _, _, _ = ran
    env = result["environment"]
    assert list(env) == [
        *P1_ENVIRONMENT_KEYS,
        "transformers",
        "model_id",
        "revision",
        "parameter_dtype",
        "attention_implementation",
        "instruction",
        "minilm_result_sha256",
    ]
    assert env["model_id"] == "Qwen/Qwen3-Embedding-0.6B" and env["revision"] == q3.QWEN_REVISION
    assert env["parameter_dtype"] == "torch.float32" and env["attention_implementation"] == "eager"
    assert env["instruction"] == INSTRUCTION and env["device"] == "cpu"
    assert env["minilm_result_sha256"] == hashlib.sha256(_bytes(doc)).hexdigest()


def test_truncation_counts_the_queries_with_the_instruction(ran):
    result = ran[0]
    for block in result["versions"].values():
        measured = block["report_only"]["p1_measurement"]
        assert measured["counts"]["query_texts_over_max_seq_length"] == 6
        assert measured["report_only"]["truncation"]["query_texts"] == 6
        assert measured["counts"]["chunk_texts_over_max_seq_length"] == 8


def test_the_1024_and_384_versions_are_the_float32_output_and_its_first_384_components(ran):
    result = ran[0]
    first = [*TEXTS, *[INSTRUCTION + q for q in QUERIES]]

    def sha(rows):
        return hashlib.sha256(np.array(rows, dtype="<f8", order="C").tobytes()).hexdigest()

    for name, size in VERSIONS.items():
        measured = result["versions"][name]["report_only"]["p1_measurement"]
        assert result["versions"][name]["dimension"] == size
        assert measured["vectors_sha256"] == sha([_unit(_output(t)[:size]) for t in first])
        assert measured["alignment_vectors_sha256"] == sha([_unit(_output(t)[:size]) for t in TEXTS])
        assert measured["valid"] is True and measured["alignment"]["bitwise_differences"] == 0
    sha_1024 = result["versions"]["1024"]["report_only"]["p1_measurement"]["vectors_sha256"]
    sha_384 = result["versions"]["384"]["report_only"]["p1_measurement"]["vectors_sha256"]
    assert sha_1024 != sha_384


def _failing(tmp_path, hook):
    code, out, _, _ = _run(tmp_path, qwen=FakeQwen(hook=hook))
    assert code == 0
    return _result(out)


def test_v1_an_output_of_the_wrong_size_fails_both_versions_and_nulls_the_decision(tmp_path):
    result = _failing(tmp_path, lambda i, t, u: u[:SMALL])
    assert result["valid"] is False and result["first_failed"] == "1024:V1"
    for block in result["versions"].values():
        assert block["valid"] is False and block["failed"] == ["V1", "V2"]
        assert block["wilcoxon"]["pass"] is None and block["report_only"]["p1_measurement"]["holds"] is None
        assert block["report_only"]["no_instruction"] is None


def test_v1_a_non_finite_component_beyond_the_384_fails_the_1024_version_only(tmp_path):
    def hook(index, text, u):
        if index == 0:
            u = u.copy()
            u[500] = np.nan
        return u

    result = _failing(tmp_path, hook)
    assert result["versions"]["1024"]["valid"] is False and result["versions"]["1024"]["failed"][0] == "V1"
    assert result["versions"]["384"]["valid"] is True
    assert result["versions"]["384"]["wilcoxon"]["pass"] in (True, False)
    assert result["valid"] is False and result["failed"] == ["1024:V1", "1024:V2"]


def test_v1_a_float64_output_fails_both_versions(tmp_path):
    result = _failing(tmp_path, lambda i, t, u: u.astype(np.float64))
    assert [b["valid"] for b in result["versions"].values()] == [False, False]


def test_v2_the_second_pass_differing_from_the_first_is_counted_and_fails_alignment(tmp_path):
    seen = {}

    def hook(index, text, u):
        seen[text] = seen.get(text, 0) + 1
        return -u if text == CHUNKS["DEF_B"] and seen[text] == 2 else u

    result = _failing(tmp_path, hook)
    for block in result["versions"].values():
        measured = block["report_only"]["p1_measurement"]
        assert measured["alignment"]["bitwise_differences"] == 1 and block["failed"] == ["V2"]
        assert block["wilcoxon"]["pass"] is None


@pytest.mark.parametrize("field", ["position", "top5"])
def test_v3_a_stored_bm25_that_differs_from_the_recomputed_one_invalidates_without_a_decision(tmp_path, field):
    def change(doc):
        arm = doc["report_only"]["items"][0]["bm25"]
        if field == "position":
            arm["position"] += 1
        else:
            arm["top5"][0], arm["top5"][1] = arm["top5"][1], arm["top5"][0]

    code, out, _, _ = _run(tmp_path, minilm=_mutated(change))
    result = _result(out)
    assert code == 0 and result["valid"] is False and result["failed"] == ["V3"] and result["first_failed"] == "V3"
    assert result["bm25_vs_minilm_result"] == {"items": 6, "mismatched_ids": [1]}
    for block in result["versions"].values():
        measured = block["report_only"]["p1_measurement"]
        assert block["valid"] is False and block["failed"] == ["V3"] and block["wilcoxon"]["pass"] is None
        assert measured["holds"] is None and measured["valid"] is False
        assert measured["k5"]["k_pass"] is None and measured["k5"]["chance"]["pass"] is None
        assert measured["k1"]["mcnemar"]["pass"] is None


# The decision and the report-only blocks on the synthetic world (B4-B9) ----------------------------


def test_the_wilcoxon_block_pairs_the_positive_items_as_minilm_minus_qwen3(ran):
    result, doc, _, _, _ = ran
    minilm = _minilm_positions(doc)
    for block in result["versions"].values():
        qwen = _engine_positions(block)
        w = block["wilcoxon"]
        pairs = [{"id": i, "minilm": minilm[i], "qwen3": qwen[i], "d": minilm[i] - qwen[i]} for i in POSITIVES]
        assert w["pairs"] == pairs
        p, observed = _brute([minilm[i] - qwen[i] for i in POSITIVES])
        assert (w["p"]["num"], w["p"]["den"]) == (p.numerator, p.denominator)
        assert w["w_plus"] == float(observed) and w["n"] + w["dropped_zeros"] == 5
        assert w["pass"] is (p < Fraction(1, 20))


def test_mcnemar_against_minilm_on_the_run_takes_qwen3_as_the_engine(ran):
    result, doc, _, _, _ = ran
    minilm = _minilm_positions(doc)
    for block in result["versions"].values():
        qwen = _engine_positions(block)
        for k in (5, 1):
            b = sum(qwen[i] <= k < minilm[i] for i in POSITIVES)
            c = sum(minilm[i] <= k < qwen[i] for i in POSITIVES)
            n = b + c
            p = Fraction(sum(math.comb(n, j) for j in range(b, n + 1)), 2**n)
            assert block["report_only"]["mcnemar_vs_minilm"][f"k{k}"] == {
                "b": b,
                "c": c,
                "n": n,
                "num": p.numerator,
                "den": p.denominator,
                "float": float(p),
            }


def test_rank_metrics_per_arm_come_from_the_arms_own_positions(ran):
    result, doc, _, _, _ = ran
    minilm = [_minilm_positions(doc)[i] for i in POSITIVES]
    for block in result["versions"].values():
        metrics = block["report_only"]["rank_metrics"]
        assert list(metrics) == ["minilm", "qwen3", "bm25"]
        qwen = [_engine_positions(block)[i] for i in POSITIVES]
        bm25 = [_bm25_positions(block)[i] for i in POSITIVES]
        for name, positions in (("minilm", minilm), ("qwen3", qwen), ("bm25", bm25)):
            assert metrics[name]["mrr"] == pytest.approx(math.fsum(1 / p for p in positions) / 5, abs=1e-12)
            assert metrics[name]["recall_10"] == sum(p <= 10 for p in positions) / 5
            assert metrics[name]["recall_20"] == sum(p <= 20 for p in positions) / 5
            assert metrics[name]["median_position"] == float(np.median(positions))


def _plain_position(size):
    """Position of chunk A for item 1 when its query goes in without the instruction (it points at chunk C)."""
    chunks = [_unit(_vec(text)[:size]) for text in TEXTS]
    query = _unit(_vec(CHUNKS["DEF_C"])[:size])
    scores = [float(np.dot(query, c)) for c in chunks]
    return 1 + sum(s > scores[0] for s in scores)


def test_the_query_without_instruction_is_ranked_against_the_first_pass_chunk_vectors(ran):
    result = ran[0]
    for name, size in VERSIONS.items():
        block = result["versions"][name]
        assert _engine_positions(block)[1] == 1
        plain = block["report_only"]["no_instruction"]
        assert list(plain) == ["items", "H_k5", "H_k1", "rank_metrics"]
        assert [item["id"] for item in plain["items"]] == POSITIVES
        position = _plain_position(size)
        assert plain["items"][0] == {"id": 1, "position": position, "k5": position <= 5, "k1": position <= 1}
        assert plain["H_k5"] == sum(item["k5"] for item in plain["items"])
        assert plain["H_k1"] == sum(item["k1"] for item in plain["items"])
        assert plain["rank_metrics"] == q3.rank_metrics([item["position"] for item in plain["items"]])


def _auc(positive, none):
    wins = sum((p < n) + Fraction(p == n, 2) for p in positive for n in none)
    return wins / (len(positive) * len(none))


def _record(fraction):
    return {"num": fraction.numerator, "den": fraction.denominator, "float": float(fraction)}


def test_auc_separates_p_from_none_with_the_nearest_chunk_distances_of_each_model(ran):
    result, doc, _, _, _ = ran
    stored = doc["report_only"]["nearest_chunk_distance"]
    assert result["report_only"]["minilm_auc"] == _record(_auc(stored["p"]["values"], stored["n0"]["values"]))
    for block in result["versions"].values():
        distances = block["report_only"]["p1_measurement"]["report_only"]["nearest_chunk_distance"]
        expected = _auc(distances["p"]["values"], distances["n0"]["values"])
        assert block["report_only"]["auc"] == _record(expected)


def test_the_formula_split_reports_hits_median_and_mrr_per_arm(ran):
    result, doc, _, _, _ = ran
    minilm = _minilm_positions(doc)
    for block in result["versions"].values():
        split = block["report_only"]["split"]
        assert split["source"].startswith("taken from P1's post-result reading")
        arms = {"minilm": minilm, "qwen3": _engine_positions(block), "bm25": _bm25_positions(block)}
        for group, ids in (("emptied", EMPTIED), ("kept", KEPT)):
            assert split[group]["ids"] == list(ids)
            for arm, positions in arms.items():
                values = [positions[i] for i in ids]
                assert split[group]["arms"][arm] == {
                    "hits_k5": sum(p <= 5 for p in values),
                    "hits_k1": sum(p <= 1 for p in values),
                    "median_position": float(np.median(values)),
                    "mrr": pytest.approx(math.fsum(1 / p for p in values) / len(values), abs=1e-12),
                }


def test_the_item_by_item_block_lists_every_arm(ran):
    result, doc, _, _, _ = ran
    minilm = _minilm_positions(doc)
    rows = result["report_only"]["items"]
    assert [row["id"] for row in rows] == POSITIVES
    for row in rows:
        assert row["minilm_position"] == minilm[row["id"]]
        assert list(row["versions"]) == ["1024", "384"]
        for name, entry in row["versions"].items():
            block = result["versions"][name]
            assert list(entry) == ["position", "top5", "no_instruction_position"]
            assert entry["position"] == _engine_positions(block)[row["id"]] and len(entry["top5"]) == 5
            plain = {item["id"]: item["position"] for item in block["report_only"]["no_instruction"]["items"]}
            assert entry["no_instruction_position"] == plain[row["id"]]
    bm25 = {item["id"]: item["bm25"]["position"] for item in doc["report_only"]["items"]}
    assert [row["bm25_position"] for row in rows] == [bm25[i] for i in POSITIVES]


# Output files (B11, B12) -----------------------------------------------------------------------------


def test_two_runs_with_the_same_fake_provider_write_a_byte_identical_result(tmp_path):
    first, second = tmp_path / "a", tmp_path / "b"
    first.mkdir()
    second.mkdir()
    _, out_a, _, _ = _run(first)
    _, out_b, _, _ = _run(second, clock=Uneven())
    assert out_a.read_bytes() == out_b.read_bytes()
    assert out_a.read_text(encoding="utf-8").endswith("}\n")


def test_the_result_holds_no_timing_and_the_timing_file_holds_only_timings(ran):
    _, _, _, out, timing = ran
    text = out.read_text(encoding="utf-8")
    assert "p50" not in text and "p95" not in text and "ru_maxrss" not in text
    data = _result(timing)
    assert list(data) == ["chunk_calls", "query_calls", "peak_resident_memory"]
    assert data["chunk_calls"] == {"count": 18, "p50_ms": 1.0, "p95_ms": 1.0}
    assert data["query_calls"] == {"count": 12, "p50_ms": 1.0, "p95_ms": 1.0}
    memory = data["peak_resident_memory"]
    assert list(memory) == ["ru_maxrss", "unit", "platform"] and memory["ru_maxrss"] > 0
    assert memory["platform"] == platform.system()
    assert memory["unit"] == ("bytes" if platform.system() == "Darwin" else "kilobytes")


def test_the_timing_percentiles_are_over_the_calls_of_each_kind(tmp_path):
    # Call k (1-based, in call order) lasts 1 + k % 10 ms; chunk calls are 1-9 and 16-24, query calls 10-15 and 25-30.
    _, _, timing, _ = _run(tmp_path, clock=Uneven())
    data = _result(timing)
    for kind, calls in (
        ("chunk_calls", [*range(1, 10), *range(16, 25)]),
        ("query_calls", [*range(10, 16), *range(25, 31)]),
    ):
        durations = [1 + k % 10 for k in calls]
        assert data[kind]["count"] == len(calls)
        assert data[kind]["p50_ms"] == pytest.approx(float(np.percentile(durations, 50)), abs=1e-9)
        assert data[kind]["p95_ms"] == pytest.approx(float(np.percentile(durations, 95)), abs=1e-9)


def test_a_non_finite_figure_refuses_before_any_file_is_touched(tmp_path):
    out, timing = tmp_path / "r.json", tmp_path / "t.json"
    with pytest.raises(ValueError):
        q3.write_outputs({out: {"ok": 1}, timing: {"bad": float("nan")}})
    assert not out.exists() and not timing.exists()
