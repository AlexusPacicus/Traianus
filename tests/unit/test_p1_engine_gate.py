"""Unit tests of tools/experiments/p1_engine_gate.py.

Specification: docs/roadmap/NEXT_RESEARCH.md ("La puerta del motor sobre P1", frozen at c848364, LEDGER seq 102).
The conftest fake provider stands for P1's encoder and for the engine's, the engine runs in process over a
temporary base, and the measurement is never run on the real corpus here.
"""

import contextlib
import hashlib
import inspect
import json
import os
import sqlite3
import tempfile
from dataclasses import dataclass, replace
from fractions import Fraction
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from helpers.db_factory import create_schema

import traianus.app as main
from tools.experiments import p1_beezer_retrieval as p1
from tools.experiments import p1_engine_gate as gate
from tools.experiments import p1_qwen3_provider as q3
from traianus import storage

TOKEN = "test-operator-token"
PREFIX = "MATH_BEEZER_"
DEFS = [f"DEF_A{i:02d}" for i in range(1, 13)]
THMS = [f"THM_B{i:02d}" for i in range(1, 13)]
CHUNKS = {suffix: f"{suffix} states a property of its own" for suffix in DEFS + THMS}
CHUNKS["THM_B12"] = CHUNKS["THM_B11"]
ITEMS = [
    (1, "first query", ["A01"]),
    (2, "second query", ["A02", "B01"]),
    (3, "third query", ["B02"]),
    (4, "fourth query", ["A03"]),
    (5, "fifth query", []),
    (6, "sixth query", ["B03", "A04"]),
    (7, "seventh query", []),
    (8, "eighth query", ["A05"]),
]
CITATIONS = [[PREFIX + "DEF_A01", PREFIX + "DEF_A02"], [PREFIX + "THM_B01", PREFIX + "DEF_A03"]]
NAMES = {
    "manifest": "beezer_manifest.json",
    "test_set": "pilot1_test_set.json",
    "citations": "beezer_citations.json",
}
MINILM_NAME = "P1_result.json"
EMPTIED = (1, 2)
KEPT = (3, 4, 6, 8)
FEW = 40
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


class FakeModel:
    device = "cpu"
    max_seq_length = 1

    def to(self, device):
        return self

    def tokenizer(self, text):
        return {"input_ids": text.split()}


class Counting:
    """Wraps a provider and counts the texts it is asked to encode."""

    def __init__(self, inner):
        self.inner, self.calls = inner, 0

    def encode(self, text):
        self.calls += 1
        return self.inner.encode(text)


class Float64:
    """A provider whose output breaks the native float32 invariant."""

    dimension = 384

    def __init__(self, inner):
        self.inner = inner

    def encode(self, text):
        return self.inner.encode(text).astype(np.float64)


class Spy:
    """Delegates to the real client and records every call."""

    def __init__(self, client):
        self.client, self.calls = client, []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.client.post(url, **kwargs)


class Canned:
    """Delegates to the real client except for the call number ``at``, which gets a canned answer."""

    def __init__(self, client, at, status, body):
        self.client, self.at, self.status, self.body, self.count = client, at, status, body, 0

    def post(self, url, **kwargs):
        self.count += 1
        if self.count != self.at:
            return self.client.post(url, **kwargs)

        def answer():
            if self.body is None:
                raise ValueError("not JSON")
            return self.body

        return SimpleNamespace(status_code=self.status, json=answer, text="")


def _raw():
    items = [{"id": i, "name": "n", "prose_es": "es", "prose_en": q, "expected": e} for i, q, e in reversed(ITEMS)]
    return {
        "manifest": json.dumps({PREFIX + key: text for key, text in CHUNKS.items()}).encode("utf-8"),
        "test_set": json.dumps({"pilot": "synthetic", "items": items}).encode("utf-8"),
        "citations": json.dumps(CITATIONS).encode("utf-8"),
    }


def _inputs():
    return p1.parse_inputs(_raw())


def _sent(inp):
    return np.array(p1.encode_texts(main.get_provider(), inp.texts))


def _ids(inp):
    return [f"VEC_{label}" for label in inp.labels]


def _bytes(doc):
    return (json.dumps(doc, indent=2, ensure_ascii=False, allow_nan=False) + "\n").encode("utf-8")


def _minilm_doc():
    inp = _inputs()
    return p1.measure(inp, p1.resolve_acros(inp), main.get_provider(), FakeModel(), {"device": "cpu"}, {})


@dataclass(frozen=True)
class World:
    paths: dict
    digests: dict
    minilm_path: Path
    minilm_digest: str
    out: Path
    provider: Counting
    model: FakeModel


@pytest.fixture
def world(tmp_path):
    raw = _raw()
    paths = {}
    for key, data in raw.items():
        paths[key] = tmp_path / NAMES[key]
        paths[key].write_bytes(data)
    stored = _bytes(_minilm_doc())
    minilm_path = tmp_path / MINILM_NAME
    minilm_path.write_bytes(stored)
    digests = {key: hashlib.sha256(data).hexdigest() for key, data in raw.items()}
    return World(
        paths,
        digests,
        minilm_path,
        hashlib.sha256(stored).hexdigest(),
        tmp_path / "P1_gate_result.json",
        Counting(main.get_provider()),
        FakeModel(),
    )


