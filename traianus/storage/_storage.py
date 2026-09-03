"""Persistence layer (SPEC-M2-DELTA-0-1, Δ1).

Single owner of the SQLite storage lifecycle: connection factory, canonical
DDL + migrations, revision sequences, epoch/axis reads, and fine-grained
persistence functions. The HTTP layer (`traianus/app.py`) and the bootstrap
entry point delegate every SQL statement to this module; no other module in
`traianus/` performs direct `sqlite3` I/O.

Design invariants (SPEC-REFACTOR-v0.2 / audit H4):
* Append-only node/edge revision logs: composite PK `(id, seq)`; never
  UPDATE/REPLACE/DELETE on `manifold_nodes`/`manifold_edges`.
* `geodesic_axes` is mutable ONLY inside logographic genesis (epoch-append).
* Every connection runs `PRAGMA journal_mode=WAL` and is used
  connection-per-operation (no shared long-lived connection); each connection
  is closed deterministically when its `with` block exits, never deferred to
  the garbage collector.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

import numpy as np

from traianus.core import compute_epsilon_edges


def _active_db_path() -> str:
    """Resolves the active DB path from the storage package (ADR-025 §2.1).

    Single source of truth is ``traianus.storage.DB_PATH``. Resolved lazily
    at call time (never bound at import) so test/tool overrides via
    ``storage.DB_PATH = X`` take effect globally without dual patches.
    """
    from traianus import storage as _pkg

    return _pkg.DB_PATH


# =====================================================================
# SHARED TABLE DDL (ADR-025 amendment A1: single source of truth).
# Canonical CREATE TABLE statements for the data/control planes.
# Consumed by init_relational_tables() (production), SQLiteEngine
# (polar pipeline) and tests/helpers/db_factory.py (harness) so the
# schema cannot diverge between owners. Index DDL stays with the
# engine (query optimization, not schema).
# =====================================================================

DATA_PLANE_DDL = """
CREATE TABLE IF NOT EXISTS data_plane (
    node_id TEXT PRIMARY KEY,
    vector_blob BLOB NOT NULL,
    dimension INTEGER NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

CONTROL_PLANE_DDL = """
CREATE TABLE IF NOT EXISTS control_plane (
    node_id TEXT PRIMARY KEY,
    centroid_id INTEGER NOT NULL,
    version INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (node_id) REFERENCES data_plane(node_id)
)
"""

# Telemetry event vocabulary for manifold_nodes.event_type (ADR-025 A1).
EVENT_ERROR = "ERROR"
EVENT_RECALIBRATION_SIGNAL = "RECALIBRATION_SIGNAL"

INGESTION_QUEUE_DDL = """
CREATE TABLE IF NOT EXISTS ingestion_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payload TEXT NOT NULL,
    idempotency_key TEXT UNIQUE,
    status TEXT DEFAULT 'PENDING',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
"""

MANIFOLD_NODES_DDL = """
CREATE TABLE IF NOT EXISTS manifold_nodes (
    id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    text TEXT NOT NULL,
    toon_factor TEXT NOT NULL,
    lifecycle_state TEXT NOT NULL,
    action_potential REAL NOT NULL,
    revision_milestone INTEGER NOT NULL,
    vector_blob BLOB NOT NULL,
    projections_json TEXT NOT NULL,
    epoch_provenance TEXT NOT NULL DEFAULT 'PROSTHETIC_NSM_V1',
    event_type TEXT NOT NULL DEFAULT 'ERROR' CHECK (event_type IN ('ERROR', 'RECALIBRATION_SIGNAL')),
    sys_internal_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, seq),
    CHECK (lifecycle_state IN ('pending_approval', 'incubating', 'consolidated', 'telemetry_error'))
)
"""

MANIFOLD_EDGES_DDL = """
CREATE TABLE IF NOT EXISTS manifold_edges (
    id TEXT NOT NULL,
    seq INTEGER NOT NULL,
    source TEXT NOT NULL,
    target TEXT NOT NULL,
    state TEXT NOT NULL,
    sys_internal_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, seq)
)
"""

GEODESIC_AXES_DDL = """
CREATE TABLE IF NOT EXISTS geodesic_axes (
    id TEXT NOT NULL,
    simbolo TEXT NOT NULL,
    tag TEXT NOT NULL,
    vector_blob BLOB NOT NULL,
    epoch_provenance TEXT NOT NULL DEFAULT 'PROSTHETIC_NSM_V1',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id, epoch_provenance)
)
"""

AUDIT_LOG_DDL = """
CREATE TABLE IF NOT EXISTS audit_log (
    case_id TEXT PRIMARY KEY,
    timestamp TEXT DEFAULT (datetime('now')),
    intent_class TEXT,
    target_file TEXT,
    decision TEXT NOT NULL,
    safety_abort TEXT
)
"""


@contextmanager
def get_db_connection() -> Iterator[sqlite3.Connection]:
    """Yields a WAL-enabled connection to the active DB_PATH.

    Import of this module is side-effect free: the database is only touched
    when a connection is requested. On exit the surrounding transaction commits
    on success / rolls back on exception and the connection is always closed,
    so closure is deterministic and independent of the garbage collector.
    Callers use `with get_db_connection() as conn:` — never as a raw factory.
    """
    conn = sqlite3.connect(_active_db_path())
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout = 5000")
    try:
        yield conn
    except BaseException:
        conn.rollback()
        raise
    else:
        conn.commit()
    finally:
        conn.close()


# =====================================================================
# CANONICAL DDL + MIGRATIONS
# =====================================================================

def init_relational_tables():
    with get_db_connection() as conn:
        conn.execute(INGESTION_QUEUE_DDL)
        # Legacy migration (SPEC v0.2 §3.3 A-c): ALTER cannot add a UNIQUE
        # constraint, so a legacy queue table is rebuilt (RENAME -> recreate ->
        # copy -> drop), mirroring the manifold_nodes/edges seq migrations.
        queue_cols = [
            row[1] for row in conn.execute("PRAGMA table_info(ingestion_queue)").fetchall()
        ]
        if queue_cols and "idempotency_key" not in queue_cols:
            conn.execute("ALTER TABLE ingestion_queue RENAME TO ingestion_queue_legacy")
            conn.execute(INGESTION_QUEUE_DDL)
            conn.execute("""
                INSERT INTO ingestion_queue (id, payload, status, created_at)
                SELECT id, payload, status, created_at FROM ingestion_queue_legacy
            """)
            conn.execute("DROP TABLE ingestion_queue_legacy")
        # =================================================================
        # H4 — APPEND-ONLY NODE LOG (invariant #1 ADR-025 / §6.2)
        # Intent_Class: the node log is immutable; every state transition
        #   INSERTS a new revision with increasing `seq` per `id`.
        # Runtime_Contract: composite PK (id, seq); never UPDATE/REPLACE/
        #   DELETE on manifold_nodes; "current state" = MAX(seq) per id.
        # Implementation_Block: revision log DDL below.
        # Topological_Grounding: ADR-025 §"Monotonic Append-Only Evolution"
        # (docs/architecture/ADR/ADR.md:126, literal quote, one line):
        # "State evolution $S_n \to S_{n+1}$ is append-only. Historical vertices, deterministic edges, and simplicial faces in persistent storage are immutable."
        # Safety_Abort: if the legacy schema cannot be migrated without loss,
        #   the transaction aborts (rollback) and the error propagates.
        # =================================================================
        conn.execute(MANIFOLD_NODES_DDL)
        # Schema migration for pre-H4 DBs (derived artifact): each existing
        # node becomes its revision seq=1. History is preserved.
        legacy_cols = [
            row[1] for row in conn.execute("PRAGMA table_info(manifold_nodes)").fetchall()
        ]
        if legacy_cols and "seq" not in legacy_cols:
            conn.execute("ALTER TABLE manifold_nodes RENAME TO manifold_nodes_legacy")
            conn.execute(MANIFOLD_NODES_DDL)
            conn.execute("""
                INSERT INTO manifold_nodes
                (id, seq, text, toon_factor, lifecycle_state, action_potential,
                 revision_milestone, vector_blob, projections_json, event_type)
                SELECT id, 1, text, toon_factor, lifecycle_state, action_potential,
                       revision_milestone, vector_blob, projections_json, 'ERROR'
                FROM manifold_nodes_legacy
            """)
            conn.execute("DROP TABLE manifold_nodes_legacy")
        # SPEC v0.2 §3.1 migration (v0.1 DBs): add `epoch_provenance` and the
        # lifecycle CHECK. SQLite cannot ALTER-ADD a CHECK, so the table is
        # rebuilt (RENAME -> recreate -> copy -> drop), backfilling the epoch.
        v02_cols = [
            row[1] for row in conn.execute("PRAGMA table_info(manifold_nodes)").fetchall()
        ]
        if v02_cols and "epoch_provenance" not in v02_cols:
            conn.execute("ALTER TABLE manifold_nodes RENAME TO manifold_nodes_v01")
            conn.execute(MANIFOLD_NODES_DDL)
            conn.execute("""
                INSERT INTO manifold_nodes
                (id, seq, text, toon_factor, lifecycle_state, action_potential,
                 revision_milestone, vector_blob, projections_json, event_type)
                SELECT id, seq, text, toon_factor, lifecycle_state, action_potential,
                       revision_milestone, vector_blob, projections_json, 'ERROR'
                FROM manifold_nodes_v01
            """)
            conn.execute("DROP TABLE manifold_nodes_v01")
        # Telemetry disambiguation (ADR-025 amendment A1): event_type
        # separates persistence failures ('ERROR') from Schmitt Trigger
        # recalibration signals ('RECALIBRATION_SIGNAL'). Pre-A1 databases
        # backfill to 'ERROR' via the column DEFAULT.
        event_cols = [
            row[1] for row in conn.execute("PRAGMA table_info(manifold_nodes)").fetchall()
        ]
        if event_cols and "event_type" not in event_cols:
            conn.execute(
                "ALTER TABLE manifold_nodes ADD COLUMN "
                "event_type TEXT NOT NULL DEFAULT 'ERROR'"
            )
        conn.execute(MANIFOLD_EDGES_DDL)
        # Schema migration for pre-H4 DBs: each existing edge becomes its
        # revision seq=1. History is preserved (append-only invariant #1).
        legacy_edge_cols = [
            row[1] for row in conn.execute("PRAGMA table_info(manifold_edges)").fetchall()
        ]
        if legacy_edge_cols and "seq" not in legacy_edge_cols:
            conn.execute("ALTER TABLE manifold_edges RENAME TO manifold_edges_legacy")
            conn.execute(MANIFOLD_EDGES_DDL)
            conn.execute("""
                INSERT INTO manifold_edges (id, seq, source, target, state)
                SELECT id, 1, source, target, state FROM manifold_edges_legacy
            """)
            conn.execute("DROP TABLE manifold_edges_legacy")
        # Data/control planes (ADR-025 §2.1): owned here, consumed by
        # SQLiteEngine and the test harness from the shared DDL above.
        conn.execute(DATA_PLANE_DDL)
        conn.execute(CONTROL_PLANE_DDL)
        _init_geodesic_axes(conn)


def _init_geodesic_axes(conn: sqlite3.Connection) -> None:
    """Creates geodesic_axes + runs the epoch-PK migration (SPEC v0.2 §3.1).

    The geodetic basis MUST support multiple epochs (one immutable row set per
    epoch_provenance), so the primary key is composite (id, epoch_provenance).
    SQLite cannot change a PK via ALTER: a legacy table (PK = id) is rebuilt,
    backfilling the epoch label. Owned here (canonical DDL), not by bootstrap.
    """
    conn.execute(GEODESIC_AXES_DDL)
    axis_sql = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='geodesic_axes'"
    ).fetchone()
    if axis_sql and "PRIMARY KEY (id, epoch_provenance)" not in (axis_sql[0] or ""):
        conn.execute("ALTER TABLE geodesic_axes RENAME TO geodesic_axes_legacy")
        conn.execute(GEODESIC_AXES_DDL)
        conn.execute("""
            INSERT INTO geodesic_axes (id, simbolo, tag, vector_blob)
            SELECT id, simbolo, tag, vector_blob FROM geodesic_axes_legacy
        """)
        conn.execute("DROP TABLE geodesic_axes_legacy")


