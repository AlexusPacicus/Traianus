"""P1 engine gate — P1's retrieval restricted to the nodes the engine consolidates (exploration).

Implements the section "La puerta del motor sobre P1" of docs/roadmap/NEXT_RESEARCH.md, frozen at c848364
(LEDGER seq 102, with its correction). P1's chunks go through the engine in process over a fresh temporary base:
/ingesta/vector with P1's first-pass vector, then /nodos/{id}/consolidar with the ethical key true (approval by
source). The candidates are the nodes whose last revision is consolidated, which by the engine's dual key means
sigma^2 >= theta_dyn; P1's ranking and tie keys are applied to them, and a statement that is not a candidate is
lost (position = chunks + 1). The only decision is the conjunction of an exact one-sided Wilcoxon against P1's
positions (p < 1/20) and a same-size random-subset control (p_random < 1/20); everything else is report-only.

Refuses to run, and writes nothing, on P1's refusals RF1-RF5, the MiniLM arm (RF6), the formula split (RF7) and
the engine (RF8): the engine's provider not offline or not at P1's pinned revision, a bootstrap failure, any
unexpected answer during ingestion or consolidation. A run that completes but fails a check (V1 unfiltered
ranking equal to the stored one, V2 BM25 equal to the stored one, V3 manifold_nodes unchanged by the query phase)
is written with valid = false and no decision.

Usage:
    python3 tools/experiments/p1_engine_gate.py [--out PATH]
"""

import os

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_var] = "1"
os.environ.setdefault("HF_HUB_OFFLINE", "1")

import argparse
import hashlib
import json
import secrets
import sqlite3
import sys
import tempfile
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

import numpy as np
from fastapi.testclient import TestClient

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from tools.experiments import p1_beezer_retrieval as p1
from tools.experiments import p1_qwen3_provider as q3
from traianus import app as engine
from traianus import bootstrap, storage
from traianus.config import resolve_epsilon_edge
from traianus.representation.sentence_transformer import (
    MODEL_REVISION,
    SentenceTransformerProvider,
    build_encoder,
)

PROTOCOL_COMMIT = "c848364"
RESULT = p1.DATA / "P1_gate_result.json"
N_DRAWS = 10_000
DRAW_SEED = 20261005
KEY_PREFIX = "p1-gate-"
CONSOLIDATED = "consolidated"
REFUSALS = {**q3.REFUSALS, "RF8": "engine"}
DECIDES = (
    "only decision.pass decides; everything under report_only decides nothing. "
    "Exploration: the 28 items were seen before this protocol, so nothing is confirmed"
)
MULTIPLICITY = "no multiplicity correction: two conditions, each at 1/20, both required"

Scored = tuple[list[int], dict[str, Any]]


# Position among the candidates and the random control ------------------------------------------------


def candidates_of(states: Sequence[str]) -> list[int]:
    return [j for j, state in enumerate(states) if state == CONSOLIDATED]


def restricted_order(scores: np.ndarray, key: np.ndarray, subset: Sequence[int]) -> p1.Order:
    """P1's ranking over the chunks of the subset only, each with its own tie key."""
    members = np.asarray(subset, dtype=np.intp)
    return members[p1.ranking(scores[members], key[members])].tolist()


def gate_position(order: Sequence[int], targets: frozenset[int] | set[int], n_chunks: int) -> int:
    """1-based place of the best expected statement that is in the order; none in it: lost, n_chunks + 1."""
    surviving = set(targets).intersection(order)
    return p1.best_position(list(order), surviving) if surviving else n_chunks + 1


def subset_scorer(
    scores: np.ndarray,
    keys: Sequence[np.ndarray],
    targets: Sequence[frozenset[int]],
    positives: Sequence[int],
    p1_positions: Sequence[int],
    n_chunks: int,
) -> Callable[[Sequence[int]], Scored]:
    """One rule for the gate and for every draw: positions of the positive items among a subset, and the
    Wilcoxon of P1's position minus the subset's."""

    def score(subset: Sequence[int]) -> Scored:
        positions = [
            gate_position(restricted_order(scores[i], keys[i], subset), targets[i], n_chunks) for i in positives
        ]
        return positions, q3.wilcoxon([a - b for a, b in zip(p1_positions, positions, strict=True)])

    return score