@pytest.fixture
def scratch(tmp_path, monkeypatch):
    """The directory the engine's temporary base is created in, so that leftovers are visible."""
    directory = tmp_path / "scratch"
    directory.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(directory))
    return directory


def _parameters(world):
    return {
        "out": world.out,
        "paths": world.paths,
        "digests": world.digests,
        "minilm_path": world.minilm_path,
        "minilm_digest": world.minilm_digest,
        "resolve_epsilon": lambda: 0.8,
        "build": lambda: world.model,
        "provider": world.provider,
        "emptied": EMPTIED,
        "kept": KEPT,
    }


def _run(world, **overrides):
    return gate.run(**{**_parameters(world), "n_draws": FEW, **overrides})


def _result(world):
    return json.loads(world.out.read_text(encoding="utf-8"))


def _rewritten(world, change):
    doc = json.loads(world.minilm_path.read_text(encoding="utf-8"))
    change(doc)
    data = _bytes(doc)
    world.minilm_path.write_bytes(data)
    return replace(world, minilm_digest=hashlib.sha256(data).hexdigest())


@pytest.fixture
def ran(world):
    assert _run(world) == 0
    return _result(world)


def _keys(node):
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from _keys(value)
    elif isinstance(node, list):
        for value in node:
            yield from _keys(value)


def _paths_named(node, name, here=()):
    found = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key == name:
                found.append(here + (key,))
            found += _paths_named(value, name, here + (key,))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            found += _paths_named(value, name, here + (index,))
    return found


def _theta(axes):
    gram = axes @ axes.T
    return float(np.mean([np.var(np.delete(gram[i], i)) for i in range(len(axes))]))


# Position among the candidates (T1) ------------------------------------------------------------------


def test_candidates_are_the_nodes_whose_last_state_is_consolidated():
    states = ["consolidated", "incubating", "pending_approval", "consolidated", "telemetry_error"]
    assert gate.candidates_of(states) == [0, 3]


def test_the_ranking_is_over_the_candidates_only_and_the_position_counts_among_them():
    scores = np.array([0.9, 0.8, 0.7, 0.6, 0.5])
    key = np.arange(5)
    order = gate.restricted_order(scores, key, [4, 2, 1])
    assert order == [1, 2, 4]
    assert gate.gate_position(order, {2}, 5) == 2
    assert p1.best_position(p1.ranking(scores, key), {2}) == 3


def test_ties_are_broken_by_the_chunk_own_key_not_by_its_place_in_the_subset():
    scores = np.full(4, 0.5)
    key = np.array([3, 0, 2, 1])
    assert gate.restricted_order(scores, key, [0, 1, 2, 3]) == [1, 3, 2, 0]
    assert gate.restricted_order(scores, key, [0, 2, 3]) == [3, 2, 0]


def test_the_restricted_order_agrees_with_a_plain_sort_on_random_subsets_with_many_ties():
    rng = np.random.default_rng(7)
    for _ in range(100):
        scores = np.round(rng.random(30), 1)
        key = rng.permutation(30)
        subset = rng.choice(30, size=int(rng.integers(0, 31)), replace=False)
        expected = sorted(subset.tolist(), key=lambda j: (-scores[j], key[j]))
        assert gate.restricted_order(scores, key, subset) == expected


def test_the_best_expected_statement_among_the_surviving_ones_gives_the_position():
    order = [7, 3, 9, 1]
    assert gate.gate_position(order, {1, 9}, 342) == 3
    assert gate.gate_position(order, {5, 1}, 342) == 4
    assert gate.gate_position(order, {7}, 342) == 1


def test_lost_is_the_worst_possible_position_over_the_whole_corpus():
    assert gate.gate_position([7, 3], {5, 8}, 342) == 343
    assert gate.gate_position([], {5}, 342) == 343
    assert gate.gate_position([7, 3], {5}, 24) == 25


def test_the_scorer_counts_lost_and_returns_the_wilcoxon_of_p1_minus_the_gate():
    scores = np.array([[0.9, 0.8, 0.1, 0.2, 0.3, 0.4], [0.1, 0.2, 0.9, 0.8, 0.3, 0.4]])
    keys = [np.arange(6), np.arange(6)]
    targets = [frozenset({0}), frozenset({2, 3})]
    scorer = gate.subset_scorer(scores, keys, targets, [0, 1], [5, 6], 6)
    positions, w = scorer(np.arange(6))
    assert positions == [1, 1]
    assert w == q3.wilcoxon([4, 5])
    positions, w = scorer(np.array([4, 5]))
    assert positions == [7, 7]
    assert w == q3.wilcoxon([-2, -1])
    positions, w = scorer(np.array([1, 2, 3]))
    assert positions == [7, 1]
    assert w == q3.wilcoxon([-2, 5])


# Random-subset control (T2) ---------------------------------------------------------------------------


def _recording(ps):
    subsets = []

    def scorer(subset):
        subsets.append(np.asarray(subset).copy())
        return [], {"p": ps[len(subsets) - 1]}

    return scorer, subsets


def test_the_control_constants_and_defaults_are_the_frozen_ones():
    assert (gate.N_DRAWS, gate.DRAW_SEED) == (10000, 20261005)
    defaults = inspect.signature(gate.random_control).parameters
    assert (defaults["n_draws"].default, defaults["seed"].default) == (10000, 20261005)
    assert inspect.signature(gate.run).parameters["n_draws"].default == 10000


