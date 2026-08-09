"""
Ephemeral SQLite DB factory — SINGLE SOURCE OF DDL for the harness.

Phase 0 (Foundations). Structural invariant: this module is the ONLY place
in the test tree where `CREATE TABLE` statements are defined; the rest of
the harness consumes `create_schema()` / `create_test_db()`.

The schema MUST match `traianus/storage.py` (`init_relational_tables`) character
by character so tests verify the real system, not a divergent copy (finding L1).
"""
import json
import os
import sqlite3

import numpy as np

from traianus.app import serialize_vector

# ---------------------------------------------------------------------------
# Canonical DDL (only permitted definition in tests; grep "CREATE TABLE" == 1)
# ---------------------------------------------------------------------------

SCHEMA_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS geodesic_axes (
        id TEXT NOT NULL,
        simbolo TEXT NOT NULL,
        tag TEXT NOT NULL,
        vector_blob BLOB NOT NULL,
        epoch_provenance TEXT NOT NULL DEFAULT 'PROSTHETIC_NSM_V1',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (id, epoch_provenance)
    )
    """,
    """
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
        sys_internal_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (id, seq),
        CHECK (lifecycle_state IN ('pending_approval', 'incubating', 'consolidated', 'telemetry_error'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ingestion_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        payload TEXT NOT NULL,
        idempotency_key TEXT UNIQUE,
        status TEXT DEFAULT 'PENDING',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS manifold_edges (
        id TEXT NOT NULL,
        seq INTEGER NOT NULL,
        source TEXT NOT NULL,
        target TEXT NOT NULL,
        state TEXT NOT NULL,
        sys_internal_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (id, seq)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_log (
        case_id TEXT PRIMARY KEY,
        timestamp TEXT DEFAULT (datetime('now')),
        intent_class TEXT,
        target_file TEXT,
        decision TEXT NOT NULL,
        safety_abort TEXT
    )
    """,
]

AXIS_COUNT = 8
AXIS_DIM = 384


def create_schema(conn: sqlite3.Connection) -> None:
    """Creates the complete relational schema on an existing connection."""
    conn.execute("PRAGMA journal_mode=WAL;")
    for statement in SCHEMA_STATEMENTS:
        conn.execute(statement)


def seed_onehot_axes(conn: sqlite3.Connection, axis_count: int = AXIS_COUNT, dim: int = AXIS_DIM) -> None:
    """
    One-hot geometry (historical behavior of pre-Phase 0 unit tests).
    Each axis is a canonical vector e_i; basis is orthonormal (off-diagonal
    cosine == 0). Suitable for C1 regression tests expecting threshold exactly
    0.0. Realistic geometry (NSM) lives in `nsm_axes_8.json` fixture and is
    seeded with `seed_realistic_axes`.
    """
    for idx in range(axis_count):
        vec = np.zeros(dim, dtype=np.float64)
        vec[idx] = 1.0
        conn.execute(
            "INSERT INTO geodesic_axes (id, simbolo, tag, vector_blob) VALUES (?, ?, ?, ?)",
            (f"AXIS_{idx + 1}", chr(0x25B2 + idx), f"_AXIS_{idx + 1}", serialize_vector(vec)),
        )


def seed_realistic_axes(conn: sqlite3.Connection, fixture_path: str | None = None) -> None:
    """
    FROZEN realistic geometry (Phase 0): NSM octagon exported by
    `tools/export_nsm_axes.py` from the real all-MiniLM-L6-v2 model (off-diag
    cosine ≈ 0.23, max ≈ 0.34). Allows hermetic tests with production
    geometry WITHOUT loading the model (L1).
    """
    if fixture_path is None:
        fixture_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "fixtures", "nsm_axes_8.json",
        )
    with open(fixture_path, encoding="utf-8") as fh:
        axes = json.load(fh)
    for entry in axes:
        vec = np.asarray(entry["vector"], dtype=np.float64)
        conn.execute(
            "INSERT INTO geodesic_axes (id, simbolo, tag, vector_blob) VALUES (?, ?, ?, ?)",
            (entry["id"], entry["simbolo"], entry["tag"], serialize_vector(vec)),
        )


def create_test_db(path: str, seed: str = "onehot") -> str:
    """
    Creates an ephemeral SQLite DB with full schema and seeded geodetic
    geometry. Returns the path.

    `seed` ∈ {"onehot", "realistic"}. "onehot" preserves historical
    behavior of the 34 pre-Phase 0 tests; "realistic" seeds the frozen
    real geometry from tests/fixtures/nsm_axes_8.json.
    """
    with sqlite3.connect(path) as conn:
        create_schema(conn)
        if seed == "realistic":
            seed_realistic_axes(conn)
        else:
            seed_onehot_axes(conn)
        conn.commit()
    return path
