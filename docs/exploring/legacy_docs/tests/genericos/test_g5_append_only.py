"""
G5 — Append-only (findings H4/ADR-025#1, audit TRAIANUS_AUDIT.md:47,77).

Normative (RFC 2119): node history (manifold_nodes) MUST be
append-only: every transition INSERTS a new revision with increasing `seq`;
UPDATE/REPLACE/DELETE on manifold_nodes is PROHIBITED in production.
Observation (GET) MUST NOT generate mutations (ADR-025#2).

Normative: docs/archive/legacy_docs/development/tests/SPEC-global.md
Coverage: G5
"""
import ast
import os
import sqlite3
from pathlib import Path

import numpy as np
import pytest

import traianus.app as main
from traianus.app import serialize_vector
from helpers.endpoint_registry import BLOCKS

APPEND_ONLY_BLOCKS = ["ingestion", "consolidation", "relations", "mutation", "observability"]

PROD_FILES = ("traianus/app.py", "traianus/bootstrap.py")
ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("block", APPEND_ONLY_BLOCKS)
def test_g5_no_destructive_statements_on_nodes(block):
    """MUST: production code contains no destructive statements on nodes."""
    repo_root = os.path.join(os.path.dirname(__file__), "..", "..")
    for rel in PROD_FILES:
        with open(os.path.join(repo_root, rel), encoding="utf-8") as fh:
            source = fh.read()
        assert "UPDATE manifold_nodes" not in source, f"{rel}: UPDATE prohibited (H4)"
        assert "REPLACE INTO manifold_nodes" not in source, f"{rel}: REPLACE prohibited (H4)"
        assert "DELETE FROM manifold_nodes" not in source, f"{rel}: DELETE prohibited (H4)"


def test_g5_consolidation_inserts_new_revision(isolate_db, client, auth_headers):
    """MUST (consolidation): consolidate INSERTS a new revision with increasing seq."""
    response = client.post(
        "/ingesta", json={"type": "text/plain", "text": "append-only probe"}, headers=auth_headers
    )
    assert response.status_code == 200
    node_id = f"NODE_{response.json()['ingestion_id']}"

    client.post(
        f"/nodos/{node_id}/consolidar",
        json={"text": "append-only probe", "ethical_key": True},
        headers=auth_headers,
    )

    with sqlite3.connect(isolate_db) as conn:
        rows = conn.execute(
            "SELECT seq FROM manifold_nodes WHERE id = ? ORDER BY seq", (node_id,)
        ).fetchall()
    assert len(rows) >= 2, "original revision + consolidated revision must exist"
    seqs = [r[0] for r in rows]
    assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)


@pytest.mark.parametrize("block", ["observability", "relations"])
def test_g5_observation_no_state_mutation(block, client, auth_headers, isolate_db):
    """MUST (ADR-025#2): GET creates no new rows."""
    client.post("/ingesta", json={"type": "text/plain", "text": "x"}, headers=auth_headers)
    before_nodes = _count(isolate_db, "manifold_nodes")
    before_edges = _count(isolate_db, "manifold_edges")

    if block == "observability":
        client.get("/nodos")
        client.get("/telemetry", headers=auth_headers)
    else:
        client.get("/relations", headers=auth_headers)

    assert _count(isolate_db, "manifold_nodes") == before_nodes
    assert _count(isolate_db, "manifold_edges") == before_edges


def _count(db_path, table):
    with sqlite3.connect(db_path) as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def test_g5_manifold_edges_composite_pk(isolate_db):
    """H4 residual: manifold_edges is a revision log with composite PK (id, seq)."""
    with sqlite3.connect(isolate_db) as conn:
        pk = [
            row[1]
            for row in conn.execute("PRAGMA table_info(manifold_edges)").fetchall()
            if row[5] > 0
        ]
    assert pk == ["id", "seq"], f"manifold_edges PK must be (id, seq), got {pk}"