def test_the_draws_are_uniform_subsets_of_size_n_pass_from_the_seed_in_sequence():
    scorer, subsets = _recording([Fraction(1)] * 5)
    gate.random_control(scorer, 20, 7, Fraction(1, 2), n_draws=5)
    rng = np.random.default_rng(20261005)
    expected = [rng.choice(20, size=7, replace=False) for _ in range(5)]
    assert len(subsets) == 5
    for got, want in zip(subsets, expected, strict=True):
        assert got.tolist() == want.tolist()
        assert len(set(got.tolist())) == 7


@pytest.mark.parametrize(
    ("draws", "gate_p", "count"),
    [
        ([Fraction(1, 2)] * 10, Fraction(1, 4), 0),
        ([Fraction(1, 4)] * 10, Fraction(1, 4), 10),
        ([Fraction(1, 8)] * 3 + [Fraction(1, 2)] * 7, Fraction(1, 4), 3),
    ],
)
def test_p_random_is_one_plus_the_draws_not_above_the_gate_over_draws_plus_one(draws, gate_p, count):
    scorer, _ = _recording(draws)
    control = gate.random_control(scorer, 20, 7, gate_p, n_draws=10)
    assert control["count"] == count
    assert control["p"] == Fraction(1 + count, 11)
    assert (control["draws"], control["seed"]) == (10, 20261005)


# Decision (T3) ------------------------------------------------------------------------------------------


W_PASS = q3.wilcoxon([1, 2, 3, 4, 5])
W_FAIL = q3.wilcoxon([1, 2, 3, 4])


def _decide(valid=True, n_pass=100, w=W_PASS, p_random=Fraction(1, 32), n_chunks=342, control=True):
    given = {"draws": 10, "seed": gate.DRAW_SEED, "count": 0, "p": p_random} if control else None
    return gate.decision(valid, n_chunks, n_pass, w, given, [])


def test_the_gate_passes_only_when_both_conditions_hold():
    assert _decide()["pass"] is True
    assert _decide(w=W_FAIL)["pass"] is False
    assert _decide(w=W_FAIL)["wilcoxon"]["pass"] is False
    assert _decide(w=W_FAIL)["random_control"]["pass"] is True
    assert _decide(p_random=Fraction(1, 20))["pass"] is False
    assert _decide(p_random=Fraction(1, 20))["wilcoxon"]["pass"] is True
    assert _decide(w=W_FAIL, p_random=Fraction(1, 2))["pass"] is False


@pytest.mark.parametrize("n_pass", [0, 342])
@pytest.mark.parametrize("control", [False, True])
def test_a_gate_that_passes_none_or_all_is_not_applicable_and_decides_nothing(n_pass, control):
    d = _decide(n_pass=n_pass, control=control)
    assert d["applicable"] is False
    assert d["pass"] is None and d["wilcoxon"]["pass"] is None
    assert d["random_control"] is None or d["random_control"]["pass"] is None


@pytest.mark.parametrize("n_pass", [1, 341])
def test_the_edges_next_to_none_and_all_are_applicable(n_pass):
    assert _decide(n_pass=n_pass)["applicable"] is True


def test_an_invalid_run_has_no_pass_field_set():
    d = _decide(valid=False)
    assert d["applicable"] is True
    assert d["pass"] is None and d["wilcoxon"]["pass"] is None and d["random_control"]["pass"] is None


def test_the_decision_records_the_figures_as_p1_fraction_records():
    d = _decide()
    w = d["wilcoxon"]
    assert (w["n"], w["dropped_zeros"], w["w_plus"], w["w_minus"]) == (5, 0, 15.0, 0.0)
    assert w["p"] == p1.fraction_record(Fraction(1, 32)) and w["pairs"] == []
    assert d["random_control"]["p"] == p1.fraction_record(Fraction(1, 32))
    assert (d["random_control"]["draws"], d["random_control"]["seed"]) == (10, 20261005)
    assert "no multiplicity correction" in d["multiplicity"]


# P1's rule with the gate (T8) ----------------------------------------------------------------------------


def test_chance_uses_the_candidates_and_is_zero_without_a_surviving_expected_statement():
    assert gate.chance_probability(10, 0, 5) == 0
    assert gate.chance_probability(10, 1, 5) == Fraction(1, 2)
    assert gate.chance_probability(10, 2, 1) == Fraction(1, 5)
    assert gate.chance_probability(3, 1, 5) == 1
    assert gate.chance_probability(0, 0, 5) == 0


def test_p1_rule_with_the_gate_on_a_hand_example():
    rule = gate.p1_rule([1, 343, 4], [2, 3, 9], [1, 0, 2], 10)
    five, one = rule["k5"], rule["k1"]
    assert (five["H_gate"], five["H_bm25"]) == (2, 2)
    assert (five["chance"]["num"], five["chance"]["den"]) == (7, 18)
    assert (five["mcnemar"]["b"], five["mcnemar"]["c"], five["mcnemar"]["n"]) == (1, 1, 2)
    assert (five["mcnemar"]["num"], five["mcnemar"]["den"]) == (3, 4)
    assert (one["H_gate"], one["H_bm25"]) == (1, 0)
    assert (one["chance"]["num"], one["chance"]["den"]) == (7, 25)
    assert (one["mcnemar"]["b"], one["mcnemar"]["c"], one["mcnemar"]["n"]) == (1, 0, 1)
    assert (one["mcnemar"]["num"], one["mcnemar"]["den"]) == (1, 2)
    assert five["chance"]["below_alpha"] is False and rule["holds"] is False