def init_db():
    """Initializes relational tables at the active DB_PATH."""
    init_relational_tables()


# =====================================================================
# REVISION SEQUENCES
# =====================================================================

def next_node_seq(conn: sqlite3.Connection, node_id: str) -> int:
    """Next revision sequence for a node in the append-only log (H4)."""
    row = conn.execute(
        "SELECT COALESCE(MAX(seq), 0) + 1 FROM manifold_nodes WHERE id = ?",
        (node_id,),
    ).fetchone()
    return int(row[0])


def next_edge_seq(conn: sqlite3.Connection, edge_id: str) -> int:
    """Next revision sequence for an edge in the append-only log (H4)."""
    row = conn.execute(
        "SELECT COALESCE(MAX(seq), 0) + 1 FROM manifold_edges WHERE id = ?",
        (edge_id,),
    ).fetchone()
    return int(row[0])


# =====================================================================
# EPOCH / GEODETIC BASELINE READS
# =====================================================================

def active_epoch() -> str:
    """Active epoch = most recently created epoch_provenance in geodesic_axes.

    Cross-epoch comparisons are prohibited (M-f): the projection basis and
    the node anchoring must both use the active epoch.
    """
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT epoch_provenance FROM geodesic_axes "
            "GROUP BY epoch_provenance ORDER BY MAX(created_at) DESC LIMIT 1"
        ).fetchone()
    return row[0] if row else "PROSTHETIC_NSM_V1"


