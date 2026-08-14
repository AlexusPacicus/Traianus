"""
Persistence hardening regression suite (SPEC-M2-DELTA-0-1 follow-up).

Closes the acceptance gaps found in the Δ1 review:
- No dead re-export shims in `traianus.app` (DB_PATH / persist_epsilon_edges):
  `traianus.storage` is the single owner of the SQLite lifecycle.
- No masked storage failures (AGENTS.md §1.3): geodetic reads fail loud.
- Ingestion node + queue-status mutation is a single atomic transaction.
- Idempotency-key handling is race-free (INSERT ... ON CONFLICT DO NOTHING).
"""
import sqlite3
import threading
import uuid

import pytest

import traianus.app as main
import traianus.bootstrap as bootstrap
import traianus.storage as storage
from traianus.app import async_spectral_processor
from helpers.db_factory import create_schema


def test_app_exposes_no_db_path_shim():
    """Δ1: `traianus.app` must not re-export DB_PATH (dead + dangerous shim)."""
    assert not hasattr(main, "DB_PATH")


def test_app_exposes_no_persist_epsilon_edges_shim():
    """Δ1: `traianus.app` must not re-export persist_epsilon_edges (unused)."""
    assert not hasattr(main, "persist_epsilon_edges")


def test_get_geodetic_matrix_db_fails_loud_on_schema_drift(isolate_db):
    """A drifted geodesic_axes (missing projection columns) must NOT be masked as empty."""
    with sqlite3.connect(isolate_db) as conn:
        conn.execute("DROP TABLE geodesic_axes")
        conn.execute(
            "CREATE TABLE geodesic_axes (id TEXT, epoch_provenance TEXT, created_at TIMESTAMP)"
        )
    with pytest.raises(sqlite3.OperationalError):
        storage.get_geodetic_matrix_db()


def test_get_current_dimension_db_fails_loud_on_missing_axes(isolate_db):
    """Missing geodesic_axes must NOT silently fall back to a magic 384."""
    with sqlite3.connect(isolate_db) as conn:
        conn.execute("DROP TABLE geodesic_axes")
    with pytest.raises(sqlite3.OperationalError):
        storage.get_current_dimension_db()


def test_ingestion_node_and_queue_commit_atomically(isolate_db):
    """If the queue-status update fails, the node revision must roll back too."""
    with sqlite3.connect(isolate_db) as conn:
        conn.execute(
            "INSERT INTO ingestion_queue (id, payload, status) VALUES (42, 'x', 'PENDING')"
        )
        conn.execute("""
            CREATE TRIGGER fail_queue_status
            BEFORE UPDATE ON ingestion_queue
            WHEN NEW.status = 'PROCESSED' AND NEW.id = 42
            BEGIN
                SELECT RAISE(ABORT, 'injected queue failure');
            END
        """)
    async_spectral_processor(42, "Entidad atómica")
    with sqlite3.connect(isolate_db) as conn:
        node = conn.execute(
            "SELECT 1 FROM manifold_nodes WHERE id = 'NODE_42'"
        ).fetchone()
        log = conn.execute(
            "SELECT 1 FROM manifold_nodes WHERE id = 'LOG_42'"
        ).fetchone()
    assert node is None, "node persisted despite queue failure (non-atomic)"
    assert log is not None, "failure log missing"


def test_enqueue_ingest_duplicate_returns_existing_id(isolate_db):
    """Same idempotency key twice: same ingestion id, second call flagged duplicate."""
    iid1, dup1 = storage.enqueue_ingest("a", "same-key")
    iid2, dup2 = storage.enqueue_ingest("b", "same-key")
    assert dup1 is False
    assert dup2 is True
    assert iid2 == iid1


