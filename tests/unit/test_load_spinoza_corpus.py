"""Unit tests of tools/experiments/tooling/load_spinoza_corpus.py.

Specification: docs/methodology/instrument-audit/contracts.md §0 (digests on the parsed bytes, null elimination, v-hat)
and the corpus-loading decision of frontend/POC.md. Synthetic artefacts and an injected transport
only: CI has no .data/, and no test opens a connection. One guard reads the real artefact when present.
"""

import ast
import hashlib
import io
import json
import re
import sqlite3
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from tools.audit import context_pack
from tools.experiments.tooling import load_spinoza_corpus as tool

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOL = REPO_ROOT / "tools" / "experiments" / "tooling" / "load_spinoza_corpus.py"
REGISTRY = REPO_ROOT / "tools" / "hooks" / "contract_registry.json"
FROZEN = REPO_ROOT / ".data" / "spinoza_frozen"
MANIFESTS = REPO_ROOT / "data" / "spinoza"
CONTRACT = "docs/methodology/instrument-audit/contracts.md"
SECTION_0 = "0. Data layer, bit level (shared)"

D = 384
N = 12
PARTS = (5, 4, 3)
URL = "http://127.0.0.1:8000"
TOKEN = "tok-7f3c9a1e5b"


@pytest.fixture(autouse=True)
def _token(monkeypatch, operator_token_env):
    monkeypatch.setenv("TRAIANUS_TOKEN", TOKEN)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _unit_rows(n, seed=20260919):
    x = np.random.default_rng(seed).standard_normal((n, D)).astype(np.float32)
    return x / np.linalg.norm(x, axis=1, keepdims=True)


def _npy(array, *, fortran=False):
    buffer = io.BytesIO()
    np.save(buffer, np.asfortranarray(array) if fortran else array, allow_pickle=False)
    return buffer.getvalue()


def _labels(counts=PARTS):
    return [
        {"label": f"P{p}_N{k:02d}", "part": f"P{p}"}
        for p, count in enumerate(counts)
        for k in range(count)
    ]


def _replace(index, **fields):
    labels = _labels()
    labels[index] = {**labels[index], **fields}
    return labels


def _keys(counts=PARTS):
    return [entry["label"] for entry in _labels(counts)]


def _sentence(label):
    """Leading and trailing blanks, a doubled space, a combining accent, curly quotes, a backslash and a
    newline: what a strip, a normalisation or a re-encoding would alter."""
    return f"  {label}: la  sustancia, é “dice” \\ x\n"


def _split(items, counts):
    parts, start = [], 0
    for count in counts[:-1]:
        parts.append(items[start : start + count])
        start += count
    return [*parts, items[start:]]


def _manifest_names(counts=PARTS):
    return [f"part{i + 1}_manifest.json" for i in range(len(counts))]


def _object_bytes(pairs):
    """A JSON object written pair by pair, so that a test can repeat a key."""
    body = ", ".join(f"{json.dumps(key)}: {json.dumps(value, ensure_ascii=False)}" for key, value in pairs)
    return ("{" + body + "}").encode("utf-8")


def _manifest_bytes(keys, counts=PARTS):
    return [_object_bytes([(key, _sentence(key)) for key in part]) for part in _split(keys, counts)]


def _pairs(part):
    return [(key, _sentence(key)) for key in _split(_keys(), PARTS)[part]]


def _manifests_with(part, data):
    manifests = _manifest_bytes(_keys())
    manifests[part] = data
    return manifests


@dataclass
class Staged:
    directory: Path
    manifests: Path
    expected: tool.Expected
    vectors: np.ndarray
    labels: list
    sentences: list


def _stage(
    directory, *, vectors=None, labels=None, npy=None, shape=(N, D), counts=PARTS, keys=None, manifests=None
):
    vectors = _unit_rows(N) if vectors is None else vectors
    labels = _labels() if labels is None else labels
    embeddings = _npy(vectors) if npy is None else npy
    keys = _keys(counts) if keys is None else keys
    manifests = _manifest_bytes(keys, counts) if manifests is None else manifests
    text = json.dumps(labels).encode("utf-8")
    folder = directory / "manifests"
    folder.mkdir(parents=True, exist_ok=True)
    (directory / "embeddings.npy").write_bytes(embeddings)
    (directory / "labels.json").write_bytes(text)
    names = _manifest_names(counts)
    for name, data in zip(names, manifests):
        (folder / name).write_bytes(data)
    digests = tuple((name, _sha(data)) for name, data in zip(names, manifests))
    expected = tool.Expected(_sha(embeddings), _sha(text), shape, counts, digests)
    return Staged(directory, folder, expected, vectors, labels, [_sentence(key) for key in keys])


@pytest.fixture
def staged(tmp_path):
    return _stage(tmp_path / "artefacts")


class Engine:
    """The two routes the loader uses, in memory. Every call is recorded; `faults` maps the index of a
    POST (or "GET") to a (status, body) reply, or to an exception to raise."""

    def __init__(self, existing=(), faults=None):
        self.calls = []
        self.nodes = list(existing)
        self.faults = dict(faults or {})

    @property
    def posts(self):
        return [call for call in self.calls if call[0] == "POST"]

    def __call__(self, method, path, headers, body):
        self.calls.append((method, path, dict(headers), body))
        assert (method, path) in {("GET", "/nodos"), ("POST", "/ingesta/vector")}
        fault = self.faults.get("GET" if method == "GET" else len(self.posts) - 1)
        if isinstance(fault, BaseException):
            raise fault
        if fault is not None:
            return fault
        if method == "GET":
            nodes = [{"id": node_id} for node_id in self.nodes]
            return 200, json.dumps({"status": "SUCCESS", "nodes": nodes}).encode()
        node_id = f"VEC_{json.loads(body)['label']}"
        self.nodes.append(node_id)
        return 201, json.dumps({"status": "accepted", "node_id": node_id, "seq": 1}).encode()


def _load(staged, engine, tmp_path, capsys, *extra, url=URL):
    report = tmp_path / "report.json"
    argv = ["load", "--url", url, "--artefacts", str(staged.directory), "--manifests", str(staged.manifests)]
    argv += ["--report", str(report), *extra]
    code = tool.main(argv, transport=engine, expected=staged.expected)
    captured = capsys.readouterr()
    return code, captured.out, captured.err, report


