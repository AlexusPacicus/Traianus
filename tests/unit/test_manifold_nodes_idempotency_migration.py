"""R1-INV4: manifold_nodes carries a nullable idempotency_key with a UNIQUE
index. Fresh and migrated databases converge, node history is never rewritten,
and the storage boundary tells a duplicate key from an (id, seq) collision."""
import sqlite3
import threading

import pytest

import traianus.storage._storage as storage_impl
from traianus import storage
from traianus.storage import MANIFOLD_NODES_DDL

KEY_COLUMN_LINE = "    idempotency_key TEXT,\n"
ORIGINAL_COLUMNS = (
    "id, seq, text, toon_factor, lifecycle_state, action_potential, "
    "revision_milestone, vector_blob, projections_json, epoch_provenance, "
    "event_type, sys_internal_timestamp"
)
LEGACY_BODY = (
    "text TEXT NOT NULL, toon_factor TEXT NOT NULL, lifecycle_state TEXT NOT NULL, "
    "action_potential REAL NOT NULL, revision_milestone INTEGER NOT NULL, "
    "vector_blob BLOB NOT NULL, projections_json TEXT NOT NULL"
)
LEGACY_SCHEMAS = [
    pytest.param(
        f"CREATE TABLE manifold_nodes (id TEXT PRIMARY KEY, {LEGACY_BODY})",
        "id",
        "?",
        id="pre_seq",
    ),
    pytest.param(
        f"CREATE TABLE manifold_nodes (id TEXT NOT NULL, seq INTEGER NOT NULL, {LEGACY_BODY}, "
        "PRIMARY KEY (id, seq))",
        "id, seq",
        "?, 1",
        id="pre_epoch",
    ),
]


def _unique_index_columns(conn):
    indexes = conn.execute("PRAGMA index_list(manifold_nodes)").fetchall()
    return [
        [col[2] for col in conn.execute(f"PRAGMA index_info({index[1]})").fetchall()]
        for index in indexes
        if index[2]
    ]


def _columns(conn):
    return [row[1] for row in conn.execute("PRAGMA table_info(manifold_nodes)").fetchall()]


def _snapshot(conn):
    return conn.execute(
        f"SELECT {ORIGINAL_COLUMNS} FROM manifold_nodes ORDER BY id, seq"
    ).fetchall()


def _schema(conn):
    return conn.execute("SELECT type, name, sql FROM sqlite_master ORDER BY name").fetchall()


def _insert(node_id, key=None, state="incubating", guard=False):
    return storage.insert_node_revision(
        node_id, "t", "▲", state, 0.1, 0, b"\x00" * 8, "{}", "PROSTHETIC_NSM_V1",
        guard_consolidated=guard, idempotency_key=key,
    )


def _keyed_rows(db_path):
    with sqlite3.connect(db_path) as conn:
        return conn.execute(
            "SELECT id, seq, idempotency_key FROM manifold_nodes ORDER BY id, seq"
        ).fetchall()


def _pre_change_ddl():
    ddl = MANIFOLD_NODES_DDL.replace(KEY_COLUMN_LINE, "")
    assert ddl != MANIFOLD_NODES_DDL, "canonical DDL has no idempotency_key column"
    return ddl


