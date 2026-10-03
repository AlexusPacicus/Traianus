"""P1 — recovery of expected Beezer statements.

Implements docs/methodology/instrument-audit/P1.md (instrument audit record, revision 6) against
docs/methodology/instrument-audit/contracts.md (section 6) and derivations.md (D5, D30-D34).

For the test items that have an expected statement, measures whether an expected label is among the
k nearest chunks of the item's query, k = 5 and k = 1, in two arms: the provider's vectors (engine)
and BM25. The engine's hits are compared with a uniform-order chance model and with BM25's hits;
the claim holds iff the four exact tests pass. Everything else is report-only and decides nothing.

Refuses to run, and writes nothing, unless the three input digests match (RF1), the inputs parse
as strict JSON (RF2), every expected acro resolves to one label (RF3), resolve_epsilon_edge()
returns 0.8, a value it cannot parse being refused too (RF4), and the encoder loads offline at the
pinned revision on the cpu (RF5). A run that completes but fails a check (V1 vectors, V2
alignment) is written with valid = false, no decision and, for V1, no vector-derived figure.

Usage:
    python3 tools/experiments/p1_beezer_retrieval.py [--out PATH]
"""

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_var] = "1"

import argparse
import hashlib
import json
import math
import platform
import re
import statistics
import sys
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from traianus.config import resolve_epsilon_edge
from traianus.representation.sentence_transformer import (
    MODEL_REVISION,
    SentenceTransformerProvider,
    build_encoder,
)

DATA = REPO_ROOT / "data" / "math"
PATHS = {
    "manifest": DATA / "beezer_manifest.json",
    "test_set": DATA / "pilot1_test_set.json",
    "citations": DATA / "beezer_citations.json",
}
EXPECTED_DIGESTS = {
    "manifest": "6d1782002c7650c3c59ed26332bcef500782fab04f8b7322661d671249fb9626",
    "test_set": "9fc7ad6f875f55d63e75e71f83fb75afa9e0adf62a1f8e699c9dd830dd866d82",
    "citations": "50e831d2041eec62fc728c4ddaf6d74aa1ea63c3b050d7a497958446b8304226",
}
RESULT = DATA / "P1_result.json"

SEED = 20261002
N_SHUFFLES = 1000
KS = (5, 1)
TOP = 5
BM25_K1 = 1.2
BM25_B = 0.75
ALPHA = Fraction(1, 20)
DIM = 384
NORM_TOLERANCE = 1e-12
EPSILON = 0.8
PINNED_REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
ACRO_PREFIXES = ("MATH_BEEZER_DEF_", "MATH_BEEZER_THM_")
REFUSALS = {
    "RF1": "digests",
    "RF2": "strict_json",
    "RF3": "acro_resolution",
    "RF4": "epsilon",
    "RF5": "encoder_offline_cpu",
}
INDEPENDENCE_LIMIT = (
    "Declared limit (P1.md, Chance): items that share a target are not independent, and the "
    "chance and McNemar tails take them as independent, so both p-values can be anti-conservative, "
    "the McNemar one the more."
)

Order = list[int]
Rows = list[np.ndarray | None]


class Refusal(Exception):
    """A refusal condition of the record: no result is written."""

    def __init__(self, identifier: str, message: str) -> None:
        super().__init__(message)
        self.identifier = identifier


class InvalidVector(ValueError):
    """A provider output failing the checks of the Vectors line."""


@dataclass(frozen=True)
class Item:
    id: int
    query: str
    acros: tuple[str, ...]


@dataclass(frozen=True)
class Inputs:
    labels: list[str]
    texts: list[str]
    index: dict[str, int]
    items: list[Item]
    citations: list[tuple[int, int]]


# Data layer (RF1, RF2, RF3) --------------------------------------------------------------------


def read_verified(paths: Mapping[str, Path], digests: Mapping[str, str]) -> dict[str, bytes]:
    """Each file read once as bytes and hashed; the parse reads these same bytes (RF1)."""
    raw = {}
    for name, path in paths.items():
        try:
            data = Path(path).read_bytes()
        except OSError as exc:
            raise Refusal("RF1", f"cannot read {path}: {exc}") from exc
        actual = hashlib.sha256(data).hexdigest()
        if actual != digests[name]:
            raise Refusal("RF1", f"sha256 mismatch for {path}: expected {digests[name]}, got {actual}")
        raw[name] = data
    return raw


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    if len({key for key, _ in pairs}) != len(pairs):
        raise ValueError("duplicate key")
    return dict(pairs)