def get_geodetic_matrix_db() -> dict:
    """
    Loads the geodetic baseline from SQLite.

    Returns {axis_id: {"symbol": str, "vector": np.ndarray}} keyed by the
    unique axis id (e.g. `AXIS_1`) for the ACTIVE epoch only.
    """
    active = active_epoch()
    matrix = {}
    with get_db_connection() as conn:
        rows = conn.execute(
            "SELECT id, simbolo, tag, vector_blob FROM geodesic_axes "
            "WHERE epoch_provenance = ? ORDER BY id",
            (active,),
        ).fetchall()
        for axis_id, symbol, tag, blob in rows:
            vec = np.frombuffer(blob, dtype=np.float64)
            matrix[axis_id] = {"symbol": symbol, "vector": vec}
    return matrix


def get_current_dimension_db() -> int:
    """Dimension of the active epoch's axes. Fails loud (no magic fallback).

    A missing/drifted `geodesic_axes` must propagate as an error instead of
    silently returning the default 384 (AGENTS.md §1.3 / audit M5). The 384
    fallback only applies to a valid-but-empty basis.
    """
    active = active_epoch()
    with get_db_connection() as conn:
        row = conn.execute(
            "SELECT vector_blob FROM geodesic_axes "
            "WHERE epoch_provenance = ? LIMIT 1",
            (active,),
        ).fetchone()
    if row:
        axis_vector = np.frombuffer(row[0], dtype=np.float64)
        return len(axis_vector)
    return 384


