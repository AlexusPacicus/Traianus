"""P1 provider baseline — Qwen3-Embedding-0.6B (exploration on the development set).

Implements the section "Línea base de proveedor: Qwen3-Embedding-0.6B" of docs/roadmap/NEXT_RESEARCH.md,
frozen at 8cfebc5 (LEDGER seq 100): P1's corpus, test set, BM25, seed, epsilon and checks, with
Qwen/Qwen3-Embedding-0.6B as provider in two versions, 1024 (the float32 output) and 384 (its first 384
components), each query encoded behind a fixed instruction. MiniLM's arm is read from
data/math/P1_result.json, never re-run. The only decision, per version, is an exact one-sided Wilcoxon
signed-rank test of the 18 positive items' positions, MiniLM minus Qwen3 (pass iff valid and p < 1/20);
everything else is report-only. The measurement block of each version is P1's own measure().

Refuses to run, and writes nothing, on P1's refusals RF1-RF5 (RF5 also when a parameter is not float32),
RF6 (the MiniLM arm: digest, strict JSON, valid != true, structure, items) and RF7 (the formula split does
not partition the positive items). A run that completes but fails a check (V1 vectors, V2 alignment, V3
BM25 equal to the stored one) is written with valid = false and no decision.

Usage:
    python3 tools/experiments/p1_qwen3_provider.py [--out PATH] [--timing-out PATH]
"""

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_var] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

import argparse
import json
import math
import platform
import resource
import statistics
import sys
import time
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.experiments import p1_beezer_retrieval as p1
from traianus.config import resolve_epsilon_edge

MODEL_ID = "Qwen/Qwen3-Embedding-0.6B"
QWEN_REVISION = "97b0c614be4d77ee51c0cef4e5f07c00f9eb65b3"
INSTRUCTION = (
    "Instruct: Given a description of a mathematical concept, retrieve the definition or theorem that states it"
    + "\n"
    + "Query:"
)
FULL_DIM = 1024
VERSIONS = {"1024": FULL_DIM, "384": p1.DIM}
MINILM_SHA256 = "00522a30465ae3dc21a949aca6d5464c9060f99d2a50038c05f088976c9132d8"
RESULT = p1.DATA / "P1_qwen3_result.json"
TIMING = p1.DATA / "P1_qwen3_timing.json"
EMPTIED = (1, 2, 6, 7, 13, 15, 18, 23, 24, 25, 28)
KEPT = (11, 12, 14, 16, 17, 21, 27)
REFUSALS = {**p1.REFUSALS, "RF6": "minilm_arm", "RF7": "formula_split"}
DECIDES = "only versions.<dimension>.wilcoxon.pass decides; everything under report_only decides nothing"
SPLIT_SOURCE = (
    "taken from P1's post-result reading (docs/roadmap/NEXT_RESEARCH.md), which came after P1's result; "
    "report-only"
)


# Report-only figures and the decision -------------------------------------------------------------


def wilcoxon(d: Sequence[float]) -> dict[str, Any]:
    """Exact one-sided signed-rank test: zeros dropped, midranks of |d|, p = P(W+ >= observed) over 2^n signs."""
    nonzero = [x for x in d if x != 0]
    count = Counter(abs(x) for x in nonzero)
    doubled: dict[float, int] = {}
    rank = 1
    for value in sorted(count):
        doubled[value] = 2 * rank + count[value] - 1
        rank += count[value]
    ways: Counter[int] = Counter({0: 1})
    for x in nonzero:
        ways = ways + Counter({s + doubled[abs(x)]: c for s, c in ways.items()})
    total = sum(doubled[abs(x)] for x in nonzero)
    observed = sum(doubled[abs(x)] for x in nonzero if x > 0)
    reaching = sum(c for s, c in ways.items() if s >= observed)
    return {
        "n": len(nonzero),
        "dropped_zeros": len(d) - len(nonzero),
        "w_plus": Fraction(observed, 2),
        "w_minus": Fraction(total - observed, 2),
        "p": Fraction(reaching, 2 ** len(nonzero)),
    }


def wilcoxon_pass(p: Fraction, valid: bool) -> bool | None:
    return p1.passes(p) if valid else None


def rank_metrics(positions: Sequence[int]) -> dict[str, float]:
    n = len(positions)
    return {
        "mrr": math.fsum(1 / p for p in positions) / n,
        "recall_10": sum(p <= 10 for p in positions) / n,
        "recall_20": sum(p <= 20 for p in positions) / n,
        "median_position": statistics.median(positions),
    }