def _refuse_constant(name: str) -> None:
    raise ValueError(f"non-finite constant {name}")


def _finite_float(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        raise ValueError(f"non-finite number {text}")
    return value


def parse_strict_json(raw: bytes) -> Any:
    try:
        return json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_no_duplicate_keys,
            parse_constant=_refuse_constant,
            parse_float=_finite_float,
        )
    except ValueError as exc:
        raise Refusal("RF2", f"not strict UTF-8 JSON: {exc}") from exc


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise Refusal("RF2", message)


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and value != ""


def parse_inputs(raw: Mapping[str, bytes]) -> Inputs:
    manifest = parse_strict_json(raw["manifest"])
    _require(isinstance(manifest, dict), "manifest must be an object")
    _require(
        all(_non_empty_string(label) and _non_empty_string(text) for label, text in manifest.items()),
        "every manifest label and text must be a non-empty string",
    )
    labels = list(manifest)
    texts = [manifest[label] for label in labels]
    index = {label: j for j, label in enumerate(labels)}

    document = parse_strict_json(raw["test_set"])
    _require(isinstance(document, dict) and isinstance(document.get("items"), list), "test set needs an items list")
    items = []
    for entry in document["items"]:
        _require(isinstance(entry, dict), "every item must be an object")
        item_id, query, acros = entry.get("id"), entry.get("prose_en"), entry.get("expected")
        _require(type(item_id) is int, "every item id must be an integer")
        _require(_non_empty_string(query), f"item {item_id}: prose_en must be a non-empty string")
        _require(
            isinstance(acros, list) and all(isinstance(acro, str) for acro in acros),
            f"item {item_id}: expected must be a list of strings",
        )
        items.append(Item(item_id, query, tuple(acros)))
    items.sort(key=lambda item: item.id)
    _require(len({item.id for item in items}) == len(items), "item ids must be distinct")

    pairs = parse_strict_json(raw["citations"])
    _require(
        isinstance(pairs, list)
        and all(
            isinstance(pair, list)
            and len(pair) == 2
            and all(isinstance(end, str) and end in index for end in pair)
            for pair in pairs
        ),
        "citations must be pairs of manifest labels",
    )
    return Inputs(labels, texts, index, items, [(index[a], index[b]) for a, b in pairs])


def acro_of(label: str) -> str | None:
    for prefix in ACRO_PREFIXES:
        if label.startswith(prefix):
            return label[len(prefix) :]
    return None


def resolve_acros(inp: Inputs) -> dict[str, int]:
    """Chunk index of each expected acro; an acro with other than one label refuses (RF3)."""
    by_acro: dict[str, list[int]] = {}
    for j, label in enumerate(inp.labels):
        acro = acro_of(label)
        if acro is not None:
            by_acro.setdefault(acro, []).append(j)
    resolved = {}
    for item in inp.items:
        for acro in item.acros:
            found = by_acro.get(acro, [])
            if len(found) != 1:
                raise Refusal("RF3", f"acro {acro!r} resolves to {len(found)} labels, not 1")
            resolved[acro] = found[0]
    return resolved


# Epsilon and encoder (RF4, RF5) ------------------------------------------------------------------


def check_epsilon(resolve: Callable[[], float]) -> None:
    try:
        value = resolve()
    except ValueError as exc:
        raise Refusal("RF4", f"resolve_epsilon_edge() cannot parse its value: {exc}") from exc
    if value != EPSILON:
        raise Refusal("RF4", f"resolve_epsilon_edge() returned {value!r}, not {EPSILON!r}")