def _verify(staged, db, capsys, *extra):
    argv = ["verify", "--db", str(db), "--artefacts", str(staged.directory), "--manifests", str(staged.manifests)]
    argv += list(extra)
    code = tool.main(argv, expected=staged.expected)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def _refused(staged, tmp_path, capsys):
    engine = Engine()
    code, _out, err, _report = _load(staged, engine, tmp_path, capsys)
    assert code == 1
    assert engine.calls == []
    return err


# T1: integrity refusals, before any request


@pytest.mark.parametrize("name", ["embeddings.npy", "labels.json"])
@pytest.mark.parametrize("where", ["first", "header", "middle", "last"])
def test_one_flipped_bit_in_an_artefact_is_refused_by_the_digest(staged, tmp_path, capsys, name, where):
    path = staged.directory / name
    data = bytearray(path.read_bytes())
    data[{"first": 0, "header": 20, "middle": len(data) // 2, "last": -1}[where]] ^= 0x01
    path.write_bytes(bytes(data))
    err = _refused(staged, tmp_path, capsys)
    assert name in err
    assert "sha256" in err


@pytest.mark.parametrize(
    ("build", "fragment"),
    [
        pytest.param(lambda v: _npy(v.astype(np.float64)), "dtype", id="float64"),
        pytest.param(lambda v: _npy(v.astype(">f4")), "dtype", id="big_endian"),
        pytest.param(lambda v: _npy(v, fortran=True), "C order", id="fortran"),
        pytest.param(lambda v: _npy(v[:-1]), "shape", id="one_row_short"),
        pytest.param(lambda v: _npy(v[:, :-1]), "shape", id="one_column_short"),
    ],
)
def test_a_wrong_npy_header_is_refused(tmp_path, capsys, build, fragment):
    staged = _stage(tmp_path / "bad", npy=build(_unit_rows(N)))
    assert fragment in _refused(staged, tmp_path, capsys)


@pytest.mark.parametrize("value", [np.nan, np.inf, -np.inf])
def test_a_non_finite_value_is_refused_naming_the_row(tmp_path, capsys, value):
    vectors = _unit_rows(N)
    vectors[4, 7] = value
    err = _refused(_stage(tmp_path / "bad", vectors=vectors), tmp_path, capsys)
    assert re.search(r"row 4\b", err)


@pytest.mark.parametrize("scale", [1 + 3.1e-5, 1 - 3.1e-5])
def test_a_row_norm_outside_the_tolerance_is_refused_naming_the_row(tmp_path, capsys, scale):
    vectors = _unit_rows(N)
    vectors[3] *= np.float32(scale)
    err = _refused(_stage(tmp_path / "bad", vectors=vectors), tmp_path, capsys)
    assert re.search(r"row 3\b", err)


@pytest.mark.parametrize("scale", [1 + 2.9e-5, 1 - 2.9e-5])
def test_a_row_norm_just_inside_the_tolerance_passes(tmp_path, scale):
    vectors = _unit_rows(N)
    vectors[3] *= np.float32(scale)
    staged = _stage(tmp_path / "edge", vectors=vectors)
    corpus = tool.load_corpus(staged.directory, staged.expected)
    assert corpus.vectors.shape == (N, D)


LABEL_CASES = [
    pytest.param(lambda: _replace(6, label=_labels()[2]["label"]), r"label 6\b.*duplicate", id="duplicate"),
    pytest.param(lambda: _replace(6, label=""), r"label 6\b", id="empty"),
    pytest.param(lambda: _replace(6, label=None), r"label 6\b", id="null"),
    pytest.param(lambda: _replace(6, label="two words"), r"label 6\b", id="space"),
    pytest.param(lambda: _replace(6, label="x" * 65), r"label 6\b", id="too_long"),
    pytest.param(lambda: _replace(6, label="NOTE\n"), r"label 6\b", id="trailing_newline"),
    pytest.param(lambda: _replace(6, part=None), r"label 6\b", id="null_part"),
    pytest.param(lambda: _replace(6, part=""), r"label 6\b", id="empty_part"),
    pytest.param(lambda: _replace(6, extra=1), r"label 6\b", id="extra_key"),
    pytest.param(lambda: [{"label": "P0_N00"}, *_labels()[1:]], r"label 0\b", id="missing_part_key"),
    pytest.param(lambda: [*_labels()[:6], "P1_N01", *_labels()[7:]], r"label 6\b", id="not_an_object"),
    pytest.param(lambda: _labels()[:-1], "label count", id="fewer_labels_than_rows"),
    pytest.param(
        lambda: [*_labels(), {"label": "EXTRA", "part": "P2"}], "label count", id="more_labels_than_rows"
    ),
    pytest.param(lambda: _replace(4, part="P1"), "part counts", id="wrong_part_counts"),
    pytest.param(lambda: {"labels": _labels()}, "not a list", id="not_a_list"),
]


@pytest.mark.parametrize(("labels", "pattern"), LABEL_CASES)
def test_a_bad_label_list_is_refused(tmp_path, capsys, labels, pattern):
    err = _refused(_stage(tmp_path / "bad", labels=labels()), tmp_path, capsys)
    assert re.search(pattern, err)


def test_verify_refuses_a_bad_artefact_before_opening_the_database(tmp_path, capsys):
    vectors = _unit_rows(N)
    vectors[4, 7] = np.nan
    staged = _stage(tmp_path / "bad", vectors=vectors)
    code, _out, err = _verify(staged, tmp_path / "absent.db", capsys)
    assert code == 1
    assert re.search(r"row 4\b", err)


# Manifests: read once, checked, and refused before any request


def _swap(keys, i, j):
    keys = list(keys)
    keys[i], keys[j] = keys[j], keys[i]
    return keys


@pytest.mark.parametrize("part", range(len(PARTS)))
@pytest.mark.parametrize("where", ["first", "middle", "last"])
def test_one_flipped_byte_in_a_manifest_is_refused_by_the_digest(staged, tmp_path, capsys, part, where):
    name = _manifest_names()[part]
    path = staged.manifests / name
    data = bytearray(path.read_bytes())
    data[{"first": 0, "middle": len(data) // 2, "last": -1}[where]] ^= 0x01
    path.write_bytes(bytes(data))
    err = _refused(staged, tmp_path, capsys)
    assert name in err
    assert "sha256" in err


def test_a_missing_manifest_is_refused_naming_the_file(staged, tmp_path, capsys):
    name = _manifest_names()[2]
    (staged.manifests / name).unlink()
    assert name in _refused(staged, tmp_path, capsys)


def test_an_unreadable_manifest_is_refused_naming_the_file(staged, tmp_path, capsys):
    name = _manifest_names()[1]
    path = staged.manifests / name
    path.unlink()
    path.mkdir()
    assert name in _refused(staged, tmp_path, capsys)


def _with_value(pairs, value):
    return _object_bytes([*pairs[:2], (pairs[2][0], value), *pairs[3:]])


MANIFEST_CASES = [
    pytest.param(lambda p: _object_bytes([*p, (p[1][0], "again")]), r"duplicate.*P1_N01", id="duplicate_key"),
    pytest.param(lambda p: json.dumps([list(pair) for pair in p]).encode(), "not a JSON object", id="list"),
    pytest.param(lambda p: b'"a sentence"', "not a JSON object", id="string"),
    pytest.param(lambda p: b"null", "not a JSON object", id="null_document"),
    pytest.param(lambda p: _with_value(p, 5), r"P1_N02.*not a string", id="number"),
    pytest.param(lambda p: _with_value(p, None), r"P1_N02.*not a string", id="null"),
    pytest.param(lambda p: _with_value(p, ["a"]), r"P1_N02.*not a string", id="list_value"),
    pytest.param(lambda p: _with_value(p, {"a": "b"}), r"P1_N02.*not a string", id="object_value"),
    pytest.param(lambda p: _with_value(p, ""), r"P1_N02.*empty", id="empty"),
    pytest.param(lambda p: _with_value(p, "a\x00b"), r"P1_N02.*NUL", id="nul"),
    pytest.param(lambda p: b'{"P1_N00": "\xff"}', "UTF-8", id="not_utf8"),
    pytest.param(lambda p: b'{"P1_N00": "a"', "UTF-8", id="truncated"),
]


@pytest.mark.parametrize(("build", "pattern"), MANIFEST_CASES)
def test_a_bad_manifest_is_refused_naming_the_file(tmp_path, capsys, build, pattern):
    staged = _stage(tmp_path / "bad", manifests=_manifests_with(1, build(_pairs(1))))
    err = _refused(staged, tmp_path, capsys)
    assert _manifest_names()[1] in err
    assert re.search(pattern, err)


ORDER_CASES = [
    pytest.param(lambda k: _swap(k, 2, 3), r"label 2\b", id="swapped_inside_one_part"),
    pytest.param(lambda k: _swap(k, 4, 5), r"label 4\b", id="swapped_across_two_parts"),
    pytest.param(lambda k: k[:6] + k[7:], r"label 6\b", id="one_missing"),
    pytest.param(lambda k: k[:-1], r"index 11\b", id="last_missing"),
    pytest.param(lambda k: [*k[:3], "EXTRA", *k[3:]], r"label 3\b", id="one_extra_inside"),
    pytest.param(lambda k: [*k, "EXTRA"], r"index 12\b", id="one_extra_at_the_end"),
]


@pytest.mark.parametrize(("arrange", "pattern"), ORDER_CASES)
def test_manifest_labels_that_differ_from_the_artefact_are_refused_naming_the_index(
    tmp_path, capsys, arrange, pattern
):
    staged = _stage(tmp_path / "bad", keys=arrange(_keys()))
    assert re.search(pattern, _refused(staged, tmp_path, capsys))


def test_a_label_repeated_across_two_manifests_is_refused_naming_the_later_file(tmp_path, capsys):
    keys = _keys()
    keys[5] = keys[0]
    err = _refused(_stage(tmp_path / "bad", keys=keys), tmp_path, capsys)
    assert _manifest_names()[1] in err
    assert keys[0] in err


def _last_manifest_flipped(directory):
    staged = _stage(directory)
    path = staged.manifests / _manifest_names()[-1]
    data = bytearray(path.read_bytes())
    data[-1] ^= 0x01
    path.write_bytes(bytes(data))
    return staged


LIMIT_CASES = [
    pytest.param(_last_manifest_flipped, "sha256", id="digest"),
    pytest.param(
        lambda d: _stage(d, manifests=_manifests_with(2, _object_bytes([(_pairs(2)[0][0], ""), *_pairs(2)[1:]]))),
        "empty",
        id="empty_value",
    ),
    pytest.param(lambda d: _stage(d, keys=_swap(_keys(), 9, 10)), r"label 9\b", id="order"),
]


@pytest.mark.parametrize("command", ["load", "verify"])
@pytest.mark.parametrize(("stage", "pattern"), LIMIT_CASES)
def test_limit_does_not_narrow_the_manifest_checks(tmp_path, capsys, command, stage, pattern):
    staged = stage(tmp_path / "bad")
    if command == "load":
        engine = Engine()
        code, _out, err, _report = _load(staged, engine, tmp_path, capsys, "--limit", "5")
        assert engine.calls == []
    else:
        code, _out, err = _verify(staged, tmp_path / "absent.db", capsys, "--limit", "5")
    assert code == 1
    assert re.search(pattern, err)


def test_verify_refuses_a_bad_manifest_before_opening_the_database(tmp_path, capsys):
    staged = _stage(tmp_path / "bad", keys=_swap(_keys(), 2, 3))
    code, _out, err = _verify(staged, tmp_path / "absent.db", capsys)
    assert code == 1
    assert re.search(r"label 2\b", err)
    assert not (tmp_path / "absent.db").exists()


# T2: the rows go in text order, one POST each


def test_load_sends_the_rows_in_text_order_one_post_each(staged, tmp_path, capsys):
    engine = Engine()
    code, out, err, _report = _load(staged, engine, tmp_path, capsys)
    assert code == 0
    assert err == ""
    assert len(out.strip().splitlines()) == 1
    assert engine.calls[0][:2] == ("GET", "/nodos")
    assert [call[0] for call in engine.calls].count("GET") == 1
    assert len(engine.posts) == N
    digest = staged.expected.embeddings_sha256[:12]
    for i, (method, path, headers, body) in enumerate(engine.posts):
        assert (method, path) == ("POST", "/ingesta/vector")
        assert json.loads(body) == {
            "vector": staged.vectors[i].astype(np.float64).tolist(),
            "label": staged.labels[i]["label"],
            "text": staged.sentences[i],
        }
        assert headers == {
            "X-Traianus-Token": TOKEN,
            "X-Idempotency-Key": f"spinoza-{i:04d}-{digest}",
            "Content-Type": "application/json",
        }


# T3: resume


def test_resume_sends_no_post_for_a_label_the_engine_already_lists(staged, tmp_path, capsys):
    labels = [row["label"] for row in staged.labels]
    present = (0, 1, 5)
    engine = Engine(existing=[f"VEC_{labels[i]}" for i in present] + ["VEC_UNRELATED"])
    code, _out, _err, report = _load(staged, engine, tmp_path, capsys)
    assert code == 0
    sent = [json.loads(call[3])["label"] for call in engine.posts]
    assert sent == [label for i, label in enumerate(labels) if i not in present]
    digest = staged.expected.embeddings_sha256[:12]
    assert engine.posts[0][2]["X-Idempotency-Key"] == f"spinoza-0002-{digest}"
    assert json.loads(report.read_text(encoding="utf-8"))["skipped"] == len(present)


def test_resume_sends_the_sentence_of_the_row_it_posts(staged, tmp_path, capsys):
    labels = [row["label"] for row in staged.labels]
    present = (0, 1, 5)
    engine = Engine(existing=[f"VEC_{labels[i]}" for i in present])
    assert _load(staged, engine, tmp_path, capsys)[0] == 0
    sent = [(json.loads(call[3])["label"], json.loads(call[3])["text"]) for call in engine.posts]
    assert sent == [(label, staged.sentences[i]) for i, label in enumerate(labels) if i not in present]


def test_a_second_full_run_sends_no_post(staged, tmp_path, capsys):
    engine = Engine()
    assert _load(staged, engine, tmp_path, capsys)[0] == 0
    code, _out, _err, report = _load(staged, engine, tmp_path, capsys)
    assert code == 0
    assert len(engine.posts) == N
    assert json.loads(report.read_text(encoding="utf-8"))["skipped"] == N


# T4: never a retry

FAULTS = [
    pytest.param((500, b"{}"), id="status_500"),
    pytest.param((422, b'{"detail": "no"}'), id="status_422"),
    pytest.param((200, b'{"node_id": "VEC_P1_N00", "seq": 1}'), id="status_200"),
    pytest.param((201, b'{"node_id": "VEC_OTHER", "seq": 1}'), id="node_id_mismatch"),
    pytest.param((201, b'{"node_id": "VEC_P1_N00", "seq": 2}'), id="seq_2"),
    pytest.param((201, b'{"node_id": "VEC_P1_N00"}'), id="seq_missing"),
    pytest.param((201, b"<html>"), id="not_json"),
    pytest.param((201, b"[1]"), id="not_an_object"),
    pytest.param(ConnectionError("down"), id="connection_error"),
    pytest.param(TimeoutError("slow"), id="timeout"),
]


@pytest.mark.parametrize("fault", FAULTS)
def test_a_failed_row_stops_the_run_after_one_attempt(staged, tmp_path, capsys, fault):
    engine = Engine(faults={5: fault})
    code, _out, err, report = _load(staged, engine, tmp_path, capsys)
    assert code == 1
    assert len(engine.posts) == 6
    assert json.loads(engine.posts[5][3])["label"] == "P1_N00"
    assert re.search(r"row 5\b", err)
    assert "P1_N00" in err
    result = json.loads(report.read_text(encoding="utf-8"))
    assert result["loaded_labels"] == [row["label"] for row in staged.labels[:5]]
    assert (result["loaded"], result["failed"]) == (5, 1)
    assert result["first_failure"]["index"] == 5
    assert result["first_failure"]["label"] == "P1_N00"


def test_a_run_after_a_failure_resumes_at_the_row_that_failed(staged, tmp_path, capsys):
    engine = Engine(faults={5: (503, b"{}")})
    assert _load(staged, engine, tmp_path, capsys)[0] == 1
    engine.faults.clear()
    assert _load(staged, engine, tmp_path, capsys)[0] == 0
    sent = [json.loads(call[3])["label"] for call in engine.posts]
    labels = [row["label"] for row in staged.labels]
    assert sent == labels[:6] + labels[5:]


@pytest.mark.parametrize(
    "reply",
    [
        pytest.param((503, b"{}"), id="status_503"),
        pytest.param((200, b"not json"), id="not_json"),
        pytest.param((200, b'{"nodes": 3}'), id="nodes_not_a_list"),
        pytest.param((200, b'{"nodes": [{"name": "x"}]}'), id="node_without_id"),
        pytest.param(ConnectionError("down"), id="connection_error"),
    ],
)
def test_an_unusable_node_listing_stops_the_run_before_any_post(staged, tmp_path, capsys, reply):
    engine = Engine(faults={"GET": reply})
    code, _out, err, report = _load(staged, engine, tmp_path, capsys)
    assert code == 1
    assert engine.posts == []
    assert "nodos" in err
    result = json.loads(report.read_text(encoding="utf-8"))
    assert (result["loaded"], result["failed"]) == (0, 1)
    assert result["first_failure"]["index"] is None


# T5: loopback only, and the token stays out of every output

HOSTILE_URLS = [
    "http://192.168.1.5:8000",
    "http://example.org:8000",
    "http://127.0.0.1.example.org:8000",
    "http://localhost.example.org",
    "http://127.0.0.1@example.org:8000",
    "http://example.org@127.0.0.1:8000",
    "http://[::1]:8000",
    "http://0.0.0.0:8000",
    "https://127.0.0.1:8000",
    "http://127.0.0.1:99999",
    "http://127.0.0.1:8000/api",
    "127.0.0.1:8000",
    "",
]


@pytest.mark.parametrize("url", HOSTILE_URLS)
def test_a_url_that_is_not_loopback_is_refused_before_any_request(staged, tmp_path, capsys, url):
    engine = Engine()
    code, _out, err, report = _load(staged, engine, tmp_path, capsys, url=url)
    assert code == 1
    assert "url" in err
    assert engine.calls == []
    assert not report.exists()


@pytest.mark.parametrize(
    "url", ["http://127.0.0.1:8000", "http://127.0.0.1", "http://localhost:8000", "http://localhost/"]
)
def test_a_loopback_url_is_accepted(staged, tmp_path, capsys, url):
    engine = Engine()
    assert _load(staged, engine, tmp_path, capsys, url=url)[0] == 0
    assert len(engine.posts) == N


@pytest.mark.parametrize("value", [None, ""])
def test_a_missing_token_is_refused_before_any_request(staged, tmp_path, capsys, monkeypatch, value):
    if value is None:
        monkeypatch.delenv("TRAIANUS_TOKEN")
    else:
        monkeypatch.setenv("TRAIANUS_TOKEN", value)
    engine = Engine()
    code, _out, err, _report = _load(staged, engine, tmp_path, capsys)
    assert code == 1
    assert "TRAIANUS_TOKEN" in err
    assert engine.calls == []


@pytest.mark.parametrize("faults", [{}, {3: (500, f"boom {TOKEN}".encode())}], ids=["success", "failure"])
def test_the_token_appears_in_no_output_and_not_in_the_report(staged, tmp_path, capsys, faults):
    engine = Engine(faults=faults)
    code, out, err, report = _load(staged, engine, tmp_path, capsys)
    assert code == (1 if faults else 0)
    assert engine.posts[0][2]["X-Traianus-Token"] == TOKEN
    if faults:
        assert "boom" in err
    for text in (out, err, report.read_text(encoding="utf-8")):
        assert TOKEN not in text


# X2: --limit, and the usage errors


def test_limit_restricts_the_rows_in_text_order(staged, tmp_path, capsys):
    engine = Engine()
    code, _out, _err, report = _load(staged, engine, tmp_path, capsys, "--limit", "5")
    assert code == 0
    sent = [json.loads(call[3])["label"] for call in engine.posts]
    assert sent == [row["label"] for row in staged.labels[:5]]
    assert json.loads(report.read_text(encoding="utf-8"))["limit"] == 5


def test_limit_does_not_narrow_the_integrity_checks(tmp_path, capsys):
    vectors = _unit_rows(N)
    vectors[9, 0] = np.nan
    engine = Engine()
    staged = _stage(tmp_path / "bad", vectors=vectors)
    code, _out, err, _report = _load(staged, engine, tmp_path, capsys, "--limit", "5")
    assert (code, engine.calls) == (1, [])
    assert re.search(r"row 9\b", err)


def test_a_limit_above_the_row_count_is_refused(staged, tmp_path, capsys):
    engine = Engine()
    code, _out, err, _report = _load(staged, engine, tmp_path, capsys, "--limit", str(N + 1))
    assert (code, engine.calls) == (1, [])
    assert "limit" in err


@pytest.mark.parametrize("limit", ["0", "-1", "x"])
def test_a_limit_that_is_not_a_positive_integer_is_a_usage_error(staged, tmp_path, capsys, limit):
    with pytest.raises(SystemExit) as raised:
        _load(staged, Engine(), tmp_path, capsys, "--limit", limit)
    assert raised.value.code == 2


@pytest.mark.parametrize("argv", [[], ["frobnicate"], ["load"], ["verify"]])
def test_a_missing_command_or_option_is_a_usage_error(argv):
    with pytest.raises(SystemExit) as raised:
        tool.main(argv)
    assert raised.value.code == 2


# T6: verify


def _vhat(row32):
    row = row32.astype("<f8")
    return row / np.sqrt(row @ row)


def _stored(staged, replace=None, texts=None):
    replace = replace or {}
    texts = texts or {}
    return [
        (
            f"VEC_{entry['label']}",
            1,
            replace.get(i, _vhat(staged.vectors[i]).tobytes()),
            texts.get(i, staged.sentences[i]),
        )
        for i, entry in enumerate(staged.labels)
    ]


def _database(path, rows):
    conn = sqlite3.connect(path)
    try:
        conn.execute(
            "CREATE TABLE manifold_nodes (id TEXT, seq INTEGER, vector_blob BLOB, text TEXT, PRIMARY KEY (id, seq))"
        )
        conn.executemany("INSERT INTO manifold_nodes VALUES (?, ?, ?, ?)", rows)
        conn.commit()
    finally:
        conn.close()
    return path


def _flip(blob, component, bit):
    words = np.frombuffer(blob, dtype="<u8").copy()
    words[component] ^= np.uint64(1) << np.uint64(bit)
    return words.tobytes()


def test_verify_passes_when_every_blob_is_v_hat(staged, tmp_path, capsys):
    db = _database(tmp_path / "ok.db", _stored(staged))
    code, out, err = _verify(staged, db, capsys)
    assert (code, err) == (0, "")
    assert len(out.strip().splitlines()) == 1


@pytest.mark.parametrize("bit", [63, 52, 0], ids=["sign", "exponent_lsb", "mantissa_bit_0"])
def test_verify_fails_on_one_flipped_bit_and_names_the_label(staged, tmp_path, capsys, bit):
    blob = _vhat(staged.vectors[4]).tobytes()
    db = _database(tmp_path / "flip.db", _stored(staged, {4: _flip(blob, 9, bit)}))
    code, _out, err = _verify(staged, db, capsys)
    assert code == 1
    assert "1 mismatched" in err
    assert staged.labels[4]["label"] in err


def test_verify_fails_on_a_missing_node_and_names_the_label(staged, tmp_path, capsys):
    absent = f"VEC_{staged.labels[7]['label']}"
    rows = [row for row in _stored(staged) if row[0] != absent]
    code, _out, err = _verify(staged, _database(tmp_path / "gap.db", rows), capsys)
    assert code == 1
    assert "0 mismatched, 1 missing" in err
    assert staged.labels[7]["label"] in err


@pytest.mark.parametrize("blob", [b"", None, bytes(8 * D)], ids=["empty", "null", "zeros"])
def test_verify_fails_on_a_blob_that_is_not_v_hat(staged, tmp_path, capsys, blob):
    db = _database(tmp_path / "odd.db", _stored(staged, {4: blob}))
    code, _out, err = _verify(staged, db, capsys)
    assert code == 1
    assert "1 mismatched" in err


def test_verify_reads_the_highest_seq_of_each_node(staged, tmp_path, capsys):
    ids = [f"VEC_{entry['label']}" for entry in staged.labels]
    good = [_vhat(v).tobytes() for v in staged.vectors]
    text = staged.sentences
    rows = [(ids[i], 1, good[i], text[i]) for i in range(N) if i not in (2, 3)]
    rows += [(ids[2], 2, good[2], text[2]), (ids[2], 1, _flip(good[2], 0, 52), text[2])]
    rows += [(ids[3], 1, good[3], text[3]), (ids[3], 2, _flip(good[3], 0, 52), text[3])]
    code, _out, err = _verify(staged, _database(tmp_path / "rev.db", rows), capsys)
    assert code == 1
    assert "1 mismatched" in err
    assert staged.labels[3]["label"] in err
    assert staged.labels[2]["label"] not in err


def test_verify_limit_checks_only_the_first_rows(staged, tmp_path, capsys):
    blob = _vhat(staged.vectors[10]).tobytes()
    absent = f"VEC_{staged.labels[11]['label']}"
    rows = [row for row in _stored(staged, {10: _flip(blob, 3, 0)}) if row[0] != absent]
    db = _database(tmp_path / "limit.db", rows)
    assert _verify(staged, db, capsys, "--limit", "10")[0] == 0
    code, _out, err = _verify(staged, db, capsys, "--limit", "11")
    assert code == 1
    assert "1 mismatched, 0 missing" in err
    code, _out, err = _verify(staged, db, capsys)
    assert code == 1
    assert "1 mismatched, 1 missing" in err
    assert staged.labels[10]["label"] in err
    assert staged.labels[11]["label"] in err


def test_verify_compares_v_hat_not_the_widened_row(staged, tmp_path, capsys):
    widened = {i: staged.vectors[i].astype("<f8").tobytes() for i in range(N)}
    db = _database(tmp_path / "raw.db", _stored(staged, widened))
    code, _out, err = _verify(staged, db, capsys)
    assert code == 1
    assert re.search(r"[1-9]\d* mismatched", err)


def test_verify_opens_the_database_read_only(staged, tmp_path, capsys, monkeypatch):
    db = _database(tmp_path / "ro.db", _stored(staged))
    opened = []
    real_connect = sqlite3.connect

    def spy(*args, **kwargs):
        opened.append((args, kwargs))
        return real_connect(*args, **kwargs)

    monkeypatch.setattr(sqlite3, "connect", spy)
    assert _verify(staged, db, capsys)[0] == 0
    assert opened
    for args, kwargs in opened:
        assert args[0].endswith("?mode=ro")
        assert kwargs.get("uri") is True


def test_a_write_through_the_read_only_uri_fails(staged, tmp_path):
    db = _database(tmp_path / "ro.db", _stored(staged))
    conn = sqlite3.connect(tool.readonly_uri(db), uri=True)
    try:
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            conn.execute("INSERT INTO manifold_nodes VALUES ('x', 1, x'00', 't')")
    finally:
        conn.close()


def test_verify_refuses_a_database_that_cannot_be_opened(staged, tmp_path, capsys):
    code, _out, err = _verify(staged, tmp_path / "absent.db", capsys)
    assert code == 1
    assert "absent.db" in err
    assert not (tmp_path / "absent.db").exists()


TEXT_CASES = [
    pytest.param(lambda s, label: label, id="the_label"),
    pytest.param(lambda s, label: None, id="null"),
    pytest.param(lambda s, label: "", id="empty"),
    pytest.param(lambda s, label: s.replace("sustancia", "sustancie"), id="one_character_changed"),
    pytest.param(lambda s, label: s.strip(), id="stripped"),
    pytest.param(lambda s, label: unicodedata.normalize("NFC", s), id="normalised"),
    pytest.param(lambda s, label: s[:-1], id="truncated"),
]


@pytest.mark.parametrize("wrong", TEXT_CASES)
def test_verify_fails_on_a_text_that_is_not_the_sentence(staged, tmp_path, capsys, wrong):
    label = staged.labels[4]["label"]
    texts = {4: wrong(staged.sentences[4], label)}
    code, out, err = _verify(staged, _database(tmp_path / "text.db", _stored(staged, texts=texts)), capsys)
    assert code == 1
    assert len(out.strip().splitlines()) == 1
    assert "0 mismatched, 0 missing" in err
    assert "1 text mismatched" in err
    assert label in err


def test_a_node_with_bad_bits_and_a_bad_text_counts_once(staged, tmp_path, capsys):
    blob = _vhat(staged.vectors[4]).tobytes()
    rows = _stored(staged, {4: _flip(blob, 9, 0)}, {4: staged.labels[4]["label"]})
    code, out, err = _verify(staged, _database(tmp_path / "both.db", rows), capsys)
    assert code == 1
    assert "11 of 12" in out
    assert "1 mismatched, 0 missing" in err
    assert "1 text mismatched" in err


def test_verify_reads_the_text_of_the_highest_seq_of_each_node(staged, tmp_path, capsys):
    ids = [f"VEC_{entry['label']}" for entry in staged.labels]
    good = [_vhat(v).tobytes() for v in staged.vectors]
    text = staged.sentences
    rows = [(ids[i], 1, good[i], text[i]) for i in range(N) if i not in (2, 3)]
    rows += [(ids[2], 2, good[2], text[2]), (ids[2], 1, good[2], "old")]
    rows += [(ids[3], 1, good[3], text[3]), (ids[3], 2, good[3], "new")]
    code, _out, err = _verify(staged, _database(tmp_path / "rev.db", rows), capsys)
    assert code == 1
    assert "1 text mismatched" in err
    assert staged.labels[3]["label"] in err
    assert staged.labels[2]["label"] not in err


def test_verify_limit_checks_only_the_text_of_the_first_rows(staged, tmp_path, capsys):
    db = _database(tmp_path / "limit.db", _stored(staged, texts={10: ""}))
    assert _verify(staged, db, capsys, "--limit", "10")[0] == 0
    code, _out, err = _verify(staged, db, capsys, "--limit", "11")
    assert code == 1
    assert "1 text mismatched" in err
    assert staged.labels[10]["label"] in err


def test_a_missing_node_is_not_also_a_text_mismatch(staged, tmp_path, capsys):
    absent = f"VEC_{staged.labels[7]['label']}"
    rows = [row for row in _stored(staged) if row[0] != absent]
    code, _out, err = _verify(staged, _database(tmp_path / "gap.db", rows), capsys)
    assert code == 1
    assert "text mismatched" not in err


# T7: end to end against the real application


def _through(client, calls):
    def transport(method, path, headers, body):
        calls.append(method)
        response = client.request(method, path, content=body, headers=dict(headers))
        return response.status_code, response.content

    return transport


def test_the_engine_stores_the_bits_the_loader_and_the_contract_expect(client, isolate_db, tmp_path, capsys):
    n = 40
    labels = [{"label": f"E2E_{i:02d}", "part": "PA" if i < 25 else "PB"} for i in range(n)]
    keys = [entry["label"] for entry in labels]
    staged = _stage(
        tmp_path / "e2e", vectors=_unit_rows(n), labels=labels, shape=(n, D), counts=(25, 15), keys=keys
    )
    report = tmp_path / "report.json"
    argv = ["load", "--url", URL, "--artefacts", str(staged.directory), "--manifests", str(staged.manifests)]
    argv += ["--report", str(report)]
    calls = []
    assert tool.main(argv, transport=_through(client, calls), expected=staged.expected) == 0
    assert calls.count("POST") == n
    nodes = {node["id"]: node["text"] for node in client.get("/nodos").json()["nodes"]}
    assert [nodes[f"VEC_{key}"] for key in keys] == staged.sentences
    capsys.readouterr()
    code, _out, err = _verify(staged, isolate_db, capsys)
    assert (code, err) == (0, "")
    calls.clear()
    assert tool.main(argv, transport=_through(client, calls), expected=staged.expected) == 0
    assert calls == ["GET"]


# T8: determinism, and where the report lands


def _reject(constant):
    raise AssertionError(f"non-finite constant {constant} in the report")


def test_two_runs_send_the_same_requests_and_write_the_same_report(staged, tmp_path, capsys):
    first, second = Engine(), Engine()
    code_a, _out, _err, report_a = _load(staged, first, tmp_path / "one", capsys)
    code_b, _out, _err, report_b = _load(staged, second, tmp_path / "two", capsys)
    assert code_a == code_b == 0
    assert first.calls == second.calls
    text = report_a.read_text(encoding="utf-8")
    assert text == report_b.read_text(encoding="utf-8")
    parsed = json.loads(text, parse_constant=_reject)
    assert text == json.dumps(parsed, sort_keys=True, indent=2, allow_nan=False) + "\n"
    assert parsed["digests"] == {
        "embeddings.npy": staged.expected.embeddings_sha256,
        "labels.json": staged.expected.labels_sha256,
        **dict(staged.expected.manifests),
    }
    assert set(parsed["environment"]) == {"numpy", "numpy_config", "platform"}
    assert (parsed["loaded"], parsed["skipped"], parsed["failed"]) == (N, 0, 0)
    assert parsed["first_failure"] is None


def test_the_default_report_is_under_the_ignored_data_directory():
    assert tool.DEFAULT_REPORT == REPO_ROOT / ".data" / "spinoza_load_report.json"
    assert ".data/" in (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()


@pytest.mark.parametrize(
    "relative", ["report.json", "tests/report.json", "data/report.json", ".data/../report.json"]
)
def test_a_report_path_inside_the_repository_tree_is_refused(staged, tmp_path, capsys, monkeypatch, relative):
    root = tmp_path / "repo"
    monkeypatch.setattr(tool, "REPO_ROOT", root)
    monkeypatch.setattr(tool, "DATA_DIR", root / ".data")
    target = root / relative
    engine = Engine()
    argv = ["load", "--url", URL, "--artefacts", str(staged.directory), "--report", str(target)]
    code = tool.main(argv, transport=engine, expected=staged.expected)
    err = capsys.readouterr().err
    assert (code, engine.calls) == (1, [])
    assert "report" in err
    assert not target.resolve().exists()


def test_a_report_path_under_data_or_outside_the_tree_is_accepted(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    monkeypatch.setattr(tool, "REPO_ROOT", root)
    monkeypatch.setattr(tool, "DATA_DIR", root / ".data")
    for path in (root / ".data" / "spinoza_load_report.json", tmp_path / "elsewhere" / "r.json"):
        assert tool.check_report_path(path) == path.resolve()


# T9: the import surface

THREAD_VARS = {"OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"}
ALLOWED_IMPORTS = {
    "__future__", "argparse", "collections", "contextlib", "dataclasses", "hashlib", "http", "io",
    "json", "os", "pathlib", "platform", "re", "sqlite3", "sys", "typing", "numpy",
}


def _imports(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name.split(".")[0]
        elif isinstance(node, ast.ImportFrom):
            yield node.lineno, (node.module or "").split(".")[0]


def _is_thread_loop(node):
    if not (isinstance(node, ast.For) and isinstance(node.iter, ast.Tuple)):
        return False
    names = {c.value for c in node.iter.elts if isinstance(c, ast.Constant)}
    sets_one = any(
        isinstance(s, ast.Assign) and isinstance(s.value, ast.Constant) and s.value.value == "1"
        for s in node.body
    )
    return names == THREAD_VARS and sets_one


def test_the_thread_variables_are_set_to_one_before_numpy_is_imported():
    tree = ast.parse(TOOL.read_text(encoding="utf-8"))
    loops = [node for node in tree.body if _is_thread_loop(node)]
    numpy_lines = [line for line, root in _imports(tree) if root == "numpy"]
    assert len(loops) == 1
    assert numpy_lines
    assert loops[0].lineno < min(numpy_lines)


def test_the_tool_imports_only_the_standard_library_and_numpy():
    tree = ast.parse(TOOL.read_text(encoding="utf-8"))
    assert {root for _line, root in _imports(tree)} <= ALLOWED_IMPORTS
    assert "__import__" not in {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}


# T10: the registry rule

LOADER = "tools/experiments/tooling/load_spinoza_corpus.py"
THIS_TEST = "tests/unit/test_load_spinoza_corpus.py"


def _rule(name, paths, *requires):
    needs = [{"path": CONTRACT, "kind": kind, "value": value} for kind, value in requires]
    return {"name": name, "paths": paths, "requires": needs}


def _registry_rules():
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    return registry, {rule["name"]: rule for rule in registry["rules"]}


def test_the_registry_has_the_corpus_loader_rule_and_the_others_are_unchanged():
    registry, rules = _registry_rules()
    assert registry["window_seconds"] == 14400
    assert set(rules) == {"engine-vector-path", "k6", "r4", "corpus-loader", "z"}
    assert rules["corpus-loader"] == _rule("corpus-loader", [LOADER, THIS_TEST], ("heading", SECTION_0))
    assert rules["z"] == _rule(
        "z",
        ["tools/experiments/zoom_*.py", "tests/unit/test_zoom_*.py"],
        ("heading", SECTION_0),
        ("heading", "4. Z — three-point zoom against a two-point benchmark"),
    )
    assert rules["engine-vector-path"] == _rule(
        "engine-vector-path",
        ["traianus/app.py", "traianus/storage/**", "traianus/representation/**", "traianus/geometry/**"],
        ("paragraph", "Engine path"),
    )
    assert rules["k6"] == _rule(
        "k6",
        ["tools/experiments/k6_*.py", "tests/unit/test_k6_*.py"],
        ("heading", SECTION_0),
        ("heading", "1. K6 — colour channel predictability"),
    )
    assert rules["r4"] == _rule(
        "r4",
        ["tools/experiments/r4_*.py", "tests/unit/test_r4_*.py"],
        ("heading", SECTION_0),
        ("heading", "2. R4 — neighbourhood kept in a 5D perspective"),
    )


def test_the_corpus_loader_rule_names_files_that_exist_and_resolves_in_the_real_contract():
    _registry, rules = _registry_rules()
    rule = rules["corpus-loader"]
    assert all((REPO_ROOT / path).is_file() for path in rule["paths"])
    for required in rule["requires"]:
        lines, _digest = context_pack.load(REPO_ROOT, required["path"])
        context_pack.SELECTORS[required["kind"]](lines, required["value"])


# T11: the constants, and the real artefact (skipped when .data/spinoza_frozen is absent, as in CI)


def test_the_constants_are_those_of_the_contract():
    assert tool.EXPECTED == tool.Expected(
        "eafb0e97172830f2404e96fa08d74bf6cccc0b6cbe84d47b790a476603e7d8d1",
        "1d60699353d810f089730c6203ee28f9c416e3004b60781bc965cec284097f4f",
        (2221, D),
        (409, 458, 627, 507, 220),
        (
            ("part1_god_manifest.json", "848c2ad98645c79820354b861532cb22e8acbf030d4d53d961b8eebc9f2696fe"),
            ("part2_mind_manifest.json", "0aa584037d237318f8a0f343403e1a0fb9c7ce90bb9cd9096607404c7523ccdf"),
            ("part3_affects_manifest.json", "7ef2f0aa66b383c80872bf35ab2e17b5d6bcee42b08113688b5db8d1b4ec4e06"),
            ("part4_bondage_manifest.json", "8aa3e2d7159f1d105ad7a0f2ba95ebd23f466bdde02e10e5ac34cc0c23daf501"),
            ("part5_power_manifest.json", "29b937dfb7fdea6e6efbd1fafc5fb7d7d604ace2d833dea75047e24babafdd70"),
        ),
    )


@pytest.mark.skipif(
    not FROZEN.is_dir(), reason=".data/spinoza_frozen is absent (git-ignored; CI has no artefacts)"
)
def test_the_real_artefact_matches_the_constants_and_passes_the_integrity_checks():
    corpus = tool.load_corpus(FROZEN, tool.EXPECTED)
    assert corpus.vectors.shape == (2221, D)
    assert len(corpus.labels) == 2221


def test_the_committed_manifests_match_the_constants_and_hold_2221_clean_sentences():
    digests = tuple((name, _sha((MANIFESTS / name).read_bytes())) for name, _digest in tool.EXPECTED.manifests)
    assert digests == tool.EXPECTED.manifests
    sentences = tool.load_manifests(MANIFESTS, tool.EXPECTED.manifests)
    assert len(sentences) == 2221
    assert all(isinstance(text, str) and text and "\x00" not in text for text in sentences.values())
    counts = tuple(len(json.loads((MANIFESTS / name).read_bytes())) for name, _digest in tool.EXPECTED.manifests)
    assert counts == (409, 458, 627, 507, 220)


@pytest.mark.skipif(
    not FROZEN.is_dir(), reason=".data/spinoza_frozen is absent (git-ignored; CI has no artefacts)"
)
def test_the_committed_manifests_agree_with_the_frozen_labels():
    corpus = tool.load_corpus(FROZEN, tool.EXPECTED)
    sentences = tool.load_manifests(MANIFESTS, tool.EXPECTED.manifests)
    assert tool.align_sentences(sentences, corpus.labels) == list(sentences.values())


@pytest.mark.parametrize("argv", [["load", "--url", URL], ["verify", "--db", "x.db"]])
def test_the_manifests_directory_defaults_to_the_tracked_spinoza_data(argv):
    assert tool._parser().parse_args(argv).manifests == tool.DEFAULT_MANIFESTS == MANIFESTS


# X1: the default transport, through an injected connection factory


def _connection(error=None):
    log = []

    class Connection:
        def __init__(self, host, port, timeout):
            log.append(("open", host, port, timeout))

        def request(self, method, path, body=None, headers=None):
            log.append(("request", method, path, body, headers))
            if error is not None:
                raise error

        def getresponse(self):
            return SimpleNamespace(status=201, read=lambda: b"{}")

        def close(self):
            log.append(("close",))

    return Connection, log


def test_the_default_transport_sends_the_request_and_closes_the_connection():
    connection, log = _connection()
    transport = tool.make_transport("127.0.0.1", 8000, connect=connection)
    assert transport("POST", "/ingesta/vector", {"X-Idempotency-Key": "k"}, b"{}") == (201, b"{}")
    assert [entry[0] for entry in log] == ["open", "request", "close"]
    assert log[0][1:3] == ("127.0.0.1", 8000)
    assert log[1][1:] == ("POST", "/ingesta/vector", b"{}", {"X-Idempotency-Key": "k"})


def test_the_default_transport_closes_the_connection_when_the_request_fails():
    connection, log = _connection(error=ConnectionRefusedError("no"))
    transport = tool.make_transport("127.0.0.1", 8000, connect=connection)
    with pytest.raises(ConnectionRefusedError):
        transport("GET", "/nodos", {}, None)
    assert log[-1] == ("close",)


# X5: each artefact is read once; X6: a missing artefact


def test_each_artefact_is_read_once(staged, monkeypatch):
    reads = []
    real_read = Path.read_bytes

    def counting(self):
        reads.append(self.name)
        return real_read(self)

    monkeypatch.setattr(Path, "read_bytes", counting)
    tool.load_corpus(staged.directory, staged.expected)
    assert sorted(reads) == ["embeddings.npy", "labels.json"]


def test_each_manifest_is_read_once(staged, monkeypatch):
    reads = []
    real_read = Path.read_bytes

    def counting(self):
        reads.append(self.name)
        return real_read(self)

    monkeypatch.setattr(Path, "read_bytes", counting)
    tool.load_manifests(staged.manifests, staged.expected.manifests)
    assert reads == _manifest_names()


def test_a_missing_artefact_is_refused_naming_the_file(staged, tmp_path, capsys):
    (staged.directory / "labels.json").unlink()
    assert "labels.json" in _refused(staged, tmp_path, capsys)