def get_active_epoch_axes() -> list[tuple]:
    """Current active-epoch axis rows (id, simbolo, tag, vector_blob)."""
    active = active_epoch()
    with get_db_connection() as conn:
        return conn.execute(
            "SELECT id, simbolo, tag, vector_blob FROM geodesic_axes "
            "WHERE epoch_provenance = ? ORDER BY id",
            (active,),
        ).fetchall()


def insert_axis(conn: sqlite3.Connection, axis_id: str, symbol: str, tag: str,
                vector_blob: bytes, epoch: str) -> None:
    """Inserts one geodesic axis row under an epoch (logographic genesis)."""
    conn.execute(
        "INSERT INTO geodesic_axes (id, simbolo, tag, vector_blob, epoch_provenance) "
        "VALUES (?, ?, ?, ?, ?)",
        (axis_id, symbol, tag, vector_blob, epoch),
    )


# =====================================================================
# INGESTION QUEUE
# =====================================================================

class StorageError(Exception):
    """Raised by persistence functions on unrecoverable storage failures."""


def enqueue_ingest(text: str, idempotency_key: str | None) -> tuple[int, bool]:
    """Persists a raw ingestion payload; returns (ingestion_id, duplicate).

    When an idempotency key is provided and already present, the existing
    ingestion id is returned with `duplicate=True` (SPEC v0.2 §3.4).

    Race-free: the INSERT is atomic (`ON CONFLICT(idempotency_key) DO
    NOTHING`); a competing request that already inserted the key is detected
    by `rowcount == 0` and resolved by re-reading the existing id. There is
    no SELECT-then-INSERT window that can raise a UNIQUE-constraint error.
    """
    try:
        with get_db_connection() as conn:
            cur = conn.execute(
                "INSERT INTO ingestion_queue (payload, idempotency_key) "
                "VALUES (?, ?) ON CONFLICT(idempotency_key) DO NOTHING",
                (text, idempotency_key),
            )
            if cur.rowcount == 0 and idempotency_key is not None:
                row = conn.execute(
                    "SELECT id FROM ingestion_queue WHERE idempotency_key = ?",
                    (idempotency_key,),
                ).fetchone()
                return int(row[0]), True
            if cur.lastrowid is None:
                raise StorageError("ingestion INSERT returned no row id")
            return int(cur.lastrowid), False
    except sqlite3.Error as e:
        raise StorageError(str(e)) from e


