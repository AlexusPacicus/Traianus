"""Load the frozen Spinoza artefact into the engine one note at a time, and verify the stored bits.

`load` ingests the artefact's vectors in text order through POST /ingesta/vector, one request per
note, never in bulk and never by re-encoding texts (frontend/POC.md, Corpus loading). The engine does
not deduplicate a repeated idempotency key, so a request is never retried: any failure stops the run,
and a later run resumes by skipping the labels GET /nodos already lists.

`verify` opens a database read-only and compares, byte for byte, the current revision of each node
with v-hat = row / sqrt(row @ row) in binary64, the vector the K6 measurement uses.

Both commands follow frontend/audits/contracts.md section 0: each artefact is read once, its sha256 is
checked on those bytes, the same bytes are parsed, and the null elimination runs before anything else.

Usage:
    TRAIANUS_TOKEN=... python3 tools/experiments/tooling/load_spinoza_corpus.py load --url http://127.0.0.1:8000
    python3 tools/experiments/tooling/load_spinoza_corpus.py verify --db traianus.db
Exit 0 on success, 1 when refused or failed, 2 on usage.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
import platform
import re
import sqlite3
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from http.client import HTTPConnection, HTTPException
from pathlib import Path
from typing import Any

for _var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ[_var] = "1"

import numpy as np
from numpy.typing import NDArray

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / ".data"
DEFAULT_ARTEFACTS = DATA_DIR / "spinoza_frozen"
DEFAULT_REPORT = DATA_DIR / "spinoza_load_report.json"
TOKEN_ENV = "TRAIANUS_TOKEN"
NORM_TOL = 3e-5
TIMEOUT_SECONDS = 60
LABEL_RE = re.compile(r"[A-Za-z0-9_-]{1,64}")
LOOPBACK_URL = re.compile(r"http://(?P<host>127\.0\.0\.1|localhost)(?::(?P<port>[0-9]{1,5}))?/?")
TRANSPORT_ERRORS = (OSError, HTTPException)

Transport = Callable[[str, str, Mapping[str, str], bytes | None], tuple[int, bytes]]


@dataclass(frozen=True)
class Expected:
    embeddings_sha256: str
    labels_sha256: str
    shape: tuple[int, int]
    part_counts: tuple[int, ...]


EXPECTED = Expected(
    "eafb0e97172830f2404e96fa08d74bf6cccc0b6cbe84d47b790a476603e7d8d1",
    "1d60699353d810f089730c6203ee28f9c416e3004b60781bc965cec284097f4f",
    (2221, 384),
    (409, 458, 627, 507, 220),
)


@dataclass(frozen=True)
class Corpus:
    vectors: NDArray[np.float32]
    labels: list[str]
    embeddings_sha256: str
    labels_sha256: str


@dataclass
class Outcome:
    loaded: list[str] = field(default_factory=list)
    skipped: int = 0
    failure: dict[str, Any] | None = None


@dataclass(frozen=True)
class Verdict:
    mismatched: int
    missing: int
    first_mismatch: str | None
    first_missing: str | None


class Refused(Exception):
    """The run is refused or has failed; the message is the reason."""


# Artefacts ----------------------------------------------------------------------------------------


def _read(directory: Path, name: str, digest: str) -> bytes:
    path = directory / name
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise Refused(f"{name}: cannot read {path}: {exc}") from exc
    actual = hashlib.sha256(data).hexdigest()
    if actual != digest:
        raise Refused(f"{name}: sha256 {actual} does not match {digest}")
    return data


def _check_embeddings(data: bytes, shape: tuple[int, int]) -> NDArray[np.float32]:
    try:
        array = np.load(io.BytesIO(data), allow_pickle=False)
    except (ValueError, OSError, EOFError) as exc:
        raise Refused(f"embeddings.npy: not a readable NPY file: {exc}") from exc
    if not isinstance(array, np.ndarray) or array.dtype != np.dtype("<f4"):
        raise Refused(f"embeddings.npy: dtype {getattr(array, 'dtype', type(array))} is not <f4")
    if not array.flags.c_contiguous:
        raise Refused("embeddings.npy: not C order")
    if array.shape != shape:
        raise Refused(f"embeddings.npy: shape {array.shape} is not {shape}")
    for i, row in enumerate(array.astype("<f8")):
        if not np.all(np.isfinite(row)):
            raise Refused(f"row {i}: non-finite value")
        norm = float(np.sqrt(row @ row))
        if abs(norm - 1.0) > NORM_TOL:
            raise Refused(f"row {i}: norm {norm!r} outside 1 +- {NORM_TOL}")
    return array


def _check_labels(data: bytes, rows: int, part_counts: tuple[int, ...]) -> list[str]:
    try:
        items = json.loads(data.decode("utf-8"))
    except ValueError as exc:
        raise Refused(f"labels.json: not UTF-8 JSON: {exc}") from exc
    if not isinstance(items, list):
        raise Refused("labels.json: not a list")
    labels: list[str] = []
    seen: dict[str, int] = {}
    parts: dict[str, int] = {}
    for i, item in enumerate(items):
        if not isinstance(item, dict) or set(item) != {"label", "part"}:
            raise Refused(f"label {i}: not an object with exactly the keys label and part")
        label, part = item["label"], item["part"]
        if not isinstance(label, str) or not label:
            raise Refused(f"label {i}: label is null or empty")
        if not isinstance(part, str) or not part:
            raise Refused(f"label {i}: part is null or empty")
        if LABEL_RE.fullmatch(label) is None:
            raise Refused(f"label {i} {label!r}: does not match [A-Za-z0-9_-]{{1,64}}")
        if label in seen:
            raise Refused(f"label {i} {label!r}: duplicate of label {seen[label]}")
        seen[label] = i
        parts[part] = parts.get(part, 0) + 1
        labels.append(label)
    if len(labels) != rows:
        raise Refused(f"label count {len(labels)} != row count {rows}")
    if tuple(parts.values()) != part_counts:
        raise Refused(f"part counts {tuple(parts.values())} != {part_counts}")
    return labels


def load_corpus(directory: Path, expected: Expected) -> Corpus:
    """Digest check on the bytes read, then null elimination on the same bytes (contracts.md section 0)."""
    directory = Path(directory)
    embeddings = _read(directory, "embeddings.npy", expected.embeddings_sha256)
    labels = _read(directory, "labels.json", expected.labels_sha256)
    vectors = _check_embeddings(embeddings, expected.shape)
    names = _check_labels(labels, expected.shape[0], expected.part_counts)
    return Corpus(vectors, names, expected.embeddings_sha256, expected.labels_sha256)


def v_hat(row: NDArray[np.float32]) -> NDArray[np.float64]:
    wide = row.astype("<f8")
    return wide / np.sqrt(wide @ wide)  # type: ignore[no-any-return]


# Where the run may reach and write ----------------------------------------------------------------


def loopback_endpoint(url: str) -> tuple[str, int]:
    match = LOOPBACK_URL.fullmatch(url)
    port = int(match["port"]) if match and match["port"] else 80
    if match is None or not 0 < port < 65536:
        raise Refused(f"url {url!r} is not http://127.0.0.1[:port] or http://localhost[:port]")
    return match["host"], port


def check_report_path(path: Path) -> Path:
    resolved = Path(path).resolve()
    if resolved.is_relative_to(REPO_ROOT) and not resolved.is_relative_to(DATA_DIR):
        raise Refused(f"report {resolved} is inside the repository tree; use .data/ or a path outside it")
    return resolved


def make_transport(
    host: str, port: int, connect: Callable[..., HTTPConnection] = HTTPConnection
) -> Transport:
    def transport(
        method: str, path: str, headers: Mapping[str, str], body: bytes | None
    ) -> tuple[int, bytes]:
        connection = connect(host, port, timeout=TIMEOUT_SECONDS)
        try:
            connection.request(method, path, body=body, headers=dict(headers))
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()

    return transport


# load ---------------------------------------------------------------------------------------------


def _send(
    transport: Transport, method: str, path: str, headers: Mapping[str, str], body: bytes | None
) -> tuple[int, bytes]:
    try:
        return transport(method, path, headers, body)
    except TRANSPORT_ERRORS as exc:
        raise Refused(f"{type(exc).__name__}: {exc}") from exc


def _reply(payload: bytes) -> dict[str, Any]:
    try:
        data = json.loads(payload)
    except ValueError as exc:
        raise Refused("response body is not JSON") from exc
    if not isinstance(data, dict):
        raise Refused("response body is not a JSON object")
    return data


def _existing_ids(transport: Transport) -> set[str]:
    status, body = _send(transport, "GET", "/nodos", {}, None)
    if status != 200:
        raise Refused(f"status {status}")
    nodes = _reply(body).get("nodes")
    if not isinstance(nodes, list) or not all(
        isinstance(node, dict) and isinstance(node.get("id"), str) for node in nodes
    ):
        raise Refused("response has no list of nodes with an id")
    return {node["id"] for node in nodes}


def _post_row(transport: Transport, token: str, key: str, node_id: str, body: bytes) -> None:
    headers = {
        "X-Traianus-Token": token,
        "X-Idempotency-Key": key,
        "Content-Type": "application/json",
    }
    status, payload = _send(transport, "POST", "/ingesta/vector", headers, body)
    if status != 201:
        raise Refused(f"status {status}: {payload.decode('utf-8', 'replace')[:200]}")
    reply = _reply(payload)
    if reply.get("node_id") != node_id or reply.get("seq") != 1:
        raise Refused(f"reply node_id {reply.get('node_id')!r}, seq {reply.get('seq')!r}")


def _failure(index: int | None, label: str | None, reason: str, token: str) -> dict[str, Any]:
    return {"index": index, "label": label, "reason": reason.replace(token, "***")}


def run_load(corpus: Corpus, transport: Transport, token: str, limit: int) -> Outcome:
    """Never retries: the first failure ends the run, recorded in the outcome."""
    outcome = Outcome()
    try:
        existing = _existing_ids(transport)
    except Refused as exc:
        outcome.failure = _failure(None, None, f"GET /nodos: {exc}", token)
        return outcome
    for index in range(limit):
        label = corpus.labels[index]
        node_id = f"VEC_{label}"
        if node_id in existing:
            outcome.skipped += 1
            continue
        key = f"spinoza-{index:04d}-{corpus.embeddings_sha256[:12]}"
        vector = corpus.vectors[index].astype(np.float64).tolist()
        body = json.dumps({"vector": vector, "label": label}, allow_nan=False).encode("utf-8")
        try:
            _post_row(transport, token, key, node_id, body)
        except Refused as exc:
            outcome.failure = _failure(index, label, str(exc), token)
            break
        outcome.loaded.append(label)
    return outcome


def _environment() -> dict[str, str]:
    config = io.StringIO()
    with contextlib.redirect_stdout(config):
        np.show_config()
    return {
        "numpy": np.__version__,
        "numpy_config": config.getvalue(),
        "platform": platform.platform(),
    }


def write_report(path: Path, corpus: Corpus, outcome: Outcome, limit: int) -> None:
    report = {
        "digests": {
            "embeddings.npy": corpus.embeddings_sha256,
            "labels.json": corpus.labels_sha256,
        },
        "environment": _environment(),
        "limit": limit,
        "loaded": len(outcome.loaded),
        "loaded_labels": outcome.loaded,
        "skipped": outcome.skipped,
        "failed": int(outcome.failure is not None),
        "first_failure": outcome.failure,
    }
    text = json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    except OSError as exc:
        raise Refused(f"report {path}: {exc}") from exc


# verify -------------------------------------------------------------------------------------------


def readonly_uri(db: Path) -> str:
    return f"{Path(db).resolve().as_uri()}?mode=ro"


def run_verify(db: Path, corpus: Corpus, limit: int) -> Verdict:
    """The current revision (highest seq) of each of the first `limit` nodes against v-hat."""
    mismatched = missing = 0
    first_mismatch = first_missing = None
    try:
        conn = sqlite3.connect(readonly_uri(db), uri=True)
        try:
            for index in range(limit):
                label = corpus.labels[index]
                row = conn.execute(
                    "SELECT vector_blob FROM manifold_nodes WHERE id = ? ORDER BY seq DESC LIMIT 1",
                    (f"VEC_{label}",),
                ).fetchone()
                if row is None:
                    missing += 1
                    first_missing = first_missing or label
                elif row[0] != v_hat(corpus.vectors[index]).tobytes():
                    mismatched += 1
                    first_mismatch = first_mismatch or label
        finally:
            conn.close()
    except sqlite3.Error as exc:
        raise Refused(f"cannot read {db} read-only: {exc}") from exc
    return Verdict(mismatched, missing, first_mismatch, first_missing)


# Command line -------------------------------------------------------------------------------------


def _positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"{text!r} is not a positive integer") from exc
    if value < 1:
        raise argparse.ArgumentTypeError(f"{text!r} is not a positive integer")
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Load the frozen Spinoza artefact; verify the stored bits.")
    commands = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (("load", "ingest the vectors one at a time"), ("verify", "compare stored bits")):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("--artefacts", type=Path, default=DEFAULT_ARTEFACTS)
        command.add_argument("--limit", type=_positive_int, default=None, help="first N rows only")
        if name == "load":
            command.add_argument("--url", required=True, help="http://127.0.0.1[:port] or localhost")
            command.add_argument("--report", type=Path, default=DEFAULT_REPORT)
        else:
            command.add_argument("--db", type=Path, required=True)
    return parser


def _limit(requested: int | None, corpus: Corpus) -> int:
    rows = len(corpus.labels)
    if requested is None:
        return rows
    if requested > rows:
        raise Refused(f"limit {requested} exceeds the row count {rows}")
    return requested


def _describe(failure: dict[str, Any]) -> str:
    if failure["index"] is None:
        return str(failure["reason"])
    return f"row {failure['index']} {failure['label']}: {failure['reason']}"


def _run_load(args: argparse.Namespace, transport: Transport | None, expected: Expected) -> int:
    host, port = loopback_endpoint(args.url)
    token = os.environ.get(TOKEN_ENV, "")
    if not token:
        raise Refused(f"{TOKEN_ENV} is not set")
    report = check_report_path(args.report)
    corpus = load_corpus(args.artefacts, expected)
    limit = _limit(args.limit, corpus)
    outcome = run_load(corpus, transport or make_transport(host, port), token, limit)
    write_report(report, corpus, outcome, limit)
    failed = int(outcome.failure is not None)
    print(f"load: loaded {len(outcome.loaded)}, skipped {outcome.skipped}, failed {failed} of {limit} rows -> {report}")
    if outcome.failure is not None:
        print(f"load: {_describe(outcome.failure)}", file=sys.stderr)
        return 1
    return 0


def _run_verify(args: argparse.Namespace, expected: Expected) -> int:
    corpus = load_corpus(args.artefacts, expected)
    limit = _limit(args.limit, corpus)
    verdict = run_verify(args.db, corpus, limit)
    holding = limit - verdict.mismatched - verdict.missing
    print(f"verify: {holding} of {limit} labels hold v-hat bit for bit")
    if holding == limit:
        return 0
    print(
        f"verify: {verdict.mismatched} mismatched, {verdict.missing} missing; "
        f"first mismatch {verdict.first_mismatch}; first missing {verdict.first_missing}",
        file=sys.stderr,
    )
    return 1


def main(
    argv: Sequence[str] | None = None, *, transport: Transport | None = None, expected: Expected = EXPECTED
) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "load":
            return _run_load(args, transport, expected)
        return _run_verify(args, expected)
    except Refused as exc:
        print(f"{args.command}: refused")
        print(f"{args.command}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