def load_encoder(build: Callable[[], Any], revision: str) -> Any:
    """The encoder, moved to the cpu; it must load offline at the pinned revision (RF5)."""
    if revision != PINNED_REVISION:
        raise Refusal("RF5", f"revision {revision} is not the pinned {PINNED_REVISION}")
    try:
        model = build()
        model.to("cpu")
    except (OSError, ValueError, ImportError) as exc:
        raise Refusal("RF5", f"encoder did not load offline: {exc}") from exc
    if str(model.device) != "cpu":
        raise Refusal("RF5", f"encoder sits on {model.device}, not on the cpu")
    return model


def environment(model: Any) -> dict[str, Any]:
    import sentence_transformers
    import torch

    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "torch": torch.__version__,
        "sentence_transformers": sentence_transformers.__version__,
        "platform": platform.platform(),
        "device": str(model.device),
        "max_seq_length": model.max_seq_length,
        "numpy_config": np.show_config(mode="dicts"),
        "torch_threads": torch.get_num_threads(),
    }


# Vectors (V1) -----------------------------------------------------------------------------------


def unit_vector(u: Any) -> np.ndarray:
    """The checks of traianus/app.py _encode_vector on the native output, then float64 and unit norm."""
    if not isinstance(u, np.ndarray) or u.ndim != 1:
        raise InvalidVector("output must be a 1-D array")
    if u.dtype != np.float32:
        raise InvalidVector(f"dtype {u.dtype} is not float32")
    if u.size != DIM:
        raise InvalidVector(f"size {u.size} is not {DIM}")
    if not np.all(np.isfinite(u)):
        raise InvalidVector("non-finite values")
    if np.linalg.norm(u) == 0.0:
        raise InvalidVector("zero norm")
    wide = u.astype(np.float64)
    v = wide / np.linalg.norm(wide)
    if abs(np.linalg.norm(v) - 1.0) > NORM_TOLERANCE:
        raise InvalidVector("norm after normalisation is not 1")
    return v


def encode_texts(provider: Any, texts: Sequence[str]) -> Rows:
    """One text per call; a row failing the vector checks is None, so every output is checked."""
    rows: Rows = []
    for text in texts:
        try:
            rows.append(unit_vector(provider.encode(text)))
        except InvalidVector:
            rows.append(None)
    return rows


def encode_passes(provider: Any, texts: Sequence[str], queries: Sequence[str]) -> tuple[Rows, Rows]:
    """First pass: the chunks, then the queries (query i at row len(texts) + i - 1); second pass: the chunks."""
    return encode_texts(provider, [*texts, *queries]), encode_texts(provider, texts)


def matrix_sha256(rows: Sequence[np.ndarray]) -> str:
    return hashlib.sha256(np.array(rows, dtype="<f8", order="C").tobytes()).hexdigest()


def score_matrix(queries: np.ndarray, chunks: np.ndarray) -> np.ndarray:
    """S(i, j) = <query i, chunk j> in binary64, one inner product per pair."""
    return np.array([[np.dot(q, c) for c in chunks] for q in queries])


def distance(score: float) -> float:
    return math.sqrt(max(0.0, 2.0 - 2.0 * score))


def alignment_matched(second: np.ndarray, chunks: np.ndarray, texts: Sequence[str]) -> int:
    """Chunks whose second-pass vector ranks first a chunk of equal text; ties to the lower index."""
    index = np.arange(len(chunks))
    matched = 0
    for j, row in enumerate(score_matrix(second, chunks)):
        first = int(np.lexsort((index, -row))[0])
        matched += int(texts[first] == texts[j])
    return matched


# BM25 -------------------------------------------------------------------------------------------


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


@dataclass(frozen=True)
class Bm25Index:
    counts: list[Counter[str]]
    lengths: list[int]
    document_frequency: Counter[str]
    avgdl: float


def bm25_index(texts: Sequence[str]) -> Bm25Index:
    counts = [Counter(tokens(text)) for text in texts]
    lengths = [sum(count.values()) for count in counts]
    frequency = Counter(term for count in counts for term in count)
    return Bm25Index(counts, lengths, frequency, sum(lengths) / len(texts))