def mark_queue_processed(conn: sqlite3.Connection, ingestion_id: int) -> None:
    conn.execute("UPDATE ingestion_queue SET status = 'PROCESSED' WHERE id = ?", (ingestion_id,))


# =====================================================================
# NODE REVISION LOG
# =====================================================================

def _insert_node_revision(conn: sqlite3.Connection, node_id: str, text: str,
                          toon_factor: str, lifecycle_state: str, action_potential: float,
                          revision_milestone: int, vector_blob: bytes,
                          projections_json: str, epoch_provenance: str) -> int:
    for attempt in range(3):
        seq = next_node_seq(conn, node_id)
        try:
            conn.execute("""
                INSERT INTO manifold_nodes
                (id, seq, text, toon_factor, lifecycle_state, action_potential, revision_milestone, vector_blob, projections_json, epoch_provenance)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                node_id, seq, text, toon_factor, lifecycle_state, action_potential,
                revision_milestone, vector_blob, projections_json, epoch_provenance,
            ))
            return seq
        except sqlite3.IntegrityError:
            if attempt == 2:
                raise
    return seq  # unreachable


def insert_node_revision(node_id: str, text: str, toon_factor: str,
                         lifecycle_state: str, action_potential: float,
                         revision_milestone: int, vector_blob: bytes,
                         projections_json: str, epoch_provenance: str,
                         conn: sqlite3.Connection | None = None) -> int:
    """Inserts a new node revision (append-only, H4); returns the seq used.

    When `conn` is provided, operates inside that transaction (no commit —
    the caller owns it); otherwise opens its own connection and commits.
    """
    if conn is None:
        with get_db_connection() as c:
            return _insert_node_revision(
                c, node_id, text, toon_factor, lifecycle_state, action_potential,
                revision_milestone, vector_blob, projections_json, epoch_provenance,
            )
    return _insert_node_revision(
        conn, node_id, text, toon_factor, lifecycle_state, action_potential,
        revision_milestone, vector_blob, projections_json, epoch_provenance,
    )


def _insert_error_log(conn: sqlite3.Connection, log_id: str, text: str,
                      toon_factor: str, action_potential: float,
                      revision_milestone: int, vector_blob: bytes,
                      projections_json: str,
                      event_type: str = EVENT_ERROR) -> None:
    if event_type not in (EVENT_ERROR, EVENT_RECALIBRATION_SIGNAL):
        raise ValueError(f"event_type must be ERROR or RECALIBRATION_SIGNAL, got {event_type!r}")
    seq = next_node_seq(conn, log_id)
    conn.execute("""
        INSERT INTO manifold_nodes
        (id, seq, text, toon_factor, lifecycle_state, action_potential, revision_milestone, vector_blob, projections_json, event_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        log_id, seq, text, toon_factor, "telemetry_error", action_potential,
        revision_milestone, vector_blob, projections_json, event_type,
    ))