def test_p1_rule_holds_when_all_four_tails_are_below_one_twentieth():
    rule = gate.p1_rule([1] * 18, [300] * 18, [1] * 18, 300)
    assert rule["holds"] is True
    assert all(rule[k][f]["below_alpha"] for k in ("k5", "k1") for f in ("chance", "mcnemar"))


# The engine path (T4, T5) ------------------------------------------------------------------------------------


def test_each_chunk_is_ingested_then_consolidated_in_manifest_order_with_the_key_as_json_true():
    inp = _inputs()
    sent = _sent(inp)
    with gate.fresh_engine() as session:
        spy = Spy(session.client)
        gate.ingest_and_consolidate(replace(session, client=spy), inp.labels, inp.texts, sent)
    expected = []
    for label in inp.labels:
        expected += ["/ingesta/vector", f"/nodos/VEC_{label}/consolidar"]
    assert [url for url, _ in spy.calls] == expected
    for j, label in enumerate(inp.labels):
        ingest, consolidate = spy.calls[2 * j][1], spy.calls[2 * j + 1][1]
        assert ingest["json"] == {"vector": sent[j].tolist(), "label": label, "text": inp.texts[j]}
        assert ingest["headers"]["X-Idempotency-Key"] == "p1-gate-" + label
        assert consolidate["json"] == {"text": inp.texts[j], "ethical_key": True}
        assert consolidate["json"]["ethical_key"] is True
    idempotency = [kwargs["headers"]["X-Idempotency-Key"] for _, kwargs in spy.calls[::2]]
    assert len(set(idempotency)) == len(idempotency) == len(inp.labels)


def test_the_final_state_is_consolidated_iff_the_variance_reaches_theta_computed_independently():
    inp = _inputs()
    with gate.fresh_engine() as session:
        records = gate.ingest_and_consolidate(session, inp.labels, inp.texts, _sent(inp))
        read = gate.query_phase(session.db_path, _ids(inp))
        axes = np.array([entry["vector"] for entry in storage.get_geodetic_matrix_db().values()])
    theta = _theta(axes)
    states = []
    for record, history in zip(records, read.revisions, strict=True):
        assert len(history) == 2 and history[0].state == "incubating"
        sigma2 = float(np.var(axes @ history[-1].vector))
        state = "consolidated" if sigma2 >= theta else "incubating"
        assert history[-1].state == state and record["new_state"] == state
        assert record["sigma2"] == pytest.approx(sigma2, abs=1e-12)
        assert record["theta_dyn"] == pytest.approx(theta, abs=1e-12)
        states.append(state)
    assert "consolidated" in states and "incubating" in states


def test_db_path_token_and_temporary_directory_are_restored(scratch):
    before = storage.DB_PATH
    with gate.fresh_engine() as session:
        assert storage.DB_PATH != before and Path(storage.DB_PATH) == session.db_path
        assert session.db_path.parent.parent == scratch
        token = os.environ["TRAIANUS_TOKEN"]
        assert token != TOKEN and len(token) == 32
        assert session.headers == {"X-Traianus-Token": token}
    assert storage.DB_PATH == before and os.environ["TRAIANUS_TOKEN"] == TOKEN
    assert list(scratch.iterdir()) == []


def test_everything_is_restored_when_the_body_raises_and_an_unset_token_stays_unset(scratch, monkeypatch):
    monkeypatch.delenv("TRAIANUS_TOKEN")
    before = storage.DB_PATH
    with pytest.raises(RuntimeError), gate.fresh_engine():
        raise RuntimeError("boom")
    assert storage.DB_PATH == before and "TRAIANUS_TOKEN" not in os.environ
    assert list(scratch.iterdir()) == []


CANNED = [
    (1, 200, {"lifecycle_state": "incubating"}),
    (1, 201, {"lifecycle_state": "consolidated"}),
    (1, 422, {}),
    (1, 201, None),
    (2, 500, {}),
    (2, 404, {}),
    (2, 200, {"new_state": "consolidated"}),
    (2, 200, None),
]


@pytest.mark.parametrize(("at", "status", "body"), CANNED)
def test_an_unexpected_answer_during_ingestion_or_consolidation_is_refused(at, status, body):
    inp = _inputs()
    with gate.fresh_engine() as session:
        canned = Canned(session.client, at, status, body)
        with pytest.raises(p1.Refusal) as caught:
            gate.ingest_and_consolidate(replace(session, client=canned), inp.labels, inp.texts, _sent(inp))
    assert caught.value.identifier == "RF8"


def test_a_repeated_idempotency_key_answers_200_and_is_refused():
    inp = _inputs()
    with gate.fresh_engine() as session, pytest.raises(p1.Refusal) as caught:
        gate.ingest_and_consolidate(session, inp.labels[:1] * 2, inp.texts[:1] * 2, _sent(inp)[:1].repeat(2, axis=0))
    assert caught.value.identifier == "RF8"


