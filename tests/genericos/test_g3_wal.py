"""
G3 — WAL (finding L2, audit TRAIANUS_AUDIT.md:345).

Normative (RFC 2119): every production function that opens the database
(sqlite3.connect) MUST execute PRAGMA journal_mode=WAL before operating
(storage consistency and crash recovery). CODE_FIX applied in Phase 1:
get_relations/forge_relation omitted the pragma (L2).

The guard combines an AST scan over traianus/app.py and traianus/bootstrap.py
with two behavioral companions (fresh-file bootstrap anchor and per-block
endpoint journal mode).

Normative: docs/development/tests/SPEC-global.md
Coverage: G3
"""
import ast
import sqlite3
from pathlib import Path

import numpy as np
import pytest

import traianus.app as main
import traianus.bootstrap as bootstrap
from helpers.endpoint_registry import BLOCKS, endpoints_for

PROD_FILES = ("traianus/app.py", "traianus/bootstrap.py")
ROOT = Path(__file__).resolve().parents[2]


def _db_opening_functions_without_wal():
    """AST scan: every function that calls `sqlite3.connect` MUST also
    execute `PRAGMA journal_mode=WAL` inside its body. Returns the list of
    violating `file:line:name` locations."""
    bad = []
    for rel in PROD_FILES:
        path = ROOT / rel
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            connects = [
                c
                for c in ast.walk(node)
                if isinstance(c, ast.Call)
                and isinstance(c.func, ast.Attribute)
                and c.func.attr == "connect"
                and isinstance(c.func.value, ast.Name)
                and c.func.value.id == "sqlite3"
            ]
            if not connects:
                continue
            pragmas = [
                c
                for c in ast.walk(node)
                if isinstance(c, ast.Call)
                and isinstance(c.func, ast.Attribute)
                and c.func.attr == "execute"
                and c.args
                and isinstance(c.args[0], ast.Constant)
                and isinstance(c.args[0].value, str)
                and c.args[0].value.startswith("PRAGMA journal_mode=WAL")
            ]
            if not pragmas:
                bad.append(f"{rel}:{node.lineno}:{node.name}")
    return bad


def _journal_mode(db_path):
    with sqlite3.connect(db_path) as conn:
        return conn.execute("PRAGMA journal_mode;").fetchone()[0]


def test_g3_all_db_opening_functions_enable_wal():
    """MUST (static): no production function opens the DB without enabling WAL."""
    violations = _db_opening_functions_without_wal()
    assert not violations, f"functions open DB without PRAGMA journal_mode=WAL:\n{violations}"


@pytest.mark.parametrize("block", [b for b in BLOCKS if endpoints_for(b)])
def test_g3_handlers_open_db_in_wal(block, client, auth_headers, isolate_db):
    """MUST (behavioral): after each block operates on DB, journal_mode == wal."""
    if block == "ingestion":
        client.post("/ingesta", json={"type": "text/plain", "text": "x"}, headers=auth_headers)
    elif block == "consolidation":
        client.post(
            "/nodos/NODE_X/consolidar",
            json={"text": "x", "ethical_key": True},
            headers=auth_headers,
        )
    elif block == "relations":
        client.get("/relations", headers=auth_headers)
        client.post(
            "/relations",
            json={"source": "NODE_A", "target": "NODE_B", "state": "consolidated"},
            headers=auth_headers,
        )
    elif block == "mutation":
        client.post("/mutate/\u2605", headers=auth_headers)
    elif block == "observability":
        client.get("/nodos")
        client.get("/telemetry", headers=auth_headers)

    assert _journal_mode(isolate_db) == "wal", f"block {block} MUST operate in WAL"


def test_g3_bootstrap_anchors_in_wal(tmp_path, monkeypatch):
    """MUST: bootstrap's geodetic anchoring operates in WAL."""
    db_path = str(tmp_path / "bootstrap_wal.db")
    monkeypatch.setattr(bootstrap, "DB_PATH", db_path)
    octagon = {
        "AXIS_1": {
            "symbol": "\u25b2",
            "tag": "_SOMETHING",
            "vector": np.zeros(8, dtype=np.float64),
        }
    }
    bootstrap.anchor_in_sqlite(octagon)
    assert _journal_mode(db_path) == "wal"