@pytest.fixture
def pre_change_db(tmp_path, monkeypatch):
    """A database holding the schema as it was before R1-INV4: several nodes with
    several revisions each, one consolidated, one telemetry error row."""
    path = str(tmp_path / "pre_change.db")
    insert = (
        "INSERT INTO manifold_nodes (id, seq, text, toon_factor, lifecycle_state, "
        "action_potential, revision_milestone, vector_blob, projections_json) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
    )
    with sqlite3.connect(path) as conn:
        conn.execute(_pre_change_ddl())
        for node_id, revisions in (("A", 3), ("B", 2), ("C", 4)):
            for seq in range(1, revisions + 1):
                state = "consolidated" if (node_id, seq) == ("B", 2) else "incubating"
                conn.execute(insert, (
                    node_id, seq, f"{node_id}{seq}", "▲", state, 0.1 * seq,
                    int(state == "consolidated"), bytes([seq]) * 8, "{}",
                ))
        conn.execute(
            "INSERT INTO manifold_nodes (id, seq, text, toon_factor, lifecycle_state, "
            "action_potential, revision_milestone, vector_blob, projections_json, event_type) "
            "VALUES ('T', 1, 'boom', 'x', 'telemetry_error', 0.0, 0, x'00', '{}', 'ERROR')"
        )
    monkeypatch.setattr(storage, "DB_PATH", path)
    return path


def test_fresh_database_has_the_unique_index_and_unkeyed_rows_coexist(isolate_db):
    for node_id in ("N1", "N1", "N2"):
        _insert(node_id)
    with sqlite3.connect(isolate_db) as conn:
        assert ["idempotency_key"] in _unique_index_columns(conn)
        (unkeyed,) = conn.execute(
            "SELECT COUNT(*) FROM manifold_nodes WHERE idempotency_key IS NULL"
        ).fetchone()
    assert unkeyed == 3


def test_init_db_on_a_fresh_file_creates_the_column_and_the_unique_index(tmp_path, monkeypatch):
    path = str(tmp_path / "fresh.db")
    monkeypatch.setattr(storage, "DB_PATH", path)
    storage.init_db()
    with sqlite3.connect(path) as conn:
        assert "idempotency_key" in _columns(conn)
        assert ["idempotency_key"] in _unique_index_columns(conn)


def test_migration_adds_column_and_index_and_leaves_history_untouched(pre_change_db):
    with sqlite3.connect(pre_change_db) as conn:
        before = _snapshot(conn)
    assert len(before) == 10
    storage.init_db()
    with sqlite3.connect(pre_change_db) as conn:
        assert "idempotency_key" in _columns(conn)
        assert ["idempotency_key"] in _unique_index_columns(conn)
        assert _snapshot(conn) == before
        (keyed,) = conn.execute(
            "SELECT COUNT(*) FROM manifold_nodes WHERE idempotency_key IS NOT NULL"
        ).fetchone()
    assert keyed == 0


def test_migrated_schema_equals_the_fresh_schema(pre_change_db, tmp_path, monkeypatch):
    storage.init_db()
    with sqlite3.connect(pre_change_db) as conn:
        migrated = (_columns(conn), _unique_index_columns(conn))
    monkeypatch.setattr(storage, "DB_PATH", str(tmp_path / "fresh.db"))
    storage.init_db()
    with sqlite3.connect(str(tmp_path / "fresh.db")) as conn:
        assert (_columns(conn), _unique_index_columns(conn)) == migrated


def test_running_init_twice_changes_nothing(pre_change_db):
    storage.init_db()
    with sqlite3.connect(pre_change_db) as conn:
        schema, rows = _schema(conn), _snapshot(conn)
    storage.init_db()
    with sqlite3.connect(pre_change_db) as conn:
        assert (_schema(conn), _snapshot(conn)) == (schema, rows)