def mcnemar_against(qwen: Sequence[bool], minilm: Sequence[bool]) -> dict[str, Any]:
    """One-sided exact McNemar, Qwen3 as the engine: b = Qwen3 hit and MiniLM miss, c = the reverse."""
    b = sum(q and not m for q, m in zip(qwen, minilm, strict=True))
    c = sum(m and not q for q, m in zip(qwen, minilm, strict=True))
    return {"b": b, "c": c, "n": b + c, **p1.fraction_record(p1.mcnemar_tail(b, c))}


def auc(positive: Sequence[float], none: Sequence[float]) -> Fraction:
    """P(a positive item's nearest-chunk distance is below a none item's); a tie counts one half."""
    wins = sum((p < n) + Fraction(p == n, 2) for p in positive for n in none)
    return Fraction(wins) / (len(positive) * len(none))


def split_check(ids: Sequence[int], emptied: Sequence[int], kept: Sequence[int]) -> None:
    union = [*emptied, *kept]
    if len(set(union)) != len(union) or set(union) != set(ids):
        raise p1.Refusal("RF7", f"the formula split is not a partition of the positive item ids {sorted(ids)}")


def _split_arm(values: Sequence[int]) -> dict[str, Any]:
    return {
        "hits_k5": sum(p <= 5 for p in values),
        "hits_k1": sum(p <= 1 for p in values),
        "median_position": statistics.median(values),
        "mrr": math.fsum(1 / p for p in values) / len(values),
    }


def split_block(
    emptied: Sequence[int], kept: Sequence[int], arms: Mapping[str, Mapping[int, int] | None]
) -> dict[str, Any]:
    block: dict[str, Any] = {"source": SPLIT_SOURCE}
    for group, ids in (("emptied", emptied), ("kept", kept)):
        block[group] = {
            "ids": list(ids),
            "arms": {
                arm: None if positions is None else _split_arm([positions[i] for i in ids])
                for arm, positions in arms.items()
            },
        }
    return block


# MiniLM's arm ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class MiniLmArm:
    positions: dict[int, int]
    bm25: dict[int, tuple[int | None, list[str]]]
    distances: dict[str, list[float]]


def read_minilm(path: Path, digest: str) -> MiniLmArm:
    """P1_result.json, verified, strict JSON, valid; the figures this baseline compares against (RF6)."""
    try:
        doc = p1.parse_strict_json(p1.read_verified({"minilm": path}, {"minilm": digest})["minilm"])
    except p1.Refusal as refusal:
        raise p1.Refusal("RF6", str(refusal)) from refusal
    if not isinstance(doc, dict) or doc.get("valid") is not True:
        raise p1.Refusal("RF6", "the MiniLM result is not an object with valid == true")
    try:
        items = doc["report_only"]["items"]
        distances = doc["report_only"]["nearest_chunk_distance"]
        return MiniLmArm(
            {item["id"]: item["engine"]["position"] for item in items if item["engine"]["position"] is not None},
            {item["id"]: (item["bm25"]["position"], item["bm25"]["top5"]) for item in items},
            {group: list(distances[group]["values"]) for group in ("p", "n0")},
        )
    except (KeyError, TypeError) as exc:
        raise p1.Refusal("RF6", f"the MiniLM result lacks the expected structure: {exc!r}") from exc


def check_minilm_items(minilm: MiniLmArm, items: Sequence[p1.Item]) -> None:
    if sorted(minilm.bm25) != [item.id for item in items]:
        raise p1.Refusal("RF6", "the MiniLM result's items are not the test set's")
    if set(minilm.positions) != {item.id for item in items if item.acros}:
        raise p1.Refusal("RF6", "the MiniLM result's positive items are not the test set's")


# Encoder (RF5) --------------------------------------------------------------------------------------


def build_qwen3() -> Any:
    import torch
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(
        MODEL_ID,
        revision=QWEN_REVISION,
        local_files_only=True,
        device="cpu",
        model_kwargs={"dtype": torch.float32, "attn_implementation": "eager"},
    )


def load_qwen3(build: Callable[[], Any], revision: str) -> Any:
    """The encoder as P1 loads its own (offline, pinned revision, cpu), with every parameter in float32."""
    model = p1.load_encoder(build, revision, QWEN_REVISION)
    other = sorted({str(parameter.dtype) for parameter in model.parameters()} - {"torch.float32"})
    if other:
        raise p1.Refusal("RF5", f"encoder parameters in {other}, not float32")
    return model