def bm25_scores(index: Bm25Index, query: str) -> list[float]:
    n = len(index.counts)
    idf = {}
    for term in dict.fromkeys(tokens(query)):
        n_t = index.document_frequency[term]
        idf[term] = math.log(1 + (n - n_t + 0.5) / (n_t + 0.5))
    scores = []
    for count, length in zip(index.counts, index.lengths, strict=True):
        score = 0.0
        for term, weight in idf.items():
            f = count[term]
            if f:
                score += weight * f * (BM25_K1 + 1) / (f + BM25_K1 * (1 - BM25_B + BM25_B * length / index.avgdl))
        scores.append(score)
    return scores


def bm25_check(texts: Sequence[str], score: Callable[[str], Sequence[float]]) -> dict[str, int]:
    """Report-only: a chunk's first token found in no other chunk, as a query, scores that chunk alone."""
    frequency = Counter(term for text in texts for term in set(tokens(text)))
    holders = passed = 0
    for j, text in enumerate(texts):
        unique = next((term for term in tokens(text) if frequency[term] == 1), None)
        if unique is None:
            continue
        holders += 1
        row = score(unique)
        passed += int(row[j] > 0 and all(s == 0 for i, s in enumerate(row) if i != j))
    return {"chunks_with_unique_token": holders, "passed": passed}


# Draws, ties, hits ------------------------------------------------------------------------------


def draw(n_chunks: int, n_items: int, n_positive: int) -> tuple[list[np.ndarray], list[list[int]]]:
    """The tie keys of the items in id order, then the label-shuffle permutations; nothing else is drawn."""
    rng = np.random.default_rng(SEED)
    keys = [rng.permutation(n_chunks) for _ in range(n_items)]
    shuffles = [rng.permutation(n_positive).tolist() for _ in range(N_SHUFFLES)]
    return keys, shuffles


def ranking(scores: Sequence[float], key: Sequence[int]) -> Order:
    """Chunk indices by score descending, then key ascending."""
    return np.lexsort((np.asarray(key), -np.asarray(scores, dtype=np.float64))).tolist()


def is_hit(order: Order, targets: frozenset[int] | set[int], k: int) -> bool:
    return not targets.isdisjoint(order[:k])


def best_position(order: Order, targets: frozenset[int] | set[int]) -> int:
    return min(order.index(t) for t in targets) + 1


def acros_recovered(
    expected: Sequence[Sequence[str]], acro_index: Mapping[str, int], tops: Sequence[Order]
) -> int:
    """Distinct acros whose label is in the top k of some item that expects them."""
    return len(
        {
            acro
            for acros, top in zip(expected, tops, strict=True)
            for acro in acros
            if acro_index[acro] in top
        }
    )


def shuffled_h(tops: Sequence[Any], targets: Sequence[Any], pi: Sequence[int]) -> int:
    """H with item s_r given the expected set of item s_{pi[r]}."""
    return sum(not tops[r].isdisjoint(targets[pi[r]]) for r in range(len(tops)))


# Chance, McNemar, decision (D30-D34) -------------------------------------------------------------


def hit_probability(n: int, m: int, k: int) -> Fraction:
    return 1 - Fraction(math.comb(n - m, k), math.comb(n, k))


def poisson_binomial_tail(ps: Sequence[Fraction], h: int) -> Fraction:
    """P(X >= h) for independent Bernoulli(p_i), in exact arithmetic."""
    f = [Fraction(1)]
    for p in ps:
        f = [
            (1 - p) * (f[x] if x < len(f) else 0) + p * (f[x - 1] if x >= 1 else 0)
            for x in range(len(f) + 1)
        ]
    return sum(f[max(h, 0) :], Fraction(0))


def mcnemar_tail(b: int, c: int) -> Fraction:
    n = b + c
    return Fraction(sum(math.comb(n, j) for j in range(b, n + 1)), 2**n)


def passes(p: Fraction) -> bool:
    return p < ALPHA


def holds(chance_5: bool, mcnemar_5: bool, chance_1: bool, mcnemar_1: bool) -> bool:
    return all((chance_5, mcnemar_5, chance_1, mcnemar_1))


def fraction_record(p: Fraction) -> dict[str, Any]:
    return {"num": p.numerator, "den": p.denominator, "float": float(p)}


