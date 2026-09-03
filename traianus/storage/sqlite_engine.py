"""SQLite engine with WAL mode for polar projector data/control planes."""

import sqlite3
from contextlib import contextmanager
from typing import Optional, Tuple
import numpy as np
from numpy.typing import NDArray


class SQLiteEngine:
    """
    Dual-plane SQLite storage with WAL mode.

    data_plane:  Immutable semantic vectors (node_id PK, vector BLOB, dimension, updated_at)
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
        """Create tables and indexes if they don't exist."""
        with self._transaction() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS data_plane (
                    node_id TEXT PRIMARY KEY,
                    vector_blob BLOB NOT NULL,
                    dimension INTEGER NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS control_plane (
                    node_id TEXT PRIMARY KEY,
                    centroid_id INTEGER NOT NULL,
                    version INTEGER NOT NULL DEFAULT 0,
                    FOREIGN KEY (node_id) REFERENCES data_plane(node_id)
                )
            """)
            # Indexes for common queries
            conn.execute("CREATE INDEX IF NOT EXISTS idx_data_plane_updated ON data_plane(updated_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_control_plane_centroid ON control_plane(centroid_id)")

    # --- Data Plane ---

    def upsert_data_plane(self, node_id: str, vector: NDArray[np.float64]) -> None:
        """
        Insert or replace vector with dimension metadata.

        Uses zero-copy serialization: float64.tobytes() / frombuffer(dtype=float64).

        Args:
            node_id: Unique node identifier.
            vector: Vector to store (any dimension, float64).
        """
        vec64 = np.asarray(vector, dtype=np.float64)
        blob = vec64.tobytes()
        dim = vec64.shape[0]

        with self._transaction() as conn:
            conn.execute("""
                INSERT INTO data_plane (node_id, vector_blob, dimension, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(node_id) DO UPDATE SET
                    vector_blob = excluded.vector_blob,
                    dimension = excluded.dimension,
                    updated_at = CURRENT_TIMESTAMP
            """, (node_id, blob, dim))

    def get_data_plane(self, node_id: str) -> Optional[Tuple[NDArray[np.float64], int]]:
        """
        Retrieve vector and dimension.

        Args:
            node_id: Node identifier.

        Returns:
            Tuple (vector, dimension) or None if not found.
        """
        with self._connect() as conn:
            row = conn.execute(
                "SELECT vector_blob, dimension FROM data_plane WHERE node_id = ?",
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

    def get_control_plane(self, node_id: str) -> Optional[Tuple[int, int]]:
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