def _has_update_geodesic_axes(func_node) -> bool:
    for c in ast.walk(func_node):
        if (
            isinstance(c, ast.Call)
            and isinstance(c.func, ast.Attribute)
            and c.func.attr == "execute"
            and c.args
            and isinstance(c.args[0], ast.Constant)
            and isinstance(c.args[0].value, str)
            and "UPDATE geodesic_axes" in c.args[0].value
        ):
            return True
    return False


def test_g5_geodesic_axes_update_restricted_to_mutate():
    """H4 residual: the only geodesic_axes UPDATE lives inside logographic_genesis.

    bootstrap.py must not mutate the basis at all (INSERT OR IGNORE only).
    """
    app_source = (ROOT / "traianus/app.py").read_text(encoding="utf-8")
    tree = ast.parse(app_source)
    logographic = next(
        f for f in ast.walk(tree)
        if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))
        and f.name == "logographic_genesis"
    )
    lo, hi = logographic.lineno, logographic.end_lineno
    update_lines = [
        lineno for lineno, line in enumerate(app_source.splitlines(), start=1)
        if "UPDATE geodesic_axes" in line
    ]
    assert update_lines, "MUST: at least one UPDATE geodesic_axes exists (logographic_genesis)"
    assert all(lo <= lineno <= hi for lineno in update_lines), (
        f"UPDATE geodesic_axes outside logographic_genesis: {update_lines}"
    )
    bootstrap_source = (ROOT / "traianus/bootstrap.py").read_text(encoding="utf-8")
    assert "UPDATE geodesic_axes" not in bootstrap_source, (
        "bootstrap MUST NOT mutate the geodetic basis (INSERT OR IGNORE only)"
    )


def test_g5_migration_legacy_nodes_to_revision_log(tmp_path, monkeypatch):
    """H4 migration: a legacy manifold_nodes (no seq) becomes seq=1 revisions."""
    db = str(tmp_path / "legacy_nodes.db")
    with sqlite3.connect(db) as conn:
        conn.execute("""
            CREATE TABLE manifold_nodes (
                id TEXT NOT NULL,
                text TEXT NOT NULL,
                toon_factor TEXT NOT NULL,
                lifecycle_state TEXT NOT NULL,
                action_potential REAL NOT NULL,
                revision_milestone INTEGER NOT NULL,
                vector_blob BLOB NOT NULL,
                projections_json TEXT NOT NULL
            )
        """)
        conn.execute(
            "INSERT INTO manifold_nodes (id, text, toon_factor, lifecycle_state, "
            "action_potential, revision_milestone, vector_blob, projections_json) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            ("NODE_LEGACY", "legacy text", "\u25b2", "incubating", 0.5, 0,
             serialize_vector(np.zeros(4)), "{}"),
        )
        conn.commit()

    monkeypatch.setattr(main, "DB_PATH", db)
    main.init_db()

    with sqlite3.connect(db) as conn:
        rows = conn.execute(
            "SELECT id, seq, text FROM manifold_nodes"
        ).fetchall()
    assert rows == [("NODE_LEGACY", 1, "legacy text")], (
        "migration MUST preserve legacy nodes as seq=1 revisions without data loss"
    )


def test_g5_migration_legacy_edges_to_revision_log(tmp_path, monkeypatch):
    """H4 migration: a legacy manifold_edges (no seq) becomes seq=1 revisions."""
    db = str(tmp_path / "legacy_edges.db")
    with sqlite3.connect(db) as conn:
        conn.execute("""
            CREATE TABLE manifold_edges (
                id TEXT NOT NULL,
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                state TEXT NOT NULL
            )
        """)
        conn.execute(
            "INSERT INTO manifold_edges (id, source, target, state) VALUES (?, ?, ?, ?)",
            ("edge-A-B", "A", "B", "manual"),
        )
        conn.commit()

    monkeypatch.setattr(main, "DB_PATH", db)
    main.init_db()

    with sqlite3.connect(db) as conn:
        rows = conn.execute(
            "SELECT id, seq, source, target, state FROM manifold_edges"
        ).fetchall()
    assert rows == [("edge-A-B", 1, "A", "B", "manual")], (
        "migration MUST preserve legacy edges as seq=1 revisions without data loss"
    )