def compare_arms(
    ps: Sequence[Fraction], hits_engine: Sequence[bool], hits_bm25: Sequence[bool]
) -> dict[str, Any]:
    h_engine, h_bm25 = sum(hits_engine), sum(hits_bm25)
    b = sum(e and not x for e, x in zip(hits_engine, hits_bm25, strict=True))
    c = sum(x and not e for e, x in zip(hits_engine, hits_bm25, strict=True))
    return {
        "H_engine": h_engine,
        "H_bm25": h_bm25,
        "p_chance": poisson_binomial_tail(ps, h_engine),
        "b": b,
        "c": c,
        "p_mcnemar": mcnemar_tail(b, c),
    }


def unit_ids(expected: Mapping[int, Sequence[str]]) -> list[list[int]]:
    """Connected components of the positive items under 'the expected lists share an acro'."""
    parent = {i: i for i in expected}

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    owner: dict[str, int] = {}
    for i, acros in expected.items():
        for acro in acros:
            if acro in owner:
                parent[find(i)] = find(owner[acro])
            else:
                owner[acro] = i
    groups: dict[int, list[int]] = {}
    for i in sorted(expected):
        groups.setdefault(find(i), []).append(i)
    return sorted(groups.values())


def unit_hits(units: Sequence[Sequence[int]], hit_by_id: Mapping[int, bool]) -> list[bool]:
    return [any(hit_by_id[i] for i in unit) for unit in units]


def unit_probabilities(units: Sequence[Sequence[int]], p_by_id: Mapping[int, Fraction]) -> list[Fraction]:
    """q_u = 1 - prod(1 - p_i) over the items of the unit (D34)."""
    result = []
    for unit in units:
        none = Fraction(1)
        for i in unit:
            none *= 1 - p_by_id[i]
        result.append(1 - none)
    return result


# Measurement ------------------------------------------------------------------------------------


def _decision_block(figures: Mapping[str, Any], decide: bool) -> dict[str, Any]:
    chance_pass = passes(figures["p_chance"]) if decide else None
    mcnemar_pass = passes(figures["p_mcnemar"]) if decide else None
    return {
        "H_engine": figures["H_engine"],
        "H_bm25": figures["H_bm25"],
        "chance": {**fraction_record(figures["p_chance"]), "pass": chance_pass},
        "mcnemar": {
            "b": figures["b"],
            "c": figures["c"],
            "n": figures["b"] + figures["c"],
            **fraction_record(figures["p_mcnemar"]),
            "pass": mcnemar_pass,
        },
        "k_pass": (chance_pass and mcnemar_pass) if decide else None,
    }


def _group_block(figures: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "H_engine": figures["H_engine"],
        "H_bm25": figures["H_bm25"],
        "chance": fraction_record(figures["p_chance"]),
        "mcnemar": {
            "b": figures["b"],
            "c": figures["c"],
            "n": figures["b"] + figures["c"],
            **fraction_record(figures["p_mcnemar"]),
        },
    }


def _group_sensitivity(
    inp: Inputs,
    positives: Sequence[int],
    ps: Mapping[int, Sequence[Fraction]],
    hits_engine: Mapping[int, Sequence[bool]],
    hits_bm25: Mapping[int, Sequence[bool]],
) -> dict[str, Any]:
    ids = [inp.items[i].id for i in positives]
    units = unit_ids({inp.items[i].id: inp.items[i].acros for i in positives})
    block: dict[str, Any] = {"units": units}
    for k in KS:
        engine = unit_hits(units, dict(zip(ids, hits_engine[k], strict=True)))
        bm25 = unit_hits(units, dict(zip(ids, hits_bm25[k], strict=True)))
        q = unit_probabilities(units, dict(zip(ids, ps[k], strict=True)))
        block[f"k{k}"] = _group_block(compare_arms(q, engine, bm25))
    return block


def _arm_entry(order: Order | None, target: frozenset[int], labels: Sequence[str]) -> dict[str, Any]:
    if order is None:
        return {"position": None, "top5": None, **{f"k{k}": None for k in KS}}
    return {
        "position": best_position(order, target) if target else None,
        "top5": [labels[j] for j in order[:TOP]],
        **{f"k{k}": is_hit(order, target, k) if target else None for k in KS},
    }