def random_control(
    scorer: Callable[[Sequence[int]], Scored],
    n_chunks: int,
    n_pass: int,
    p_gate: Fraction,
    n_draws: int = N_DRAWS,
    seed: int = DRAW_SEED,
) -> dict[str, Any]:
    """p_random = (1 + #{draws whose Wilcoxon p is <= the gate's}) / (n_draws + 1), draws in sequence."""
    rng = np.random.default_rng(seed)
    count = sum(scorer(rng.choice(n_chunks, size=n_pass, replace=False))[1]["p"] <= p_gate for _ in range(n_draws))
    return {"draws": n_draws, "seed": seed, "count": count, "p": Fraction(1 + count, n_draws + 1)}


def decision(
    valid: bool,
    n_chunks: int,
    n_pass: int,
    w: Mapping[str, Any],
    control: Mapping[str, Any] | None,
    pairs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """The only figure with a pass field: nothing is decided unless valid and applicable."""
    applicable = 0 < n_pass < n_chunks
    live = valid and applicable
    pass_w = p1.passes(w["p"]) if live else None
    pass_r = p1.passes(control["p"]) if live and control is not None else None
    return {
        "applicable": applicable,
        "wilcoxon": {
            "n": w["n"],
            "dropped_zeros": w["dropped_zeros"],
            "w_plus": float(w["w_plus"]),
            "w_minus": float(w["w_minus"]),
            "p": p1.fraction_record(w["p"]),
            "pass": pass_w,
            "pairs": list(pairs),
        },
        "random_control": None
        if control is None
        else {
            "draws": control["draws"],
            "seed": control["seed"],
            "count": control["count"],
            "p": p1.fraction_record(control["p"]),
            "pass": pass_r,
        },
        "pass": None if pass_r is None else bool(pass_w and pass_r),
        "multiplicity": MULTIPLICITY,
    }


# P1's rule with the gate (report-only) ---------------------------------------------------------------


def chance_probability(n: int, m: int, k: int) -> Fraction:
    """Chance that k of n candidates hold one of the m expected ones that survive; 0 when none survives."""
    if m == 0:
        return Fraction(0)
    return Fraction(1) if k >= n else p1.hit_probability(n, m, k)


def p1_rule(
    positions: Sequence[int], bm25_positions: Sequence[int], surviving: Sequence[int], n_pass: int
) -> dict[str, Any]:
    block: dict[str, Any] = {}
    for k in p1.KS:
        ps = [chance_probability(n_pass, m, k) for m in surviving]
        figures = p1.compare_arms(ps, [p <= k for p in positions], [p <= k for p in bm25_positions])
        block[f"k{k}"] = {
            "H_gate": figures["H_engine"],
            "H_bm25": figures["H_bm25"],
            "chance": {**p1.fraction_record(figures["p_chance"]), "below_alpha": p1.passes(figures["p_chance"])},
            "mcnemar": {
                "b": figures["b"],
                "c": figures["c"],
                "n": figures["b"] + figures["c"],
                **p1.fraction_record(figures["p_mcnemar"]),
                "below_alpha": p1.passes(figures["p_mcnemar"]),
            },
        }
    block["holds"] = p1.holds(
        *(block[f"k{k}"][figure]["below_alpha"] for k in p1.KS for figure in ("chance", "mcnemar"))
    )
    return block


# The engine, in process ------------------------------------------------------------------------------


@dataclass(frozen=True)
class Session:
    client: Any
    headers: dict[str, str]
    db_path: Path


@dataclass(frozen=True, eq=False)
class Revision:
    seq: int
    state: str
    vector: np.ndarray
    epoch: str


@dataclass(frozen=True)
class Read:
    revisions: list[list[Revision]]
    digest_before: str
    digest_after: str


def check_engine_provider(revision: str, environ: Mapping[str, str]) -> None:
    if revision != p1.PINNED_REVISION:
        raise p1.Refusal("RF8", f"the engine's MODEL_REVISION {revision} is not P1's pinned {p1.PINNED_REVISION}")
    if environ.get("HF_HUB_OFFLINE") != "1":
        raise p1.Refusal("RF8", "the engine's provider is not offline: HF_HUB_OFFLINE is not 1")


@contextmanager
def fresh_engine() -> Iterator[Session]:
    """A bootstrapped engine over a fresh temporary base, in process; DB_PATH and the token are restored and
    the directory removed on exit, also when the body raises."""
    previous_path = storage.DB_PATH
    previous_token = os.environ.get("TRAIANUS_TOKEN")
    token = secrets.token_hex(16)
    with tempfile.TemporaryDirectory(prefix="p1-gate-") as directory:
        db_path = Path(directory) / "gate.db"
        try:
            storage.DB_PATH = str(db_path)
            os.environ["TRAIANUS_TOKEN"] = token
            try:
                bootstrap.main()
            except (OSError, ValueError, RuntimeError, ImportError, sqlite3.Error) as exc:
                raise p1.Refusal("RF8", f"bootstrap failed: {exc}") from exc
            client = TestClient(engine.app, raise_server_exceptions=False)
            yield Session(client, {"X-Traianus-Token": token}, db_path)
        finally:
            storage.DB_PATH = previous_path
            if previous_token is None:
                os.environ.pop("TRAIANUS_TOKEN", None)
            else:
                os.environ["TRAIANUS_TOKEN"] = previous_token


def _answer(response: Any, status: int, step: str) -> Any:
    if response.status_code != status:
        raise p1.Refusal("RF8", f"{step}: HTTP {response.status_code}, expected {status}")
    try:
        return response.json()
    except ValueError as exc:
        raise p1.Refusal("RF8", f"{step}: the answer is not JSON") from exc


def ingest_and_consolidate(
    session: Session, labels: Sequence[str], texts: Sequence[str], vectors: Sequence[np.ndarray]
) -> list[dict[str, Any]]:
    """Per chunk, in order: /ingesta/vector (201, incubating), then /nodos/VEC_<label>/consolidar (200)."""
    records = []
    for label, text, vector in zip(labels, texts, vectors, strict=True):
        node_id = f"VEC_{label}"
        ingested = _answer(
            session.client.post(
                "/ingesta/vector",
                json={"vector": vector.tolist(), "label": label, "text": text},
                headers={**session.headers, "X-Idempotency-Key": KEY_PREFIX + label},
            ),
            201,
            f"ingestion of {label}",
        )
        if not isinstance(ingested, dict) or ingested.get("lifecycle_state") != "incubating":
            raise p1.Refusal("RF8", f"ingestion of {label}: the node is not incubating")
        consolidated = _answer(
            session.client.post(
                f"/nodos/{node_id}/consolidar",
                json={"text": text, "ethical_key": True},
                headers=session.headers,
            ),
            200,
            f"consolidation of {label}",
        )
        try:
            key = consolidated["dual_key_status"]["topological_key"]
            records.append(
                {
                    "key": label,
                    "node_id": node_id,
                    "sigma2_ingest": float(ingested["spectral_variance"]),
                    "sigma2": float(key["variance"]),
                    "theta_dyn": float(key["threshold"]),
                    "topological_passed": bool(key["passed"]),
                    "new_state": str(consolidated["new_state"]),
                }
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise p1.Refusal("RF8", f"consolidation of {label}: unexpected answer {exc!r}") from exc
    return records


# The query phase: read-only, and R2 --------------------------------------------------------------------


def open_readonly(db_path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"{Path(db_path).resolve().as_uri()}?mode=ro", uri=True)


def table_digest(conn: sqlite3.Connection) -> str:
    """sha256 of every row of manifold_nodes, all columns, ordered by (id, seq), serialised canonically."""
    cursor = conn.execute("SELECT * FROM manifold_nodes ORDER BY id, seq")
    digest = hashlib.sha256()
    digest.update(json.dumps([column[0] for column in cursor.description]).encode("utf-8") + b"\n")
    for row in cursor:
        cells = [{"blob": cell.hex()} if isinstance(cell, bytes) else cell for cell in row]
        digest.update(json.dumps(cells, ensure_ascii=False, allow_nan=False).encode("utf-8") + b"\n")
    return digest.hexdigest()


def read_revisions(conn: sqlite3.Connection, node_ids: Sequence[str]) -> list[list[Revision]]:
    revisions = []
    for node_id in node_ids:
        rows = conn.execute(
            "SELECT seq, lifecycle_state, vector_blob, epoch_provenance FROM manifold_nodes WHERE id = ? ORDER BY seq",
            (node_id,),
        ).fetchall()
        revisions.append(
            [Revision(seq, state, np.frombuffer(blob, dtype=np.float64).copy(), epoch) for seq, state, blob, epoch in rows]
        )
    return revisions


def query_phase(db_path: Path, node_ids: Sequence[str]) -> Read:
    """Reads each node's revisions through a read-only connection, the table digested before and after."""
    conn = open_readonly(db_path)
    try:
        before = table_digest(conn)
        revisions = read_revisions(conn, node_ids)
        after = table_digest(conn)
    finally:
        conn.close()
    for node_id, history in zip(node_ids, revisions, strict=True):
        if len(history) != 2 or history[0].state != "incubating" or any(r.vector.size != p1.DIM for r in history):
            raise p1.Refusal("RF8", f"{node_id}: the base does not hold one ingested and one consolidating revision")
    return Read(revisions, before, after)


# Inputs and measurement --------------------------------------------------------------------------------


def read_stored_engine(path: Path, digest: str) -> dict[int, tuple[int | None, list[str]]]:
    """P1_result.json's engine arm, every item: (position, top5)."""
    try:
        doc = p1.parse_strict_json(p1.read_verified({"minilm": path}, {"minilm": digest})["minilm"])
    except p1.Refusal as refusal:
        raise p1.Refusal("RF6", str(refusal)) from refusal
    try:
        return {item["id"]: (item["engine"]["position"], item["engine"]["top5"]) for item in doc["report_only"]["items"]}
    except (KeyError, TypeError) as exc:
        raise p1.Refusal("RF6", f"the MiniLM result lacks the expected structure: {exc!r}") from exc


def encode_first_pass(provider: Any, inp: p1.Inputs) -> tuple[np.ndarray, np.ndarray]:
    """P1's first pass: the chunks, then the queries; a row failing P1's vector checks refuses (RF5)."""
    rows = p1.encode_texts(provider, [*inp.texts, *[item.query for item in inp.items]])
    failed = [i for i, row in enumerate(rows) if row is None]
    if failed:
        raise p1.Refusal("RF5", f"{len(failed)} encoder outputs fail P1's vector checks, the first at row {failed[0]}")
    n = len(inp.texts)
    return np.array(rows[:n]), np.array(rows[n:])


def vector_differences(sent: np.ndarray, revisions: Sequence[Revision]) -> dict[str, Any]:
    return {
        "of": len(revisions),
        "byte_identical": sum(r.vector.tobytes() == s.tobytes() for r, s in zip(revisions, sent, strict=True)),
        "max_abs_difference": float(max(np.max(np.abs(r.vector - s)) for r, s in zip(revisions, sent, strict=True))),
    }


def measure(
    inp: p1.Inputs,
    acro_index: Mapping[str, int],
    minilm: q3.MiniLmArm,
    stored: Mapping[int, tuple[int | None, list[str]]],
    sent: np.ndarray,
    query_rows: np.ndarray,
    records: Sequence[Mapping[str, Any]],
    read: Read,
    env: Mapping[str, Any],
    digests: Mapping[str, str],
    emptied: Sequence[int],
    kept: Sequence[int],
    n_draws: int = N_DRAWS,
) -> dict[str, Any]:
    n, items, labels = len(inp.texts), inp.items, inp.labels
    targets = [frozenset(acro_index[acro] for acro in item.acros) for item in items]
    positives = [i for i, target in enumerate(targets) if target]
    ids = [items[i].id for i in positives]
    keys, _ = p1.draw(n, len(items), len(positives))

    last = [history[-1] for history in read.revisions]
    states = [revision.state for revision in last]
    scores = p1.score_matrix(query_rows, np.array([revision.vector for revision in last]))

    def top(order: Sequence[int]) -> list[str]:
        return [labels[j] for j in order[: p1.TOP]]

    unfiltered = [p1.ranking(row, key) for row, key in zip(scores, keys, strict=True)]
    v1 = [
        item.id
        for item, order, target in zip(items, unfiltered, targets, strict=True)
        if (p1.best_position(order, target) if target else None, top(order)) != stored[item.id]
    ]
    index = p1.bm25_index(inp.texts)
    bm25_orders = [p1.ranking(p1.bm25_scores(index, item.query), key) for item, key in zip(items, keys, strict=True)]
    recomputed = [
        {"id": item.id, "bm25": {"position": p1.best_position(order, target) if target else None, "top5": top(order)}}
        for item, order, target in zip(items, bm25_orders, targets, strict=True)
    ]
    v2 = q3.bm25_mismatches(minilm, recomputed)
    v3 = read.digest_before == read.digest_after
    failed = [name for name, ok in (("V1", not v1), ("V2", not v2), ("V3", v3)) if not ok]
    valid = not failed

    candidates = candidates_of(states)
    n_pass = len(candidates)
    member = set(candidates)
    p1_positions = [minilm.positions[i] for i in ids]
    scorer = subset_scorer(scores, keys, targets, positives, p1_positions, n)
    positions, w = scorer(candidates)
    control = random_control(scorer, n, n_pass, w["p"], n_draws) if 0 < n_pass < n else None
    pairs = [{"id": i, "p1": a, "gate": b, "d": a - b} for i, a, b in zip(ids, p1_positions, positions, strict=True)]

    surviving = {items[i].id: [acro for acro in items[i].acros if acro_index[acro] in member] for i in positives}
    gate_orders = {items[i].id: restricted_order(scores[i], keys[i], candidates) for i in positives}
    bm25_positions = [minilm.bm25[i][0] for i in ids]
    rows = [
        {
            "id": i,
            "p1_position": minilm.positions[i],
            "gate_position": position,
            "gate_top5": top(gate_orders[i]),
            "surviving_expected": surviving[i],
            "bm25_position": bm25_position,
        }
        for i, position, bm25_position in zip(ids, positions, bm25_positions, strict=True)
    ]

    nearest: dict[str, list[float]] | None = None
    if candidates:
        nearest = {"p": [], "n0": []}
        for i, row in enumerate(scores):
            nearest["p" if targets[i] else "n0"].append(p1.distance(float(row[candidates].max())))
    auc = None
    if nearest is not None and nearest["p"] and nearest["n0"]:
        auc = p1.fraction_record(q3.auc(nearest["p"], nearest["n0"]))

    groups: dict[str, list[int]] = {}
    for j, text in enumerate(inp.texts):
        groups.setdefault(text, []).append(j)
    expected = {acro for i in positives for acro in items[i].acros}
    thetas = sorted({record["theta_dyn"] for record in records})

    return {
        "valid": valid,
        "first_failed": failed[0] if failed else None,
        "failed": failed,
        "decides": DECIDES,
        "digests": dict(digests),
        "environment": {
            **env,
            "engine_model_revision": MODEL_REVISION,
            "epoch_provenance": sorted({r.epoch for history in read.revisions for r in history}),
            "protocol_commit": PROTOCOL_COMMIT,
        },
        "counts": {"chunks": n, "items": len(items), "positives": len(positives), "candidates": n_pass},
        "validity": {
            "V1": {"mismatched_ids": v1},
            "V2": {"mismatched_ids": v2},
            "V3": {"equal": v3},
        },
        "decision": decision(valid, n, n_pass, w, control, pairs),
        "report_only": {
            "n_pass": n_pass,
            "theta_dyn": records[0]["theta_dyn"],
            "theta_dyn_distinct": len(thetas),
            "expected_statements": {
                "distinct": len(expected),
                "surviving": sum(acro_index[acro] in member for acro in expected),
            },
            "duplicated_texts": [
                {"text": text, "keys": [labels[j] for j in js], "states": [states[j] for j in js]}
                for text, js in groups.items()
                if len(js) > 1
            ],
            "chunks": [
                {
                    "key": label,
                    "sigma2": record["sigma2"],
                    "sigma2_ingest": record["sigma2_ingest"],
                    "threshold": record["theta_dyn"],
                    "topological_passed": record["topological_passed"],
                    "state": state,
                }
                for label, record, state in zip(labels, records, states, strict=True)
            ],
            "vector_differences": {
                "ingested": vector_differences(sent, [history[0] for history in read.revisions]),
                "consolidated": vector_differences(sent, last),
            },
            "p1_rule": p1_rule(positions, bm25_positions, [len(surviving[i]) for i in ids], n_pass),
            "mcnemar_gate_vs_p1": {
                f"k{k}": q3.mcnemar_against([p <= k for p in positions], [p <= k for p in p1_positions])
                for k in p1.KS
            },
            "rank_metrics": {
                "gate": q3.rank_metrics(positions),
                "p1": q3.rank_metrics(p1_positions),
                "bm25": q3.rank_metrics(bm25_positions),
            },
            "nearest_candidate_distance": nearest,
            "auc": auc,
            "split": q3.split_block(
                emptied,
                kept,
                {"p1": minilm.positions, "gate": dict(zip(ids, positions, strict=True)), "bm25": dict(zip(ids, bm25_positions, strict=True))},
            ),
            "items": rows,
        },
    }


# Entry point -------------------------------------------------------------------------------------------


def run(
    out: Path,
    paths: Mapping[str, Path],
    digests: Mapping[str, str],
    minilm_path: Path,
    minilm_digest: str,
    resolve_epsilon: Callable[[], float],
    build: Callable[[], Any],
    provider: Any,
    *,
    emptied: Sequence[int] = q3.EMPTIED,
    kept: Sequence[int] = q3.KEPT,
    n_draws: int = N_DRAWS,
) -> int:
    try:
        inp = p1.parse_inputs(p1.read_verified(paths, digests))
        acro_index = p1.resolve_acros(inp)
        p1.check_epsilon(resolve_epsilon)
        model = p1.load_encoder(build, p1.MODEL_REVISION)
        minilm = q3.read_minilm(minilm_path, minilm_digest)
        q3.check_minilm_items(minilm, inp.items)
        stored = read_stored_engine(minilm_path, minilm_digest)
        q3.split_check([item.id for item in inp.items if item.acros], emptied, kept)
        check_engine_provider(MODEL_REVISION, os.environ)
        sent, query_rows = encode_first_pass(provider, inp)
        with fresh_engine() as session:
            records = ingest_and_consolidate(session, inp.labels, inp.texts, sent)
            read = query_phase(session.db_path, [f"VEC_{label}" for label in inp.labels])
        result = measure(
            inp,
            acro_index,
            minilm,
            stored,
            sent,
            query_rows,
            records,
            read,
            {**p1.environment(model), "minilm_result_sha256": minilm_digest},
            {Path(paths[name]).name: digests[name] for name in paths},
            emptied,
            kept,
            n_draws,
        )
    except p1.Refusal as refusal:
        print(f"{refusal.identifier} {REFUSALS[refusal.identifier]}: {refusal}", file=sys.stderr)
        return 1
    p1.write_result(result, out)
    print(f"wrote {out}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--out", type=Path, default=RESULT)
    args = parser.parse_args(argv)
    return run(
        args.out,
        p1.PATHS,
        p1.EXPECTED_DIGESTS,
        p1.RESULT,
        q3.MINILM_SHA256,
        resolve_epsilon_edge,
        build_encoder,
        SentenceTransformerProvider(),
    )


if __name__ == "__main__":
    sys.exit(main())