@pytest.mark.parametrize(("create_sql", "id_columns", "id_marks"), LEGACY_SCHEMAS)
def test_legacy_databases_still_upgrade_and_gain_the_key_index(
    tmp_path, monkeypatch, create_sql, id_columns, id_marks
):
    path = str(tmp_path / "legacy.db")
    with sqlite3.connect(path) as conn:
        conn.execute(create_sql)
        for node_id, state in (("A", "incubating"), ("B", "consolidated"), ("C", "telemetry_error")):
            conn.execute(
                f"INSERT INTO manifold_nodes ({id_columns}, text, toon_factor, lifecycle_state, "
                "action_potential, revision_milestone, vector_blob, projections_json) "
                f"VALUES ({id_marks}, ?, 'x', ?, 0.5, 0, x'00', '{{}}')",
                (node_id, f"text-{node_id}", state),
            )
    monkeypatch.setattr(storage, "DB_PATH", path)
    storage.init_db()
    with sqlite3.connect(path) as conn:
        rows = conn.execute(
            "SELECT id, seq, text, lifecycle_state, event_type, idempotency_key "
            "FROM manifold_nodes ORDER BY id"
        ).fetchall()
        assert ["idempotency_key"] in _unique_index_columns(conn)
    assert rows == [
        ("A", 1, "text-A", "incubating", None, None),
        ("B", 1, "text-B", "consolidated", None, None),
        ("C", 1, "text-C", "telemetry_error", "ERROR", None),
    ]


def test_node_by_idempotency_key_finds_the_keyed_revision(isolate_db):
    with storage.get_db_connection() as conn:
        assert storage.node_by_idempotency_key(conn, "k") is None
    _insert("A", key="k")
    _insert("A")
    with storage.get_db_connection() as conn:
        assert storage.node_by_idempotency_key(conn, "k") == ("A", 1)


@pytest.mark.parametrize("second_node", ["A", "B"])
def test_second_insert_with_the_same_key_is_a_duplicate(isolate_db, second_node):
    assert _insert("A", key="k") == 1
    with pytest.raises(storage.DuplicateIdempotencyKeyError) as excinfo:
        _insert(second_node, key="k")
    assert (excinfo.value.node_id, excinfo.value.seq) == ("A", 1)
    assert _keyed_rows(isolate_db) == [("A", 1, "k")]


def test_a_duplicate_key_is_not_a_storage_error():
    assert not issubclass(storage.DuplicateIdempotencyKeyError, storage.StorageError)


def test_duplicate_key_is_not_retried(isolate_db, monkeypatch):
    _insert("A", key="k")
    calls = []
    real = storage_impl.next_node_seq

    def counting(conn, node_id):
        calls.append(node_id)
        return real(conn, node_id)

    monkeypatch.setattr(storage_impl, "next_node_seq", counting)
    with pytest.raises(storage.DuplicateIdempotencyKeyError):
        _insert("A", key="k")
    assert len(calls) == 1


def test_seq_collision_with_a_fresh_key_is_still_retried_then_raised(isolate_db, monkeypatch):
    _insert("A", key="k1")
    calls = []

    def stuck(conn, node_id):
        calls.append(node_id)
        return 1

    monkeypatch.setattr(storage_impl, "next_node_seq", stuck)
    with pytest.raises(sqlite3.IntegrityError):
        _insert("A", key="k2")
    assert len(calls) == 3
    assert _keyed_rows(isolate_db) == [("A", 1, "k1")]


def test_duplicate_key_wins_over_the_consolidated_guard(isolate_db):
    _insert("A", key="k")
    _insert("A", state="consolidated")
    with pytest.raises(storage.DuplicateIdempotencyKeyError):
        _insert("A", key="k", guard=True)
    with pytest.raises(storage.ConsolidatedRegressionError):
        _insert("A", key="fresh", guard=True)
    assert _keyed_rows(isolate_db) == [("A", 1, "k"), ("A", 2, None)]


def test_concurrent_inserts_with_one_key_leave_exactly_one_row(isolate_db):
    workers = 6
    barrier = threading.Barrier(workers)
    outcomes = []

    def worker(index):
        barrier.wait()
        node_id = "A" if index % 2 else f"N{index}"
        try:
            _insert(node_id, key="k")
            outcomes.append("inserted")
        except storage.DuplicateIdempotencyKeyError:
            outcomes.append("duplicate")
        except sqlite3.Error as exc:
            outcomes.append(repr(exc))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(workers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(outcomes) == ["duplicate"] * (workers - 1) + ["inserted"]
    assert len(_keyed_rows(isolate_db)) == 1