def _distance_group(values: list[float]) -> dict[str, Any]:
    return {
        "values": values,
        "min": min(values),
        "median": statistics.median(values),
        "max": max(values),
    }


def _over(texts: Sequence[str], tokenizer: Callable[[str], Any], limit: int) -> int:
    return sum(len(tokenizer(text)["input_ids"]) > limit for text in texts)


def measure(
    inp: Inputs,
    acro_index: Mapping[str, int],
    provider: Any,
    model: Any,
    env: Mapping[str, Any],
    digests: Mapping[str, str],
) -> dict[str, Any]:
    n = len(inp.texts)
    items = inp.items
    queries = [item.query for item in items]
    targets = [frozenset(acro_index[acro] for acro in item.acros) for item in items]
    positives = [i for i, target in enumerate(targets) if target]

    first, second = encode_passes(provider, inp.texts, queries)
    v1 = all(row is not None for row in [*first, *second])
    keys, shuffles = draw(n, len(items), len(positives))

    index = bm25_index(inp.texts)
    bm25_rows = [bm25_scores(index, query) for query in queries]
    orders_bm25 = [ranking(row, key) for row, key in zip(bm25_rows, keys, strict=True)]

    orders_engine: list[Order] | None = None
    scores = chunks = None
    matched = differences = None
    if v1:
        chunks, query_rows = np.array(first[:n]), np.array(first[n:])
        scores = score_matrix(query_rows, chunks)
        orders_engine = [ranking(row, key) for row, key in zip(scores, keys, strict=True)]
        matched = alignment_matched(np.array(second), chunks, inp.texts)
        differences = sum(a.tobytes() != b.tobytes() for a, b in zip(first[:n], second, strict=True))
    v2 = v1 and matched == n
    failed = [name for name, ok in (("V1", v1), ("V2", v2)) if not ok]
    valid = not failed

    def hits(orders: list[Order], k: int) -> list[bool]:
        return [is_hit(orders[i], targets[i], k) for i in positives]

    ps = {k: [hit_probability(n, len(targets[i]), k) for i in positives] for k in KS}
    hits_bm25 = {k: hits(orders_bm25, k) for k in KS}
    hits_engine = {k: hits(orders_engine, k) for k in KS} if orders_engine is not None else None

    blocks: dict[int, dict[str, Any]] = {}
    for k in KS:
        if hits_engine is None:
            blocks[k] = {
                "H_engine": None,
                "H_bm25": sum(hits_bm25[k]),
                "chance": None,
                "mcnemar": None,
                "k_pass": None,
            }
        else:
            blocks[k] = _decision_block(compare_arms(ps[k], hits_engine[k], hits_bm25[k]), valid)

    shuffle = group = None
    if hits_engine is not None and orders_engine is not None:
        shuffle = {}
        positive_targets = [targets[i] for i in positives]
        for k in KS:
            tops = [frozenset(orders_engine[i][:k]) for i in positives]
            h_engine = sum(hits_engine[k])
            count = sum(shuffled_h(tops, positive_targets, pi) >= h_engine for pi in shuffles)
            shuffle[f"k{k}"] = {"count": count, "total": len(shuffles), "fraction": count / len(shuffles)}
        group = _group_sensitivity(inp, positives, ps, hits_engine, hits_bm25)

    expected = [items[i].acros for i in positives]
    recovered = {"distinct_expected": len({acro for acros in expected for acro in acros})}
    for arm, orders in (("engine", orders_engine), ("bm25", orders_bm25)):
        recovered[arm] = (
            None
            if orders is None
            else {
                f"k{k}": acros_recovered(expected, acro_index, [orders[i][:k] for i in positives])
                for k in KS
            }
        )

    report_items = [
        {
            "id": item.id,
            "m": len(target),
            "engine": _arm_entry(orders_engine[i] if orders_engine is not None else None, target, inp.labels),
            "bm25": {
                **_arm_entry(orders_bm25[i], target, inp.labels),
                "positive_scores": sum(s > 0 for s in bm25_rows[i]),
            },
        }
        for i, (item, target) in enumerate(zip(items, targets, strict=True))
    ]

    nearest = citation = None
    if scores is not None and chunks is not None:
        by_group = {"n0": [], "p": []}
        for i, row in enumerate(scores):
            by_group["p" if targets[i] else "n0"].append(distance(float(row.max())))
        nearest = {name: _distance_group(values) for name, values in by_group.items()}
        within = int(sum(distance(float(np.dot(chunks[a], chunks[b]))) <= EPSILON for a, b in inp.citations))
        citation = {
            "pairs": len(inp.citations),
            "within": within,
            "fraction": within / len(inp.citations),
            "epsilon": EPSILON,
        }

    words = [len(text.split()) for text in inp.texts]
    q1, median, q3 = np.percentile(words, [25, 50, 75])
    over_chunks = _over(inp.texts, model.tokenizer, model.max_seq_length)
    over_queries = _over(queries, model.tokenizer, model.max_seq_length)

    return {
        "valid": valid,
        "first_failed": failed[0] if failed else None,
        "failed": failed,
        "digests": dict(digests),
        "environment": dict(env),
        "vectors_sha256": matrix_sha256(first) if v1 else None,
        "alignment_vectors_sha256": matrix_sha256(second) if v1 else None,
        "counts": {
            "chunks": n,
            "distinct_texts": len(set(inp.texts)),
            "items": len(items),
            "positives": len(positives),
            "chunk_texts_over_max_seq_length": over_chunks,
            "query_texts_over_max_seq_length": over_queries,
        },
        "alignment": {"matched": matched, "required": n, "bitwise_differences": differences},
        **{f"k{k}": blocks[k] for k in KS},
        "holds": holds(
            blocks[5]["chance"]["pass"],
            blocks[5]["mcnemar"]["pass"],
            blocks[1]["chance"]["pass"],
            blocks[1]["mcnemar"]["pass"],
        )
        if valid
        else None,
        "holds_limit": INDEPENDENCE_LIMIT,
        "shuffle": shuffle,
        "bm25_check": bm25_check(inp.texts, lambda query: bm25_scores(index, query)),
        "group_sensitivity": group,
        "report_only": {
            "items": report_items,
            "acros_recovered": recovered,
            "bm25_fewer_than_k_positive": {
                f"k{k}": sum(sum(s > 0 for s in bm25_rows[i]) < k for i in positives) for k in KS
            },
            "nearest_chunk_distance": nearest,
            "words_per_chunk": {
                "min": min(words),
                "q1": float(q1),
                "median": float(median),
                "q3": float(q3),
                "max": max(words),
                "at_most_10": sum(w <= 10 for w in words),
            },
            "truncation": {
                "max_seq_length": model.max_seq_length,
                "chunk_texts": over_chunks,
                "query_texts": over_queries,
            },
            "bitwise_second_pass_differences": differences,
            "citation_fraction": citation,
        },
    }