def _engine_refused(world, scratch, capsys):
    before = storage.DB_PATH
    assert _run(world) == 1
    assert capsys.readouterr().err.startswith("RF8 engine:")
    assert not world.out.exists() and list(scratch.iterdir()) == []
    assert storage.DB_PATH == before and os.environ["TRAIANUS_TOKEN"] == TOKEN


def test_a_bootstrap_failure_refuses_through_run_and_leaves_nothing(world, scratch, monkeypatch, capsys):
    def boom():
        raise OSError("no weights")

    monkeypatch.setattr(gate.bootstrap, "main", boom)
    _engine_refused(world, scratch, capsys)


def test_an_http_error_from_the_engine_refuses_through_run_and_leaves_nothing(world, scratch, monkeypatch, capsys):
    fake = main.get_provider()
    monkeypatch.setattr(main, "get_provider", lambda: Float64(fake))
    _engine_refused(world, scratch, capsys)


def test_a_vector_failing_p1_checks_refuses_rf5_before_the_engine(world, scratch, capsys):
    assert _run(world, provider=Float64(world.provider)) == 1
    assert capsys.readouterr().err.startswith("RF5")
    assert not world.out.exists() and list(scratch.iterdir()) == []


def _bad_digest(world, monkeypatch):
    return world, {"digests": {**world.digests, "manifest": "0" * 64}}


def _bad_epsilon(world, monkeypatch):
    return world, {"resolve_epsilon": lambda: 0.5}


def _no_weights(world, monkeypatch):
    def build():
        raise OSError("not in the local cache")

    return world, {"build": build}


def _bad_minilm_digest(world, monkeypatch):
    return world, {"minilm_digest": "0" * 64}


def _invalid_minilm(world, monkeypatch):
    return _rewritten(world, lambda doc: doc.update(valid=False)), {}


def _bad_split(world, monkeypatch):
    return world, {"kept": (3, 4)}


def _other_revision(world, monkeypatch):
    monkeypatch.setattr(gate, "MODEL_REVISION", "0" * 40)
    return world, {}


def _online(world, monkeypatch):
    monkeypatch.setenv("HF_HUB_OFFLINE", "0")
    return world, {}


@pytest.mark.parametrize(
    ("identifier", "arrange"),
    [
        ("RF1", _bad_digest),
        ("RF4", _bad_epsilon),
        ("RF5", _no_weights),
        ("RF6", _bad_minilm_digest),
        ("RF6", _invalid_minilm),
        ("RF7", _bad_split),
        ("RF8", _other_revision),
        ("RF8", _online),
    ],
)
def test_a_refusal_before_any_encoding_exits_1_writes_nothing_and_leaves_nothing(
    identifier, arrange, world, scratch, monkeypatch, capsys
):
    before = storage.DB_PATH
    world, overrides = arrange(world, monkeypatch)
    assert _run(world, **overrides) == 1
    assert capsys.readouterr().err.startswith(f"{identifier} {gate.REFUSALS[identifier]}:")
    assert world.provider.calls == 0 and not world.out.exists()
    assert list(scratch.iterdir()) == [] and storage.DB_PATH == before


def test_the_engine_provider_must_be_at_p1_pinned_revision_and_offline():
    gate.check_engine_provider(p1.PINNED_REVISION, {"HF_HUB_OFFLINE": "1"})
    for revision, environ in (
        ("0" * 40, {"HF_HUB_OFFLINE": "1"}),
        (p1.PINNED_REVISION, {"HF_HUB_OFFLINE": "0"}),
        (p1.PINNED_REVISION, {}),
    ):
        with pytest.raises(p1.Refusal) as caught:
            gate.check_engine_provider(revision, environ)
        assert caught.value.identifier == "RF8"


# Read-only query phase and R2 (T6) -----------------------------------------------------------------------------


BASE_ROW = {
    "id": "VEC_a",
    "seq": 1,
    "text": "t",
    "toon_factor": "x",
    "lifecycle_state": "incubating",
    "action_potential": 0.5,
    "revision_milestone": 0,
    "vector_blob": bytes([1, 2, 3]),
    "projections_json": "{}",
    "epoch_provenance": "PROSTHETIC_NSM_V1",
    "event_type": None,
    "sys_internal_timestamp": "2026-01-01 00:00:00",
    "idempotency_key": None,
}
CHANGES = {
    "id": "VEC_b",
    "seq": 2,
    "text": "u",
    "toon_factor": "y",
    "lifecycle_state": "consolidated",
    "action_potential": 0.25,
    "revision_milestone": 1,
    "vector_blob": bytes([1, 2, 4]),
    "projections_json": "[]",
    "epoch_provenance": "OTHER",
    "event_type": "ERROR",
    "sys_internal_timestamp": "2026-01-02 00:00:00",
    "idempotency_key": "k",
}
INSERT_ROW = (
    "INSERT INTO manifold_nodes (id, seq, text, toon_factor, lifecycle_state, action_potential, "
    "revision_milestone, vector_blob, projections_json) VALUES ('z', 1, 't', 'x', 'incubating', 0.0, 0, x'00', '{}')"
)


