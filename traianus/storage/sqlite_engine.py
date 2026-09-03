"""SQLite engine with WAL mode for polar projector data/control planes.

Table DDL is owned by ``traianus.storage._storage`` (ADR-025 amendment A1/A2:
DATA_PLANE_DDL / CONTROL_PLANE_DDL are the single source of truth); this
module only adds query indexes. ``insert_data_plane`` accepts an external
connection so callers can join a wider atomic transaction.
"""

import sqlite3
from contextlib import contextmanager

import numpy as np
from numpy.typing import NDArray

from traianus.storage._storage import CONTROL_PLANE_DDL, DATA_PLANE_DDL


class SQLiteEngine:
    """
    Dual-plane SQLite storage with WAL mode.

    data_plane:  Immutable semantic vectors, append-only PRIMARY KEY
        (node_id, seq) mirroring manifold_nodes (ADR-025 A2)
    control_plane: Hot execution cache (node_id PK, centroid_id, version)

    Both tables in same DB file for atomic cross-plane transactions.
    """

    def __init__(self, db_path: str = "traianus.db") -> None:
        """
        Initialize SQLiteEngine.

        Args:
            db_path: Path to SQLite database file. Defaults to "traianus.db".
        """
        self.db_path = db_path
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        """
        Create a new connection with WAL pragmas.

        Returns:
            Configured SQLite connection.
        """
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        return conn

    @contextmanager
    def _transaction(self):
        """
        Context manager for atomic transactions.

        Yields:
            SQLite connection with automatic commit/rollback.
        """
        conn = self._connect()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        """Create tables (shared DDL) and indexes if they don't exist."""
        with self._transaction() as conn:
            conn.execute(DATA_PLANE_DDL)
            conn.execute(CONTROL_PLANE_DDL)
            # Indexes for common queries (optimization, owned here)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_data_plane_updated ON data_plane(updated_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_control_plane_centroid ON control_plane(centroid_id)")

    # --- Data Plane (append-only revision log, ADR-025 A2) ---

    @staticmethod
    def _next_data_plane_seq(conn: sqlite3.Connection, node_id: str) -> int:
        row = conn.execute(
            "SELECT COALESCE(MAX(seq), 0) + 1 FROM data_plane WHERE node_id = ?",
            (node_id,),
        ).fetchone()
        return int(row[0])

    @classmethod
    def _insert_data_plane(
        cls, conn: sqlite3.Connection, node_id: str, vector: NDArray[np.float64]
    ) -> int:
        """Appends one vector revision; returns its seq. Never UPDATEs."""
        vec64 = np.asarray(vector, dtype=np.float64)
        blob = vec64.tobytes()
        dim = vec64.shape[0]
        seq = cls._next_data_plane_seq(conn, node_id)
        conn.execute("""
            INSERT INTO data_plane (node_id, seq, vector_blob, dimension, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, (node_id, seq, blob, dim))
        return seq

    def insert_data_plane(
        self,
        node_id: str,
        vector: NDArray[np.float64],
        conn: sqlite3.Connection | None = None,
    ) -> int:
        """
        Append a vector revision with dimension metadata.

        Append-only PRIMARY KEY (node_id, seq): re-ingestion of an existing
        node_id INSERTS a new revision, never overwrites (ADR-025 A2).
        Uses zero-copy serialization: float64.tobytes() / frombuffer(dtype=float64).

        Args:
            node_id: Unique node identifier.
            vector: Vector to store (any dimension, float64).
            conn: Optional external connection to join a wider atomic
                transaction (caller owns commit); otherwise commits alone.

        Returns:
            The seq assigned to the new revision.
        """
        if conn is None:
            with self._transaction() as own_conn:
                return self._insert_data_plane(own_conn, node_id, vector)
        return self._insert_data_plane(conn, node_id, vector)

    def get_data_plane(self, node_id: str) -> tuple[NDArray[np.float64], int] | None:
        """
        Retrieve the LATEST vector revision and dimension.

        Args:
            node_id: Node identifier.

        Returns:
            Tuple (vector, dimension) or None if not found.
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT vector_blob, dimension FROM data_plane WHERE node_id = ? "
                "ORDER BY seq DESC LIMIT 1",
                (node_id,)
            ).fetchone()

        if row is None:
            return None
        blob, dim = row
        vector = np.frombuffer(blob, dtype=np.float64)
        if vector.shape[0] != dim:
            raise ValueError(
                f"Dimension mismatch: blob has {vector.shape[0]} elements, metadata says {dim}"
            )
        return vector, dim

    # --- Control Plane ---

    def upsert_control_plane(self, node_id: str, centroid_id: int, version: int) -> None:
        """
        Insert or replace centroid mapping with version.

        Args:
            node_id: Node identifier (must exist in data_plane).
            centroid_id: Codebook centroid identifier.
            version: Monotonically increasing version number.
        """
        with self._transaction() as conn:
            conn.execute("""
                INSERT INTO control_plane (node_id, centroid_id, version)
                VALUES (?, ?, ?)
                ON CONFLICT(node_id) DO UPDATE SET
                    centroid_id = excluded.centroid_id,
                    version = excluded.version
            """, (node_id, centroid_id, version))

    def get_control_plane(self, node_id: str) -> tuple[int, int] | None:
        """
        Retrieve (centroid_id, version).

        Args:
            node_id: Node identifier.

        Returns:
            Tuple (centroid_id, version) or None if not found.
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT centroid_id, version FROM control_plane WHERE node_id = ?",
                (node_id,)
            ).fetchone()
        return row if row is None else (row[0], row[1])

    def increment_version(self, node_id: str) -> int:
        """
        Atomically increment version, return new version.

        Args:
            node_id: Node identifier.

        Returns:
            New version number.
        """
        with self._transaction() as conn:
            conn.execute(
                "UPDATE control_plane SET version = version + 1 WHERE node_id = ?",
                (node_id,)
            )
            row = conn.execute(
                "SELECT version FROM control_plane WHERE node_id = ?",
                (node_id,)
            ).fetchone()
        return row[0] if row else 0