def test_enqueue_ingest_concurrent_same_key_no_error(isolate_db):
    """Two concurrent requests with the same key must both succeed, never 503."""
    errors = []
    barrier = threading.Barrier(2)

    def worker(key):
        try:
            barrier.wait()
            storage.enqueue_ingest(f"payload-{key}", key)
        except Exception as e:  # deliberate collection for assertion
            errors.append(e)

    for _ in range(100):
        key = uuid.uuid4().hex
        threads = [threading.Thread(target=worker, args=(key,)) for _ in range(2)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == [], f"concurrent ingest raised: {errors[0]!r}"


def test_db_connection_closed_after_with_block(isolate_db):
    """Connection-per-operation: the connection must be closed when the with-block exits.

    `sqlite3.Connection.__exit__` commits/rolls back but never closes, so the
    handle survives until GC (`.closed` was removed in Python 3.11). The fix —
    a closing context manager — makes closure deterministic: any use after the
    with-block must raise ProgrammingError instead of silently succeeding.
    """
    ref = None
    with storage.get_db_connection() as conn:
        ref = conn
        conn.execute("SELECT 1")
    with pytest.raises(sqlite3.ProgrammingError):
        ref.execute("SELECT 1")


def test_db_connection_sets_busy_timeout(isolate_db):
    """WAL concurrency: parallel writers must retry instead of failing with 503.

    A `busy_timeout` makes SQLite wait for the write lock instead of raising
    `database is locked` under real (non-test) load.
    """
    with storage.get_db_connection() as conn:
        timeout_ms = conn.execute("PRAGMA busy_timeout").fetchone()[0]
    assert timeout_ms == 5000


def test_db_connection_commits_on_normal_exit(isolate_db):
    """A successful with-block commits the transaction."""
    key = f"commit-{uuid.uuid4().hex}"
    with storage.get_db_connection() as conn:
        conn.execute(
            "INSERT INTO ingestion_queue (payload, idempotency_key) VALUES (?, ?)",
            (key, key),
        )
    with storage.get_db_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM ingestion_queue WHERE idempotency_key = ?", (key,)
        ).fetchone()
    assert row is not None


def test_db_connection_rolls_back_on_exception(isolate_db):
    """An exception in the with-block rolls back; no partial write survives."""
    key = f"rollback-{uuid.uuid4().hex}"
    with pytest.raises(RuntimeError):
        with storage.get_db_connection() as conn:
            conn.execute(
                "INSERT INTO ingestion_queue (payload, idempotency_key) VALUES (?, ?)",
                (key, key),
            )
            raise RuntimeError("injected failure")
    with storage.get_db_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM ingestion_queue WHERE idempotency_key = ?", (key,)
        ).fetchone()
    assert row is None


def test_init_db_creates_geodesic_axes(tmp_path, monkeypatch):
    """Canonical DDL: init_db() alone must create the FULL schema incl. geodesic_axes.

    `geodesic_axes` used to be created only by bootstrap.anchor_in_sqlite, so a
    bare server boot produced an incomplete schema. storage.py is the single
    owner of the canonical DDL (finding #1 of the Δ1 review).
    """
    db_path = str(tmp_path / "init_only.db")
    monkeypatch.setattr(storage, "DB_PATH", db_path)
    storage.init_db()
    with sqlite3.connect(db_path) as conn:
        names = {
            r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    assert "geodesic_axes" in names


def test_bootstrap_anchor_is_self_sufficient(tmp_path, monkeypatch):
    """bootstrap must not need a pre-existing schema: anchor_in_sqlite self-initializes."""
    db_path = str(tmp_path / "bootstrap_only.db")
    monkeypatch.setattr(storage, "DB_PATH", db_path)
    octagon = bootstrap.extract_pure_octagon()
    bootstrap.anchor_in_sqlite(octagon)
    with sqlite3.connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM geodesic_axes").fetchone()[0]
    assert count == len(octagon)


def test_consolidar_empty_basis_returns_400(client, auth_headers, tmp_path, monkeypatch):
    """Consolidating before bootstrap must fail loud with 4xx, not a generic 500."""
    db_path = str(tmp_path / "empty_basis.db")
    monkeypatch.setattr(storage, "DB_PATH", db_path)
    with sqlite3.connect(db_path) as conn:
        create_schema(conn)  # full schema, NO seeded axes -> empty geodetic basis
    resp = client.post(
        "/nodos/NODE_1/consolidar",
        json={"text": "x", "ethical_key": True},
        headers=auth_headers,
    )
    assert resp.status_code == 400