def _digest_of(directory, name, rows):
    path = directory / name
    with contextlib.closing(sqlite3.connect(path)) as conn:
        create_schema(conn)
        for row in rows:
            marks = ", ".join("?" * len(row))
            conn.execute(f"INSERT INTO manifold_nodes ({', '.join(row)}) VALUES ({marks})", list(row.values()))
        conn.commit()
    with contextlib.closing(gate.open_readonly(path)) as reader:
        return gate.table_digest(reader)


def test_the_read_only_connection_refuses_a_write(tmp_path):
    path = tmp_path / "base.db"
    with contextlib.closing(sqlite3.connect(path)) as conn:
        create_schema(conn)
    with contextlib.closing(gate.open_readonly(path)) as reader, pytest.raises(sqlite3.OperationalError):
        reader.execute(INSERT_ROW)


def test_the_query_phase_reads_through_the_read_only_connection(monkeypatch):
    inp = _inputs()
    seen = []
    original = gate.read_revisions

    def probe(conn, node_ids):
        try:
            conn.execute(INSERT_ROW)
        except sqlite3.OperationalError as error:
            seen.append(str(error))
        return original(conn, node_ids)

    monkeypatch.setattr(gate, "read_revisions", probe)
    with gate.fresh_engine() as session:
        gate.ingest_and_consolidate(session, inp.labels, inp.texts, _sent(inp))
        read = gate.query_phase(session.db_path, _ids(inp))
    assert len(seen) == 1 and "readonly" in seen[0]
    assert read.digest_before == read.digest_after


@pytest.mark.parametrize("column", sorted(CHANGES))
def test_the_digest_sees_a_change_in_any_single_column(tmp_path, column):
    base = _digest_of(tmp_path, "a.db", [BASE_ROW])
    assert _digest_of(tmp_path, "b.db", [{**BASE_ROW, column: CHANGES[column]}]) != base
    assert _digest_of(tmp_path, "c.db", [BASE_ROW]) == base


def test_the_digest_sees_an_added_row_and_ignores_the_insertion_order(tmp_path):
    second = {**BASE_ROW, "seq": 2}
    both = _digest_of(tmp_path, "a.db", [BASE_ROW, second])
    assert _digest_of(tmp_path, "b.db", [second, BASE_ROW]) == both
    assert _digest_of(tmp_path, "c.db", [BASE_ROW]) != both


def test_a_row_appended_during_the_query_phase_invalidates_v3(world, monkeypatch):
    original = gate.read_revisions

    def writing(conn, node_ids):
        storage.insert_node_revision(
            "VEC_extra", "t", "x", "incubating", 0.0, 0, np.zeros(384).tobytes(), "{}", storage.active_epoch()
        )
        return original(conn, node_ids)

    monkeypatch.setattr(gate, "read_revisions", writing)
    assert _run(world) == 0
    result = _result(world)
    assert result["valid"] is False and result["failed"] == ["V3"] and result["first_failed"] == "V3"
    assert result["validity"]["V3"]["equal"] is False
    assert result["decision"]["pass"] is None and result["decision"]["wilcoxon"]["pass"] is None


# Validity V1 and V2 (T7) ----------------------------------------------------------------------------------------


def test_a_consistent_world_is_valid_and_decides(ran):
    assert ran["valid"] is True and ran["failed"] == [] and ran["first_failed"] is None
    assert ran["validity"]["V1"]["mismatched_ids"] == [] and ran["validity"]["V2"]["mismatched_ids"] == []
    assert ran["validity"]["V3"]["equal"] is True
    assert ran["decision"]["applicable"] is True and isinstance(ran["decision"]["pass"], bool)


def _position_plus_one(doc):
    doc["report_only"]["items"][0]["engine"]["position"] += 1


def _swap_top5(doc):
    top5 = doc["report_only"]["items"][1]["engine"]["top5"]
    top5[0], top5[1] = top5[1], top5[0]


def _swap_top5_of_an_item_without_expected(doc):
    item = next(entry for entry in doc["report_only"]["items"] if not entry["m"])
    item["engine"]["top5"].reverse()


@pytest.mark.parametrize("change", [_position_plus_one, _swap_top5, _swap_top5_of_an_item_without_expected])
def test_v1_fails_when_one_unfiltered_position_or_top5_differs_from_the_stored_one(world, change):
    world = _rewritten(world, change)
    assert _run(world) == 0
    result = _result(world)
    assert result["valid"] is False and result["failed"] == ["V1"]
    assert len(result["validity"]["V1"]["mismatched_ids"]) == 1
    assert result["validity"]["V2"]["mismatched_ids"] == []
    assert result["decision"]["pass"] is None and result["decision"]["wilcoxon"]["pass"] is None


def test_v2_fails_when_the_recomputed_bm25_differs_from_the_stored_one(world):
    world = _rewritten(world, lambda doc: doc["report_only"]["items"][2]["bm25"].update(position=999))
    assert _run(world) == 0
    result = _result(world)
    assert result["valid"] is False and result["failed"] == ["V2"]
    assert result["validity"]["V2"]["mismatched_ids"] == [3] and result["validity"]["V1"]["mismatched_ids"] == []
    assert result["decision"]["pass"] is None