# Output and entry point -------------------------------------------------------------------------


def write_result(result: Mapping[str, Any], path: Path) -> None:
    """json.dumps first, so a NaN or Infinity refuses before any file is touched."""
    text = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    Path(path).write_bytes(text.encode("utf-8"))


def run(
    out: Path,
    paths: Mapping[str, Path],
    digests: Mapping[str, str],
    resolve_epsilon: Callable[[], float],
    build: Callable[[], Any],
    provider: Any,
) -> int:
    try:
        raw = read_verified(paths, digests)
        inp = parse_inputs(raw)
        acro_index = resolve_acros(inp)
        check_epsilon(resolve_epsilon)
        model = load_encoder(build, MODEL_REVISION)
        result = measure(
            inp,
            acro_index,
            provider,
            model,
            environment(model),
            {Path(paths[name]).name: digests[name] for name in paths},
        )
    except Refusal as refusal:
        print(f"{refusal.identifier} {REFUSALS[refusal.identifier]}: {refusal}", file=sys.stderr)
        return 1
    write_result(result, out)
    print(f"wrote {out}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--out", type=Path, default=RESULT)
    args = parser.parse_args(argv)
    return run(
        args.out, PATHS, EXPECTED_DIGESTS, resolve_epsilon_edge, build_encoder, SentenceTransformerProvider()
    )


if __name__ == "__main__":
    sys.exit(main())