def insert_error_log(log_id: str, text: str, toon_factor: str,
                     action_potential: float, revision_milestone: int,
                     vector_blob: bytes, projections_json: str,
                     event_type: str = EVENT_ERROR) -> None:
    """Persists an append-only telemetry_error log row."""
    with get_db_connection() as conn:
        _insert_error_log(
            conn, log_id, text, toon_factor, action_potential,
            revision_milestone, vector_blob, projections_json, event_type,
        )


def node_exists(conn: sqlite3.Connection, node_id: str) -> bool:
    """True when the node id is present in the append-only log (any seq)."""
    return conn.execute(
        "SELECT 1 FROM manifold_nodes WHERE id = ? LIMIT 1", (node_id,)
    ).fetchone() is not None


def get_current_nodes() -> list[tuple]:
    """Current-state nodes (MAX(seq) per id), telemetry_error excluded."""
    with get_db_connection() as conn:
        return conn.execute("""
            SELECT id, text, toon_factor, lifecycle_state, action_potential,
                   revision_milestone, projections_json
            FROM manifold_nodes m
            WHERE lifecycle_state != 'telemetry_error'
              AND seq = (SELECT MAX(seq) FROM manifold_nodes m2 WHERE m2.id = m.id)
            ORDER BY id DESC
        """).fetchall()


def get_telemetry_errors() -> list[tuple]:
    """Append-only telemetry_error log rows (current revision each)."""
    with get_db_connection() as conn:
        return conn.execute("""
            SELECT id, text, projections_json, sys_internal_timestamp, event_type
            FROM manifold_nodes m
            WHERE lifecycle_state = 'telemetry_error'
              AND seq = (SELECT MAX(seq) FROM manifold_nodes m2 WHERE m2.id = m.id)
            ORDER BY sys_internal_timestamp DESC
        """).fetchall()


# =====================================================================
# EDGE REVISION LOG / DETERMINISTIC E_n
# =====================================================================

def _insert_edge_revision(conn: sqlite3.Connection, edge_id: str, source: str,
                          target: str, state: str) -> int:
    seq = next_edge_seq(conn, edge_id)
    conn.execute("""
        INSERT INTO manifold_edges (id, seq, source, target, state)
        VALUES (?, ?, ?, ?, ?)
    """, (edge_id, seq, source, target, state))
    return seq


def insert_edge_revision(conn: sqlite3.Connection, edge_id: str, source: str,
                         target: str, state: str) -> int:
    """Inserts a new edge revision inside the caller's transaction (H4)."""
    return _insert_edge_revision(conn, edge_id, source, target, state)


def _current_node_vectors(conn: sqlite3.Connection) -> dict[str, np.ndarray]:
    """Current-state vectors (MAX(seq) per id), excluding telemetry_error.

    Shared DB read for E_n reconstruction/persistence (ADR-023/H5, RE-08/RE-09):
    telemetry_error log rows are not part of the manifold (mirrors /nodos).
    """
    rows = conn.execute("""
        SELECT m.id, m.vector_blob
        FROM manifold_nodes m
        WHERE m.lifecycle_state != 'telemetry_error'
          AND m.seq = (SELECT MAX(seq) FROM manifold_nodes m2 WHERE m2.id = m.id)
    """).fetchall()
    return {nid: np.frombuffer(blob, dtype=np.float64) for nid, blob in rows}