def environment(model: Any, minilm_sha256: str) -> dict[str, Any]:
    import transformers

    return {
        **p1.environment(model),
        "transformers": transformers.__version__,
        "model_id": MODEL_ID,
        "revision": QWEN_REVISION,
        "parameter_dtype": str(next(model.parameters()).dtype),
        "attention_implementation": model[0].auto_model.config._attn_implementation,
        "instruction": INSTRUCTION,
        "minilm_result_sha256": minilm_sha256,
    }


# Encoding, timed ------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Outputs:
    first: list[Any]
    second: list[Any]
    plain: list[Any]


class Timed:
    """The encoder's single-text calls; the duration of each is kept by kind."""

    def __init__(self, model: Any, clock: Callable[[], int]) -> None:
        self.model, self.clock = model, clock
        self.durations: dict[str, list[int]] = {"chunk": [], "query": []}

    def encode(self, text: str, kind: str) -> Any:
        start = self.clock()
        output = self.model.encode(text)
        self.durations[kind].append(self.clock() - start)
        return output


def encode_all(timed: Timed, texts: Sequence[str], queries: Sequence[str]) -> Outputs:
    """P1's two passes (chunks then instructed queries, chunks again), then the queries without it."""
    first = [timed.encode(text, "chunk") for text in texts]
    first += [timed.encode(INSTRUCTION + query, "query") for query in queries]
    second = [timed.encode(text, "chunk") for text in texts]
    return Outputs(first, second, [timed.encode(query, "query") for query in queries])


class Replay:
    """Hands P1's measurement the recorded outputs, in the order its passes ask for them."""

    def __init__(self, texts: Sequence[str], outputs: Sequence[Any]) -> None:
        self._calls = iter(zip(texts, outputs, strict=True))

    def encode(self, text: str) -> Any:
        expected, output = next(self._calls)
        if text != expected:
            raise RuntimeError(f"replay out of order: asked for {text!r}, recorded {expected!r}")
        return output


def for_version(output: Any, dim: int) -> Any:
    """The 1024 output as is, or its first components; None when the 1024 output is not a float32 vector."""
    if dim == FULL_DIM:
        return output
    ok = isinstance(output, np.ndarray) and output.ndim == 1 and output.dtype == np.float32
    return output[:dim] if ok and output.size == FULL_DIM else None


# Measurement ------------------------------------------------------------------------------------------


def invalidate(measured: dict[str, Any], name: str) -> None:
    """A failed check after measure(): every decision field of P1's block becomes null."""
    measured["valid"] = False
    measured["failed"].append(name)
    measured["first_failed"] = measured["failed"][0]
    measured["holds"] = None
    for k in p1.KS:
        block = measured[f"k{k}"]
        block["k_pass"] = None
        for figure in ("chance", "mcnemar"):
            if block[figure] is not None:
                block[figure]["pass"] = None


def bm25_mismatches(minilm: MiniLmArm, items: Sequence[Mapping[str, Any]]) -> list[int]:
    """V3: the ids whose recomputed BM25 position or top5 differ from the stored ones."""
    return [
        item["id"]
        for item in items
        if (item["bm25"]["position"], item["bm25"]["top5"]) != minilm.bm25[item["id"]]
    ]


def no_instruction(
    inp: p1.Inputs,
    acro_index: Mapping[str, int],
    keys: Sequence[Any],
    chunk_outputs: Sequence[Any],
    plain_outputs: Sequence[Any],
    dim: int,
) -> dict[str, Any] | None:
    """The queries without the instruction against the version's first-pass chunk vectors, same tie keys."""
    queries = [item.query for item in inp.items]
    chunks = p1.encode_texts(Replay(inp.texts, chunk_outputs), inp.texts, dim)
    rows = p1.encode_texts(Replay(queries, plain_outputs), queries, dim)
    if any(row is None for row in [*chunks, *rows]):
        return None
    scores = p1.score_matrix(np.array(rows), np.array(chunks))
    found = []
    for item, row, key in zip(inp.items, scores, keys, strict=True):
        if item.acros:
            order = p1.ranking(row, key)
            found.append({"id": item.id, "position": p1.best_position(order, {acro_index[a] for a in item.acros})})
    items = [{**entry, "k5": entry["position"] <= 5, "k1": entry["position"] <= 1} for entry in found]
    return {
        "items": items,
        "H_k5": sum(entry["k5"] for entry in items),
        "H_k1": sum(entry["k1"] for entry in items),
        "rank_metrics": rank_metrics([entry["position"] for entry in items]),
    }