def test_v1_and_v2_are_both_named_when_both_fail(world):
    def both(doc):
        _position_plus_one(doc)
        doc["report_only"]["items"][2]["bm25"]["top5"].reverse()

    world = _rewritten(world, both)
    assert _run(world) == 0
    result = _result(world)
    assert result["failed"] == ["V1", "V2"] and result["first_failed"] == "V1"


# Not applicable and the report (B5, B6, B7) -----------------------------------------------------------------------


@pytest.mark.parametrize("everyone", [False, True])
def test_a_gate_passing_none_or_all_is_written_as_not_applicable(world, monkeypatch, everyone):
    monkeypatch.setattr(gate, "candidates_of", lambda states: list(range(len(states))) if everyone else [])
    assert _run(world) == 0
    result = _result(world)
    assert result["valid"] is True and result["decision"]["applicable"] is False
    assert result["decision"]["pass"] is None and result["decision"]["wilcoxon"]["pass"] is None
    assert result["decision"]["random_control"] is None
    assert result["report_only"]["n_pass"] == (len(CHUNKS) if everyone else 0)


def test_the_decision_block_of_a_run_is_consistent_with_its_own_figures(ran):
    d = ran["decision"]
    w, control = d["wilcoxon"], d["random_control"]
    assert [pair["id"] for pair in w["pairs"]] == [1, 2, 3, 4, 6, 8]
    assert all(pair["d"] == pair["p1"] - pair["gate"] for pair in w["pairs"])
    assert w["pass"] is (Fraction(w["p"]["num"], w["p"]["den"]) < Fraction(1, 20))
    assert (control["draws"], control["seed"]) == (FEW, 20261005)
    assert Fraction(control["p"]["num"], control["p"]["den"]) == Fraction(1 + control["count"], FEW + 1)
    assert control["pass"] is (Fraction(control["p"]["num"], control["p"]["den"]) < Fraction(1, 20))
    assert d["pass"] is (w["pass"] and control["pass"])


def test_the_gate_positions_agree_with_an_independent_computation(ran):
    inp = _inputs()
    chunks = _sent(inp)
    queries = np.array(p1.encode_texts(main.get_provider(), [item.query for item in inp.items]))
    positives = [i for i, item in enumerate(inp.items) if item.acros]
    keys, _ = p1.draw(len(inp.texts), len(inp.items), len(positives))
    states = {row["key"]: row["state"] for row in ran["report_only"]["chunks"]}
    candidates = [j for j, label in enumerate(inp.labels) if states[label] == "consolidated"]
    rows = {row["id"]: row for row in ran["report_only"]["items"]}
    acro_index = p1.resolve_acros(inp)
    assert 0 < len(candidates) < len(inp.texts) and ran["report_only"]["n_pass"] == len(candidates)
    for i in positives:
        item = inp.items[i]
        scores = chunks @ queries[i]
        order = sorted(candidates, key=lambda j: (-scores[j], keys[i][j]))
        survivors = [acro for acro in item.acros if acro_index[acro] in candidates]
        row = rows[item.id]
        assert row["gate_position"] == min((order.index(acro_index[a]) + 1 for a in survivors), default=len(inp.texts) + 1)
        assert row["gate_top5"] == [inp.labels[j] for j in order[:5]]
        assert row["surviving_expected"] == survivors


def test_only_the_decision_has_a_pass_field(ran):
    assert _paths_named(ran, "pass") != []
    assert all(path[0] == "decision" for path in _paths_named(ran, "pass"))


def test_the_report_only_blocks(ran):
    ro = ran["report_only"]
    inp = _inputs()
    assert [row["key"] for row in ro["chunks"]] == inp.labels
    assert set(ro["chunks"][0]) == {"key", "sigma2", "sigma2_ingest", "threshold", "topological_passed", "state"}
    assert isinstance(ro["theta_dyn"], float) and ro["theta_dyn_distinct"] == 1
    twins = [PREFIX + "THM_B11", PREFIX + "THM_B12"]
    duplicated = ro["duplicated_texts"]
    assert [(group["text"], group["keys"]) for group in duplicated] == [(CHUNKS["THM_B11"], twins)]
    assert duplicated[0]["states"][0] == duplicated[0]["states"][1]
    for revision, tolerance in (("ingested", 1e-12), ("consolidated", 1e-6)):
        block = ro["vector_differences"][revision]
        assert block["of"] == len(inp.texts) and 0 <= block["byte_identical"] <= block["of"]
        assert 0.0 <= block["max_abs_difference"] < tolerance
    assert set(ro["p1_rule"]) == {"k5", "k1", "holds"}
    assert set(ro["mcnemar_gate_vs_p1"]) == {"k5", "k1"}
    assert set(ro["mcnemar_gate_vs_p1"]["k5"]) == {"b", "c", "n", "num", "den", "float"}
    assert set(ro["rank_metrics"]) == {"gate", "p1", "bm25"}
    assert set(ro["rank_metrics"]["gate"]) == {"mrr", "recall_10", "recall_20", "median_position"}
    assert set(ro["auc"]) == {"num", "den", "float"}
    assert ro["split"]["emptied"]["ids"] == list(EMPTIED) and ro["split"]["kept"]["ids"] == list(KEPT)
    assert set(ro["split"]["emptied"]["arms"]) == {"p1", "gate", "bm25"}
    assert [row["id"] for row in ro["items"]] == [1, 2, 3, 4, 6, 8]
    assert set(ro["items"][0]) == {"id", "p1_position", "gate_position", "gate_top5", "surviving_expected", "bm25_position"}