def rebuild_epsilon_edges(epsilon: float) -> list[dict]:
    """Deterministic E_n (ADR-023/H5, RE-08): (v_i, v_j) ∈ E_n iff ||v_i − v_j||₂ ≤ epsilon.

    Reads current states (MAX(seq)) from manifold_nodes (telemetry_error
    excluded), projects L2 vectors, and returns ε-adjacent edges. Does not
    mutate DB: E_n reconstruction is a pure function over persisted state.
    """
    with get_db_connection() as conn:
        nodes = _current_node_vectors(conn)
    return compute_epsilon_edges(nodes, epsilon)


def _persist_epsilon_edges(conn: sqlite3.Connection, epsilon: float) -> int:
    """Inserts auto/removed edge revisions for the current ε-adjacency (RE-09).

    Runs inside the caller's connection; the caller owns commit/rollback.
    """
    nodes = _current_node_vectors(conn)
    edges = compute_epsilon_edges(nodes, epsilon)
    desired = {f"auto-edge-{e['source']}-{e['target']}" for e in edges}

    prev = {
        r[0]: (r[1], r[2], r[3])
        for r in conn.execute("""
            SELECT id, source, target, state
            FROM manifold_edges e
            WHERE id LIKE 'auto-edge-%'
              AND seq = (SELECT MAX(seq) FROM manifold_edges e2 WHERE e2.id = e.id)
        """).fetchall()
    }

    for edge in edges:
        edge_id = f"auto-edge-{edge['source']}-{edge['target']}"
        if prev.get(edge_id) is None or prev[edge_id][2] != "auto":
            _insert_edge_revision(conn, edge_id, edge["source"], edge["target"], "auto")

    for edge_id in prev:
        if edge_id not in desired:
            source, target, _ = prev[edge_id]
            _insert_edge_revision(conn, edge_id, source, target, "removed")

    return len(edges)


def persist_epsilon_edges(epsilon: float, conn: sqlite3.Connection | None = None) -> int:
    """Persists deterministic E_n as auto-edge-<src>-<tgt> rows (RE-09, ADR-023/H5).

    Append-only (H4): never UPDATE/DELETE. State transitions are recorded as
    new revisions with increasing seq:
      * a newly adjacent pair (or one previously 'removed') INSERTS state='auto';
      * a pair that is no longer ε-adjacent INSERTS a tombstone state='removed'.
    The current view (get_relations) exposes MAX(seq) per id and excludes
    'removed'. Manual edge-* rows are preserved. Excludes telemetry_error nodes.
    If `conn` is provided, operates inside that transaction (no commit — the
    caller owns the transaction); otherwise opens its own connection and
    commits. Returns the number of currently adjacent auto edges.

    RE-09 contract primitive: the live E_n path is observational
    (`rebuild_epsilon_edges` computed on read, per SPEC M-a). This persistence
    function is exercised by the regression suite
    (tests/test_substrate.py::test_epsilon_edges_adjacency) and is available
    for a future server-side persistence delta.
    """
    if conn is None:
        with get_db_connection() as own_conn:
            return _persist_epsilon_edges(own_conn, epsilon)
    return _persist_epsilon_edges(conn, epsilon)


def get_current_edges() -> list[tuple]:
    """Current manual edge revisions (MAX(seq) per id), tombstones excluded."""
    with get_db_connection() as conn:
        return conn.execute("""
            SELECT id, source, target, state
            FROM manifold_edges e
            WHERE state != 'removed'
              AND seq = (SELECT MAX(seq) FROM manifold_edges e2 WHERE e2.id = e.id)
              AND id LIKE 'edge-%'
            ORDER BY id
        """).fetchall()