def _wilcoxon_block(
    minilm: Mapping[int, int], qwen: Mapping[int, int] | None, ids: Sequence[int], valid: bool
) -> dict[str, Any]:
    if qwen is None:
        names = ("n", "dropped_zeros", "w_plus", "w_minus", "p", "pass", "pairs")
        return dict.fromkeys(names)
    pairs = [{"id": i, "minilm": minilm[i], "qwen3": qwen[i], "d": minilm[i] - qwen[i]} for i in ids]
    w = wilcoxon([pair["d"] for pair in pairs])
    return {
        "n": w["n"],
        "dropped_zeros": w["dropped_zeros"],
        "w_plus": float(w["w_plus"]),
        "w_minus": float(w["w_minus"]),
        "p": p1.fraction_record(w["p"]),
        "pass": wilcoxon_pass(w["p"], valid),
        "pairs": pairs,
    }


def version_block(
    dim: int,
    measured: dict[str, Any],
    plain: dict[str, Any] | None,
    minilm: MiniLmArm,
    ids: Sequence[int],
    emptied: Sequence[int],
    kept: Sequence[int],
) -> dict[str, Any]:
    items = measured["report_only"]["items"]
    engine = {item["id"]: item["engine"]["position"] for item in items if item["m"]}
    qwen = None if None in engine.values() else engine
    bm25 = {item["id"]: item["bm25"]["position"] for item in items if item["m"]}
    distances = measured["report_only"]["nearest_chunk_distance"]
    return {
        "dimension": dim,
        "valid": measured["valid"],
        "first_failed": measured["first_failed"],
        "failed": list(measured["failed"]),
        "wilcoxon": _wilcoxon_block(minilm.positions, qwen, ids, measured["valid"]),
        "report_only": {
            "p1_measurement": measured,
            "mcnemar_vs_minilm": None
            if qwen is None
            else {
                f"k{k}": mcnemar_against([qwen[i] <= k for i in ids], [minilm.positions[i] <= k for i in ids])
                for k in p1.KS
            },
            "rank_metrics": {
                "minilm": rank_metrics([minilm.positions[i] for i in ids]),
                "qwen3": None if qwen is None else rank_metrics([qwen[i] for i in ids]),
                "bm25": rank_metrics([bm25[i] for i in ids]),
            },
            "no_instruction": plain,
            "auc": None
            if distances is None
            else p1.fraction_record(auc(distances["p"]["values"], distances["n0"]["values"])),
            "split": split_block(emptied, kept, {"minilm": minilm.positions, "qwen3": qwen, "bm25": bm25}),
        },
    }