def test_the_p1_rule_of_a_run_uses_the_candidates_and_the_surviving_expected_statements(ran):
    ro = ran["report_only"]
    rows = ro["items"]
    survivors = [len(row["surviving_expected"]) for row in rows]
    expected = gate.p1_rule(
        [row["gate_position"] for row in rows], [row["bm25_position"] for row in rows], survivors, ro["n_pass"]
    )
    assert ro["p1_rule"] == json.loads(json.dumps(expected))


def test_the_environment_carries_p1_fields_and_the_engine_ones(ran, world):
    env = ran["environment"]
    assert all(key in env for key in P1_ENVIRONMENT_KEYS)
    assert env["engine_model_revision"] == p1.PINNED_REVISION
    assert env["epoch_provenance"] == ["PROSTHETIC_NSM_V1"]
    assert env["minilm_result_sha256"] == world.minilm_digest and env["protocol_commit"] == "c848364"
    assert ran["digests"] == {NAMES[key]: world.digests[key] for key in NAMES}
    counts = ran["counts"]
    assert (counts["chunks"], counts["items"], counts["positives"]) == (len(CHUNKS), len(ITEMS), 6)
    assert counts["candidates"] == ran["report_only"]["n_pass"]


def test_p1_encoder_is_asked_for_the_first_pass_only(world, ran):
    assert world.provider.calls == len(CHUNKS) + len(ITEMS)


# Determinism and output (T9) --------------------------------------------------------------------------------------


def test_two_runs_with_the_same_fakes_write_the_same_bytes_and_no_timing(world, tmp_path):
    second = tmp_path / "second.json"
    assert _run(world) == 0 and _run(world, out=second) == 0
    assert world.out.read_bytes() == second.read_bytes()
    timing = ("time", "duration", "elapsed", "second", "_ms", "latency")
    assert [key for key in _keys(_result(world)) if any(word in key.lower() for word in timing)] == []


def test_the_result_is_p1_json_with_a_final_newline(world, ran):
    text = world.out.read_text(encoding="utf-8")
    assert text.endswith("}\n") and text == _bytes(json.loads(text)).decode("utf-8")


def test_a_non_finite_figure_stops_before_any_file_is_touched(world, scratch, monkeypatch):
    monkeypatch.setattr(gate, "measure", lambda *args, **kwargs: {"x": float("nan")})
    with pytest.raises(ValueError):
        _run(world)
    assert not world.out.exists() and list(scratch.iterdir()) == []


def test_a_run_with_the_default_draws_records_ten_thousand_draws(world):
    assert gate.run(**_parameters(world)) == 0
    control = _result(world)["decision"]["random_control"]
    assert (control["draws"], control["seed"]) == (10000, 20261005)
    assert Fraction(control["p"]["num"], control["p"]["den"]) == Fraction(1 + control["count"], 10001)


def test_main_hands_run_p1_inputs_and_the_default_result_path(monkeypatch, tmp_path):
    seen = {}

    def fake_run(*args):
        seen["args"] = args
        return 0

    monkeypatch.setattr(gate, "run", fake_run)
    monkeypatch.setattr(gate, "SentenceTransformerProvider", lambda: "provider")
    assert gate.main([]) == 0
    out, paths, digests, minilm_path, minilm_digest, _, build, provider = seen["args"]
    assert (out, paths, digests) == (gate.RESULT, p1.PATHS, p1.EXPECTED_DIGESTS)
    assert (minilm_path, minilm_digest) == (p1.RESULT, q3.MINILM_SHA256)
    assert build is gate.build_encoder and provider == "provider"
    assert gate.RESULT == p1.DATA / "P1_gate_result.json"
    assert gate.main(["--out", str(tmp_path / "x.json")]) == 0 and seen["args"][0] == tmp_path / "x.json"


# Guard: P1 and the Qwen3 baseline do not change (T10) -----------------------------------------------------------------


def test_p1_and_the_qwen3_baseline_keep_their_constants_and_refusals():
    assert (p1.SEED, p1.N_SHUFFLES, p1.KS, p1.TOP, p1.DIM, p1.EPSILON) == (20261002, 1000, (5, 1), 5, 384, 0.8)
    assert p1.PINNED_REVISION == "1110a243fdf4706b3f48f1d95db1a4f5529b4d41" and p1.ALPHA == Fraction(1, 20)
    assert p1.REFUSALS == {
        "RF1": "digests",
        "RF2": "strict_json",
        "RF3": "acro_resolution",
        "RF4": "epsilon",
        "RF5": "encoder_offline_cpu",
    }
    assert q3.EMPTIED == (1, 2, 6, 7, 13, 15, 18, 23, 24, 25, 28) and q3.KEPT == (11, 12, 14, 16, 17, 21, 27)
    assert q3.MINILM_SHA256 == "00522a30465ae3dc21a949aca6d5464c9060f99d2a50038c05f088976c9132d8"
    assert q3.REFUSALS == {**p1.REFUSALS, "RF6": "minilm_arm", "RF7": "formula_split"}
    assert gate.REFUSALS == {**q3.REFUSALS, "RF8": "engine"}
    assert gate.PROTOCOL_COMMIT == "c848364"