def _item_rows(
    ids: Sequence[int], minilm: MiniLmArm, blocks: Mapping[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    rows = []
    for i in ids:
        row: dict[str, Any] = {"id": i, "minilm_position": minilm.positions[i], "bm25_position": None, "versions": {}}
        for name, block in blocks.items():
            measured = block["report_only"]["p1_measurement"]["report_only"]["items"]
            item = next(entry for entry in measured if entry["id"] == i)
            row["bm25_position"] = item["bm25"]["position"]
            plain = block["report_only"]["no_instruction"]
            row["versions"][name] = {
                "position": item["engine"]["position"],
                "top5": item["engine"]["top5"],
                "no_instruction_position": None
                if plain is None
                else next(entry["position"] for entry in plain["items"] if entry["id"] == i),
            }
        rows.append(row)
    return rows


def measure(
    inp: p1.Inputs,
    acro_index: Mapping[str, int],
    model: Any,
    outputs: Outputs,
    minilm: MiniLmArm,
    emptied: Sequence[int],
    kept: Sequence[int],
    env: Mapping[str, Any],
    digests: Mapping[str, str],
) -> dict[str, Any]:
    texts, n = inp.texts, len(inp.texts)
    queries = [item.query for item in inp.items]
    ids = [item.id for item in inp.items if item.acros]
    keys, _ = p1.draw(n, len(inp.items), len(ids))
    over_queries = sum(len(model.tokenizer(INSTRUCTION + q)["input_ids"]) > model.max_seq_length for q in queries)

    measured: dict[str, dict[str, Any]] = {}
    plain: dict[str, dict[str, Any] | None] = {}
    for name, dim in VERSIONS.items():
        first = [for_version(u, dim) for u in outputs.first]
        second = [for_version(u, dim) for u in outputs.second]
        replay = Replay([*texts, *queries, *texts], [*first, *second])
        measured[name] = p1.measure(inp, acro_index, replay, model, {}, {}, dim)
        del measured[name]["digests"], measured[name]["environment"]
        measured[name]["counts"]["query_texts_over_max_seq_length"] = over_queries
        measured[name]["report_only"]["truncation"]["query_texts"] = over_queries
        plain[name] = no_instruction(inp, acro_index, keys, first[:n], [for_version(u, dim) for u in outputs.plain], dim)

    mismatched = bm25_mismatches(minilm, measured["1024"]["report_only"]["items"])
    if mismatched:
        for block in measured.values():
            invalidate(block, "V3")
    blocks = {
        name: version_block(dim, measured[name], plain[name], minilm, ids, emptied, kept)
        for name, dim in VERSIONS.items()
    }
    failed = [f"{name}:{check}" for name, b in blocks.items() for check in b["failed"] if check != "V3"]
    if mismatched:
        failed.append("V3")
    return {
        "valid": not failed,
        "first_failed": failed[0] if failed else None,
        "failed": failed,
        "decides": DECIDES,
        "digests": dict(digests),
        "environment": dict(env),
        "bm25_vs_minilm_result": {"items": len(inp.items), "mismatched_ids": mismatched},
        "versions": blocks,
        "report_only": {
            "minilm_auc": p1.fraction_record(auc(minilm.distances["p"], minilm.distances["n0"])),
            "items": _item_rows(ids, minilm, blocks),
        },
    }


# Output and entry point -------------------------------------------------------------------------


def timing_document(durations: Mapping[str, Sequence[int]]) -> dict[str, Any]:
    def summary(nanoseconds: Sequence[int]) -> dict[str, Any]:
        milliseconds = np.array(nanoseconds) / 1e6
        return {
            "count": len(nanoseconds),
            "p50_ms": float(np.percentile(milliseconds, 50)),
            "p95_ms": float(np.percentile(milliseconds, 95)),
        }

    return {
        "chunk_calls": summary(durations["chunk"]),
        "query_calls": summary(durations["query"]),
        "peak_resident_memory": {
            "ru_maxrss": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "unit": "bytes" if platform.system() == "Darwin" else "kilobytes",
            "platform": platform.system(),
        },
    }


def write_outputs(documents: Mapping[Path, Mapping[str, Any]]) -> None:
    """Every file is serialised (allow_nan=False) before any is written."""
    texts = {
        path: json.dumps(document, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        for path, document in documents.items()
    }
    for path, text in texts.items():
        Path(path).write_bytes(text.encode("utf-8"))


def run(
    out: Path,
    timing_out: Path,
    paths: Mapping[str, Path],
    digests: Mapping[str, str],
    minilm_path: Path,
    minilm_digest: str,
    resolve_epsilon: Callable[[], float],
    build: Callable[[], Any],
    *,
    emptied: Sequence[int] = EMPTIED,
    kept: Sequence[int] = KEPT,
    clock: Callable[[], int] = time.perf_counter_ns,
) -> int:
    try:
        inp = p1.parse_inputs(p1.read_verified(paths, digests))
        acro_index = p1.resolve_acros(inp)
        p1.check_epsilon(resolve_epsilon)
        model = load_qwen3(build, QWEN_REVISION)
        minilm = read_minilm(minilm_path, minilm_digest)
        check_minilm_items(minilm, inp.items)
        split_check([item.id for item in inp.items if item.acros], emptied, kept)
        timed = Timed(model, clock)
        outputs = encode_all(timed, inp.texts, [item.query for item in inp.items])
        result = measure(
            inp,
            acro_index,
            model,
            outputs,
            minilm,
            emptied,
            kept,
            environment(model, minilm_digest),
            {Path(paths[name]).name: digests[name] for name in paths},
        )
    except p1.Refusal as refusal:
        print(f"{refusal.identifier} {REFUSALS[refusal.identifier]}: {refusal}", file=sys.stderr)
        return 1
    write_outputs({out: result, timing_out: timing_document(timed.durations)})
    print(f"wrote {out} and {timing_out}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--out", type=Path, default=RESULT)
    parser.add_argument("--timing-out", type=Path, default=TIMING)
    args = parser.parse_args(argv)
    return run(
        args.out,
        args.timing_out,
        p1.PATHS,
        p1.EXPECTED_DIGESTS,
        p1.RESULT,
        MINILM_SHA256,
        resolve_epsilon_edge,
        build_qwen3,
    )


if __name__ == "__main__":
    sys.exit(main())
